#!/usr/bin/env python3
"""
config_toggle.py — view or update qute-essentials notification config.

The `/config` skill dispatches here; this script is the deterministic
kernel that holds the ntfy.json schema, key-set semantics, and config-
file resolution.

USAGE
    config_toggle.py [-h|--help]
    config_toggle.py [show]                     # pretty-print current config
    config_toggle.py set <key>=<value>          # update top-level scalar
    config_toggle.py enable <event>             # set events.<event> = true
    config_toggle.py disable <event>            # set events.<event> = false
    config_toggle.py filter <key>=<value>       # update filters.<key>

SETTABLE TOP-LEVEL KEYS (set <key>=<value>)
    server      ntfy server URL          (default: https://ntfy.sh)
    topic       notification topic       (default: <hostname>-<user>-claude)
    priority    default priority         (one of: min, low, default, high, urgent)
    tags        comma-separated tags     (default: robot)

NOTIFICATION EVENTS (enable / disable <event>)
    task_complete    a long-running task finishes
    build_success    a build completes successfully
    build_failure    a build fails
    test_complete    tests finish running
    commit           a git commit is created
    error            an error occurs
    session_end      the Claude session ends

FILTERS (filter <key>=<value>)
    min_duration_seconds   notify only if the command ran ≥ N seconds (int)
    commands               comma-separated allowlist of monitored cmds
                           (npm, python, pytest, make, cargo, …); empty = match all

CONFIG RESOLUTION (first hit wins)
    1. ${CLAUDE_PLUGIN_ROOT}/config/ntfy.json
    2. <script-dir>/../config/ntfy.json
    3. ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/config/ntfy.json

GOTCHAS

  - ntfy.sh is public — anyone who knows your topic string can subscribe.
    Use a hard-to-guess topic, or self-host ntfy for sensitive projects.
  - ntfy.sh free tier is 250 messages/day — set `min_duration_seconds`
    high (≥ 60) for projects with frequent build cycles, or self-host.
  - Changing `topic` only affects future notifications. Past ones stay
    on the old topic; subscribers there stop receiving updates.
  - Each event flag is consulted by exactly one caller in notify.py
    (`task_complete`, `build_success`/`build_failure` via build helpers).
    Most ntfy sends in the qute-essentials hooks are unconditional and
    do NOT consult this map — flipping a flag may not silence what you
    expect. Inspect `scripts/notify.py` if a flag has no apparent
    effect.
  - Guards (lakera, langfuse, secrets, audit, destructive, malware) are
    NOT managed here. Use /guard for those.

EXIT CODES
    0 — success
    1 — usage error or config missing
    2 — unknown event / key
"""

import json
import os
import platform
import sys
from pathlib import Path

# Ensure unicode (emoji, ✓/✗) prints cleanly on Windows cp1250/cp1252 consoles.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VALID_PRIORITY = {"min", "low", "default", "high", "urgent"}
VALID_TOP_KEYS = {"server", "topic", "priority", "tags"}
VALID_EVENTS = {
    "task_complete",
    "build_success",
    "build_failure",
    "test_complete",
    "commit",
    "error",
    "session_end",
}
VALID_FILTER_KEYS = {"min_duration_seconds", "commands"}


