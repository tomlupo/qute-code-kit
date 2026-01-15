#!/usr/bin/env python3
"""
Fetch a plugin from GitHub.

Usage:
    python scripts/fetch.py github:username/repo-name
    python scripts/fetch.py github:username/repo-name --branch main
"""

import subprocess
import sys
from pathlib import Path

MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
EXTERNAL_DIR = MARKETPLACE_ROOT / "external"


def parse_github_source(source: str) -> tuple[str, str]:
    """Parse github:user/repo format and return (user, repo)."""
    if source.startswith("github:"):
        source = source[7:]  # Remove "github:" prefix

    if "/" not in source:
        raise ValueError(f"Invalid format. Expected 'github:user/repo' or 'user/repo', got: {source}")

    parts = source.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid format. Expected 'user/repo', got: {source}")

    return parts[0], parts[1]


def fetch_plugin(source: str, branch: str = "main"):
    """Clone a plugin from GitHub into external/."""
    try:
        user, repo = parse_github_source(source)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    target_dir = EXTERNAL_DIR / repo

    if target_dir.exists():
        print(f"❌ Error: Plugin '{repo}' already exists at {target_dir}")
        print(f"   Use 'python scripts/update.py {repo}' to update it")
        sys.exit(1)

    # Ensure external directory exists
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    github_url = f"https://github.com/{user}/{repo}.git"
    print(f"🔄 Cloning {github_url}...")
    print(f"   Branch: {branch}")
    print(f"   Target: {target_dir}")

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, github_url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Error cloning repository:")
        print(e.stderr)
        sys.exit(1)

    # Verify plugin.json exists
    if not (target_dir / "plugin.json").exists():
        print(f"⚠ Warning: No plugin.json found in {repo}")
        print(f"   This may not be a valid Claude Code plugin")

    print(f"✅ Cloned: {repo}")
    print(f"\n📝 Next steps:")
    print(f"   1. Run: python scripts/build.py")
    print(f"   2. Restart Claude to use the new plugin")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch.py github:username/repo-name [--branch BRANCH]")
        print("\nExamples:")
        print("  python scripts/fetch.py github:anthropics/example-plugin")
        print("  python scripts/fetch.py github:user/repo --branch develop")
        sys.exit(1)

    source = sys.argv[1]
    branch = "main"

    # Parse optional --branch argument
    if "--branch" in sys.argv:
        idx = sys.argv.index("--branch")
        if idx + 1 < len(sys.argv):
            branch = sys.argv[idx + 1]

    fetch_plugin(source, branch)


if __name__ == "__main__":
    main()
