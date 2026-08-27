"""Pipeline de captura: clasificar -> plantilla -> OCR two-pass ROI -> regex ->
validación tipada -> accepted/rejected/missing -> reporte.

Integra OCR (ocr_engine), extracción (templates/regex), validación semántica
(validators) y reporte (field_reporting_processor). Mide tiempos por etapa.

Feature 09-confianza-y-enrutamiento-hitl: scores y umbrales por campo para
enrutamiento automático (auto_accepted, needs_review, blocked, missing).
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PIL import Image

from . import image_prep, ocr_engine, pdf_util, quality_gate
from .field_reporting_processor import FieldConfidence, generate_field_report
from .services_config import get_service_confidence_config
from .templates import get_template, unknown_template


def _extract_field(field_tpl, texts, page_text_full=""):
    """Aplica regex del campo sobre los textos de su banda. Devuelve (candidate, source, extraction_path)."""
    if field_tpl.extract is None:
        return None, None, "none"
    # intentar primero con ancla si existe
    candidates = []
    for t in texts:
        if field_tpl.anchor and not re.search(field_tpl.anchor, t, re.IGNORECASE):
            # si hay ancla, exigir que aparezca en el texto de la banda;
            # si no aparece, igual intentamos regex puro del extract (típico valor sin label)
            pass
        m = re.search(field_tpl.extract, t, re.IGNORECASE)
        if m:
            candidates.append((m.group(1), "zone_regex"))
    if not candidates and page_text_full:
        m = re.search(field_tpl.extract, page_text_full, re.IGNORECASE)
        if m:
            candidates.append((m.group(1), "fulltext_regex"))
    if not candidates:
        return None, None, "none"
    return candidates[0][0], candidates[0][1], "zone_regex" if candidates[0][1] == "zone_regex" else "fulltext_regex"


def _calc_extraction_score(extraction_path: str, has_anchor: bool) -> float:
    """Calcula score de extracción según el camino usado.

    - zone_regex (regex en banda OCR): 1.0
    - fulltext_regex (regex en texto completo): 0.9
    - anchor_only (solo ancla matcheó, regex genérico): 0.7
    - generic (fallback genérico): 0.3
    - none: 0.0
    """
    if extraction_path == "zone_regex":
        return 1.0
    if extraction_path == "fulltext_regex":
        return 0.9
    if extraction_path == "anchor_only":
        return 0.7
    if extraction_path == "generic":
        return 0.3
    return 0.0


def _make_confidence_decision(
    field_name: str,
    ocr_score: float,
    extraction_score: float,
    validation_passed: bool,
    validation_reason: Optional[str],
    confidence_config: Dict[str, Any],
) -> Tuple[str, FieldConfidence]:
    """Determina la decisión de enrutamiento para un campo.

    Returns:
        (decision, confidence_detail)
        decision: "auto_accepted" | "needs_review" | "blocked" | "missing"
        confidence_detail: dict con trazabilidad completa
    """
    auto_accept = confidence_config.get("auto_accept", 0.85)
    needs_review = confidence_config.get("needs_review", 0.50)
    sensitive = confidence_config.get("sensitive", False)
    block_on_fail = confidence_config.get("block_on_validation_fail", True)

    final_score = round((ocr_score * 0.6) + (extraction_score * 0.4), 3)

    if validation_passed:
        if final_score >= auto_accept:
            decision = "auto_accepted"
        elif final_score >= needs_review:
            decision = "needs_review"
        else:
            decision = "needs_review"
    else:
        # Validación semántica falló
        if sensitive or block_on_fail:
            decision = "blocked"
        else:
            decision = "rejected"  # comportamiento legacy, va a rejected_fields

    confidence_detail = FieldConfidence(
        ocr_score=round(ocr_score, 3),
        extraction_score=round(extraction_score, 3),
        final_score=final_score,
        validation_passed=validation_passed,
        validation_reason=validation_reason,
        decision=decision,
        thresholds={"auto": auto_accept, "review": needs_review},
        sensitive=sensitive,
        block_on_validation_fail=block_on_fail,
    )
    return decision, confidence_detail


def process_image(
    image_np: np.ndarray,
    source_ref: str,
    page_text_full: str = "",
    operator_id: Optional[str] = None,
    operator_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Procesa una imagen preparada. Devuelve el resultado estructurado T3.2+T3.3.

    page_text_full: texto nativo del PDF (si aplica) para fallback de regex.
    Usa UNA sola detección OCR reutilizada para clasificación y extracción.
    """
    import time as _t

    t_start = _t.time()
    timings = {}

    # 1) detección única (reutilizada)
    t0 = _t.time()
    norm_boxes, boxes_raw, det_dt = ocr_engine.detect_page(image_np)
    timings["ocr_det_s"] = round(det_dt, 3)

    # 2) clasificación: rec selectivo sobre bandas de clasificación de todas las plantillas
    from .templates import all_templates

    templates = all_templates()
    classify_bands = []
    for t in templates:
        for b in t.classify_bands:
            classify_bands.append(b)
    sel_cls = ocr_engine.select_boxes_in_bands(norm_boxes, classify_bands)
    t0 = _t.time()
    rec_cls = ocr_engine.recognize_selected(image_np, sel_cls)
    timings["classify_rec_s"] = round(_t.time() - t0, 3)
    cls_texts = " ".join(t[0] for t in rec_cls).lower()

    best_provider = "UNKNOWN"
    best_conf = 0.0
    for t in templates:
        hits = sum(1 for kw in t.classify_keywords if kw in cls_texts)
        norm = hits / max(len(t.classify_keywords), 1)
        if hits > 0 and norm > best_conf:
            best_conf = norm
            best_provider = t.provider
    if best_conf < 0.34:
        best_provider = "UNKNOWN"
    provider = best_provider
    conf = round(best_conf, 3)
    template = get_template(provider)
    timings["classify_s"] = round(_t.time() - t0, 3)

    # 3) extracción: rec selectivo sobre bandas del template elegido
    t0 = _t.time()
    if provider == "UNKNOWN":
        box_results, full_dt = ocr_engine.ocr_full_page(image_np)
        texts = [r["text"] for r in box_results]
        timings["ocr_rec_s"] = round(full_dt, 3)
    else:
        field_bands = [f.band for f in template.fields]
        sel_ext = ocr_engine.select_boxes_in_bands(norm_boxes, field_bands)
        rec_ext = ocr_engine.recognize_selected(image_np, sel_ext)
        h, w = image_np.shape[:2]
        box_results = []
        for text, score, box in rec_ext:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            box_results.append(
                {
                    "text": text,
                    "score": round(score, 3),
                    "x1": min(xs) / w,
                    "y1": min(ys) / h,
                    "x2": max(xs) / w,
                    "y2": max(ys) / h,
                }
            )
        texts = [r["text"] for r in box_results]
        timings["ocr_rec_s"] = round(_t.time() - t0, 3)
    timings["ocr_total_s"] = round(timings["ocr_det_s"] + timings["ocr_rec_s"] + timings.get("classify_rec_s", 0.0), 3)

    raw_ocr_text = "\n".join(texts)

    # 4) extracción + validación por campo
    candidate_fields: Dict[str, Optional[str]] = {}
    validated_fields: Dict[str, str] = {}
    rejected_fields: Dict[str, Dict[str, str]] = {}
    field_scores: Dict[str, float] = {}
    field_confidence: Dict[str, FieldConfidence] = {}

    if provider != "UNKNOWN":
        # Obtener configuración de confianza para este servicio
        confidence_configs = get_service_confidence_config(template.service)
        for ft in template.fields:
            if ft.name in candidate_fields and candidate_fields[ft.name] is not None:
                continue
            band_texts = [
                r["text"]
                for r in box_results
                if (
                    ft.band[0] <= ((r["y1"] + r["y2"]) / 2) <= ft.band[1]
                    and ft.band[2] <= ((r["x1"] + r["x2"]) / 2) <= ft.band[3]
                )
            ]
            cand, extraction_path, _src = _extract_field(ft, band_texts, page_text_full)
            candidate_fields[ft.name] = cand

            # Calcular ocr_score (max score OCR en banda)
            ocr_score = max(
                (
                    r["score"]
                    for r in box_results
                    if (
                        ft.band[0] <= ((r["y1"] + r["y2"]) / 2) <= ft.band[1]
                        and ft.band[2] <= ((r["x1"] + r["x2"]) / 2) <= ft.band[3]
                    )
                ),
                default=0.0,
            )
            field_scores[ft.name] = round(ocr_score, 3)

            if cand is None:
                # Campo missing: registrar confidence con decision=missing
                fc = confidence_configs.get(ft.name, {})
                field_confidence[ft.name] = {
                    "ocr_score": round(ocr_score, 3),
                    "extraction_score": 0.0,
                    "final_score": 0.0,
                    "validation_passed": False,
                    "validation_reason": "no_candidate",
                    "decision": "missing",
                    "thresholds": {"auto": fc.get("auto_accept", 0.85), "review": fc.get("needs_review", 0.50)},
                    "sensitive": fc.get("sensitive", False),
                    "block_on_validation_fail": fc.get("block_on_validation_fail", True),
                }
                continue

            # Calcular extraction_score según camino de extracción
            has_anchor = ft.anchor is not None
            extraction_score = _calc_extraction_score(extraction_path, has_anchor)

            # Validación semántica
            validation_passed = True
            validation_reason: Optional[str] = None
            if ft.validator is not None:
                value, reason = ft.validator(cand)
                if value is not None:
                    validated_fields[ft.name] = str(value)
                else:
                    validation_passed = False
                    validation_reason = reason or "invalid"
                    rejected_fields[ft.name] = {"value": cand, "reason": validation_reason}
            else:
                validated_fields[ft.name] = cand

            # Decisión de confianza
            fc = confidence_configs.get(ft.name, {})
            decision, conf_detail = _make_confidence_decision(
                ft.name, ocr_score, extraction_score, validation_passed, validation_reason, fc
            )
            field_confidence[ft.name] = conf_detail

            # Si decision es blocked, mover de rejected_fields a blocked (nueva categoría)
            if decision == "blocked" and ft.name in rejected_fields:
                # Mantenemos en rejected_fields para compatibilidad, pero la decisión es blocked
                pass

    if provider != "UNKNOWN":
        validated_fields["provider"] = template.provider
        candidate_fields["provider"] = template.provider
        validated_fields["service"] = template.service
        # provider y service no tienen confidence config, agregar default
        field_confidence["provider"] = FieldConfidence(
            ocr_score=0.0,
            extraction_score=0.0,
            final_score=1.0,
            validation_passed=True,
            validation_reason=None,
            decision="auto_accepted",
            thresholds={"auto": 0.85, "review": 0.50},
            sensitive=False,
            block_on_validation_fail=True,
        )
        field_confidence["service"] = FieldConfidence(
            ocr_score=0.0,
            extraction_score=0.0,
            final_score=1.0,
            validation_passed=True,
            validation_reason=None,
            decision="auto_accepted",
            thresholds={"auto": 0.85, "review": 0.50},
            sensitive=False,
            block_on_validation_fail=True,
        )

    # 5) campos faltantes
    required = list(template.required_fields)
    missing_fields = {f: None for f in required if f not in validated_fields and f not in rejected_fields}

    # Agregar confidence para campos missing que no se procesaron arriba
    if provider != "UNKNOWN":
        confidence_configs = get_service_confidence_config(template.service)
        for f in missing_fields:
            if f not in field_confidence:
                fc = confidence_configs.get(f, {})
                field_confidence[f] = FieldConfidence(
                    ocr_score=0.0,
                    extraction_score=0.0,
                    final_score=0.0,
                    validation_passed=False,
                    validation_reason="missing_required",
                    decision="missing",
                    thresholds={"auto": fc.get("auto_accept", 0.85), "review": fc.get("needs_review", 0.50)},
                    sensitive=fc.get("sensitive", False),
                    block_on_validation_fail=fc.get("block_on_validation_fail", True),
                )

    # 6) reporte de campos
    field_report = generate_field_report(
        raw_ocr_text=raw_ocr_text,
        candidate_fields=candidate_fields,
        validated_fields=validated_fields,
        rejected_fields=rejected_fields,
        missing_fields=missing_fields,
        document_type=template.document_type,
        source_document_reference=source_ref,
        validation_rules=["date", "period", "account", "meter", "amount", "comprobante"],
        field_confidence=field_confidence,
    )

    timing_total = round(_t.time() - t_start, 3)
    timings["total_s"] = timing_total

    return {
        "processing_metadata": {
            "provider_detected": provider,
            "provider_confidence": conf,
            "timings": timings,
            "engine": "RapidOCR-ONNX-PP-OCRv3",
            "operator_id": operator_id,
            "operator_role": operator_role,
        },
        "raw_ocr_text": raw_ocr_text,
        "structured_output": {
            "document_type": template.document_type,
            "source_document_reference": source_ref,
            "candidate_fields": candidate_fields,
            "validated_fields": validated_fields,
            "rejected_fields": rejected_fields,
            "missing_fields": missing_fields,
            "field_confidence": field_confidence,
        },
        "field_report": field_report,
        "field_scores": field_scores,
    }


