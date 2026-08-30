# Plan — Multi-file drag-and-drop upload

Feature: upload multiple ride files (`.fit/.tcx/.gpx/.gz`) at once via drag-and-drop,
while keeping per-file **name** and **bike** editable.

## Core decision (lazy-but-correct)
**Frontend-only.** The backend `POST /api/uploads` already accepts a single file +
`name`/`bike_id` metadata, and `recompute_all(force=False)` is incremental (it skips
activities that already have bests), so calling the endpoint once per file in a loop is
cheap. **No new backend endpoint.** Only `UploadDialog.svelte`, `api.ts` (tiny),
`i18n.ts`, one new backend test, and the README change.

## Open design questions
1. **Per-row editable fields** — default: **name + bike only** (exactly the ask).
   Type + description stay editable *after* upload via the existing per-ride edit (no regression).
   *Alt:* add type/description per row (more clutter).
2. **Sequential vs parallel uploads** — default: **sequential** (`for…await`).
   Parallel would hit SQLite single-writer locks in the per-file recompute.
   *Alt:* parallel only if a batch endpoint is added.
3. **New batch endpoint?** — default: **none.** Only add `POST /api/uploads/batch`
   (single recompute, atomicity) if 50+ file uploads become routine.

---

## Milestones

### M0 — Branch setup
- `git checkout -b feat/multi-upload` from `master` (clean tree).

### M1 — Frontend: multi-file queue + drag-and-drop (core)
- Rework `UploadDialog.svelte` into a multi-file flow:
  - **Drop zone**: `on:dragover` (preventDefault) + `on:drop` (read `e.dataTransfer.files`);
    hidden `<input type="file" multiple>` for click-to-browse.
  - **Queue** of `{ file, name, bikeId }`; each row: filename (read-only) + **name**
    (pre-filled from filename) + **bike** (select) + remove button.
  - **Dedupe** by `name+size` so the same file isn't queued twice.
  - Accept filter `.fit,.tcx,.gpx,.gz`. A single drop = a one-row queue (single upload keeps working).
- Reuses `api.uploadRide` unchanged.

### M2 — Frontend: batch submit + per-file status
- Submit loops the queue **sequentially** → `api.uploadRide(row.file, { name, bike_id })`.
- Per-row status (`idle/uploading/done/error`) + overall progress; summary on finish
  (N uploaded, M failed).
- After completion → dispatch `uploaded` → `RidesList` reloads (existing).
- Optional: "clear all" + keep-failed affordances.

### M3 — i18n + polish
- New de + en keys: drop hint, "N files", per-row labels, statuses, errors, remove,
  clear-all, progress.
- Keyboard/focus: Escape closes, focus management, `aria` on drop zone + rows.

### M4 — Tests
- **Backend:** new `tests/backend/routers/test_admin.py` — upload a tiny GPX with
  `name` + `bike_id` via `POST /api/uploads`, assert `activity_id` returned and
  name + bike persisted (validates the exact call the frontend makes in a loop).
  *(Currently `/api/uploads` has no test coverage.)*
- **Frontend:** **no new test framework** (none exists; YAGNI) — the queue + loop is
  simple and covered by manual QA. *Alt:* add vitest if wanted.

### M5 — Documentation
- **README.md**: extend the upload/ingestion feature section to state multi-file
  drag-and-drop upload with per-file name + bike.
- Note any new manual-QA steps in the README.

### M6 — Commit strategy + handoff
Logical commits on `feat/multi-upload` (each a coherent unit):
1. `feat(upload): multi-file drag-and-drop queue with per-file name + bike` *(M1)*
2. `feat(upload): sequential batch submit with per-file status + progress` *(M2)*
3. `i18n(upload): de + en strings for multi-upload` *(M3)*
4. `test(upload): cover name + bike metadata on POST /api/uploads` *(M4)*
5. `docs: document multi-file upload` *(M5)*
- Then open a PR to `master` (or merge directly).

**Upgrade path (not built unless requested):** `POST /api/uploads/batch` endpoint for
atomicity + single recompute, if large batch uploads become common.