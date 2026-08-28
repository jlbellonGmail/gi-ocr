"""
Helper functions for regression test suite.
Provides simple synchronous wrappers around the async OCR pipeline.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import mock OCR for fast testing
from backend.app.extraction_engine import extract_service_fields
from backend.app.validators import (
    validate_account,
    validate_amount,
    validate_comprobante,
    validate_date,
    validate_period,
)
from backend.tests.mock_ocr import MOCK_MODE, get_expected_text_for_image


def extract_text(image_path: Path) -> str:
    """Ejecuta OCR sobre una imagen y devuelve texto plano."""
    if MOCK_MODE:
        return get_expected_text_for_image(image_path)

    # Real OCR path disabled - mock mode always active
    raise RuntimeError("Real OCR path not available in regression suite. Enable MOCK_MODE.")


def extract_fields(ocr_text: str, provider: str, image_path: Path = None) -> Dict[str, Any]:
    """Extrae campos desde texto OCR para un proveedor."""
    normalized_provider = provider.strip().upper()

    # Don't pass image_np to avoid zone extraction interference in mock mode
    image_np = None

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            extract_service_fields(
                service=normalized_provider,
                ocr_text=ocr_text,
                image_np=image_np,
            )
        )
    finally:
        loop.close()

    # Convert to expected format: {field: {"value": val, "confidence": conf}}
    extracted = {}
    for field, value in result["fields"].items():
        confidence = 0.9 if value is not None else 0.0
        extracted[field] = {"value": value, "confidence": confidence}
    return extracted


def validate_semantic(extracted: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Aplica validación semántica a campos extraídos."""
    validated = {}
    provider.strip().upper()

    # Map services.ini field names to validators
    field_validators = {
        # GAS
        "importe": lambda v: validate_amount(v)[0] if v else None,
        "cliente": lambda v: validate_account(v, length=(8, 10))[0] if v else None,
        "nro_medidor": lambda v: v,  # No semantic validation in real pipeline
        "a_pagar_hasta": lambda v: validate_date(v)[0] if v else None,
        "periodo": lambda v: validate_period(v)[0] if v else None,
        # CEVT
        "medidor_numero": lambda v: v,  # No semantic validation in real pipeline
        "vencimiento": lambda v: validate_date(v)[0] if v else None,
        "codigo_pago_electronico": lambda v: v,
        "total_a_pagar": lambda v: validate_amount(v)[0] if v else None,
        # Generic
        "numero_comprobante": lambda v: validate_comprobante(v)[0] if v else None,
        "fecha_emision": lambda v: validate_date(v)[0] if v else None,
        "periodo_facturado": lambda v: validate_period(v)[0] if v else None,
        "importe_total": lambda v: validate_amount(v)[0] if v else None,
        "cuit_emisor": lambda v: validate_account(v, length=(11, 11))[0] if v else None,
        "cuit_receptor": lambda v: validate_account(v, length=(11, 11))[0] if v else None,
        "consumo_kwh": lambda v: v,
        "consumo_m3": lambda v: v,
        "numero_linea": lambda v: v,
        "iva_21": lambda v: validate_amount(v)[0] if v else None,
        "iva_10_5": lambda v: validate_amount(v)[0] if v else None,
        "razon_social_emisor": lambda v: v,
        "razon_social_receptor": lambda v: v,
    }

    for field, field_data in extracted.items():
        value = field_data.get("value")
        confidence = field_data.get("confidence", 0.9)

        if value is not None and field in field_validators:
            try:
                validated_value = field_validators[field](str(value))
                validated[field] = {
                    "value": validated_value,
                    "confidence": confidence if validated_value is not None else 0.0,
                }
            except Exception:
                validated[field] = {"value": None, "confidence": 0.0}
        else:
            validated[field] = {"value": value, "confidence": confidence}

    return validated


def run_full_pipeline(image_path: Path, provider: str) -> Dict[str, Any]:
    """Ejecuta pipeline completo: OCR -> Extracción -> Validación."""
    ocr_text = extract_text(image_path)
    extracted = extract_fields(ocr_text, provider, image_path)
    validated = validate_semantic(extracted, provider)
    return validated
