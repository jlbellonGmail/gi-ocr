"""
Motor de extracción OCR configurable.

Este motor lee la configuración desde services.ini y aplica extracción
genérica basada en zonas OCR y/o patrones regex configurables.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .ocr import extract_text_from_zone
from .services_config import (
    get_service_config,
)

# Global configuration for semantic validation
SEMANTIC_VALIDATION_ENABLED = True


async def extract_service_fields(
    service: str,
    ocr_text: str,
    image_np: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Extrae campos para un servicio dado a partir de texto OCR.

    Estrategia:
    1. Si hay zonas configuradas y se proporciona image_np, extrae texto por zona.
    2. Si hay patrones regex configurados, los aplica sobre el texto (zona o completo).
    3. Fallback: lógica genérica basada en palabras clave (compatibilidad hacia atrás).

    Args:
        service: Código del servicio (ej. "GAS")
        ocr_text: Texto completo extraído por OCR
        image_np: Array numpy de la imagen (opcional, requerido para extracción por zonas)

    Returns:
        Dict con:
        - fields: dict campo -> valor extraído (o None)
        - detected_fields: lista de campos con valor
        - missing_fields: lista de campos sin valor
        - normalized_text: texto OCR normalizado
        - service: código de servicio
    """
    config = get_service_config(service)
    if config is None:
        raise ValueError(f"Servicio '{service}' no configurado en services.ini")

    fields = config["fields"]
    zones = config["zones"]
    patterns = config["patterns"]

    # Normalizar texto completo
    normalized_text = _normalize_text(ocr_text)

    # Extraer texto por zonas si están configuradas y tenemos imagen
    zone_texts: Dict[str, str] = {}
    if zones and image_np is not None:
        zone_texts = await _extract_zones(image_np, zones)

    # Para cada campo, intentar extraer valor
    extracted: Dict[str, Optional[str]] = {}

    for field in fields:
        value = None

        # 1. Si hay zona para este campo, usar texto de zona
        if field in zone_texts:
            zone_text = zone_texts[field]
            value = _extract_with_patterns(field, zone_text, patterns)
            if value is None:
                value = _extract_generic(field, zone_text)

        # 2. Si no hay zona o falló, intentar con patrones sobre texto completo
        if value is None and field in patterns:
            value = _extract_with_patterns(field, normalized_text, patterns)

        # 3. Fallback: lógica genérica sobre texto completo
        if value is None:
            value = _extract_generic(field, normalized_text)

        # Apply semantic validation
        value = _validate_semantic_field(field, value)
        extracted[field] = value

    detected = [f for f in fields if extracted[f] is not None]
    missing = [f for f in fields if extracted[f] is None]

    return {
        "fields": extracted,
        "detected_fields": detected,
        "missing_fields": missing,
        "normalized_text": normalized_text,
        "service": service,
    }


async def _extract_zones(
    image_np: np.ndarray,
    zones: Dict[str, Tuple[float, float, float, float]],
) -> Dict[str, str]:
    """Extrae texto de cada zona configurada."""
    zone_texts: Dict[str, str] = {}
    for field, coords in zones.items():
        text = await extract_text_from_zone(image_np, coords, use_preprocessing=True)
        zone_texts[field] = text
    return zone_texts


def _normalize_text(text: str | None) -> str:
    """Normaliza texto OCR para extracción estable."""
    if not text:
        return ""
    normalized = text.replace("\r", " ").replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _extract_with_patterns(
    field: str,
    text: str,
    patterns: Dict[str, str],
) -> Optional[str]:
    """Extrae valor usando patrones regex configurados para el campo."""
    if field not in patterns:
        return None
    pattern = patterns[field]
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return _clean_value(match.group(1) if match.lastindex else match.group(0))
    return None


def _extract_generic(field: str, text: str) -> Optional[str]:
    """
    Extracción genérica basada en palabras clave (fallback compatibilidad).
    Mismo comportamiento que ocr.py extract_fields_from_zones.
    """
    text_clean = text.strip()
    if not text_clean:
        return None

    field_lower = field.lower()

    if "cliente" in field_lower:
        match = re.search(r"(\d{8,10})", text_clean)
        return match.group(1) if match else text_clean[:10]

    if "medidor" in field_lower:
        match = re.search(r"(\d{4,6}[-]?\d{6,8}|\d{7,15})", text_clean)
        return match.group(1) if match else text_clean[:15]

    if "periodo" in field_lower or "período" in field_lower:
        match = re.search(r"(\d{1,2}[/-]\d{4})", text_clean)
        return match.group(1) if match else text_clean[:10]

    if "pagar" in field_lower or "vencimiento" in field_lower:
        # Try extended delimiters and ignore stray text like COMPROBANT
        match = re.search(r"(\d{1,2}[/\-\.\*]\d{1,2}[/\-\.\*]\d{2,4})", text_clean)
        if match:
            return match.group(1)
        # Fallback: keep original behavior with limited delimiters
        match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text_clean)
        return match.group(1) if match else None

    if "importe" in field_lower or "total" in field_lower:
        match = re.search(r"([\d]{1,3}[.,][\d]{3}[.,][\d]{2}|[\d]+[.,][\d]{2})", text_clean)
        return match.group(1) if match else text_clean[:15]

    return text_clean[:50]


def _clean_value(value: str | None) -> Optional[str]:
    """Limpia valor extraído: quita símbolos iniciales y finales."""
    if value is None:
        return None
    cleaned = value.strip()
    cleaned = re.sub(r"^[\s:$\-]+", "", cleaned)
    cleaned = re.sub(r"[\s,.;:]+$", "", cleaned)
    return cleaned or None


def _validate_semantic_field(field: str, value: str | None) -> Optional[str]:
    """
    Validates semantic field values (e.g., rejects invalid terms for date fields).
    Used for semantic field validation.
    """
    if not value:
        return None

    # Reject COMPROBANT for date fields specifically
    if field == "a_pagar_hasta" and "COMPROBANT" in value.upper():
        return None  # Reject COMPROBANT completely

    # Additional semantic validations would go here
    return value
