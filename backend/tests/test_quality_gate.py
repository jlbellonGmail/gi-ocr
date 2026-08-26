"""Tests del control de calidad de captura previo a OCR (feature
`06-calidad-captura-mobile`, `backend/app/quality_gate.py`).

Cubre las 8 señales de calidad (criterios 6-13 de
`runs/06-calidad-captura-mobile/spec.md`), el veredicto agregado de tres
niveles (criterios 14-17), la integración con `capture_pipeline.
process_document` (OCR no invocado en `reject`) y con `job_queue.JobQueue`
(estado nuevo `needs_new_photo`, `confirm`/`retry`, criterios 18-19), y los
casos borde del spec (señales simultáneas, deduplicación corte/perspectiva,
imágenes degeneradas, imagen corrupta, determinismo de retry, PDF fuera de
alcance).

Todas las fixtures son 100% sintéticas (rectángulos/óvalos/texto dibujados
con PIL, transformaciones OpenCV controladas), generadas en memoria — nunca
comprobantes reales ni derivados de `storage_bridge/` (mismo patrón que
`test_image_prep.py`/`test_exif_orientation.py`).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from backend.app import capture_pipeline, image_prep, ocr_engine, quality_gate
from backend.app.job_queue import JobQueue
from backend.app.job_store import JobStore
from PIL import Image, ImageDraw

# --- helpers de fixtures sintéticas -----------------------------------------


def _textured_doc(w: int = 1200, h: int = 1600, bg: int = 210, lines: int = 25) -> np.ndarray:
    """Documento sintético con suficiente densidad de texto/bordes para que
    la métrica de blur (varianza del Laplaciano) sea representativa (ver
    limitación documentada en docs/tecnica/calidad-captura-mobile.md: una
    imagen nítida pero de fondo uniforme no debe interpretarse como blur)."""
    img = Image.new("RGB", (w, h), (bg, bg, bg))
    d = ImageDraw.Draw(img)
    y = 40
    for _ in range(lines):
        d.text((40, y), "FACTURA DE SERVICIO 1234567890 ABCDEFGH " * 2, fill=(10, 10, 10))
        y += 55
    return np.array(img)


def _doc_on_bg(
    canvas_w: int,
    canvas_h: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    bg: int = 30,
    doc: int = 225,
    with_text: bool = True,
) -> np.ndarray:
    """ "Documento" (rectángulo claro) sobre fondo oscuro, en una posición y
    tamaño configurables dentro de un canvas — para las señales de corte,
    perspectiva y encuadre. `x0`/`y0` pueden ser negativos (documento que se
    sale del cuadro por ese lado)."""
    img = Image.new("RGB", (canvas_w, canvas_h), (bg, bg, bg))
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], fill=(doc, doc, doc))
    if with_text:
        for y in range(max(y0, 0) + 30, y1 - 30, 60):
            d.text((max(x0, 0) + 30, y), "FACTURA SERVICIO 12345678", fill=(20, 20, 20))
    return np.array(img)


def _warp_perspective(arr: np.ndarray, dx_top: int, dx_bottom: int, bg: int = 30) -> np.ndarray:
    h, w = arr.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[dx_top, 0], [w - dx_top, 0], [w - dx_bottom, h], [dx_bottom, h]])
    m = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(arr, m, (w, h), borderValue=(bg, bg, bg))


# --- 1) Blur / desenfoque (criterio 6) --------------------------------------


def test_blur_sharp_image_is_ok():
    sharp = _textured_doc()
    signal = quality_gate.evaluate(sharp)["signals"]["blur"]
    assert signal["verdict"] == "ok"


def test_blur_light_blur_is_warn():
    base = _textured_doc()
    light_blur = cv2.GaussianBlur(base, (0, 0), sigmaX=1.0)
    signal = quality_gate.evaluate(light_blur)["signals"]["blur"]
    assert signal["verdict"] == "warn"


def test_blur_strong_blur_is_reject():
    base = _textured_doc()
    strong_blur = cv2.GaussianBlur(base, (0, 0), sigmaX=3.0)
    r = quality_gate.evaluate(strong_blur)
    assert r["signals"]["blur"]["verdict"] == "reject"
    assert r["verdict"] == "reject"
    assert any(reason["signal"] == "blur" for reason in r["reasons"])


# --- 2) Baja resolución (criterio 7) ----------------------------------------


def test_low_resolution_small_image_is_reject():
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    signal = quality_gate.evaluate(small)["signals"]["low_resolution"]
    assert signal["verdict"] == "reject"
    assert signal["metric"] == 300.0  # min(h, w) sobre la imagen original


def test_low_resolution_large_image_is_ok():
    large = np.zeros((1600, 1200, 3), dtype=np.uint8)
    signal = quality_gate.evaluate(large)["signals"]["low_resolution"]
    assert signal["verdict"] == "ok"


def test_low_resolution_reason_identifier_is_stable_and_distinguishable():
    """El identificador de razón para "baja resolución" debe ser estable y
    distinto del resto de señales (caso borde: resolución baja por
    limitación real del dispositivo, no corregible con "otra" foto)."""
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    r = quality_gate.evaluate(small)
    ids = {reason["signal"] for reason in r["reasons"]}
    assert "low_resolution" in ids
    assert ids - {"low_resolution", "blur", "poor_lighting"} == set() or "low_resolution" in ids


def test_low_resolution_measured_on_original_not_prepared_image():
    """El chequeo corre sobre la imagen tal como llega, no sobre una copia ya
    reducida por `image_prep.normalize_scale` (que solo reduce el lado
    mayor, nunca sube resolución)."""
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    prepared = image_prep.normalize_scale(small, max_side=1600)
    # normalize_scale no reduce nada porque 400 < 1600: el chequeo de
    # quality_gate debe seguir viendo la imagen original de baja resolución.
    signal = quality_gate.evaluate(prepared)["signals"]["low_resolution"]
    assert signal["verdict"] == "reject"


# --- 3) Reflejos / glare (criterio 8) ---------------------------------------


def _with_glare(base_pil: Image.Image, radius_ratio: float) -> np.ndarray:
    im2 = base_pil.copy()
    d = ImageDraw.Draw(im2)
    w, h = im2.size
    r = int(min(w, h) * radius_ratio)
    cx, cy = w // 2, h // 3
    d.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=(255, 255, 255))
    return np.array(im2)


def _textured_doc_pil(w: int = 1200, h: int = 1600, bg: int = 210, lines: int = 25) -> Image.Image:
    img = Image.new("RGB", (w, h), (bg, bg, bg))
    d = ImageDraw.Draw(img)
    y = 40
    for _ in range(lines):
        d.text((40, y), "FACTURA DE SERVICIO 1234567890 ABCDEFGH " * 2, fill=(10, 10, 10))
        y += 55
    return img


def test_glare_no_reflection_is_ok():
    base = _textured_doc_pil()
    signal = quality_gate.evaluate(np.array(base))["signals"]["glare"]
    assert signal["verdict"] == "ok"


def test_glare_small_reflection_is_warn():
    base = _textured_doc_pil()
    glared = _with_glare(base, radius_ratio=0.12)
    signal = quality_gate.evaluate(glared)["signals"]["glare"]
    assert signal["verdict"] == "warn"


def test_glare_large_reflection_is_reject():
    base = _textured_doc_pil()
    glared = _with_glare(base, radius_ratio=0.3)
    r = quality_gate.evaluate(glared)
    assert r["signals"]["glare"]["verdict"] == "reject"
    assert any(reason["signal"] == "glare" for reason in r["reasons"])


def test_glare_uniform_bright_background_is_not_a_false_positive():
    """Fondo de papel blanco brillante pero UNIFORME (difuso, no
    concentrado): no debe dispararse como reflejo (criterio 8, distinción
    frente a "mala iluminación", criterio 12)."""
    uniform_bright = np.full((1600, 1200, 3), 250, dtype=np.uint8)
    signal = quality_gate.evaluate(uniform_bright)["signals"]["glare"]
    assert signal["verdict"] == "ok"


# --- 4) Sombras / iluminación desigual (criterio 9) -------------------------


def _with_shadow(arr: np.ndarray, darken_frac: float) -> np.ndarray:
    out = arr.astype(np.float64).copy()
    _h, w = out.shape[:2]
    gradient = np.linspace(1 - darken_frac, 1.0, w)[None, :, None]
    out = out * gradient
    return np.clip(out, 0, 255).astype(np.uint8)


def test_shadow_uniform_lighting_is_ok():
    base = _textured_doc()
    signal = quality_gate.evaluate(base)["signals"]["uneven_lighting"]
    assert signal["verdict"] == "ok"


def test_shadow_moderate_gradient_is_warn():
    base = _textured_doc()
    shadowed = _with_shadow(base, darken_frac=0.35)
    signal = quality_gate.evaluate(shadowed)["signals"]["uneven_lighting"]
    assert signal["verdict"] == "warn"


def test_shadow_strong_gradient_is_reject():
    base = _textured_doc()
    shadowed = _with_shadow(base, darken_frac=0.6)
    r = quality_gate.evaluate(shadowed)
    assert r["signals"]["uneven_lighting"]["verdict"] == "reject"
    assert any(reason["signal"] == "uneven_lighting" for reason in r["reasons"])


def test_shadow_does_not_fire_for_uniformly_dark_image():
    """Falso positivo evitado: una imagen uniformemente OSCURA (sin
    varianza entre regiones) no debe disparar "sombras" — dispara "mala
    iluminación" (criterio 12) en su lugar."""
    base = _textured_doc()
    uniform_dark = np.clip(base.astype(np.float64) * 0.15, 0, 255).astype(np.uint8)
    r = quality_gate.evaluate(uniform_dark)
    assert r["signals"]["uneven_lighting"]["verdict"] == "ok"
    assert r["signals"]["poor_lighting"]["verdict"] == "reject"


