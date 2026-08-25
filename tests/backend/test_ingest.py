"""Pipeline tests for app.ingest: directory ingest, idempotency, failure
isolation, and the upload path. All I/O is redirected to temp dirs via the
``data_dir`` fixture; the real data directory is never touched.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app import db
from app.ingest import RIDE_TYPES, ingest, ingest_uploaded_file

assert "Ride" in RIDE_TYPES, f"'Ride' missing from {RIDE_TYPES!r}"

GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="cycling-view-test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Synthetic GPX ride</name>
    <trkseg>
      <trkpt lat="48.85000" lon="2.35000"><time>2026-01-01T10:00:00Z</time><ele>100</ele></trkpt>
      <trkpt lat="48.85011" lon="2.35011"><time>2026-01-01T10:00:01Z</time><ele>101</ele></trkpt>
      <trkpt lat="48.85022" lon="2.35022"><time>2026-01-01T10:00:02Z</time><ele>102</ele></trkpt>
      <trkpt lat="48.85033" lon="2.35033"><time>2026-01-01T10:00:03Z</time><ele>103</ele></trkpt>
      <trkpt lat="48.85044" lon="2.35044"><time>2026-01-01T10:00:04Z</time><ele>104</ele></trkpt>
    </trkseg>
  </trk>
</gpx>
"""

TCX = """<?xml version="1.0"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Biking">
      <Id>2026-01-01T11:00:00Z</Id>
      <Lap StartTime="2026-01-01T11:00:00Z">
        <Track>
          <Trackpoint><Time>2026-01-01T11:00:00Z</Time><Position><LatitudeDegrees>48.85000</LatitudeDegrees><LongitudeDegrees>2.35000</LongitudeDegrees></Position><AltitudeMeters>100</AltitudeMeters></Trackpoint>
          <Trackpoint><Time>2026-01-01T11:00:01Z</Time><Position><LatitudeDegrees>48.85011</LatitudeDegrees><LongitudeDegrees>2.35011</LongitudeDegrees></Position><AltitudeMeters>101</AltitudeMeters></Trackpoint>
          <Trackpoint><Time>2026-01-01T11:00:02Z</Time><Position><LatitudeDegrees>48.85022</LatitudeDegrees><LongitudeDegrees>2.35022</LongitudeDegrees></Position><AltitudeMeters>102</AltitudeMeters></Trackpoint>
          <Trackpoint><Time>2026-01-01T11:00:03Z</Time><Position><LatitudeDegrees>48.85033</LatitudeDegrees><LongitudeDegrees>2.35033</LongitudeDegrees></Position><AltitudeMeters>103</AltitudeMeters></Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
"""


@pytest.fixture()
def conn(data_dir) -> "db.Connection":
    db.init_db()
    return db.connect()


def _activity_count(c: "db.Connection") -> int:
    return c.execute("SELECT COUNT(*) FROM activities").fetchone()[0]


def _parquet_count() -> int:
    return len(list(Path(db.settings.streams_dir).glob("*.parquet")))


# Strava UI export format: space-separated headers, one file per ride.
CSV_HEADER = "Activity ID,Activity Date,Activity Name,Activity Type,Activity Description,Activity Gear,Filename,Device Watts"


def _csv_row(rid: int, name: str, fname: str) -> str:
    return f"{rid},2026-01-01T10:00:00Z,{name},Ride,,Test Bike,{fname},true"


def _export_dir(tmp_path: Path, specs: list[tuple[int, str, str, str]]) -> Path:
    """specs: list of (id, name, filename, file_content)."""
    d = tmp_path / "export"
    d.mkdir()
    rows = [CSV_HEADER]
    for rid, name, fname, content in specs:
        (d / fname).write_text(content, encoding="utf-8")
        rows.append(_csv_row(rid, name, fname))
    (d / "activities.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return d


def test_ingest_directory_ingests_gpx_and_tcx(conn, tmp_path) -> None:
    export = _export_dir(
        tmp_path, [(1, "Synthetic GPX ride", "a.gpx", GPX), (2, "Synthetic TCX ride", "b.tcx", TCX)]
    )
    result = ingest(export)
    conn.commit()

    assert sum(result) == 2, f"unexpected ingest result: {result!r}"
    assert _activity_count(conn) == 2
    assert _parquet_count() == 2


def test_ingest_is_idempotent(conn, tmp_path) -> None:
    export = _export_dir(tmp_path, [(1, "Synthetic GPX ride", "a.gpx", GPX)])
    ingest(export)
    conn.commit()
    assert _activity_count(conn) == 1

    # Second run of the same export: nothing new is ingested.
    ingest(export)
    conn.commit()
    assert _activity_count(conn) == 1
    assert _parquet_count() == 1


def test_ingest_force_replaces_without_duplicates(conn, tmp_path) -> None:
    export = _export_dir(tmp_path, [(1, "Synthetic GPX ride", "a.gpx", GPX)])
    ingest(export)
    conn.commit()

    ingest(export, force=True)
    conn.commit()
    assert _activity_count(conn) == 1


def test_ingest_isolates_failed_files(conn, tmp_path) -> None:
    export = _export_dir(
        tmp_path,
        [
            (1, "Broken ride", "bad.gpx", "<gpx><broken"),
            (2, "Synthetic GPX ride", "ok.gpx", GPX),
            (3, "Synthetic TCX ride", "ok.tcx", TCX),
        ],
    )
    result = ingest(export)  # must not raise
    conn.commit()

    assert sum(result) == 3
    # The two valid files are ingested regardless of the broken one.
    assert _activity_count(conn) >= 2
    assert _parquet_count() >= 2


def test_ingest_uploaded_file_returns_activity_id(conn, tmp_path) -> None:
    src = tmp_path / "upload.gpx"
    src.write_text(GPX, encoding="utf-8")

    activity_id = ingest_uploaded_file(src)
    conn.commit()

    assert isinstance(activity_id, int) and activity_id > 0
    assert _activity_count(conn) == 1
    assert _parquet_count() == 1
    row = conn.execute(
        "SELECT COUNT(*) FROM activities WHERE id = ?", (activity_id,)
    ).fetchone()
    assert row[0] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))