"""Control de calidad de captura, previo a OCR (feature `06-calidad-captura-mobile`).

Evalúa 8 señales de calidad sobre la imagen ya orientada por EXIF
(`image_prep.apply_exif_orientation`) pero ANTES de `image_prep.prepare`
(deskew/perspectiva/escala) y antes de invocar el motor OCR
(`ocr_engine`/`capture_pipeline.process_image`):

1. Blur/desenfoque (varianza del Laplaciano).
2. Baja resolución (lado menor de la imagen original, en píxeles).
3. Reflejos/glare (componente conexo de píxeles saturados).
4. Sombras / iluminación desigual (varianza de brillo entre bloques de una
   grilla).
5. Documento cortado (el contorno del documento toca el borde del frame en
   más de un lado).
6. Mala perspectiva (deformación del cuadrilátero del documento respecto de
   un rectángulo).
7. Mala iluminación (brillo medio global, sub/sobreexpuesta).
8. Encuadre insuficiente (área del documento / área total de la imagen;
   techo `warn`, nunca dispara `reject` por sí sola).

Las señales 5, 6 y 8 reutilizan la detección de contorno de documento ya
existente en `image_prep.py` (`find_document_contour` /
`largest_contour_bounding_box`, ambas extraídas de la lógica que ya usaba
`image_prep.correct_perspective`) en vez de duplicarla.

Cada señal produce un sub-veredicto (`ok`/`warn`/`reject`, o `None` cuando la
señal no es evaluable, por ejemplo si no se detecta ningún contorno de
documento). El veredicto agregado (`evaluate(...)["verdict"]`) es el peor
sub-veredicto entre todas las señales evaluables.

Ver `docs/tecnica/calidad-captura-mobile.md` para el detalle de cada
heurística, los valores por defecto de los umbrales y su justificación, y
los casos borde contemplados.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

from . import image_prep

# Estado de job usado por `job_queue.py` cuando el veredicto agregado es
# `reject`: distinto de `queued`/`processing`/`ready`/`confirmed`/`failed`.
# Nombre estable, documentado en `docs/tecnica/calidad-captura-mobile.md`.
REJECTED_JOB_STATUS = "needs_new_photo"

# --- umbrales configurables por variable de entorno (globales al sistema,
# no en backend/config/services.ini: este chequeo corre antes de clasificar
# el proveedor/servicio, ver runs/06-calidad-captura-mobile/spec.md,
# "Riesgos / supuestos"). Mismo patrón que
# `upload_validation.max_upload_bytes` (`GI_OCR_MAX_UPLOAD_BYTES`). ---
_DEFAULTS: Dict[str, float] = {
    "GI_OCR_QUALITY_BLUR_REJECT_BELOW": 40.0,
    "GI_OCR_QUALITY_BLUR_WARN_BELOW": 100.0,
    "GI_OCR_QUALITY_MIN_SIDE_REJECT_BELOW": 500.0,
    "GI_OCR_QUALITY_MIN_SIDE_WARN_BELOW": 900.0,
    "GI_OCR_QUALITY_GLARE_BRIGHT_THRESHOLD": 245.0,
    "GI_OCR_QUALITY_GLARE_AREA_WARN_ABOVE": 0.02,
    "GI_OCR_QUALITY_GLARE_AREA_REJECT_ABOVE": 0.06,
    "GI_OCR_QUALITY_GLARE_MAX_BBOX_RATIO": 0.5,
    "GI_OCR_QUALITY_SHADOW_DIFF_WARN_ABOVE": 45.0,
    "GI_OCR_QUALITY_SHADOW_DIFF_REJECT_ABOVE": 80.0,
    "GI_OCR_QUALITY_BRIGHTNESS_DARK_REJECT_BELOW": 40.0,
    "GI_OCR_QUALITY_BRIGHTNESS_DARK_WARN_BELOW": 70.0,
    "GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_WARN_ABOVE": 250.0,
    "GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE": 254.5,
    "GI_OCR_QUALITY_EDGE_TOUCH_MARGIN_RATIO": 0.015,
    "GI_OCR_QUALITY_CUT_MIN_AREA_RATIO": 0.15,
    "GI_OCR_QUALITY_CONTOUR_MIN_AREA_RATIO": 0.01,
    "GI_OCR_QUALITY_PERSPECTIVE_RATIO_WARN_ABOVE": 1.25,
    "GI_OCR_QUALITY_PERSPECTIVE_RATIO_REJECT_ABOVE": 1.6,
    "GI_OCR_QUALITY_FRAME_FILL_WARN_BELOW": 0.35,
}


def _threshold(name: str) -> float:
    """Lee un umbral desde variable de entorno, con default razonable si no
    está definida, está vacía o no es un float válido (mismo patrón de
    tolerancia que `upload_validation.max_upload_bytes`)."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return _DEFAULTS[name]
    try:
        return float(raw.strip())
    except ValueError:
        return _DEFAULTS[name]


