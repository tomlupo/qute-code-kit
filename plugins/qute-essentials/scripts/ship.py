"""/ship — universal release command.

One entry point, two modes (detected automatically):

* **Plugin mode** — `.claude-plugin/marketplace.json` at repo root.
  Delegates to `scripts/release-plugin.sh <plugin> <bump>`.
* **Python mode** — `pyproject.toml` at repo root (and no marketplace).
  Refuses to bump if any tracked file lives under a forbidden path or if the
  tracked working tree is dirty, runs first-time-setup idempotently, then
  bumps.

Python mode drives commitizen in **files-only** mode
(`cz bump --yes --changelog --version-files-only`): cz rewrites the version
files and `CHANGELOG.md` but creates neither commit nor tag. This script then
creates the bump commit and an **annotated** tag itself. One tagging path,
owned here — a lightweight tag is silently skipped by `git push
--follow-tags`, so a release can otherwise look cut while never leaving the
machine.

Webapps (`package.json`) use `gstack ship` instead.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import shutil
import string
import subprocess
import sys
from pathlib import Path

# Universal forbidden paths — skill-generated artifacts that must not reach main.
# Project-specific additions live in .claude/forbidden-paths.txt (one per line).
UNIVERSAL_FORBIDDEN = (
    "docs/superpowers",
    "docs/specs",
    ".claude/handoffs",
    ".claude/skill-use-log.jsonl",
)

BUMP_KINDS = {"patch", "minor", "major"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# commitizen's own defaults — mirrored so the history a repo already has stays
# continuous when ship.py takes over commit/tag creation from cz.
DEFAULT_TAG_FORMAT = "v$version"
BUMP_MESSAGE = "bump: version $current_version → $new_version"
DEFAULT_CHANGELOG_FILE = "CHANGELOG.md"


def info(msg: str) -> None:
    print(f"ship: {msg}")


def fail(msg: str) -> int:
    print(f"ship: error: {msg}", file=sys.stderr)
    return 1


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


USAGE = """\
Usage:
  /ship [--dry-run]                                  # Python: auto-bump from commits
  /ship [patch|minor|major|X.Y.Z] [--dry-run]        # Python: forced bump
  /ship [<plugin>] <patch|minor|major|X.Y.Z>         # Plugin: delegate to release-plugin.sh

Detects mode by repo root:
  .claude-plugin/marketplace.json → plugin mode
  pyproject.toml                  → python mode
