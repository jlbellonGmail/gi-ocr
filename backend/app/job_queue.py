"""Cola de procesamiento asíncrona con workers concurrentes.

Permite seguir cargando documentos mientras otros se procesan (no bloqueante).
Estados: queued, processing, ready, confirmed, failed, needs_new_photo
(rechazo del control de calidad de captura previo a OCR, feature
`06-calidad-captura-mobile`, ver `quality_gate.py`). Reintentos individuales.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .capture_pipeline import process_document
from .job_store import JobStore, new_job_id, sanitize_name
from .logging_config import get_logger, log_job_event
from .metrics import inc_jobs_total, set_queue_size
from .quality_gate import REJECTED_JOB_STATUS
from .redaction import redact_exception


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobQueue:
    def __init__(self, store: JobStore, workers: int = 2):
        self.store = store
        self.workers = workers
        self._queue: Optional["asyncio.Queue[str]"] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = False
        self._subscribers: List[asyncio.Queue] = []
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._logger = get_logger("job_queue")

    # --- loop interno en thread dedicado ---
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._queue = asyncio.Queue()
            self._ready.set()
            for _ in range(self.workers):
                loop.create_task(self._worker())
            loop.run_forever()

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=10)
        self._logger.info("job_queue_started", workers=self.workers)

    def stop(self) -> None:
        self._stop = True
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # --- API pública (thread-safe) ---
    def enqueue(
        self,
        file_path: str,
        original_name: str,
        source: str = "web",
        operator_id: Optional[str] = None,
        operator_role: Optional[str] = None,
    ) -> str:
        job_id = new_job_id()
        job = {
            "job_id": job_id,
            "file_path": file_path,
            "original_name": sanitize_name(original_name),
            "source": source,
            "status": "queued",
            "created_at": _now(),
            "updated_at": _now(),
            "result": None,
            "error": None,
            "attempts": 0,
            "operator_id": operator_id,
            "operator_role": operator_role,
        }
        self.store.put(job)
        inc_jobs_total("queued")
        set_queue_size(self._queue.qsize() if self._queue else 0)
        if self._loop and self._queue:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, job_id)
        self._logger.info("job_enqueued", job_id=job_id, source=source)
        return job_id

    def retry(self, job_id: str) -> bool:
        job = self.store.get(job_id)
        if not job:
            return False
        if job["status"] in ("ready", "confirmed"):
            return False
        job["status"] = "queued"
        job["error"] = None
        job["updated_at"] = _now()
        self.store.put(job)
        inc_jobs_total("queued")
        set_queue_size(self._queue.qsize() if self._queue else 0)
        if self._loop and self._queue:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, job_id)
        self._logger.info("job_retry", job_id=job_id)
        return True

    def status_list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(j) for j in self.store.all()]

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get(job_id)

    # --- SSE / suscripciones ---
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def _notify(self, payload: Dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    # --- worker ---
    async def _worker(self):
        while not self._stop:
            job_id = await self._queue.get()
            await self._process(job_id)

    async def _process(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if not job:
            return
        start_time = time.perf_counter()
        with self._lock:
            job["status"] = "processing"
            job["attempts"] = int(job.get("attempts", 0)) + 1
            job["updated_at"] = _now()
            self.store.put(job)
        inc_jobs_total("processing")
        set_queue_size(self._queue.qsize() if self._queue else 0)
        self._notify({"job_id": job_id, "status": "processing"})
        log_job_event(self._logger, "job_processing_started", job_id, "processing")
        try:
            file_path = job["file_path"]
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, process_document, file_path, file_path, job.get("operator_id"), job.get("operator_role")
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            quality = (result.get("processing_metadata") or {}).get("quality_gate") or {}
            if quality.get("verdict") == "reject":
                with self._lock:
                    job["status"] = REJECTED_JOB_STATUS
                    job["result"] = result
                    job["error"] = None
                    job["updated_at"] = _now()
                    self.store.put(job)
                inc_jobs_total("rejected")
                self._notify({"job_id": job_id, "status": REJECTED_JOB_STATUS})
                log_job_event(self._logger, "job_quality_rejected", job_id, "quality_gate", duration_ms=duration_ms)
            else:
                with self._lock:
                    job["status"] = "ready"
                    job["result"] = result
                    job["updated_at"] = _now()
                    self.store.put(job)
                self.store.save_original(job_id, result)
                inc_jobs_total("ready")
                self._notify({"job_id": job_id, "status": "ready"})
                log_job_event(self._logger, "job_completed", job_id, "processing", duration_ms=duration_ms)
        except Exception as e:
            safe_error = redact_exception(e)
            with self._lock:
                job["status"] = "failed"
                job["error"] = safe_error
                job["updated_at"] = _now()
                self.store.put(job)
            inc_jobs_total("failed")
            self._notify({"job_id": job_id, "status": "failed", "error": safe_error})
            log_job_event(self._logger, "job_failed", job_id, "processing", error=safe_error)
        finally:
            set_queue_size(self._queue.qsize() if self._queue else 0)
