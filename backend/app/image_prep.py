"""Preprocesamiento de imagen: corrección de orientación, perspectiva y escala.

Mejoras robustas (OpenCV) que no dependen de píxeles absolutos. Las plantillas usan
coordenadas normalizadas; la corrección aquí hace que el layout se alinee a esas bandas.

La corrección de orientación EXIF (`apply_exif_orientation`) es un paso previo y
distinto a `correct_orientation`: opera sobre la imagen PIL original (con metadata)
ANTES de convertir a `np.ndarray`, mientras que `correct_orientation` es una
heurística de contenido (varianza de gradiente) que opera sobre el array ya sin
metadata. Ver `docs/tecnica/correccion-orientacion-exif.md` para el detalle
completo y la relación entre ambas.
"""

from __future__ import annotations

from typing import Tuple

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

    applied = (
        isinstance(orientation_tag, int)
        and not isinstance(orientation_tag, bool)
        and 2 <= orientation_tag <= 8
    )
    return transposed, applied


def to_rgb(image_np: np.ndarray) -> np.ndarray:
    if image_np.ndim == 2:
        return cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    if image_np.shape[2] == 4:
        return cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
    return image_np


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
    img = to_rgb(image_np)
    if skip:
        return img
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
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if var_x > var_y * 2.2 and w < h:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    except Exception:
        pass
    return img


def deskew(image_np: np.ndarray) -> np.ndarray:
    """Corrige skew leve (< 5°) usando proyección horizontal de texto."""
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
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.1 or abs(angle) > 5:
            return img
        (h2, w2) = img.shape[:2]
        M = cv2.getRotationMatrix2D((w2 / 2, h2 / 2), angle, 1.0)
        return cv2.warpAffine(img, M, (w2, h2), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return img


def correct_perspective(image_np: np.ndarray) -> np.ndarray:
    """Corrección de perspectiva basada en detección del borde del documento.

    Detecta el contorno más grande y rectifica a su bounding box. Si no encuentra
    un cuadrilátero claro, devuelve la imagen original (no destructivo).
    """
    img = to_rgb(image_np)
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(gray, 75, 200)
        cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        screen = None
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4 and cv2.contourArea(c) > 0.3 * img.shape[0] * img.shape[1]:
                screen = approx.reshape(4, 2)
                break
        if screen is None:
            return img
        rect = _order_points(screen.astype(np.float32))
        (tl, tr, br, bl) = rect
        width = max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))
        height = max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))
        if width < 10 or height < 10:
            return img
        dst = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float32,
        )
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (int(width), int(height)))
    except Exception:
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


def normalize_scale(image_np: np.ndarray, max_side: int = 1600) -> np.ndarray:
    """Escala la imagen para que el lado mayor sea <= max_side (mantiene aspecto)."""
    img = to_rgb(image_np)
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img
    scale = max_side / m
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def prepare(
    image_np: np.ndarray,
    max_side: int = 1600,
    apply_perspective: bool = False,
    exif_orientation_applied: bool = False,
) -> np.ndarray:
    """Pipeline de preparación: orientación -> skew -> (perspectiva opcional) -> escala.

    La corrección de perspectiva es OPT-OUT por defecto: sólo se aplica cuando el
    borde del documento se detecta con claridad y se solicita explícitamente, evitando
    warps espurios que desalineen las ROI normalizadas de las plantillas.

    `exif_orientation_applied` indica que, antes de llegar acá, ya se corrigió la
    orientación de la imagen usando su tag EXIF (ver
    `image_prep.apply_exif_orientation`, invocado en
    `capture_pipeline.process_document`). En ese caso se subordina la heurística
    `correct_orientation` (no se ejecuta) para evitar doble corrección.
    """
    out = correct_orientation(image_np, skip=exif_orientation_applied)
    out = deskew(out)
    if apply_perspective:
        out = correct_perspective(out)
    out = normalize_scale(out, max_side)
    return out


__all__ = [
    "prepare",
    "apply_exif_orientation",
    "correct_orientation",
    "deskew",
    "correct_perspective",
    "normalize_scale",
    "to_rgb",
]
