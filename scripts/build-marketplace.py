#!/usr/bin/env python3
"""
Build script for qute-marketplace.

Generates:
1. .claude-plugin/marketplace.json - Marketplace manifest listing all plugins
2. plugins/*/.claude-plugin/plugin.json - Individual plugin manifests
3. plugins/*/hooks/hooks.json - Converted hook format (if needed)

This allows the marketplace to be registered with:
    claude plugin marketplace add github:twilc/qute-marketplace

And individual plugins installed with:
    claude plugin install <plugin-name>@qute-marketplace
"""

import json
import shutil
from pathlib import Path
from typing import Any

# Get marketplace root directory (parent of scripts/)
MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
PLUGINS_DIR = MARKETPLACE_ROOT / "plugins"
EXTERNAL_DIR = MARKETPLACE_ROOT / "external"
MARKETPLACE_JSON = MARKETPLACE_ROOT / ".claude-plugin" / "marketplace.json"

# Marketplace metadata
MARKETPLACE_NAME = "qute-marketplace"
MARKETPLACE_DESCRIPTION = "Personal Claude Code plugin marketplace"
MARKETPLACE_OWNER = {
    "name": "twilc",
    "email": "twilc@users.noreply.github.com"
}


def load_old_manifest(plugin_dir: Path) -> dict[str, Any] | None:
    """Load plugin's plugin.json manifest.

    Checks plugin root first, then falls back to .claude-plugin/plugin.json
    (used by some external marketplace repos).
    """
    manifest_path = plugin_dir / "plugin.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)

    # Fallback: check .claude-plugin/plugin.json
    fallback_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if fallback_path.exists():
        with open(fallback_path) as f:
            return json.load(f)

    return None


def convert_hooks_format(old_hooks_path: Path, new_hooks_path: Path, plugin_name: str) -> bool:
    """
    Convert old hook format to official Claude Code format.

    Old format (from current qute-marketplace):
    {
      "hooks": [
        {
          "matcher": "UserPromptSubmit",
          "hooks": [{ "type": "command", "command": "..." }]
        }
      ]
    }

    New format (official):
    {
      "description": "...",
      "hooks": {
        "UserPromptSubmit": [
          {
            "hooks": [{ "type": "command", "command": "..." }]
          }
        ]
      }
    }
    """
    if not old_hooks_path.exists():
        return False

    with open(old_hooks_path) as f:
        old_data = json.load(f)

    # Check if already in new format (hooks is a dict, not a list)
    if isinstance(old_data.get("hooks"), dict):
        # Already in new format
        if old_hooks_path.resolve() != new_hooks_path.resolve():
            # Only copy if different files
            new_hooks_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(old_hooks_path, new_hooks_path)
        return True

    # Convert from old format to new format
    new_hooks: dict[str, list] = {}

    for hook_entry in old_data.get("hooks", []):
        matcher = hook_entry.get("matcher")
        if not matcher:
            continue

        inner_hooks = hook_entry.get("hooks", [])
        if not inner_hooks and "command" in hook_entry:
            # Flat format - convert to nested
            inner_hooks = [{"type": "command", "command": hook_entry["command"]}]

        if matcher not in new_hooks:
            new_hooks[matcher] = []

        new_hooks[matcher].append({"hooks": inner_hooks})

    new_data = {
        "description": f"Hooks for {plugin_name} plugin",
        "hooks": new_hooks
    }

    new_hooks_path.parent.mkdir(parents=True, exist_ok=True)
    with open(new_hooks_path, "w") as f:
        json.dump(new_data, f, indent=2)

    return True


def create_plugin_manifest(plugin_dir: Path, old_manifest: dict) -> dict:
    """Create .claude-plugin/plugin.json for a plugin."""
    claude_plugin_dir = plugin_dir / ".claude-plugin"
    claude_plugin_dir.mkdir(exist_ok=True)

    # Get author info
    author = old_manifest.get("author", MARKETPLACE_OWNER["name"])
    if isinstance(author, str):
        author = {"name": author}

    plugin_manifest = {
        "name": old_manifest.get("name", plugin_dir.name),
        "description": old_manifest.get("description", f"{plugin_dir.name} plugin"),
        "author": author
    }

    manifest_path = claude_plugin_dir / "plugin.json"
    with open(manifest_path, "w") as f:
        json.dump(plugin_manifest, f, indent=2)

    return plugin_manifest


