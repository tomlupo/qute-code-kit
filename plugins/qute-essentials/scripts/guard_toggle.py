#!/usr/bin/env python3
"""
Helper script for the `guard` skill. Toggles Lakera Guard and/or Langfuse
on/off, and reports current status.

Replaces the inline ``python -c`` one-liner that used to live in the skill
body (which violated the bash-discipline "no inline python" rule and also
hardcoded the plugin version in the config path).

Usage:
    guard_toggle.py status                    # show current status table
    guard_toggle.py lakera on                 # enable Lakera Guard
    guard_toggle.py lakera off                # disable Lakera Guard
    guard_toggle.py langfuse on               # enable Langfuse tracing
    guard_toggle.py langfuse off              # disable Langfuse tracing
    guard_toggle.py all on                    # enable both
    guard_toggle.py all off                   # disable both

Config location resolution (first hit wins):
    1. ${CLAUDE_PLUGIN_ROOT}/config/guards.json (preferred, version-agnostic)
    2. <script-dir>/../config/guards.json (relative to this script)
    3. ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/config/guards.json (fallback, any version)

Exit codes:
    0 — success
    1 — usage error or config missing
    2 — unknown guard name
"""

import json
import os
import sys
from pathlib import Path

GUARDS = {
    "lakera": {
        "display": "Lakera Guard",
        "env_key": "LAKERA_API_KEY",
        "description": "Prompt injection screening",
    },
    "langfuse": {
        "display": "Langfuse",
        "env_key": "LANGFUSE_SECRET_KEY",
        "description": "Tracing / evaluation",
    },
}


def find_config() -> Path | None:
    """Resolve the guards.json path. Returns None if nothing found."""
    # 1. Plugin root env var (preferred — set by the Claude Code hook runtime)
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidate = Path(plugin_root) / "config" / "guards.json"
        if candidate.exists():
            return candidate

    # 2. Relative to this script (if the plugin is installed and we're running from it)
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir.parent / "config" / "guards.json"
    if candidate.exists():
        return candidate

    # 3. Fallback: search the user's plugin cache for any version of qute-essentials
    cache_root = (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "qute-marketplace"
        / "qute-essentials"
    )
    if cache_root.exists():
        # Pick the highest-version directory that has a guards.json
        versions = sorted(
            (p for p in cache_root.iterdir() if p.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        )
        for vdir in versions:
            candidate = vdir / "config" / "guards.json"
            if candidate.exists():
                return candidate

    return None


def load_config(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: could not read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def save_config(path: Path, config: dict) -> None:
    try:
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"ERROR: could not write {path}: {e}", file=sys.stderr)
        sys.exit(1)


def is_configured(env_key: str) -> bool:
    """Return True if the given environment variable is set to a non-empty value."""
    return bool(os.environ.get(env_key, "").strip())


def print_status(config: dict, config_path: Path) -> None:
    """Print a status table of all guards."""
    print(f"Guards config: {config_path}")
    print()
    print(f"{'Guard':<15} {'Enabled':<10} {'API key':<15} {'Description'}")
    print(f"{'-' * 15} {'-' * 10} {'-' * 15} {'-' * 30}")
    for key, meta in GUARDS.items():
        guard_cfg = config.get(key, {})
        enabled = guard_cfg.get("enabled", False)
        enabled_display = "yes" if enabled else "no"
        key_ok = is_configured(meta["env_key"])
        key_display = "set" if key_ok else f"missing ({meta['env_key']})"
        print(
            f"{meta['display']:<15} {enabled_display:<10} {key_display:<15} {meta['description']}"
        )


def set_guard(config: dict, guard: str, enabled: bool) -> None:
    """Mutate config in place to enable/disable a named guard."""
    if guard not in GUARDS:
        print(
            f"ERROR: unknown guard '{guard}'. Valid: {', '.join(GUARDS)}",
            file=sys.stderr,
        )
        sys.exit(2)
    if guard not in config:
        config[guard] = {}
    config[guard]["enabled"] = enabled


def main() -> None:
    args = sys.argv[1:]
    if not args:
        args = ["status"]

    config_path = find_config()
    if config_path is None:
        print(
            "ERROR: could not locate guards.json. Set CLAUDE_PLUGIN_ROOT or "
            "install the qute-essentials plugin.",
            file=sys.stderr,
        )
        sys.exit(1)

    config = load_config(config_path)

    cmd = args[0].lower()

    if cmd == "status":
        print_status(config, config_path)
        return

    # Toggle commands: <guard> <on|off>
    if len(args) != 2 or args[1].lower() not in ("on", "off"):
        print(
            "USAGE: guard_toggle.py [status | <lakera|langfuse|all> <on|off>]",
            file=sys.stderr,
        )
        sys.exit(1)

    target = args[0].lower()
    enabled = args[1].lower() == "on"

    if target == "all":
        for guard in GUARDS:
            set_guard(config, guard, enabled)
    else:
        set_guard(config, target, enabled)

    save_config(config_path, config)
    print(f"Updated {config_path}")
    print()
    print_status(config, config_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
