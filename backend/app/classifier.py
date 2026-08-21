"""Clasificador de proveedor basado en anclas/keywords ubicadas en bandas normalizadas.

Estrategia: OCR focalizado en bandas de clasificación de cada plantilla -> texto ->
keywords. Nunca asigna GAS por defecto a un documento desconocido (devuelve UNKNOWN).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from . import ocr_engine
from .templates import ProviderTemplate, all_templates


def classify(image_np, templates: Optional[List[ProviderTemplate]] = None) -> Tuple[str, float]:
    """Devuelve (provider, confidence). provider='UNKNOWN' si no hay match seguro.

    Usa detección completa + rec selectivo sobre las bandas de clasificación de cada
    plantilla conocida, buscando las keywords ancla. La confianza es la mejor densidad
    de coincidencias normalizada.
    """
    if templates is None:
        templates = all_templates()
    norm_boxes, boxes_raw, _ = ocr_engine.detect_page(image_np)
    # bandas de clasificación de todas las plantillas
    all_bands = []
    for t in templates:
        for b in t.classify_bands:
            all_bands.append(b)
    sel = ocr_engine.select_boxes_in_bands(norm_boxes, all_bands)
    rec = ocr_engine.recognize_selected(image_np, sel)
    texts = " ".join(t[0] for t in rec).lower()
    if not texts.strip():
        return "UNKNOWN", 0.0

    best_provider = "UNKNOWN"
    best_score = 0.0
    for t in templates:
        score = 0.0
        hits = 0
        for kw in t.classify_keywords:
            if kw in texts:
                hits += 1
                score += 1.0
        # normalizar por cantidad de keywords
        norm = score / max(len(t.classify_keywords), 1)
        # exigir al menos 1 hit
        if hits > 0 and norm > best_score:
            best_score = norm
            best_provider = t.provider
    # Confianza exigida para no asignar GAS a desconocidos
    if best_score < 0.34:
        return "UNKNOWN", best_score
    return best_provider, round(best_score, 3)


def classify_and_pick(image_np):
    """Clasifica y devuelve (provider, template)."""
    provider, conf = classify(image_np)
    from .templates import get_template

    return provider, get_template(provider), conf


__all__ = ["classify", "classify_and_pick"]
