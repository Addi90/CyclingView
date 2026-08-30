"""API tests for the admin upload endpoint (POST /api/uploads)."""
from __future__ import annotations

import datetime

import pytest


def _gpx(start: str, lat: float = 47.0, lon: float = 8.0, n: int = 60) -> bytes:
    """Minimal GPX: ``n`` trackpoints spaced 1s apart starting at ``start``."""
    base = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
    pts = []
    for i in range(n):
        t = base + datetime.timedelta(seconds=i)
        pts.append(
            f'<trkpt lat="{lat + i * 0.0001:.6f}" lon="{lon + i * 0.0001:.6f}">'
            f'<time>{t.strftime("%Y-%m-%dT%H:%M:%SZ")}</time><ele>{500 + i}</ele></trkpt>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">'
        f'<trk><trkseg>{"".join(pts)}</trkseg></trk></gpx>'
    ).encode()


def _empty_gpx() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
        "<trk><trkseg></trkseg></trk></gpx>"
    ).encode()


def _upload(client, fname: str, content: bytes, **form):
    data = {k: v for k, v in form.items() if v is not None}
    return client.post(
        "/api/uploads",
        data=data,
        files={"file": (fname, content, "application/gpx")},
    )


def _rides(client) -> list[dict]:
    return client.get("/api/rides", params={"limit": 100}).json()["items"]


def test_upload_with_name_and_bike(api_client) -> None:
    bike = api_client.post("/api/bikes", json={"name": "Test Bike"}).json()
    res = _upload(
        api_client, "a.gpx", _gpx("2026-05-01T09:00:00Z"),
        name="Morning", bike_id=str(bike["id"]),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Morning"
    assert body["bike_id"] == bike["id"]
    assert isinstance(body["activity_id"], int)

    ride = next(i for i in _rides(api_client) if i["id"] == body["activity_id"])
    assert ride["name"] == "Morning"
    assert ride["bike_name"] == "Test Bike"
    assert ride["bike_id"] == bike["id"]


def test_upload_without_bike(api_client) -> None:
    res = _upload(api_client, "b.gpx", _gpx("2026-05-02T09:00:00Z"), name="Evening")
    assert res.status_code == 200
    assert res.json()["bike_id"] is None

    ride = next(i for i in _rides(api_client) if i["id"] == res.json()["activity_id"])
    assert ride["name"] == "Evening"
    assert ride["bike_name"] is None
    assert ride["bike_id"] is None


def test_upload_defaults_name_to_filename_stem(api_client) -> None:
    res = _upload(api_client, "morning.gpx", _gpx("2026-05-03T09:00:00Z"))
    assert res.status_code == 200
    ride = next(i for i in _rides(api_client) if i["id"] == res.json()["activity_id"])
    # No name supplied -> the original filename stem is used.
    assert ride["name"] == "morning"


def test_upload_rejects_unsupported_extension(api_client) -> None:
    res = _upload(api_client, "notes.txt", b"definitely not a ride file")
    assert res.status_code == 400


def test_upload_rejects_file_without_trackpoints(api_client) -> None:
    res = _upload(api_client, "empty.gpx", _empty_gpx())
    assert res.status_code == 422


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))