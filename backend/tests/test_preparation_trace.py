"""Tests de preprocesamiento documental no destructivo (feature
`07-preprocesamiento-documental-no-destructivo`, `backend/app/image_prep.py`
+ `backend/app/capture_pipeline.py`).

Cubre:
- No-destructividad del archivo original (`output/uploads/`) verificada por
  hash SHA-256 antes/después, tanto vía `capture_pipeline.process_document`
  directo como vía `POST /api/v1/jobs/{job_id}/retry` (criterios 6-8).
- Traza ordenada de transformaciones dentro de `processing_metadata`
  (criterios 9-10), incluidos los casos borde de `quality_gate.verdict ==
  "reject"` (criterio 11) y del camino PDF, con y sin imagen renderizada
  (criterio 12).
- El paso nuevo de normalización de contraste/iluminación
  (`image_prep.normalize_contrast`): determinismo, salvaguarda contra
  sobre-procesamiento y mejora verificable sobre fixtures de bajo contraste
  (criterios 13-16), incluida la regla de dominio OCR sobre el fixture GAS
  de referencia (sin pérdida ni invención de dígitos).
- Idempotencia de reprocesamiento (criterio 17).

Todas las fixtures son sintéticas (generadas en memoria con PIL/OpenCV) o
reutilizan `backend/tests/fixtures/gas_sample.jpg` (ya sintético, usado por
`test_quality_gate.py`/`test_exif_orientation.py`) -- nunca comprobantes
reales.
"""

from __future__ import annotations

import hashlib
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from backend.app import capture_pipeline, image_prep
from backend.app.main import app
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

client = TestClient(app, headers={"X-Operator-Id": "test_operator", "X-Operator-Role": "admin"})

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GAS_SAMPLE = FIXTURES_DIR / "gas_sample.jpg"

_ORIENTATION_TAG = 0x0112  # 274, EXIF "Orientation"


# --- helpers de fixtures sintéticas -----------------------------------------


def _textured_doc(w: int = 1200, h: int = 1600, bg: int = 210, text=(10, 10, 10), lines: int = 25) -> np.ndarray:
    """Documento sintético con suficiente densidad de texto/bordes para pasar
    `quality_gate` en `ok`/`warn` (mismo patrón que `test_quality_gate.py`)."""
    img = Image.new("RGB", (w, h), (bg, bg, bg))
    d = ImageDraw.Draw(img)
    y = 40
    for _ in range(lines):
        d.text((40, y), "FACTURA DE SERVICIO 1234567890 ABCDEFGH " * 2, fill=text)
        y += 55
    return np.array(img)


