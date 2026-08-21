"""Tests de corrección de orientación EXIF (feature 05-correccion-orientacion-exif).

Cubre:
- Los 8 valores estándar de EXIF `Orientation` (1-8) sobre imágenes sintéticas
  con contenido asimétrico verificable por código.
- Casos borde: sin EXIF, EXIF sin tag `Orientation`, `Orientation` corrupto o
  fuera de rango (0, 9, no numérico).
- Subordinación de la heurística `image_prep.correct_orientation` cuando ya se
  aplicó una corrección EXIF válida (sin regresión cuando no la hay).
- Integración end-to-end: `capture_pipeline.process_document` sobre una imagen
  con texto renderizado y EXIF `Orientation=6`/`8`, verificando que RapidOCR
  devuelve texto reconocible.

Todas las imágenes usadas son 100% sintéticas, generadas en memoria con PIL/
OpenCV. No se versionan fotos reales de celular.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from backend.app import image_prep
from backend.app.capture_pipeline import process_document

ORIENTATION_TAG = 0x0112  # 274, EXIF "Orientation"

# Transformación PIL que, aplicada a la imagen canónica (orientación 1), produce
# los píxeles "crudos" tal como quedarían almacenados por una cámara/celular que
# etiquetó la foto con ese valor de Orientation. Es la tabla inversa exacta de la
# que usa internamente `PIL.ImageOps.exif_transpose` (verificado empíricamente:
# `exif_transpose(raw)` reproduce el array canónico para los 8 valores).
_RAW_TRANSFORM_FOR_ORIENTATION = {
    1: None,
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_90,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_270,
}


def _make_canonical_marker_image() -> Image.Image:
    """Imagen 40x60 (no cuadrada) con un marcador rojo asimétrico en la esquina
    superior izquierda, sobre fondo gris oscuro. Sirve como "orientación 1"."""
    img = Image.new("RGB", (40, 60), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 9, 9], fill=(255, 0, 0))
    return img


def _make_raw_for_orientation(canonical: Image.Image, orientation: int) -> Image.Image:
    """Construye la imagen "cruda" (como la guardaría la cámara) para un valor
    de EXIF Orientation dado, y le setea el tag correspondiente."""
    method = _RAW_TRANSFORM_FOR_ORIENTATION[orientation]
    raw = canonical if method is None else canonical.transpose(method)
    exif = raw.getexif()
    exif[ORIENTATION_TAG] = orientation
    return raw


@pytest.mark.parametrize("orientation", [1, 2, 3, 4, 5, 6, 7, 8])
def test_apply_exif_orientation_all_8_values(orientation):
    """Para cada valor estándar 1-8, la corrección debe reproducir exactamente
    la imagen canónica (marcador rojo en la esquina superior izquierda)."""
    canonical = _make_canonical_marker_image()
    canonical_arr = np.array(canonical)
    raw = _make_raw_for_orientation(canonical, orientation)

    corrected, applied = image_prep.apply_exif_orientation(raw)
    corrected_arr = np.array(corrected.convert("RGB"))

    assert np.array_equal(corrected_arr, canonical_arr), (
        f"orientation={orientation} no reprodujo la imagen canónica"
    )
    # El marcador debe seguir en la esquina superior izquierda (0..9, 0..9).
    assert tuple(corrected_arr[0, 0]) == (255, 0, 0)
    if orientation == 1:
        assert applied is False
    else:
        assert applied is True


def test_no_exif_at_all():
    """Imagen sin ningún bloque EXIF: no debe alterarse ni romper el pipeline."""
    img = Image.new("RGB", (40, 60), (10, 10, 10))
    before = np.array(img)

    corrected, applied = image_prep.apply_exif_orientation(img)

    assert applied is False
    assert np.array_equal(np.array(corrected.convert("RGB")), before)


def test_exif_present_but_no_orientation_tag():
    """Imagen con EXIF presente pero sin el tag Orientation (274)."""
    img = Image.new("RGB", (40, 60), (10, 10, 10))
    exif = img.getexif()
    exif[0x0132] = "2024:01:01 00:00:00"  # DateTime, no Orientation
    before = np.array(img)

    corrected, applied = image_prep.apply_exif_orientation(img)

    assert applied is False
    assert np.array_equal(np.array(corrected.convert("RGB")), before)


@pytest.mark.parametrize("bad_value", [0, 9, -1, 100])
def test_orientation_out_of_range_degrades_gracefully(bad_value):
    """Orientation fuera del rango válido (1-8): no debe romper el pipeline y
    debe tratarse como si no hubiera tag utilizable (sin transformación)."""
    canonical = _make_canonical_marker_image()
    before = np.array(canonical)
    img = canonical.copy()
    exif = img.getexif()
    exif[ORIENTATION_TAG] = bad_value

    corrected, applied = image_prep.apply_exif_orientation(img)

    assert applied is False
    assert np.array_equal(np.array(corrected.convert("RGB")), before)


def test_orientation_non_numeric_degrades_gracefully():
    """Orientation con valor no numérico (EXIF corrupto): no debe lanzar
    excepción, se trata como si no hubiera tag utilizable."""
    canonical = _make_canonical_marker_image()
    img = canonical.copy()
    exif = img.getexif()
    exif[ORIENTATION_TAG] = "not-a-number"

    corrected, applied = image_prep.apply_exif_orientation(img)

    assert applied is False
    assert corrected is not None


def test_correct_orientation_skip_true_bypasses_heuristic():
    """Cuando exif_orientation_applied=True (subordinación), la heurística de
    contenido `correct_orientation` no debe ejecutarse: una imagen que la
    heurística normalmente rotaría queda intacta con skip=True."""
    import cv2

    # Imagen alta (h>w) con líneas verticales fuertes: dispara la heurística
    # de rotación bajo comportamiento normal (skip=False/no aplicado).
    img = np.full((600, 300, 3), 255, dtype=np.uint8)
    for x in range(0, 300, 10):
        cv2.line(img, (x, 0), (x, 600), (0, 0, 0), 2)

    rotated = image_prep.correct_orientation(img, skip=False)
    unchanged = image_prep.correct_orientation(img, skip=True)

    assert rotated.shape[:2] != img.shape[:2], "la heurística debía rotar la imagen sin skip"
    assert unchanged.shape[:2] == img.shape[:2], "con skip=True no debe rotar"
    assert np.array_equal(unchanged, image_prep.to_rgb(img))


def test_correct_orientation_no_regression_without_exif():
    """Sin corrección EXIF (comportamiento por defecto/legacy), la heurística
    de contenido sigue funcionando exactamente igual que antes."""
    import cv2

    img = np.full((600, 300, 3), 255, dtype=np.uint8)
    for x in range(0, 300, 10):
        cv2.line(img, (x, 0), (x, 600), (0, 0, 0), 2)

    default_call = image_prep.correct_orientation(img)
    explicit_no_skip = image_prep.correct_orientation(img, skip=False)

    assert np.array_equal(default_call, explicit_no_skip)
    assert default_call.shape[:2] != img.shape[:2]


def test_prepare_subordinates_heuristic_when_exif_applied():
    """`image_prep.prepare(..., exif_orientation_applied=True)` no debe
    disparar la heurística de contenido; `exif_orientation_applied=False`
    (default) preserva el comportamiento legacy."""
    import cv2

    img = np.full((600, 300, 3), 255, dtype=np.uint8)
    for x in range(0, 300, 10):
        cv2.line(img, (x, 0), (x, 600), (0, 0, 0), 2)

    out_default = image_prep.prepare(img, exif_orientation_applied=False)
    out_subordinated = image_prep.prepare(img, exif_orientation_applied=True)

    # Sin EXIF aplicado, la heurística puede rotar 90/270 -> h/w se invierten.
    assert out_default.shape[1] == 600 and out_default.shape[0] == 300
    # Con EXIF ya aplicado, se preserva la orientación de entrada (mismo
    # aspect ratio relativo, sin la rotación de la heurística).
    assert out_subordinated.shape[0] >= out_subordinated.shape[1]


def _build_gas_receipt_with_exif(orientation: int) -> Path:
    """Genera, en un archivo temporal JPEG, un comprobante de gas sintético
    (texto renderizado, tipo LITORAL_GAS) con el tag EXIF Orientation dado."""
    canonical = Image.new("RGB", (800, 600), (255, 255, 255))
    draw = ImageDraw.Draw(canonical)
    lines = [
        "COMPROBANTE GAS",
        "Litoral Gas - Servicio de Gas Natural",
        "N Cliente: 12345678",
        "Nro Medidor: 123456789012",
        "Periodo: 05/2026",
        "A pagar hasta: 15/06/2026",
        "Importe: $ 123.45",
    ]
    y = 40
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0))
        y += 60

    method = _RAW_TRANSFORM_FOR_ORIENTATION[orientation]
    raw = canonical if method is None else canonical.transpose(method)
    exif = raw.getexif()
    exif[ORIENTATION_TAG] = orientation

    tmp_path = Path(tempfile.mktemp(suffix=".jpg"))
    raw.save(tmp_path, exif=exif)
    return tmp_path


@pytest.mark.parametrize("orientation", [6, 8])
def test_process_document_recovers_text_from_rotated_exif_image(orientation):
    """Integración end-to-end: `process_document` sobre una imagen con texto
    renderizado y EXIF Orientation=6/8 debe producir texto OCR reconocible
    (no vacío) equivalente al de la imagen ya derecha, gracias a la
    corrección EXIF aplicada antes de OCR."""
    tmp_path = _build_gas_receipt_with_exif(orientation)
    try:
        result = process_document(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)

    raw_text = result["raw_ocr_text"]
    assert isinstance(raw_text, str)
    assert raw_text.strip() != "", "OCR no debe devolver texto vacío tras corregir EXIF"
    # El identificador de cliente sintético debe ser legible: confirma que el
    # contenido llegó a OCR en la orientación correcta (no rotado/espejado).
    assert "12345678" in raw_text.replace(" ", "")
