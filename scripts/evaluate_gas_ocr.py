from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT_DIR / "_local_samples" / "gas"
REPORTS_DIR = ROOT_DIR / "_ocr_reports"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.ocr import extract_text_from_image  # noqa: E402


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def extract_first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_gas_fields(ocr_text: str) -> dict[str, str | None]:
    text = normalize_text(ocr_text)

    return {
        "importe": extract_first(
            [
                r"(?:importe|total|a pagar|saldo)\D{0,30}(\$?\s?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?)",
                r"(\$?\s?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2}))",
                r"(\$?\s?\d+(?:[.,]\d{2}))",
            ],
            text,
        ),
        "a pagar hasta": extract_first(
            [
                r"(?:pagar hasta|vencimiento|vence|fecha de vencimiento)\D{0,30}(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            ],
            text,
        ),
        "n° cliente": extract_first(
            [
                r"(?:cliente|cuenta|usuario|nro cliente|n° cliente|numero cliente)\D{0,30}(\d{6,12})",
                r"\b(\d{8,10})\b",
            ],
            text,
        ),
        "periodo": extract_first(
            [
                r"(?:periodo|período)\D{0,30}(\d{1,2}[/-]\d{2,4})",
                r"\b(\d{1,2}[/-]\d{4})\b",
            ],
            text,
        ),
        "nro medidor": extract_first(
            [
                r"(?:medidor|nro medidor|n° medidor|numero medidor)\D{0,30}(\d{6,15})",
                r"\b(\d{10,15})\b",
            ],
            text,
        ),
    }


def list_images() -> list[Path]:
    if not SAMPLES_DIR.exists():
        return []

    return sorted(
        path
        for path in SAMPLES_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    )


async def evaluate_image(image_path: Path) -> dict[str, Any]:
    start = time.perf_counter()

    with Image.open(image_path) as image:
        image_np = np.array(image.convert("RGB"))

    ocr_text, lines_count = await extract_text_from_image(
        image_np,
        use_preprocessing=True,
    )

    elapsed = round(time.perf_counter() - start, 3)
    fields = extract_gas_fields(ocr_text)

    detected_fields = [key for key, value in fields.items() if value]
    missing_fields = [key for key, value in fields.items() if not value]

    return {
        "file": str(image_path.relative_to(ROOT_DIR)),
        "elapsed_seconds": elapsed,
        "ocr_lines_count": lines_count,
        "fields": fields,
        "detected_fields": detected_fields,
        "missing_fields": missing_fields,
        "ocr_text": ocr_text,
    }


async def main() -> int:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    images = list_images()

    if not images:
        print("No se encontraron imágenes para evaluar.")
        print(f"Coloque imágenes reales o sanitizadas en: {SAMPLES_DIR.relative_to(ROOT_DIR)}")
        print("Extensiones soportadas: .jpg, .jpeg, .png, .tif, .tiff")
        return 0

    print(f"Imágenes encontradas: {len(images)}")
    results = []

    for image_path in images:
        print(f"Procesando: {image_path.relative_to(ROOT_DIR)}")
        result = await evaluate_image(image_path)
        results.append(result)

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

    report = {
        "service": "GAS",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "samples_dir": str(SAMPLES_DIR.relative_to(ROOT_DIR)),
        "engine": "current_project_ocr",
        "total_images": len(results),
        "results": results,
    }

    report_path = REPORTS_DIR / f"gas-evaluation-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Reporte generado: {report_path.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
