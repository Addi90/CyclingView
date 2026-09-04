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


@pytest.fixture()
def seeded_bikes(api_client, data_dir):
    """One bike with a ride in 2024 and 2026, plus an unassigned 2026 ride."""
    from app.db import connect, init_db

    init_db()
    conn = connect()
    conn.execute("INSERT INTO bikes (id, name) VALUES (1, 'Test Bike')")
    for rid, start, dist in ((11, "2024-06-01T09:00:00Z", 10_000.0), (12, "2026-06-01T09:00:00Z", 20_000.0)):
        conn.execute(
            "INSERT INTO activities (id, start_time, name, type, bike_id, distance_m, moving_s) "
            "VALUES (?, ?, ?, 'Ride', 1, ?, 3600.0)",
            (rid, start, f"Bike ride {start[:4]}", dist),
        )
    conn.execute(
        "INSERT INTO activities (id, start_time, name, type, distance_m, moving_s) "
        "VALUES (13, '2026-07-01T09:00:00Z', 'No bike ride', 'Ride', 5000.0, 3600.0)"
    )
    conn.commit()
    conn.close()
    return api_client


def test_per_bike_all_time_and_year(seeded_bikes) -> None:
    all_time = seeded_bikes.get("/api/stats").json()
    bike = next(b for b in all_time["per_bike"] if b["bike_name"] == "Test Bike")
    assert bike["rides"] == 2
    assert bike["distance_m"] == 30_000.0

    for year, (rides, dist) in {2024: (1, 10_000.0), 2026: (1, 20_000.0)}.items():
        res = seeded_bikes.get(f"/api/stats?year={year}")
        assert res.status_code == 200
        bike = next(b for b in res.json()["per_bike"] if b["bike_name"] == "Test Bike")
        assert bike["rides"] == rides
        assert bike["distance_m"] == dist

    # Unassigned respects the year filter too; totals stay all-time.
    u24 = seeded_bikes.get("/api/stats?year=2024").json()["unassigned"]
    u26 = seeded_bikes.get("/api/stats?year=2026").json()["unassigned"]
    assert u24["rides"] == 0
    assert u26["rides"] == 1  # the unassigned 2026 ride
    assert seeded_bikes.get("/api/stats?year=2024").json()["totals"]["rides"] == 3

    res = seeded_bikes.get("/api/stats?year=1899")
    assert res.status_code == 400


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))