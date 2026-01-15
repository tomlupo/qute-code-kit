#!/usr/bin/env python3
"""
Update external plugins from GitHub.

Usage:
    python scripts/update.py           # Update all external plugins
    python scripts/update.py <name>    # Update specific plugin
"""

import subprocess
import sys
from pathlib import Path

MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
EXTERNAL_DIR = MARKETPLACE_ROOT / "external"


def update_plugin(plugin_dir: Path) -> bool:
    """Update a single plugin using git pull."""
    if not plugin_dir.is_dir():
        return False

    git_dir = plugin_dir / ".git"
    if not git_dir.exists():
        print(f"  ⚠ {plugin_dir.name}: Not a git repository, skipping")
        return False

    print(f"  🔄 Updating {plugin_dir.name}...")

    try:
        result = subprocess.run(
            ["git", "-C", str(plugin_dir), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            check=True
        )
        if "Already up to date" in result.stdout:
            print(f"     ✓ Already up to date")
        else:
            print(f"     ✓ Updated")
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"     ❌ Failed to update: {e.stderr.strip()}")
        return False


def update_all():
    """Update all external plugins."""
    if not EXTERNAL_DIR.exists():
        print("📂 No external plugins directory found")
        return

    plugins = [d for d in EXTERNAL_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not plugins:
        print("📂 No external plugins to update")
        return

    print(f"🔄 Updating {len(plugins)} external plugin(s)...\n")

    updated = 0
    for plugin_dir in sorted(plugins):
        if update_plugin(plugin_dir):
            updated += 1

    print(f"\n✅ Updated {updated}/{len(plugins)} plugins")
    if updated > 0:
        print("\n📝 Next steps:")
        print("   1. Run: python scripts/build.py")
        print("   2. Restart Claude to apply changes")


def update_one(name: str):
    """Update a specific external plugin."""
    plugin_dir = EXTERNAL_DIR / name

    if not plugin_dir.exists():
        print(f"❌ Error: Plugin '{name}' not found in external/")
        print(f"   Available plugins: {', '.join(d.name for d in EXTERNAL_DIR.iterdir() if d.is_dir())}")
        sys.exit(1)

    print(f"🔄 Updating {name}...\n")
    if update_plugin(plugin_dir):
        print("\n📝 Next steps:")
        print("   1. Run: python scripts/build.py")
        print("   2. Restart Claude to apply changes")


def main():
    if len(sys.argv) > 1:
        update_one(sys.argv[1])
    else:
        update_all()


if __name__ == "__main__":
    main()
