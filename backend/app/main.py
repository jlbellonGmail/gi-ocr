"""API FastAPI — Captura OCR Local Ágil.

Backend único (sin Node.js). Sirve API REST + SSE + frontend estático.
Endpoints de jobs (multi-entrada), confirmación, descarga, export, watcher inbound.
"""
from __future__ import annotations

import os

os.environ.setdefault("GI_OCR_ORT_THREADS", "3")

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ocr_engine
from .document_services import normalize_service_id
from .exif_privacy import anonymize_upload_bytes
from .fs_permissions import secure_dir, secure_file
from .inbound_watcher import SUPPORTED, InboundWatcher
from .job_queue import JobQueue
from .job_store import JOB_ID_RE, JobStore, sanitize_name
from .review_service import confirm_review
from .services_config import (
    ServiceNotFoundError,
    ServicesConfigError,
    get_service_schema,
    list_services_schema,
)
from .upload_validation import (
    UploadValidationError,
    max_upload_bytes,
    random_upload_name,
    validate_upload_content,
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "output"
INBOUND_DIR = BASE_DIR / "inbound"
FRONTEND_DIR = BASE_DIR / "frontend"

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}
MAX_BYTES = 30 * 1024 * 1024  # 30 MB, valor por defecto (ver upload_validation.max_upload_bytes)

store = JobStore(DATA_DIR)
queue = JobQueue(store, workers=2)
queue.start()
watcher = InboundWatcher(INBOUND_DIR, on_new=lambda p: queue.enqueue(str(p), p.name, source="inbound"))
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
    """Valida extensión (sin cambios) y tamaño máximo configurable
    (`GI_OCR_MAX_UPLOAD_BYTES`, ver `upload_validation.max_upload_bytes`).
    Devuelve el nombre sanitizado (sin path traversal). No valida firma de
    archivo ni Content-Type: eso lo hace `upload_validation.
    validate_upload_content` sobre el contenido real, en `_save_upload`."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Extensión no soportada: {ext}")
    limit = max_upload_bytes()
    if size > limit:
        raise HTTPException(413, f"Archivo demasiado grande (máx {limit} bytes)")
    return sanitize_name(filename)


def _save_upload(upload: UploadFile) -> Path:
    """Valida (extensión, tamaño, firma real, Content-Type declarado) y
    persiste el upload en `output/uploads/` con nombre aleatorio no
    predecible, tras anonimizar metadata EXIF identificatoria (JPEG/TIFF).

    Si cualquier validación falla, no queda ningún archivo nuevo en
    `output/uploads/` (la validación completa ocurre antes de escribir a
    disco)."""
    content = upload.file.read()
    filename = upload.filename or "doc"
    name = _validate_upload(filename, len(content))
    try:
        family = validate_upload_content(filename, content, upload.content_type)
    except UploadValidationError as e:
        raise HTTPException(status_code=e.status_code, detail={"reason": e.reason, "message": e.message})

    content = anonymize_upload_bytes(content, family)

    uploads = DATA_DIR / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    secure_dir(uploads)
    dest = uploads / random_upload_name(Path(name).suffix)
    dest.write_bytes(content)
    secure_file(dest)
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


@app.get("/api/v1/services")
async def list_services():
    """Lista de solo lectura de los servicios/documentos configurados en
    backend/config/services.ini, con su esquema validado (id, title,
    fields). No incluye datos de comprobantes ni requiere autenticación
    (config de solo lectura, ver docs/tecnica/administracion-servicios-documentos.md).
    """
    try:
        return {"services": list_services_schema()}
    except ServicesConfigError as e:
        raise HTTPException(500, str(e))


@app.get("/api/v1/services/{service_id}")
async def get_service(service_id: str):
    """Esquema validado de un único servicio (normaliza service_id igual
    que document_services.normalize_service_id: strip().upper())."""
    try:
        normalized = normalize_service_id(service_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        return get_service_schema(normalized)
    except ServiceNotFoundError as e:
        raise HTTPException(404, str(e))
    except ServicesConfigError as e:
        raise HTTPException(500, str(e))


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
    final_filename = doc.get("confirmation_metadata", {}).get("final_filename") or store.build_final_filename("doc", job_id)
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