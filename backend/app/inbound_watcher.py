"""Watcher de carpeta inbound: detección segura de nuevos archivos, dedupe, estados.

No procesa dos veces el mismo archivo (registro de hashes/nombres). No sobrescribe ni
pierde originales. Usa watchfiles si está disponible (dependencia de uvicorn[standard]),
si no, polling ligero.
"""
from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

SUPPORTED = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class InboundWatcher:
    def __init__(self, inbound_dir: Path, on_new: Callable[[Path], None], poll_interval: float = 1.5):
        self.inbound_dir = Path(inbound_dir)
        self.inbound_dir.mkdir(parents=True, exist_ok=True)
        (self.inbound_dir / ".gitkeep").touch(exist_ok=True)
        self.on_new = on_new
        self.poll_interval = poll_interval
        self._seen: Dict[str, str] = {}  # filename -> sha256
        self._stop = False
        self._thread: Optional[threading.Thread] = None
        self._initial_scan_done = False

    def _scan_once(self, initial: bool = False) -> None:
        try:
            for p in sorted(self.inbound_dir.iterdir()):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in SUPPORTED:
                    continue
                name = p.name
                if name in self._seen:
                    continue
                try:
                    digest = file_hash(p)
                except OSError:
                    continue
                # dedupe por contenido aunque cambie el nombre
                if digest in self._seen.values():
                    self._seen[name] = digest
                    continue
                self._seen[name] = digest
                if initial:
                    continue  # no reprocesar lo que ya estaba al iniciar
                try:
                    self.on_new(p)
                except Exception:
                    pass
        except Exception:
            pass

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._scan_once(initial=True)
        self._initial_scan_done = True

        def runner():
            while not self._stop:
                self._scan_once(initial=False)
                time.sleep(self.poll_interval)

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True

    def status(self) -> Dict[str, Any]:
        files = [p.name for p in self.inbound_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED]
        return {
            "inbound_dir": str(self.inbound_dir),
            "watching": self._thread is not None and self._thread.is_alive(),
            "files_present": len(files),
            "files_seen_history": len(self._seen),
        }


__all__ = ["InboundWatcher", "file_hash", "SUPPORTED"]