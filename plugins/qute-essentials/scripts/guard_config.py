"""Shared guard config resolution for qute-essentials.

Every guard hook resolves its on/off state through here so the semantics
live in one place. Two things matter:

1. **User overrides survive plugin updates.** The shipped ``config/guards.json``
   lives inside the versioned plugin cache, so a plugin update overwrites it.
   User toggles are therefore written to a stable path — ``~/.claude/qute-guards.json``
   — and overlaid on top of the shipped defaults per guard. The shipped file is
   defaults only; the user file is the source of truth for what the user chose.

2. **Fail modes differ by guard class.** When config is missing or unreadable,
   guards that send data off-box (lakera → Lakera API, langfuse → Langfuse)
   fail CLOSED (default off) — a corrupt config must never silently start
   shipping tool output to a third party. Deterministic local guards
   (secrets, destructive, audit) fail OPEN (default on) so a corrupt config
   never silently drops a safety net that costs nothing to keep.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

USER_CONFIG = Path.home() / ".claude" / "qute-guards.json"

# Guards that reach the network / send data off-box. These default OFF and
# must be deliberately opted into; they also fail closed on config errors.
NETWORK_GUARDS = frozenset({"lakera", "langfuse"})


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def shipped_config_path() -> Path | None:
    """Locate the plugin's shipped guards.json (defaults only)."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        candidate = Path(plugin_root) / "config" / "guards.json"
        if candidate.exists():
            return candidate
    # scripts/ -> ../config/guards.json
    candidate = Path(__file__).resolve().parent.parent / "config" / "guards.json"
    if candidate.exists():
        return candidate
    return None


def load_guards() -> dict:
    """Return merged guard config: shipped defaults overlaid by the user file."""
    merged: dict = {}
    shipped = shipped_config_path()
    if shipped:
        merged.update(_read_json(shipped))
    for name, cfg in _read_json(USER_CONFIG).items():
        if isinstance(cfg, dict):
            merged.setdefault(name, {}).update(cfg)
        else:
            merged[name] = cfg
    return merged


def default_enabled(name: str) -> bool:
    """Fail mode for a guard when config is absent: network guards off, others on."""
    return name not in NETWORK_GUARDS


def guard_enabled(name: str) -> bool:
    """Whether guard ``name`` is enabled, honouring env overrides and fail modes.

    Precedence: CLAUDE_SKIP_GUARDS=1 (all off) > CLAUDE_GUARD_<NAME>=0/1 >
    merged config (user file over shipped defaults) > per-class fail mode.
    """
    if os.environ.get("CLAUDE_SKIP_GUARDS") == "1":
        return False
    override = os.environ.get(f"CLAUDE_GUARD_{name.upper()}")
    if override == "0":
        return False
    if override == "1":
        return True
    default = default_enabled(name)
    guard_cfg = load_guards().get(name)
    if not isinstance(guard_cfg, dict):
        return default
    return bool(guard_cfg.get("enabled", default))