def process_plugin(plugin_dir: Path, prefix: str) -> dict | None:
    """
    Process a plugin directory:
    1. Read old manifest
    2. Create new .claude-plugin/plugin.json
    3. Convert hooks if needed
    4. Return plugin entry for marketplace.json
    """
    print(f"  📦 Processing {plugin_dir.name}...")

    old_manifest = load_old_manifest(plugin_dir)
    if not old_manifest:
        print(f"     ⚠ No plugin.json found, skipping")
        return None

    # Create new plugin manifest
    plugin_manifest = create_plugin_manifest(plugin_dir, old_manifest)
    print(f"     ✓ Created .claude-plugin/plugin.json")

    # Convert hooks if present
    hooks_file = old_manifest.get("hooks")
    if hooks_file:
        old_hooks_path = plugin_dir / hooks_file
        new_hooks_path = plugin_dir / "hooks" / "hooks.json"
        if convert_hooks_format(old_hooks_path, new_hooks_path, plugin_dir.name):
            print(f"     ✓ Converted hooks format")

    # Validate rules if present
    for rule_path in old_manifest.get("rules", []):
        full_path = plugin_dir / rule_path
        if full_path.exists():
            print(f"     ✓ OK: Rule: {rule_path}")
        else:
            print(f"     ⚠ WARNING: Rule not found: {rule_path}")

    # Build marketplace entry
    marketplace_entry = {
        "name": plugin_manifest["name"],
        "description": plugin_manifest["description"],
        "version": old_manifest.get("version", "1.0.0"),
        "author": plugin_manifest["author"],
        "source": f"./{prefix}/{plugin_dir.name}",
        "category": old_manifest.get("category", "utility")
    }

    return marketplace_entry


def scan_plugins(base_dir: Path, prefix: str) -> list[dict]:
    """Scan a directory for plugins and process each one.

    For external/ directories, detects marketplace repos (those with
    .claude-plugin/marketplace.json) and scans their plugins/ subdirectory
    for individual plugins instead of treating the whole repo as one plugin.
    """
    plugins = []

    if not base_dir.exists():
        return plugins

    for plugin_dir in sorted(base_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        if plugin_dir.name.startswith("."):
            continue

        # Check if this is an external marketplace repo
        marketplace_manifest = plugin_dir / ".claude-plugin" / "marketplace.json"
        if marketplace_manifest.exists():
            print(f"  🏪 Detected marketplace repo: {plugin_dir.name}")
            sub_plugins_dir = plugin_dir / "plugins"
            if sub_plugins_dir.is_dir():
                # Multi-plugin marketplace: scan its plugins/ subdir
                for sub_dir in sorted(sub_plugins_dir.iterdir()):
                    if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                        continue
                    sub_prefix = f"{prefix}/{plugin_dir.name}/plugins"
                    entry = process_plugin(sub_dir, sub_prefix)
                    if entry:
                        plugins.append(entry)
            else:
                # Single-plugin marketplace: synthesize from marketplace.json
                with open(marketplace_manifest) as f:
                    mkt_data = json.load(f)
                mkt_plugins = mkt_data.get("plugins", [])
                if mkt_plugins:
                    # Use first plugin entry, fix source path
                    entry_data = mkt_plugins[0].copy()
                    entry_data["source"] = f"./{prefix}/{plugin_dir.name}"
                    plugins.append(entry_data)
                    print(f"  📦 Synthesized from marketplace.json: {entry_data.get('name')}")
            continue

        entry = process_plugin(plugin_dir, prefix)
        if entry:
            plugins.append(entry)

    return plugins


def build_marketplace():
    """Build the marketplace manifest."""
    print("🔨 Building qute-marketplace...\n")

    all_plugins = []

    # Scan plugins/ directory (local plugins only)
    print("📂 Scanning plugins/")
    plugins = scan_plugins(PLUGINS_DIR, "plugins")
    all_plugins.extend(plugins)

    # Note: external/ plugins are NOT included in this marketplace.
    # They come from their own marketplaces (every-marketplace, etc.).

    # Build marketplace.json
    marketplace = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": MARKETPLACE_NAME,
        "description": MARKETPLACE_DESCRIPTION,
        "owner": MARKETPLACE_OWNER,
        "plugins": all_plugins
    }

    # Write marketplace.json
    MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(MARKETPLACE_JSON, "w") as f:
        json.dump(marketplace, f, indent=2)
    print(f"\n✅ Written: {MARKETPLACE_JSON}")

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Plugins: {len(all_plugins)}")
    for p in all_plugins:
        print(f"     - {p['name']}")

    print(f"\n🎉 Build complete!")
    print(f"\nTo register this marketplace:")
    print(f"   claude plugin marketplace add {MARKETPLACE_ROOT}")
    print(f"\nTo install a plugin:")
    print(f"   claude plugin install <plugin-name>@{MARKETPLACE_NAME}")


if __name__ == "__main__":
    build_marketplace()
