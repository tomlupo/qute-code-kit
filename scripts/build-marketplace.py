#!/usr/bin/env python3
"""Regenerate `.claude-plugin/marketplace.json` from plugin manifests.

Single source of truth: `plugins/<name>/.claude-plugin/plugin.json`.
This script reads each plugin manifest and emits the marketplace catalog.
It does NOT write to plugin manifests — that direction is hand-edited.

Run after editing a plugin manifest, or let `scripts/release-plugin.sh`
call it during a release.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
PLUGINS_DIR = MARKETPLACE_ROOT / "plugins"
MARKETPLACE_JSON = MARKETPLACE_ROOT / ".claude-plugin" / "marketplace.json"

MARKETPLACE_NAME = "qute-marketplace"
MARKETPLACE_DESCRIPTION = "Personal Claude Code plugin marketplace"
MARKETPLACE_OWNER = {"name": "twilc", "email": "twilc@users.noreply.github.com"}


def load_plugin_manifest(plugin_dir: Path) -> dict[str, Any] | None:
    """Read the canonical manifest at `.claude-plugin/plugin.json`."""
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return None
    with open(manifest_path) as f:
        return json.load(f)


def normalize_author(author: Any) -> dict[str, str]:
    if isinstance(author, str):
        return {"name": author}
    if isinstance(author, dict):
        return author
    return {"name": MARKETPLACE_OWNER["name"]}


def build_entry(plugin_dir: Path) -> dict[str, Any] | None:
    manifest = load_plugin_manifest(plugin_dir)
    if not manifest:
        print(f"  skip {plugin_dir.name}: no .claude-plugin/plugin.json")
        return None

    name = manifest.get("name", plugin_dir.name)
    entry = {
        "name": name,
        "description": manifest.get("description", f"{name} plugin"),
        "version": manifest["version"],
        "author": normalize_author(manifest.get("author")),
        "source": f"./plugins/{plugin_dir.name}",
        "category": manifest.get("category", "utility"),
    }
    print(f"  + {name} v{entry['version']}")
    return entry


def build_marketplace() -> int:
    if not PLUGINS_DIR.is_dir():
        print(f"error: {PLUGINS_DIR} not found", file=sys.stderr)
        return 1

    entries: list[dict[str, Any]] = []
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue
        if (entry := build_entry(plugin_dir)) is not None:
            entries.append(entry)

    marketplace = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": MARKETPLACE_NAME,
        "description": MARKETPLACE_DESCRIPTION,
        "owner": MARKETPLACE_OWNER,
        "plugins": entries,
    }

    MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(MARKETPLACE_JSON, "w") as f:
        json.dump(marketplace, f, indent=2)
        f.write("\n")

    print(
        f"\nwrote {MARKETPLACE_JSON.relative_to(MARKETPLACE_ROOT)} ({len(entries)} plugin(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(build_marketplace())
