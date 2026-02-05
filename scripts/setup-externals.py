#!/usr/bin/env python3
"""
Set up external plugins from the manifest.

Usage:
    python scripts/setup-externals.py           # Fetch missing plugins
    python scripts/setup-externals.py --force   # Re-clone all plugins
    python scripts/setup-externals.py --update  # Update existing plugins
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def main():
    if "--update" in sys.argv:
        # Delegate to update-externals.py
        subprocess.run([sys.executable, SCRIPTS_DIR / "update-externals.py"])
    else:
        # Delegate to fetch-external.py (manifest mode)
        args = [sys.executable, SCRIPTS_DIR / "fetch-external.py"]
        if "--force" in sys.argv:
            args.append("--force")
        subprocess.run(args)


if __name__ == "__main__":
    main()
