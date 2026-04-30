"""Parse Garmin .tcx files into the same normalized DataFrame as the .fit parser."""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import IO

import pandas as pd
from lxml import etree

NS = {
    "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "tpx": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
}


def _open(path: Path) -> IO[bytes]:
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def _txt(node, xpath: str) -> str | None:
    res = node.find(xpath, NS)
    return res.text if res is not None and res.text is not None else None


def parse_tcx(path: Path) -> pd.DataFrame:
    with _open(path) as fh:
        data = fh.read()
    # Some Strava-exported TCX files have leading whitespace / BOM before the XML decl.
    data = data.lstrip().lstrip(b"\xef\xbb\xbf")
    root = etree.fromstring(data)

    rows = []
    for tp in root.iterfind(".//tcx:Trackpoint", NS):
        row: dict[str, float | str] = {}
        t = _txt(tp, "tcx:Time")
        if t is None:
            continue
        row["t"] = t
        lat = _txt(tp, "tcx:Position/tcx:LatitudeDegrees")
        lon = _txt(tp, "tcx:Position/tcx:LongitudeDegrees")
        if lat is not None:
            row["lat"] = lat
        if lon is not None:
            row["lon"] = lon
        alt = _txt(tp, "tcx:AltitudeMeters")
        if alt is not None:
            row["altitude"] = alt
        dist = _txt(tp, "tcx:DistanceMeters")
        if dist is not None:
            row["distance"] = dist
        hr = _txt(tp, "tcx:HeartRateBpm/tcx:Value")
        if hr is not None:
            row["heart_rate"] = hr
        cad = _txt(tp, "tcx:Cadence")
        if cad is not None:
            row["cadence"] = cad
        # Extensions: speed, watts, sometimes cadence
        ext_speed = _txt(tp, "tcx:Extensions/tpx:TPX/tpx:Speed")
        if ext_speed is not None:
            row["speed"] = ext_speed
        watts = _txt(tp, "tcx:Extensions/tpx:TPX/tpx:Watts")
        if watts is not None:
            row["power"] = watts
        ext_cad = _txt(tp, "tcx:Extensions/tpx:TPX/tpx:RunCadence")
        if ext_cad is not None and "cadence" not in row:
            row["cadence"] = ext_cad
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"], utc=True, errors="coerce")
    df = df.dropna(subset=["t"]).sort_values("t").reset_index(drop=True)
    for col in df.columns:
        if col == "t":
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
