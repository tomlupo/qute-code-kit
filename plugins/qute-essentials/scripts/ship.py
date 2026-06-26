"""/ship — universal release command.

One entry point, two modes (detected automatically):

* **Plugin mode** — `.claude-plugin/marketplace.json` at repo root.
  Delegates to `scripts/release-plugin.sh <plugin> <bump>`.
* **Python mode** — `pyproject.toml` at repo root (and no marketplace).
  Refuses to bump if any tracked file lives under a forbidden path,
  runs first-time-setup idempotently, then `cz bump --yes --changelog`.

Webapps (`package.json`) use `gstack ship` instead.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
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

    # 2. First-time setup — idempotent; safe to call every time.
    from ship_setup import setup_python

    if rc := setup_python(root, pyproject):
        return rc

    # 3. Build the cz command.
    if shutil.which("uv"):
        cmd = ["uv", "run", "cz", "bump", "--yes", "--changelog"]
    elif shutil.which("cz"):
        cmd = ["cz", "bump", "--yes", "--changelog"]
    else:
        return fail("neither `uv` nor `cz` found on PATH. Install commitizen or uv.")

    if parsed.dry_run:
        cmd.append("--dry-run")
    if parsed.increment:
        cmd += ["--increment", parsed.increment.upper()]
    if parsed.version:
        cmd.append(parsed.version)

    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        return fail(f"commitizen bump failed with exit code {exc.returncode}")

    if parsed.dry_run:
        info("dry run complete; no commit or tag created.")
        return 0

    # 4. Wipe TASKS.md::Completed sections — canonical now in CHANGELOG.md.
    wipe_tasks_completed(root, pyproject)

    info(
        "done. Review the bump commit and tag, then `git push --follow-tags` when ready."
    )
    return 0


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
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    cz_block = re.search(r"\[tool\.commitizen\][^\[]*", content, re.DOTALL)
    if not cz_block:
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', cz_block.group(0), re.MULTILINE)
    return m.group(1) if m else None


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
