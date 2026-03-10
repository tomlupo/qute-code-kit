#!/usr/bin/env python3
"""
Core notification module for ntfy integration.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional


DEFAULT_CONFIG: dict[str, Any] = {
    "server": "https://ntfy.sh",
    "topic": "claude-notifications",
    "priority": "default",
    "tags": ["robot"],
    "events": {
        "task_complete": True,
        "build_success": True,
        "build_failure": True,
        "test_complete": True,
        "commit": False,
        "error": True,
        "session_end": False,
    },
    "filters": {
        "min_duration_seconds": 30,
        "commands": ["npm", "python", "pytest", "make", "cargo"],
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dictionaries recursively.

    Args:
        base: Base configuration dictionary.
        override: Override configuration dictionary.

    Returns:
        A merged dictionary where override values win.
    """
    result = dict(base)
    for key, value in override.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            result[key] = _deep_merge(base_value, value)
        else:
            result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON config file safely.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed dictionary, or empty dict if unavailable/invalid.
    """
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data: Any = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_config() -> dict[str, Any]:
    """Load notification configuration with project-level overrides.

    Lookup order (later sources override earlier ones):
    1) Built-in defaults
    2) Plugin config: <plugin-root>/config/ntfy.json
    3) Project config: <cwd>/.claude/config/ntfy.json
    """
    plugin_config_path = Path(__file__).parent.parent / "config" / "ntfy.json"
    project_config_path = Path.cwd() / ".claude" / "config" / "ntfy.json"

    config = dict(DEFAULT_CONFIG)
    config = _deep_merge(config, _load_json(plugin_config_path))
    config = _deep_merge(config, _load_json(project_config_path))
    return config


def send_notification(
    message: str,
    title: str = "Claude",
    priority: str = "default",
    tags: Optional[list[str]] = None
) -> bool:
    """
    Send a notification via ntfy.

    Args:
        message: Notification message
        title: Notification title
        priority: Priority level (min, low, default, high, urgent)
        tags: List of emoji tags

    Returns:
        True if successful, False otherwise
    """
    config = get_config()

    server = config.get("server", "https://ntfy.sh")
    topic = config.get("topic", "claude-notifications")

    if tags is None:
        tags = config.get("tags", ["robot"])

    url = f"{server}/{topic}"

    # Build curl command
    cmd = [
        "curl",
        "-s",
        "-o", "/dev/null",
        "-w", "%{http_code}",
        "-d", message,
        "-H", f"Title: {title}",
        "-H", f"Priority: {priority}",
        "-H", f"Tags: {','.join(tags)}",
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        status_code = result.stdout.strip()
        return status_code == "200"
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def notify_task_complete(command: str, duration: float, success: bool) -> bool:
    """Send notification for task completion."""
    config = get_config()
    events = config.get("events", {})

    # Check if we should notify
    if success and not events.get("task_complete", True):
        return False
    if not success and not events.get("error", True):
        return False

    # Check duration filter
    min_duration = config.get("filters", {}).get("min_duration_seconds", 30)
    if duration < min_duration:
        return False

    # Build message
    status = "✅" if success else "❌"
    title = "Task Complete" if success else "Task Failed"
    message = f"{status} {command}\nDuration: {duration:.1f}s"
    priority = "default" if success else "high"
    tags = ["white_check_mark", "robot"] if success else ["x", "warning"]

    return send_notification(message, title, priority, tags)


def notify_build(success: bool, output: str = "") -> bool:
    """Send notification for build completion."""
    config = get_config()
    events = config.get("events", {})

    event_key = "build_success" if success else "build_failure"
    if not events.get(event_key, True):
        return False

    status = "✅" if success else "❌"
    title = "Build Success" if success else "Build Failed"
    message = f"{status} Build {'completed' if success else 'failed'}"
    if output and not success:
        # Include first line of error
        first_line = output.split('\n')[0][:100]
        message += f"\n{first_line}"

    priority = "default" if success else "high"
    tags = ["hammer", "white_check_mark"] if success else ["hammer", "x"]

    return send_notification(message, title, priority, tags)


if __name__ == "__main__":
    # Test notification
    success = send_notification(
        "🧪 Test notification from Claude Code",
        title="Claude Test",
        tags=["robot", "test_tube"]
    )
    print(f"Test notification: {'✅ sent' if success else '❌ failed'}")
