"""Preprocesamiento de imagen: corrección de orientación, perspectiva, escala y
contraste/iluminación.

Mejoras robustas (OpenCV) que no dependen de píxeles absolutos. Las plantillas usan
coordenadas normalizadas; la corrección aquí hace que el layout se alinee a esas bandas.

La corrección de orientación EXIF (`apply_exif_orientation`) es un paso previo y
distinto a `correct_orientation`: opera sobre la imagen PIL original (con metadata)
ANTES de convertir a `np.ndarray`, mientras que `correct_orientation` es una
heurística de contenido (varianza de gradiente) que opera sobre el array ya sin
metadata. Ver `docs/tecnica/correccion-orientacion-exif.md` para el detalle
completo y la relación entre ambas.

Traza de transformaciones (feature `07-preprocesamiento-documental-no-destructivo`):
`prepare()` acepta un parámetro opcional `trace` (lista mutable) donde registra, en
orden de ejecución, una entrada por cada paso que corre dentro de la función
(`correct_orientation`, `deskew`, `correct_perspective`, `normalize_scale`,
`normalize_contrast`), con el formato `{"step": str, "applied": bool, ...}`. Cada
función pública (`deskew`, `correct_perspective`, `normalize_scale`,
`normalize_contrast`, `correct_orientation`) sigue devolviendo únicamente
`np.ndarray` (sin cambios de firma, no rompe a quien ya las llama directo); la
metadata enriquecida para la traza se calcula en funciones internas `_*_impl` que
`prepare()` invoca directamente para no duplicar cómputo. Ver
`docs/tecnica/preprocesamiento-documental-no-destructivo.md` para el detalle
completo del formato y las decisiones de diseño.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps


def apply_exif_orientation(image: Image.Image) -> Tuple[Image.Image, bool]:
    """Aplica el tag EXIF `Orientation` (1-8) a una imagen PIL recién abierta.

    Usa `PIL.ImageOps.exif_transpose`, que interpreta los 8 valores estándar
    (rotaciones de 90/180/270 y variantes espejadas) y devuelve una nueva
    imagen ya orientada "de pie". Si la imagen no tiene EXIF, no tiene el tag
    `Orientation`, o el valor es inválido/corrupto, Pillow simplemente no
    modifica nada (degrada con gracia, no lanza excepción en el caso normal).

    Devuelve una tupla `(imagen_corregida, se_aplico_correccion)`:
    - `se_aplico_correccion` es `True` únicamente cuando el tag `Orientation`
      estaba presente con un valor distinto de 1 (es decir, cuando
      `exif_transpose` efectivamente transformó los píxeles). Esto permite a
      quien orquesta el pipeline decidir si subordinar heurísticas
      posteriores de orientación por contenido (ver `correct_orientation`).

    No debe lanzar excepción por EXIF corrupto: cualquier error inesperado al
    leer el tag se trata como "sin corrección EXIF disponible" y se devuelve
    la imagen original sin modificar.
    """
    orientation_tag = None
    try:
        exif = image.getexif()
        if exif:
            orientation_tag = exif.get(0x0112)  # 274, tag EXIF "Orientation"
    except Exception:
        orientation_tag = None

    try:
        transposed = ImageOps.exif_transpose(image)
    except Exception:
        return image, False
    if transposed is None:
        return image, False

    applied = isinstance(orientation_tag, int) and not isinstance(orientation_tag, bool) and 2 <= orientation_tag <= 8
    return transposed, applied


def to_rgb(image_np: np.ndarray) -> np.ndarray:
    if image_np.ndim == 2:
        return cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    if image_np.shape[2] == 4:
        return cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
    return image_np


def _correct_orientation_impl(image_np: np.ndarray, skip: bool) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Implementación interna de `correct_orientation` que además devuelve
    metadata suficiente para la traza (`prepare()`), sin duplicar cómputo entre
    la función pública y el trazado."""
    img = to_rgb(image_np)
    if skip:
        return img, {
            "applied": False,
            "reason": "omitido: orientación ya corregida por EXIF (apply_exif_orientation)",
        }
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Heurística de orientación: el texto tiende a tener más bordes horizontales
        # que verticales cuando está derecho. Comparar varianza de.gradiente.
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        var_x = float(np.var(gx))
        var_y = float(np.var(gy))
        # Si la imagen está rotada 90/270, las relaciones se invierten fuerte.
        h, w = img.shape[:2]
        if var_y > var_x * 2.2 and h < w:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE), {
                "applied": True,
                "reason": "rotado 90° clockwise por heurística de contenido",
                "rotation": "90_cw",
            }
        if var_x > var_y * 2.2 and w < h:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE), {
                "applied": True,
                "reason": "rotado 90° counterclockwise por heurística de contenido",
                "rotation": "90_ccw",
            }
    except Exception:
        return img, {"applied": False, "reason": "error interno en la heurística, sin cambios", "error": True}
    return img, {"applied": False, "reason": "no fue necesario (orientación ya correcta)"}


