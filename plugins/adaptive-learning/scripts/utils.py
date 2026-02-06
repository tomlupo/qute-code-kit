#!/usr/bin/env python3
"""Shared helpers for adaptive-learning plugin."""

import json
import os
from pathlib import Path


STORAGE_DIR = Path.home() / ".claude" / "adaptive-learning"
PLUGIN_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = PLUGIN_DIR / "config" / "defaults.json"


def get_storage_dir():
    """Return storage directory, creating subdirs if needed."""
    for sub in ("instincts/personal", "instincts/inherited", "exports"):
        (STORAGE_DIR / sub).mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR


def get_config():
    """Load defaults, merge user overrides from storage dir."""
    try:
        defaults = json.loads(DEFAULTS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        defaults = {}

    user_config = STORAGE_DIR / "config.json"
    if user_config.exists():
        try:
            overrides = json.loads(user_config.read_text())
            _deep_merge(defaults, overrides)
        except (OSError, json.JSONDecodeError):
            pass

    return defaults


def _deep_merge(base, override):
    """Merge override dict into base dict in place."""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


def truncate_str(s, max_len=5000):
    """Truncate string with suffix if needed."""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "... [truncated]"


def rotate_if_needed(path, max_mb=10, archive_count=3):
    """Rotate file if it exceeds max_mb. Numbered archives (.1, .2, .3)."""
    if not path.exists():
        return
    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError:
        return

    if size_mb < max_mb:
        return

    # Shift existing archives
    for i in range(archive_count, 1, -1):
        older = Path(f"{path}.{i}")
        newer = Path(f"{path}.{i - 1}")
        if newer.exists():
            newer.rename(older)

    # Current -> .1
    path.rename(Path(f"{path}.1"))


def parse_frontmatter(text):
    """Parse YAML-like frontmatter between --- markers. Returns (metadata_dict, body)."""
    if not text.startswith("---"):
        return {}, text

    lines = text.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    meta = {}
    for line in lines[1:end_idx]:
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # Try to parse numbers and booleans
        if val.lower() in ("true", "false"):
            val = val.lower() == "true"
        else:
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
        meta[key] = val

    body = "\n".join(lines[end_idx + 1:])
    return meta, body
