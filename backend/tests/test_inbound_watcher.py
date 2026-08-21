"""Tests del watcher de carpeta inbound: dedupe y detección segura."""

import time

from backend.app.inbound_watcher import SUPPORTED, InboundWatcher, file_hash


def test_file_hash_stable(tmp_path):
    p = tmp_path / "a.jpg"
    p.write_bytes(b"hello")
    assert file_hash(p) == file_hash(p)


def test_watcher_dedupes_and_detects(tmp_path):
    seen = []
    w = InboundWatcher(tmp_path, on_new=lambda p: seen.append(p.name), poll_interval=0.2)
    # pre-colocar un archivo antes de start -> no se procesa (initial scan)
    (tmp_path / "old.jpg").write_bytes(b"old")
    w.start()
    try:
        # nuevo archivo después de start -> detectado
        time.sleep(0.3)
        (tmp_path / "new.png").write_bytes(b"newdata")
        deadline = time.time() + 3
        while time.time() < deadline and "new.png" not in seen:
            time.sleep(0.2)
        assert "new.png" in seen
        # old no debe haberse procesado (initial scan)
        assert "old.jpg" not in seen
        # dedupe: reescribir mismo nombre no vuelve a disparar
        (tmp_path / "new.png").write_bytes(b"changed")
        n = len(seen)
        time.sleep(0.6)
        assert len([s for s in seen if s == "new.png"]) == 1 or len(seen) == n
    finally:
        w.stop()


def test_supported_exts():
    for e in SUPPORTED:
        assert e.startswith(".")
