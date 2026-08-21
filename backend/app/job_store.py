"""Almacén de jobs: estado en memoria + persistencia JSON en output/jobs y output/confirmed.

Mantiene resultados originales y confirmados separados. Nombres sanitizados.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_MAX_NAME = 120
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_name(name: str) -> str:
    """Sanitiza un nombre de archivo para prevenir path traversal."""
    base = Path(name).name
    safe = _UNSAFE.sub("_", base).strip("._")
    if len(safe) > _MAX_NAME:
        ext = Path(safe).suffix
        stem = safe[: _MAX_NAME - len(ext)]
        safe = stem + ext
    return safe[:_MAX_NAME] or "doc"


def new_job_id() -> str:
    return uuid.uuid4().hex


class JobStore:
    def __init__(self, base_dir: Path):
        self.base = Path(base_dir)
        self.jobs_dir = self.base / "jobs"
        self.confirmed_dir = self.base / "confirmed"
        self.inbound_dir = self.base / "inbound"
        for d in (self.jobs_dir, self.confirmed_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Dict[str, Any]] = {}

    # --- estado en memoria ---
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._state.get(job_id)

    def all(self) -> list:
        return list(self._state.values())

    def put(self, job: Dict[str, Any]) -> None:
        self._state[job["job_id"]] = job

    # --- nombre seguro ---
    def job_path(self, job_id: str) -> Path:
        if not JOB_ID_RE.match(job_id):
            raise ValueError("job_id inválido")
        return self.jobs_dir / f"{job_id}.json"

    def confirmed_path(self, job_id: str) -> Path:
        if not JOB_ID_RE.match(job_id):
            raise ValueError("job_id inválido")
        return self.confirmed_dir / f"{job_id}.confirmed.json"

    def original_exists(self, job_id: str) -> bool:
        try:
            return self.job_path(job_id).exists()
        except ValueError:
            return False

    def confirmed_exists(self, job_id: str) -> bool:
        try:
            return self.confirmed_path(job_id).exists()
        except ValueError:
            return False

    def save_original(self, job_id: str, result: Dict[str, Any]) -> None:
        path = self.job_path(job_id)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_original(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = self.job_path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_confirmed(self, job_id: str, doc: Dict[str, Any]) -> Path:
        path = self.confirmed_path(job_id)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_confirmed(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = self.confirmed_path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def build_final_filename(self, doc_type: str, job_id: str) -> str:
        prefix = sanitize_name(doc_type) or "doc"
        return f"{prefix}_{job_id[:8]}.json"


__all__ = ["JobStore", "sanitize_name", "new_job_id", "JOB_ID_RE"]