# --- 5) Documento cortado + 6) mala perspectiva + 8) encuadre (criterios
#        10, 11, 13; deduplicación de causa raíz) --------------------------


def test_cut_document_fully_inside_frame_is_ok():
    full = _doc_on_bg(1200, 1600, 100, 150, 1100, 1450)
    r = quality_gate.evaluate(full)
    assert r["signals"]["document_cropped"]["verdict"] == "ok"


def test_cut_document_touching_two_edges_is_reject():
    cut = _doc_on_bg(1200, 1600, -150, -100, 900, 1200)
    r = quality_gate.evaluate(cut)
    assert r["signals"]["document_cropped"]["verdict"] == "reject"
    assert any(reason["signal"] == "document_cropped" for reason in r["reasons"])
    assert r["verdict"] == "reject"


def test_cut_document_deduplicates_perspective_reason():
    """Cuando el documento está cortado (no se detecta un cuadrilátero de 4
    lados claro), la señal de "mala perspectiva" no debe evaluarse como una
    segunda razón independiente por la misma causa raíz: cede el resultado
    a "documento cortado" (criterio 11, "Casos borde" del spec)."""
    cut = _doc_on_bg(1200, 1600, -150, -100, 900, 1200)
    r = quality_gate.evaluate(cut)
    assert r["signals"]["bad_perspective"]["verdict"] == "not_evaluable"
    ids = {reason["signal"] for reason in r["reasons"]}
    assert "document_cropped" in ids
    assert "bad_perspective" not in ids


