"""Confirmación de revisión humana sobre el resultado de un job.

Preserva valores originales del servidor. Valida estados confirmed/corrected/unresolved.
Genera nombre de archivo seguro. Persiste JSON confirmado separado del original.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .job_store import JobStore


def confirm_review(store: JobStore, job_id: str, corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    original = store.load_original(job_id)
    if original is None:
        raise FileNotFoundError("Job original no encontrado")
    so = original.get("structured_output", {})
    validated_fields: Dict[str, Any] = dict(so.get("validated_fields", {}))
    corrected: List[str] = []
    confirmed_count = 0
    corrected_count = 0
    unresolved_count = 0
    confirmed_fields: Dict[str, Any] = {}

    for c in corrections:
        field = c.get("field")
        state = c.get("state", "unresolved")
        final_value = c.get("final_value")
        if not field:
            continue
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

    doc_type = original.get("processing_metadata", {}).get("provider_detected", "doc") or "doc"
    final_filename = store.build_final_filename(doc_type, job_id)

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
    }


__all__ = ["confirm_review"]
