"""/ship — universal release command (Python v1).

Cuts a release for the current Python project:

1. Refuses to bump if the working tree has any tracked forbidden path
   (skill artifacts that must not reach main).
2. If `[tool.commitizen]` is missing from pyproject.toml, runs the
   one-time setup automatically (idempotent — safe to re-run).
3. Bumps version + updates CHANGELOG.md + creates an annotated `vX.Y.Z`
   git tag based on Conventional Commits since the last release.

v1 supports Python (via commitizen). Webapps use `gstack ship` instead.
"""

from __future__ import annotations

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


def info(msg: str) -> None:
    print(f"ship: {msg}")


def fail(msg: str) -> int:
    print(f"ship: error: {msg}", file=sys.stderr)
    return 1


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    root = Path.cwd()
    pyproject = root / "pyproject.toml"

    if pyproject.exists():
        return ship_python(root, pyproject)

    if (root / "package.json").exists():
        return fail(
            "package.json detected — webapps are handled by `gstack ship`, "
            "not `/ship` (Python only in v1)."
        )

    if (root / "Cargo.toml").exists():
        return fail("Cargo.toml detected — Rust is not yet supported.")

    return fail(
        "no supported project type detected in the current directory. "
        "/ship v1 requires a pyproject.toml."
    )


def ship_python(root: Path, pyproject: Path) -> int:
    # 1. Forbidden-paths check — refuse to bump if skill artifacts are tracked.
    if rc := check_forbidden_paths(root):
        return rc

    # 2. Auto-setup commitizen if missing (idempotent).
    content = pyproject.read_text(encoding="utf-8")
    if "[tool.commitizen]" not in content:
        info("no [tool.commitizen] block — running first-time setup")
        from ship_setup import setup_python

        if rc := setup_python(root, pyproject):
            return rc
        info("setup complete; proceeding with bump")

    # 3. Bump.
    if shutil.which("uv"):
        cmd = ["uv", "run", "cz", "bump", "--yes", "--changelog"]
    elif shutil.which("cz"):
        cmd = ["cz", "bump", "--yes", "--changelog"]
    else:
        return fail("neither `uv` nor `cz` found on PATH. Install commitizen or uv.")

    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        return fail(f"commitizen bump failed with exit code {exc.returncode}")

    info("done. Review the bump commit and tag, then `git push --follow-tags` when ready.")
    return 0


def check_forbidden_paths(root: Path) -> int:
    """Refuse to bump if any tracked file lives under a forbidden path.

    Universal list is hardcoded; project may add extras in
    `.claude/forbidden-paths.txt` (one path per line, blank lines and
    `#` comments allowed).
    """
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
            continue  # not a git repo, or git unavailable — skip silently
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
