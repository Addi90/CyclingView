"""Stream loading + downsampling helpers."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import lttb
import numpy as np
import pandas as pd

from ..config import settings

# Stream fields the API can serve.
STREAM_FIELDS = ("power", "heart_rate", "speed", "altitude", "cadence", "distance", "temperature")


def _resolve(parquet_path: str | None, activity_id: int) -> Path:
    if parquet_path:
        candidate = settings.data_dir / parquet_path
        if candidate.exists():
            return candidate
    return settings.streams_dir / f"{activity_id}.parquet"


@lru_cache(maxsize=64)
def load_stream(activity_id: int, parquet_path: str | None = None) -> pd.DataFrame:
    p = _resolve(parquet_path, activity_id)
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_parquet(p)
    if "t" in df.columns:
        df["t"] = pd.to_datetime(df["t"], utc=True, errors="coerce")
    return df


def _to_relative_seconds(t: pd.Series) -> np.ndarray:
    if t.empty:
        return np.array([], dtype=np.float64)
    return (t - t.iloc[0]).dt.total_seconds().to_numpy(dtype=np.float64)


def downsample(
    df: pd.DataFrame, fields: list[str], n_points: int = 4000
) -> dict[str, list[float] | list[None]]:
    """Return a dict with `t` (seconds since start) and one array per field, all aligned."""
    if df.empty or "t" not in df.columns:
        return {"t": [], **{f: [] for f in fields}}

    t_rel = _to_relative_seconds(df["t"])
    n = len(df)

    # Pick the indices using LTTB on the first available field, otherwise uniform.
    pick_field = next((f for f in fields if f in df.columns and df[f].notna().any()), None)

    # n_points <= 0 means "no downsampling, return all points".
    if n_points <= 0 or n <= n_points or pick_field is None:
        idx = np.arange(n)
    else:
        y = df[pick_field].astype(float).to_numpy()
        # lttb requires no NaNs; fill with last valid then 0.
        y = pd.Series(y).ffill().bfill().fillna(0.0).to_numpy()
        data = np.column_stack([t_rel, y])
        sampled = lttb.downsample(data, n_out=n_points)
        # Map sampled t-values back to original indices via searchsorted.
        idx = np.searchsorted(t_rel, sampled[:, 0])
        idx = np.clip(idx, 0, n - 1)
        idx = np.unique(idx)

    out: dict[str, list[float] | list[None]] = {"t": t_rel[idx].tolist()}
    for f in fields:
        if f in df.columns:
            arr = df[f].to_numpy()[idx]
            # JSON-safe: convert NaN to None
            out[f] = [None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v) for v in arr]
        else:
            out[f] = [None] * len(idx)
    return out
