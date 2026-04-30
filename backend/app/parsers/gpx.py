"""Parse GPX files into the same normalized DataFrame as the .fit/.tcx parsers.

Supports common power/HR/cadence extensions (Garmin TrackPointExtension and
power namespaces).
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import IO

import pandas as pd
from lxml import etree

NS = {
    "gpx": "http://www.topografix.com/GPX/1/1",
    "gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
    "gpxtpx2": "http://www.garmin.com/xmlschemas/TrackPointExtension/v2",
    "gpxpx": "http://www.garmin.com/xmlschemas/PowerExtension/v1",
}


def _open(path: Path) -> IO[bytes]:
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def _txt(node, xpath: str) -> str | None:
    res = node.find(xpath, NS)
    return res.text if res is not None and res.text is not None else None


def _local_text(parent, local_name: str) -> str | None:
    """Find first direct/descendant child by local name, ignoring namespace."""
    for el in parent.iter():
        if etree.QName(el).localname == local_name and el.text is not None:
            return el.text
    return None


def parse_gpx(path: Path) -> pd.DataFrame:
    with _open(path) as fh:
        data = fh.read()
    data = data.lstrip().lstrip(b"\xef\xbb\xbf")
    root = etree.fromstring(data)

    # Find trkpt by local-name so we work whether the GPX namespace is
    # declared as the default xmlns or not (Sauce/Strava omit it).
    trkpts = [el for el in root.iter() if etree.QName(el).localname == "trkpt"]

    rows = []
    for tp in trkpts:
        row: dict[str, str | float] = {}
        lat = tp.get("lat")
        lon = tp.get("lon")
        if lat is not None:
            row["lat"] = lat
        if lon is not None:
            row["lon"] = lon
        # Core fields by local-name (namespace-agnostic).
        # Look only at direct children to avoid grabbing extensions/<time>.
        for child in tp:
            ln = etree.QName(child).localname
            if ln == "time" and child.text:
                row["t"] = child.text
            elif ln == "ele" and child.text:
                row["altitude"] = child.text

        # Extensions: HR, cadence, temperature, power
        for ext_xpath in (
            ".//gpxtpx:hr",
            ".//gpxtpx2:hr",
        ):
            v = _txt(tp, ext_xpath)
            if v is not None:
                row["heart_rate"] = v
                break
        else:
            v = _local_text(tp, "hr")
            if v is not None:
                row["heart_rate"] = v
        for ext_xpath in (
            ".//gpxtpx:cad",
            ".//gpxtpx2:cad",
        ):
            v = _txt(tp, ext_xpath)
            if v is not None:
                row["cadence"] = v
                break
        else:
            v = _local_text(tp, "cad")
            if v is not None:
                row["cadence"] = v
        for ext_xpath in (
            ".//gpxtpx:atemp",
            ".//gpxtpx2:atemp",
        ):
            v = _txt(tp, ext_xpath)
            if v is not None:
                row["temperature"] = v
                break
        else:
            v = _local_text(tp, "atemp")
            if v is not None:
                row["temperature"] = v
        # Power can live under PowerExtension or as a plain <power> element.
        v = _txt(tp, ".//gpxpx:PowerInWatts")
        if v is None:
            # Fallback: any element whose local-name == 'power'
            for el in tp.iter():
                if etree.QName(el).localname.lower() == "power" and el.text:
                    v = el.text
                    break
        if v is not None:
            row["power"] = v

        if "t" in row:
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

    # GPX has no cumulative distance — derive from lat/lon if present.
    if "distance" not in df.columns and {"lat", "lon"}.issubset(df.columns):
        import numpy as np
        lat = np.deg2rad(df["lat"].to_numpy())
        lon = np.deg2rad(df["lon"].to_numpy())
        dlat = np.diff(lat)
        dlon = np.diff(lon)
        a = np.sin(dlat / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2) ** 2
        d = 2 * 6371000.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        cum = np.concatenate([[0.0], np.cumsum(d)])
        df["distance"] = cum

    # Derive speed from distance/time if missing.
    if "speed" not in df.columns and "distance" in df.columns:
        dt = df["t"].diff().dt.total_seconds().to_numpy()
        dd = df["distance"].diff().to_numpy()
        with __import__("numpy").errstate(divide="ignore", invalid="ignore"):
            speed = dd / dt
        df["speed"] = speed

    return df
