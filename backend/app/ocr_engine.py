"""Motor OCR local basado en RapidOCR (PP-OCRv3) + ONNX Runtime.

Reemplaza a EasyOCR como motor principal. Modelos ONNX bundled (Apache-2.0/MIT).
Carga única (singleton) al iniciar el servicio. Arquitectura two-pass ROI-focalizada:
  1) detección completa (text_detector) -> cajas con coords normalizadas.
  2) reconocimiento (text_recognizer) selectivo sobre cajas dentro de bandas del template.
OCR completo como fallback para documentos desconocidos / bandas sin anclas.
"""
from __future__ import annotations

import os
import threading
from typing import List, Optional, Tuple

import numpy as np

try:
    import onnxruntime as _ort
    # Cap de threads intra-op de onnxruntime antes de que RapidOCR cree sesiones.
    # Sin este cap, cada inferencia usa todos los núcleos físicos; al concatenar
    # workers ocurre oversubscription disastrous. Con intra_op reducido, los workers
    # paralelizan de forma determinista sin contención.
    _orig_inference_session = _ort.InferenceSession

    class _CappedInferenceSession(_orig_inference_session):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            opts = kwargs.pop("sess_options", None)
            if opts is None:
                opts = _ort.SessionOptions()
                opts.intra_op_num_threads = int(os.environ.get("GI_OCR_ORT_THREADS", "3"))
                opts.inter_op_num_threads = 1
            kwargs["sess_options"] = opts
            super().__init__(*args, **kwargs)

    _ort.InferenceSession = _CappedInferenceSession
except Exception:
    pass

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception as e:  # pragma: no cover - entorno sin rapidocr
    RapidOCR = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None

_ENGINE_LOCK = threading.Lock()
_engine = None
_tls = threading.local()


def get_engine():
    """Devuelve el singleton RapidOCR compartido.

    Modelos cargados una sola vez al iniciar el servicio. El queue paraleliza vía
    workers sobre el mismo motor (onnxruntime permite inferencias concurrentes sobre
    la misma sesión con el cap de threads intra-op aplicado). Medición mostró que un
    motor compartido supera a uno por-thread en este perfil (menor oversubscription).
    """
    global _engine
    if _engine is not None:
        return _engine
    if RapidOCR is None:
        raise RuntimeError(f"RapidOCR no disponible: {_IMPORT_ERROR}")
    with _ENGINE_LOCK:
        if _engine is None:
            _engine = RapidOCR(
                use_angle_cls=False,
                min_height=16,
                box_thresh=0.5,
                text_score=0.4,
            )
    return _engine


def get_thread_engine():
    """Alias de compatibilidad; devuelve el singleton compartido."""
    return get_engine()


def warmup() -> None:
    """Carga el singleton (arranque en frío medible aparte en benchmark)."""
    get_engine()


def _norm_boxes(boxes: List, width: int, height: int):
    """Lista de cajas -> listas de (box_norm, center_norm, x1,y1,x2,y2 normalizados)."""
    out = []
    for b in boxes:
        xs = [p[0] for p in b]
        ys = [p[1] for p in b]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        out.append(
            {
                "box": b,
                "cx": cx / width,
                "cy": cy / height,
                "x1": x1 / width,
                "y1": y1 / height,
                "x2": x2 / width,
                "y2": y2 / height,
            }
        )
    return out


def detect_page(image_np: np.ndarray):
    """Paso 1: detección completa. Devuelve (boxes_normalized, boxes_raw, det_seconds)."""
    import time

    eng = get_engine()
    h, w = image_np.shape[:2]
    t0 = time.time()
    boxes, _ = eng.text_detector(image_np)
    dt = time.time() - t0
    if boxes is None:
        return [], [], dt
    norm = _norm_boxes(boxes, w, h)
    return norm, boxes, dt


def recognize_selected(image_np: np.ndarray, boxes_raw: List):
    """Paso 2: reconocimiento selectivo. Devuelve list[(text, score, box_sorted)].

    El orden de salida corresponde a los boxes ordenados por sorted_boxes (el mismo
    orden que usa get_crop_img_list y el recognizer), de modo que texto y caja quedan
    alineados exactamente.
    """
    if not boxes_raw:
        return []
    eng = get_engine()
    arr = np.asarray(boxes_raw, dtype=np.float32)
    sorted_boxes = eng.sorted_boxes(arr)
    crops = eng.get_crop_img_list(image_np, sorted_boxes)
    res, _ = eng.text_recognizer(crops)
    if not res:
        return []
    out = []
    for box, r in zip(sorted_boxes, res):
        text = r[0]
        score = float(r[1]) if r[1] is not None else 0.0
        out.append((text, score, box))
    return out


def select_boxes_in_bands(norm_boxes, bands):
    """Selecciona cajas cuyo centro cae dentro de alguna banda normalizada (y1,y2,x1,x2)."""
    sel_raw = []
    seen = set()
    for nb in norm_boxes:
        cx, cy = nb["cx"], nb["cy"]
        for (y1, y2, x1, x2) in bands:
            if y1 <= cy <= y2 and x1 <= cx <= x2:
                key = (
                    round(nb["x1"], 3),
                    round(nb["y1"], 3),
                    round(nb["x2"], 3),
                    round(nb["y2"], 3),
                )
                if key not in seen:
                    seen.add(key)
                    sel_raw.append(nb["box"])
                break
    return sel_raw


def ocr_full_page(image_np: np.ndarray):
    """OCR completo (fallback). Devuelve list[(text, score, box_norm)]."""
    import time

    eng = get_engine()
    h, w = image_np.shape[:2]
    t0 = time.time()
    result, _ = eng(image_np)
    dt = time.time() - t0
    out = []
    if result:
        for box, text, score in result:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            out.append(
                {
                    "text": text,
                    "score": float(score) if score is not None else 0.0,
                    "x1": min(xs) / w,
                    "y1": min(ys) / h,
                    "x2": max(xs) / w,
                    "y2": max(ys) / h,
                }
            )
    return out, dt


def recognize_image_roi(image_np: np.ndarray, bands):
    """Two-pass ROI: detección + rec selectivo sobre bandas.

    Args:
        bands: lista de tuplas (y1, y2, x1, x2) normalizadas.
    Devuelve: (texts_list, box_results, det_seconds, rec_seconds)
        texts_list: [text, ...]
        box_results: [{"text","score","x1","y1","x2","y2"}]
    """
    import time

    norm_boxes, boxes_raw, det_dt = detect_page(image_np)
    sel = select_boxes_in_bands(norm_boxes, bands)
    t0 = time.time()
    rec = recognize_selected(image_np, sel)
    rec_dt = time.time() - t0
    out = []
    h, w = image_np.shape[:2]
    for text, score, box in rec:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append(
            {
                "text": text,
                "score": round(score, 3),
                "x1": min(xs) / w,
                "y1": min(ys) / h,
                "x2": max(xs) / w,
                "y2": max(ys) / h,
            }
        )
    texts = [r["text"] for r in out]
    return texts, out, det_dt, rec_dt


__all__ = [
    "get_engine",
    "warmup",
    "detect_page",
    "recognize_selected",
    "select_boxes_in_bands",
    "ocr_full_page",
    "recognize_image_roi",
]