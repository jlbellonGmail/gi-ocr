"""
Procesador de reportes para T3.3 - Field Reporting.

Genera reportes estructurados con campos aceptados, rechazados y no encontrados.

Feature 09-confianza-y-enrutamiento-hitl: agrega confidence_summary al reporte.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict


class FieldConfidence(TypedDict, total=False):
    ocr_score: float
    extraction_score: float
    final_score: float
    validation_passed: bool
    validation_reason: Optional[str]
    decision: str
    thresholds: Dict[str, float]
    sensitive: bool
    block_on_validation_fail: bool


def generate_field_report(
    raw_ocr_text: str,
    candidate_fields: Dict[str, Optional[str]],
    validated_fields: Dict[str, str],
    rejected_fields: Dict[str, Dict[str, str]],
    missing_fields: Dict[str, None],
    document_type: str,
    source_document_reference: str,
    validation_rules: Optional[List[str]] = None,
    field_confidence: Optional[Dict[str, FieldConfidence]] = None,
) -> Dict[str, Any]:
    """Genera un reporte estructurado de clasificación de campos.

    Args:
        raw_ocr_text: Texto bruto extraído por OCR
        candidate_fields: Posibles campos identificados (campo -> valor o None)
        validated_fields: Campos que pasaron validación (campo -> valor)
        rejected_fields: Campos rechazados con razón (campo -> {value, reason})
        missing_fields: Campos esperados no encontrados (campo -> None)
        document_type: Tipo de documento genérico
        source_document_reference: Referencia al documento de entrada
        validation_rules: Lista de reglas de validación aplicadas
        field_confidence: Confianza y decisión por campo (feature 09-confianza-y-enrutamiento-hitl)

    Returns:
        Dict con reporte estructurado conforme a spec T3.3 + confidence_summary
    """
    accepted_field_ids = list(validated_fields.keys())
    rejected_field_ids = list(rejected_fields.keys())
    missing_field_ids = list(missing_fields.keys())

    report = {
        "document_type": document_type,
        "source_document_reference": source_document_reference,
        "accepted_fields": accepted_field_ids,
        "rejected_fields": [
            {"field": field, "reason": info.get("reason", "unknown")} for field, info in rejected_fields.items()
        ],
        "missing_fields": missing_field_ids,
        "summary_counts": {
            "accepted_count": len(accepted_field_ids),
            "rejected_count": len(rejected_field_ids),
            "missing_count": len(missing_field_ids),
        },
        "validation_metadata": {
            "schema_version": "1.0",
            "validation_rules_used": validation_rules or [],
        },
        "execution_metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    }

    # Feature 09-confianza-y-enrutamiento-hitl: confidence_summary
    if field_confidence:
        confidence_summary: Dict[str, Any] = {
            "auto_accepted": 0,
            "needs_review": 0,
            "blocked": 0,
            "missing": 0,
            "by_field": {},
        }
        for field, conf in field_confidence.items():
            decision = conf.get("decision", "unknown")
            if decision in ("auto_accepted", "needs_review", "blocked", "missing"):
                confidence_summary[decision] += 1
            confidence_summary["by_field"][field] = {
                "decision": decision,
                "final_score": conf.get("final_score", 0.0),
                "ocr_score": conf.get("ocr_score", 0.0),
                "extraction_score": conf.get("extraction_score", 0.0),
                "validation_passed": conf.get("validation_passed", False),
            }
        report["confidence_summary"] = confidence_summary

    return report


def classify_fields_from_t32_output(
    t32_result: Dict[str, Any],
    document_type: str,
    source_document_reference: str,
    validation_rules: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Clasifica campos a partir de salida T3.2 existente.

    Args:
        t32_result: Resultado de t3_2_orchestrator.orquestar_documento_controlado()
        document_type: Tipo de documento genérico
        source_document_reference: Referencia al documento de entrada
        validation_rules: Lista de reglas de validación aplicadas

    Returns:
        Dict con reporte estructurado conforme a spec T3.3
    """
    raw_ocr_text = t32_result.get("raw_ocr_text", "")
    candidate_fields = t32_result.get("candidate_fields", {})
    validated_fields = t32_result.get("validated_fields", {})
    rejected_fields = t32_result.get("rejected_fields", {})
    missing_fields = t32_result.get("missing_fields", {})

    return generate_field_report(
        raw_ocr_text=raw_ocr_text,
        candidate_fields=candidate_fields,
        validated_fields=validated_fields,
        rejected_fields=rejected_fields,
        missing_fields=missing_fields,
        document_type=document_type,
        source_document_reference=source_document_reference,
        validation_rules=validation_rules,
    )


def differentiate_field_states(
    raw_ocr_text: str,
    candidate_fields: Dict[str, Optional[str]],
    validated_fields: Dict[str, str],
    rejected_fields: Dict[str, Dict[str, str]],
    missing_fields: Dict[str, None],
) -> Dict[str, Any]:
    """Diferencia explícitamente los estados de los campos.

    Args:
        raw_ocr_text: Texto bruto OCR
        candidate_fields: Campos candidatos identificados
        validated_fields: Campos validados
        rejected_fields: Campos rechazados con razón
        missing_fields: Campos no encontrados

    Returns:
        Dict con diferenciación explícita de estados
    """
    return {
        "raw_ocr_text": raw_ocr_text,
        "candidate_fields": candidate_fields,
        "validated_fields": validated_fields,
        "rejected_fields": rejected_fields,
        "missing_fields": missing_fields,
    }


__all__ = [
    "generate_field_report",
    "classify_fields_from_t32_output",
    "differentiate_field_states",
]
