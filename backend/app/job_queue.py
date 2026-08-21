"""Cola de procesamiento asíncrona con workers concurrentes.

Permite seguir cargando documentos mientras otros se procesan (no bloqueante).
Estados: queued, processing, ready, confirmed, failed. Reintentos individuales.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .capture_pipeline import process_document
from .job_store import JobStore, new_job_id, sanitize_name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobQueue:
    def __init__(self, store: JobStore, workers: int = 2):
        self.store = store
        self.workers = workers
        self._queue: Optional["asyncio.Queue[str]"] = None  # created on first start
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = False
        self._subscribers: List[asyncio.Queue] = []
        self._lock = threading.Lock()
        self._ready = threading.Event()

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

    def stop(self) -> None:
        self._stop = True
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # --- API pública (thread-safe) ---
    def enqueue(self, file_path: str, original_name: str, source: str = "web") -> str:
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
        }
        self.store.put(job)
        if self._loop and self._queue:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, job_id)
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
        if self._loop and self._queue:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, job_id)
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
        with self._lock:
            job["status"] = "processing"
            job["attempts"] = int(job.get("attempts", 0)) + 1
            job["updated_at"] = _now()
            self.store.put(job)
        self._notify({"job_id": job_id, "status": "processing"})
        try:
            file_path = job["file_path"]
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, process_document, file_path, job["original_name"])
            with self._lock:
                job["status"] = "ready"
                job["result"] = result
                job["updated_at"] = _now()
                self.store.put(job)
            self.store.save_original(job_id, result)
            self._notify({"job_id": job_id, "status": "ready"})
        except Exception as e:
            with self._lock:
                job["status"] = "failed"
                job["error"] = str(e)
                job["updated_at"] = _now()
                self.store.put(job)
            self._notify({"job_id": job_id, "status": "failed", "error": str(e)})


__all__ = ["JobQueue"]
