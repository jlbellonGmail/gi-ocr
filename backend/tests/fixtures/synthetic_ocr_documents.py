"""Generadores deterministas de imágenes sintéticas para
`backend/tests/test_ocr_regression_dataset.py` (feature
`08-regresion-dataset-ocr`).

No es un módulo de test (no matchea `test_*.py`/`*_test.py`, ver
`pytest.ini`): pytest no lo colecciona, sólo se importa desde el módulo de
test. Vive en `fixtures/` junto a `gas_sample.jpg` (patrón ya existente en
este directorio).

Genera cada imagen en memoria (nunca se persiste como archivo versionado,
ver "Decisión: fixtures generadas en tiempo de test" en
`docs/tecnica/regresion-dataset-ocr.md`). Todo el contenido es ficticio,
dibujado por código: ningún comprobante real, ninguna dependencia de
`storage_bridge/` (regla de dominio OCR de `AGENTS.md`).

Adapta (no reutiliza tal cual) `scripts/benchmark_captura.py::_base_case_image`:
mismas posiciones relativas de campo por proveedor (ya alineadas contra las
bandas ROI de `backend/app/templates/providers.py`), pero:

- Fondo gris uniforme (`_BACKGROUND_GRAY = 210`) en vez de blanco puro
  (255,255,255). `_base_case_image` nunca se había ejercitado contra
  `quality_gate.evaluate` con el motor OCR real antes de esta feature
  (ver `runs/08-regresion-dataset-ocr/audit-2.md`, hallazgo no
  bloqueante); un canvas blanco puro con poco texto queda peligrosamente
  cerca del umbral de brillo `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE`
  (254.5). Verificado empíricamente (ver decision.md): con fondo gris 210,
  el brillo medio queda ~207-208 en las cuatro fixtures de esta suite, con
  margen amplio respecto de los umbrales `warn`/`reject` (250/254.5) y del
  umbral `dark` (40/70) en ambos extremos.
- Canvas más grande (1400x1960 en vez de 1000x1400) para separar mejor,
  en píxeles absolutos, campos cuyas bandas ROI son adyacentes o se
  superponen levemente (ver casos borde de
  `runs/08-regresion-dataset-ocr/spec.md`, "dos campos que compiten por el
  mismo patrón textual") — evita que el detector de texto fusione dos
  campos en una sola caja, y evita que el bounding box de un campo
  (`vencimiento`, con fecha completa) haga bleed hacia la banda de un
  campo vecino (`periodo`) cuyo regex es un subconjunto del de una fecha
  completa.
- Un borde rectangular fino agrega densidad de bordes (métrica de blur =
  varianza del Laplaciano) sin interferir con ninguna banda de campo,
  alejando aún más el veredicto de `quality_gate` del umbral de rechazo
  por desenfoque.
- Fallback de fuente mejorado: si no hay `arial.ttf`/`DejaVuSans.ttf`
  instaladas (posible en un runner de CI mínimo), usa
  `ImageFont.load_default(size=...)` (fuente escalable embebida en Pillow
  desde 10.1) en vez de `ImageFont.load_default()` sin tamaño (bitmap
  diminuto ~10px) que usa `scripts/benchmark_captura.py::_font`. Verificado
  empíricamente (ver decision.md) que, forzando este fallback, el motor OCR
  real sigue extrayendo y validando todos los campos igual que con
  `arial.ttf`.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

CANVAS_WIDTH = 1400
CANVAS_HEIGHT = 1960
_BACKGROUND_GRAY = 210
_BORDER_GRAY = 60
_TEXT_FILL = (15, 15, 15)


def _font(size: int) -> ImageFont.ImageFont:
    """Prioriza TrueType (mejor legibilidad para el motor OCR real); si no
    hay ninguna disponible, usa la fuente escalable embebida de Pillow con
    el tamaño pedido -- nunca la bitmap fija de `ImageFont.load_default()`
    sin argumentos (ver docstring del módulo)."""
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - Pillow < 10.1 sin soporte de size
        return ImageFont.load_default()


def _draw_text(img: Image.Image, x: float, y: float, text: str, size: int) -> None:
    draw = ImageDraw.Draw(img)
    draw.text((int(img.width * x), int(img.height * y)), text, fill=_TEXT_FILL, font=_font(size))


def _canvas() -> Image.Image:
    img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (_BACKGROUND_GRAY, _BACKGROUND_GRAY, _BACKGROUND_GRAY))
    margin = int(CANVAS_WIDTH * 0.05)
    ImageDraw.Draw(img).rectangle(
        [margin, margin, CANVAS_WIDTH - margin, CANVAS_HEIGHT - margin],
        outline=(_BORDER_GRAY, _BORDER_GRAY, _BORDER_GRAY),
        width=4,
    )
    return img


def build_litoral_gas_image(periodo: str = "06/2026") -> Tuple[Image.Image, Dict[str, Any]]:
    """Documento `LITORAL_GAS` sintético. `periodo` parametrizable para
    reutilizar exactamente el mismo layout en el caso "válido completo" y en
    el caso "campo semánticamente inválido" (evita duplicar coordenadas).

    Las posiciones están calibradas para caer, con margen, dentro de las
    bandas ROI de `litoral_gas_template()` (`backend/app/templates/providers.py`)
    y fuera de las bandas de campos vecinos -- ver decision.md para el
    detalle de la calibración (caso concreto: `vencimiento` se dibuja más
    arriba en su propia banda para que el centro de su caja OCR no caiga
    dentro de la banda de `periodo`, que de otro modo capturaría por
    sustring el propio valor de `vencimiento` en vez del de `periodo`).
    """
    img = _canvas()
    _draw_text(img, 0.42, 0.170, "Litoral Gas", 32)
    _draw_text(img, 0.70, 0.190, "0001-00001234", 32)
    _draw_text(img, 0.72, 0.205, "05/06/2026", 32)
    _draw_text(img, 0.77, 0.249, "20/06/2026", 30)
    _draw_text(img, 0.66, 0.280, "12345678", 32)
    _draw_text(img, 0.80, 0.278, periodo, 32)
    _draw_text(img, 0.72, 0.855, "$ 12.345,67", 32)
    expected_fields: Dict[str, Any] = {
        "provider": "LITORAL_GAS",
        "cliente": "12345678",
        "periodo": periodo,
        "comprobante": "0001-00001234",
        "fecha_emision": "05/06/2026",
        "vencimiento": "20/06/2026",
        "total": 12345.67,
    }
    return img, expected_fields


def build_cevt_image() -> Tuple[Image.Image, Dict[str, Any]]:
    """Documento `CEVT` sintético, con todos los `required_fields` de
    `cevt_template()`."""
    img = _canvas()
    _draw_text(img, 0.06, 0.035, "Cooperativa Electrica CEVT", 24)
    _draw_text(img, 0.46, 0.040, "Periodo: 06/2026 0002-00004321", 22)
    _draw_text(img, 0.56, 0.065, "05/06/2026", 22)
    _draw_text(img, 0.56, 0.085, "20/06/2026", 22)
    _draw_text(img, 0.60, 0.165, "99887766", 22)
    _draw_text(img, 0.22, 0.205, "Medidor 123456789", 22)
    _draw_text(img, 0.10, 0.485, "Cliente 11223344", 22)
    _draw_text(img, 0.60, 0.330, "$ 45.678,90", 22)
    expected_fields: Dict[str, Any] = {
        "provider": "CEVT",
        "cliente": "11223344",
        "medidor": "123456789",
        "periodo": "06/2026",
        "comprobante": "0002-00004321",
        "fecha_emision": "05/06/2026",
        "vencimiento": "20/06/2026",
        "codigo_pago_electronico": "99887766",
        "total": 45678.90,
    }
    return img, expected_fields


def build_unknown_document_image() -> Image.Image:
    """Documento "no reconocido": texto legible/nítido, misma calidad de
    imagen que los fixtures válidos (mismo fondo, mismo borde, mismo tamaño
    de fuente), pero sin ninguna `classify_keyword` de `LITORAL_GAS`
    (`"litoral gas"`, `"litoralgas"`, `"litoral"`) ni de `CEVT` (`"cevt"`,
    `"cooperativa"`, `"electri"`), ni ninguna subcadena que las contenga
    (ver `backend/app/templates/providers.py`)."""
    img = _canvas()
    _draw_text(img, 0.10, 0.10, "Comprobante Generico de Servicio", 32)
    _draw_text(img, 0.10, 0.22, "Fecha: 05/06/2026", 32)
    _draw_text(img, 0.10, 0.34, "Monto: $ 999,00", 32)
    _draw_text(img, 0.10, 0.46, "Referencia: XZ-000000", 32)
    return img


__all__ = [
    "CANVAS_WIDTH",
    "CANVAS_HEIGHT",
    "build_litoral_gas_image",
    "build_cevt_image",
    "build_unknown_document_image",
]