# Mensajes por señal y severidad. Identificador de señal (clave externa)
# estable e independiente del texto exacto (criterio 21 del spec, caso
# borde de "baja resolución por limitación real del dispositivo").
REASON_MESSAGES: Dict[str, Dict[str, str]] = {
    "blur": {
        "warn": "La imagen se ve algo borrosa; el resultado puede ser menos preciso.",
        "reject": "La imagen está demasiado borrosa para leerse. Tomá la foto de nuevo, sosteniendo el celular firme.",
    },
    "low_resolution": {
        "warn": "La imagen tiene resolución algo baja; el resultado puede ser menos preciso.",
        "reject": (
            "La imagen tiene muy poca resolución. Si tu dispositivo no permite una foto "
            "de mayor calidad, el resultado puede no ser preciso."
        ),
    },
    "glare": {
        "warn": "Hay un reflejo de luz sobre parte del documento.",
        "reject": "Hay un reflejo de luz que tapa parte del texto. Evitá superficies reflectantes o cambiá el ángulo.",
    },
    "uneven_lighting": {
        "warn": "La iluminación es despareja (sombra parcial sobre el documento).",
        "reject": "Hay una sombra marcada que tapa parte del documento. Buscá una luz más pareja.",
    },
    "document_cropped": {
        "reject": (
            "El documento está cortado en el encuadre. "
            "Volvé a fotografiarlo completo, sin que se salga del cuadro."
        ),
    },
    "bad_perspective": {
        "warn": "El documento está fotografiado en ángulo; el resultado puede ser menos preciso.",
        "reject": "El documento está muy inclinado en la foto. Fotografialo de frente, lo más plano posible.",
    },
    "poor_lighting": {
        "warn": "La foto está algo oscura o muy clara; el resultado puede ser menos preciso.",
        "reject": "La foto está demasiado oscura o sobreexpuesta para leerse. Buscá mejor luz.",
    },
    "insufficient_framing": {
        "warn": "El documento ocupa poco espacio en el encuadre; acercate un poco más.",
    },
}

_SEVERITY_ORDER = {"ok": 0, "warn": 1, "reject": 2}


# --- señales individuales: cada una devuelve (metrica, severidad) o
# (None, None) cuando no es evaluable. ---


