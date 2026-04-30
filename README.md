# Cycling View

Local web app to explore your Strava cycling data (rides only).

- **Backend**: FastAPI + SQLite (metadata) + Parquet (per-ride streams)
- **Frontend**: Svelte (Vite + TypeScript) with synchronized uPlot charts
- **Data source**: a Strava bulk-export folder (default: `export_105894778(1) 2/`)

## Quick start

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend

# 2. Ingest your Strava export (one-time, idempotent)
python -m app.ingest "export_105894778(1) 2"

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

## Layout

```
backend/    FastAPI app + ingest CLI
frontend/   Svelte UI
docker/     Dockerfiles
data/       SQLite DB + per-ride Parquet streams (generated, gitignored)
```
