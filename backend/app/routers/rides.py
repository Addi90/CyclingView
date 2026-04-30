"""API routes for rides and bikes."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_conn
from ..services.streams import STREAM_FIELDS, downsample, load_stream

router = APIRouter(prefix="/api")


def _row_to_dict(row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


@router.get("/bikes")
def list_bikes() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bikes ORDER BY name").fetchall()
        return [_row_to_dict(r) for r in rows]


@router.get("/rides")
def list_rides(
    bike_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    where = []
    params: list[Any] = []
    if bike_id is not None:
        where.append("a.bike_id = ?")
        params.append(bike_id)
    if date_from:
        where.append("a.start_time >= ?")
        params.append(date_from)
    if date_to:
        where.append("a.start_time <= ?")
        params.append(date_to)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM activities a {where_sql}", params
        ).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT a.*, b.name AS bike_name, b.brand AS bike_brand, b.model AS bike_model
            FROM activities a
            LEFT JOIN bikes b ON a.bike_id = b.id
            {where_sql}
            ORDER BY a.start_time DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_row_to_dict(r) for r in rows],
    }


def _fetch_activity(activity_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT a.*, b.name AS bike_name, b.brand AS bike_brand, b.model AS bike_model
            FROM activities a
            LEFT JOIN bikes b ON a.bike_id = b.id
            WHERE a.id = ?
            """,
            (activity_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, f"activity {activity_id} not found")
    return row


@router.get("/rides/{activity_id}")
def get_ride(activity_id: int) -> dict[str, Any]:
    return _row_to_dict(_fetch_activity(activity_id))


class RideUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    description: str | None = None
    bike_id: int | None = None


@router.patch("/rides/{activity_id}")
def update_ride(activity_id: int, body: RideUpdate) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "no fields to update")

    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not existing:
            raise HTTPException(404, f"activity {activity_id} not found")

        if "bike_id" in fields and fields["bike_id"] is not None:
            b = conn.execute("SELECT id FROM bikes WHERE id = ?", (fields["bike_id"],)).fetchone()
            if not b:
                raise HTTPException(400, f"bike {fields['bike_id']} does not exist")

        sets = ", ".join(f"{k} = ?" for k in fields.keys())
        conn.execute(
            f"UPDATE activities SET {sets} WHERE id = ?",
            [*fields.values(), activity_id],
        )
        conn.commit()

    return _row_to_dict(_fetch_activity(activity_id))


@router.delete("/rides/{activity_id}")
def delete_ride(activity_id: int) -> dict[str, Any]:
    from ..config import settings

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, parquet_path, filename FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"activity {activity_id} not found")

        conn.execute("DELETE FROM power_bests WHERE activity_id = ?", (activity_id,))
        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        conn.commit()

    # Best-effort cleanup of parquet + uploaded source.
    try:
        if row["parquet_path"]:
            p = settings.data_dir / row["parquet_path"]
            if p.exists():
                p.unlink()
        else:
            p = settings.streams_dir / f"{activity_id}.parquet"
            if p.exists():
                p.unlink()
    except Exception:
        pass

    try:
        from ..services.streams import load_stream as _ls
        _ls.cache_clear()
    except Exception:
        pass

    return {"deleted": activity_id}


@router.get("/rides/{activity_id}/streams")
def get_streams(
    activity_id: int,
    fields: str = Query(
        default="power,heart_rate,speed,altitude,cadence",
        description="Comma-separated list of fields to return.",
    ),
    n_points: int = Query(0, ge=0, le=500000, description="0 = no downsampling, return all points."),
) -> dict[str, Any]:
    row = _fetch_activity(activity_id)
    requested = [f.strip() for f in fields.split(",") if f.strip()]
    invalid = [f for f in requested if f not in STREAM_FIELDS]
    if invalid:
        raise HTTPException(400, f"Unknown fields: {invalid}. Allowed: {list(STREAM_FIELDS)}")

    try:
        df = load_stream(activity_id, row["parquet_path"])
    except FileNotFoundError:
        raise HTTPException(404, "stream file missing")

    data = downsample(df, requested, n_points=n_points)
    return {
        "activity_id": activity_id,
        "fields": requested,
        "count": len(data["t"]),
        **data,
    }


@router.get("/rides/{activity_id}/geo")
def get_geo(
    activity_id: int,
    n_points: int = Query(8000, ge=100, le=50000),
) -> dict[str, Any]:
    """Return GeoJSON LineString plus parallel stream arrays for color-coded overlays."""
    row = _fetch_activity(activity_id)
    if not row["has_geo"]:
        raise HTTPException(404, "activity has no GPS data")

    try:
        df = load_stream(activity_id, row["parquet_path"])
    except FileNotFoundError:
        raise HTTPException(404, "stream file missing")

    df = df.dropna(subset=["lat", "lon"])
    if df.empty:
        raise HTTPException(404, "no valid GPS points")

    # Downsample uniformly while keeping streams aligned.
    if len(df) > n_points:
        idx = np.linspace(0, len(df) - 1, n_points).astype(int)
        df = df.iloc[idx].reset_index(drop=True)

    coords = list(zip(df["lon"].astype(float), df["lat"].astype(float)))

    streams: dict[str, list] = {}
    for f in ("power", "heart_rate", "speed", "altitude", "cadence", "distance"):
        if f in df.columns:
            arr = df[f].to_numpy()
            streams[f] = [
                None if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)
                for v in arr
            ]

    if "t" in df.columns:
        t_rel = (df["t"] - df["t"].iloc[0]).dt.total_seconds().to_numpy().tolist()
    else:
        t_rel = list(range(len(df)))

    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [list(c) for c in coords]},
        "properties": {
            "activity_id": activity_id,
            "t": t_rel,
            "streams": streams,
        },
    }
