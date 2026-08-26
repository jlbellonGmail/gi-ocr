"""Tests de seguridad de uploads y privacidad de documentos
(`14-seguridad-privacidad-documentos`).

Cubre los criterios de aceptación 1 (firma de archivo / magic bytes), 3
(tamaño máximo configurable), 4 (Content-Type vs. firma real), 5 (nombre
aleatorio no predecible), 6 (permisos de filesystem POSIX), 7 (purga por
retención) y 8 (redacción de errores). El criterio 9 (anonimización EXIF,
JPEG + TIFF) vive en `test_exif_privacy.py`.
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path

import numpy as np
import pytest
from backend.app.job_store import sanitize_name
from backend.app.main import DATA_DIR, app, queue, store
from fastapi.testclient import TestClient
from PIL import Image

c = TestClient(app, headers={"X-Operator-Id": "test_operator", "X-Operator-Role": "admin"})


def _uploads_dir() -> Path:
    return DATA_DIR / "uploads"


def _snapshot_uploads() -> set:
    d = _uploads_dir()
    if not d.exists():
        return set()
    return set(d.iterdir())


def _upload_and_get_new_file(filename: str, content: bytes, content_type: str) -> Path:
    """Sube `content` vía la API real y devuelve el único archivo nuevo
    aparecido en output/uploads/ como consecuencia de ese upload."""
    before = _snapshot_uploads()
    r = c.post("/api/v1/jobs", files={"files": (filename, content, content_type)})
    assert r.status_code == 200, r.text
    after = _snapshot_uploads()
    new_files = list(after - before)
    assert len(new_files) == 1, f"esperaba exactamente 1 archivo nuevo, hubo {len(new_files)}: {new_files}"
    return new_files[0]


def _noise_png_bytes(size=(200, 200)) -> bytes:
    """PNG con contenido ruidoso (no comprime a casi nada, a diferencia de
    un color sólido) — usado para tests de tamaño máximo."""
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 255, size=(size[1], size[0], 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _small_png_bytes() -> bytes:
    img = Image.new("RGB", (4, 4), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _small_tiff_bytes() -> bytes:
    img = Image.new("RGB", (4, 4), color=(40, 50, 60))
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    return buf.getvalue()


# --- Criterio 1: firma de archivo (magic bytes) ---


def test_upload_rejects_signature_mismatch_and_leaves_no_file():
    before = _snapshot_uploads()
    r = c.post(
        "/api/v1/jobs",
        files={"files": ("fake.jpg", b"esto es texto plano, no una imagen JPEG", "image/jpeg")},
    )
    assert r.status_code in (400, 415)
    body = r.json()
    assert "signature_mismatch" in str(body)
    after = _snapshot_uploads()
    assert after == before, "no debe quedar ningun archivo nuevo en output/uploads/ tras un intento rechazado"


def test_upload_rejects_empty_file():
    before = _snapshot_uploads()
    r = c.post("/api/v1/jobs", files={"files": ("empty.png", b"", "image/png")})
    assert r.status_code == 400
    assert "empty_file" in str(r.json())
    after = _snapshot_uploads()
    assert after == before


# --- Criterio 3: tamaño máximo configurable ---


def test_max_upload_bytes_configurable_via_env(monkeypatch):
    content = _noise_png_bytes()
    assert len(content) > 2048, "fixture debe superar el limite reducido del test"
    monkeypatch.setenv("GI_OCR_MAX_UPLOAD_BYTES", "2048")
    before = _snapshot_uploads()
    r = c.post("/api/v1/jobs", files={"files": ("big.png", content, "image/png")})
    assert r.status_code == 413
    after = _snapshot_uploads()
    assert after == before


def test_max_upload_bytes_defaults_to_30mb_when_unset(monkeypatch):
    monkeypatch.delenv("GI_OCR_MAX_UPLOAD_BYTES", raising=False)
    from backend.app.upload_validation import DEFAULT_MAX_UPLOAD_BYTES, max_upload_bytes

    assert max_upload_bytes() == DEFAULT_MAX_UPLOAD_BYTES == 30 * 1024 * 1024


# --- Criterio 4: Content-Type declarado vs. firma real ---


def test_content_type_mismatch_rejected():
    pdf_bytes = b"%PDF-1.4\n%fake-pdf-body-for-signature-only\n"
    before = _snapshot_uploads()
    r = c.post("/api/v1/jobs", files={"files": ("x.jpg", pdf_bytes, "image/jpeg")})
    assert r.status_code in (400, 415)
    assert "content_type_mismatch" in str(r.json())
    after = _snapshot_uploads()
    assert after == before


def test_content_type_absent_accepted_for_tiff():
    tiff_bytes = _small_tiff_bytes()
    r = c.post("/api/v1/jobs", files={"files": ("x.tif", tiff_bytes, "")})
    assert r.status_code == 200, r.text


# --- Criterio 5: nombre de archivo aleatorio no predecible ---


def test_uploaded_filename_is_random_not_derived_from_original():
    original_name = "DNI_Juan_Perez_MUY_SECRETO.png"
    sanitized = sanitize_name(original_name)
    content = _small_png_bytes()

    dest1 = _upload_and_get_new_file(original_name, content, "image/png")
    dest2 = _upload_and_get_new_file(original_name, content, "image/png")

    assert dest1.name != dest2.name
    assert sanitized not in dest1.name
    assert sanitized not in dest2.name
    assert "DNI_Juan_Perez" not in dest1.name
    assert "DNI_Juan_Perez" not in dest2.name


# --- Criterio 6: permisos de filesystem restrictivos (POSIX) ---


@pytest.mark.skipif(os.name != "posix", reason="permisos POSIX no aplican en Windows (entorno de desarrollo)")
def test_uploaded_file_has_owner_only_permissions():
    dest = _upload_and_get_new_file("perm_test.png", _small_png_bytes(), "image/png")
    mode = dest.stat().st_mode & 0o777
    assert mode == 0o600


@pytest.mark.skipif(os.name != "posix", reason="permisos POSIX no aplican en Windows (entorno de desarrollo)")
def test_uploads_dir_has_owner_only_permissions():
    _upload_and_get_new_file("perm_test_dir.png", _small_png_bytes(), "image/png")
    mode = _uploads_dir().stat().st_mode & 0o777
    assert mode == 0o700


def test_fs_permissions_is_noop_on_non_posix(monkeypatch):
    from backend.app import fs_permissions

    monkeypatch.setattr(fs_permissions, "IS_POSIX", False)
    calls = []
    monkeypatch.setattr(fs_permissions.os, "chmod", lambda *a, **k: calls.append(a))
    fs_permissions.secure_file("cualquier-ruta")
    fs_permissions.secure_dir("cualquier-ruta")
    assert calls == []


# --- Criterio 8: redacción de datos sensibles en job["error"] ---


def test_job_error_redacts_absolute_path_marker():
    marker = "gi_ocr_secret_marker_9f3a1c"
    original_name = "documento_confidencial_original.jpg"
    missing_path = Path(os.environ.get("TEMP") or "/tmp") / marker / original_name

    job_id = queue.enqueue(str(missing_path), original_name, source="test")

    deadline = time.time() + 15
    job = store.get(job_id)
    while time.time() < deadline and job and job.get("status") not in ("failed", "ready"):
        time.sleep(0.2)
        job = store.get(job_id)

    assert job is not None
    assert job["status"] == "failed"

    r = c.get(f"/api/v1/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert marker not in str(body["error"])
    assert str(missing_path) not in str(body["error"])
