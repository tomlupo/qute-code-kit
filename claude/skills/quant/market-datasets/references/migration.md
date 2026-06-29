# Project Migration

After prototyping with this skill, migrate fetchers to your production project.

## Migrate a Data Source

```bash
# List available sources
uv run scripts/migrate_to_project.py --list

# Migrate Stooq fetcher to your project
uv run scripts/migrate_to_project.py stooq --target src/data_sources/

# Migrate with utilities and .env template
uv run scripts/migrate_to_project.py yahoo --target src/market_data/ --include-utils --include-env

# Migrate all fetchers
uv run scripts/migrate_to_project.py all --target src/fetchers/ --include-utils --include-env
```

## What Migration Produces

```
src/data_sources/           # Your target directory
├── fetch_stooq.py          # Self-contained with PEP 723 dependencies
├── utils.py                # Shared utilities (if --include-utils)
└── .env.example            # API key template (if --include-env)
```

## After Migration

The migrated scripts work standalone:
```bash
uv run src/data_sources/fetch_stooq.py PKO 2024-01-01 2024-12-31
```

Or import in your code:
```python
sys.path.insert(0, 'src/data_sources')
from fetch_stooq import fetch_stooq
df = fetch_stooq('pko', '2024-01-01')
```
