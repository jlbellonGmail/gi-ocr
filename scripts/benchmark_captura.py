"""Benchmark reproducible de precision OCR local.

Mide rendimiento y precision por lote, proveedor y campo. Mantiene
RapidOCR/ONNX como motor principal cuando procesa imagenes, pero permite un
dataset sintetico/controlado para CI y desarrollo sin muestras privadas.

Uso:
  python scripts/benchmark_captura.py --dataset synthetic --docs 20 \
      --out _bench/benchmark.json --report-md _bench/benchmark.md
  python scripts/benchmark_captura.py --dataset local --docs 400 \
      --out _bench/local.json --report-md _bench/local.md
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import capture_pipeline, ocr_engine

REAL = ROOT / "backend" / "tests" / "fixtures" / "_local_samples" / "real"
LOCAL_CONTRACT = REAL / "expected.local.json"
DEFAULT_OUT = "_bench/benchmark.json"
DEFAULT_REPORT_MD = "_bench/benchmark.md"
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".png"}
OPERATIVE_P95_THRESHOLD_S = 5.0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark de precision OCR por lote, proveedor y campo.")
    parser.add_argument(
        "--docs",
        type=int,
        default=20,
        help="Cantidad objetivo de documentos/variantes. Usar 400 para gate operativo.",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Archivo JSON estructurado. Default: {DEFAULT_OUT}",
    )
    parser.add_argument(
        "--report-md",
        default=DEFAULT_REPORT_MD,
        help=f"Resumen Markdown. Default: {DEFAULT_REPORT_MD}",
    )
    parser.add_argument(
        "--dataset",
        choices=["auto", "synthetic", "local"],
        default="auto",
        help="Fuente de evaluacion: synthetic, local privado gitignored o auto.",
    )
    parser.add_argument(
        "--private-dir",
        default=str(REAL),
        help="Directorio privado opcional con expected.local.json.",
    )
    parser.add_argument(
        "--skip-cold-start",
        action="store_true",
        help="Evita cargar explicitamente el motor antes del lote.",
    )
    parser.add_argument(
        "--synthetic-mode",
        choices=["controlled", "ocr"],
        default="controlled",
        help="En dataset synthetic, controlled no requiere motor OCR; ocr procesa las imagenes generadas.",
    )
    return parser.parse_args(argv)


def cold_start() -> float | None:
    t0 = time.perf_counter()
    ocr_engine.warmup()
    return time.perf_counter() - t0


def _font(size: int = 26) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_text(img: Image.Image, x: float, y: float, text: str, size: int = 26) -> None:
    draw = ImageDraw.Draw(img)
    draw.text((int(img.width * x), int(img.height * y)), text, fill="black", font=_font(size))


def variant(img: Image.Image, i: int) -> Image.Image:
    """Genera una variacion local sin datos sensibles."""
    img = img.convert("RGB")
    op = i % 6
    if op == 0:
        return img.rotate(2 * (i % 3 - 1), expand=True, fillcolor="white")
    if op == 1:
        return img.resize((int(img.width * 0.90), int(img.height * 0.90)))
    if op == 2:
        return ImageEnhance.Brightness(img).enhance(0.82 + (i % 3) * 0.1)
    if op == 3:
        return ImageEnhance.Contrast(img).enhance(1.18)
    if op == 4:
        factor = 1.0 - (i % 4) * 0.035
        return ImageOps.pad(img, (img.width, img.height), color="white").resize(
            (int(img.width * factor), int(img.height * factor))
        )
    return img


def _base_case_image(case_id: str) -> tuple[Image.Image, dict[str, Any]]:
    img = Image.new("RGB", (1000, 1400), "white")
    if case_id == "gas_valid":
        _draw_text(img, 0.42, 0.170, "Litoral Gas")
        _draw_text(img, 0.70, 0.190, "0001-00001234")
        _draw_text(img, 0.72, 0.205, "05/06/2026")
        _draw_text(img, 0.77, 0.262, "20/06/2026")
        _draw_text(img, 0.66, 0.280, "12345678")
        _draw_text(img, 0.80, 0.278, "06/2026")
        _draw_text(img, 0.72, 0.855, "$ 12.345,67")
        return img, {
            "id": "synthetic-gas-valid",
            "provider": "LITORAL_GAS",
            "service": "GAS",
            "document_type": "LITORAL_GAS_BILL",
            "fields": {
                "provider": "LITORAL_GAS",
                "cliente": "12345678",
                "periodo": "06/2026",
                "comprobante": "0001-00001234",
                "fecha_emision": "05/06/2026",
                "vencimiento": "20/06/2026",
                "total": 12345.67,
            },
        }
    if case_id == "cevt_valid":
        _draw_text(img, 0.06, 0.035, "Cooperativa Electrica CEVT", 24)
        _draw_text(img, 0.46, 0.040, "Periodo: 06/2026 0002-00004321", 22)
        _draw_text(img, 0.56, 0.065, "05/06/2026", 22)
        _draw_text(img, 0.56, 0.085, "20/06/2026", 22)
        _draw_text(img, 0.60, 0.165, "99887766", 22)
        _draw_text(img, 0.22, 0.205, "Medidor 123456789", 22)
        _draw_text(img, 0.10, 0.485, "Cliente 11223344", 22)
        _draw_text(img, 0.60, 0.330, "$ 45.678,90", 22)
        return img, {
            "id": "synthetic-cevt-valid",
            "provider": "CEVT",
            "service": "ELECTRICITY",
            "document_type": "CEVT_ELECTRICITY_BILL",
            "fields": {
                "provider": "CEVT",
                "cliente": "11223344",
                "medidor": "123456789",
                "periodo": "06/2026",
                "comprobante": "0002-00004321",
                "fecha_emision": "05/06/2026",
                "vencimiento": "20/06/2026",
                "codigo_pago_electronico": "99887766",
                "total": 45678.90,
            },
        }
    if case_id == "gas_invalid_period":
        img, expected = _base_case_image("gas_valid")
        _draw_text(img, 0.80, 0.278, "13/2026")
        expected = dict(expected)
        expected["id"] = "synthetic-gas-invalid-period"
        expected["fields"] = dict(expected["fields"])
        expected["fields"].pop("periodo")
        expected["must_reject_fields"] = ["periodo"]
        return img, expected

    return img, {
        "id": "synthetic-unknown-blank",
        "provider": "UNKNOWN",
        "service": "UNKNOWN",
        "document_type": "MANUAL_REVIEW",
        "fields": {},
    }


def build_synthetic_dataset(docs: int, out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cycle = ["gas_valid", "cevt_valid", "gas_invalid_period", "unknown_blank"]
    cases: list[dict[str, Any]] = []
    for i in range(max(docs, 0)):
        base_id = cycle[i % len(cycle)]
        image, expected = _base_case_image(base_id)
        image = variant(image, i)
        path = out_dir / f"{expected['id']}-{i:04d}.jpg"
        image.save(path, quality=85)
        item = dict(expected)
        item["id"] = f"{expected['id']}-{i:04d}"
        item["image_path"] = path
        item["dataset_kind"] = "synthetic"
        cases.append(item)
    return cases


def _load_local_contract(private_dir: Path, docs: int) -> list[dict[str, Any]]:
    contract_path = private_dir / "expected.local.json"
    if not contract_path.exists():
        return []
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    documents = contract.get("documents", {})
    cases: list[dict[str, Any]] = []
    for doc_key, doc in documents.items():
        image_name = doc.get("image")
        if not image_name:
            continue
        image_path = private_dir / image_name
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS or not image_path.exists():
            continue
        cases.append(
            {
                "id": doc.get("id", doc_key),
                "image_path": image_path,
                "provider": doc.get("provider", doc.get("expected_provider", doc_key)),
                "service": doc.get("service", doc.get("expected_service", "UNKNOWN")),
                "document_type": doc.get("document_type", "UNKNOWN"),
                "fields": doc.get("fields", {}),
                "allowed_missing_fields": doc.get("allowed_missing_fields", []),
                "must_reject_fields": doc.get("must_reject_fields", []),
                "dataset_kind": "local_private",
            }
        )
    if docs and len(cases) < docs and cases:
        expanded = []
        for i in range(docs):
            item = dict(cases[i % len(cases)])
            item["id"] = f"{item['id']}-{i:04d}"
            expanded.append(item)
        return expanded
    return cases[:docs] if docs else cases


def resolve_dataset(args: argparse.Namespace) -> tuple[str, list[dict[str, Any]], str | None]:
    private_dir = Path(args.private_dir)
    if args.dataset in {"auto", "local"}:
        local = _load_local_contract(private_dir, args.docs)
        if local:
            return "local_private", local, None
        if args.dataset == "local":
            return "local_private", [], f"No hay muestras privadas locales en {private_dir}."
    synthetic = build_synthetic_dataset(args.docs, ROOT / "_bench" / "synthetic_inputs")
    reason = None
    if args.dataset == "auto":
        reason = "Muestras privadas locales no disponibles; se uso dataset sintetico/controlado."
    return "synthetic", synthetic, reason


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def values_match(actual: Any, expected: Any) -> bool:
    if expected is None:
        return actual is None
    if isinstance(expected, (int, float)):
        try:
            return math.isclose(float(actual), float(expected), abs_tol=0.01)
        except (TypeError, ValueError):
            return False
    return _as_text(actual).strip().lower() == _as_text(expected).strip().lower()


def evaluate_document_result(
    case: dict[str, Any],
    result: dict[str, Any],
    elapsed_s: float,
) -> dict[str, Any]:
    metadata = result.get("processing_metadata", {})
    structured = result.get("structured_output", {})
    candidate = structured.get("candidate_fields", {}) or {}
    validated = structured.get("validated_fields", {}) or {}
    rejected = structured.get("rejected_fields", {}) or {}
    missing = structured.get("missing_fields", {}) or {}
    expected_fields = dict(case.get("fields", {}))
    if "provider" in candidate or "provider" in validated:
        expected_fields.setdefault("provider", case.get("provider", "UNKNOWN"))
    if "service" in candidate or "service" in validated:
        expected_fields.setdefault("service", case.get("service", "UNKNOWN"))
    allowed_missing = set(case.get("allowed_missing_fields", []))
    must_reject = set(case.get("must_reject_fields", []))

    field_names = sorted(
        set(expected_fields) | set(candidate) | set(validated) | set(rejected) | set(missing) | must_reject
    )
    field_results: dict[str, dict[str, Any]] = {}
    false_positives_avoided: list[dict[str, Any]] = []

    for field in field_names:
        expected = expected_fields.get(field)
        cand = candidate.get(field)
        val = validated.get(field)
        rej = rejected.get(field)
        is_missing = field in missing or (field in expected_fields and field not in validated and field not in rejected)

        if field in rejected or field in must_reject:
            status = "rejected_expected" if field in must_reject else "rejected"
        elif field in validated:
            status = "validated_match" if values_match(val, expected) else "validated_mismatch"
        elif is_missing:
            status = "missing_allowed" if field in allowed_missing else "missing_unexpected"
        else:
            status = "not_expected"

        if rej:
            false_positives_avoided.append(
                {
                    "field": field,
                    "candidate_value": rej.get("value") if isinstance(rej, dict) else cand,
                    "reason": rej.get("reason", "invalid") if isinstance(rej, dict) else "invalid",
                    "validation_applied": "semantic_field_validator",
                }
            )
        elif cand is not None and field not in validated and field not in expected_fields:
            false_positives_avoided.append(
                {
                    "field": field,
                    "candidate_value": cand,
                    "reason": "candidate_not_in_expected_contract",
                    "validation_applied": "provider_or_contract_filter",
                }
            )

        field_results[field] = {
            "expected": expected,
            "candidate": cand,
            "validated": val,
            "rejected": rej,
            "missing": is_missing,
            "status": status,
        }

    provider_detected = metadata.get("provider_detected", "UNKNOWN")
    service_detected = validated.get("service", "UNKNOWN")
    provider_expected = case.get("provider", "UNKNOWN")
    service_expected = case.get("service", "UNKNOWN")
    provider_ok = provider_detected == provider_expected
    service_ok = service_detected == service_expected or service_expected == "UNKNOWN"

    return {
        "id": case.get("id"),
        "dataset_kind": case.get("dataset_kind"),
        "source_file": str(case.get("image_path", "")),
        "expected_provider": provider_expected,
        "expected_service": service_expected,
        "expected_document_type": case.get("document_type", "UNKNOWN"),
        "provider_detected": provider_detected,
        "service_detected": service_detected,
        "provider_match": provider_ok,
        "service_match": service_ok,
        "elapsed_s": round(elapsed_s, 3),
        "timings": metadata.get("timings", {}),
        "engine": metadata.get("engine", "unknown"),
        "raw_ocr_text": result.get("raw_ocr_text", ""),
        "candidate_fields": candidate,
        "validated_fields": validated,
        "rejected_fields": rejected,
        "missing_fields": missing,
        "field_results": field_results,
        "false_positives_avoided": false_positives_avoided,
        "error": None,
    }


def evaluate_error(case: dict[str, Any], exc: Exception, elapsed_s: float) -> dict[str, Any]:
    return {
        "id": case.get("id"),
        "dataset_kind": case.get("dataset_kind"),
        "source_file": str(case.get("image_path", "")),
        "expected_provider": case.get("provider", "UNKNOWN"),
        "expected_service": case.get("service", "UNKNOWN"),
        "provider_detected": "ERROR",
        "service_detected": "ERROR",
        "provider_match": False,
        "service_match": False,
        "elapsed_s": round(elapsed_s, 3),
        "timings": {},
        "engine": "RapidOCR-ONNX-PP-OCRv3",
        "raw_ocr_text": "",
        "candidate_fields": {},
        "validated_fields": {},
        "rejected_fields": {},
        "missing_fields": {},
        "field_results": {},
        "false_positives_avoided": [],
        "error": {"type": type(exc).__name__, "message": str(exc)},
    }


def synthetic_controlled_result(case: dict[str, Any]) -> dict[str, Any]:
    """Devuelve una salida controlada con el mismo contrato que capture_pipeline.

    Se usa solo para dataset sintetico/controlado. No reemplaza el motor real:
    permite que CI y desarrollo sin RapidOCR ni muestras privadas validen el
    parser, agregador, JSON, Markdown y falsos positivos evitados.
    """
    provider = case.get("provider", "UNKNOWN")
    service = case.get("service", "UNKNOWN")
    fields = dict(case.get("fields", {}))
    candidate_fields: dict[str, Any] = {}
    validated_fields: dict[str, Any] = {}
    rejected_fields: dict[str, dict[str, str]] = {}
    missing_fields: dict[str, None] = {}

    if provider != "UNKNOWN":
        candidate_fields.update(fields)
        validated_fields.update(fields)
        validated_fields["provider"] = provider
        validated_fields["service"] = service
        candidate_fields["provider"] = provider

    if case.get("id", "").startswith("synthetic-gas-invalid-period"):
        candidate_fields["periodo"] = "13/2026"
        rejected_fields["periodo"] = {"value": "13/2026", "reason": "month_out_of_range"}
        validated_fields.pop("periodo", None)

    for field in case.get("allowed_missing_fields", []):
        missing_fields[field] = None

    raw_lines = [f"{field}: {value}" for field, value in candidate_fields.items()]
    if provider == "UNKNOWN":
        raw_lines = []

    return {
        "processing_metadata": {
            "provider_detected": provider,
            "provider_confidence": 1.0 if provider != "UNKNOWN" else 0.0,
            "timings": {
                "controlled_decode_s": 0.0,
                "controlled_extract_s": 0.0,
                "total_s": 0.0,
            },
            "engine": "SYNTHETIC-CONTROLLED-NO-OCR",
        },
        "raw_ocr_text": "\n".join(raw_lines),
        "structured_output": {
            "document_type": case.get("document_type", "MANUAL_REVIEW"),
            "source_document_reference": case.get("id"),
            "candidate_fields": candidate_fields,
            "validated_fields": validated_fields,
            "rejected_fields": rejected_fields,
            "missing_fields": missing_fields,
        },
        "field_report": {},
        "field_scores": {},
    }


def _percentile(values: list[float], q: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    return float(statistics.quantiles(values, n=100, method="inclusive")[q - 1])


def _memory_mb() -> float | None:
    try:
        import psutil  # type: ignore

        return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    except Exception:
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return round(usage / 1024, 1)
        except Exception:
            return None


def aggregate_results(
    document_results: list[dict[str, Any]],
    cold_start_s: float | None = None,
    dataset_kind: str = "unknown",
    dataset_note: str | None = None,
) -> dict[str, Any]:
    per_doc = [doc.get("elapsed_s", 0.0) for doc in document_results]
    by_provider: dict[str, Any] = {}
    by_field: dict[str, Any] = defaultdict(lambda: defaultdict(int))
    stage_values: dict[str, list[float]] = defaultdict(list)
    false_positive_count = 0

    for doc in document_results:
        key = f"{doc.get('expected_provider', 'UNKNOWN')}/{doc.get('expected_service', 'UNKNOWN')}"
        entry = by_provider.setdefault(
            key,
            {
                "documents": 0,
                "provider_matches": 0,
                "service_matches": 0,
                "field_status_counts": defaultdict(int),
                "fields": defaultdict(lambda: defaultdict(int)),
                "false_positives_avoided": 0,
                "errors": 0,
            },
        )
        entry["documents"] += 1
        entry["provider_matches"] += int(bool(doc.get("provider_match")))
        entry["service_matches"] += int(bool(doc.get("service_match")))
        entry["errors"] += int(bool(doc.get("error")))
        entry["false_positives_avoided"] += len(doc.get("false_positives_avoided", []))
        false_positive_count += len(doc.get("false_positives_avoided", []))

        for stage, value in (doc.get("timings") or {}).items():
            if isinstance(value, (int, float)):
                stage_values[stage].append(float(value))

        for field, field_result in (doc.get("field_results") or {}).items():
            status = field_result.get("status", "unknown")
            entry["field_status_counts"][status] += 1
            entry["fields"][field][status] += 1
            by_field[field][status] += 1

    timings_by_stage = {
        stage: {
            "p50_s": round(_percentile(values, 50), 3),
            "p95_s": round(_percentile(values, 95), 3),
            "mean_s": round(statistics.mean(values), 3),
        }
        for stage, values in stage_values.items()
    }
    hot_p95 = _percentile(per_doc, 95)
    p95_status = "pass" if hot_p95 <= OPERATIVE_P95_THRESHOLD_S else "risk"

    def plain_counts(mapping: Any) -> dict[str, Any]:
        return {k: plain_counts(v) if isinstance(v, defaultdict) else v for k, v in mapping.items()}

    summary = {
        "dataset": dataset_kind,
        "dataset_note": dataset_note,
        "docs": len(document_results),
        "cold_start_s": round(cold_start_s, 3) if cold_start_s is not None else None,
        "hot_p50_s": round(_percentile(per_doc, 50), 3),
        "hot_p95_s": round(hot_p95, 3),
        "hot_mean_s": round(statistics.mean(per_doc), 3) if per_doc else 0.0,
        "hot_max_s": round(max(per_doc), 3) if per_doc else 0.0,
        "docs_per_minute": round(60.0 / statistics.mean(per_doc), 2) if per_doc and statistics.mean(per_doc) > 0 else 0,
        "batch_total_s": round(sum(per_doc), 3),
        "process_rss_mb": _memory_mb(),
        "timings_by_stage": timings_by_stage,
        "provider_service": plain_counts(by_provider),
        "fields": plain_counts(by_field),
        "false_positives_avoided_count": false_positive_count,
        "thresholds": {
            "hot_p95_s": OPERATIVE_P95_THRESHOLD_S,
            "hot_p95_status": p95_status,
        },
    }
    return {"summary": summary, "documents": document_results}


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Benchmark Precision OCR",
        "",
        f"- Dataset: `{summary['dataset']}`",
        f"- Documentos: {summary['docs']}",
        f"- Cold start: {summary['cold_start_s']}",
        "- Hot p50/p95/media/max: "
        f"{summary['hot_p50_s']}s / {summary['hot_p95_s']}s / "
        f"{summary['hot_mean_s']}s / {summary['hot_max_s']}s",
        f"- Throughput: {summary['docs_per_minute']} docs/min",
        f"- Memoria RSS aprox.: {summary['process_rss_mb']} MB",
        f"- Falsos positivos evitados: {summary['false_positives_avoided_count']}",
        f"- Umbral p95 <= {summary['thresholds']['hot_p95_s']}s: {summary['thresholds']['hot_p95_status']}",
    ]
    if summary.get("dataset_note"):
        lines.append(f"- Nota dataset: {summary['dataset_note']}")

    lines.extend(["", "## Por proveedor/servicio", ""])
    for key, data in summary["provider_service"].items():
        lines.append(f"### {key}")
        lines.append("")
        lines.append(f"- Documentos: {data['documents']}")
        lines.append(f"- Clasificacion proveedor correcta: {data['provider_matches']}/{data['documents']}")
        lines.append(f"- Servicio correcto: {data['service_matches']}/{data['documents']}")
        lines.append(f"- Errores: {data['errors']}")
        lines.append(f"- Falsos positivos evitados: {data['false_positives_avoided']}")
        lines.append("")
        lines.append(
            "| Campo | validated_match | validated_mismatch | rejected | "
            "rejected_expected | missing_allowed | missing_unexpected |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for field, counts in sorted(data["fields"].items()):
            lines.append(
                f"| {field} | {counts.get('validated_match', 0)} | "
                f"{counts.get('validated_mismatch', 0)} | {counts.get('rejected', 0)} | "
                f"{counts.get('rejected_expected', 0)} | {counts.get('missing_allowed', 0)} | "
                f"{counts.get('missing_unexpected', 0)} |"
            )
        lines.append("")

    lines.extend(["## Falsos Positivos Evitados", ""])
    any_fp = False
    for doc in report["documents"]:
        for fp in doc.get("false_positives_avoided", []):
            any_fp = True
            lines.append(
                f"- `{doc['id']}` campo `{fp['field']}` valor `{fp.get('candidate_value')}`: "
                f"{fp.get('reason')} ({fp.get('validation_applied')})"
            )
    if not any_fp:
        lines.append("- No se registraron candidatos rechazados en este lote.")

    lines.extend(["", "## Documentos Con Error", ""])
    errors = [doc for doc in report["documents"] if doc.get("error")]
    if errors:
        for doc in errors:
            lines.append(f"- `{doc['id']}`: {doc['error']['type']} - {doc['error']['message']}")
    else:
        lines.append("- Ninguno.")
    lines.append("")
    return "\n".join(lines)


def run_benchmark(
    cases: list[dict[str, Any]],
    dataset_kind: str,
    dataset_note: str | None,
    cold_start_s: float | None,
    processor: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    document_results: list[dict[str, Any]] = []
    for case in cases:
        path = Path(case["image_path"])
        t0 = time.perf_counter()
        try:
            if processor is None:
                result = capture_pipeline.process_document(str(path), case.get("id") or path.name)
            else:
                result = processor(case)
            elapsed = time.perf_counter() - t0
            document_results.append(evaluate_document_result(case, result, elapsed))
        except Exception as exc:  # preservar el lote y reportar por documento
            elapsed = time.perf_counter() - t0
            document_results.append(evaluate_error(case, exc, elapsed))
    return aggregate_results(document_results, cold_start_s, dataset_kind, dataset_note)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    dataset_kind, cases, dataset_note = resolve_dataset(args)
    if not cases:
        print(dataset_note or "No hay documentos para evaluar.")
        return 0

    use_controlled = dataset_kind == "synthetic" and args.synthetic_mode == "controlled"
    cold = None if args.skip_cold_start or use_controlled else cold_start()
    processor = synthetic_controlled_result if use_controlled else None
    if use_controlled:
        dataset_note = dataset_note or (
            "Dataset sintetico/controlado sin OCR real; usar --synthetic-mode ocr para procesar imagenes generadas."
        )
    report = run_benchmark(cases, dataset_kind, dataset_note, cold, processor=processor)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    report_md = Path(args.report_md)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_markdown_report(report), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"JSON: {out}")
    print(f"Markdown: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
