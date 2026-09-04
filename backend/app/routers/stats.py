"""Aggregated stats: totals, per-year, per-bike, plus power leaderboards & bike CRUD."""
from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_conn
from ..services.power_bests import (
    WINDOWS_S,
    all_time_leaderboard,
    get_or_compute_for_activity,
    recompute_all,
)

router = APIRouter(prefix="/api")


# --- Bike CRUD ---------------------------------------------------------------

class BikeIn(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    default_sport: str | None = None


@router.post("/bikes")
def create_bike(b: BikeIn) -> dict[str, Any]:
    if not b.name.strip():
        raise HTTPException(400, "name must not be empty")
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO bikes(name, brand, model, default_sport) VALUES (?, ?, ?, ?)",
                (b.name.strip(), b.brand, b.model, b.default_sport),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"bike with name '{b.name}' already exists") from e
        return {
            "id": cur.lastrowid,
            "name": b.name.strip(),
            "brand": b.brand,
            "model": b.model,
            "default_sport": b.default_sport,
        }


@router.patch("/bikes/{bike_id}")
def update_bike(bike_id: int, b: BikeIn) -> dict[str, Any]:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM bikes WHERE id = ?", (bike_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "bike not found")
        try:
            conn.execute(
                "UPDATE bikes SET name=?, brand=?, model=?, default_sport=? WHERE id=?",
                (b.name.strip(), b.brand, b.model, b.default_sport, bike_id),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, "name conflicts with another bike") from e
    return {"id": bike_id, **b.model_dump()}


@router.delete("/bikes/{bike_id}")
def delete_bike(bike_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        used = conn.execute(
            "SELECT COUNT(*) AS c FROM activities WHERE bike_id = ?", (bike_id,)
        ).fetchone()["c"]
        if used:
            raise HTTPException(409, f"bike is used by {used} activity/-ies; reassign first")
        cur = conn.execute("DELETE FROM bikes WHERE id = ?", (bike_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "bike not found")
    return {"deleted": bike_id}


# --- Aggregated stats --------------------------------------------------------

@router.get("/stats")
def overall_stats(year: int = 0) -> dict[str, Any]:
    """Global stats. With ?year=N the per-bike / unassigned tables are
    restricted to that year (totals, longest and per-year stay all-time)."""
    if year and not (1900 <= year <= 2100):
        raise HTTPException(400, "year must be between 1900 and 2100")
    with get_conn() as conn:
        totals = dict(conn.execute(
            """
            SELECT
                COUNT(*)                           AS rides,
                COALESCE(SUM(distance_m), 0)       AS distance_m,
                COALESCE(SUM(moving_s), 0)         AS moving_s,
                COALESCE(SUM(elapsed_s), 0)        AS elapsed_s,
                COALESCE(SUM(elevation_gain_m), 0) AS elevation_gain_m,
                MAX(distance_m)                    AS longest_distance_m,
                MAX(moving_s)                      AS longest_moving_s
            FROM activities
            """
        ).fetchone())

        # Find the longest-distance and longest-duration ride records.
        longest_dist = conn.execute(
            "SELECT id, name, start_time, distance_m, moving_s "
            "FROM activities WHERE distance_m IS NOT NULL ORDER BY distance_m DESC LIMIT 1"
        ).fetchone()
        longest_time = conn.execute(
            "SELECT id, name, start_time, distance_m, moving_s "
            "FROM activities WHERE moving_s IS NOT NULL ORDER BY moving_s DESC LIMIT 1"
        ).fetchone()

        per_year = [dict(r) for r in conn.execute(
            """
            SELECT substr(start_time, 1, 4) AS year,
                   COUNT(*) AS rides,
                   COALESCE(SUM(distance_m), 0) AS distance_m,
                   COALESCE(SUM(moving_s), 0)   AS moving_s,
                   COALESCE(SUM(elevation_gain_m), 0) AS elevation_gain_m,
                   MAX(distance_m) AS longest_distance_m,
                   MAX(moving_s)   AS longest_moving_s
            FROM activities
            GROUP BY year
            ORDER BY year DESC
            """
        ).fetchall()]

        per_bike = [dict(r) for r in conn.execute(
            """
            SELECT b.id AS bike_id, b.name AS bike_name,
                   COUNT(a.id) AS rides,
                   COALESCE(SUM(a.distance_m), 0) AS distance_m,
                   COALESCE(SUM(a.moving_s), 0)   AS moving_s,
                   COALESCE(SUM(a.elevation_gain_m), 0) AS elevation_gain_m,
                   MIN(a.start_time) AS first_ride,
                   MAX(a.start_time) AS last_ride
            FROM bikes b
            LEFT JOIN activities a ON a.bike_id = b.id
              AND (? = 0 OR substr(a.start_time, 1, 4) = CAST(? AS TEXT))
            GROUP BY b.id, b.name
            ORDER BY distance_m DESC
            """,
            (year, str(year))
        ).fetchall()]

        # Activities without an assigned bike (same year filter).
        unassigned = dict(conn.execute(
            """
            SELECT COUNT(*) AS rides,
                   COALESCE(SUM(distance_m), 0) AS distance_m,
                   COALESCE(SUM(moving_s), 0)   AS moving_s
            FROM activities
            WHERE bike_id IS NULL
              AND (? = 0 OR substr(start_time, 1, 4) = CAST(? AS TEXT))
            """,
            (year, str(year))
        ).fetchone())

    return {
        "totals": totals,
        "longest_distance": dict(longest_dist) if longest_dist else None,
        "longest_duration": dict(longest_time) if longest_time else None,
        "per_year": per_year,
        "per_bike": per_bike,
        "unassigned": unassigned,
    }


# --- Power bests -------------------------------------------------------------

@router.get("/power-bests/windows")
def power_windows() -> dict[str, list[int]]:
    return {"windows_s": list(WINDOWS_S)}


@router.get("/power-bests/{activity_id}")
def power_bests_for_ride(activity_id: int) -> dict[str, Any]:
    bests = get_or_compute_for_activity(activity_id)
    est = 0
    with get_conn() as conn:
        row = conn.execute("SELECT estimated_power FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if row:
            est = row["estimated_power"]
    return {
        "activity_id": activity_id,
        "estimated_power": est,
        "windows_s": list(WINDOWS_S),
        "bests": [{"window_s": w, "watts": bests.get(w)} for w in WINDOWS_S],
    }


@router.get("/power-bests")
def power_bests_all_time(top_n: int = 5) -> dict[str, Any]:
    leaderboard = all_time_leaderboard(top_n=top_n)
    return {
        "windows_s": list(WINDOWS_S),
        "leaderboard": {str(w): leaderboard.get(w, []) for w in WINDOWS_S},
    }


@router.post("/power-bests/recompute")
def power_bests_recompute(force: bool = False) -> dict[str, Any]:
    return recompute_all(force=force)
