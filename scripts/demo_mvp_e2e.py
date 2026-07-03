#!/usr/bin/env python3
"""
GI-OCR / TGI-OCR — Demo MVP End-to-End

Demuestra el flujo completo del MVP desde fixture hasta salida estructurada:
Imagen → OCR → Texto bruto → Candidatos → Validación → Validados/Rechazados/No encontrados → .DATA
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

# Add project root to path for imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Import pipeline components
from backend.app.ocr import extract_text_from_image
from backend.app.gas_extractor import extract_gas_fields
from backend.app.service_data_validation import validate_service_data
from backend.app.storage_bridge_writer import (
    build_data_content,
)

# GAS service fields
GAS_FIELDS = ("importe", "a_pagar_hasta", "cliente", "periodo", "nro_medidor")


def load_fixture_image(image_path: str) -> np.ndarray:
    """Load image fixture as numpy array."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {image_path}")
    image = Image.open(path)
    return np.array(image)


async def run_ocr(image_np: np.ndarray) -> tuple[str, int]:
    """Run OCR on image and return raw text and line count."""
    return await extract_text_from_image(image_np, use_preprocessing=True)


def run_extraction(ocr_text: str) -> dict:
    """Extract candidate fields from OCR text using GAS extractor."""
    return extract_gas_fields(ocr_text)


def run_validation(extracted_fields: dict) -> dict:
    """Validate extracted fields against GAS service rules."""
    return validate_service_data("GAS", extracted_fields, list(GAS_FIELDS))


def build_demo_output(
    fixture_path: str,
    ocr_text: str,
    raw_line_count: int,
    extraction_result: dict,
    validation_result: dict,
    elapsed_time: float,
) -> dict:
    """Build structured demo output differentiating all stages."""
    fields = extraction_result.get("fields", {})

    # Separate candidates (all extracted) from validated/rejected/missing
    candidates = {field: fields.get(field) for field in GAS_FIELDS}

    validated = validation_result.get("validated_fields", {})
    rejected = validation_result.get("rejected_fields", {})
    missing_fields = validation_result.get("missing_fields", [])

    return {
        "meta": {
            "fixture": fixture_path,
            "service": "GAS",
            "timestamp": datetime.now().isoformat(),
            "ocr_time_seconds": round(elapsed_time, 3),
            "ocr_lines": raw_line_count,
        },
        "ocr_raw_text": ocr_text,
        "candidates": candidates,
        "validated": validated,
        "rejected": rejected,
        "not_found": missing_fields,
        "summary": {
            "total_fields": len(GAS_FIELDS),
            "candidates_count": len([v for v in candidates.values() if v is not None]),
            "validated_count": len(validated),
            "rejected_count": len(rejected),
            "not_found_count": len(missing_fields),
            "pipeline_status": "complete",
        },
    }


def run_demo(fixture_path: str = "backend/tests/fixtures/gas_sample.jpg") -> dict:
    """
    Run the complete MVP demo pipeline and return structured output.

    This function is the main entry point for testing and demo purposes.
    It does NOT write files to storage_bridge/ready - it returns the output
    as a dictionary for further processing.

    Args:
        fixture_path: Path to the image fixture to process

    Returns:
        dict: Structured demo output with OCR text, candidates, validated,
              rejected, and not_found fields.
    """
    image_np = load_fixture_image(fixture_path)
    ocr_text, line_count = asyncio.run(run_ocr(image_np))
    extraction_result = run_extraction(ocr_text)
    validation_result = run_validation(extraction_result.get("fields", {}))

    demo_output = build_demo_output(
        fixture_path=fixture_path,
        ocr_text=ocr_text,
        raw_line_count=line_count,
        extraction_result=extraction_result,
        validation_result=validation_result,
        elapsed_time=0.0,  # Will be updated below
    )

    return demo_output


