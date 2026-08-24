"""Tests for app.db: schema, migration, and connection behavior."""
from __future__ import annotations

import sqlite3

import pytest

from app.db import SCHEMA, connect, get_conn, init_db

# Simulate a pre-migration database: identical to SCHEMA but without the
# estimated_power column (it was added later via the ALTER in init_db).
LEGACY_SCHEMA = SCHEMA.replace("    estimated_power INTEGER NOT NULL DEFAULT 0,\n", "")


@pytest.fixture()
def db_path(tmp_path):
    p = tmp_path / "test.db"
    init_db(p)
    return p


def test_connect_enables_wal_and_foreign_keys(db_path) -> None:
    conn = connect(db_path)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_connect_creates_missing_parent_dirs(tmp_path) -> None:
    p = tmp_path / "nested" / "dir" / "db.sqlite"
    conn = connect(p)
    try:
        assert p.exists()
    finally:
        conn.close()


def test_init_db_is_idempotent(db_path) -> None:
    init_db(db_path)
    init_db(db_path)
    with connect(db_path) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()}
    assert {"bikes", "activities", "power_bests"} <= tables


def test_estimated_power_migration_backfills_default(tmp_path) -> None:
    p = tmp_path / "legacy.db"
    legacy = sqlite3.connect(p)
    legacy.row_factory = sqlite3.Row
    legacy.executescript(LEGACY_SCHEMA)
    legacy.execute(
        "INSERT INTO activities (id, start_time, point_count) VALUES (1, '2026-01-01T09:00:00Z', 100)"
    )
    legacy.commit()
    legacy.close()

    init_db(p)

    conn = connect(p)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(activities)")}
        assert "estimated_power" in cols
        value = conn.execute(
            "SELECT estimated_power FROM activities WHERE id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert value == 0


def test_foreign_keys_enforced_between_activity_and_bike(db_path) -> None:
    with connect(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO activities (id, start_time, bike_id) VALUES (1, '2026-01-01T09:00:00Z', 999)"
            )


def test_indexes_exist(db_path) -> None:
    with connect(db_path) as conn:
        # PRAGMA index_list columns: (seq, name, unique, origin, partial)
        activity_idx = {r[1] for r in conn.execute("PRAGMA index_list(activities)")}
        bests_idx = {r[1] for r in conn.execute("PRAGMA index_list(power_bests)")}
    assert {"idx_activities_start_time", "idx_activities_bike_id", "idx_activities_type"} <= activity_idx
    assert "idx_power_bests_window" in bests_idx


def test_get_conn_closes_the_connection(data_dir) -> None:
    # init_db() resolves to settings.db_path inside the temp data dir.
    init_db()
    with get_conn() as conn:
        conn.execute("SELECT 1")
    # After leaving the context manager the connection must be closed.
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
