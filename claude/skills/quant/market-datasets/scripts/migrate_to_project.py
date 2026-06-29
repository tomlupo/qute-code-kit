#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click>=8.0",
# ]
# ///
"""
Migrate a data source fetcher from skill to production project.

This script copies fetcher scripts to your project directory,
making them available for production use.

Usage:
    uv run migrate_to_project.py stooq --target src/data_sources/
    uv run migrate_to_project.py yahoo --target src/market_data/ --include-utils
    uv run migrate_to_project.py all --target src/fetchers/ --include-utils --include-env
    uv run migrate_to_project.py --list  # List available sources
"""

import shutil
import sys
from pathlib import Path
from typing import List, Dict

# Script directory
SKILL_DIR = Path(__file__).parent

# Source to file mapping
SOURCE_MAP: Dict[str, List[str]] = {
    'stooq': ['fetch_stooq.py'],
    'stooq-corporate': ['fetch_stooq_corporate_actions.py', 'fetch_stooq_corporate_actions_firecrawl.py'],
    'yahoo': ['fetch_yahoo.py'],
    'yahoo-direct': ['fetch_yahoo_direct.py'],
    'nbp': ['fetch_nbp.py'],
    'fred': ['fetch_fred.py'],
    'tiingo': ['fetch_tiingo.py'],
    'ccxt': ['fetch_ccxt.py'],
    'pandas-datareader': ['fetch_pandas_datareader.py'],
    'registry': ['ticker_registry.py'],
    'unified': ['fetch_unified.py'],
    'all': [
        'fetch_unified.py',
        'fetch_stooq.py',
        'fetch_yahoo.py',
        'fetch_yahoo_direct.py',
        'fetch_nbp.py',
        'fetch_fred.py',
        'fetch_tiingo.py',
        'fetch_ccxt.py',
        'fetch_pandas_datareader.py',
        'ticker_registry.py',
        'utils.py',
    ],
}

# API keys required by each source
ENV_KEYS: Dict[str, List[str]] = {
    'tiingo': ['TIINGO_API_KEY'],
    'fred': ['FRED_API_KEY'],
    'stooq-corporate': ['FIRECRAWL_API_KEY'],
    'all': ['TIINGO_API_KEY', 'FRED_API_KEY', 'FIRECRAWL_API_KEY'],
}


def list_sources():
    """Print available sources."""
    print("Available sources:\n")
    for source, files in SOURCE_MAP.items():
        print(f"  {source:20} -> {', '.join(files)}")
    print("\nUsage: uv run migrate_to_project.py <source> --target <dir>")


def migrate(source: str, target: str, include_utils: bool, include_env: bool):
    """Migrate data source fetcher to project directory."""
    if source not in SOURCE_MAP:
        print(f"Error: Unknown source '{source}'")
        print("Use --list to see available sources.")
        sys.exit(1)

    target_dir = Path(target)
    target_dir.mkdir(parents=True, exist_ok=True)

    files = SOURCE_MAP[source].copy()

    # Add utils.py if requested and not already included
    if include_utils and 'utils.py' not in files:
        files.append('utils.py')

    print(f"Migrating '{source}' to {target_dir}/\n")

    copied_files = []
    for filename in files:
        src = SKILL_DIR / filename
        dst = target_dir / filename

        if not src.exists():
            print(f"  Warning: {src} not found, skipping")
            continue

        print(f"  Copying {filename}")
        shutil.copy2(src, dst)
        copied_files.append(filename)

    # Create .env.example if requested
    if include_env:
        env_keys = ENV_KEYS.get(source, [])
        if env_keys:
            env_template = target_dir / '.env.example'
            env_content = "# API Keys for market data fetchers\n"
            env_content += "# Copy to .env and fill in your keys\n\n"
            for key in env_keys:
                env_content += f"{key}=\n"
            env_template.write_text(env_content)
            print(f"  Created .env.example")
            copied_files.append('.env.example')

    # Also copy data files for registry
    if source in ['registry', 'all', 'unified']:
        data_dir = SKILL_DIR.parent / 'data'
        if data_dir.exists():
            target_data_dir = target_dir / 'data'
            target_data_dir.mkdir(exist_ok=True)
            for data_file in data_dir.glob('*.csv'):
                dst = target_data_dir / data_file.name
                shutil.copy2(data_file, dst)
                print(f"  Copying data/{data_file.name}")

    print(f"\n{len(copied_files)} file(s) migrated to {target_dir}/")
    print(f"\nTo use, run:")
    print(f"  uv run {target_dir}/{copied_files[0]} --help")

    if include_utils:
        print(f"\nNote: utils.py included. Scripts can import shared utilities.")


def main():
    """Main entry point."""
    # Simple argument parsing without click (for minimal dependencies)
    args = sys.argv[1:]

    if not args or '--help' in args or '-h' in args:
        print(__doc__)
        sys.exit(0)

    if '--list' in args:
        list_sources()
        sys.exit(0)

    # Parse arguments
    source = None
    target = None
    include_utils = '--include-utils' in args
    include_env = '--include-env' in args

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ['--include-utils', '--include-env']:
            i += 1
            continue
        elif arg in ['--target', '-t']:
            if i + 1 < len(args):
                target = args[i + 1]
                i += 2
            else:
                print("Error: --target requires a value")
                sys.exit(1)
        elif not source and not arg.startswith('-'):
            source = arg
            i += 1
        else:
            i += 1

    if not source:
        print("Error: Source name required")
        print("Use --list to see available sources.")
        sys.exit(1)

    if not target:
        print("Error: --target <directory> required")
        sys.exit(1)

    migrate(source, target, include_utils, include_env)


if __name__ == "__main__":
    main()
