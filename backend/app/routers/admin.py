"""Admin endpoints: upload single ride file, trigger Strava bulk ingest, export/import data."""
from __future__ import annotations

import io
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import settings
from ..ingest import ingest as ingest_export
from ..ingest import ingest_uploaded_file
from ..services.power_bests import recompute_all as recompute_power_bests

router = APIRouter(prefix="/api")

ALLOWED_SUFFIXES = {".fit", ".tcx", ".gpx", ".gz"}


@router.post("/uploads")
async def upload_ride(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    bike_id: int | None = Form(default=None),
    activity_type: str = Form(default="Ride"),
    description: str | None = Form(default=None),
) -> dict[str, Any]:
    fname = file.filename or "upload.bin"
    suffixes = Path(fname).suffixes
    if not suffixes or suffixes[-1].lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported file extension: {fname}")

    # Persist upload to a temp file matching the original suffix(es), then ingest.
    suffix = "".join(suffixes)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        try:
            act_id = ingest_uploaded_file(
                tmp_path,
                name=name or Path(fname).stem,
                activity_type=activity_type,
                description=description,
                bike_id=bike_id,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(500, f"ingest failed: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)

    try:
        recompute_power_bests(force=False)
    except Exception:
        pass
    return {"activity_id": act_id, "name": name, "bike_id": bike_id}


class StravaIngestRequest(BaseModel):
    path: str | None = None  # absolute or relative to repo root
    force: bool = False


@router.post("/ingest/strava")
def ingest_strava(req: StravaIngestRequest) -> dict[str, Any]:
    raw = req.path or "export_105894778(1) 2"
    p = Path(raw)
    if not p.is_absolute():
        p = settings.repo_root / p
    if not p.exists() or not (p / "activities.csv").exists():
        raise HTTPException(404, f"Strava export not found at {p}")
    ok, skipped, failed = ingest_export(p, force=req.force)
    try:
        recompute_power_bests(force=False)
    except Exception:
        pass
    return {"ingested": ok, "skipped": skipped, "failed": failed, "path": str(p)}


# --- Export / Import ---------------------------------------------------------

EXPORT_INCLUDE_DIRS = ("streams", "uploads")
EXPORT_DB_NAME = "cycling.db"


@router.get("/export")
def export_data() -> StreamingResponse:
    """Stream a ZIP archive of the entire data/ directory (DB + streams + uploads)."""
    data_dir = settings.data_dir
    if not data_dir.exists():
        raise HTTPException(404, "data directory does not exist")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        db_path = data_dir / EXPORT_DB_NAME
        if db_path.exists():
            # Use SQLite backup API for a consistent snapshot.
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                src = sqlite3.connect(str(db_path))
                dst = sqlite3.connect(str(tmp_path))
                with dst:
                    src.backup(dst)
                src.close()
                dst.close()
                zf.write(tmp_path, EXPORT_DB_NAME)
            finally:
                tmp_path.unlink(missing_ok=True)

        for sub in EXPORT_INCLUDE_DIRS:
            d = data_dir / sub
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(data_dir))

    buf.seek(0)
    fname = f"cycling-view-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/import")
async def import_data(file: UploadFile = File(...), replace: bool = Form(default=False)) -> dict[str, Any]:
    """Restore a previously exported ZIP. Merges by default; pass replace=true to wipe first."""
    fname = file.filename or "import.zip"
    if not fname.lower().endswith(".zip"):
        raise HTTPException(400, "expected a .zip file")

    raw = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise HTTPException(400, "not a valid zip archive")

    names = zf.namelist()
    if not any(n == EXPORT_DB_NAME or n.endswith("/" + EXPORT_DB_NAME) for n in names):
        raise HTTPException(400, f"archive does not contain {EXPORT_DB_NAME}")

    # Reject path traversal.
    for n in names:
        norm = Path(n)
        if norm.is_absolute() or any(part == ".." for part in norm.parts):
            raise HTTPException(400, f"unsafe path in archive: {n}")

    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    if replace:
        for sub in (EXPORT_DB_NAME, *EXPORT_INCLUDE_DIRS):
            target = data_dir / sub
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()

    extracted = 0
    for n in names:
        if n.endswith("/"):
            continue
        target = data_dir / n
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(n) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)
        extracted += 1

    return {"extracted": extracted, "data_dir": str(data_dir), "replaced": replace}