def test_perspective_frontal_document_is_ok():
    base = _doc_on_bg(1200, 1600, 100, 150, 1100, 1450)
    warped = _warp_perspective(base, dx_top=20, dx_bottom=20)
    r = quality_gate.evaluate(warped)
    assert r["signals"]["bad_perspective"]["verdict"] == "ok"


def test_perspective_moderate_skew_is_warn():
    base = _doc_on_bg(1200, 1600, 100, 150, 1100, 1450)
    warped = _warp_perspective(base, dx_top=170, dx_bottom=20)
    signal = quality_gate.evaluate(warped)["signals"]["bad_perspective"]
    assert signal["verdict"] == "warn"


def test_perspective_strong_skew_is_reject():
    base = _doc_on_bg(1200, 1600, 100, 150, 1100, 1450)
    warped = _warp_perspective(base, dx_top=300, dx_bottom=20)
    r = quality_gate.evaluate(warped)
    assert r["signals"]["bad_perspective"]["verdict"] == "reject"
    assert any(reason["signal"] == "bad_perspective" for reason in r["reasons"])


def test_framing_document_fills_frame_is_ok():
    full = _doc_on_bg(1200, 1600, 100, 150, 1100, 1450)
    signal = quality_gate.evaluate(full)["signals"]["insufficient_framing"]
    assert signal["verdict"] == "ok"