"""


def main() -> int:
    args = sys.argv[1:]
    if any(a in {"-h", "--help"} for a in args):
        print(USAGE)
        return 0

    root = Path.cwd()

    marketplace_json = root / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        return ship_plugin(root, marketplace_json, args)

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        return ship_python(root, pyproject, args)

    if (root / "package.json").exists():
        return fail(
            "package.json detected — webapps are handled by `gstack ship`, not `/ship`."
        )

    if (root / "Cargo.toml").exists():
        return fail("Cargo.toml detected — Rust is not yet supported.")

    return fail(
        "no supported project type detected. "
        "/ship requires `.claude-plugin/marketplace.json` (plugin mode) "
        "or `pyproject.toml` (Python mode) at the repo root."
    )


# ---------------------------------------------------------------------------
# Plugin mode
# ---------------------------------------------------------------------------


def ship_plugin(root: Path, marketplace_json: Path, args: list[str]) -> int:
    with open(marketplace_json) as f:
        marketplace = json.load(f)

    plugins = [p["name"] for p in marketplace.get("plugins", [])]
    if not plugins:
        return fail(f"{marketplace_json.relative_to(root)} has no plugins")

    if len(args) == 2:
        plugin_name, bump_spec = args
    elif len(args) == 1:
        if len(plugins) > 1:
            return fail(
                f"marketplace has multiple plugins ({', '.join(plugins)}); "
                "specify name: /ship <plugin> <patch|minor|major|X.Y.Z>"
            )
        plugin_name = plugins[0]
        bump_spec = args[0]
    else:
        return fail("usage: /ship [<plugin>] <patch|minor|major|X.Y.Z>")

    if plugin_name not in plugins:
        return fail(
            f"plugin '{plugin_name}' not in marketplace; available: {', '.join(plugins)}"
        )

    if bump_spec not in BUMP_KINDS and not SEMVER_RE.match(bump_spec):
        return fail(
            f"bump spec '{bump_spec}' must be patch|minor|major or explicit X.Y.Z"
        )

    release_script = root / "scripts" / "release-plugin.sh"
    if not release_script.exists():
        return fail(f"{release_script.relative_to(root)} not found")

    try:
        run(["bash", str(release_script), plugin_name, bump_spec])
    except subprocess.CalledProcessError as exc:
        return fail(f"release-plugin.sh failed with exit code {exc.returncode}")
    return 0


# ---------------------------------------------------------------------------
# Python mode
# ---------------------------------------------------------------------------


def parse_python_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="/ship", add_help=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--increment", choices=sorted(BUMP_KINDS))
    parsed, leftover = parser.parse_known_args(args)
    parsed.version = None
    for a in leftover:
        if SEMVER_RE.match(a):
            parsed.version = a
        elif a in BUMP_KINDS:
            parsed.increment = a
        else:
            parser.error(f"unknown argument: {a}")
    return parsed


def ship_python(root: Path, pyproject: Path, args: list[str]) -> int:
    parsed = parse_python_args(args)

    # 1. Forbidden-paths check.
    if rc := check_forbidden_paths(root):
        return rc

    # 2. Clean-tree gate. Deliberately BEFORE setup: setup legitimately writes
    #    to pyproject.toml / CHANGELOG.md, so checking afterwards would trip on
    #    its own edits. Everything from here on is either a write or a commit.
    if rc := check_clean_worktree(root, dry_run=parsed.dry_run):
        return rc

    # 3. First-time setup — idempotent; safe to call every time.
    from ship_setup import setup_python

    if rc := setup_python(root, pyproject):
        return rc

    # 4. Build the cz command.
    #
    # `--version-files-only` makes cz a pure file rewriter: it bumps every
    # `version_files` entry AND the `[tool.commitizen] version` field, writes
    # the changelog, and then stops — no commit, no tag, changes left in the
    # working tree. Commit and tag creation happen below, in this script, so
    # there is exactly ONE tagging path and it always produces an annotated tag.
    if shutil.which("uv"):
        cz = ["uv", "run", "cz"]
    elif shutil.which("cz"):
        cz = ["cz"]
    else:
        return fail("neither `uv` nor `cz` found on PATH. Install commitizen or uv.")

    cmd = [*cz, "bump", "--yes", "--changelog", "--version-files-only"]

    if parsed.dry_run:
        cmd.append("--dry-run")
    if parsed.increment:
        cmd += ["--increment", parsed.increment.upper()]
    if parsed.version:
        cmd.append(parsed.version)

    cz_config = _read_cz_config(pyproject)
    old_version = _current_version(root, pyproject, cz)

    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        return fail(f"commitizen bump failed with exit code {exc.returncode}")

    if parsed.dry_run:
        info("dry run complete; no files written, no commit or tag created.")
        return 0

    # 5. Create the bump commit — cz's own default message, so `git log` reads
    #    continuously across the handover.
    new_version = _current_version(root, pyproject, cz)
    if not new_version:
        return fail(
            "could not read the bumped version from pyproject.toml after cz bump; "
            "the version files were rewritten but no commit or tag was created."
        )
    if old_version == new_version:
        return fail(
            f"cz bump left the version unchanged at {new_version}; "
            "no commit or tag created."
        )

    message = (
        string.Template(BUMP_MESSAGE)
        .safe_substitute(current_version=old_version or "?", new_version=new_version)
        .strip()
    )
    if rc := git_commit_bump(root, pyproject, cz_config, message):
        return rc

    # 6. Create the tag — ALWAYS annotated. `git push --follow-tags` silently
    #    ignores lightweight tags, so a release cut with one never leaves the
    #    machine; making it annotated here removes the dependency on a config
    #    key (`annotated_tag`) being set correctly in every consuming repo.
    tag = resolve_tag(root, cz, cz_config, new_version)
    tag_message = build_tag_message(root, cz_config, tag, new_version)
    try:
        # `--cleanup=whitespace` because the default (`strip`) treats lines
        # beginning with `#` as comments and deletes them — which silently eats
        # the `### Feat` / `### Fix` headings out of a markdown changelog body.
        run(
            [
                "git",
                "-C",
                str(root),
                "tag",
                "-a",
                "--cleanup=whitespace",
                tag,
                "-m",
                tag_message,
            ]
        )
    except subprocess.CalledProcessError as exc:
        return fail(f"`git tag -a {tag}` failed with exit code {exc.returncode}")
    info(f"created annotated tag {tag}")

    # 7. Wipe TASKS.md::Completed sections — canonical now in CHANGELOG.md.
    #    Deliberately AFTER the tag: its follow-up commit must land on top of
    #    the bump commit and must not be captured by the release tag.
    wipe_tasks_completed(root, pyproject)

    info(
        "done. Review the bump commit and tag, then `git push --follow-tags` when ready."
    )
    return 0


def git_commit_bump(
    root: Path, pyproject: Path, cz_config: dict[str, object], message: str
) -> int:
    """Stage the files cz rewrote and create the bump commit."""
    files = bumped_files(root, pyproject, cz_config)
    if not files:
        return fail("cz bump rewrote no files; nothing to commit.")

    try:
        run(["git", "-C", str(root), "add", "--", *files])
        run(["git", "-C", str(root), "commit", "-m", message])
    except subprocess.CalledProcessError as exc:
        return fail(f"bump commit failed with exit code {exc.returncode}")
    return 0


def bumped_files(
    root: Path, pyproject: Path, cz_config: dict[str, object]
) -> list[str]:
    """Paths cz may have rewritten: version_files + config file + changelog.

    `pyproject.toml` is always included because cz writes the new version into
    `[tool.commitizen] version` there regardless of `version_files`.
    """
    candidates: list[Path] = [pyproject]

    version_files = cz_config.get("version_files")
    if isinstance(version_files, list):
        for entry in version_files:
            if not isinstance(entry, str):
                continue
            # `path:pattern` — cz splits on the first colon; the path half may
            # itself be a glob.
            raw = entry.split(":", 1)[0].strip()
            if not raw:
                continue
            matches = glob.glob(str(root / raw))
            if matches:
                candidates.extend(Path(m) for m in matches)
            else:
                candidates.append(root / raw)

    changelog = cz_config.get("changelog_file")
    candidates.append(
        root / (changelog if isinstance(changelog, str) else DEFAULT_CHANGELOG_FILE)
    )

    seen: dict[str, None] = {}
    for path in candidates:
        if not path.exists():
            continue
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:  # outside the repo — cz would not have touched it
            continue
        seen.setdefault(rel, None)
    return list(seen)


def build_tag_message(
    root: Path, cz_config: dict[str, object], tag: str, version: str
) -> str:
    """Message for the annotated release tag.

    An annotated tag carries a message, so it should say what shipped rather
    than restate its own name — `git show <tag>` and `git tag -n99` then
    display the release notes without anyone opening the changelog.

    Precedence: an explicit `annotated_tag_message` wins (the repo asked for a
    fixed message); otherwise `Release <tag>` plus this version's changelog
    section when it can be located; otherwise `Release <tag>` alone. Extraction
    is best-effort — a tag with a thin message beats a failed release.
    """
    configured = cz_config.get("annotated_tag_message")
    if isinstance(configured, str) and configured.strip():
        return configured

    subject = f"Release {tag}"
    body = changelog_section(root, cz_config, version)
    return f"{subject}\n\n{body}" if body else subject


def changelog_section(
    root: Path, cz_config: dict[str, object], version: str
) -> str | None:
    """The changelog body for `version`, or None if it can't be located.

    Matches the first `## ` heading mentioning the version and returns the
    lines up to the next `## `. Tolerant of the heading styles commitizen
    emits (`## v1.2.0 (2026-07-28)`, `## 1.2.0`).
    """
    name = cz_config.get("changelog_file")
    changelog = root / (name if isinstance(name, str) and name else "CHANGELOG.md")
    try:
        lines = changelog.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and version in line:
            start = i + 1
            break
    if start is None:
        return None

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    body = "\n".join(lines[start:end]).strip()
    return body or None


def resolve_tag(
    root: Path, cz: list[str], cz_config: dict[str, object], version: str
) -> str:
    """The tag name commitizen itself would use for `version`.

    `tag_format` is commitizen's syntax, not this script's. It accepts more
    variables than the four rendered below — `$prerelease`, `$devrelease` —
    and cz used the real format to compute the version and the changelog. A
    tag rendered by a second, partial formatter is exactly the provenance
    break this script exists to prevent: git would carry `v1.2.3$prerelease`
    while cz's history says `v1.2.3`. So ask the tool that owns the format.

    `cz version --project --tag` prints the tag for the version currently in
    the project — which, run AFTER the files-only bump, is the new one. It
    also honours a non-default `version_provider`, which local rendering
    cannot see.

    Falls back to local `string.Template` rendering when the query fails or
    returns something unusable (empty output, or whitespace — cz reports "no
    project information" on stderr and prints nothing). A thin tag beats
    aborting a release whose bump commit has already landed; the fallback
    announces itself rather than swapping the tag silently.
    """
    try:
        result = subprocess.run(
            [*cz, "version", "--project", "--tag"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        local = render_tag(cz_config, version)
        info(f"`cz version --project --tag` failed ({exc}); using local tag {local}")
        return local

    tag = result.stdout.strip()
    if not tag or any(ch.isspace() for ch in tag):
        local = render_tag(cz_config, version)
        info(
            "`cz version --project --tag` returned no usable tag "
            f"({tag!r}); using local tag {local}"
        )
        return local
    return tag


def render_tag(cz_config: dict[str, object], version: str) -> str:
    """Local fallback for `tag_format` — only used when cz cannot be asked.

    Deliberately partial: it knows `$version`/`$major`/`$minor`/`$patch` and
    leaves anything else as a literal. `resolve_tag` is the real answer.
    """
    fmt = cz_config.get("tag_format")
    if not isinstance(fmt, str) or not fmt.strip():
        fmt = DEFAULT_TAG_FORMAT
    parts = (version.split("-", 1)[0].split(".") + ["0", "0", "0"])[:3]
    return string.Template(fmt).safe_substitute(
        version=version,
        major=parts[0],
        minor=parts[1],
        patch=parts[2],
    )


def _current_version(root: Path, pyproject: Path, cz: list[str]) -> str | None:
    """Version cz considers current — the config field, or ask cz's provider."""
    if version := _read_pyproject_version(pyproject):
        return version
    # Non-default `version_provider` (pep621, uv, …) keeps the version
    # elsewhere; cz itself is the only reliable reader.
    try:
        result = subprocess.run(
            [*cz, "version", "--project"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def wipe_tasks_completed(root: Path, pyproject: Path) -> None:
    """Remove `## Completed (...)` sections from TASKS.md after a successful bump."""
    tasks = root / "TASKS.md"
    if not tasks.exists():
        return

    content = tasks.read_text(encoding="utf-8")
    # Tier-1 only: a repo that graduated to GitHub Issues leaves TASKS.md as a
    # migration tombstone — its completion record lives in the Issues tab.
    if "qute-tasks: migrated-to-github" in content:
        return

    pattern = re.compile(
        r"^## Completed\b[^\n]*\n.*?(?=^## |^---\s*$|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    new_content, n = pattern.subn("", content)
    if n == 0:
        return

    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    tasks.write_text(new_content, encoding="utf-8")

    version = _read_pyproject_version(pyproject) or "release"
    try:
        subprocess.run(["git", "add", "TASKS.md"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore(tasks): wipe Completed after v{version}"],
            cwd=root,
            check=True,
        )
        info(f"wiped {n} Completed section(s) from TASKS.md")
    except subprocess.CalledProcessError:
        info("TASKS.md sweep skipped (git add/commit failed — check working tree)")


def _read_pyproject_version(pyproject: Path) -> str | None:
    version = _read_cz_config(pyproject).get("version")
    return version if isinstance(version, str) else None


def _read_cz_config(pyproject: Path) -> dict[str, object]:
    """The `[tool.commitizen]` table, or `{}` if absent/unreadable."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        return _read_cz_config_regex(pyproject)

    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return _read_cz_config_regex(pyproject)

    tool = data.get("tool")
    cz = tool.get("commitizen") if isinstance(tool, dict) else None
    return cz if isinstance(cz, dict) else {}


def _read_cz_config_regex(pyproject: Path) -> dict[str, object]:
    """Fallback parse of the keys /ship needs, for interpreters without tomllib."""
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return {}
    block = re.search(r"^\[tool\.commitizen\]\n(.*?)(?=^\[|\Z)", content, re.S | re.M)
    if not block:
        return {}
    text = block.group(1)

    config: dict[str, object] = {}
    for key in ("version", "tag_format", "changelog_file", "annotated_tag_message"):
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', text, re.MULTILINE)
        if m:
            config[key] = m.group(1)
    vf = re.search(r"^version_files\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if vf:
        config["version_files"] = re.findall(r'"([^"]+)"', vf.group(1))
    return config


def check_clean_worktree(root: Path, *, dry_run: bool = False) -> int:
    """Refuse to bump when tracked files carry uncommitted changes.

    Mirrors the gate `release-plugin.sh` already applies in plugin mode, in
    both check and spirit: ANY modified tracked file blocks, not just the
    configured `version_files`. The bump commit stages whole files, so an
    unrelated edit would ride into the commit that the release tag points at,
    and consumers pin that tag. Releases come from a clean tree.

    Untracked files are deliberately ignored (`--untracked-files=no`, same as
    plugin mode): a lockfile, scratch output, or a stray build artifact is
    routine and must not be able to block a release.

    `--dry-run` reports instead of refusing. A dry run answers "what would
    ship" and creates neither commit nor tag, so a dirty tree cannot
    contaminate anything — and checking the next version mid-edit is exactly
    when a dry run earns its keep.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repo, or no git on PATH. Nothing to protect here; the
        # commit/tag steps later on fail loudly by themselves.
        return 0

    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if not dirty:
        return 0

    if dry_run:
        info("working tree has uncommitted tracked changes:")
        for line in dirty:
            print(f"  {line}")
        info("dry run — reporting only; a real release refuses until these are clean.")
        return 0

    print("ship: error: working tree has uncommitted tracked changes:", file=sys.stderr)
    for line in dirty:
        print(f"  {line}", file=sys.stderr)
    print(
        "\nA release must be cut from a clean tree — the bump commit stages whole\n"
        "files, so these edits would land inside the release commit and inside the\n"
        "annotated tag that points at it. Commit or stash them first, then re-run:\n"
        "  git commit -am '...'   # or: git stash push -- <paths>\n"
        "Untracked files are ignored and never block a release.",
        file=sys.stderr,
    )
    return 1


def check_forbidden_paths(root: Path) -> int:
    """Refuse to bump if any tracked file lives under a forbidden path."""
    paths = list(UNIVERSAL_FORBIDDEN)
    extras = root / ".claude" / "forbidden-paths.txt"
    if extras.exists():
        for line in extras.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                paths.append(line)

    violations: list[tuple[str, int]] = []
    for p in paths:
        try:
            result = subprocess.run(
                ["git", "ls-files", p],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        files = [f for f in result.stdout.splitlines() if f]
        if files:
            violations.append((p, len(files)))

    if not violations:
        return 0

    print("ship: error: forbidden paths are tracked in this branch:", file=sys.stderr)
    for p, n in violations:
        print(f"  - {p} ({n} files)", file=sys.stderr)
    print(
        "\nThese paths are skill-generated artifacts that must not reach main.\n"
        "Strip them before shipping, e.g.:\n"
        f"  git rm -r {' '.join(p for p, _ in violations)}\n"
        "  git commit -m 'chore: strip skill artifacts before release'",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
