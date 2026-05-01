"""Validate TASKS.md and docs/tasks/*.md format conventions.

Two checks:

1. Root TASKS.md sections begin with `Now`, `Next`, `Later` in that
   order, followed by one or more `Completed*` sections (the dated-batch
   convention `## Completed (YYYY-MM-DD — note)` is allowed). Now must
   hold ≤ 3 active items, where an "item" is either a `- [ ]` checkbox
   bullet or a `### header` subsection — projects pick one shape.
2. Every docs/tasks/*.md (excluding completed/) either has no YAML
   frontmatter at all OR has the full agentic-task schema. Half-frontmatter
   files (some required keys present, others missing) are an error per
   .claude/rules/agentic-tasks.md.

Exit 0 when clean, exit 1 on any violation. Violations are printed one
per line to stderr so callers (`/handoff`, `/pickup`) can surface them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_PREFIX = ("Now", "Next", "Later")
COMPLETED_PATTERN = re.compile(r"^Completed\b")
NOW_CAP = 3

# Required top-level keys for an agentic-task plan per
# .claude/rules/agentic-tasks.md. A file with NONE of these is a plain
# human-only plan and is allowed. A file with SOME but not all is a
# half-frontmatter error.
DISPATCHABLE_REQUIRED = {
    "slug",
    "agent",
    "phases",
    "outputs",
    "validation",
    "done_when",
}


def parse_frontmatter_keys(text: str) -> set[str] | None:
    """Return the set of top-level YAML keys, or None if no frontmatter.

    Naive — only matches `key:` at column 0 between the leading `---\\n`
    and the closing `\\n---\\n`. Sufficient for presence checks; we never
    need to interpret values here.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    block = text[4:end]
    return {
        m.group(1) for line in block.splitlines() if (m := re.match(r"^([a-z_][a-z_0-9]*):", line))
    }


def check_tasks_md(root: Path) -> list[str]:
    f = root / "TASKS.md"
    if not f.exists():
        return []
    text = f.read_text(encoding="utf-8")

    # Capture the first word of each `## ` heading so dated-batch headers
    # like "## Completed (2026-04-30 — Phase B/C)" still match "Completed".
    headings = tuple(re.findall(r"^##\s+(\w+)", text, re.MULTILINE))
    violations: list[str] = []

    # First three headings must be exactly Now, Next, Later in order.
    if headings[:3] != REQUIRED_PREFIX:
        violations.append(
            f"TASKS.md: first three sections must be {list(REQUIRED_PREFIX)} in order; "
            f"found {list(headings[:3])}"
        )
    # Everything after must be at least one `Completed*` section.
    tail = headings[3:]
    if not tail or not all(COMPLETED_PATTERN.match(h) for h in tail):
        violations.append(
            f"TASKS.md: after Later, expected one or more `Completed` sections; "
            f"found {list(tail) or '<none>'}"
        )

    # Now-cap check. Projects use one of two item shapes:
    #   - `### Header` subsections (with nested bullets as sub-tasks), OR
    #   - top-level `- [ ]` checkbox bullets.
    # If any `###` is present, those are the items (don't double-count the
    # nested bullets). Otherwise count `- [ ]` bullets at column 0.
    now_match = re.search(r"^##\s+Now\b.*?\n(.*?)(?=^##\s+|\Z)", text, re.MULTILINE | re.DOTALL)
    if now_match:
        body = now_match.group(1)
        subheads = re.findall(r"^###\s+", body, re.MULTILINE)
        if subheads:
            n = len(subheads)
        else:
            n = len(re.findall(r"^-\s+\[[ x]\]", body, re.MULTILINE))
        if n > NOW_CAP:
            violations.append(
                f"TASKS.md: ## Now has {n} items (soft cap {NOW_CAP}) — demote some to Next"
            )
    return violations


def check_task_plans(root: Path) -> list[str]:
    plans_dir = root / "docs" / "tasks"
    if not plans_dir.exists():
        return []
    violations: list[str] = []
    for f in sorted(plans_dir.glob("*.md")):
        keys = parse_frontmatter_keys(f.read_text(encoding="utf-8"))
        if keys is None:
            continue  # no frontmatter — plain human-only plan
        present = keys & DISPATCHABLE_REQUIRED
        missing = DISPATCHABLE_REQUIRED - keys
        if present and missing:
            violations.append(
                f"{f.relative_to(root)}: dispatchable frontmatter is incomplete — "
                f"has {sorted(present)} but missing {sorted(missing)}; "
                f"either complete the schema or remove all dispatchable fields"
            )
    return violations


def main() -> int:
    root = Path.cwd()
    violations = check_tasks_md(root) + check_task_plans(root)
    if not violations:
        return 0
    print("validate_tasks: format violations:", file=sys.stderr)
    for v in violations:
        print(f"  - {v}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
