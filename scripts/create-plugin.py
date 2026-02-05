#!/usr/bin/env python3
"""
Create a new plugin from template.

Usage:
    python scripts/create.py <plugin-name>
"""

import json
import os
import shutil
import sys
from pathlib import Path

MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
TEMPLATES_DIR = MARKETPLACE_ROOT / "templates" / "plugin-template"
PLUGINS_DIR = MARKETPLACE_ROOT / "plugins"


def create_plugin(name: str):
    """Create a new plugin from the template."""
    # Validate name
    if not name:
        print("❌ Error: Plugin name is required")
        sys.exit(1)

    # Normalize name (lowercase, hyphens)
    normalized_name = name.lower().replace("_", "-").replace(" ", "-")
    plugin_dir = PLUGINS_DIR / normalized_name

    if plugin_dir.exists():
        print(f"❌ Error: Plugin '{normalized_name}' already exists at {plugin_dir}")
        sys.exit(1)

    if not TEMPLATES_DIR.exists():
        print(f"❌ Error: Template not found at {TEMPLATES_DIR}")
        sys.exit(1)

    print(f"🔨 Creating plugin: {normalized_name}")

    # Copy template
    shutil.copytree(TEMPLATES_DIR, plugin_dir)

    # Update plugin.json with the plugin name
    manifest_path = plugin_dir / "plugin.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

        manifest["name"] = normalized_name
        manifest["description"] = f"{normalized_name} plugin for Claude Code"

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    # Update README
    readme_path = plugin_dir / "README.md"
    if readme_path.exists():
        content = readme_path.read_text()
        content = content.replace("{{PLUGIN_NAME}}", normalized_name)
        readme_path.write_text(content)

    # Update example command
    example_cmd = plugin_dir / "commands" / "example.md"
    if example_cmd.exists():
        content = example_cmd.read_text()
        content = content.replace("{{PLUGIN_NAME}}", normalized_name)
        example_cmd.write_text(content)

    print(f"✅ Created plugin at: {plugin_dir}")
    print(f"\n📝 Next steps:")
    print(f"   1. Edit {plugin_dir}/plugin.json to configure commands/skills")
    print(f"   2. Add your commands to {plugin_dir}/commands/")
    print(f"   3. Run: python scripts/build.py")
    print(f"   4. Restart Claude to use /{normalized_name}:* commands")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/create.py <plugin-name>")
        print("\nExample:")
        print("  python scripts/create.py my-awesome-plugin")
        sys.exit(1)

    plugin_name = sys.argv[1]
    create_plugin(plugin_name)


if __name__ == "__main__":
    main()
