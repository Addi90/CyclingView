"""Shared fixtures for backend tests.

Tests must never touch the real ``data/`` directory: every fixture that needs
storage points the app's ``settings`` at a throwaway temp dir instead.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Point the app at a throwaway data dir (DB + Parquet streams)."""
    d = tmp_path / "data"
    d.mkdir()
    (d / "streams").mkdir()
    # settings.data_dir is a plain attribute; the db_path / streams_dir
    # properties derive from it, so patching it redirects everything.
    monkeypatch.setattr(settings, "data_dir", d)
    return d


@pytest.fixture()
def api_client(data_dir):
    """TestClient with startup events run (init_db) against the temp data dir."""
    from app.main import app

    with TestClient(app) as client:
        yield client