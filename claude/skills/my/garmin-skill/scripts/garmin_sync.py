#!/usr/bin/env python3
"""Daily Garmin data sync service.

Pulls health and activity data from Garmin Connect, computes summaries,
and stores everything in SQLite for efficient agent queries.

Usage:
    python garmin_sync.py              # Sync today
    python garmin_sync.py --backfill 7 # Sync last 7 days
    python garmin_sync.py --date 2026-01-20  # Sync specific date
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from garminconnect import Garmin

# Paths
DATA_DIR = Path.home() / ".garmin-skill"
DB_PATH = DATA_DIR / "garmin.db"
LOCK_PATH = DATA_DIR / "sync.lock"


def get_client() -> Garmin:
    """Authenticate with Garmin Connect.

    Tries token-based auth first (garminconnect library stores tokens in ~/.garminconnect),
    falls back to username/password from environment.
    """
    try:
        # Try token-based auth first
        client = Garmin()
        client.login()
        return client
    except Exception:
        pass

    # Fall back to env vars
    username = os.environ.get("GARMIN_USERNAME")
    password = os.environ.get("GARMIN_PASSWORD")

    if not username or not password:
        print("Error: Garmin authentication failed.", file=sys.stderr)
        print("Set GARMIN_USERNAME and GARMIN_PASSWORD environment variables,", file=sys.stderr)
        print("or ensure valid tokens exist in ~/.garminconnect/", file=sys.stderr)
        sys.exit(1)

    client = Garmin(username, password)
    client.login()
    return client


def safe(fn):
    """Execute function safely, returning None on error."""
    try:
        return fn()
    except Exception:
        return None


def pull_health_data(client: Garmin, day: str) -> dict:
    """Pull all health metrics for a given day."""
    return {
        "date": day,
        "sleep": safe(lambda: client.get_sleep_data(day)),
        "hrv": safe(lambda: client.get_hrv_data(day)),
        "stress": safe(lambda: client.get_stress_data(day)),
        "body_battery": safe(lambda: client.get_body_battery(day)),
        "training_readiness": safe(lambda: client.get_training_readiness(day)),
        "morning_training_readiness": safe(lambda: client.get_morning_training_readiness(day)),
        "steps": safe(lambda: client.get_steps_data(day)),
        "heart_rates": safe(lambda: client.get_heart_rates(day)),
    }


def extract_metrics(raw: dict) -> dict:
    """Extract normalized metrics from raw API response."""
    metrics = {
        "date": raw["date"],
        "sleep_seconds": None,
        "sleep_score": None,
        "deep_sleep_seconds": None,
        "hrv_last_night": None,
        "hrv_weekly_avg": None,
        "hrv_status": None,
        "resting_hr": None,
        "stress_avg": None,
        "stress_max": None,
        "body_battery_start": None,
        "body_battery_end": None,
        "training_readiness": None,
        "training_readiness_level": None,
        "steps": None,
    }

    # Sleep
    sleep = raw.get("sleep") or {}
    dto = sleep.get("dailySleepDTO") or {}
    metrics["sleep_seconds"] = dto.get("sleepTimeSeconds")
    scores = dto.get("sleepScores") or {}
    overall = scores.get("overall") or {}
    metrics["sleep_score"] = overall.get("value")
    metrics["deep_sleep_seconds"] = dto.get("deepSleepSeconds")

    # HRV
    hrv = raw.get("hrv") or {}
    summary = hrv.get("hrvSummary") or {}
    metrics["hrv_last_night"] = summary.get("lastNightAvg")
    metrics["hrv_weekly_avg"] = summary.get("weeklyAvg")
    metrics["hrv_status"] = summary.get("status")

    # Heart rate
    hr = raw.get("heart_rates") or {}
    metrics["resting_hr"] = hr.get("restingHeartRate")

    # Stress
    stress = raw.get("stress") or {}
    metrics["stress_avg"] = stress.get("avgStressLevel")
    metrics["stress_max"] = stress.get("maxStressLevel")

    # Body battery
    bb = raw.get("body_battery") or []
    if bb and isinstance(bb, list) and len(bb) > 0:
        arr = bb[0].get("bodyBatteryValuesArray") or []
        if arr:
            metrics["body_battery_start"] = arr[0][1] if len(arr[0]) > 1 else None
            metrics["body_battery_end"] = arr[-1][1] if len(arr[-1]) > 1 else None

    # Training readiness
    tr = raw.get("morning_training_readiness") or raw.get("training_readiness") or {}
    metrics["training_readiness"] = tr.get("score")
    metrics["training_readiness_level"] = tr.get("level")

    # Steps
    steps_data = raw.get("steps") or []
    if steps_data and isinstance(steps_data, list):
        metrics["steps"] = sum(s.get("steps", 0) for s in steps_data if isinstance(s, dict))

    return metrics


def compute_baseline(conn: sqlite3.Connection, day: str) -> dict:
    """Compute 7-day rolling averages for comparison."""
    target = date.fromisoformat(day)
    start = (target - timedelta(days=7)).isoformat()

    cursor = conn.execute("""
        SELECT
            AVG(hrv_last_night) as hrv_avg,
            AVG(sleep_seconds) as sleep_avg,
            AVG(resting_hr) as rhr_avg,
            AVG(stress_avg) as stress_avg
        FROM daily_health
        WHERE date >= ? AND date < ?
    """, (start, day))

    row = cursor.fetchone()
    return {
        "hrv_7day_avg": row[0],
        "sleep_7day_avg": row[1],
        "resting_hr_7day_avg": row[2],
        "stress_7day_avg": row[3],
    }


def _fmt_hours(seconds: int | None) -> str:
    """Format seconds as Xh Ym."""
    if seconds is None:
        return "?"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    return f"{hours}h {mins:02d}m"


def _sleep_quality(score: int | None) -> str:
    """Convert sleep score to quality label."""
    if score is None:
        return "?"
    if score >= 80:
        return "good"
    if score >= 60:
        return "fair"
    return "poor"


def _trend_str(current: float | None, baseline: float | None) -> str:
    """Generate trend string like '+8%' or '-5%'."""
    if current is None or baseline is None or baseline == 0:
        return ""
    pct = ((current - baseline) / baseline) * 100
    sign = "+" if pct >= 0 else ""
    return f" ({sign}{pct:.0f}%)"


def _readiness_label(level: str | None) -> str:
    """Normalize readiness level."""
    if not level:
        return "?"
    level = level.upper()
    if level in ("PRIME", "READY"):
        return "Ready"
    if level == "MODERATE":
        return "Moderate"
    return "Low"


def generate_summaries(metrics: dict, baseline: dict) -> tuple[str, str]:
    """Generate brief and normal summaries."""
    day = metrics["date"]

    # Brief summary (~50 tokens)
    sleep_hours = _fmt_hours(metrics["sleep_seconds"]) if metrics["sleep_seconds"] else "?"
    sleep_qual = _sleep_quality(metrics["sleep_score"])
    hrv = metrics["hrv_last_night"]
    hrv_str = f"{hrv:.0f}ms" if hrv else "?"
    hrv_trend = _trend_str(hrv, baseline.get("hrv_7day_avg"))
    bb = metrics["body_battery_start"]
    bb_str = str(bb) if bb else "?"
    readiness = _readiness_label(metrics["training_readiness_level"])

    brief = f"Health {day}: Sleep {sleep_hours} ({sleep_qual}), HRV {hrv_str}{hrv_trend}, Body Battery {bb_str}, {readiness}"

    # Normal summary (~150 tokens)
    deep = _fmt_hours(metrics["deep_sleep_seconds"]) if metrics["deep_sleep_seconds"] else "?"
    deep_pct = ""
    if metrics["sleep_seconds"] and metrics["deep_sleep_seconds"]:
        pct = (metrics["deep_sleep_seconds"] / metrics["sleep_seconds"]) * 100
        deep_pct = f" ({pct:.0f}%)"

    hrv_status = metrics["hrv_status"] or "?"
    stress = metrics["stress_avg"]
    stress_str = f"avg {stress}" if stress else "?"
    bb_end = metrics["body_battery_end"]
    bb_used = (bb - bb_end) if bb and bb_end else None
    bb_range = f"{bb} → {bb_end} (used {bb_used})" if bb_used is not None else bb_str
    tr_score = metrics["training_readiness"]
    tr_str = f"{tr_score} ({readiness})" if tr_score else readiness
    steps = metrics["steps"]
    steps_str = f"{steps:,}" if steps else "?"
    rhr = metrics["resting_hr"]
    rhr_str = f"{rhr} bpm" if rhr else "?"

    normal = f"""Health Summary - {day}

