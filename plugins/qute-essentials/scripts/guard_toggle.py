#!/usr/bin/env python3
"""
guard_toggle.py — view or toggle qute-essentials security guards.

The `/guard` skill dispatches here; this script is the deterministic kernel
that holds all the guard semantics, gotchas, and config-file handling.

USAGE
    guard_toggle.py [-h|--help]
    guard_toggle.py [status]                    # show current status table
    guard_toggle.py <name> <on|off>             # toggle one guard
    guard_toggle.py all <on|off>                # toggle all guards

Where <name> is one of: lakera, langfuse, secrets, audit, destructive.

GUARDS

    lakera        Prompt-injection screening on tool outputs (WebFetch,
                  WebSearch, MCP responses). Requires LAKERA_API_KEY.
                  Effectively off if the key is missing, even when
                  'enabled: true'.

    langfuse      Tracing / evaluation. PostToolUse spans grouped by
                  Claude session ID. Requires LANGFUSE_SECRET_KEY +
                  LANGFUSE_PUBLIC_KEY. Costs ~2.7s per tool call —
                  default OFF for interactive; turn ON for headless /
                  agentic-cron runs (CLAUDE_GUARD_LANGFUSE=1).

    secrets       Block Write/Edit operations that leak API keys,
                  tokens, or target credential files (.env, *.pem,
                  id_rsa, database.ini). May false-positive on test
                  fixtures with fake key patterns — disable per-write
                  with CLAUDE_GUARD_SECRETS=0 in the failing call only.

    audit         Auto-run pip-audit after package installs (uv add /
                  sync / lock, pip install). Reports CVEs against the
                  OSV database. Informational, non-blocking.

    destructive   Block dangerous shell commands (rm -rf, git reset
                  --hard, DROP TABLE, kubectl delete, force-push, etc).
                  May false-positive on legitimate cleanup commands
                  like 'rm -rf dist/' or 'git reset --hard' on a clean
                  feature branch — disable temporarily, then re-enable.

CONFIG RESOLUTION (first hit wins)

    1. ${CLAUDE_PLUGIN_ROOT}/config/guards.json
    2. <script-dir>/../config/guards.json
    3. ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/config/guards.json

GOTCHAS

  - API-key guards (lakera, langfuse) are EFFECTIVELY OFF when their
    key env var is missing, regardless of 'enabled' value. The status
    table shows 'missing' in the API key column for this case.
  - Guard state in guards.json is session-persistent — changes take
    effect immediately on the next tool call and survive across
    sessions. There is no auto-reset.
  - CLAUDE_SKIP_GUARDS=1 bypasses ALL guards regardless of guards.json.
    Never set this in a shell profile or .env — only inline for a
    specific command that needs it.
  - Per-guard env overrides: CLAUDE_GUARD_<NAME>=0 disables one guard
    for the current process (e.g. CLAUDE_GUARD_LANGFUSE=0). Use this
    for cron sessions that legitimately need different guard policies
    than your interactive shell.

EXIT CODES

    0 — success
    1 — usage error or config missing
    2 — unknown guard name
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

GUARDS = {
    "lakera": {
        "display": "Lakera Guard",
        "env_key": "LAKERA_GUARD_API_KEY",
        "description": "Prompt injection screening",
    },
    "langfuse": {
        "display": "Langfuse",
        "env_key": "LANGFUSE_SECRET_KEY",
        "description": "Tracing / evaluation",
    },
    "secrets": {
        "display": "Secrets Guard",
        "description": "Block writes that leak API keys, tokens, or credential files",
    },
    "audit": {
        "display": "Audit Guard",
        "description": "Auto-run pip-audit after package installs (informational)",
    },
    "destructive": {
        "display": "Destructive Guard",
        "description": "Block destructive commands (git reset --hard, rm -rf, DROP TABLE)",
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
    print(f"{'Guard':<18} {'Enabled':<10} {'API key':<15} {'Description'}")
    print(f"{'-' * 18} {'-' * 10} {'-' * 15} {'-' * 30}")
    for key, meta in GUARDS.items():
        guard_cfg = config.get(key, {})
        enabled = guard_cfg.get("enabled", False)
        enabled_display = "yes" if enabled else "no"
        env_key = meta.get("env_key")
        if env_key:
            key_display = "set" if is_configured(env_key) else f"missing ({env_key})"
        else:
            key_display = "n/a"
        print(
            f"{meta['display']:<18} {enabled_display:<10} {key_display:<15} {meta['description']}"
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

    if args and args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

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
            "USAGE: guard_toggle.py [status | <lakera|langfuse|secrets|audit|destructive|all> <on|off>]",
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
