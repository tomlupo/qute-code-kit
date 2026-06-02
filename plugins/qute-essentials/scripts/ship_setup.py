"""/ship-setup — one-time project setup for /ship (Python v1).

Installs commitizen as a dev dependency, adds [tool.commitizen] to
pyproject.toml, creates CHANGELOG.md from the template if missing, and
drops a GitHub Actions release workflow if one doesn't exist.

Before seeding commitizen it reconciles the version across every source —
the [project] version, the latest `vX.Y.Z` git tag, and any stray
`__version__` literals — seeding from the highest and aligning the rest, so
the first `cz bump` can neither collide with an existing tag nor leave a
literal stale. Stray literals are also registered in `version_files`.

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
    pyproject_text = pyproject.read_text(encoding="utf-8")

    # 1. Install commitizen as a dev dependency (skip if already declared anywhere).
    if "commitizen" in pyproject_text:
        info("commitizen already declared in pyproject.toml — skipping install")
    elif shutil.which("uv"):
        try:
            run(["uv", "add", "--dev", "commitizen"])
            pyproject_text = pyproject.read_text(encoding="utf-8")
        except subprocess.CalledProcessError as exc:
            info(
                f"`uv add --dev commitizen` failed (exit {exc.returncode}); continuing"
            )
    else:
        info("`uv` not on PATH — skipping commitizen install. Add it manually.")

    # 2. Reconcile the version across all sources before seeding commitizen.
    #    Seeding cz from a stale [project] version while git tags are ahead is
    #    the classic trap: the first `cz bump` then collides with an existing
    #    tag or leapfrogs the real version. Seed from the highest of
    #    {pyproject version, latest vX.Y.Z tag, stray __version__ literals},
    #    then align every literal to it so cz's string-replacement bumps work.
    content = pyproject_text
    pyproject_version = _extract_version(content)
    tag_version = _latest_tag_version(root)
    literals = _find_version_literals(root)  # [(Path, current_value), ...]

    candidates = [
        v for v in (pyproject_version, tag_version, *(v for _, v in literals)) if v
    ]
    seed = _max_version(candidates) if candidates else "0.1.0"

    sources = {v for v in (pyproject_version, tag_version) if v}
    if len(sources) > 1:
        info(
            f"WARNING: version sources disagree — pyproject={pyproject_version!r}, "
            f"latest tag=v{tag_version}. Seeding commitizen at the highest ({seed}) "
            f"and aligning all version strings to it."
        )

    # Align the [project] version literal (the first `^version =` in the file).
    if pyproject_version and pyproject_version != seed:
        content = re.sub(
            r'(?m)^(version\s*=\s*")[^"]+(")', rf"\g<1>{seed}\g<2>", content, count=1
        )
        pyproject.write_text(content, encoding="utf-8")
        info(f"aligned pyproject [project] version {pyproject_version} -> {seed}")

    # Stray literals (e.g. src/pkg/__init__.py __version__) become both
    # version_files entries (so cz keeps them in lockstep) and are aligned now.
    extra_version_files = [
        f"{path.relative_to(root).as_posix()}:__version__" for path, _ in literals
    ]

    if "[tool.commitizen]" in content:
        info("pyproject.toml already has [tool.commitizen] — skipping block insert")
    else:
        snippet = (TEMPLATES / "pyproject-commitizen.toml").read_text(encoding="utf-8")
        snippet = snippet.replace("{{VERSION}}", seed)
        if extra_version_files:
            all_vf = ["pyproject.toml:version", *extra_version_files]
            rendered = (
                "version_files = [\n" + "".join(f'    "{vf}",\n' for vf in all_vf) + "]"
            )
            snippet = snippet.replace(
                'version_files = ["pyproject.toml:version"]', rendered
            )
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + snippet
        pyproject.write_text(content, encoding="utf-8")
        info(
            f"added [tool.commitizen] block (version {seed}, "
            f"{1 + len(extra_version_files)} version file(s) tracked)"
        )

    for path, cur in literals:
        if cur != seed:
            _set_version_literal(path, seed)
            info(
                f"aligned {path.relative_to(root).as_posix()} "
                f"__version__ {cur} -> {seed}"
            )

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


def _latest_tag_version(root: Path) -> str | None:
    """Highest `vX.Y.Z` git tag in the repo, as a bare `X.Y.Z` (or None)."""
    try:
        result = subprocess.run(
            ["git", "tag", "--list", "v[0-9]*"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None  # not a git repo, or git unavailable
    versions = [t[1:] for t in result.stdout.split() if re.match(r"^v\d+\.\d+\.\d+", t)]
    return _max_version(versions) if versions else None


_VERSION_LITERAL_RE = re.compile(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']')
_SCAN_GLOBS = (
    "src/*/__init__.py",
    "src/*/__about__.py",
    "src/*/_version.py",
    "*/__init__.py",
    "*/_version.py",
    "*/__about__.py",
)
_SCAN_EXCLUDE = (".venv", "site-packages", "node_modules", "build", "dist", ".git")


def _find_version_literals(root: Path) -> list[tuple[Path, str]]:
    """Hardcoded `__version__ = "X.Y.Z"` literals outside pyproject.toml.

    These are the second source of truth that silently drifts when only
    `pyproject.toml:version` is bumped. A `__version__` derived from
    `importlib.metadata` is a call, not a string literal, so it is correctly
    skipped (the regex only matches a quoted value).
    """
    found: dict[Path, str] = {}
    for pattern in _SCAN_GLOBS:
        for path in root.glob(pattern):
            if any(part in _SCAN_EXCLUDE for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            m = _VERSION_LITERAL_RE.search(text)
            if m:
                found[path] = m.group(1)
    return sorted(found.items())


def _set_version_literal(path: Path, new_version: str) -> None:
    """Rewrite the first `__version__ = "..."` literal in `path` to new_version."""
    text = path.read_text(encoding="utf-8")
    text = _VERSION_LITERAL_RE.sub(
        lambda m: m.group(0).replace(m.group(1), new_version), text, count=1
    )
    path.write_text(text, encoding="utf-8")


def _semver_key(version: str) -> tuple[int, int, int]:
    """Sort key for an `X.Y.Z` string; pre-release/build metadata is ignored."""
    core = re.split(r"[-+]", version, maxsplit=1)[0]
    parts = (core.split(".") + ["0", "0", "0"])[:3]
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


def _max_version(versions: list[str]) -> str:
    return max(versions, key=_semver_key)


if __name__ == "__main__":
    sys.exit(main())