def find_config() -> Path | None:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidate = Path(plugin_root) / "config" / "ntfy.json"
        if candidate.exists():
            return candidate

    script_dir = Path(__file__).resolve().parent
    candidate = script_dir.parent / "config" / "ntfy.json"
    if candidate.exists():
        return candidate

    cache_root = (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "qute-marketplace"
        / "qute-essentials"
    )
    if cache_root.exists():
        versions = sorted(
            (p for p in cache_root.iterdir() if p.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        )
        for vdir in versions:
            candidate = vdir / "config" / "ntfy.json"
            if candidate.exists():
                return candidate

    return None


def default_topic() -> str:
    hostname = platform.node().split(".")[0].lower()
    user = os.environ.get("USER") or os.environ.get("USERNAME", "unknown")
    return f"{hostname}-{user}-claude".lower()


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


def print_config(config: dict, path: Path) -> None:
    server = config.get("server", "https://ntfy.sh")
    topic = config.get("topic") or f"(unset — falls back to {default_topic()})"
    priority = config.get("priority", "default")
    tags = config.get("tags", ["robot"])
    events = config.get("events", {})
    filters = config.get("filters", {})

    print(f"Notify config: {path}")
    print()
    print("Notifications (ntfy.sh)")
    print(f"  Server:   {server}")
    print(f"  Topic:    {topic}")
    print(f"  Priority: {priority}")
    print(f"  Tags:     {', '.join(tags) if isinstance(tags, list) else tags}")
    print()
    print("Events")
    for ev in sorted(VALID_EVENTS):
        on = events.get(ev, False)
        mark = "✓" if on else "·"
        print(f"  [{mark}] {ev}")
    print()
    print("Filters")
    min_dur = filters.get("min_duration_seconds", 30)
    cmds = filters.get("commands", [])
    print(f"  min_duration_seconds: {min_dur}")
    cmd_display = ", ".join(cmds) if cmds else "(empty — match all)"
    print(f"  commands:             {cmd_display}")


def parse_kv(arg: str) -> tuple[str, str]:
    if "=" not in arg:
        print(f"ERROR: expected key=value, got '{arg}'", file=sys.stderr)
        sys.exit(1)
    k, v = arg.split("=", 1)
    return k.strip(), v.strip()


def cmd_set(config: dict, kv: str) -> None:
    key, value = parse_kv(kv)
    if key not in VALID_TOP_KEYS:
        print(
            f"ERROR: unknown key '{key}'. Valid: {', '.join(sorted(VALID_TOP_KEYS))}",
            file=sys.stderr,
        )
        sys.exit(2)
    if key == "priority" and value not in VALID_PRIORITY:
        print(
            f"ERROR: priority must be one of {sorted(VALID_PRIORITY)}, got '{value}'",
            file=sys.stderr,
        )
        sys.exit(2)
    if key == "tags":
        config[key] = [t.strip() for t in value.split(",") if t.strip()]
    else:
        config[key] = value


def cmd_event(config: dict, event: str, enabled: bool) -> None:
    if event not in VALID_EVENTS:
        print(
            f"ERROR: unknown event '{event}'. Valid: {', '.join(sorted(VALID_EVENTS))}",
            file=sys.stderr,
        )
        sys.exit(2)
    config.setdefault("events", {})[event] = enabled


def cmd_filter(config: dict, kv: str) -> None:
    key, value = parse_kv(kv)
    if key not in VALID_FILTER_KEYS:
        print(
            f"ERROR: unknown filter key '{key}'. Valid: {', '.join(sorted(VALID_FILTER_KEYS))}",
            file=sys.stderr,
        )
        sys.exit(2)
    filters = config.setdefault("filters", {})
    if key == "min_duration_seconds":
        try:
            filters[key] = int(value)
        except ValueError:
            print(
                f"ERROR: min_duration_seconds must be an integer, got '{value}'",
                file=sys.stderr,
            )
            sys.exit(1)
    elif key == "commands":
        filters[key] = [c.strip() for c in value.split(",") if c.strip()]


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    if not args:
        args = ["show"]

    config_path = find_config()
    if config_path is None:
        print(
            "ERROR: could not locate ntfy.json. Set CLAUDE_PLUGIN_ROOT or "
            "install the qute-essentials plugin.",
            file=sys.stderr,
        )
        sys.exit(1)

    config = load_config(config_path)
    cmd = args[0].lower()

    if cmd == "show":
        print_config(config, config_path)
        return

    if cmd == "set":
        if len(args) != 2:
            print("USAGE: config_toggle.py set <key>=<value>", file=sys.stderr)
            sys.exit(1)
        cmd_set(config, args[1])
    elif cmd == "enable":
        if len(args) != 2:
            print("USAGE: config_toggle.py enable <event>", file=sys.stderr)
            sys.exit(1)
        cmd_event(config, args[1], True)
    elif cmd == "disable":
        if len(args) != 2:
            print("USAGE: config_toggle.py disable <event>", file=sys.stderr)
            sys.exit(1)
        cmd_event(config, args[1], False)
    elif cmd == "filter":
        if len(args) != 2:
            print("USAGE: config_toggle.py filter <key>=<value>", file=sys.stderr)
            sys.exit(1)
        cmd_filter(config, args[1])
    else:
        print(f"ERROR: unknown command '{cmd}'. Run with --help.", file=sys.stderr)
        sys.exit(1)

    save_config(config_path, config)
    print(f"Updated {config_path}")
    print()
    print_config(config, config_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