def test_framing_small_document_is_warn_never_reject():
    small = _doc_on_bg(1200, 1600, 450, 650, 750, 950)
    r = quality_gate.evaluate(small)
    assert r["signals"]["insufficient_framing"]["verdict"] == "warn"
    # Techo warn: esta señal nunca aparece como razón de "reject" (criterio 13).
    for reason in r["reasons"]:
        if reason["signal"] == "insufficient_framing":
            assert reason["severity"] == "warn"


def test_framing_degrades_gracefully_without_document_contour():
    """Sin ningún contorno de documento detectable (fondo muy uniforme), la
    señal de encuadre no debe inventar un área: degrada a "no evaluable"
    sin afectar el veredicto agregado por esta señal (criterio 13)."""
    uniform = np.full((1600, 1200, 3), 200, dtype=np.uint8)
    r = quality_gate.evaluate(uniform)
    assert r["signals"]["insufficient_framing"]["verdict"] == "not_evaluable"
    assert not any(reason["signal"] == "insufficient_framing" for reason in r["reasons"])


# --- 7) Mala iluminación (criterio 12) --------------------------------------


def _textured_doc_normal(w: int = 1200, h: int = 1600, bg: int = 180) -> np.ndarray:
    return _textured_doc(w=w, h=h, bg=bg)


def test_illumination_normal_brightness_is_ok():
    base = _textured_doc_normal()
    signal = quality_gate.evaluate(base)["signals"]["poor_lighting"]
    assert signal["verdict"] == "ok"


def test_illumination_dark_warn():
    base = _textured_doc_normal()
    dim = np.clip(base.astype(np.float64) * 0.30, 0, 255).astype(np.uint8)
    signal = quality_gate.evaluate(dim)["signals"]["poor_lighting"]
    assert signal["verdict"] == "warn"


def test_illumination_dark_reject():
    base = _textured_doc_normal()
    dark = np.clip(base.astype(np.float64) * 0.15, 0, 255).astype(np.uint8)
    r = quality_gate.evaluate(dark)
    assert r["signals"]["poor_lighting"]["verdict"] == "reject"
    assert any(reason["signal"] == "poor_lighting" for reason in r["reasons"])


def test_illumination_overexposed_reject():
    """Simula sobreexposición (flash/glare que lava el contraste, incluido
    el texto) sumando un offset uniforme en vez de multiplicar: sobre un
    documento con fondo claro (convención de fixtures de este repo, ver
    `backend/tests/fixtures/gas_sample.jpg`), multiplicar por un factor deja
    el texto anclado en valores oscuros y no reproduce una sobreexposición
    real: la suma sí desplaza también el texto hacia blanco, perdiendo
    contraste como en una foto realmente sobreexpuesta."""
    base = _textured_doc_normal()
    overexposed = np.clip(base.astype(np.float64) + 210, 0, 255).astype(np.uint8)
    r = quality_gate.evaluate(overexposed)
    assert r["signals"]["poor_lighting"]["verdict"] == "reject"
    assert any(reason["signal"] == "poor_lighting" for reason in r["reasons"])


# --- Umbrales configurables por variable de entorno -------------------------


def test_threshold_overridable_by_env_var(monkeypatch):
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    assert quality_gate.evaluate(small)["signals"]["low_resolution"]["verdict"] == "reject"

    monkeypatch.setenv("GI_OCR_QUALITY_MIN_SIDE_REJECT_BELOW", "100")
    monkeypatch.setenv("GI_OCR_QUALITY_MIN_SIDE_WARN_BELOW", "200")
    assert quality_gate.evaluate(small)["signals"]["low_resolution"]["verdict"] == "ok"