def correct_orientation(image_np: np.ndarray, skip: bool = False) -> np.ndarray:
    """Corrigerotación 0/90/180/270 usando OSD del detector de texto de OpenCV
    (no siempre disponible). Fallback: detecta orientación por densidad de bordes
    comparando proyecciones (heurística ligera, no destructiva).

    `skip=True` subordina esta heurística: se usa cuando aguas arriba
    (`apply_exif_orientation`) ya se aplicó una corrección EXIF válida sobre la
    misma imagen, para evitar doble corrección (EXIF ya dejó la imagen "de pie";
    volver a rotarla por heurística de contenido la desorientaría de nuevo). Si
    no hubo corrección EXIF utilizable, esta heurística sigue corriendo igual
    que antes (comportamiento sin regresión)."""
    img, _meta = _correct_orientation_impl(image_np, skip)
    return img


def _deskew_impl(image_np: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Implementación interna de `deskew` que además devuelve metadata (ángulo
    estimado, si se aplicó o no y por qué) para la traza de `prepare()`."""
    img = to_rgb(image_np)
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # cv2.cvtColor(..., COLOR_RGB2GRAY) siempre devuelve un ndarray
        # uint8 en runtime; los stubs de cv2/numpy no lo tipan lo bastante
        # preciso y mypy infiere un dtype que incluye floating, para el
        # cual '~' (invert bit a bit) no esta definido -> type: ignore.
        bw = cv2.adaptiveThreshold(
            ~gray,  # type: ignore[misc]
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,
            -2,
        )
        h, w = bw.shape
        # kernel horizontal largo -> detecta líneas de texto
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 30, 1), 1))
        opened = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel)
        coords = np.column_stack(np.where(opened > 0))
        if len(coords) < 50:
            return img, {"applied": False, "reason": "contenido insuficiente para estimar ángulo de skew"}
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.1 or abs(angle) > 5:
            return img, {
                "applied": False,
                "reason": "ángulo despreciable o fuera de rango corregible (±5°)",
                "angle_deg": round(float(angle), 3),
            }
        (h2, w2) = img.shape[:2]
        M = cv2.getRotationMatrix2D((w2 / 2, h2 / 2), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w2, h2), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated, {
            "applied": True,
            "reason": "skew corregido por rotación",
            "angle_deg": round(float(angle), 3),
        }
    except Exception:
        return img, {"applied": False, "reason": "error interno, sin cambios", "error": True}


def deskew(image_np: np.ndarray) -> np.ndarray:
    """Corrige skew leve (< 5°) usando proyección horizontal de texto."""
    img, _meta = _deskew_impl(image_np)
    return img


def _document_edge_contours(image_np: np.ndarray):
    """Contornos crudos (sin ordenar ni filtrar) sobre el mapa de bordes
    (Canny) de la imagen: base compartida por `correct_perspective`
    (deskew/perspectiva) y por el control de calidad de captura
    (`quality_gate.py`, feature `06-calidad-captura-mobile`) para detectar
    el borde del documento fotografiado, sin duplicar la lógica de
    detección en dos lugares. Cada función que la usa ordena estos
    contornos según el criterio que le interesa (ver `find_document_contour`
    y `largest_contour_bounding_box`).
    """
    img = to_rgb(image_np)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 75, 200)
    cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    return cnts


def find_document_contour(image_np: np.ndarray, min_area_ratio: float = 0.3) -> Optional[np.ndarray]:
    """Cuadrilátero del documento detectado por bordes (Canny + findContours +
    approxPolyDP), ordenado `(tl, tr, br, bl)` como `np.ndarray` de forma
    `(4, 2)`, o `None` si no se encuentra un cuadrilátero de 4 lados con área
    mayor a `min_area_ratio` del total de la imagen.

    Candidatos ordenados por área ENCERRADA (`cv2.contourArea`, mayor
    primero): para un documento fotografiado de forma normal (contorno
    cerrado), esa área domina ampliamente sobre cualquier trazo de texto u
    otro ruido de la imagen.

    `correct_perspective` la usa con su umbral histórico (`0.3`, sin cambio de
    comportamiento). `quality_gate.py` la reutiliza con un umbral más laxo
    para las señales de "mala perspectiva" y "encuadre insuficiente" (ver
    `docs/tecnica/calidad-captura-mobile.md`).
    """
    img = to_rgb(image_np)
    h, w = img.shape[:2]
    try:
        cnts = sorted(_document_edge_contours(img), key=cv2.contourArea, reverse=True)[:5]
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4 and cv2.contourArea(c) > min_area_ratio * h * w:
                return _order_points(approx.reshape(4, 2).astype(np.float32))
    except Exception:
        return None
    return None


def largest_contour_bounding_box(image_np: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """Bounding box `(x, y, w, h)` del contorno de bordes con mayor extensión
    espacial (`w * h` del bounding box, no área encerrada), sin exigir que
    cierre en un cuadrilátero de 4 lados.

    Un documento que se sale del encuadre produce un contorno de bordes
    *abierto* (no hay gradiente detectable exactamente en el borde del
    frame, ver `docs/tecnica/calidad-captura-mobile.md`), cuya área
    ENCERRADA es casi nula (es apenas el trazo del borde, no el interior del
    documento) — por eso esta función ordena por área de *bounding box* y no
    por `cv2.contourArea` como `find_document_contour`: así el contorno
    abierto del documento (que sí tiene un bounding box grande, aunque
    encierre poca área) no pierde frente a un trazo de texto pequeño pero
    cerrado. Devuelve `None` si no hay ningún contorno detectable.
    """
    img = to_rgb(image_np)
    try:
        cnts = _document_edge_contours(img)
        if not cnts:
            return None
        best = max(cnts, key=lambda c: _bbox_area(c))
        x, y, cw, ch = cv2.boundingRect(best)
        return int(x), int(y), int(cw), int(ch)
    except Exception:
        return None


def _bbox_area(contour: np.ndarray) -> int:
    _, _, w, h = cv2.boundingRect(contour)
    return int(w) * int(h)


def _correct_perspective_impl(image_np: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Implementación interna de `correct_perspective`, invocada solo cuando ya
    se decidió intentar la corrección (ver `prepare()`, que distingue "omitido
    porque no se pidió" de "intentado pero sin cuadrilátero claro" sin llamar a
    esta función en el primer caso)."""
    img = to_rgb(image_np)
    try:
        rect = find_document_contour(img, min_area_ratio=0.3)
        if rect is None:
            return img, {"applied": False, "reason": "intentado, no se encontró cuadrilátero claro"}
        (tl, tr, br, bl) = rect
        width = max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))
        height = max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))
        if width < 10 or height < 10:
            return img, {"applied": False, "reason": "cuadrilátero degenerado (<10px de lado)"}
        dst = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float32,
        )
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (int(width), int(height)))
        return warped, {
            "applied": True,
            "reason": "perspectiva corregida por cuadrilátero detectado",
            "width": int(width),
            "height": int(height),
        }
    except Exception:
        return img, {"applied": False, "reason": "error interno, sin cambios", "error": True}