def print_demo_result(demo_output: dict) -> None:
    """Print formatted demo result to console."""
    meta = demo_output["meta"]
    summary = demo_output["summary"]

    print("=" * 70)
    print("GI-OCR / TGI-OCR — MVP End-to-End Demo")
    print("=" * 70)
    print(f"\nFixture: {meta['fixture']}")
    print(f"Servicio: {meta['service']}")
    print(f"Tiempo OCR: {meta['ocr_time_seconds']}s")
    print(f"Lineas OCR: {meta['ocr_lines']}")

    print("\n" + "-" * 70)
    print("1. TEXTO BRUTO OCR")
    print("-" * 70)
    ocr_text = demo_output["ocr_raw_text"]
    print(ocr_text if ocr_text else "(vacio)")

    print("\n" + "-" * 70)
    print("2. CAMPOS CANDIDATOS (extraidos por OCR/Extractor)")
    print("-" * 70)
    for field, value in demo_output["candidates"].items():
        status = "OK" if value else "X"
        print(f"  {status} {field}: {value if value else '(no detectado)'}")

    print("\n" + "-" * 70)
    print("3. CAMPOS VALIDADOS (pasaron validacion semantica)")
    print("-" * 70)
    validated = demo_output["validated"]
    if validated:
        for field, value in validated.items():
            print(f"  OK {field}: {value}")
    else:
        print("  (ninguno)")

    print("\n" + "-" * 70)
    print("4. CAMPOS RECHAZADOS (fallaron validacion)")
    print("-" * 70)
    rejected = demo_output["rejected"]
    if rejected:
        for field, info in rejected.items():
            print(f"  X {field}: {info['value']}  ->  motivo: {info['reason']}")
    else:
        print("  (ninguno)")

    print("\n" + "-" * 70)
    print("5. CAMPOS NO ENCONTRADOS")
    print("-" * 70)
    not_found = demo_output["not_found"]
    if not_found:
        for field in not_found:
            print(f"  ? {field}")
    else:
        print("  (ninguno)")

    print("\n" + "-" * 70)
    print("RESUMEN")
    print("-" * 70)
    print(f"  Total campos esperados: {summary['total_fields']}")
    print(f"  Candidatos detectados:  {summary['candidates_count']}")
    print(f"  Validados:              {summary['validated_count']}")
    print(f"  Rechazados:             {summary['rejected_count']}")
    print(f"  No encontrados:         {summary['not_found_count']}")

    print("\n" + "=" * 70)
    print("Demo MVP End-to-End completada")
    print("=" * 70)


async def main_async() -> int:
    """Async main entry point for the demo."""
    fixture_path = "backend/tests/fixtures/gas_sample.jpg"

    print(f"\nIniciando demo MVP con fixture: {fixture_path}\n")

    # 1. Load image
    try:
        image_np = load_fixture_image(fixture_path)
        print(f"Imagen cargada: {image_np.shape[1]}x{image_np.shape[0]} px")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    # 2. OCR
    print("\nEjecutando OCR...")
    start_time = time.time()
    ocr_text, line_count = await run_ocr(image_np)
    ocr_elapsed = time.time() - start_time
    print(f"OCR completado en {ocr_elapsed:.3f}s ({line_count} lineas)")

    # 3. Extraction (candidates)
    print("\nExtrayendo campos candidatos...")
    extraction_result = run_extraction(ocr_text)
    print(f"Extraccion completada: {len(extraction_result.get('detected_fields', []))} campos detectados")

    # 4. Validation
    print("\nValidando campos semanticamente...")
    validation_result = run_validation(extraction_result.get("fields", {}))
    print(f"Validacion completada: {len(validation_result.get('validated_fields', {}))} validados, {len(validation_result.get('rejected_fields', {}))} rechazados")

    # 5. Build demo output
    demo_output = build_demo_output(
        fixture_path=fixture_path,
        ocr_text=ocr_text,
        raw_line_count=line_count,
        extraction_result=extraction_result,
        validation_result=validation_result,
        elapsed_time=ocr_elapsed,
    )

    # 6. Print results (NO file persistence)
    print_demo_result(demo_output)

    return 0


def main() -> int:
    """Main entry point."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())