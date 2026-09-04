# PROJECT KNOWLEDGE BASE

**Generated:** 2026-09-02

## OVERVIEW
Project: **Cycling View**
Local web app for exploring cycling data from any source (Strava bulk export, TCX/GPX/FIT files, SQLite import/export).
Stack: Python 3.11+ (FastAPI, SQLite, Parquet via pandas/pyarrow) · Svelte 4 (Vite 5, TypeScript, uPlot, MapLibre GL) · Docker (nginx front) · pytest · GitHub Actions

## STRUCTURE
```
backend/app/
  main.py          FastAPI app factory, CORS, router registration, /api/health
  config.py        pydantic-settings (env prefix CV_, .env); repo_root + data_dir paths
  db.py            SQLite schema (bikes, activities, power_bests), WAL, FK ON, connect/get_conn
  ingest.py        Strava bulk export ingest + ingest_uploaded_file() for single files
  summary.py       Per-ride summary metrics (NP, elevation gain, etc.) from normalized DataFrame
  parsers/         fit.py / tcx.py / gpx.py → one normalized stream DataFrame each
  routers/         rides.py (rides+streams+geo), admin.py (upload/strava ingest/export/import),
                   stats.py (bike CRUD, /stats, power-bests endpoints)
  services/        streams.py (lru_cached parquet load + LTTB downsample),
                   power_bests.py (mean-max power, windows, leaderboards, recompute)
frontend/src/
  App.svelte       svelte-routing shell: header (desktop settings cog), mobile bottom tab bar
                   (Rides | + upload | Stats & Bests), floating settings gear FAB (mobile),
                   stats/bests BottomSheet (must stay inside <Router>)
  routes/          RidesList.svelte (dual layout: desktop table + aside filters / mobile cards
                   + toolbar + filter sheet; RangeSlider distance/duration filters, pagination
                   with mobile swipe-to-paginate (touch/mouse parallax + chevron arrow),
                   blur loading overlay), RideDetail.svelte
  lib/             api.ts (typed fetch client — single source of API truth), i18n.ts (de/en,
                   default de), settings.ts, upload.ts (writable counter that opens UploadDialog
                   from anywhere), BottomSheet.svelte (backdrop sheet: Esc / backdrop click /
                   gated swipe-down), RangeSlider.svelte (dual-knob, two overlapping native
                   range inputs), charts/StreamChart.svelte (synced uPlot), RouteMap.svelte,
                   StatsPanel.svelte, PowerBestsTable.svelte, SettingsDialog.svelte,
                   UploadDialog.svelte
tests/backend/     pytest suite mirroring app layout (parsers/, routers/, services/)
data/              GENERATED, gitignored: cycling.db + streams/*.parquet + uploads/
docker/            backend.Dockerfile (python:3.12-slim), frontend.Dockerfile (node→nginx), nginx.conf
docs/              feature plans (e.g. plan-multi-upload.md)
do                 bash dev entrypoint (test/ingest/serve/docker)
compose.yaml       docker compose: backend:8000, frontend:8080
```

## COMMANDS
| Action | Command |
|--------|---------|
| Install backend | `pip install -e 'backend[dev]'` (dev extras: pytest, httpx) |
| Install frontend | `cd frontend && npm install` |
| Test | `do test` (= `backend/.venv/bin/python -m pytest -q`) or `python -m pytest -q` |
| Serve API | `do serve [port]` (default 8000) |
| Frontend dev | `cd frontend && npm run dev` (5173, CORS-allowed origin) |
| Frontend type-check | `cd frontend && npm run check` (svelte-check) |
| Frontend build | `cd frontend && npm run build` |
| Ingest Strava export | `do ingest <export_dir>` or `python -m app.ingest <dir> --force` |
| Docker | `do docker` (UI :8080, API :8000); one-shot ingest: `docker compose run --rm backend python -m app.ingest /export` |

## CODING STANDARDS
*   **Language**: Python 3.11+ with `from __future__ import annotations`; raw `sqlite3` (no ORM) with `Row` factory; Pydantic models for request bodies; Svelte 4 syntax (`on:click`, `new App({ target })`), TypeScript interfaces.
*   **Style**: Routers grouped under `app/routers/` with `prefix="/api"`; services hold reusable computation (`services/streams.py`, `services/power_bests.py`); `@lru_cache` on parquet loads (must `cache_clear` on deletion — already done in the DELETE route); no frontend test framework (deliberate YAGNI); no linter/formatter configs committed.
*   **Data contract**: Parsers all emit the same normalized DataFrame: `t` (datetime, UTC), `lat`, `lon`, `power`, `heart_rate`, `speed`, `altitude`, `cadence`, `distance`, `temperature` (NaN for missing). `STREAM_FIELDS` in `services/streams.py` is the API-allowed field list.
*   **Tests**: `tests/backend/conftest.py` `data_dir` fixture monkeypatches `settings.data_dir` to a temp dir and clears the `load_stream` lru_cache. **Tests must never touch the real `data/` directory.** Router tests use `api_client` (TestClient with startup events).

