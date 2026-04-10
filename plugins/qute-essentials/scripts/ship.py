"""/ship — universal release command (Python v1).

Detects the project type from the current working directory and runs the
appropriate bump tool. Bumps version, updates CHANGELOG.md, and creates a
git tag based on Conventional Commits since the last release.

v1 supports Python (via commitizen). Webapps use `gstack ship` instead.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


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
    content = pyproject.read_text(encoding="utf-8")
    if "[tool.commitizen]" not in content:
        return fail(
            "pyproject.toml has no [tool.commitizen] section. "
            "Run /ship-setup first to configure this project."
        )

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

    info(
        "done. Review the bump commit and tag, then `git push --follow-tags` when ready."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