def correct_perspective(image_np: np.ndarray) -> np.ndarray:
    """Corrección de perspectiva basada en detección del borde del documento.

    Detecta el contorno más grande y rectifica a su bounding box. Si no encuentra
    un cuadrilátero claro, devuelve la imagen original (no destructivo).
    """
    img, _meta = _correct_perspective_impl(image_np)
    return img


def _order_points(pts):
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _normalize_scale_impl(image_np: np.ndarray, max_side: int) -> Tuple[np.ndarray, Dict[str, Any]]:
    img = to_rgb(image_np)
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img, {
            "applied": False,
            "reason": "ya dentro del límite (no se achica)",
            "original_size": [int(w), int(h)],
            "final_size": [int(w), int(h)],
            "scale_factor": 1.0,
        }
    scale = max_side / m
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, {
        "applied": True,
        "reason": "reescalado al lado mayor máximo permitido",
        "original_size": [int(w), int(h)],
        "final_size": [int(new_w), int(new_h)],
        "scale_factor": round(float(scale), 4),
    }


def normalize_scale(image_np: np.ndarray, max_side: int = 1600) -> np.ndarray:
    """Escala la imagen para que el lado mayor sea <= max_side (mantiene aspecto)."""
    img, _meta = _normalize_scale_impl(image_np, max_side)
    return img