def test_threshold_invalid_env_var_falls_back_to_default(monkeypatch):
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    monkeypatch.setenv("GI_OCR_QUALITY_MIN_SIDE_REJECT_BELOW", "not-a-number")
    assert quality_gate.evaluate(small)["signals"]["low_resolution"]["verdict"] == "reject"


# --- Veredicto agregado (criterios 14-17) y casos borde ---------------------


def test_verdict_worst_subverdict_wins_with_all_reasons_listed():
    """Múltiples señales en reject simultáneamente: el veredicto agregado es
    reject una sola vez, con TODAS las razones listadas, no solo la
    primera."""
    small_cut = _doc_on_bg(400, 300, -60, -40, 300, 250)
    r = quality_gate.evaluate(small_cut)
    assert r["verdict"] == "reject"
    ids = {reason["signal"] for reason in r["reasons"]}
    assert "low_resolution" in ids
    assert "document_cropped" in ids
    assert len(r["reasons"]) >= 2


def test_verdict_mixed_severity_reject_wins_but_both_listed():
    base = _textured_doc()
    mixed = cv2.GaussianBlur(base, (0, 0), sigmaX=1.0)  # blur -> warn
    mixed = np.clip(mixed.astype(np.float64) * 0.15, 0, 255).astype(np.uint8)  # + oscuro -> reject
    r = quality_gate.evaluate(mixed)
    assert r["verdict"] == "reject"
    ids = {reason["signal"] for reason in r["reasons"]}
    assert "blur" in ids
    assert "poor_lighting" in ids


def test_degenerate_all_black_image_does_not_raise_and_rejects():
    arr = np.zeros((600, 800, 3), dtype=np.uint8)
    r = quality_gate.evaluate(arr)
    assert r["verdict"] == "reject"
    assert r["reasons"]


def test_degenerate_all_white_image_does_not_raise_and_rejects():
    arr = np.full((600, 800, 3), 255, dtype=np.uint8)
    r = quality_gate.evaluate(arr)
    assert r["verdict"] == "reject"
    assert r["reasons"]


def test_degenerate_1x1_image_does_not_raise():
    arr = np.zeros((1, 1, 3), dtype=np.uint8)
    r = quality_gate.evaluate(arr)
    assert r["verdict"] == "reject"
    assert r["reasons"]


def test_evaluate_is_deterministic():
    arr = _doc_on_bg(1200, 1600, -150, -100, 900, 1200)
    r1 = quality_gate.evaluate(arr)
    r2 = quality_gate.evaluate(arr)
    assert r1 == r2


# --- Integración con capture_pipeline.process_document (criterios 15-17) ---


def _write_temp_image(arr: np.ndarray, suffix: str = ".png") -> Path:
    tmp = Path(tempfile.mktemp(suffix=suffix))
    Image.fromarray(arr).save(tmp)
    return tmp


def test_process_document_reject_does_not_invoke_ocr():
    """Veredicto reject: `ocr_engine.detect_page` (usado por `process_image`)
    NO debe invocarse (criterio 17)."""
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    tmp = _write_temp_image(small)
    try:
        with patch.object(ocr_engine, "detect_page") as spy:
            result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    spy.assert_not_called()
    qg = result["processing_metadata"]["quality_gate"]
    assert qg["verdict"] == "reject"
    assert result["structured_output"]["validated_fields"] == {}
    assert result["raw_ocr_text"] == ""


def test_process_document_reject_lists_specific_reason_messages():
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    tmp = _write_temp_image(small)
    try:
        result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    reasons = result["processing_metadata"]["quality_gate"]["reasons"]
    assert reasons
    for reason in reasons:
        assert reason["message"]
        assert reason["signal"]


def test_process_document_warn_still_runs_ocr_and_flags_metadata():
    base = _textured_doc(bg=210)
    light_blur = cv2.GaussianBlur(base, (0, 0), sigmaX=1.0)
    tmp = _write_temp_image(light_blur, suffix=".jpg")
    try:
        result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    qg = result["processing_metadata"]["quality_gate"]
    assert qg["verdict"] in ("warn", "ok")  # depende de las demás señales sobre esta imagen concreta
    # El pipeline normal corrió: hay texto OCR (aunque no se valide ningún campo conocido).
    assert "raw_ocr_text" in result
    assert result["processing_metadata"]["engine"] == "RapidOCR-ONNX-PP-OCRv3"


