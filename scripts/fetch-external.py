#!/usr/bin/env python3
"""
Fetch external plugins from GitHub.

Usage:
    python scripts/fetch-external.py                    # Fetch all from manifest
    python scripts/fetch-external.py --force            # Re-clone all (removes existing)
    python scripts/fetch-external.py github:user/repo   # Fetch single plugin
    python scripts/fetch-external.py github:user/repo --branch main
"""

import json
import subprocess
import sys
from pathlib import Path

MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
EXTERNAL_DIR = MARKETPLACE_ROOT / "external"
MANIFEST_FILE = MARKETPLACE_ROOT / "external-plugins.json"


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


def fetch_plugin(source: str, branch: str = "main", force: bool = False, exit_on_exists: bool = True) -> bool:
    """Clone a plugin from GitHub into external/.

    Returns True if plugin was cloned, False if skipped.
    """
    try:
        user, repo = parse_github_source(source)
    except ValueError as e:
        print(f"❌ Error: {e}")
        if exit_on_exists:
            sys.exit(1)
        return False

    target_dir = EXTERNAL_DIR / repo

    if target_dir.exists():
        if force:
            import shutil
            print(f"🗑️  Removing existing {repo}...")
            shutil.rmtree(target_dir)
        elif exit_on_exists:
            print(f"❌ Error: Plugin '{repo}' already exists at {target_dir}")
            print(f"   Use 'python scripts/update-externals.py {repo}' to update it")
            print(f"   Or use --force to re-clone")
            sys.exit(1)
        else:
            print(f"  ⏭️  {repo}: Already exists, skipping")
            return False

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
        print(f"  ❌ Error cloning {repo}:")
        print(f"     {e.stderr.strip()}")
        if exit_on_exists:
            sys.exit(1)
        return False

    # Verify plugin.json exists
    if not (target_dir / "plugin.json").exists():
        print(f"⚠ Warning: No plugin.json found in {repo}")
        print(f"   This may not be a valid Claude Code plugin")

    print(f"  ✅ Cloned: {repo}")
    return True


def load_manifest() -> list[dict]:
    """Load plugins from external-plugins.json manifest."""
    if not MANIFEST_FILE.exists():
        print(f"❌ Error: Manifest file not found: {MANIFEST_FILE}")
        sys.exit(1)

    with open(MANIFEST_FILE) as f:
        data = json.load(f)

    return data.get("plugins", [])


def fetch_all_from_manifest(force: bool = False):
    """Fetch all plugins listed in the manifest."""
    plugins = load_manifest()

    if not plugins:
        print("📂 No plugins listed in manifest")
        return

    print(f"🔄 Fetching {len(plugins)} external plugin(s) from manifest...\n")

    # Ensure external directory exists
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    cloned = 0
    skipped = 0

    for plugin in plugins:
        repo = plugin.get("repo", "")
        branch = plugin.get("branch", "main")

        if fetch_plugin(repo, branch, force=force, exit_on_exists=False):
            cloned += 1
        else:
            skipped += 1

    print(f"\n✅ Cloned: {cloned}, Skipped: {skipped}")

    if cloned > 0:
        print("\n📝 Next steps:")
        print("   1. Run: python scripts/build-marketplace.py")
        print("   2. Restart Claude to use the new plugins")


def main():
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    # No positional args = fetch from manifest
    if not args:
        fetch_all_from_manifest(force=force)
        return

    # Single plugin source provided
    source = args[0]
    branch = "main"

    # Parse optional --branch argument
    if "--branch" in sys.argv:
        idx = sys.argv.index("--branch")
        if idx + 1 < len(sys.argv):
            branch = sys.argv[idx + 1]

    if fetch_plugin(source, branch, force=force):
        print("\n📝 Next steps:")
        print("   1. Run: python scripts/build-marketplace.py")
        print("   2. Restart Claude to use the new plugin")


if __name__ == "__main__":
    main()
