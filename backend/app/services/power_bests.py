"""Mean-max power computation per activity, plus all-time leaderboard."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..db import get_conn
from .streams import load_stream

# Standard durations (seconds) used in cycling power profiles.
WINDOWS_S: tuple[int, ...] = (
    3, 5, 15, 30,
    60, 120, 180, 300, 600, 1200, 1800,
    3600, 7200, 14400,
)


def compute_bests_from_df(df: pd.DataFrame, windows: Iterable[int] = WINDOWS_S) -> dict[int, float]:
    """Return {window_s: best mean-max watts} for the given ride dataframe."""
    if "power" not in df.columns or "t" not in df.columns:
        return {}
    if df["power"].notna().sum() < 2:
        return {}

    s = df.set_index("t")["power"].astype(float)
    # Resample to a regular 1 Hz grid so rolling windows correspond to seconds.
    s = s.resample("1s").mean().interpolate(limit=5).fillna(0.0)
    if s.empty:
        return {}

    duration_s = (s.index[-1] - s.index[0]).total_seconds()
    out: dict[int, float] = {}
    for w in windows:
        if duration_s + 0.5 < w:
            continue  # ride was shorter than window
        rolled = s.rolling(window=w, min_periods=w).mean()
        best = float(np.nanmax(rolled.values)) if rolled.notna().any() else float("nan")
        if not np.isnan(best):
            out[w] = best
    return out


def get_or_compute_for_activity(activity_id: int) -> dict[int, float]:
    """Return cached bests, computing & persisting on first request."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT window_s, watts FROM power_bests WHERE activity_id = ?",
            (activity_id,),
        ).fetchall()
        if rows:
            return {r["window_s"]: r["watts"] for r in rows}

        row = conn.execute(
            "SELECT id, parquet_path, has_power FROM activities WHERE id = ?",
            (activity_id,),
        ).fetchone()
        if row is None or not row["has_power"]:
            return {}

    df = load_stream(activity_id, row["parquet_path"])
    bests = compute_bests_from_df(df)
    if bests:
        with get_conn() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO power_bests(activity_id, window_s, watts) VALUES (?, ?, ?)",
                [(activity_id, w, v) for w, v in bests.items()],
            )
            conn.commit()
    return bests


def recompute_all(force: bool = False) -> dict[str, int]:
    """Compute (and cache) bests for every activity that has power. Returns counts."""
    with get_conn() as conn:
        if force:
            conn.execute("DELETE FROM power_bests")
            conn.commit()
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM activities WHERE has_power = 1 ORDER BY start_time"
        ).fetchall()]
        existing = {r["activity_id"] for r in conn.execute(
            "SELECT DISTINCT activity_id FROM power_bests"
        ).fetchall()}

    processed = 0
    skipped = 0
    failed = 0
    for aid in ids:
        if aid in existing and not force:
            skipped += 1
            continue
        try:
            get_or_compute_for_activity(aid)
            processed += 1
        except Exception:
            failed += 1
    return {"processed": processed, "skipped": skipped, "failed": failed, "total": len(ids)}


def all_time_leaderboard(top_n: int = 5) -> dict[int, list[dict]]:
    """Return {window_s: [{activity_id, watts, start_time, name}, ...]}."""
    out: dict[int, list[dict]] = {}
    with get_conn() as conn:
        for w in WINDOWS_S:
            rows = conn.execute(
                """
                SELECT pb.activity_id, pb.watts, a.start_time, a.name
                FROM power_bests pb
                JOIN activities a ON a.id = pb.activity_id
                WHERE pb.window_s = ?
                ORDER BY pb.watts DESC
                LIMIT ?
                """,
                (w, top_n),
            ).fetchall()
            if rows:
                out[w] = [dict(r) for r in rows]
    return out
