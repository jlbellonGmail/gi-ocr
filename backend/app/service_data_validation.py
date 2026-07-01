"""
Validaciones específicas por tipo de servicio para el flujo DATA evaluator.

Este módulo proporciona validaciones de datos extraídos según reglas
propias de cada servicio/documento, complementando la extracción OCR genérica.
"""
import re
from typing import Any, Dict, List, Optional


def validate_service_data(
    service_id: str,
    extracted_fields: Dict[str, Any],
    expected_fields: List[str],
) -> Dict[str, Any]:
    """
    Valida los campos extraídos contra reglas específicas del servicio.

    Args:
        service_id: Código del servicio (ej. "GAS", "CEVT")
        extracted_fields: Diccionario con campos extraídos (campo -> valor o None)
        expected_fields: Lista de campos esperados según inventario

    Returns:
        Dict con estructura:
        {
            "service_id": str,
            "is_valid": bool,
            "validated_fields": Dict[str, str],
            "rejected_fields": Dict[str, Dict[str, str]],
            "missing_fields": List[str],
            "errors": List[str],
        }
    """
    result = {
        "service_id": service_id,
        "is_valid": True,
        "validated_fields": {},
        "rejected_fields": {},
        "missing_fields": [],
        "errors": [],
    }

    for field in expected_fields:
        value = extracted_fields.get(field)
        if value is None:
            result["missing_fields"].append(field)
        else:
            is_valid, error = _validate_field(service_id, field, value)
            if is_valid:
                result["validated_fields"][field] = value
            else:
                result["rejected_fields"][field] = {
                    "value": value,
                    "reason": error,
                }
                result["errors"].append(f"Field '{field}': {error}")

    result["is_valid"] = (len(result["errors"]) == 0 and
                         len(result["missing_fields"]) == 0)

    return result


def _validate_field(service_id: str, field_name: str, value: str) -> tuple[bool, Optional[str]]:
    """
    Valida un campo específico según el servicio y el nombre del campo.

    Returns:
        (is_valid, error_message) - error_message es None si es válido
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, "Empty value"

    cleaned = str(value).strip()

    # Importe/total fields
    if field_name in ("importe", "total_a_pagar", "total"):
        return _validate_amount(cleaned)

    # Date fields
    if field_name in ("a_pagar_hasta", "vencimiento", "fecha"):
        return _validate_date(cleaned)

    # Period fields
    if field_name == "periodo":
        return _validate_period(cleaned)

    # Code/ID fields
    if field_name in ("cliente", "nro_medidor", "medidor_numero", "codigo_pago_electronico"):
        return _validate_code(cleaned)

    # Default: accept any non-empty value
    return True, None


def _validate_amount(value: str) -> tuple[bool, Optional[str]]:
    """Valida formato de importe/monto."""
    if not value:
        return False, "Invalid amount format"

    # Must contain digits
    if not re.search(r"\d", value):
        return False, "Invalid amount format"

    # Reject values that are only letters
    if re.match(r"^[A-Za-z\s]+$", value):
        return False, "Invalid amount format"

    # Reject COMPROBANTE in amount fields
    if re.search(r"COMPROBANTE", value, re.IGNORECASE):
        return False, "Contains invalid term 'COMPROBANTE'"

    return True, None


def _validate_date(value: str) -> tuple[bool, Optional[str]]:
    """Valida formato de fecha completa."""
    if not value:
        return False, "Empty value"

    # Date formats: DD/MM/YYYY or DD-MM-YYYY etc.
    if not re.match(r"^\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}$", value):
        return False, "Invalid date format"

    # Reject COMPROBANTE
    if re.search(r"COMPROBANTE", value, re.IGNORECASE):
        return False, "Contains invalid term 'COMPROBANTE'"

    return True, None


def _validate_period(value: str) -> tuple[bool, Optional[str]]:
    """Valida formato de periodo MM/YYYY."""
    if not value:
        return False, "Empty value"

    # Accept MM/YYYY or MM-YYYY or MM.YYYY
    if not re.match(r"^\d{1,2}[\/\-\.]\d{4}$", value):
        return False, "Invalid period format"

    return True, None


def _validate_code(value: str) -> tuple[bool, Optional[str]]:
    """Valida formato de código/identificador."""
    if not value:
        return False, "Empty code"

    cleaned = value.upper().replace(" ", "")

    # Accept alphanumeric codes
    if re.match(r"^[A-Z0-9\-]{1,30}$", cleaned):
        return True, None

    # Accept pure numeric codes
    if re.match(r"^\d{4,20}$", cleaned):
        return True, None

    return False, "Invalid code format"


def validate_and_filter_fields(
    service_id: str,
    extracted_fields: Dict[str, Any],
    expected_fields: List[str],
) -> Dict[str, Any]:
    """
    Valida y filtra campos, devolviendo solo los válidos para escritura DATA.

    Esta función está diseñada para integrarse fácilmente en el evaluator:
    - Valida campos según reglas del servicio
    - Devuelve estructura con campos validados y rechazados
    - Mantiene compatibilidad con flujo existente
    """
    validation_result = validate_service_data(service_id, extracted_fields, expected_fields)

    filtered_fields = {}
    for field in expected_fields:
        if field in validation_result["validated_fields"]:
            filtered_fields[field] = validation_result["validated_fields"][field]
        elif field in validation_result["rejected_fields"]:
            filtered_fields[field] = ""
        else:
            filtered_fields[field] = ""

    return {
        "validation": validation_result,
        "fields_for_data": filtered_fields,
    }


def _is_amount_field(field_name: str) -> bool:
    """Determina si un campo es de tipo importe/amount."""
    amount_keywords = ["importe", "total", "saldo", "a_pagar", "pagar", "monto"]
    return any(kw in field_name for kw in amount_keywords)


def _is_date_field(field_name: str) -> bool:
    """Determina si un campo es de tipo fecha."""
    date_keywords = ["fecha", "vencimiento", "vence", "pagar_hasta", "periodo"]
    return any(kw in field_name for kw in date_keywords)


def _is_code_field(field_name: str) -> bool:
    """Determina si un campo es de tipo código/identificador."""
    code_keywords = ["codigo", "código", "id", "identificador", "referencia", "cliente", "medidor", "cuenta"]
    return any(kw in field_name for kw in code_keywords)