# Agents.md

## Project Overview
Local web app for exploring cycling data from Strava exports or individual activity files (TCX, GPX, FIT, JSON). FastAPI backend with SQLite metadata + Parquet per-ride streams. Svelte 4 frontend with uPlot charts and MapLibre GL maps.

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, SQLite (WAL mode), Parquet
- **Frontend**: Svelte 4 (Vite + TypeScript), uPlot, MapLibre GL, svelte-routing
- **Deployment**: Docker Compose (nginx reverse proxy for frontend)

## Development Workflow

### Backend
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e backend          # from repo root
uvicorn app.main:app --reload --port 8000   # cwd must be backend/
```

### Frontend (separate terminal)
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```
Vite proxies `/api` → `http://localhost:8000`. No CORS issues in dev.

### Docker
```bash
docker compose up --build        # UI: :8080, API: :8000
docker compose run --rm backend python -m app.ingest /export   # one-shot ingest
```

### Data Ingestion
- **CLI**: `python -m app.ingest "path/to/strava/export"` (from repo root, requires `cd backend` first or run as module)
- **API**: POST `/api/ingest/strava` with `{path, force}` or upload individual files via UI at `/import`
- **File formats**: `.fit`, `.tcx`, `.gpx`, `.gz` (compressed FIT)

## Architecture

### Backend (`backend/app/`)
- `main.py` — FastAPI app, CORS middleware, router registration, startup DB init
- `config.py` — Pydantic Settings with `CV_` env prefix + `.env` file. Data dir defaults to `<repo_root>/data/`. DB at `data/cycling.db`, streams at `data/streams/`
- `db.py` — SQLite schema (3 tables: `bikes`, `activities`, `power_bests`). Auto-creates on startup. WAL journal mode, foreign keys ON.
- `ingest.py` — CLI entry (`__main__`) + `ingest()` for Strava bulk, `ingest_uploaded_file()` for single files
- `routers/rides.py` — Ride listing, detail, streams, geo, edit, delete
- `routers/admin.py` — Uploads, Strava ingest endpoint, export/import, power bests recompute
- `routers/stats.py` — Overall statistics endpoint
- `services/` — Business logic (power bests computation)
- `parsers/` — Format-specific parsers (FIT via fitdecode, TCX/GPX via lxml)
- `summary.py` — Ride summary calculations

### Frontend (`frontend/src/`)
- 2 route pages: `RidesList.svelte`, `RideDetail.svelte` (client-side routing via svelte-routing)
- `lib/api.ts` — Typed API client, all fetch calls go through here
- `lib/charts/` — uPlot chart components with synchronized hover via Svelte stores (`hoverTime`)
- `lib/RouteMap.svelte` — MapLibre GL map with metric color coding, hover-synced to charts
- `lib/settings.ts` + `SettingsDialog.svelte` — User settings (MapLibre token, etc.)

### Data Storage
- SQLite: `data/cycling.db` — ride metadata, bikes, power bests
- Parquet: `data/streams/<activity_id>.parquet` — per-ride time-series (power, HR, speed, altitude, cadence, distance, temperature)
- Both directories are gitignored. Use `/api/export` and `/api/import` for portability.

## Key Gotchas
- **Power bests recompute** runs automatically after every upload/ingest (best-effort, exceptions silently caught)
- **Strava export path** defaults to `export_105894778(1) 2` directory — has spaces and parentheses in the name
- **Export uses SQLite backup API** for consistent snapshots, not file copy
- **Import merges by default**; pass `replace=true` to wipe existing data first
- **No tests exist yet** — pytest is a dev dependency but no test files are committed
- **`frontend/backend/`** is an empty stale directory — safe to ignore
