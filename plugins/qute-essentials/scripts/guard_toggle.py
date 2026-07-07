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

CONFIG RESOLUTION

    Effective state is the shipped defaults (config/guards.json inside the
    plugin) overlaid by a stable USER override file:

        ~/.claude/qute-guards.json

    Toggles are WRITTEN to the user file, which survives plugin updates —
    the shipped file lives in the versioned plugin cache and is overwritten
    on every update, so it holds defaults only. Status shows the merged
    (effective) state.

GOTCHAS

  - API-key guards (lakera, langfuse) are EFFECTIVELY OFF when their
    key env var is missing, regardless of 'enabled' value. The status
    table shows 'missing' in the API key column for this case.
  - Guard state is written to ~/.claude/qute-guards.json and is
    session-persistent — changes take effect immediately on the next
    tool call and survive across sessions AND plugin updates. There is
    no auto-reset.
  - lakera and langfuse are OFF by default and must be opted into
    (`/guard lakera on`) — they send data off-box (Lakera API /
    Langfuse). On a config error they fail CLOSED (stay off).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_config import USER_CONFIG, load_guards  # noqa: E402

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


def load_user_config() -> dict:
    """Read the user override file (may not exist yet)."""
    if not USER_CONFIG.exists():
        return {}
    try:
        data = json.loads(USER_CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: could not read {USER_CONFIG}: {e}", file=sys.stderr)
        sys.exit(1)


def save_user_config(config: dict) -> None:
    try:
        USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        USER_CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"ERROR: could not write {USER_CONFIG}: {e}", file=sys.stderr)
        sys.exit(1)


def is_configured(env_key: str) -> bool:
    """Return True if the given environment variable is set to a non-empty value."""
    return bool(os.environ.get(env_key, "").strip())


def print_status(config: dict) -> None:
    """Print a status table of all guards (effective/merged state)."""
    user_state = (
        "present" if USER_CONFIG.exists() else "not created yet (shipped defaults)"
    )
    print(f"User overrides: {USER_CONFIG} ({user_state})")
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

    cmd = args[0].lower()

    if cmd == "status":
        # Show effective (shipped defaults overlaid by user overrides).
        print_status(load_guards())
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

    # Toggles are persisted to the user override file so they survive plugin
    # updates; only the touched guards are written.
    user_config = load_user_config()

    if target == "all":
        for guard in GUARDS:
            set_guard(user_config, guard, enabled)
    else:
        set_guard(user_config, target, enabled)

    save_user_config(user_config)
    print(f"Updated {USER_CONFIG}")
    print()
    print_status(load_guards())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
