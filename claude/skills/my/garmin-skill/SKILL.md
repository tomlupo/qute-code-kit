---
name: garmin-health
description: Token-efficient Garmin health data access via pre-computed SQLite summaries. Use for "health stats", "HRV", "sleep", "Garmin", "stress", "recovery", "training readiness", "body battery", or when preparing health briefings.
version: 1.0.0
---

# Garmin Health Skill

Query health and fitness data from Garmin Connect efficiently. Data is pre-computed daily—no API calls during conversation.

## When to Use

Activate this skill when user asks about:
- Sleep quality, duration, or patterns
- Heart rate variability (HRV) or recovery status
- Stress levels or body battery
- Training readiness or workout recovery
- Recent activities or workout history
- Health trends over time

## Quick Commands

All commands use the script at `garmin-skill/scripts/garmin_query.py`.

**Important:** Run from the garmin-skill directory with the venv activated:
```bash
cd ~/projects/garmin/garmin-skill && source .venv/bin/activate
```

### Daily Summary (Default)
```bash
python scripts/garmin_query.py summary
```
Returns ~50 tokens: `Health 2026-01-28: Sleep 7h 12m (good), HRV 48ms (+8%), Body Battery 85, Ready`

### Detailed Summary
```bash
python scripts/garmin_query.py -v summary
```
Returns ~150 tokens with trends and all metrics.

### Full JSON (for edge cases)
```bash
python scripts/garmin_query.py -vv summary
```

### Trend Analysis
```bash
python scripts/garmin_query.py trends hrv 7
python scripts/garmin_query.py trends sleep 14
python scripts/garmin_query.py trends stress 7
python scripts/garmin_query.py trends rhr 30
```
Available metrics: `hrv`, `sleep`, `stress`, `rhr`

### Compare to Baseline
```bash
python scripts/garmin_query.py compare
python scripts/garmin_query.py compare 2026-01-25
```
Shows today's metrics vs 7-day rolling averages.

### Recent Activities
```bash
python scripts/garmin_query.py activities 5
```

### Refresh Data (if stale)
```bash
python scripts/garmin_query.py sync
```

## Output Tier Selection

| User Query | Tier | Command |
|------------|------|---------|
| "How'd I sleep?" | brief | `summary` |
| "Quick health check" | brief | `summary` |
| "Give me a health report" | normal | `-v summary` |
| "Detailed health stats" | normal | `-v summary` |
| "Full health data as JSON" | detailed | `-vv summary` |
| "What's my HRV trend?" | normal | `trends hrv 7` |
| "Compare to my baseline" | normal | `compare` |

## Staleness Handling

Data syncs daily (typically 6 AM via cron). If data is >18 hours old:
- Output is prefixed with `[STALE: Xh ago]`
- Exit code is 2 (vs 0 for fresh)
- Consider running `sync` command if critical decisions needed

## Metric Interpretation

| Metric | Good | Moderate | Poor |
|--------|------|----------|------|
| HRV | >50ms or +5% trend | 40-50ms | <40ms or declining |
| Sleep | >7h, score >80 | 6-7h, score 60-80 | <6h, score <60 |
| Body Battery | Start >80 | Start 50-80 | Start <50 |
| Training Readiness | >70 (Ready/Prime) | 50-70 (Moderate) | <50 (Low) |
| Stress | Avg <30 | Avg 30-50 | Avg >50 |

## Training Recommendations Based on Metrics

| Condition | Recommendation |
|-----------|----------------|
| HRV <40ms OR Sleep <6h | Rest day / easy movement |
| HRV balanced + Sleep good | Proceed with planned training |
| Readiness PRIME + Body Battery >80 | Can push harder if desired |
| Stress avg >50 | Prioritize recovery, reduce intensity |

## Error Handling

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success, data fresh |
| 1 | Error (DB missing, invalid args, auth failed) |
| 2 | Success but data stale (>18h old) |

## Files

- Database: `~/.garmin-skill/garmin.db`
- Sync log: `~/.garmin-skill/sync.log`
- Scripts: `garmin-skill/scripts/`
- Lock file: `~/.garmin-skill/sync.lock` (prevents concurrent syncs)