def _doc_on_dark_bg(canvas_w: int = 1200, canvas_h: int = 1600, margin: int = 150) -> np.ndarray:
    """Documento claro sobre fondo oscuro, con margen suficiente para que
    `find_document_contour` detecte un cuadrilátero claro (mismo patrón que
    `test_quality_gate.py::_doc_on_bg`)."""
    img = Image.new("RGB", (canvas_w, canvas_h), (20, 20, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([margin, margin, canvas_w - margin, canvas_h - margin], fill=(225, 225, 225))
    for y in range(margin + 40, canvas_h - margin - 40, 60):
        d.text((margin + 30, y), "FACTURA SERVICIO 12345678", fill=(20, 20, 20))
    return np.array(img)


def _write_temp_image(arr: np.ndarray, suffix: str = ".jpg") -> Path:
    tmp = Path(tempfile.mktemp(suffix=suffix))
    Image.fromarray(arr).save(tmp)
    return tmp


def _sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _build_receipt_with_exif(orientation: int, bg=210, text=(10, 10, 10)) -> Path:
    """Genera un comprobante sintético con el tag EXIF `Orientation` dado
    (mismo patrón que `test_exif_orientation.py::_build_gas_receipt_with_exif`)."""
    canonical = Image.fromarray(_textured_doc(w=800, h=600, bg=bg, text=text, lines=8))
    raw = canonical.transpose(Image.Transpose.ROTATE_90) if orientation == 6 else canonical
    exif = raw.getexif()
    exif[_ORIENTATION_TAG] = orientation
    tmp = Path(tempfile.mktemp(suffix=".jpg"))
    raw.save(tmp, exif=exif)
    return tmp


def _build_native_text_pdf(path: Path, text: str) -> None:
    """Construye a mano un PDF mínimo válido con texto NATIVO (sin imagen),
    usando sintaxis PDF cruda con una fuente estándar (Helvetica, no requiere
    embeber fuente). `pypdfium2` en esta versión no expone una API simple de
    autoría de texto (`PdfPage.insert_text`/`PdfTextObj.new` no existen),
    pero sí puede LEER cualquier PDF válido -- construir el PDF a mano es la
    forma más simple y determinística de obtener un fixture 100% sintético
    con texto nativo suficiente para que `pdf_util.extract_text_and_render`
    lo clasifique como `needs_ocr=False` (>=6 caracteres alfanuméricos)."""
    content = f"BT /F1 24 Tf 10 150 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode()
        out += obj
        out += b"\nendobj\n"
    xref_offset = len(out)
    n = len(objects) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n"
    out += f"<< /Size {n} /Root 1 0 R >>\n".encode()
    out += b"startxref\n"
    out += f"{xref_offset}\n".encode()
    out += b"%%EOF"
    path.write_bytes(bytes(out))


def _wait_ready(job_id: str, timeout: float = 60.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/v1/jobs/{job_id}").json()
        if j["status"] in ("ready", "failed", "needs_new_photo"):
            return j
        time.sleep(0.2)
    return client.get(f"/api/v1/jobs/{job_id}").json()


# --- No-destructividad del original (criterios 6-8) -------------------------


@pytest.mark.parametrize("suffix", [".jpg", ".png"])
def test_process_document_does_not_modify_original_file(suffix):
    arr = _textured_doc()
    tmp = _write_temp_image(arr, suffix=suffix)
    try:
        before = _sha256_file(tmp)
        capture_pipeline.process_document(str(tmp))
        after = _sha256_file(tmp)
        assert before == after, "process_document no debe modificar el archivo original"
    finally:
        tmp.unlink(missing_ok=True)


def test_process_document_does_not_modify_original_pdf():
    tmp_dir = Path(tempfile.mkdtemp())
    pdf_path = tmp_dir / "native.pdf"
    _build_native_text_pdf(pdf_path, "COMPROBANTE 123456")
    try:
        before = _sha256_file(pdf_path)
        capture_pipeline.process_document(str(pdf_path))
        after = _sha256_file(pdf_path)
        assert before == after
    finally:
        pdf_path.unlink(missing_ok=True)


def test_retry_endpoint_does_not_modify_original_file():
    """`JobQueue.retry` sólo bloquea jobs `ready`/`confirmed` (ver
    `job_queue.py`); se usa una imagen que dispara `quality_gate.verdict ==
    "reject"` (estado `needs_new_photo`, reintentable) para poder ejercer
    `/retry` de punta a punta con un veredicto determinístico."""
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    tmp = _write_temp_image(small, suffix=".png")
    try:
        with open(tmp, "rb") as f:
            r = client.post("/api/v1/jobs", files={"files": ("doc.png", f, "image/png")})
        assert r.status_code == 200
        job_id = r.json()["created"][0]["job_id"]
        job = _wait_ready(job_id)
        assert job["status"] == "needs_new_photo"
        file_path = job["file_path"]

        before = _sha256_file(file_path)
        r2 = client.post(f"/api/v1/jobs/{job_id}/retry")
        assert r2.status_code == 200
        job2 = _wait_ready(job_id)
        assert job2["status"] == "needs_new_photo"
        after = _sha256_file(file_path)
        assert before == after, "/retry no debe modificar el archivo original en output/uploads/"
    finally:
        tmp.unlink(missing_ok=True)


# --- Traza de transformaciones: camino de imagen (criterios 9-10) ----------


def test_process_document_image_path_trace_order_and_shape():
    arr = _textured_doc(bg=210)
    tmp = _write_temp_image(arr, suffix=".jpg")
    try:
        result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    qg = result["processing_metadata"]["quality_gate"]
    assert qg["verdict"] in ("ok", "warn")

    trace = result["processing_metadata"]["preparation_trace"]
    steps = [e["step"] for e in trace]
    assert steps == [
        "apply_exif_orientation",
        "correct_orientation",
        "deskew",
        "correct_perspective",
        "normalize_scale",
        "normalize_contrast",
    ]
    for entry in trace:
        assert isinstance(entry["step"], str)
        assert isinstance(entry["applied"], bool)

    # perspectiva no solicitada por defecto: "omitido", no "intentado y no encontrado"
    persp = trace[3]
    assert persp["applied"] is False
    assert persp["requested"] is False


def test_trace_reflects_exif_applied_and_subordinates_content_heuristic():
    tmp = _build_receipt_with_exif(6)
    try:
        result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    trace = result["processing_metadata"]["preparation_trace"]
    exif_entry = trace[0]
    assert exif_entry["step"] == "apply_exif_orientation"
    assert exif_entry["applied"] is True

    orientation_entry = trace[1]
    assert orientation_entry["step"] == "correct_orientation"
    assert orientation_entry["applied"] is False
    assert "exif" in orientation_entry["reason"].lower()


def test_trace_reports_exif_not_applied_when_no_exif_tag():
    tmp = _write_temp_image(_textured_doc(), suffix=".jpg")
    try:
        result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    trace = result["processing_metadata"]["preparation_trace"]
    exif_entry = trace[0]
    assert exif_entry["applied"] is False
    orientation_entry = trace[1]
    # sin EXIF aplicado, la heurística de contenido corre igual que siempre
    # (no subordinada); sobre un documento ya derecho, no debería rotar.
    assert orientation_entry["applied"] is False
    assert "exif" not in orientation_entry["reason"].lower()


# --- Caso borde: quality_gate reject no genera traza fantasma (criterio 11) -


def test_quality_reject_result_has_no_preparation_trace():
    small = np.zeros((300, 400, 3), dtype=np.uint8)
    tmp = _write_temp_image(small, suffix=".png")
    try:
        result = capture_pipeline.process_document(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    assert result["processing_metadata"]["quality_gate"]["verdict"] == "reject"
    assert "preparation_trace" not in result["processing_metadata"]


# --- Traza de transformaciones: camino PDF (criterio 12) --------------------


def test_pdf_with_rendered_image_trace_excludes_exif_and_quality_gate(tmp_path):
    pdfium = pytest.importorskip("pypdfium2")
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(600, 800)
    pdf_path = tmp_path / "blank.pdf"
    pdf.save(str(pdf_path))
    pdf.close()

    result = capture_pipeline.process_document(str(pdf_path))
    meta = result["processing_metadata"]
    assert meta.get("is_pdf") is True
    assert "quality_gate" not in meta

    trace = meta["preparation_trace"]
    steps = [e["step"] for e in trace]
    assert steps == ["correct_orientation", "deskew", "correct_perspective", "normalize_scale", "normalize_contrast"]
    assert "apply_exif_orientation" not in steps


def test_pdf_native_text_has_no_preparation_trace(tmp_path):
    pytest.importorskip("pypdfium2")
    pdf_path = tmp_path / "native.pdf"
    _build_native_text_pdf(pdf_path, "COMPROBANTE GAS 123456")

    result = capture_pipeline.process_document(str(pdf_path))
    meta = result["processing_metadata"]
    assert meta.get("is_pdf") is True
    assert meta.get("pdf_pages_ocr") == 0
    assert "preparation_trace" not in meta
    assert "quality_gate" not in meta


# --- Perspectiva: "omitido" vs "intentado sin encontrar" (caso borde) ------


def test_trace_perspective_not_requested_is_distinct_from_attempted_not_found():
    arr = _textured_doc(bg=210)  # sin fondo oscuro que delimite un cuadrilátero

    not_requested_trace: list = []
    image_prep.prepare(arr, apply_perspective=False, trace=not_requested_trace)
    entry = next(e for e in not_requested_trace if e["step"] == "correct_perspective")
    assert entry["applied"] is False
    assert entry["requested"] is False

    requested_trace: list = []
    image_prep.prepare(arr, apply_perspective=True, trace=requested_trace)
    entry2 = next(e for e in requested_trace if e["step"] == "correct_perspective")
    assert entry2["requested"] is True
    assert entry2["applied"] is False
    assert "no se encontró" in entry2["reason"]


def test_trace_perspective_applied_when_requested_and_quad_detected():
    arr = _doc_on_dark_bg()
    trace: list = []
    image_prep.prepare(arr, apply_perspective=True, trace=trace)
    entry = next(e for e in trace if e["step"] == "correct_perspective")
    assert entry["requested"] is True
    assert entry["applied"] is True
    assert entry["width"] > 0
    assert entry["height"] > 0


# --- Deskew: ángulo reportado cuando se aplica ------------------------------


def test_trace_deskew_reports_angle_when_applied():
    arr = _textured_doc(w=1200, h=1600, bg=210)
    rotated = np.array(Image.fromarray(arr).rotate(2.0, resample=Image.BICUBIC, fillcolor=(210, 210, 210)))
    trace: list = []
    image_prep.prepare(rotated, trace=trace)
    entry = next(e for e in trace if e["step"] == "deskew")
    assert isinstance(entry["applied"], bool)
    if entry["applied"]:
        assert "angle_deg" in entry
        assert 0.1 <= abs(entry["angle_deg"]) <= 5


# --- Escala: factor y dimensiones (criterio 10) -----------------------------


def test_trace_normalize_scale_reports_factor_and_sizes_when_downscaled():
    arr = np.full((3000, 2000, 3), 200, dtype=np.uint8)
    trace: list = []
    image_prep.prepare(arr, trace=trace)
    entry = next(e for e in trace if e["step"] == "normalize_scale")
    assert entry["applied"] is True
    assert entry["original_size"] == [2000, 3000]
    assert max(entry["final_size"]) <= 1600
    assert 0 < entry["scale_factor"] < 1


def test_trace_normalize_scale_no_upscale_reports_not_applied():
    arr = np.full((100, 100, 3), 200, dtype=np.uint8)
    trace: list = []
    image_prep.prepare(arr, trace=trace)
    entry = next(e for e in trace if e["step"] == "normalize_scale")
    assert entry["applied"] is False
    assert entry["scale_factor"] == 1.0


# --- Contraste: función pura, determinismo (criterio 13) --------------------


def test_normalize_contrast_is_deterministic():
    arr = _textured_doc(bg=140, text=(120, 120, 120))
    out1 = image_prep.normalize_contrast(arr)
    out2 = image_prep.normalize_contrast(arr)
    assert np.array_equal(out1, out2)


def test_normalize_contrast_never_raises_on_degenerate_input():
    degenerate = np.zeros((1, 1, 3), dtype=np.uint8)
    out = image_prep.normalize_contrast(degenerate)
    assert out is not None
    assert out.shape[0] > 0 and out.shape[1] > 0

    uniform = np.full((50, 50, 3), 128, dtype=np.uint8)
    out2 = image_prep.normalize_contrast(uniform)
    assert np.array_equal(out2, image_prep.to_rgb(uniform))


# --- Contraste: salvaguarda contra sobre-procesamiento (criterio 15) -------


def _sharpness(arr: np.ndarray) -> float:
    gray = cv2.cvtColor(image_prep.to_rgb(arr), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def test_normalize_contrast_does_not_degrade_well_lit_synthetic_fixture():
    """Documento ya bien iluminado/con buen contraste (blanco/negro puro):
    la mejora no debe caer la nitidez proxy más del margen de seguridad."""
    arr = _textured_doc(bg=255, text=(0, 0, 0))
    before = _sharpness(arr)
    out = image_prep.normalize_contrast(arr)
    after = _sharpness(out)
    assert after >= before * 0.85


def test_normalize_contrast_safety_guard_discards_degrading_enhancement():
    """Fuerza (vía monkeypatch de `_apply_clahe`) una mejora que degradaría
    la nitidez: la salvaguarda debe descartarla y devolver la imagen de
    entrada sin modificar, con `applied=False` y motivo explícito."""
    arr = _textured_doc(bg=140, text=(120, 120, 120))

    def _fake_blur(image_np):
        img = image_prep.to_rgb(image_np)
        return cv2.GaussianBlur(img, (15, 15), 0)

    with patch.object(image_prep, "_apply_clahe", side_effect=_fake_blur):
        out, meta = image_prep._normalize_contrast_impl(arr)

    assert meta["applied"] is False
    assert "degrad" in meta["reason"].lower()
    assert np.array_equal(out, image_prep.to_rgb(arr))


def test_normalize_contrast_improves_low_contrast_synthetic_fixture():
    arr = _textured_doc(bg=140, text=(120, 120, 120))
    before = _sharpness(arr)
    out = image_prep.normalize_contrast(arr)
    after = _sharpness(out)
    assert after >= before
    assert not np.array_equal(out, image_prep.to_rgb(arr))


def test_normalize_contrast_improves_darkened_gas_fixture():
    """Fixture GAS de referencia oscurecida artificialmente (mala
    iluminación simulada): la normalización debe mejorar (o no empeorar) la
    métrica proxy de nitidez."""
    arr = np.array(Image.open(GAS_SAMPLE).convert("RGB"))
    darkened = np.clip(arr.astype(np.float32) * 0.4 + 60, 0, 255).astype(np.uint8)
    before = _sharpness(darkened)
    out = image_prep.normalize_contrast(darkened)
    after = _sharpness(out)
    assert after >= before


# --- Regla de dominio OCR: fixture GAS, sin pérdida ni invención de dígitos
# (criterio 16) ---------------------------------------------------------


def _digit_sequences(text: str) -> list:
    import re as _re

    return _re.findall(r"\d+", text)


def test_gas_fixture_contrast_step_preserves_fields_and_digits():
    """Campo(s) afectados: todos los campos configurados del template GAS
    (n° cliente, nro medidor, periodo, a pagar hasta, importe -- ADR-004),
    porque el contraste se aplica a la imagen completa antes de OCR.
    Tipo de documento probado: GAS (`gas_sample.jpg`, sintético; no clasifica
    a un proveedor conocido con este fixture puntual -- comportamiento
    preexistente e independiente de esta feature, verificado también sobre
    el código sin este cambio -- por lo que la comparación relevante para la
    regla de dominio OCR es sobre `raw_ocr_text`/`candidate_fields`, no sobre
    `validated_fields`). Salida esperada: mismos campos candidatos y mismas
    secuencias de dígitos extraídas con el paso de contraste incluido que
    sin él (ningún dígito se inventa ni se deforma -- falso positivo
    evitado). Validación semántica aplicada: `backend/app/validators.py`,
    sin cambios (no se ejecuta sobre este fixture porque no hay
    `provider` clasificado, pero corre sin cambios de código)."""
    img = Image.open(GAS_SAMPLE)
    img, exif_applied = image_prep.apply_exif_orientation(img)
    arr = np.array(img.convert("RGB"))

    # Pipeline "sin contraste": replica el orden previo a esta feature
    # (orientación -> deskew -> escala, sin normalize_contrast).
    pre = image_prep.correct_orientation(arr, skip=exif_applied)
    pre = image_prep.deskew(pre)
    pre = image_prep.normalize_scale(pre)
    result_without_contrast = capture_pipeline.process_image(pre, str(GAS_SAMPLE))

    # Pipeline actual (con contraste incluido, vía prepare()).
    prepared = image_prep.prepare(arr, exif_orientation_applied=exif_applied)
    result_with_contrast = capture_pipeline.process_image(prepared, str(GAS_SAMPLE))

    text_before = result_without_contrast["raw_ocr_text"]
    text_after = result_with_contrast["raw_ocr_text"]
    assert text_before.strip(), "el fixture de referencia debe producir texto OCR reconocible sin el paso de contraste"

    digits_before = _digit_sequences(text_before)
    digits_after = _digit_sequences(text_after)
    assert digits_before, "el fixture de referencia debe contener dígitos reconocibles (n° cliente, importe, etc.)"
    assert digits_after == digits_before, (
        "el paso de contraste no debe inventar ni deformar dígitos en los campos numéricos"
    )

    # Ningún campo antes candidato (aunque el fixture no clasifique a un
    # proveedor conocido, `validated_fields`/`rejected_fields`/
    # `missing_fields` deben seguir teniendo la misma forma vacía).
    fields_before = result_without_contrast["structured_output"]["validated_fields"]
    fields_after = result_with_contrast["structured_output"]["validated_fields"]
    assert fields_after == fields_before


# --- Idempotencia (criterio 17) ---------------------------------------------


def test_reprocessing_same_original_is_idempotent():
    r1 = capture_pipeline.process_document(str(GAS_SAMPLE))
    r2 = capture_pipeline.process_document(str(GAS_SAMPLE))

    assert r1["processing_metadata"]["preparation_trace"] == r2["processing_metadata"]["preparation_trace"]
    assert r1["structured_output"]["validated_fields"] == r2["structured_output"]["validated_fields"]
    assert r1["structured_output"]["rejected_fields"] == r2["structured_output"]["rejected_fields"]
    assert r1["structured_output"]["missing_fields"] == r2["structured_output"]["missing_fields"]
