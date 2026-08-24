"""Unit tests for app.services.power_bests.compute_bests_from_df (no DB)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.power_bests import WINDOWS_S, compute_bests_from_df


def _df(seconds: int, power: float | None = 200.0, freq_s: float = 1.0) -> pd.DataFrame:
    # periods = seconds + 1 so the span covers exactly `seconds` seconds
    # (compute_bests_from_df skips windows longer than the last-first span).
    n = int(seconds / freq_s) + 1
    t = pd.date_range("2026-01-01 09:00:00+00:00", periods=n, freq=f"{int(freq_s * 1000)}ms")
    return pd.DataFrame({"t": t, "power": [power] * n})


def test_constant_series_gives_constant_best_for_all_fitting_windows() -> None:
    df = _df(600, power=300.0)  # exactly 10 minutes
    bests = compute_bests_from_df(df)
    for w in WINDOWS_S:
        if w <= 600:
            assert bests[w] == pytest.approx(300.0)
        else:
            assert w not in bests  # ride shorter than window


def test_short_ride_omits_longer_windows() -> None:
    bests = compute_bests_from_df(_df(50))
    assert 3 in bests
    assert 60 not in bests
    assert 300 not in bests


def test_missing_power_column_returns_empty() -> None:
    df = pd.DataFrame(
        {"t": pd.date_range("2026-01-01 00:00:00+00:00", periods=10, freq="s"), "heart_rate": 1.0}
    )
    assert compute_bests_from_df(df) == {}


def test_missing_t_column_returns_empty() -> None:
    assert compute_bests_from_df(pd.DataFrame({"power": [1.0, 2.0]})) == {}


def test_fewer_than_two_valid_samples_returns_empty() -> None:
    df = _df(10).assign(power=np.nan)
    assert compute_bests_from_df(df) == {}
    one_sample = _df(10).assign(power=np.nan)
    one_sample.loc[0, "power"] = 150.0
    assert compute_bests_from_df(one_sample) == {}


def test_window_best_tracks_local_spike() -> None:
    # 600s of 100W with a 30s stretch of 700W in the middle (601 samples):
    # the 30s window best must reflect the spike, the 600s best the low average.
    power = [100.0] * 601
    power[300:330] = [700.0] * 30
    df = _df(600).assign(power=power)
    bests = compute_bests_from_df(df)
    assert bests[30] == pytest.approx(700.0)
    # Every 600-sample rolling window holds all 30 spike samples:
    # 570 x 100W + 30 x 700W over a 600s window = 130.0 W exactly.
    assert bests[600] == pytest.approx((570 * 100.0 + 30 * 700.0) / 600.0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))