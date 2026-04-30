"""Compute per-ride summary metrics from a normalized stream DataFrame."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _has(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns and df[col].notna().any()


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(x)


def normalized_power(power: pd.Series, time: pd.Series) -> float | None:
    """Coggan's NP: 30s rolling mean ^ 4 -> mean -> 4th root."""
    p = power.copy().astype(float)
    if p.notna().sum() < 30:
        return None
    p = p.fillna(0.0)
    # Resample to 1Hz on the time axis to make rolling window meaningful.
    s = pd.Series(p.values, index=pd.to_datetime(time))
    s = s.resample("1s").mean().interpolate(limit=5).fillna(0.0)
    rolling = s.rolling("30s", min_periods=1).mean()
    if len(rolling) == 0:
        return None
    np_val = float(np.power(np.mean(np.power(rolling.values, 4)), 0.25))
    return _safe_float(np_val)


def elevation_gain(altitude: pd.Series) -> float | None:
    if altitude.notna().sum() < 2:
        return None
    # Smooth roughly with a rolling median to suppress sensor noise.
    a = altitude.astype(float).interpolate(limit=10)
    a = a.rolling(window=5, min_periods=1, center=True).median()
    diffs = a.diff().fillna(0.0)
    gain = float(diffs[diffs > 0].sum())
    return _safe_float(gain)


def summarize(df: pd.DataFrame) -> dict[str, float | int | None]:
    """Return a summary dict for an activity."""
    out: dict[str, Any] = {
        "point_count": int(len(df)),
        "has_geo": int(_has(df, "lat") and _has(df, "lon")),
        "has_power": int(_has(df, "power")),
        "has_hr": int(_has(df, "heart_rate")),
        "has_cadence": int(_has(df, "cadence")),
    }

    if "t" in df.columns and len(df) >= 2:
        elapsed = (df["t"].iloc[-1] - df["t"].iloc[0]).total_seconds()
        out["elapsed_s"] = _safe_float(elapsed)
    else:
        out["elapsed_s"] = None

    if _has(df, "distance"):
        d = df["distance"].dropna()
        out["distance_m"] = _safe_float(float(d.iloc[-1] - d.iloc[0]))
    else:
        out["distance_m"] = None

    if _has(df, "speed"):
        s = df["speed"].dropna()
        out["avg_speed_ms"] = _safe_float(s.mean())
        out["max_speed_ms"] = _safe_float(s.max())
        # Moving time: speed > 0.5 m/s (~1.8 km/h)
        if "t" in df.columns and len(df) >= 2:
            dt = df["t"].diff().dt.total_seconds().fillna(0.0)
            moving = float(dt[df["speed"].fillna(0) > 0.5].sum())
            out["moving_s"] = _safe_float(moving)
        else:
            out["moving_s"] = None
    else:
        out["avg_speed_ms"] = out["max_speed_ms"] = out["moving_s"] = None

    if _has(df, "heart_rate"):
        hr = df["heart_rate"].dropna()
        out["avg_hr"] = _safe_float(hr.mean())
        out["max_hr"] = _safe_float(hr.max())
    else:
        out["avg_hr"] = out["max_hr"] = None

    if _has(df, "power"):
        p = df["power"].dropna()
        out["avg_power"] = _safe_float(p.mean())
        out["max_power"] = _safe_float(p.max())
        if "t" in df.columns:
            out["np_power"] = normalized_power(df["power"], df["t"])
        else:
            out["np_power"] = None
    else:
        out["avg_power"] = out["max_power"] = out["np_power"] = None

    if _has(df, "cadence"):
        c = df["cadence"].dropna()
        out["avg_cadence"] = _safe_float(c.mean())
        out["max_cadence"] = _safe_float(c.max())
    else:
        out["avg_cadence"] = out["max_cadence"] = None

    if _has(df, "altitude"):
        a = df["altitude"].dropna()
        out["elevation_gain_m"] = elevation_gain(df["altitude"])
        out["elevation_low_m"] = _safe_float(a.min())
        out["elevation_high_m"] = _safe_float(a.max())
    else:
        out["elevation_gain_m"] = out["elevation_low_m"] = out["elevation_high_m"] = None

    if "temperature" in df.columns:
        t = df["temperature"].dropna()
        out["avg_temp"] = _safe_float(t.mean()) if len(t) else None
    else:
        out["avg_temp"] = None

    return out