Sleep: {sleep_hours} | Quality: {sleep_qual.title()} | Deep: {deep}{deep_pct}
HRV: {hrv_str} | Trend:{hrv_trend or ' stable'} | Status: {hrv_status}
Stress: {stress_str} | Body Battery: {bb_range}
Training Readiness: {tr_str}
Steps: {steps_str} | Resting HR: {rhr_str}"""

    return brief.strip(), normal.strip()


def store_day(conn: sqlite3.Connection, metrics: dict, baseline: dict,
              brief: str, normal: str, raw_json: str):
    """Store all data for a day in the database."""
    now = datetime.now().isoformat()

    # Insert/replace daily_health
    conn.execute("""
        INSERT OR REPLACE INTO daily_health
        (date, sleep_seconds, sleep_score, deep_sleep_seconds,
         hrv_last_night, hrv_weekly_avg, hrv_status, resting_hr,
         stress_avg, stress_max, body_battery_start, body_battery_end,
         training_readiness, training_readiness_level, steps, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        metrics["date"], metrics["sleep_seconds"], metrics["sleep_score"],
        metrics["deep_sleep_seconds"], metrics["hrv_last_night"],
        metrics["hrv_weekly_avg"], metrics["hrv_status"], metrics["resting_hr"],
        metrics["stress_avg"], metrics["stress_max"], metrics["body_battery_start"],
        metrics["body_battery_end"], metrics["training_readiness"],
        metrics["training_readiness_level"], metrics["steps"], raw_json
    ))

    # Insert/replace summaries
    conn.execute("""
        INSERT OR REPLACE INTO summaries (date, brief, normal, computed_at)
        VALUES (?, ?, ?, ?)
    """, (metrics["date"], brief, normal, now))

    # Insert/replace baselines
    conn.execute("""
        INSERT OR REPLACE INTO baselines
        (date, hrv_7day_avg, sleep_7day_avg, resting_hr_7day_avg, stress_7day_avg)
        VALUES (?, ?, ?, ?, ?)
    """, (
        metrics["date"], baseline.get("hrv_7day_avg"), baseline.get("sleep_7day_avg"),
        baseline.get("resting_hr_7day_avg"), baseline.get("stress_7day_avg")
    ))

    conn.commit()


