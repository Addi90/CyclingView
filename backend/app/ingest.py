"""Ingest a Strava bulk export into SQLite + per-ride Parquet files.

Usage:
    python -m app.ingest "export_105894778(1) 2"
    python -m app.ingest path/to/export --force
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dateutil import parser as dtparser

from .config import settings
from .db import connect, init_db
from .parsers.fit import parse_fit
from .parsers.tcx import parse_tcx
from .parsers.gpx import parse_gpx
from .summary import summarize

LOG = logging.getLogger("ingest")

RIDE_TYPES = {
    "Ride",
    "Gravel Ride",
    "Mountain Bike Ride",
    "MountainBikeRide",
    "Virtual Ride",
    "VirtualRide",
    "E-Bike Ride",
    "EBikeRide",
    "EMountainBikeRide",
    "E-Mountain Bike Ride",
}


# activities.csv has duplicate column names (e.g. "Elapsed Time" appears twice).
# csv.reader returns rows as lists; we extract by *first* index of each header name
# we care about. Using pandas would silently rename duplicates.
WANTED_HEADERS = {
    "Activity ID": "id",
    "Activity Date": "date",
    "Activity Name": "name",
    "Activity Type": "type",
    "Activity Description": "description",
    "Activity Gear": "gear",
    "Filename": "filename",
}


def load_bikes(export_dir: Path, conn) -> dict[str, int]:
    bikes_csv = export_dir / "bikes.csv"
    name_to_id: dict[str, int] = {}
    if not bikes_csv.exists():
        return name_to_id
    with bikes_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("Bike Name") or "").strip()
            if not name:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO bikes(name, brand, model, default_sport) VALUES (?,?,?,?)",
                (name, row.get("Bike Brand"), row.get("Bike Model"), row.get("Bike Default Sport Types")),
            )
            if cur.lastrowid:
                name_to_id[name] = cur.lastrowid
            else:
                row2 = conn.execute("SELECT id FROM bikes WHERE name = ?", (name,)).fetchone()
                if row2:
                    name_to_id[name] = row2["id"]
    conn.commit()
    return name_to_id


def iter_activities(activities_csv: Path):
    """Yield dicts with our wanted fields, taking the *first* occurrence of each header."""
    with activities_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        # First index of each wanted header
        idx: dict[str, int] = {}
        for h, key in WANTED_HEADERS.items():
            try:
                idx[key] = header.index(h)
            except ValueError:
                pass
        for row in reader:
            if not row:
                continue
            yield {key: row[i] if i < len(row) else "" for key, i in idx.items()}


def parse_one(stream_path: Path) -> pd.DataFrame:
    name = stream_path.name.lower()
    if name.endswith(".fit.gz") or name.endswith(".fit"):
        return parse_fit(stream_path)
    if name.endswith(".tcx.gz") or name.endswith(".tcx"):
        return parse_tcx(stream_path)
    if name.endswith(".gpx.gz") or name.endswith(".gpx"):
        return parse_gpx(stream_path)
    raise ValueError(f"Unsupported file: {stream_path}")


def write_parquet(df: pd.DataFrame, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Convert timestamps to int64 ns for compact storage; keep as datetime in df.
    df.to_parquet(out, index=False, compression="snappy")


def upsert_activity(conn, row: dict) -> None:
    cols = ",".join(row.keys())
    placeholders = ",".join(["?"] * len(row))
    updates = ",".join(f"{k}=excluded.{k}" for k in row.keys() if k != "id")
    conn.execute(
        f"INSERT INTO activities ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}",
        list(row.values()),
    )


def ingest_uploaded_file(
    src_path: Path,
    *,
    name: str | None = None,
    activity_type: str = "Ride",
    description: str | None = None,
    bike_id: int | None = None,
) -> int:
    """Parse an uploaded ride file, copy it into data/uploads, write summary + parquet.

    Returns the new activity id.
    """
    init_db()
    settings.streams_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir = settings.data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    df = parse_one(src_path)
    if df.empty:
        raise ValueError("file contained no track points")

    # Use the first timestamp (microseconds) as a stable, unique-ish activity id.
    if "t" in df.columns and not df["t"].isna().all():
        first_t = df["t"].dropna().iloc[0]
        start_iso = first_t.isoformat()
        act_id = int(first_t.value // 1000)  # microseconds since epoch
    else:
        start_iso = datetime.utcnow().isoformat()
        act_id = int(datetime.utcnow().timestamp() * 1_000_000)

    # Persist a copy of the original file alongside the parquet for reproducibility.
    dst_name = f"{act_id}{''.join(src_path.suffixes)}"
    dst_path = uploads_dir / dst_name
    dst_path.write_bytes(src_path.read_bytes())

    parquet_path = settings.streams_dir / f"{act_id}.parquet"
    write_parquet(df, parquet_path)

    summary = summarize(df)

    db_row = {
        "id": act_id,
        "start_time": start_iso,
        "name": name or f"Upload {dst_path.stem}",
        "type": activity_type,
        "description": description,
        "bike_id": bike_id,
        "filename": str(dst_path.relative_to(settings.data_dir)),
        "parquet_path": str(parquet_path.relative_to(settings.data_dir)),
        **summary,
    }
    with connect() as conn:
        upsert_activity(conn, db_row)
        conn.commit()
    return act_id


def ingest(export_dir: Path, force: bool = False) -> tuple[int, int, int]:
    init_db()
    settings.streams_dir.mkdir(parents=True, exist_ok=True)

    activities_csv = export_dir / "activities.csv"
    if not activities_csv.exists():
        raise SystemExit(f"activities.csv not found in {export_dir}")

    ok = 0
    skipped = 0
    failed = 0

    with connect() as conn:
        bike_map = load_bikes(export_dir, conn)
        LOG.info("Loaded %d bikes", len(bike_map))

        for act in iter_activities(activities_csv):
            atype = (act.get("type") or "").strip()
            if atype not in RIDE_TYPES:
                continue

            try:
                act_id = int(act["id"])
            except (KeyError, ValueError):
                continue

            filename = (act.get("filename") or "").strip()
            if not filename:
                LOG.warning("activity %s has no filename, skipping", act_id)
                continue
            stream_path = export_dir / filename
            if not stream_path.exists():
                LOG.warning("activity %s: file %s missing", act_id, filename)
                continue

            parquet_path = settings.streams_dir / f"{act_id}.parquet"
            if parquet_path.exists() and not force:
                # already ingested
                skipped += 1
                continue

            try:
                df = parse_one(stream_path)
            except Exception as exc:  # noqa: BLE001
                LOG.error("activity %s: parse failed: %s", act_id, exc)
                failed += 1
                continue

            if df.empty:
                LOG.warning("activity %s: empty stream", act_id)
                failed += 1
                continue

            try:
                write_parquet(df, parquet_path)
            except Exception as exc:  # noqa: BLE001
                LOG.error("activity %s: parquet write failed: %s", act_id, exc)
                failed += 1
                continue

            summary = summarize(df)

            # Parse date
            try:
                start_time = dtparser.parse(act.get("date") or "")
                start_iso = start_time.isoformat()
            except Exception:  # noqa: BLE001
                start_iso = datetime.utcnow().isoformat()

            bike_name = (act.get("gear") or "").strip()
            bike_id = bike_map.get(bike_name)

            db_row = {
                "id": act_id,
                "start_time": start_iso,
                "name": act.get("name") or None,
                "type": atype,
                "description": act.get("description") or None,
                "bike_id": bike_id,
                "filename": filename,
                "parquet_path": str(parquet_path.relative_to(settings.data_dir)),
                **summary,
            }
            upsert_activity(conn, db_row)
            conn.commit()
            ok += 1
            if ok % 25 == 0:
                LOG.info("ingested %d activities so far...", ok)

    LOG.info("Done. ok=%d skipped=%d failed=%d", ok, skipped, failed)
    return ok, skipped, failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest a Strava export.")
    ap.add_argument("export_dir", type=Path, help="Path to the unpacked export folder.")
    ap.add_argument("--force", action="store_true", help="Re-parse even if Parquet exists.")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ok, skipped, failed = ingest(args.export_dir, force=args.force)
    print(f"ingested={ok} skipped={skipped} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
