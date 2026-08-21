"""API FastAPI — Captura OCR Local Ágil.

Backend único (sin Node.js). Sirve API REST + SSE + frontend estático.
Endpoints de jobs (multi-entrada), confirmación, descarga, export, watcher inbound.
"""

from __future__ import annotations

import os

os.environ.setdefault("GI_OCR_ORT_THREADS", "3")

import asyncio
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ocr_engine
from .inbound_watcher import InboundWatcher
from .job_queue import JobQueue
from .job_store import JOB_ID_RE, JobStore, sanitize_name
from .review_service import confirm_review

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "output"
INBOUND_DIR = BASE_DIR / "inbound"
FRONTEND_DIR = BASE_DIR / "frontend"

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}
MAX_BYTES = 30 * 1024 * 1024  # 30 MB

store = JobStore(DATA_DIR)
queue = JobQueue(store, workers=2)
queue.start()


def _on_new_inbound(p: Path) -> None:
    queue.enqueue(str(p), p.name, source="inbound")


watcher = InboundWatcher(INBOUND_DIR, on_new=_on_new_inbound)
watcher.start()

app = FastAPI(title="Captura OCR Local Ágil", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FieldCorrection(BaseModel):
    field: str
    state: str  # confirmed | corrected | unresolved
    final_value: Optional[str] = None


class ConfirmPayload(BaseModel):
    confirmed_fields: List[FieldCorrection]


def _validate_upload(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Extensión no soportada: {ext}")
    if size > MAX_BYTES:
        raise HTTPException(413, "Archivo demasiado grande (máx 30MB)")
    return sanitize_name(filename)


def _save_upload(upload: UploadFile) -> Path:
    content = upload.file.read()
    _validate_upload(upload.filename or "doc", len(content))
    name = sanitize_name(upload.filename or "doc")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(name).suffix)
    tmp.write(content)
    tmp.close()
    # mover a directorio de uploads persistente (output/uploads, gitignored)
    uploads = DATA_DIR / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    safe = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{name}"
    dest = uploads / safe
    shutil.move(tmp.name, dest)
    return dest


@app.on_event("startup")
async def _startup() -> None:
    # Cargar modelos OCR una sola vez (arranque en frío medible aparte en benchmark)
    ocr_engine.warmup()


@app.get("/api/v1")
async def root():
    return {"status": "ok", "app": "Captura OCR Local Ágil", "version": "2.0.0"}


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "engine_loaded": ocr_engine.get_engine() is not None,
        "queue_workers": queue.workers,
        "inbound": watcher.status(),
    }


@app.post("/api/v1/jobs")
async def create_jobs(files: List[UploadFile] = File(...)):
    """Carga uno o varios documentos. Crea jobs en cola (no bloqueante)."""
    if not files:
        raise HTTPException(400, "No se enviaron archivos")
    created = []
    for f in files:
        try:
            dest = _save_upload(f)
            job_id = queue.enqueue(str(dest), f.filename or dest.name, source="web")
            created.append({"job_id": job_id, "filename": f.filename})
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Error al guardar '{f.filename}': {e}")
    return {"created": created, "queued": len(created)}


@app.get("/api/v1/jobs")
async def list_jobs():
    return {"jobs": queue.status_list()}


@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    if not JOB_ID_RE.match(job_id):
        raise HTTPException(400, "job_id inválido")
    job = store.get(job_id)
    if not job and not store.original_exists(job_id):
        raise HTTPException(404, "Job no encontrado")
    if not job:
        job = {"job_id": job_id, "status": "ready"}
    confirmed = store.confirmed_exists(job_id)
    return {**job, "confirmed": confirmed}


@app.post("/api/v1/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    if not JOB_ID_RE.match(job_id):
        raise HTTPException(400, "job_id inválido")
    ok = queue.retry(job_id)
    if not ok:
        raise HTTPException(409, "No se Puede reintentar (no existe o ya listo)")
    return {"job_id": job_id, "status": "queued"}


@app.post("/api/v1/jobs/{job_id}/confirm")
async def confirm_job(job_id: str, payload: ConfirmPayload):
    if not JOB_ID_RE.match(job_id):
        raise HTTPException(400, "job_id inválido")
    if not store.original_exists(job_id):
        raise HTTPException(404, "Job no encontrado")
    try:
        result = confirm_review(store, job_id, [c.model_dump() for c in payload.confirmed_fields])
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return result


@app.get("/api/v1/jobs/{job_id}/download")
async def download_confirmed(job_id: str):
    if not JOB_ID_RE.match(job_id):
        raise HTTPException(400, "job_id inválido")
    if not store.original_exists(job_id):
        raise HTTPException(404, "Job no encontrado")
    if not store.confirmed_exists(job_id):
        raise HTTPException(409, "Resultado no confirmado. Confirme la revisión antes de descargar.")
    doc = store.load_confirmed(job_id)
    if doc is None:
        # Carrera improbable entre el chequeo confirmed_exists() y la
        # lectura: el archivo desapareció justo después de confirmarse.
        raise HTTPException(404, "Job no encontrado")
    final_filename = doc.get("confirmation_metadata", {}).get("final_filename") or store.build_final_filename(
        "doc", job_id
    )
    return FileResponse(str(store.confirmed_path(job_id)), media_type="application/json", filename=final_filename)


@app.get("/api/v1/jobs/{job_id}/original")
async def download_original(job_id: str):
    if not JOB_ID_RE.match(job_id):
        raise HTTPException(400, "job_id inválido")
    if not store.original_exists(job_id):
        raise HTTPException(404, "Resultado original no encontrado")
    return FileResponse(str(store.job_path(job_id)), media_type="application/json", filename=f"{job_id}_original.json")


@app.get("/api/v1/export")
async def export_batch():
    """Export del lote: JSON consolidado de resultados confirmados."""
    items = []
    for j in store.all():
        if store.confirmed_exists(j["job_id"]):
            c = store.load_confirmed(j["job_id"])
            items.append({"job_id": j["job_id"], **c.get("confirmed_fields", {})})
    payload = json.dumps({"batch": items, "count": len(items)}, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=batch_export.json"},
    )


@app.get("/api/v1/inbound/status")
async def inbound_status():
    return watcher.status()


@app.post("/api/v1/inbound/config")
async def inbound_config(payload: dict):
    # Por seguridad, la carpeta inbound es fija (no se permite path traversal).
    return {"status": "ok", "inbound_dir": str(INBOUND_DIR), "note": "carpeta fija por seguridad"}


@app.get("/api/v1/stream")
async def stream(request: Request):
    """SSE de progreso de la cola (no bloqueante)."""
    q = queue.subscribe()

    async def event_gen():
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                payload = await asyncio.wait_for(q.get(), timeout=15)
                yield f"data: {json.dumps(payload)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# Servir frontend después de las rutas API
if FRONTEND_DIR.exists():
    app.mount("", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
