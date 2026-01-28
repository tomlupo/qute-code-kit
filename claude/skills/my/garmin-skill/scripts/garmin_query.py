#!/usr/bin/env python3
"""Query interface for Garmin health data.

Reads pre-computed summaries from SQLite for efficient agent queries.

Usage:
    python garmin_query.py summary           # Brief summary for today
    python garmin_query.py -v summary        # Normal detail
    python garmin_query.py -vv summary       # Full JSON
    python garmin_query.py summary 2026-01-20  # Specific date
    python garmin_query.py trends hrv 7      # HRV trend over 7 days
    python garmin_query.py compare           # Compare today to baseline
    python garmin_query.py activities 5      # Recent 5 activities
    python garmin_query.py sync              # Trigger on-demand sync

Exit codes:
    0 - Success, data fresh
    1 - Error (DB missing, invalid args, etc.)
    2 - Success but data is stale (>18h old)
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path.home() / ".garmin-skill"
DB_PATH = DATA_DIR / "garmin.db"
STALENESS_HOURS = 18


def get_connection() -> sqlite3.Connection:
    """Get database connection with helpful error."""
    if not DB_PATH.exists():
        print("Error: Database not found.", file=sys.stderr)
        print("Run install.sh first to set up the Garmin skill.", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def check_staleness(conn: sqlite3.Connection) -> tuple[bool, str]:
    """Check if data is stale. Returns (is_stale, last_sync_time)."""
    cursor = conn.execute(
        "SELECT value FROM sync_meta WHERE key = 'last_sync'"
    )
    row = cursor.fetchone()

    if not row:
        return True, "never"

    last_sync_str = row[0]
    try:
        last_sync = datetime.fromisoformat(last_sync_str)
        age = datetime.now() - last_sync
        is_stale = age > timedelta(hours=STALENESS_HOURS)
        # Format as relative time
        hours_ago = int(age.total_seconds() // 3600)
        if hours_ago < 1:
            time_str = "just now"
        elif hours_ago < 24:
            time_str = f"{hours_ago}h ago"
        else:
            days = hours_ago // 24
            time_str = f"{days}d ago"
        return is_stale, time_str
    except ValueError:
        return True, "unknown"


def cmd_summary(args):
    """Return health summary for a date."""
    conn = get_connection()
    is_stale, last_sync = check_staleness(conn)

    target_date = args.date or date.today().isoformat()

    # Validate date format
    try:
        date.fromisoformat(target_date)
    except ValueError:
        print(f"Error: Invalid date format '{target_date}'. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    # Check for future date
    if target_date > date.today().isoformat():
        print(f"Error: Cannot query future date {target_date}.", file=sys.stderr)
        sys.exit(1)

    # Select output based on verbosity
    if args.verbose >= 2:
        # Detailed: return raw JSON
        cursor = conn.execute(
            "SELECT raw_json FROM daily_health WHERE date = ?",
            (target_date,)
        )
        row = cursor.fetchone()
        if not row:
            print(f"No data for {target_date}", file=sys.stderr)
            sys.exit(1)
        print(row[0])
    else:
        # Brief or normal summary
        cursor = conn.execute(
            "SELECT brief, normal FROM summaries WHERE date = ?",
            (target_date,)
        )
        row = cursor.fetchone()
        if not row:
            print(f"No data for {target_date}", file=sys.stderr)
            sys.exit(1)

        brief, normal = row

        if args.verbose == 1:
            output = normal
        else:
            output = brief
            if is_stale:
                output = f"[STALE: {last_sync}] {output}"

        print(output)

    sys.exit(2 if is_stale else 0)


def cmd_trends(args):
    """Return trend analysis for a metric."""
    conn = get_connection()
    is_stale, _ = check_staleness(conn)

    metric = args.metric
    days = args.days

    # Map metric name to column
    column_map = {
        "hrv": "hrv_last_night",
        "sleep": "sleep_seconds",
        "stress": "stress_avg",
        "rhr": "resting_hr",
    }
    column = column_map.get(metric)
    if not column:
        print(f"Error: Unknown metric '{metric}'", file=sys.stderr)
        sys.exit(1)

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    cursor = conn.execute(f"""
        SELECT date, {column}
        FROM daily_health
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    """, (start_date.isoformat(), end_date.isoformat()))

    rows = cursor.fetchall()

    if not rows:
        print(f"No {metric} data for the last {days} days", file=sys.stderr)
        sys.exit(1)

    # Calculate stats
    values = [v for _, v in rows if v is not None]
    if not values:
        print(f"No valid {metric} values in the last {days} days", file=sys.stderr)
        sys.exit(1)

    avg = sum(values) / len(values)
    min_val = min(values)
    max_val = max(values)

    # First and last for trend
    first = values[0]
    last = values[-1]
    change = ((last - first) / first * 100) if first else 0
    trend_dir = "↑" if change > 2 else "↓" if change < -2 else "→"

    # Format based on metric
    if metric == "sleep":
        # Convert to hours
        def fmt(v):
            return f"{v / 3600:.1f}h"
        print(f"{metric.upper()} Trend ({days} days): {fmt(avg)} avg | Range: {fmt(min_val)}-{fmt(max_val)} | {trend_dir} {change:+.0f}%")
    else:
        unit = "ms" if metric == "hrv" else "bpm" if metric == "rhr" else ""
        print(f"{metric.upper()} Trend ({days} days): {avg:.0f}{unit} avg | Range: {min_val:.0f}-{max_val:.0f}{unit} | {trend_dir} {change:+.0f}%")

    # Show daily values
    print("\nDaily values:")
    for dt, val in rows:
        if val is not None:
            if metric == "sleep":
                print(f"  {dt}: {val / 3600:.1f}h")
            else:
                print(f"  {dt}: {val:.0f}")
        else:
            print(f"  {dt}: --")

    sys.exit(2 if is_stale else 0)


def cmd_compare(args):
    """Compare date to 7-day baseline."""
    conn = get_connection()
    is_stale, _ = check_staleness(conn)

    target_date = args.date or date.today().isoformat()

    # Get metrics for target date
    cursor = conn.execute("""
        SELECT sleep_seconds, hrv_last_night, stress_avg, resting_hr, body_battery_start
        FROM daily_health WHERE date = ?
    """, (target_date,))
    today_row = cursor.fetchone()

    if not today_row:
        print(f"No data for {target_date}", file=sys.stderr)
        sys.exit(1)

    sleep, hrv, stress, rhr, bb = today_row

    # Get baseline
    cursor = conn.execute("""
        SELECT hrv_7day_avg, sleep_7day_avg, resting_hr_7day_avg, stress_7day_avg
        FROM baselines WHERE date = ?
    """, (target_date,))
    baseline_row = cursor.fetchone()

    def compare_metric(name: str, current, baseline, unit: str = "", higher_is_better: bool = True):
        """Generate comparison string."""
        if current is None:
            return f"{name}: --"
        if baseline is None:
            return f"{name}: {current:.0f}{unit}"
        diff = current - baseline
        pct = (diff / baseline * 100) if baseline else 0
        sign = "+" if diff >= 0 else ""
        # Color indicator
        if higher_is_better:
            indicator = "✓" if pct > 2 else "✗" if pct < -2 else "="
        else:
            indicator = "✗" if pct > 2 else "✓" if pct < -2 else "="
        return f"{name}: {current:.0f}{unit} ({sign}{pct:.0f}% vs 7d avg) {indicator}"

    print(f"Comparison for {target_date} vs 7-day baseline\n")

    if baseline_row:
        hrv_base, sleep_base, rhr_base, stress_base = baseline_row
        print(compare_metric("HRV", hrv, hrv_base, "ms", higher_is_better=True))
        if sleep:
            sleep_h = sleep / 3600
            sleep_base_h = sleep_base / 3600 if sleep_base else None
            if sleep_base_h:
                diff_h = sleep_h - sleep_base_h
                pct = (diff_h / sleep_base_h * 100)
                sign = "+" if diff_h >= 0 else ""
                indicator = "✓" if pct > 2 else "✗" if pct < -2 else "="
                print(f"Sleep: {sleep_h:.1f}h ({sign}{pct:.0f}% vs 7d avg) {indicator}")
            else:
                print(f"Sleep: {sleep_h:.1f}h")
        print(compare_metric("Stress", stress, stress_base, "", higher_is_better=False))
        print(compare_metric("Resting HR", rhr, rhr_base, "bpm", higher_is_better=False))
    else:
        # No baseline, just show values
        print(f"HRV: {hrv:.0f}ms" if hrv else "HRV: --")
        print(f"Sleep: {sleep / 3600:.1f}h" if sleep else "Sleep: --")
        print(f"Stress: {stress:.0f}" if stress else "Stress: --")
        print(f"Resting HR: {rhr}bpm" if rhr else "Resting HR: --")
        print("\n(Baseline not available - need more days of data)")

    if bb:
        print(f"Body Battery: {bb}")

    sys.exit(2 if is_stale else 0)


def cmd_activities(args):
    """Return recent activities."""
    conn = get_connection()
    is_stale, _ = check_staleness(conn)

    n = args.n

    cursor = conn.execute("""
        SELECT date, type, name, summary
        FROM activities
        ORDER BY date DESC
        LIMIT ?
    """, (n,))

    rows = cursor.fetchall()

    if not rows:
        print("No activities recorded")
        sys.exit(0)

    print(f"Recent Activities ({len(rows)}):\n")
    for dt, activity_type, name, summary in rows:
        print(f"  {dt} | {activity_type:10} | {name}")
        print(f"           {summary}")

    sys.exit(2 if is_stale else 0)


def cmd_sync(args):
    """Trigger on-demand sync."""
    sync_script = Path(__file__).parent / "garmin_sync.py"
    if not sync_script.exists():
        print("Error: garmin_sync.py not found", file=sys.stderr)
        sys.exit(1)

    print("Starting sync...")
    result = subprocess.run(
        [sys.executable, str(sync_script)],
        capture_output=False
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Query Garmin health data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0  Success, data fresh
  1  Error (DB missing, invalid args)
  2  Success but data stale (>18h)

Examples:
  garmin_query.py summary           Brief health summary
  garmin_query.py -v summary        Detailed summary
  garmin_query.py trends hrv 14     HRV trend over 14 days
  garmin_query.py compare           Compare today to baseline
  garmin_query.py activities 10     Last 10 activities
  garmin_query.py sync              Refresh data
"""
    )
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity (-v normal, -vv detailed)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # summary [date]
    p_summary = subparsers.add_parser("summary", help="Daily health summary")
    p_summary.add_argument("date", nargs="?", help="Date (YYYY-MM-DD), default today")
    p_summary.set_defaults(func=cmd_summary)

    # trends <metric> <days>
    p_trends = subparsers.add_parser("trends", help="Metric trends over time")
    p_trends.add_argument("metric", choices=["hrv", "sleep", "stress", "rhr"],
                          help="Metric to analyze")
    p_trends.add_argument("days", type=int, nargs="?", default=7,
                          help="Number of days (default: 7)")
    p_trends.set_defaults(func=cmd_trends)

    # compare [date]
    p_compare = subparsers.add_parser("compare", help="Compare to 7-day baseline")
    p_compare.add_argument("date", nargs="?", help="Date (YYYY-MM-DD), default today")
    p_compare.set_defaults(func=cmd_compare)

    # activities [n]
    p_activities = subparsers.add_parser("activities", help="Recent activities")
    p_activities.add_argument("n", type=int, nargs="?", default=5,
                              help="Number of activities (default: 5)")
    p_activities.set_defaults(func=cmd_activities)

    # sync
    p_sync = subparsers.add_parser("sync", help="Trigger on-demand sync")
    p_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
