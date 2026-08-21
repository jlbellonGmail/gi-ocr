"""
Evaluador local genérico de OCR para servicios configurables.

Defaults:
- Servicio: GAS
- Muestras: _local_samples/gas/
- Salida: _ocr_reports/

Salida legacy:
- Archivos .DATA
- Separador: ;
- Nombre: SERVICIO_YYYYMMDD_HHMMSS.DATA

Puede escribir salida local de reportes o DATA atómico en storage_bridge/ready/.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_SERVICE = "GAS"
DEFAULT_SAMPLES = "_local_samples/gas"
DEFAULT_OUTPUT = "_ocr_reports"
DEFAULT_TARGET = "reports"

# Bridge directories (defaults from storage_bridge_writer)
DEFAULT_BRIDGE_DIR = Path("storage_bridge")
DEFAULT_INBOUND_DIR = DEFAULT_BRIDGE_DIR / "inbound"
DEFAULT_READY_DIR = DEFAULT_BRIDGE_DIR / "ready"
DEFAULT_FAILED_DIR = DEFAULT_BRIDGE_DIR / "failed"

SAMPLES_DIR = ROOT_DIR / DEFAULT_SAMPLES
REPORTS_DIR = ROOT_DIR / DEFAULT_OUTPUT

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.document_services import (
    DisabledDataEvaluatorServiceError,
    UnsupportedDocumentServiceError,
    get_document_service,
)
from backend.app.extraction_engine import extract_service_fields
from backend.app.ocr import extract_text_from_image
from backend.app.plain_text_writer import write_data_file
from backend.app.service_data_validation import validate_service_data
from backend.app.services_config import get_service_fields
from backend.app.storage_bridge_writer import write_atomic_data_file


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluador local de OCR configurable con salida legacy .DATA.")
    parser.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help=f"Servicio configurado a evaluar. Default: {DEFAULT_SERVICE}",
    )
    parser.add_argument(
        "--samples",
        default=DEFAULT_SAMPLES,
        help=f"Directorio de imágenes de entrada. Default: {DEFAULT_SAMPLES}",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Directorio de salida para archivos .DATA. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--target",
        choices=["reports", "bridge"],
        default=DEFAULT_TARGET,
        help=f"Modo de salida: 'reports' para salida local, 'bridge' para storage bridge. Default: {DEFAULT_TARGET}",
    )
    parser.add_argument(
        "--bridge-inbound",
        default=str(DEFAULT_INBOUND_DIR),
        help=f"Directorio inbound para modo bridge. Default: {DEFAULT_INBOUND_DIR}",
    )
    parser.add_argument(
        "--bridge-ready",
        default=str(DEFAULT_READY_DIR),
        help=f"Directorio ready para modo bridge. Default: {DEFAULT_READY_DIR}",
    )
    parser.add_argument(
        "--bridge-failed",
        default=str(DEFAULT_FAILED_DIR),
        help=f"Directorio failed para modo bridge. Default: {DEFAULT_FAILED_DIR}",
    )
    return parser.parse_args(argv)


def resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def format_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def list_images(samples_dir: Path | None = None) -> list[Path]:
    target_dir = samples_dir if samples_dir is not None else SAMPLES_DIR

    if not target_dir.exists():
        return []

    return sorted(path for path in target_dir.iterdir() if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS)


def _get_validated_data_fields(values: dict[str, str], validation: dict | None) -> dict[str, str]:
    """Return only DATA fields accepted by service validation.

    The evaluator keeps validation metadata for traceability, but .DATA represents
    final structured data and must not publish fields rejected by validation.
    """
    if not validation:
        return dict(values)

    validated_fields = validation.get("validated_fields")
    if isinstance(validated_fields, dict):
        return {field_name: field_value for field_name, field_value in values.items() if field_name in validated_fields}

    # Fallback: if validation uses a different key naming, preserve original values.
    return dict(values)


def _calculate_rejected_metrics(normalized_service: str, extraction: dict[str, Any]) -> dict[str, Any]:
    """
    Devuelve métricas compactas de campos rechazados por campo y servicio.
    Ubicación del evaluador para evitar mezclar responsabilidades.
    La salida presenta contadores de campos rechazados reconocibles para monitoreo, sin modificar .DATA ni OCR.
    """
    metrics = {
        "service": normalized_service,
        "rejected_fields_count": 0,
        "rejected_by_field": {},
        "rejected_by_reason": {},
    }

    # Extraer de validación si existe
    validation = extraction.get("_validation")
    if isinstance(validation, dict) and "rejected_fields" in validation:
        rejected = validation["rejected_fields"]
        for field, info in rejected.items():
            metrics["rejected_fields_count"] += 1
            metrics["rejected_by_field"][field] = metrics["rejected_by_field"].get(field, 0) + 1

            # Obtener motivo (uso "unknown" si no existe)
            if isinstance(info, dict):
                reason = info.get("reason", "unknown")
            else:
                reason = str(info) if info else "unknown"
            metrics["rejected_by_reason"][reason] = metrics["rejected_by_reason"].get(reason, 0) + 1

    return metrics


async def evaluate_image(
    image_path: Path,
    service: str = DEFAULT_SERVICE,
    output_dir: Path | None = None,
    target: str = DEFAULT_TARGET,
    bridge_inbound_dir: Path | None = None,
    bridge_ready_dir: Path | None = None,
    bridge_failed_dir: Path | None = None,
) -> dict[str, Any]:
    normalized_service = service.strip().upper()

    start = time.perf_counter()

    with Image.open(image_path) as image:
        image_np = np.array(image.convert("RGB"))

    ocr_text, lines_count = await extract_text_from_image(
        image_np,
        use_preprocessing=True,
    )

    extraction = await extract_service_fields(
        service=normalized_service,
        ocr_text=ocr_text,
        image_np=image_np,
    )

    # --- Service-specific data validation ---
    try:
        service_def = get_document_service(normalized_service)
        expected_fields = service_def.get("expected_fields", extraction["fields"])
        validation_result = validate_service_data(
            normalized_service,
            extraction["fields"],
            expected_fields,
        )
        extraction["_validation"] = validation_result
    except (UnsupportedDocumentServiceError, DisabledDataEvaluatorServiceError):
        pass

    elapsed = round(time.perf_counter() - start, 3)

    timestamp = datetime.now()

    fields_order = get_service_fields(normalized_service)
    values_dict = extraction["fields"]
    filtered_values = _get_validated_data_fields(values_dict, extraction.get("_validation"))

    if target == "reports":
        target_output_dir = output_dir if output_dir is not None else REPORTS_DIR
        target_output_dir.mkdir(parents=True, exist_ok=True)

        written_path = write_data_file(
            service=normalized_service,
            fields=fields_order,
            values=filtered_values,
            timestamp=timestamp,
            output_dir=target_output_dir,
        )

        filename = f"{normalized_service}_{timestamp.strftime('%Y%m%d_%H%M%S')}.DATA"
        if written_path is not None:
            filename = Path(written_path).name

        data_path = str(target_output_dir / filename)

    elif target == "bridge":
        inbound_dir = bridge_inbound_dir if bridge_inbound_dir is not None else DEFAULT_INBOUND_DIR
        ready_dir = bridge_ready_dir if bridge_ready_dir is not None else DEFAULT_READY_DIR
        failed_dir = bridge_failed_dir if bridge_failed_dir is not None else DEFAULT_FAILED_DIR

        # Ensure bridge directories exist
        Path(inbound_dir).mkdir(parents=True, exist_ok=True)
        Path(ready_dir).mkdir(parents=True, exist_ok=True)
        Path(failed_dir).mkdir(parents=True, exist_ok=True)

        final_path = write_atomic_data_file(
            service=normalized_service,
            fields=fields_order,
            values=filtered_values,
            timestamp=timestamp,
            inbound_dir=inbound_dir,
            ready_dir=ready_dir,
            failed_dir=failed_dir,
        )

        filename = final_path.name
        data_path = str(final_path)

    else:
        raise ValueError(f"Unknown target: {target}")

    # Métrica derivada de validación, agregada al resultado del evaluador (sin alterar .DATA)
    rejected_metrics = _calculate_rejected_metrics(normalized_service, extraction)

    return {
        "file": format_path(image_path),
        "service": normalized_service,
        "elapsed_seconds": elapsed,
        "ocr_lines_count": lines_count,
        "fields": extraction["fields"],
        "detected_fields": extraction["detected_fields"],
        "missing_fields": extraction["missing_fields"],
        "normalized_text": extraction["normalized_text"],
        "ocr_text": ocr_text,
        "data_file": filename,
        "data_path": data_path,
        "target": target,
        "rejected_metrics": rejected_metrics,
    }


async def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    service = args.service.strip().upper()
    samples_dir = resolve_path(args.samples)
    output_dir = resolve_path(args.output)

    samples_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    images = list_images(samples_dir)

    if not images:
        print("No se encontraron imágenes para evaluar.")
        print(f"Servicio: {service}")
        print(f"Directorio de muestras: {format_path(samples_dir)}")
        print(f"Directorio de salida: {format_path(output_dir)}")
        print("Extensiones soportadas: .jpg, .jpeg, .png, .tif, .tiff")
        return 0

    print(f"Servicio: {service}")
    print(f"Directorio de muestras: {format_path(samples_dir)}")
    print(f"Directorio de salida: {format_path(output_dir)}")
    print(f"Imágenes encontradas: {len(images)}")

    for image_path in images:
        print(f"Procesando: {format_path(image_path)}")
        result = await evaluate_image(
            image_path=image_path,
            service=service,
            output_dir=output_dir,
        )

        print(f"  Tiempo: {result['elapsed_seconds']}s")
        print(f"  Líneas OCR: {result['ocr_lines_count']}")
        print(
            "  Campos detectados: "
            + (", ".join(result["detected_fields"]) if result["detected_fields"] else "(ninguno)")
        )
        print(
            "  Campos faltantes: " + (", ".join(result["missing_fields"]) if result["missing_fields"] else "(ninguno)")
        )
        print(f"  Archivo .DATA: {result['data_file']}")

    print("\nEvaluación completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
