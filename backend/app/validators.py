"""Validadores tipados y normalizadores para campos de comprobantes (AR).

Separan texto bruto OCR -> candidato -> validado / rechazado / no encontrado.
Sin hardcodeo de valores de negocio: sólo normalización y validación genérica de tipos.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

DATE_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})")
PERIOD_RE = re.compile(r"(\d{1,2})[/-](\d{4})")
COMPROBANTE_RE = re.compile(r"(\d{4})[-]?(\d{8})")
AMOUNT_VIS_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}|\d+[.,]\d{2}|\d+)")
DIGITS_RE = re.compile(r"\d+")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_amount(value: str) -> Optional[float]:
    """Convierte monto AR con tolerancia a confusiones de OCR.

    Formatos canónicos aceptados: '13.429,89' (AR) y '13429,89'.
    Tolerancia a OCR que reemplaza ',' por '.': '13.429.89' -> 13429.89
    Heurística: si hay dos separadores y el grupo central tiene 3 dígitos y el
    final 2, el primer separador es de miles y el segundo decimal.
    """
    if not value:
        return None
    v = value.strip().lstrip("$").strip()
    v = re.sub(r"[^\d.,]", "", v)
    if not v:
        return None
    m = re.match(r"^(\d{1,3})[.,](\d{3})[.,](\d{2})$", v)
    if m:
        return round(float(m.group(1)) * 1000 + float(m.group(2)) + float(m.group(3)) / 100, 2)
    m = re.match(r"^(\d{1,3})[.,](\d{3})$", v)
    if m:
        # ambiguous: '4.572' o '4,572' -> integer miles without decimals
        return round(float(m.group(1)) * 1000 + float(m.group(2)), 2)
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        if re.search(r",\d{2}$", v):
            v = v.replace(".", "").replace(",", ".")
        else:
            v = v.replace(",", "")
    elif "." in v:
        if re.search(r"\.\d{2}$", v):
            pass
        else:
            v = v.replace(".", "")
    try:
        return round(float(v), 2)
    except ValueError:
        return None


def validate_date(value: str) -> Tuple[Optional[str], Optional[str]]:
    """Devuelve (fecha_normalizada DD/MM/YYYY, reason). None si inválida."""
    if not value:
        return None, "empty"
    m = DATE_RE.search(value)
    if not m:
        return None, "no_date_pattern"
    d, mo, y = m.group(1), m.group(2), m.group(3)
    if len(y) == 2:
        y = "20" + y
    di, mi = int(d), int(mo)
    if not (1 <= mi <= 12 and 1 <= di <= 31):
        return None, "out_of_range"
    return f"{int(d):02d}/{int(mo):02d}/{y}", None


def validate_period(value: str) -> Tuple[Optional[str], Optional[str]]:
    """Devuelve (periodo MM/YYYY, reason)."""
    if not value:
        return None, "empty"
    m = PERIOD_RE.search(value)
    if not m:
        return None, "no_period_pattern"
    mo, y = m.group(1), m.group(2)
    if not (1 <= int(mo) <= 12):
        return None, "month_out_of_range"
    return f"{int(mo):02d}/{y}", None


def validate_comprobante(value: str) -> Tuple[Optional[str], Optional[str]]:
    """Comprobante NNNN-NNNNNNNN (puede venir con ruido). Conserva guion_canónico."""
    if not value:
        return None, "empty"
    # extraer bloque de 12 dígitos
    digits = "".join(DIGITS_RE.findall(value))
    if len(digits) < 12:
        return None, "too_short"
    block = digits[-12:]
    return f"{block[:4]}-{block[4:]}", None


def validate_account(value: str, length: Tuple[int, int] = (8, 10)) -> Tuple[Optional[str], Optional[str]]:
    """Identificador de cuenta / cliente: dígitos puros dentro de rango de longitud."""
    if not value:
        return None, "empty"
    digits = "".join(DIGITS_RE.findall(value))
    if not digits:
        return None, "no_digits"
    lo, hi = length
    if not (lo <= len(digits) <= hi):
        return None, f"length_{len(digits)}"
    return digits, None


def validate_meter(value: str) -> Tuple[Optional[str], Optional[str]]:
    """Medidor: 7-18 dígitos."""
    if not value:
        return None, "empty"
    digits = "".join(DIGITS_RE.findall(value))
    if len(digits) < 7:
        return None, "too_short"
    return digits, None


def validate_amount(value: str) -> Tuple[Optional[float], Optional[str]]:
    f = normalize_amount(value)
    if f is None:
        return None, "amount_parse"
    return f, None


__all__ = [
    "normalize_amount",
    "validate_date",
    "validate_period",
    "validate_comprobante",
    "validate_account",
    "validate_meter",
    "validate_amount",
    "_clean",
]
