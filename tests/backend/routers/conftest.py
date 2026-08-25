"""Fixtures for API router tests: seeded SQLite + matching Parquet stream.

Everything stays inside the temp data dir set up by the root conftest —
the real data/ directory is never touched.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.db import connect, init_db

ACTIVITY_ID = 1
ACTIVITY_START = "2026-05-01T09:00:00Z"
RIDE_SECONDS = 5400  # 90 minutes of 1 Hz data


@pytest.fixture()
def seeded(api_client, data_dir):
    """TestClient against a DB with one ride (power + geo) and its Parquet file."""
    init_db()
    conn = connect()
    conn.execute(
        """
        INSERT INTO activities (
            id, start_time, name, type, description,
            distance_m, elapsed_s, moving_s,
            avg_speed_ms, max_speed_ms, avg_hr, max_hr,
            avg_power, max_power, np_power,
            has_geo, has_power, point_count
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            1, 1, ?
        )
        """,
        (
            ACTIVITY_ID, ACTIVITY_START, "Morning Ride", "Ride", "test ride",
            42_000.0, float(RIDE_SECONDS), 5_200.0,
            7.78, 12.5, 150.0, 180.0,
            250.0, 600.0, 270.0,
            RIDE_SECONDS,
        ),
    )
    conn.commit()
    conn.close()

    df = pd.DataFrame(
        {
            "t": pd.date_range("2026-05-01 09:00:00+00:00", periods=RIDE_SECONDS, freq="s"),
            "power": 250.0,
            "heart_rate": 150.0,
            "speed": 8.0,
            "altitude": 100.0,
            "distance": np.arange(RIDE_SECONDS, dtype=float) * 8.0,
        }
    )
    df.to_parquet(data_dir / "streams" / f"{ACTIVITY_ID}.parquet", index=False)
    return api_client