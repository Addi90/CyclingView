"""API tests for the stats router (aggregates and power-bests surfaces).

Endpoints are located through the app's OpenAPI schema so the tests survive
route renames. API-level recompute/leaderboard *behavior* is deliberately not
locked in here (route names vary); the numeric power-bests behavior is covered
by the unit tests for ``compute_bests_from_df``.
"""
from __future__ import annotations

import pytest

from app.services.power_bests import WINDOWS_S


def _openapi_paths(client) -> dict:
    return client.get("/openapi.json").json().get("paths", {})


def test_summary_reports_total_distance(seeded) -> None:
    # Totals may live under /stats itself or a dedicated route; try the likely
    # candidates and accept the first one that reports the seeded ride.
    for path in ("/api/stats/summary", "/api/stats", "/api/summary", "/api/stats/totals"):
        res = seeded.get(path)
        if res.status_code == 200 and "42000" in res.text:
            return
    pytest.fail("no stats endpoint reported the seeded ride's total distance")


def test_recompute_endpoint_registered(seeded) -> None:
    matches = [p for p in _openapi_paths(seeded) if "recompute" in p]
    assert matches, "expected a power-bests recompute route to be registered"


def test_power_bests_windows_list(seeded) -> None:
    candidates = [p for p in _openapi_paths(seeded) if "window" in p or "best" in p]
    for path in candidates:
        res = seeded.get(path)
        if res.status_code == 200 and "windows_s" in res.json():
            # Must match the canonical cycling windows from the service.
            assert res.json()["windows_s"] == list(WINDOWS_S)
            return
    pytest.fail(f"no endpoint returned the supported power windows: {candidates}")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))