"""Parser tests: GPX and TCX parsing, plus parse_one dispatch."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.ingest import parse_one
from app.parsers.gpx import parse_gpx
from app.parsers.tcx import parse_tcx

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

GPX_EMPTY = """<?xml version="1.0"?>
<gpx version="1.1" creator="cycling-view-test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>No points</name><trkseg></trkseg></trk>
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


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_parse_gpx_returns_one_row_per_trackpoint(tmp_path) -> None:
    df = parse_gpx(_write(tmp_path, "a.gpx", GPX))
    assert not df.empty
    assert len(df) == 5
    assert "t" in df.columns


def test_parse_gpx_no_points_returns_empty(tmp_path) -> None:
    df = parse_gpx(_write(tmp_path, "empty.gpx", GPX_EMPTY))
    assert df.empty


def test_parse_tcx_returns_one_row_per_trackpoint(tmp_path) -> None:
    df = parse_tcx(_write(tmp_path, "b.tcx", TCX))
    assert not df.empty
    assert len(df) == 4
    assert "t" in df.columns


def test_parse_one_dispatches_by_extension(tmp_path) -> None:
    gpx = _write(tmp_path, "a.gpx", GPX)
    tcx = _write(tmp_path, "b.tcx", TCX)
    assert len(parse_one(gpx)) == 5
    assert len(parse_one(tcx)) == 4


def test_parse_one_rejects_unsupported_files(tmp_path) -> None:
    txt = _write(tmp_path, "notes.txt", "hello")
    with pytest.raises(ValueError):
        parse_one(txt)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))