## API SURFACE (summary)
- `GET /api/health`
- Bikes: `GET/POST /api/bikes`, `PATCH/DELETE /api/bikes/{id}` (delete refused while rides assigned)
- Rides: `GET /api/rides?bike_id&date_from&date_to&min_km&max_km&min_hours&max_hours&limit&offset` → `{total, items}` (`limit=0` = no limit); `GET /api/rides/bounds` → distance/duration min-max for filter sliders; `GET/PATCH/DELETE /api/rides/{id}` (bounds route must stay before `/{id}`)
- Streams: `GET /api/rides/{id}/streams?fields=a,b&n_points=0` (0 = all points; else LTTB)
- Geo: `GET /api/rides/{id}/geo` → GeoJSON LineString + parallel `streams` for color overlays
- Upload: `POST /api/uploads` (multipart: file, name, bike_id, activity_type, description)
- Admin: `POST /api/ingest/strava {path, force}`, `GET /api/export` (ZIP), `POST /api/import` (ZIP, replace)
- Stats: `GET /api/stats` (totals, longest, per_year, per_bike, unassigned)
- Power: `GET /api/power-bests/{id}`, `GET /api/power-bests?top_n=5`, `POST /api/power-bests/recompute?force`, `GET /api/power-bests/windows`

## WHERE TO LOOK
*   **Backend source**: `backend/app/`
*   **Tests**: `tests/backend/` (root `pytest.ini`: `testpaths=tests`, `pythonpath=. backend`)
*   **Frontend source**: `frontend/src/`
*   **Docs/plans**: `docs/`, `README.md`
*   **CI**: `.github/workflows/backend-tests.yml` (pytest on push/PR, Python 3.13)

## NOTES
*   **Responsive design**: one codebase; mobile ≤768px (bottom tab bar, settings FAB, bottom sheets, ride cards) vs desktop ≥769px (table + aside filters). Shared tokens live in `app.css` (`--bg/--panel/--panel-2/--border/--text/--muted/--accent`, `--touch` ≥44px, `--elev-*`); component styles are scoped. **No hardcoded colors — use the tokens.**
*   **Anything rendering `<Link>` must stay inside `<Router>`**: svelte-routing's Link dereferences router context and throws outside it (crashed the app-level stats sheet once; the sheet is mounted inside the Router on purpose).
*   `BottomSheet.svelte` closes on Escape, backdrop click, and swipe-down — the swipe is gated: sheet content scrolled to top AND finger not on `input/button/select/textarea/a/summary`.
*   Pagination convention: `limit=0` = no limit (rides API), same as `n_points=0` = all points (streams API); frontend per-page 25/50/100/0 ("All"). Keep the 0-means-all convention when adding new list endpoints.
*   Distance/duration filters (RangeSlider): bounds come from `GET /api/rides/bounds`; a knob parked on the domain edge sends **no** param (unfiltered); the list refetches on knob release, not per drag.
*   `lib/upload.ts` exports writable counter `uploadRequest`; bumping it opens UploadDialog (used by the mobile tab bar `+`).
*   svelte-check baseline: 3 pre-existing errors + 12 warnings (RouteMap GeoJSON typing) — don't chase; `npm run build` is the gate.
*   iOS Safari renders `input[type=date]` wider than its CSS box (segments + clear button scale with the text-size setting) — in the mobile filter sheet the date bar can sit flush to the sheet's right edge on some devices. Blind CSS fixes (grid `1fr`, `min-width: 0`, `fit-content`, `text-align: center`) were tried and reverted without resolving it; don't retry blind, get a real-device screenshot first.
*   Known contrast debt: `--muted` and `--accent` pass WCAG AA but fail APCA Lc 75 for small text; re-tuning the palette is a design decision, not a code fix.
*   **Two ID schemes**: Strava-ingested activities keep their real Strava `id`; uploaded files get an id of first trackpoint timestamp in **microseconds**. Upload source files are copied to `data/uploads/` as `{id}{suffixes}`; parquet to `data/streams/{id}.parquet`.
*   `estimated_power` flag = stream has power but Strava marked "Device Watts" false (estimated, not measured). UI surfaces it.
*   `config.py` defaults: `data_dir = <repo>/data`, `repo_root = <repo>/`; override with `CV_DATA_DIR` / `CV_REPO_ROOT` env vars (Docker does this). CORS origins are hardcoded to localhost:5173/8080.
*   The default Strava export dir is hardcoded in a few places as `export_105894778(1) 2` (user's export, gitignored).
*   Strava `activities.csv` has **duplicate column headers** — `ingest.iter_activities` uses `csv.reader` and takes the first occurrence of each wanted header on purpose (pandas silently renames duplicates).
*   Strava ingest skips non-ride activity types (`RIDE_TYPES` set in `ingest.py`) and is incremental (skips existing parquet unless `--force`); power bests are recomputed incrementally after ingest/upload.
*   Docker: nginx serves the SPA and proxies `/api/` → `backend:8000`; the Strava export is mounted read-only at `/export`.
*   Known doc drift: README says "Svelte 5" but `package.json` is Svelte 4 (all components use Svelte 4 APIs — don't "upgrade" syntax when editing).
*   i18n is German by default; add new user-facing strings to both `de` and `en` dictionaries in `lib/i18n.ts`.
*   `do` script assumes `backend/.venv`; it also reads backend/frontend logs into `.do/`.
*   `.opencode/` contains a separate OpenCode config (not part of the app).
