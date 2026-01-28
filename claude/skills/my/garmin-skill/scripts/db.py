"""Database initialization and helpers for Garmin skill."""

import sqlite3
from pathlib import Path

SCHEMA = """
-- Core health metrics
CREATE TABLE IF NOT EXISTS daily_health (
    date TEXT PRIMARY KEY,
    sleep_seconds INTEGER,
    sleep_score INTEGER,
    deep_sleep_seconds INTEGER,
    hrv_last_night REAL,
    hrv_weekly_avg REAL,
    hrv_status TEXT,
    resting_hr INTEGER,
    stress_avg INTEGER,
    stress_max INTEGER,
    body_battery_start INTEGER,
    body_battery_end INTEGER,
    training_readiness INTEGER,
    training_readiness_level TEXT,
    steps INTEGER,
    raw_json TEXT
);

-- Pre-computed summaries
CREATE TABLE IF NOT EXISTS summaries (
    date TEXT PRIMARY KEY,
    brief TEXT,
    normal TEXT,
    computed_at TEXT
);

-- Rolling baselines for trend comparisons
CREATE TABLE IF NOT EXISTS baselines (
    date TEXT PRIMARY KEY,
    hrv_7day_avg REAL,
    sleep_7day_avg REAL,
    resting_hr_7day_avg REAL,
    stress_7day_avg REAL
);

-- Recent activities
CREATE TABLE IF NOT EXISTS activities (
    activity_id TEXT PRIMARY KEY,
    date TEXT,
    type TEXT,
    name TEXT,
    duration_seconds INTEGER,
    distance_meters REAL,
    calories INTEGER,
    avg_hr INTEGER,
    training_effect REAL,
    summary TEXT
);

-- Sync metadata
CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Create indices for common queries
CREATE INDEX IF NOT EXISTS idx_daily_health_date ON daily_health(date);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a connection to the database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return sqlite3.connect(db_path)
