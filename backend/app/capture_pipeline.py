"""Pipeline de captura: clasificar -> plantilla -> OCR two-pass ROI -> regex ->
validación tipada -> accepted/rejected/missing -> reporte.

Integra OCR (ocr_engine), extracción (templates/regex), validación semántica
(validators) y reporte (field_reporting_processor). Mide tiempos por etapa.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image

from . import image_prep, ocr_engine, pdf_util
from .field_reporting_processor import generate_field_report
from .templates import get_template, unknown_template


def _extract_field(field_tpl, texts, page_text_full=""):
    """Aplica regex del campo sobre los textos de su banda. Devuelve (candidate, source)."""
    if field_tpl.extract is None:
        return None, None
    # intentar primero con ancla si existe
    candidates = []
    for t in texts:
        if field_tpl.anchor and not re.search(field_tpl.anchor, t, re.IGNORECASE):
            # si hay ancla, exigir que aparezca en el texto de la banda;
            # si no aparece, igual intentamos regex puro del extract (típico valor sin label)
            pass
        m = re.search(field_tpl.extract, t, re.IGNORECASE)
        if m:
            candidates.append(m.group(1))
    if not candidates and page_text_full:
        m = re.search(field_tpl.extract, page_text_full, re.IGNORECASE)
        if m:
            candidates.append(m.group(1))
    if not candidates:
        return None, None
    return candidates[0], "ocr_region"


def process_image(image_np: np.ndarray, source_ref: str, page_text_full: str = "") -> Dict[str, Any]:
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

    if provider != "UNKNOWN":
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
            cand, _src = _extract_field(ft, band_texts, page_text_full)
            candidate_fields[ft.name] = cand
            if cand is None:
                continue
            score = max(
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
            field_scores[ft.name] = round(score, 3)
            if ft.validator is not None:
                value, reason = ft.validator(cand)
                if value is not None:
                    validated_fields[ft.name] = str(value)
                else:
                    rejected_fields[ft.name] = {"value": cand, "reason": reason or "invalid"}
            else:
                validated_fields[ft.name] = cand

    if provider != "UNKNOWN":
        validated_fields["provider"] = template.provider
        candidate_fields["provider"] = template.provider
        validated_fields["service"] = template.service

    # 5) campos faltantes
    required = list(template.required_fields)
    missing_fields = {f: None for f in required if f not in validated_fields and f not in rejected_fields}

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
    )

    timing_total = round(_t.time() - t_start, 3)
    timings["total_s"] = timing_total

    return {
        "processing_metadata": {
            "provider_detected": provider,
            "provider_confidence": conf,
            "timings": timings,
            "engine": "RapidOCR-ONNX-PP-OCRv3",
        },
        "raw_ocr_text": raw_ocr_text,
        "structured_output": {
            "document_type": template.document_type,
            "source_document_reference": source_ref,
            "candidate_fields": candidate_fields,
            "validated_fields": validated_fields,
            "rejected_fields": rejected_fields,
            "missing_fields": missing_fields,
        },
        "field_report": field_report,
        "field_scores": field_scores,
    }


def process_document(path: str, source_ref: Optional[str] = None) -> Dict[str, Any]:
    """Procesa imagen o PDF. Devuelve resultado estructurado (página 0 por convención)."""
    src = source_ref or path
    if pdf_util.is_pdf(path):
        return _process_pdf(path, src)
    img = Image.open(path)
    img, exif_applied = image_prep.apply_exif_orientation(img)
    img = img.convert("RGB")
    arr = np.array(img)
    prepared = image_prep.prepare(arr, exif_orientation_applied=exif_applied)
    return process_image(prepared, src)


def _process_pdf(path: str, src: str) -> Dict[str, Any]:
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
        return _process_pdf_native(pages, native_text, src)
    prepared = image_prep.prepare(page_to_process["image"])
    result = process_image(prepared, src, page_text_full=native_text)
    result["processing_metadata"]["is_pdf"] = True
    result["processing_metadata"]["pdf_pages"] = len(pages)
    result["processing_metadata"]["pdf_pages_ocr"] = sum(1 for p in pages if p["needs_ocr"])
    return result


def _process_pdf_native(pages, native_text, src):
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
    if template is not None and provider != "UNKNOWN":
        for ft in template.fields:
            m = re.search(ft.extract or "", native_text, re.IGNORECASE) if ft.extract else None
            cand = m.group(1) if m else None
            candidate[ft.name] = cand
            if cand and ft.validator:
                v, reason = ft.validator(cand)
                if v is not None:
                    validated[ft.name] = str(v)
                else:
                    rejected[ft.name] = {"value": cand, "reason": reason or "invalid"}
            elif cand:
                validated[ft.name] = cand
        validated["provider"] = template.provider
    missing = {
        f: None for f in (template.required_fields if template else []) if f not in validated and f not in rejected
    }
    fr = generate_field_report(
        raw_ocr_text=native_text,
        candidate_fields=candidate,
        validated_fields=validated,
        rejected_fields=rejected,
        missing_fields=missing,
        document_type=template.document_type if template else "MANUAL_REVIEW",
        source_document_reference=src,
        validation_rules=["native_pdf_text"],
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
        },
        "raw_ocr_text": native_text,
        "structured_output": {
            "document_type": template.document_type if template else "MANUAL_REVIEW",
            "source_document_reference": src,
            "candidate_fields": candidate,
            "validated_fields": validated,
            "rejected_fields": rejected,
            "missing_fields": missing,
        },
        "field_report": fr,
        "field_scores": {},
    }


def __import_templates():
    from .templates import all_templates

    return all_templates()


__all__ = ["process_image", "process_document"]
