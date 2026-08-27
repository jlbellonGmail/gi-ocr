"""Confirmación de revisión humana sobre el resultado de un job.

Preserva valores originales del servidor. Valida estados confirmed/corrected/unresolved.
Genera nombre de archivo seguro. Persiste JSON confirmado separado del original.
Escribe .DATA v2 + .CONFIDENCE.json a storage_bridge/ready/ para integración legacy.

Feature 09-confianza-y-enrutamiento-hitl: registra confidence_at_review y decision_at_review
en confirmation_metadata para trazabilidad completa.

Feature 10-consola-revision-humana-profesional: registra correction_reasons (motivo de
corrección/rechazo) obligatorio cuando state != confirmed.

Feature 11-auditoria-permisos-operador: registra audit_trail con operador, valor original,
valor final, fecha, motivo y acción por campo.

Feature 12-contrato-integracion-legacy-v2: versionado v2, idempotencia, reintentos, reconciliación.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .job_store import JobStore
from .storage_bridge_writer import (
    CONTRACT_VERSION,
    compute_data_hash,
    write_atomic_data_file_with_retry,
    write_confidence_file,
)


def confirm_review(
    store: JobStore,
    job_id: str,
    corrections: List[Dict[str, Any]],
    operator_id: str,
    operator_role: str,
) -> Dict[str, Any]:
    original = store.load_original(job_id)
    if original is None:
        raise FileNotFoundError("Job original no encontrado")
    so = original.get("structured_output", {})
    validated_fields: Dict[str, Any] = dict(so.get("validated_fields", {}))
    candidate_fields: Dict[str, Any] = dict(so.get("candidate_fields", {}))
    field_confidence: Dict[str, Any] = dict(so.get("field_confidence", {}))
    corrected: List[str] = []
    confirmed_count = 0
    corrected_count = 0
    unresolved_count = 0
    confirmed_fields: Dict[str, Any] = {}
    confidence_at_review: Dict[str, Any] = {}
    decision_at_review: Dict[str, str] = {}
    correction_reasons: Dict[str, str] = {}
    audit_trail: List[Dict[str, Any]] = []

    for c in corrections:
        field = c.get("field")
        state = c.get("state", "unresolved")
        final_value = c.get("final_value")
        reason = c.get("reason", "").strip()
        if not field:
            continue
        # Excluir campos internos no editables
        if field in ("provider", "service"):
            continue
        # Validar reason obligatorio para corrected/unresolved
        if state in ("corrected", "unresolved") and not reason:
            raise ValueError(f"Campo '{field}': motivo obligatorio cuando estado es '{state}'")
        # Para confirmed, reason es opcional pero se guarda si se provee
        if reason:
            correction_reasons[field] = reason
        # Valor original: validado > candidato > null
        original_value = validated_fields.get(field, candidate_fields.get(field))
        if state == "confirmed":
            confirmed_count += 1
            confirmed_fields[field] = validated_fields.get(field, final_value)
        elif state == "corrected":
            corrected_count += 1
            corrected.append(field)
            confirmed_fields[field] = final_value
            validated_fields[field] = final_value
        else:
            unresolved_count += 1
            confirmed_fields[field] = final_value
        # Registrar confidence y decision al momento de revisión
        confidence_at_review[field] = field_confidence.get(field, {})
        decision_at_review[field] = state  # confirmed/corrected/unresolved
        # Audit trail entry
        audit_trail.append(
            {
                "field": field,
                "operator_id": operator_id,
                "operator_role": operator_role,
                "original_value": original_value,
                "final_value": final_value,
                "action": state,
                "reason": reason or None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    doc_type = original.get("processing_metadata", {}).get("provider_detected", "doc") or "doc"
    final_filename = store.build_final_filename(doc_type, job_id)

    # Preparar campos para .DATA (validated_fields sin provider/service internos)
    data_fields = [f for f in validated_fields.keys() if f not in ("provider", "service")]
    data_values = {f: validated_fields[f] for f in data_fields}
    service = so.get("service", "UNKNOWN")

    # Escribir .DATA v2 atómicamente con idempotencia y reintentos
    data_file = write_atomic_data_file_with_retry(
        service=service,
        fields=data_fields,
        values=data_values,
    )

    # Escribir .CONFIDENCE.json compañero
    confidence_file = write_confidence_file(
        service=service,
        field_confidence={f: field_confidence.get(f, {}) for f in data_fields if f in field_confidence},
    )

    confirmed_doc = {
        "job_id": job_id,
        "document_type": original.get("structured_output", {}).get("document_type", "MANUAL_REVIEW"),
        "confirmed_fields": confirmed_fields,
        "validated_fields": validated_fields,
        "corrections": corrected,
        "summary": {
            "confirmed_count": confirmed_count,
            "corrected_count": corrected_count,
            "unresolved_count": unresolved_count,
        },
        "confirmation_metadata": {
            "final_filename": final_filename,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "original_source": original.get("structured_output", {}).get("source_document_reference", ""),
            "confidence_at_review": confidence_at_review,
            "decision_at_review": decision_at_review,
            "correction_reasons": correction_reasons,
            "audit_trail": audit_trail,
            "contract_version": CONTRACT_VERSION,
            "data_file": str(data_file),
            "confidence_file": str(confidence_file),
            "data_hash": compute_data_hash(service, data_fields, data_values),
        },
        "original_result_ref": job_id,
    }
    path = store.save_confirmed(job_id, confirmed_doc)
    return {
        "job_id": job_id,
        "review_state": "confirmed" if unresolved_count == 0 else "partial",
        "document_type": confirmed_doc["document_type"],
        "final_filename": final_filename,
        "final_download_url": f"/api/v1/jobs/{job_id}/download",
        "confirmed_fields": confirmed_fields,
        "corrections": corrected,
        "summary": confirmed_doc["summary"],
        "confirmed_path": str(path),
        "correction_reasons": correction_reasons,
        "audit_trail": audit_trail,
        "data_file": str(data_file),
        "confidence_file": str(confidence_file),
        "data_hash": confirmed_doc["confirmation_metadata"]["data_hash"],
    }


__all__ = ["confirm_review"]
