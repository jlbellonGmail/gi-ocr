"""Tests de anonimización de metadata EXIF (criterio 9 de
`14-seguridad-privacidad-documentos`): JPEG y TIFF, eliminación de tags
identificatorios, preservación del tag Orientation y ausencia de
degradación de calidad/dimensiones.

Ejercita el flujo real de subida (`POST /api/v1/jobs` -> `output/uploads/`)
para validar la integración completa, no solo la función de anonimización
en aislamiento (esa cobertura unitaria vive igual, vía las mismas
aserciones sobre el archivo persistido).
"""

from __future__ import annotations

import io
from pathlib import Path

from backend.app.exif_privacy import anonymize_upload_bytes
from backend.app.main import DATA_DIR, app
from fastapi.testclient import TestClient
from PIL import Image

c = TestClient(app, headers={"X-Operator-Id": "test_operator", "X-Operator-Role": "admin"})

# Tags EXIF usados en las fixtures: Make(271), Model(272), Orientation(274), GPSInfo(34853).
_MAKE = 271
_MODEL = 272
_ORIENTATION = 274
_GPSINFO = 34853


def _uploads_dir() -> Path:
    return DATA_DIR / "uploads"


def _snapshot_uploads() -> set:
    d = _uploads_dir()
    if not d.exists():
        return set()
    return set(d.iterdir())


def _upload_and_get_new_file(filename: str, content: bytes, content_type: str) -> Path:
    before = _snapshot_uploads()
    r = c.post("/api/v1/jobs", files={"files": (filename, content, content_type)})
    assert r.status_code == 200, r.text
    after = _snapshot_uploads()
    new_files = list(after - before)
    assert len(new_files) == 1
    return new_files[0]


def _jpeg_with_exif(orientation: int = 6) -> bytes:
    img = Image.new("RGB", (64, 48), color=(120, 60, 200))
    exif = img.getexif()
    exif[_MAKE] = "TestCameraMake"
    exif[_MODEL] = "TestCameraModel"
    exif[_ORIENTATION] = orientation
    gps_ifd = exif.get_ifd(_GPSINFO)
    gps_ifd[1] = "N"
    gps_ifd[2] = (10, 0, 0)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif, quality=90)
    return buf.getvalue()


def _tiff_with_exif(orientation: int = 6) -> bytes:
    img = Image.new("RGB", (40, 20), color=(10, 20, 30))
    exif = img.getexif()
    exif[_MAKE] = "TiffCameraMake"
    exif[_MODEL] = "TiffCameraModel"
    exif[_ORIENTATION] = orientation
    gps_ifd = exif.get_ifd(_GPSINFO)
    gps_ifd[1] = "N"
    gps_ifd[2] = (10, 0, 0)
    buf = io.BytesIO()
    img.save(buf, format="TIFF", exif=exif)
    return buf.getvalue()


# --- JPEG ---


def test_exif_anonymization_jpeg_strips_identifying_tags_preserves_orientation():
    src_bytes = _jpeg_with_exif(orientation=6)
    dest = _upload_and_get_new_file("photo_with_exif.jpg", src_bytes, "image/jpeg")

    out_exif = Image.open(dest).getexif()
    assert out_exif.get(_ORIENTATION) == 6
    assert _MAKE not in out_exif
    assert _MODEL not in out_exif
    assert _GPSINFO not in out_exif


def test_exif_anonymization_jpeg_does_not_recompress_pixel_data():
    src_bytes = _jpeg_with_exif(orientation=6)
    src_quantization = Image.open(io.BytesIO(src_bytes)).quantization

    dest = _upload_and_get_new_file("photo_quality.jpg", src_bytes, "image/jpeg")
    out_quantization = Image.open(dest).quantization

    assert out_quantization == src_quantization


def test_exif_anonymization_jpeg_without_exif_is_noop():
    img = Image.new("RGB", (16, 16), color=(1, 2, 3))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    src_bytes = buf.getvalue()

    result = anonymize_upload_bytes(src_bytes, "jpeg")
    assert result == src_bytes


# --- TIFF ---


def test_exif_anonymization_tiff_strips_identifying_tags_preserves_orientation():
    src_bytes = _tiff_with_exif(orientation=6)
    dest = _upload_and_get_new_file("scan_with_exif.tiff", src_bytes, "image/tiff")

    out_exif = Image.open(dest).getexif()
    assert out_exif.get(_ORIENTATION) == 6
    assert _MAKE not in out_exif
    assert _MODEL not in out_exif
    assert _GPSINFO not in out_exif


def test_exif_anonymization_tiff_preserves_size_and_mode():
    src_bytes = _tiff_with_exif(orientation=6)
    src_img = Image.open(io.BytesIO(src_bytes))
    src_size, src_mode = src_img.size, src_img.mode

    dest = _upload_and_get_new_file("scan_dims.tiff", src_bytes, "image/tiff")
    out_img = Image.open(dest)

    assert out_img.size == src_size
    assert out_img.mode == src_mode


def test_exif_anonymization_tiff_without_exif_is_noop():
    img = Image.new("RGB", (16, 16), color=(4, 5, 6))
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    src_bytes = buf.getvalue()

    result = anonymize_upload_bytes(src_bytes, "tiff")
    assert result == src_bytes


# --- PNG/PDF: no aplica (no llevan bloque EXIF estándar) ---


def test_exif_anonymization_noop_for_png_and_pdf():
    png_bytes = b"\x89PNG\r\n\x1a\nnot-a-real-png-body"
    pdf_bytes = b"%PDF-1.4\nnot-a-real-pdf-body"
    assert anonymize_upload_bytes(png_bytes, "png") == png_bytes
    assert anonymize_upload_bytes(pdf_bytes, "pdf") == pdf_bytes


def test_exif_anonymization_corrupt_content_does_not_raise():
    # Firma TIFF válida pero cuerpo corrupto/truncado: no debe lanzar.
    garbage = b"II*\x00" + b"\x00" * 4
    result = anonymize_upload_bytes(garbage, "tiff")
    assert isinstance(result, bytes)

    garbage_jpeg = b"\xff\xd8\xff" + b"\x00" * 4
    result_jpeg = anonymize_upload_bytes(garbage_jpeg, "jpeg")
    assert isinstance(result_jpeg, bytes)
