#!/usr/bin/env python3
"""
PostToolUse hook (Edit/Write): targeted documentation staleness reminder.

Replaces the legacy ``track_edits.py`` generic code-vs-doc nudge with a
semantic check: when a source file is edited, grep the ``docs/`` tree for
references to that file and, if any are found, print a targeted reminder
naming the specific docs that may need review.

Design goals (see plugins/qute-essentials/skills/decision/SKILL.md and
the project's doc-enforcement discussion):

- **Targeted, not generic**. Only fires for files that are actually
  referenced by documentation. Files with no doc references are silent -
  this avoids the noise of the old generic "you've edited N code files
  without touching docs" nudge that fired on every untracked file.

- **Classified by doc type**. Matches are grouped by location so the
  reminder can recommend the right action:
    * ``docs/decisions/``      -> ADR governance - consider if edit
                                    supersedes the decision
    * ``docs/methodology/``    -> design-rationale doc - check freshness
    * ``docs/reference/``      -> reference doc - check schema/signature
                                    consistency
    * ``docs/instructions/``   -> operational doc - check steps still work
    * other ``docs/**/*.md``   -> generic doc reference

- **Session-scoped dedupe**. Each (file, session) pair gets at most one
  reminder, stored in a per-session tempfile (same mechanism as the old
  track_edits.py).

- **Skip list**. Binary files, scratch/data/output dirs, the ``.claude/``
  tree, and the ``docs/`` tree itself are silently ignored (editing docs
  doesn't trigger a reminder about docs).

- **Fail-soft**. Any error exits cleanly with code 0 so the hook never
  blocks an edit.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

# Session identifier for per-session dedupe state
SESSION_ID = os.environ.get("CLAUDE_SESSION_ID", str(os.getppid()))
STATE_FILE = Path(tempfile.gettempdir()) / f"doc-reminder-{SESSION_ID}.json"

# Directories and extensions to skip entirely
SKIP_DIR_PARTS = {
    ".claude",
    "scratch",
    "data",
    "output",
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".whl",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".lock",
    ".parquet",
    ".pkl",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
}

# Source code extensions that warrant a reminder check when edited
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".sql",
}

# Category classification by doc path prefix under docs/
DOC_CATEGORIES = [
    ("docs/decisions", "ADR"),
    ("docs/methodology", "methodology"),
    ("docs/reference", "reference"),
    ("docs/instructions", "instructions"),
]


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return {"reminded_files": []}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state))
    except OSError:
        pass  # tempfile write failure is non-fatal


def should_skip(file_path: str) -> bool:
    """Return True if this file path should not trigger a reminder check."""
    if not file_path:
        return True
    p = Path(file_path)

    # Skip any path that contains a skip-list directory part
    for part in p.parts:
        if part in SKIP_DIR_PARTS:
            return True

    # Skip doc files themselves (editing a doc doesn't trigger a self-reminder)
    if "docs" in p.parts and p.suffix.lower() == ".md":
        return True

    # Skip binaries and known non-source extensions
    if p.suffix.lower() in SKIP_EXTENSIONS:
        return True

    # Only consider actual source code files
    if p.suffix.lower() not in CODE_EXTENSIONS:
        return True

    return False


def find_repo_root(start: Path) -> Path:
    """Walk upward from start until a .git directory is found, else return start."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return start


def find_doc_references(repo_root: Path, file_path: str) -> list[tuple[Path, str]]:
    """
    Find all docs/**/*.md files that reference the edited file.

    Returns a list of (doc_path, category) tuples. Matches on either the
    full relative path or the bare filename. Scans up to 500 doc files and
    reads up to 200KB per file to bound cost.
    """
    docs_dir = repo_root / "docs"
    if not docs_dir.exists():
        return []

    rel_path = Path(file_path)
    try:
        rel_path = rel_path.resolve().relative_to(repo_root)
    except (ValueError, OSError):
        rel_path = Path(file_path)

    rel_str = str(rel_path).replace("\\", "/")
    basename = rel_path.name

    results: list[tuple[Path, str]] = []
    doc_files = list(docs_dir.rglob("*.md"))[:500]

    for doc in doc_files:
        try:
            content = doc.read_text(encoding="utf-8", errors="ignore")[:200_000]
        except OSError:
            continue

        # Match if ANY needle appears - prefer exact path matches, but
        # bare-basename matches are fine for most cases
        matched = False
        if rel_str in content:
            matched = True
        elif basename in content:
            # Require the basename to appear with a word boundary (avoid
            # matching e.g. "foo.py" inside "foofoo.py")
            if re.search(rf"\b{re.escape(basename)}\b", content):
                matched = True

        if not matched:
            continue

        # Classify by category
        rel_doc = doc.resolve().relative_to(repo_root)
        rel_doc_str = str(rel_doc).replace("\\", "/")
        category = "docs"
        for prefix, label in DOC_CATEGORIES:
            if rel_doc_str.startswith(prefix):
                category = label
                break
        results.append((rel_doc, category))

    return results


def format_reminder(file_path: str, matches: list[tuple[Path, str]]) -> str:
    """Build the reminder message. Groups matches by category."""
    lines = [f"[DocReminder] {file_path} is referenced by documentation:"]

    by_category: dict[str, list[Path]] = {}
    for doc_path, category in matches:
        by_category.setdefault(category, []).append(doc_path)

    for category in ("ADR", "methodology", "reference", "instructions", "docs"):
        if category not in by_category:
            continue
        for doc_path in by_category[category]:
            rel = str(doc_path).replace("\\", "/")
            if category == "ADR":
                # Extract ADR number from filename if possible (e.g. 0004-foo.md -> 0004)
                m = re.match(r"(\d{4})-", doc_path.name)
                adr_num = m.group(1) if m else ""
                adr_label = f"ADR-{adr_num}" if adr_num else rel
                lines.append(
                    f"  * {adr_label} ({rel}) - ensure edit is consistent "
                    f"or invoke /decision --supersedes {adr_num} if it "
                    f"changes the decision"
                )
            elif category == "methodology":
                lines.append(
                    f"  * methodology: {rel} - check for freshness after this edit"
                )
            elif category == "reference":
                lines.append(
                    f"  * reference: {rel} - check schema / signature consistency"
                )
            elif category == "instructions":
                lines.append(
                    f"  * instructions: {rel} - verify operational steps still work"
                )
            else:
                lines.append(f"  * {rel} - review for freshness")

    lines.append("Review these before committing.")
    return "\n".join(lines)


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path or should_skip(file_path):
        return

    repo_root = find_repo_root(
        Path(file_path).parent if Path(file_path).is_absolute() else Path.cwd()
    )

    matches = find_doc_references(repo_root, file_path)
    if not matches:
        return  # Silent on untracked files - this is the point

    # Session-scoped dedupe: don't remind twice per file per session
    state = load_state()
    reminded = set(state.get("reminded_files", []))
    key = str(Path(file_path).as_posix())
    if key in reminded:
        return
    reminded.add(key)
    state["reminded_files"] = sorted(reminded)
    save_state(state)

    print(format_reminder(file_path, matches))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)
