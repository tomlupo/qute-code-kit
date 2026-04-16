#!/usr/bin/env python3
"""
SessionStart hook: daily version check for qute-essentials plugin.
Outputs JSON with update notice if a newer version is available.

Cross-platform replacement for check-update.sh.
"""

import json
import subprocess
import time
from pathlib import Path


def main():
    state_dir = Path.home() / ".gstack"
    state_dir.mkdir(parents=True, exist_ok=True)
    cache_file = state_dir / "qute-essentials-update-check"
    marketplace_dir = (
        Path.home() / ".claude" / "plugins" / "marketplaces" / "qute-marketplace"
    )

    # Only check once per day
    if cache_file.exists():
        try:
            last_check = int(cache_file.read_text().strip())
            if time.time() - last_check < 86400:
                print("{}")
                return
        except (ValueError, OSError):
            pass

    # Record check time
    cache_file.write_text(str(int(time.time())))

    # Get local version from cached plugin.json
    local_version = ""
    cache_dir = (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "qute-marketplace"
        / "qute-essentials"
    )
    if cache_dir.exists():
        for version_dir in sorted(cache_dir.iterdir(), reverse=True):
            pj = version_dir / "plugin.json"
            if pj.exists():
                try:
                    local_version = json.loads(pj.read_text())["version"]
                    break
                except (json.JSONDecodeError, KeyError):
                    continue

    if not local_version:
        print("{}")
        return

    # Fetch latest from git
    remote_version = ""
    if marketplace_dir.exists():
        try:
            subprocess.run(
                ["git", "fetch", "origin", "main", "--quiet"],
                cwd=str(marketplace_dir),
                capture_output=True,
                timeout=10,
            )
            result = subprocess.run(
                ["git", "show", "origin/main:.claude-plugin/marketplace.json"],
                cwd=str(marketplace_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for p in data.get("plugins", []):
                    if p["name"] == "qute-essentials":
                        remote_version = p["version"]
                        break
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass

    if not remote_version:
        print("{}")
        return

    if local_version != remote_version:
        msg = (
            f"qute-essentials update available: {local_version} → {remote_version}. "
            f"Run: claude plugin marketplace update && claude plugin update qute-essentials@qute-marketplace"
        )
        print(json.dumps({"additionalContext": msg}))
    else:
        print("{}")


if __name__ == "__main__":
    main()