def process_document(
    path: str,
    source_ref: Optional[str] = None,
    operator_id: Optional[str] = None,
    operator_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Procesa imagen o PDF. Devuelve resultado estructurado (página 0 por convención).

    Sobre el camino de imagen (no PDF, ver `docs/tecnica/
    correccion-orientacion-exif.md`, "Fuera de alcance"), corre el control de
    calidad de captura (`quality_gate.evaluate`, feature
    `06-calidad-captura-mobile`) justo después de la corrección EXIF y ANTES
    de `image_prep.prepare`/OCR: un veredicto `reject` no invoca OCR y
    devuelve un resultado mínimo con `processing_metadata.quality_gate`
    (consumido por `job_queue.JobQueue._process` para dejar el job en el
    estado `quality_gate.REJECTED_JOB_STATUS`, sin llamar `save_original`,
    igual que el camino `failed` existente). Un veredicto `ok`/`warn` sigue
    el pipeline normal y agrega `processing_metadata.quality_gate` al
    resultado final.

    No destructivo (feature `07-preprocesamiento-documental-no-destructivo`):
    esta función solo lee `path` (`Image.open`); ningún paso de `image_prep`
    escribe sobre esa ruta, todo corre en memoria (`np.ndarray`). Cuando el
    pipeline efectivamente prepara la imagen (no hay `reject` de
    `quality_gate` en el camino de imagen, y siempre en el camino PDF salvo
    `_process_pdf_native`), el resultado incluye
    `processing_metadata.preparation_trace`: una lista ordenada de los pasos
    de `image_prep` efectivamente ejecutados, ver
    `docs/tecnica/preprocesamiento-documental-no-destructivo.md`.
    """
    src = source_ref or path
    if pdf_util.is_pdf(path):
        return _process_pdf(path, src, operator_id, operator_role)
    img: Image.Image = Image.open(path)
    img, exif_applied = image_prep.apply_exif_orientation(img)
    img = img.convert("RGB")
    arr = np.array(img)

    quality = quality_gate.evaluate(arr)
    if quality["verdict"] == "reject":
        # Traza de preparación (feature `07-preprocesamiento-documental-no-
        # destructivo`): un veredicto `reject` corta ANTES de
        # `image_prep.prepare`, por lo que no se genera ninguna entrada de
        # traza (ni siquiera la de EXIF, ver criterio 11 del spec) -- la
        # clave `preparation_trace` queda ausente en este resultado, no una
        # lista con pasos "inventados".
        return _quality_rejected_result(src, quality, operator_id, operator_role)

    # `preparation_trace` acumula, en orden, la corrección EXIF (paso previo a
    # `image_prep.prepare`, sólo en este camino de imagen) y los pasos que
    # corren dentro de `prepare()` (orientación por contenido, deskew,
    # perspectiva, escala, contraste). Ver criterios 9-10 del spec.
    trace: list = [
        {
            "step": "apply_exif_orientation",
            "applied": exif_applied,
            "reason": (
                "corrección aplicada según tag EXIF Orientation"
                if exif_applied
                else "sin corrección EXIF necesaria/disponible"
            ),
        }
    ]
    prepared = image_prep.prepare(arr, exif_orientation_applied=exif_applied, trace=trace)
    result = process_image(prepared, src, operator_id=operator_id, operator_role=operator_role)
    result["processing_metadata"]["quality_gate"] = quality
    result["processing_metadata"]["preparation_trace"] = trace
    return result


def _quality_rejected_result(
    src: str,
    quality: Dict[str, Any],
    operator_id: Optional[str] = None,
    operator_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Resultado mínimo para un veredicto `reject` de `quality_gate`: no se
    invocó OCR (`ocr_engine`/`process_image`), por lo que no hay campos
    extraídos. Mismo "shape" que el resultado normal (todas las claves
    presentes, vacías) para que el resto del código (frontend, exportadores)
    no tenga que distinguir dos formatos distintos de resultado."""
    return {
        "processing_metadata": {
            "quality_gate": quality,
            "engine": None,
            "operator_id": operator_id,
            "operator_role": operator_role,
        },
        "raw_ocr_text": "",
        "structured_output": {
            "document_type": None,
            "source_document_reference": src,
            "candidate_fields": {},
            "validated_fields": {},
            "rejected_fields": {},
            "missing_fields": {},
            "field_confidence": {},
        },
        "field_report": None,
        "field_scores": {},
    }


def _process_pdf(
    path: str,
    src: str,
    operator_id: Optional[str] = None,
    operator_role: Optional[str] = None,
) -> Dict[str, Any]:
    pages = pdf_util.extract_text_and_render(path)
    # texto nativo consolidado (fallback regex)
    native_text = "\n".join(p["text"] for p in pages if not p["needs_ocr"])
    # primera página que necesite OCR para clasificar/procesar; si todas tienen
    # texto nativo, usamos la primera página renderizada para clasificación visual.
    page_to_process = None
    for p in pages:
        if p["image"] is not None:
            page_to_process = p
            break
    if page_to_process is None:
        # PDF con texto nativo: construir resultado a partir del texto nativo
        # (sin imagen). Clasificación por texto. Rec por regex sobre texto nativo.
        # `image_prep.prepare` nunca se invoca en este sub-camino
        # (`_process_pdf_native`) -- no se genera ninguna entrada de
        # `preparation_trace` (misma convención que el veredicto `reject` de
        # `quality_gate`, ver criterio 12/casos borde del spec).
        return _process_pdf_native(pages, native_text, src, operator_id, operator_role)
    # `image_prep.prepare()` es la MISMA función que usa el camino de imagen:
    # corre (y se traza) `correct_orientation` (heurística de contenido, con
    # `skip=False` porque este camino nunca pasa `exif_orientation_applied`),
    # `deskew` (incondicional), `correct_perspective` (si se pide) y
    # `normalize_scale`/`normalize_contrast`, igual que sobre imágenes. No se
    # agrega una entrada `apply_exif_orientation` ni `quality_gate`: ninguno de
    # los dos se invoca nunca en el camino PDF (ver criterio 12 del spec).
    trace: list = []
    prepared = image_prep.prepare(page_to_process["image"], trace=trace)
    result = process_image(
        prepared,
        src,
        page_text_full=native_text,
        operator_id=operator_id,
        operator_role=operator_role,
    )
    result["processing_metadata"]["is_pdf"] = True
    result["processing_metadata"]["pdf_pages"] = len(pages)
    result["processing_metadata"]["pdf_pages_ocr"] = sum(1 for p in pages if p["needs_ocr"])
    result["processing_metadata"]["preparation_trace"] = trace
    return result


def _process_pdf_native(
    pages,
    native_text,
    src,
    operator_id: Optional[str] = None,
    operator_role: Optional[str] = None,
):
    t_start = time.time()
    # clasificación por keywords sobre texto nativo
    best = ("UNKNOWN", 0.0, None)
    for t in [t for t in __import_templates()]:
        s = 0.0
        low = native_text.lower()
        for kw in t.classify_keywords:
            if kw in low:
                s += 1.0
        norm = s / max(len(t.classify_keywords), 1)
        if norm > best[1] and norm >= 0.34:
            best = (t.provider, norm, t)
    provider, conf, template = best[0], best[1], best[2] or unknown_template()
    validated = {}
    rejected = {}
    candidate = {}
    field_confidence: Dict[str, FieldConfidence] = {}
    if template is not None and provider != "UNKNOWN":
        confidence_configs = get_service_confidence_config(template.service)
        for ft in template.fields:
            m = re.search(ft.extract or "", native_text, re.IGNORECASE) if ft.extract else None
            cand = m.group(1) if m else None
            candidate[ft.name] = cand
            fc = confidence_configs.get(ft.name, {})
            if cand is None:
                field_confidence[ft.name] = {
                    "ocr_score": 0.0,
                    "extraction_score": 0.0,
                    "final_score": 0.0,
                    "validation_passed": False,
                    "validation_reason": "no_candidate",
                    "decision": "missing",
                    "thresholds": {"auto": fc.get("auto_accept", 0.85), "review": fc.get("needs_review", 0.50)},
                    "sensitive": fc.get("sensitive", False),
                    "block_on_validation_fail": fc.get("block_on_validation_fail", True),
                }
                continue
            # extraction_score para native PDF: 0.9 (regex sobre texto nativo)
            extraction_score = 0.9
            validation_passed = True
            validation_reason = None
            if ft.validator:
                v, reason = ft.validator(cand)
                if v is not None:
                    validated[ft.name] = str(v)
                else:
                    validation_passed = False
                    validation_reason = reason or "invalid"
                    rejected[ft.name] = {"value": cand, "reason": validation_reason}
            else:
                validated[ft.name] = cand
            # ocr_score = 0 para native PDF (no hay OCR)
            decision, conf_detail = _make_confidence_decision(
                ft.name, 0.0, extraction_score, validation_passed, validation_reason, fc
            )
            field_confidence[ft.name] = conf_detail
        validated["provider"] = template.provider
        field_confidence["provider"] = FieldConfidence(
            ocr_score=0.0,
            extraction_score=0.0,
            final_score=1.0,
            validation_passed=True,
            validation_reason=None,
            decision="auto_accepted",
            thresholds={"auto": 0.85, "review": 0.50},
            sensitive=False,
            block_on_validation_fail=True,
        )
    missing = {
        f: None for f in (template.required_fields if template else []) if f not in validated and f not in rejected
    }
    # Agregar confidence para campos missing
    if template is not None and provider != "UNKNOWN":
        confidence_configs = get_service_confidence_config(template.service)
        for f in missing:
            if f not in field_confidence:
                fc = confidence_configs.get(f, {})
                field_confidence[f] = FieldConfidence(
                    ocr_score=0.0,
                    extraction_score=0.0,
                    final_score=0.0,
                    validation_passed=False,
                    validation_reason="missing_required",
                    decision="missing",
                    thresholds={"auto": fc.get("auto_accept", 0.85), "review": fc.get("needs_review", 0.50)},
                    sensitive=fc.get("sensitive", False),
                    block_on_validation_fail=fc.get("block_on_validation_fail", True),
                )
    fr = generate_field_report(
        raw_ocr_text=native_text,
        candidate_fields=candidate,
        validated_fields=validated,
        rejected_fields=rejected,
        missing_fields=missing,
        document_type=template.document_type if template else "MANUAL_REVIEW",
        source_document_reference=src,
        validation_rules=["native_pdf_text"],
        field_confidence=field_confidence,
    )
    return {
        "processing_metadata": {
            "provider_detected": provider,
            "provider_confidence": conf,
            "engine": "PDF-NATIVE-TEXT",
            "is_pdf": True,
            "pdf_pages": len(pages),
            "pdf_pages_ocr": 0,
            "timings": {"total_s": round(time.time() - t_start, 3)},
            "operator_id": operator_id,
            "operator_role": operator_role,
        },
        "raw_ocr_text": native_text,
        "structured_output": {
            "document_type": template.document_type if template else "MANUAL_REVIEW",
            "source_document_reference": src,
            "candidate_fields": candidate,
            "validated_fields": validated,
            "rejected_fields": rejected,
            "missing_fields": missing,
            "field_confidence": field_confidence,
        },
        "field_report": fr,
        "field_scores": {},
    }


def __import_templates():
    from .templates import all_templates

    return all_templates()


__all__ = ["process_image", "process_document"]
