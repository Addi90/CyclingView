"""M0 smoke test: harness, root tests/ layout, and fixtures are wired up."""
from __future__ import annotations


def test_health(api_client) -> None:
    res = api_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}