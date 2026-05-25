"""SQLite schema and helpers."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS bikes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    brand TEXT,
    model TEXT,
    default_sport TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id              INTEGER PRIMARY KEY,
    start_time      TEXT NOT NULL,
    name            TEXT,
    type            TEXT,
    description     TEXT,
    bike_id         INTEGER REFERENCES bikes(id),
    filename        TEXT,

    distance_m      REAL,
    elapsed_s       REAL,
    moving_s        REAL,

    avg_speed_ms    REAL,
    max_speed_ms    REAL,

    avg_hr          REAL,
    max_hr          REAL,

    avg_power       REAL,
    max_power       REAL,
    np_power        REAL,

    avg_cadence     REAL,
    max_cadence     REAL,

    elevation_gain_m REAL,
    elevation_low_m  REAL,
    elevation_high_m REAL,

    calories        REAL,
    avg_temp        REAL,

    has_geo         INTEGER NOT NULL DEFAULT 0,
    has_power       INTEGER NOT NULL DEFAULT 0,
    has_hr          INTEGER NOT NULL DEFAULT 0,
    has_cadence     INTEGER NOT NULL DEFAULT 0,

    point_count     INTEGER NOT NULL DEFAULT 0,
    estimated_power INTEGER NOT NULL DEFAULT 0,
    parquet_path    TEXT
);

CREATE INDEX IF NOT EXISTS idx_activities_start_time ON activities(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_activities_bike_id   ON activities(bike_id);
CREATE INDEX IF NOT EXISTS idx_activities_type      ON activities(type);

CREATE TABLE IF NOT EXISTS power_bests (
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    window_s    INTEGER NOT NULL,
    watts       REAL NOT NULL,
    PRIMARY KEY (activity_id, window_s)
);
CREATE INDEX IF NOT EXISTS idx_power_bests_window ON power_bests(window_s, watts DESC);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # Migration: add estimated_power if missing
        try:
            conn.execute("ALTER TABLE activities ADD COLUMN estimated_power INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # already exists
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