def _blur_signal(gray: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
    metric = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    reject_below = _threshold("GI_OCR_QUALITY_BLUR_REJECT_BELOW")
    warn_below = _threshold("GI_OCR_QUALITY_BLUR_WARN_BELOW")
    if metric < reject_below:
        return metric, "reject"
    if metric < warn_below:
        return metric, "warn"
    return metric, "ok"


def _resolution_signal(h: int, w: int) -> Tuple[Optional[float], Optional[str]]:
    metric = float(min(h, w))
    reject_below = _threshold("GI_OCR_QUALITY_MIN_SIDE_REJECT_BELOW")
    warn_below = _threshold("GI_OCR_QUALITY_MIN_SIDE_WARN_BELOW")
    if metric < reject_below:
        return metric, "reject"
    if metric < warn_below:
        return metric, "warn"
    return metric, "ok"


def _glare_signal(gray: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
    bright_threshold = _threshold("GI_OCR_QUALITY_GLARE_BRIGHT_THRESHOLD")
    mask = (gray >= bright_threshold).astype(np.uint8)
    h, w = gray.shape[:2]
    total = float(h * w)
    if total <= 0 or mask.sum() == 0:
        return 0.0, "ok"
    n_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n_labels <= 1:
        return 0.0, "ok"
    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = int(np.argmax(areas)) + 1
    comp_area = float(stats[idx, cv2.CC_STAT_AREA])
    comp_w = float(stats[idx, cv2.CC_STAT_WIDTH])
    comp_h = float(stats[idx, cv2.CC_STAT_HEIGHT])
    area_ratio = comp_area / total
    bbox_ratio = (comp_w * comp_h) / total

    max_bbox_ratio = _threshold("GI_OCR_QUALITY_GLARE_MAX_BBOX_RATIO")
    if bbox_ratio > max_bbox_ratio:
        # Brillo difuso, no concentrado en una zona compacta (ej. fondo de
        # papel blanco uniforme): no se cuenta como reflejo. Si además el
        # brillo medio global es alto, lo captura la señal de "mala
        # iluminación" (poor_lighting), que sí mira el nivel absoluto.
        return area_ratio, "ok"

    reject_above = _threshold("GI_OCR_QUALITY_GLARE_AREA_REJECT_ABOVE")
    warn_above = _threshold("GI_OCR_QUALITY_GLARE_AREA_WARN_ABOVE")
    if area_ratio > reject_above:
        return area_ratio, "reject"
    if area_ratio > warn_above:
        return area_ratio, "warn"
    return area_ratio, "ok"


def _shadow_signal(gray: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
    h, w = gray.shape[:2]
    rows, cols = 4, 4
    if h < rows or w < cols:
        return 0.0, "ok"
    means: List[float] = []
    for r in range(rows):
        y0, y1 = int(r * h / rows), int((r + 1) * h / rows)
        for c in range(cols):
            x0, x1 = int(c * w / cols), int((c + 1) * w / cols)
            block = gray[y0:y1, x0:x1]
            if block.size == 0:
                continue
            means.append(float(block.mean()))
    if not means:
        return 0.0, "ok"
    metric = max(means) - min(means)
    warn_above = _threshold("GI_OCR_QUALITY_SHADOW_DIFF_WARN_ABOVE")
    reject_above = _threshold("GI_OCR_QUALITY_SHADOW_DIFF_REJECT_ABOVE")
    if metric > reject_above:
        return metric, "reject"
    if metric > warn_above:
        return metric, "warn"
    return metric, "ok"


def _illumination_signal(gray: np.ndarray) -> Tuple[Optional[float], Optional[str]]:
    metric = float(gray.mean())
    dark_reject = _threshold("GI_OCR_QUALITY_BRIGHTNESS_DARK_REJECT_BELOW")
    dark_warn = _threshold("GI_OCR_QUALITY_BRIGHTNESS_DARK_WARN_BELOW")
    bright_warn = _threshold("GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_WARN_ABOVE")
    bright_reject = _threshold("GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE")
    if metric < dark_reject or metric > bright_reject:
        return metric, "reject"
    if metric < dark_warn or metric > bright_warn:
        return metric, "warn"
    return metric, "ok"


def _document_geometry(img: np.ndarray) -> Dict[str, Any]:
    """Detección de contorno de documento compartida (`image_prep.py`) para
    las señales de corte/perspectiva/encuadre. Nunca lanza excepción: ante
    cualquier error de OpenCV, degrada a "no evaluable" (quad/bbox `None`)."""
    h, w = img.shape[:2]
    quad = None
    bbox = None
    quad_area_ratio = None
    try:
        contour_ratio = _threshold("GI_OCR_QUALITY_CONTOUR_MIN_AREA_RATIO")
        quad = image_prep.find_document_contour(img, min_area_ratio=contour_ratio)
        if quad is not None:
            quad_area_ratio = float(cv2.contourArea(quad.astype(np.float32))) / float(h * w)
    except Exception:
        quad = None
        quad_area_ratio = None
    try:
        bbox = image_prep.largest_contour_bounding_box(img)
    except Exception:
        bbox = None
    return {"h": h, "w": w, "quad": quad, "bbox": bbox, "quad_area_ratio": quad_area_ratio}


def _cut_signal(geom: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Documento cortado: el bounding box del contorno de bordes más grande
    toca o cruza el borde del frame en más de un lado, con área
    significativa (ver `docs/tecnica/calidad-captura-mobile.md` para la
    tolerancia de margen y por qué se usa el bounding box, no el
    cuadrilátero cerrado, para esta señal específica)."""
    bbox = geom["bbox"]
    h, w = geom["h"], geom["w"]
    if bbox is None or h <= 0 or w <= 0:
        return None, None
    x, y, bw, bh = bbox
    area_ratio = (bw * bh) / float(h * w)
    min_area_ratio = _threshold("GI_OCR_QUALITY_CUT_MIN_AREA_RATIO")
    if area_ratio < min_area_ratio:
        return area_ratio, "ok"
    margin_ratio = _threshold("GI_OCR_QUALITY_EDGE_TOUCH_MARGIN_RATIO")
    margin_x = max(1, int(w * margin_ratio))
    margin_y = max(1, int(h * margin_ratio))
    touches = 0
    if x <= margin_x:
        touches += 1
    if y <= margin_y:
        touches += 1
    if x + bw >= w - margin_x:
        touches += 1
    if y + bh >= h - margin_y:
        touches += 1
    if touches >= 2:
        return area_ratio, "reject"
    return area_ratio, "ok"


def _perspective_signal(geom: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Mala perspectiva: deformación del cuadrilátero detectado respecto de
    un rectángulo (relación entre lados opuestos). Si no se detectó un
    cuadrilátero de 4 lados claro, esta señal no es evaluable (`None, None`)
    — cede el resultado a la señal de "documento cortado" en vez de
    reportar una segunda razón redundante por la misma causa raíz (ver
    "Casos borde" en `runs/06-calidad-captura-mobile/spec.md` y el detalle
    en `docs/tecnica/calidad-captura-mobile.md`)."""
    quad = geom["quad"]
    if quad is None:
        return None, None
    tl, tr, br, bl = quad
    top = float(np.linalg.norm(tr - tl))
    bottom = float(np.linalg.norm(br - bl))
    left = float(np.linalg.norm(bl - tl))
    right = float(np.linalg.norm(br - tr))
    if min(top, bottom, left, right) < 1e-6:
        return None, None
    ratio_h = max(top, bottom) / min(top, bottom)
    ratio_v = max(left, right) / min(left, right)
    metric = max(ratio_h, ratio_v)
    warn_above = _threshold("GI_OCR_QUALITY_PERSPECTIVE_RATIO_WARN_ABOVE")
    reject_above = _threshold("GI_OCR_QUALITY_PERSPECTIVE_RATIO_REJECT_ABOVE")
    if metric > reject_above:
        return metric, "reject"
    if metric > warn_above:
        return metric, "warn"
    return metric, "ok"


def _framing_signal(geom: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Encuadre insuficiente: área del cuadrilátero del documento / área
    total. Techo `warn`, nunca dispara `reject` por sí sola (ver "Riesgos /
    supuestos" del spec). Si no se detecta ningún contorno de documento
    claro, no inventa un área: degrada a "no evaluable" sin afectar el
    veredicto agregado por esta señal."""
    ratio = geom["quad_area_ratio"]
    if ratio is None:
        return None, None
    warn_below = _threshold("GI_OCR_QUALITY_FRAME_FILL_WARN_BELOW")
    if ratio < warn_below:
        return ratio, "warn"
    return ratio, "ok"


def _safe_signal(
    fn: Callable[..., Tuple[Optional[float], Optional[str]]], *args: Any
) -> Tuple[Optional[float], Optional[str]]:
    """Nunca deja escapar una excepción: una imagen sintética/degenerada
    (todo negro, todo blanco, dimensiones extremas) degrada la señal
    correspondiente a "no evaluable" en vez de romper el pipeline con un
    500 (ver "Casos borde" del spec)."""
    try:
        return fn(*args)
    except Exception:
        return None, None


def evaluate(image_np: np.ndarray) -> Dict[str, Any]:
    """Evalúa las 8 señales de calidad sobre `image_np` (imagen ya orientada
    por EXIF, RGB, ANTES de `image_prep.prepare` y de OCR). Nunca lanza
    excepción.

    Devuelve:
        {
          "verdict": "ok" | "warn" | "reject",
          "reasons": [{"signal": <id>, "severity": "warn"|"reject", "message": <str>}, ...],
          "signals": {<id>: {"metric": float | None, "verdict": "ok"|"warn"|"reject"|"not_evaluable"}, ...},
        }
    """
    img = image_prep.to_rgb(image_np)
    h, w = img.shape[:2]
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    except Exception:
        gray = None

    signals: Dict[str, Any] = {}
    reasons: List[Dict[str, str]] = []

    def _add(signal_id: str, metric_severity: Tuple[Optional[float], Optional[str]]) -> None:
        metric, severity = metric_severity
        signals[signal_id] = {
            "metric": None if metric is None else round(float(metric), 4),
            "verdict": severity if severity is not None else "not_evaluable",
        }
        if severity in ("warn", "reject"):
            reasons.append(
                {
                    "signal": signal_id,
                    "severity": severity,
                    "message": REASON_MESSAGES[signal_id][severity],
                }
            )

    if gray is not None:
        _add("blur", _safe_signal(_blur_signal, gray))
        _add("glare", _safe_signal(_glare_signal, gray))
        _add("uneven_lighting", _safe_signal(_shadow_signal, gray))
        _add("poor_lighting", _safe_signal(_illumination_signal, gray))
    else:
        for signal_id in ("blur", "glare", "uneven_lighting", "poor_lighting"):
            _add(signal_id, (None, None))

    _add("low_resolution", _safe_signal(_resolution_signal, h, w))

    geom = _document_geometry(img)
    _add("document_cropped", _safe_signal(_cut_signal, geom))
    _add("bad_perspective", _safe_signal(_perspective_signal, geom))
    _add("insufficient_framing", _safe_signal(_framing_signal, geom))

    worst = "ok"
    for r in reasons:
        if _SEVERITY_ORDER[r["severity"]] > _SEVERITY_ORDER[worst]:
            worst = r["severity"]

    return {"verdict": worst, "reasons": reasons, "signals": signals}


__all__ = [
    "REJECTED_JOB_STATUS",
    "REASON_MESSAGES",
    "evaluate",
]