def test_process_document_ok_has_neutral_quality_gate_block():
    fixture = Path(__file__).resolve().parent / "fixtures" / "gas_sample.jpg"
    result = capture_pipeline.process_document(str(fixture))
    qg = result["processing_metadata"]["quality_gate"]
    assert qg["verdict"] in ("ok", "warn")
    assert "reasons" in qg and "signals" in qg


# --- Corrupted / degenerate file handling (fuera del scope de quality_gate) -


def test_process_document_corrupt_file_raises_not_quality_reject():
    """Un archivo que pasó la validación de firma pero no puede abrirse con
    Pillow debe seguir fallando como antes (excepción -> `status == failed`
    en `job_queue`), NO como rechazo de calidad (son conceptualmente
    distintos)."""
    tmp = Path(tempfile.mktemp(suffix=".jpg"))
    tmp.write_bytes(b"\xff\xd8\xff" + b"esto no es una imagen JPEG valida")
    try:
        with pytest.raises(Exception):
            capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)


def test_pdf_path_bypasses_quality_gate():
    """El chequeo de calidad aplica solo al camino de imagen: un PDF no debe
    invocar `quality_gate.evaluate` (fuera de alcance explícito, ver
    `docs/tecnica/correccion-orientacion-exif.md`, "Fuera de alcance").

    Genera un PDF sintético en blanco en memoria con `pypdfium2` (mismo
    patrón que `test_pdf_util.py::_make_pdf_blank`), sin versionar ningún
    archivo PDF en el repo.
    """
    pypdfium2 = pytest.importorskip("pypdfium2")
    tmp_dir = Path(tempfile.mkdtemp(prefix="gi_ocr_quality_gate_pdf_"))
    pdf_path = tmp_dir / "blank.pdf"
    try:
        pdf = pypdfium2.PdfDocument.new()
        pdf.new_page(600, 800)
        pdf.save(str(pdf_path))
        pdf.close()

        with patch.object(quality_gate, "evaluate") as spy:
            capture_pipeline.process_document(str(pdf_path))
        spy.assert_not_called()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# --- Integración con JobQueue (criterios 18-19) -----------------------------


@pytest.fixture()
def isolated_queue():
    # No usa el fixture `tmp_path` de pytest: en este entorno de desarrollo
    # el directorio base de pytest (`%TEMP%/pytest-of-<user>`) puede no ser
    # listable (permisos), un problema de entorno ajeno a esta feature.
    # `tempfile.mkdtemp()` escribe directo bajo `%TEMP%`, sin ese problema
    # (mismo patrón que `_write_temp_image` en este archivo y que
    # `test_exif_orientation.py::_build_gas_receipt_with_exif`).
    base_dir = Path(tempfile.mkdtemp(prefix="gi_ocr_quality_gate_test_"))
    store = JobStore(base_dir)
    queue = JobQueue(store, workers=1)
    queue.start()
    yield queue, store
    queue.stop()
    shutil.rmtree(base_dir, ignore_errors=True)


def _wait_status(store: JobStore, job_id: str, timeout: float = 30.0):
    import time as _time

    deadline = _time.time() + timeout
    job = store.get(job_id)
    while _time.time() < deadline and job and job["status"] in ("queued", "processing"):
        _time.sleep(0.1)
        job = store.get(job_id)
    return job


def test_job_queue_reject_sets_needs_new_photo_status(isolated_queue):
    queue, store = isolated_queue
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    tmp = _write_temp_image(small)
    try:
        job_id = queue.enqueue(str(tmp), "foto_borrosa.png", source="test")
        job = _wait_status(store, job_id)

        assert job is not None
        assert job["status"] == quality_gate.REJECTED_JOB_STATUS
        assert job["status"] not in ("ready", "failed")
        # Sin OCR, no se llamó save_original: el original no "existe" para
        # el store (criterio 18: confirm/download deben seguir dando 404).
        assert store.original_exists(job_id) is False
    finally:
        tmp.unlink(missing_ok=True)


