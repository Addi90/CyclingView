"""Unit tests for app.services.streams.downsample (no DB, no files)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.streams import STREAM_FIELDS, downsample


def _df(n: int, with_nan: bool = False) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "t": pd.date_range("2026-01-01 09:00:00+00:00", periods=n, freq="s"),
            "power": np.arange(n, dtype=float),
            "heart_rate": np.full(n, 150.0),
        }
    )
    if with_nan:
        df.loc[[10, 20, 30], "power"] = np.nan
    return df


def test_empty_df_returns_empty_fields() -> None:
    out = downsample(pd.DataFrame(), ["power"])
    assert out == {"t": [], "power": []}


def test_missing_t_column_returns_empty() -> None:
    df = pd.DataFrame({"power": [1.0, 2.0, 3.0]})
    out = downsample(df, ["power"])
    assert out["t"] == []
    assert out["power"] == []


def test_small_series_untouched_and_t_relative() -> None:
    df = _df(10)
    out = downsample(df, ["power", "heart_rate"])
    assert len(out["t"]) == 10
    assert out["t"][0] == 0.0
    assert out["t"][-1] == 9.0
    assert out["power"] == [float(v) for v in df["power"]]
    assert out["heart_rate"] == [150.0] * 10


def test_zero_n_points_means_no_downsampling() -> None:
    df = _df(5000)
    out = downsample(df, ["power"], n_points=0)
    assert len(out["t"]) == 5000
    assert out["power"] == [float(v) for v in df["power"]]


def test_downsampled_output_bounded_and_aligned() -> None:
    df = _df(5000, with_nan=True)
    out = downsample(df, ["power"], n_points=100)
    assert len(out["t"]) <= 100
    # All field arrays align with t, and every value is JSON-safe (float|None).
    for field in ("t", "power"):
        assert len(out[field]) == len(out["t"])
        for v in out[field]:
            assert v is None or (isinstance(v, float) and np.isfinite(v))
    # t stays monotonically non-decreasing after LTTB sampling.
    assert all(b >= a for a, b in zip(out["t"], out["t"][1:]))


def test_missing_field_becomes_all_null() -> None:
    df = _df(10)
    out = downsample(df, list(STREAM_FIELDS))
    assert len(out["power"]) == 10
    for field in STREAM_FIELDS:
        if field not in df.columns:
            assert out[field] == [None] * 10


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))