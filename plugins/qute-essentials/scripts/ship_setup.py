"""/ship-setup — one-time project setup for /ship (Python v1).

Installs commitizen as a dev dependency, adds [tool.commitizen] to
pyproject.toml, creates CHANGELOG.md from the template if missing, and
drops a GitHub Actions release workflow if one doesn't exist.

Idempotent: safe to re-run. Skips any step whose artifact is already in place.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN_DIR / "templates"


def info(msg: str) -> None:
    print(f"ship-setup: {msg}")


def fail(msg: str) -> int:
    print(f"ship-setup: error: {msg}", file=sys.stderr)
    return 1


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    root = Path.cwd()
    pyproject = root / "pyproject.toml"

    if not pyproject.exists():
        return fail("no pyproject.toml in the current directory (Python only in v1)")

    return setup_python(root, pyproject)


def setup_python(root: Path, pyproject: Path) -> int:
    # 1. Install commitizen as a dev dependency
    if shutil.which("uv"):
        try:
            run(["uv", "add", "--dev", "commitizen"])
        except subprocess.CalledProcessError as exc:
            info(
                f"`uv add --dev commitizen` failed (exit {exc.returncode}); continuing"
            )
    else:
        info("`uv` not on PATH — skipping commitizen install. Add it manually.")

    # 2. Merge [tool.commitizen] block if missing
    content = pyproject.read_text(encoding="utf-8")
    if "[tool.commitizen]" in content:
        info("pyproject.toml already has [tool.commitizen] — skipping")
    else:
        snippet = (TEMPLATES / "pyproject-commitizen.toml").read_text(encoding="utf-8")
        version = _extract_version(content) or "0.1.0"
        snippet = snippet.replace("{{VERSION}}", version)
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + snippet
        pyproject.write_text(content, encoding="utf-8")
        info(f"added [tool.commitizen] block (version {version})")

    # 3. Create CHANGELOG.md if missing
    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        info("CHANGELOG.md already exists — skipping")
    else:
        template = (TEMPLATES / "CHANGELOG.template.md").read_text(encoding="utf-8")
        changelog.write_text(template, encoding="utf-8")
        info("created CHANGELOG.md from template")

    # 4. Create GitHub Actions release workflow if missing
    workflow = root / ".github" / "workflows" / "release.yml"
    if workflow.exists():
        info(".github/workflows/release.yml already exists — skipping")
    else:
        workflow.parent.mkdir(parents=True, exist_ok=True)
        template = (TEMPLATES / "github-workflow-release.yml").read_text(
            encoding="utf-8"
        )
        workflow.write_text(template, encoding="utf-8")
        info("created .github/workflows/release.yml")

    info(
        "setup complete. Commit these changes, then run /ship on main to cut releases."
    )
    return 0


def _extract_version(pyproject_content: str) -> str | None:
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject_content)
    return match.group(1) if match else None


if __name__ == "__main__":
    sys.exit(main())