CONTRAST_METHOD = "clahe_lab_l_channel"
_CONTRAST_CLIP_LIMIT = 2.0
_CONTRAST_TILE_GRID = (8, 8)
# Documentos casi perfectamente planos (fondo uniforme, sin texto detectable
# en absoluto) no tienen nada que normalizar: intentar mejorarlos arriesga
# "inventar" textura a partir de ruido de compresión. Umbral bajo a propósito
# (ver docs/tecnica/preprocesamiento-documental-no-destructivo.md).
_CONTRAST_MIN_STD_TO_ATTEMPT = 1.0
# Salvaguarda contra sobre-procesamiento (ítem 07 de ROADMAP.md: "evitando
# que una mejora visual destruya ROI o datos útiles"): si aplicar CLAHE
# bajara la nitidez (proxy: varianza del Laplaciano, la misma métrica que usa
# `quality_gate._blur_signal`) más de este margen relativo, se descarta el
# resultado y se conserva la imagen de entrada sin modificar. Calibrado
# empíricamente sobre `backend/tests/fixtures/gas_sample.jpg` (variación real
# observada: -2%, muy por debajo del 10% tolerado) y una fixture sintética de
# bajo contraste (mejora observada: +170%), ver
# `docs/tecnica/preprocesamiento-documental-no-destructivo.md`.
_CONTRAST_SHARPNESS_SAFETY_MARGIN = 0.9


def _contrast_metric(image_np: np.ndarray) -> float:
    """Proxy de contraste/iluminación: desvío estándar de la intensidad en
    escala de grises. Se reporta en la traza como dato informativo (criterio
    10), y se usa para detectar el caso degenerado de imagen casi uniforme."""
    img = to_rgb(image_np)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return float(np.std(gray))


def _sharpness_metric(image_np: np.ndarray) -> float:
    """Proxy de nitidez/legibilidad: varianza del Laplaciano en escala de
    grises (misma métrica que `quality_gate._blur_signal`). Es la base de la
    salvaguarda contra sobre-procesamiento: si la normalización de contraste
    bajara sensiblemente esta métrica, se descarta (ver
    `_normalize_contrast_impl`)."""
    img = to_rgb(image_np)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _apply_clahe(image_np: np.ndarray) -> np.ndarray:
    """Aplica CLAHE (Contrast Limited Adaptive Histogram Equalization) sobre
    el canal L (luminosidad) de LAB, dejando los canales de color (a, b)
    intactos. Aislada en su propia función para poder probar la salvaguarda
    de `_normalize_contrast_impl` de forma determinística sin depender de
    encontrar una fixture real que la dispare (ver
    `backend/tests/test_preparation_trace.py`)."""
    img = to_rgb(image_np)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=_CONTRAST_CLIP_LIMIT, tileGridSize=_CONTRAST_TILE_GRID)
    l_enhanced = clahe.apply(l_channel)
    enhanced_lab = cv2.merge((l_enhanced, a_channel, b_channel))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)


