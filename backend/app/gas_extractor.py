"""Extractor específico para comprobantes GAS."""
from __future__ import annotations

import re
from typing import Any


FIELD_NAMES = (
    "importe",
    "a_pagar_hasta",
    "cliente",
    "periodo",
    "nro_medidor",
)

AMOUNT_PATTERN = r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})|\d+)"
DATE_PATTERN = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
PERIOD_PATTERN = r"(\d{1,2}[/-]\d{2,4})"


def normalize_text(text: str | None) -> str:
    """Normalize OCR text for stable regex extraction."""
    if not text:
        return ""

    normalized = text.replace("\r", " ").replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _clean_value(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    cleaned = re.sub(r"^[\s:$\-]+", "", cleaned)
    cleaned = re.sub(r"[\s,.;:]+$", "", cleaned)
    return cleaned or None


def _extract_first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_value(match.group(1))
    return None


def _extract_importe(text: str) -> str | None:
    patterns = [
        rf"(?:importe|total|saldo|a\s+pagar)\s*(?:final|total)?\s*[:\-]?\s*(?:\$|s/|s'|ars|pesos)?\s*{AMOUNT_PATTERN}",
    ]
    return _extract_first(patterns, text)


def _extract_a_pagar_hasta(text: str) -> str | None:
    patterns = [
        rf"(?:a\s+pagar\s+hasta|pagar\s+hasta|fecha\s+de\s+vencimiento|vencimiento|vence)\D{{0,40}}{DATE_PATTERN}",
    ]
    return _extract_first(patterns, text)


def _extract_cliente(text: str) -> str | None:
    patterns = [
        r"(?:nro\.?|n°|numero|número)?\s*cliente\s*[:\-]?\s*(\d{6,12})",
        r"(?:cuenta|usuario)\s*[:\-]?\s*(\d{6,12})",
    ]
    return _extract_first(patterns, text)


def _extract_periodo(text: str) -> str | None:
    patterns = [
        rf"(?:periodo|período)\s*[:\-]?\s*{PERIOD_PATTERN}",
    ]
    return _extract_first(patterns, text)


def _extract_nro_medidor(text: str) -> str | None:
    patterns = [
        r"(?:nro\.?|n°|numero|número)?\s*medidor\s*[:\-]?\s*(\d{7,18})",
        r"medidor\s*(?:nro\.?|n°|numero|número)?\s*[:\-]?\s*(\d{7,18})",
    ]
    return _extract_first(patterns, text)


def extract_gas_fields(ocr_text: str | None) -> dict[str, Any]:
    """Extract structured GAS fields from OCR text."""
    normalized_text = normalize_text(ocr_text)

    fields: dict[str, str | None] = {
        "importe": None,
        "a_pagar_hasta": None,
        "cliente": None,
        "periodo": None,
        "nro_medidor": None,
    }

    if normalized_text:
        fields["importe"] = _extract_importe(normalized_text)
        fields["a_pagar_hasta"] = _extract_a_pagar_hasta(normalized_text)
        fields["cliente"] = _extract_cliente(normalized_text)
        fields["periodo"] = _extract_periodo(normalized_text)
        fields["nro_medidor"] = _extract_nro_medidor(normalized_text)

    detected_fields = [field for field in FIELD_NAMES if fields[field] is not None]
    missing_fields = [field for field in FIELD_NAMES if fields[field] is None]

    return {
        "fields": fields,
        "detected_fields": detected_fields,
        "missing_fields": missing_fields,
        "normalized_text": normalized_text,
    }