def test_job_queue_retry_on_rejected_job_is_deterministic(isolated_queue):
    queue, store = isolated_queue
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    tmp = _write_temp_image(small)
    try:
        job_id = queue.enqueue(str(tmp), "foto_borrosa.png", source="test")
        job = _wait_status(store, job_id)
        assert job["status"] == quality_gate.REJECTED_JOB_STATUS
        first_reasons = job["result"]["processing_metadata"]["quality_gate"]["reasons"]

        ok = queue.retry(job_id)
        assert ok is True

        job2 = _wait_status(store, job_id)
        assert job2["status"] == quality_gate.REJECTED_JOB_STATUS
        second_reasons = job2["result"]["processing_metadata"]["quality_gate"]["reasons"]
        assert first_reasons == second_reasons
    finally:
        tmp.unlink(missing_ok=True)


def test_job_queue_ready_job_still_calls_save_original(isolated_queue):
    """Regresión: el camino `ok`/`warn` (no rechazado) sigue guardando el
    original como antes."""
    queue, store = isolated_queue
    fixture = Path(__file__).resolve().parent / "fixtures" / "gas_sample.jpg"
    job_id = queue.enqueue(str(fixture), "gas_sample.jpg", source="test")
    job = _wait_status(store, job_id)

    assert job is not None
    assert job["status"] == "ready"
    assert store.original_exists(job_id) is True


# --- Integración HTTP end-to-end (criterios 18-19, vía la app real) --------


def _small_png_bytes() -> bytes:
    import io

    img = Image.fromarray(np.zeros((300, 400, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _wait_job_http(client, job_id: str, timeout: float = 30.0) -> dict:
    import time as _time

    deadline = _time.time() + timeout
    body = client.get(f"/api/v1/jobs/{job_id}").json()
    while _time.time() < deadline and body.get("status") in ("queued", "processing"):
        _time.sleep(0.2)
        body = client.get(f"/api/v1/jobs/{job_id}").json()
    return body


def test_api_job_rejected_by_quality_gate_returns_needs_new_photo_status():
    from backend.app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app, headers={"X-Operator-Id": "test_operator", "X-Operator-Role": "admin"})
    r = client.post("/api/v1/jobs", files={"files": ("borrosa.png", _small_png_bytes(), "image/png")})
    assert r.status_code == 200
    job_id = r.json()["created"][0]["job_id"]

    job = _wait_job_http(client, job_id)
    assert job["status"] == quality_gate.REJECTED_JOB_STATUS
    assert job["result"]["processing_metadata"]["quality_gate"]["reasons"]


def test_api_confirm_on_rejected_job_returns_404():
    """Criterio 18: `confirm` sigue rechazando (404) la confirmación de un
    job en el nuevo estado de rechazo por calidad, porque no se generó
    resultado OCR que confirmar (vía `store.original_exists`, sin cambios
    de comportamiento en ese chequeo)."""
    from backend.app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app, headers={"X-Operator-Id": "test_operator", "X-Operator-Role": "admin"})
    r = client.post("/api/v1/jobs", files={"files": ("borrosa2.png", _small_png_bytes(), "image/png")})
    job_id = r.json()["created"][0]["job_id"]
    job = _wait_job_http(client, job_id)
    assert job["status"] == quality_gate.REJECTED_JOB_STATUS

    rc = client.post(f"/api/v1/jobs/{job_id}/confirm", json={"confirmed_fields": []})
    assert rc.status_code == 404


def test_api_retry_on_rejected_job_returns_200_and_requeues():
    """Criterio 19: `retry` sigue funcionando sin lanzar excepción sobre un
    job en el nuevo estado de rechazo por calidad."""
    from backend.app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app, headers={"X-Operator-Id": "test_operator", "X-Operator-Role": "admin"})
    r = client.post("/api/v1/jobs", files={"files": ("borrosa3.png", _small_png_bytes(), "image/png")})
    job_id = r.json()["created"][0]["job_id"]
    job = _wait_job_http(client, job_id)
    assert job["status"] == quality_gate.REJECTED_JOB_STATUS

    rr = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert rr.status_code == 200

    job2 = _wait_job_http(client, job_id)
    assert job2["status"] == quality_gate.REJECTED_JOB_STATUS