def sync_activities(client: Garmin, conn: sqlite3.Connection, count: int = 10):
    """Sync recent activities."""
    try:
        activities = client.get_activities(0, count)
    except Exception as e:
        print(f"Warning: Could not fetch activities: {e}", file=sys.stderr)
        return

    for a in activities:
        activity_id = str(a.get("activityId", ""))
        if not activity_id:
            continue

        date_str = a.get("startTimeLocal", "")[:10]
        activity_type = a.get("activityType", {}).get("typeKey", "unknown")
        name = a.get("activityName", "")
        duration = int(a.get("duration", 0))
        distance = a.get("distance")
        calories = a.get("calories")
        avg_hr = a.get("averageHR")
        te = a.get("aerobicTrainingEffect")

        # Generate one-liner summary
        dur_mins = duration // 60
        summary_parts = [f"{dur_mins}min {activity_type}"]
        if distance:
            km = distance / 1000
            summary_parts.append(f"{km:.1f}km")
        if calories:
            summary_parts.append(f"{calories}kcal")
        if avg_hr:
            summary_parts.append(f"{avg_hr}bpm avg")
        summary = ", ".join(summary_parts)

        conn.execute("""
            INSERT OR REPLACE INTO activities
            (activity_id, date, type, name, duration_seconds, distance_meters,
             calories, avg_hr, training_effect, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (activity_id, date_str, activity_type, name, duration, distance,
              calories, avg_hr, te, summary))

    conn.commit()


def sync_day(client: Garmin, conn: sqlite3.Connection, day: str):
    """Sync a single day's health data."""
    print(f"Syncing {day}...", end=" ", flush=True)

    raw = pull_health_data(client, day)
    metrics = extract_metrics(raw)
    baseline = compute_baseline(conn, day)
    brief, normal = generate_summaries(metrics, baseline)
    raw_json = json.dumps(raw, ensure_ascii=False)

    store_day(conn, metrics, baseline, brief, normal, raw_json)

    # Update last_sync
    conn.execute("""
        INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_sync', ?)
    """, (datetime.now().isoformat(),))
    conn.commit()

    print("done")


def main():
    parser = argparse.ArgumentParser(description="Sync Garmin health data")
    parser.add_argument("--date", help="Sync specific date (YYYY-MM-DD)")
    parser.add_argument("--backfill", type=int, metavar="DAYS",
                        help="Backfill N days of data")
    args = parser.parse_args()

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Acquire lock
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Error: Another sync is already running.", file=sys.stderr)
        sys.exit(1)

    try:
        # Initialize DB if needed
        from db import init_db
        conn = init_db(DB_PATH)

        # Authenticate
        print("Authenticating with Garmin...")
        client = get_client()
        print("Authenticated successfully")

        # Determine days to sync
        today = date.today()
        if args.date:
            days = [args.date]
        elif args.backfill:
            days = [(today - timedelta(days=i)).isoformat()
                    for i in range(args.backfill - 1, -1, -1)]
        else:
            days = [today.isoformat()]

        # Sync each day
        for day in days:
            sync_day(client, conn, day)

        # Sync activities
        print("Syncing activities...")
        sync_activities(client, conn)
        print("Sync complete!")

    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


if __name__ == "__main__":
    main()
