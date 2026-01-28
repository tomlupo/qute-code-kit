# Garmin Agent-Efficient Skill

A Claude Code skill for token-efficient Garmin health data access.

Instead of raw API responses (~2000 tokens), this skill provides pre-computed summaries (~50 tokens) from a local SQLite database.

## Features

- **Token-efficient**: Brief summaries use ~50 tokens vs ~2000 for raw API
- **Offline queries**: Data cached in SQLite, no API calls during conversation
- **Tiered output**: Brief → Normal → Detailed based on need
- **Trend analysis**: Compare metrics to 7-day rolling baselines
- **Staleness detection**: Warns when data is >18 hours old

## Installation

```bash
cd garmin-skill
./install.sh
```

The installer will:
1. Create a Python virtual environment
2. Install dependencies (garminconnect)
3. Initialize the SQLite database
4. Test Garmin authentication
5. Run an initial sync (7 days of data)
6. Provide cron setup instructions

## Requirements

- Python 3.10+
- Garmin Connect account
- Credentials via one of:
  - Existing tokens in `~/.garminconnect/` (from previous garminconnect usage)
  - Environment variables: `GARMIN_USERNAME`, `GARMIN_PASSWORD`

## Usage

Activate the virtual environment first:
```bash
cd garmin-skill
source .venv/bin/activate
```

### Daily Summary
```bash
# Brief (~50 tokens)
python scripts/garmin_query.py summary

# Normal detail (~150 tokens)
python scripts/garmin_query.py -v summary

# Full JSON
python scripts/garmin_query.py -vv summary

# Specific date
python scripts/garmin_query.py summary 2026-01-20
```

### Trends
```bash
python scripts/garmin_query.py trends hrv 7    # HRV over 7 days
python scripts/garmin_query.py trends sleep 14 # Sleep over 14 days
python scripts/garmin_query.py trends stress 7 # Stress over 7 days
python scripts/garmin_query.py trends rhr 30   # Resting HR over 30 days
```

### Compare to Baseline
```bash
python scripts/garmin_query.py compare         # Today vs 7-day avg
python scripts/garmin_query.py compare 2026-01-20  # Specific date
```

### Activities
```bash
python scripts/garmin_query.py activities 5    # Recent 5 activities
```

### Manual Sync
```bash
python scripts/garmin_query.py sync            # On-demand sync
python scripts/garmin_sync.py --backfill 30    # Backfill 30 days
```

## Cron Setup

For automatic daily sync at 6 AM:

```bash
crontab -e
```

Add:
```
0 6 * * * cd /path/to/garmin-skill && .venv/bin/python scripts/garmin_sync.py >> ~/.garmin-skill/sync.log 2>&1
```

## How It Works

```
┌─────────────────────────────────────────────┐
│  garmin_sync.py (runs daily via cron)       │
│  - Pulls from Garmin Connect API            │
│  - Extracts normalized metrics              │
│  - Computes 7-day rolling baselines         │
│  - Generates brief/normal summaries         │
│  - Stores everything in SQLite              │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  ~/.garmin-skill/garmin.db (SQLite)         │
│  - daily_health: metrics for each day       │
│  - summaries: pre-computed brief/normal     │
│  - baselines: 7-day rolling averages        │
│  - activities: recent workout summaries     │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  garmin_query.py (called by agent)          │
│  - Reads from SQLite (no API calls)         │
│  - Returns tiered output based on -v flag   │
│  - Detects staleness (>18h = warning)       │
│  - Exit code 0=fresh, 2=stale, 1=error      │
└─────────────────────────────────────────────┘
```

## Data Stored

| Table | Purpose |
|-------|---------|
| `daily_health` | Sleep, HRV, stress, body battery, training readiness, steps, resting HR |
| `summaries` | Pre-computed brief (~50 tokens) and normal (~150 tokens) summaries |
| `baselines` | 7-day rolling averages for trend comparison |
| `activities` | Recent activities with one-liner summaries |
| `sync_meta` | Last sync timestamp for staleness detection |

## Troubleshooting

### "Database not found"
Run `./install.sh` to set up the skill.

### "Authentication failed"
Set environment variables:
```bash
export GARMIN_USERNAME="your@email.com"
export GARMIN_PASSWORD="your_password"
```
Or ensure you have valid tokens in `~/.garminconnect/`.

### "Another sync is already running"
Wait for the current sync to finish, or remove the lock file:
```bash
rm ~/.garmin-skill/sync.lock
```

### Data is stale
Run a manual sync:
```bash
python scripts/garmin_query.py sync
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, data fresh |
| 1 | Error (invalid args, DB missing, auth failed) |
| 2 | Success but data stale (>18h old) |
