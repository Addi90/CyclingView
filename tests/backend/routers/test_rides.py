"""API tests for the rides router (list, detail, streams, update, 404s)."""
from __future__ import annotations

import pytest

from tests.backend.routers.conftest import ACTIVITY_ID


def test_rides_list_contains_seeded_ride(seeded) -> None:
    res = seeded.get(f"/api/rides")
    assert res.status_code == 200
    assert "Morning Ride" in res.text


def test_rides_filter_by_distance_and_duration(seeded) -> None:
    # Seeded ride: 42 km, 5200 s (~1.44 h) moving.
    res = seeded.get("/api/rides?min_km=40&max_km=50&min_hours=1&max_hours=2")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    # Out of range on either dimension excludes it.
    assert seeded.get("/api/rides?min_km=50").json()["total"] == 0
    assert seeded.get("/api/rides?max_km=40").json()["total"] == 0
    assert seeded.get("/api/rides?min_hours=2").json()["total"] == 0
    assert seeded.get("/api/rides?max_hours=1").json()["total"] == 0


def test_rides_bounds(seeded) -> None:
    res = seeded.get("/api/rides/bounds")
    assert res.status_code == 200
    body = res.json()
    assert body["distance_m"] == pytest.approx([42_000.0, 42_000.0])
    assert body["moving_s"] == pytest.approx([5_200.0, 5_200.0])


def test_rides_pagination(seeded) -> None:
    from app.db import connect

    conn = connect()
    conn.execute(
        "INSERT INTO activities (id, start_time, name, distance_m, moving_s) "
        "VALUES (2, '2026-05-02T09:00:00Z', 'Second', 10000.0, 3600.0)"
    )
    conn.commit()
    conn.close()

    body = seeded.get("/api/rides", params={"limit": 1, "offset": 0}).json()
    assert body["total"] == 2
    assert [r["id"] for r in body["items"]] == [2]  # start_time DESC
    body = seeded.get("/api/rides", params={"limit": 1, "offset": 1}).json()
    assert [r["id"] for r in body["items"]] == [1]
    # limit=0 means no limit.
    assert len(seeded.get("/api/rides", params={"limit": 0}).json()["items"]) == 2
    # Offset past the end returns an empty page.
    assert seeded.get("/api/rides", params={"limit": 1, "offset": 2}).json()["items"] == []


def test_ride_detail(seeded) -> None:
    res = seeded.get(f"/api/rides/{ACTIVITY_ID}")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Morning Ride"
    assert body["distance_m"] == pytest.approx(42_000.0)
    assert body["avg_power"] == pytest.approx(250.0)


def test_ride_detail_missing_is_404(seeded) -> None:
    assert seeded.get("/api/rides/999").status_code == 404


def _field_arrays(body: dict) -> dict:
    """Field arrays live either under a `streams` key or at the top level."""
    return body["streams"] if "streams" in body else body


def test_ride_streams_downsampled(seeded) -> None:
    res = seeded.get(
        f"/api/rides/{ACTIVITY_ID}/streams",
        params={"fields": "power,heart_rate", "n_points": 100},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["activity_id"] == ACTIVITY_ID
    # t is relative to ride start; every field array aligns with it.
    assert body["t"][0] == 0.0
    assert len(body["t"]) <= 100
    fields = _field_arrays(body)
    for field in ("power", "heart_rate"):
        assert len(fields[field]) == len(body["t"])
    # Constant 250W / 150bpm in the fixture must survive downsampling.
    assert fields["power"][0] == pytest.approx(250.0)
    assert fields["heart_rate"][0] == pytest.approx(150.0)


def test_update_ride(seeded) -> None:
    res = seeded.patch(
        f"/api/rides/{ACTIVITY_ID}",
        json={"name": "Evening Ride", "description": "renamed"},
    )
    assert res.status_code == 200
    detail = seeded.get(f"/api/rides/{ACTIVITY_ID}").json()
    assert detail["name"] == "Evening Ride"
    assert detail["description"] == "renamed"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))