def _normalize_contrast_impl(image_np: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    img = to_rgb(image_np)
    try:
        std_before = _contrast_metric(img)
        if std_before < _CONTRAST_MIN_STD_TO_ATTEMPT:
            return img, {
                "applied": False,
                "method": CONTRAST_METHOD,
                "reason": "imagen casi uniforme (sin variación de intensidad detectable), nada que normalizar",
                "std_before": round(std_before, 2),
                "std_after": round(std_before, 2),
            }
        sharpness_before = _sharpness_metric(img)
        enhanced = _apply_clahe(img)
        sharpness_after = _sharpness_metric(enhanced)
        if sharpness_after < sharpness_before * _CONTRAST_SHARPNESS_SAFETY_MARGIN:
            # Salvaguarda: la mejora habría degradado la nitidez/legibilidad
            # más de lo tolerado -- se descarta y se conserva la imagen de
            # entrada sin modificar (nunca se "empeora" el documento).
            return img, {
                "applied": False,
                "method": CONTRAST_METHOD,
                "reason": "mejora habría degradado la nitidez, se descarta (salvaguarda anti sobre-procesamiento)",
                "std_before": round(std_before, 2),
                "std_after": round(std_before, 2),
                "sharpness_before": round(sharpness_before, 2),
                "sharpness_after": round(sharpness_after, 2),
            }
        if np.array_equal(enhanced, img):
            return img, {
                "applied": False,
                "method": CONTRAST_METHOD,
                "reason": "sin cambios efectivos sobre los píxeles",
                "std_before": round(std_before, 2),
                "std_after": round(std_before, 2),
            }
        std_after = _contrast_metric(enhanced)
        return enhanced, {
            "applied": True,
            "method": CONTRAST_METHOD,
            "reason": "contraste normalizado (CLAHE sobre canal L de LAB)",
            "std_before": round(std_before, 2),
            "std_after": round(std_after, 2),
            "sharpness_before": round(sharpness_before, 2),
            "sharpness_after": round(sharpness_after, 2),
        }
    except Exception:
        return img, {
            "applied": False,
            "method": CONTRAST_METHOD,
            "reason": "error interno, sin cambios",
            "error": True,
        }


def normalize_contrast(image_np: np.ndarray) -> np.ndarray:
    """Normaliza contraste/iluminación de forma determinística (CLAHE sobre el
    canal L de LAB).

    Salvaguarda contra sobre-procesamiento (criterio 15 del spec): antes de
    aceptar el resultado, se compara la nitidez (varianza del Laplaciano)
    antes/después; si la normalización degradaría esa métrica más de un 10%
    (`_CONTRAST_SHARPNESS_SAFETY_MARGIN`), se descarta y se devuelve la
    imagen de entrada sin modificar. Imágenes casi uniformes (sin variación
    de intensidad) tampoco se tocan, para no "inventar" textura a partir de
    ruido. Degrada con gracia ante cualquier error (mismo patrón que
    `deskew`/`correct_perspective`): nunca lanza excepción, siempre devuelve
    una imagen válida.

    Ver `docs/tecnica/preprocesamiento-documental-no-destructivo.md` para el
    detalle del algoritmo, la calibración de los umbrales y la regla de
    dominio OCR (campos afectados, fixture de referencia, falsos positivos
    evitados).
    """
    img, _meta = _normalize_contrast_impl(image_np)
    return img


def _append_step(trace: Optional[List[Dict[str, Any]]], step: str, meta: Dict[str, Any]) -> None:
    """Agrega una entrada `{"step": step, ...meta}` a `trace` si no es `None`.
    No hace nada si `trace` es `None` (llamador no pidió trazabilidad)."""
    if trace is None:
        return
    entry: Dict[str, Any] = {"step": step}
    entry.update(meta)
    trace.append(entry)


def prepare(
    image_np: np.ndarray,
    max_side: int = 1600,
    apply_perspective: bool = False,
    exif_orientation_applied: bool = False,
    trace: Optional[List[Dict[str, Any]]] = None,
) -> np.ndarray:
    """Pipeline de preparación: orientación -> skew -> (perspectiva opcional) ->
    escala -> contraste.

    La corrección de perspectiva es OPT-OUT por defecto: sólo se aplica cuando el
    borde del documento se detecta con claridad y se solicita explícitamente, evitando
    warps espurios que desalineen las ROI normalizadas de las plantillas.

    `exif_orientation_applied` indica que, antes de llegar acá, ya se corrigió la
    orientación de la imagen usando su tag EXIF (ver
    `image_prep.apply_exif_orientation`, invocado en
    `capture_pipeline.process_document`). En ese caso se subordina la heurística
    `correct_orientation` (no se ejecuta) para evitar doble corrección.

    `trace`, si se pasa una lista, se completa en el mismo orden en que corren
    los pasos (`correct_orientation`, `deskew`, `correct_perspective`,
    `normalize_scale`, `normalize_contrast`), cada uno con al menos
    `{"step": str, "applied": bool}` y parámetros adicionales verificables (ver
    `docs/tecnica/preprocesamiento-documental-no-destructivo.md`). Esta función
    es compartida por el camino de imagen (`capture_pipeline.process_document`)
    y el camino PDF (`capture_pipeline._process_pdf`): no distingue el llamador,
    por lo que todos los pasos (incluido el contraste) corren y se trazan igual
    en ambos caminos.
    """
    out = to_rgb(image_np)

    out, meta = _correct_orientation_impl(out, skip=exif_orientation_applied)
    _append_step(trace, "correct_orientation", meta)

    out, meta = _deskew_impl(out)
    _append_step(trace, "deskew", meta)

    if apply_perspective:
        out, meta = _correct_perspective_impl(out)
        meta = dict(meta)
        meta["requested"] = True
    else:
        meta = {
            "applied": False,
            "requested": False,
            "reason": "omitido: no solicitado (apply_perspective=False)",
        }
    _append_step(trace, "correct_perspective", meta)

    out, meta = _normalize_scale_impl(out, max_side)
    _append_step(trace, "normalize_scale", meta)

    out, meta = _normalize_contrast_impl(out)
    _append_step(trace, "normalize_contrast", meta)

    return out


__all__ = [
    "prepare",
    "apply_exif_orientation",
    "correct_orientation",
    "deskew",
    "correct_perspective",
    "find_document_contour",
    "largest_contour_bounding_box",
    "normalize_scale",
    "normalize_contrast",
    "to_rgb",
]
