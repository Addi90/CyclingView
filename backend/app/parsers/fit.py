"""Parse Garmin .fit files into a normalized DataFrame.

Output columns (any may be all-NaN if absent in the file):
    t            datetime64[ns, UTC]   timestamp
    lat, lon     float64               degrees (semicircles converted)
    altitude     float64               meters
    distance     float64               meters from start
    speed        float64               m/s
    power        float64               watts
    heart_rate   float64               bpm
    cadence      float64               rpm
    temperature  float64               degrees C
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import IO, Any

import fitdecode
import pandas as pd

_SEMI_TO_DEG = 180.0 / 2**31

_FIELD_MAP = {
    "timestamp": "t",
    "position_lat": "lat",
    "position_long": "lon",
    "altitude": "altitude",
    "enhanced_altitude": "altitude",
    "distance": "distance",
    "speed": "speed",
    "enhanced_speed": "speed",
    "power": "power",
    "heart_rate": "heart_rate",
    "cadence": "cadence",
    "temperature": "temperature",
}


def _open(path: Path) -> IO[bytes]:
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def parse_fit(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with _open(path) as fh, fitdecode.FitReader(fh) as reader:
        for frame in reader:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            if frame.name != "record":
                continue
            row: dict[str, Any] = {}
            for field in frame.fields:
                key = _FIELD_MAP.get(field.name)
                if key is None:
                    continue
                val = field.value
                if val is None:
                    continue
                if key in ("lat", "lon") and isinstance(val, (int, float)):
                    # Some files store semicircles; fitdecode usually converts.
                    # If the magnitude is huge, treat as semicircles.
                    if abs(val) > 180:
                        val = val * _SEMI_TO_DEG
                row[key] = val
            if row:
                rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "t" in df.columns:
        df["t"] = pd.to_datetime(df["t"], utc=True, errors="coerce")
        df = df.dropna(subset=["t"]).sort_values("t").reset_index(drop=True)
    # Coerce numeric columns
    for col in df.columns:
        if col == "t":
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
