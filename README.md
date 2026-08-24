# Cycling View

Local web app for exploring cycling data from any source (Strava, TCX, GPX, JSON).

- **Backend**: FastAPI + SQLite (metadata) + Parquet (per-ride streams)
- **Frontend**: Svelte 5 (Vite + TypeScript) with synchronized uPlot charts and MapLibre GL maps
- **Data sources**: Strava bulk export, individual activity files (TCX/GPX/JSON), or SQLite database import/export

## Quick start

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend

# 2. Ingest data (pick one)
python -m app.ingest "path/to/strava/export"    # Strava bulk export
# Or upload individual files via the UI at /import

# 3. Run API
uvicorn app.main:app --reload --port 8000

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Or with Docker:

```bash
docker compose up --build
# UI:  http://localhost:8080
# API: http://localhost:8000
```

## Features

- **Multi-source ingestion** — Strava exports, individual TCX/GPX/JSON files, or full database import/export
- **Bike management** — Track multiple bikes with per-bike stats and ride assignment
- **Rich charts** — Synchronized time-series views (power, HR, speed, cadence, elevation, distance)
- **Interactive route map** — Color-coded routes by metric with hover synchronization
- **Power bests** — All-time best power outputs across standard time windows with leaderboards
- **Statistics** — Overall totals, per-year trends, per-bike breakdowns, longest ride tracking
- **Ride editing** — Edit name, type, description, and bike assignment directly in the UI

## Development

```bash
do help              # list commands
do test              # run the backend test suite (tests/backend/, pytest)
do serve [port]      # start the API (default port 8000)
do ingest <export>   # ingest a Strava bulk export
do docker            # docker compose up --build
```

Backend tests live in `tests/backend/` and are configured by the root `pytest.ini`
(the `do` script reuses `backend/.venv`). CI runs the same suite on every push/PR
(`.github/workflows/backend-tests.yml`). Tests never touch the real `data/`
directory.

## Layout

```
backend/    FastAPI app + ingest CLI
frontend/   Svelte UI
docker/     Dockerfiles
data/       SQLite DB + per-ride Parquet streams (generated, gitignored)
```
