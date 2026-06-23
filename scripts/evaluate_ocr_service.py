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

No genera JSON ni escribe en storage_bridge/.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from PIL import Image
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_SERVICE = "GAS"
DEFAULT_SAMPLES = "_local_samples/gas"
DEFAULT_OUTPUT = "_ocr_reports"

SAMPLES_DIR = ROOT_DIR / DEFAULT_SAMPLES
REPORTS_DIR = ROOT_DIR / DEFAULT_OUTPUT

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services_config import get_service_fields
from backend.app.extraction_engine import extract_service_fields
from backend.app.plain_text_writer import write_data_file
from backend.app.ocr import extract_text_from_image


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluador local de OCR configurable con salida legacy .DATA."
    )
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

    return sorted(
        path
        for path in target_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    )


async def evaluate_image(
    image_path: Path,
    service: str = DEFAULT_SERVICE,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    normalized_service = service.strip().upper()
    target_output_dir = output_dir if output_dir is not None else REPORTS_DIR
    target_output_dir.mkdir(parents=True, exist_ok=True)

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

    elapsed = round(time.perf_counter() - start, 3)

    timestamp = datetime.now()
    filename = f"{normalized_service}_{timestamp.strftime('%Y%m%d_%H%M%S')}.DATA"

    fields_order = get_service_fields(normalized_service)
    values_dict = extraction["fields"]

    written_path = write_data_file(
        service=normalized_service,
        fields=fields_order,
        values=values_dict,
        timestamp=timestamp,
        output_dir=target_output_dir,
    )

    if written_path is not None:
        filename = Path(written_path).name

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
            "  Campos faltantes: "
            + (", ".join(result["missing_fields"]) if result["missing_fields"] else "(ninguno)")
        )
        print(f"  Archivo .DATA: {result['data_file']}")

    print("\nEvaluación completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))