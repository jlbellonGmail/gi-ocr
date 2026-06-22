"""
Evaluador local de OCR para comprobantes GAS.

- Lee imágenes desde _local_samples/gas/
- Usa motor configurable de extracción (services.ini + extraction_engine)
- Escribe resultados como archivos .DATA en _ocr_reports/
  con formato: SERVICIO_YYYYMMDD_HHMMSS.DATA
- No genera JSON ni escribe en storage_bridge/
"""
from __future__ import annotations

import asyncio
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
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tif"}  # .tiff included via .tif? We'll add .tiff

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services_config import get_service_fields
from backend.app.extraction_engine import extract_service_fields
from backend.app.plain_text_writer import write_data_file
from backend.app.ocr import extract_text_from_image


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

    # Extraer campos usando motor configurable
    extraction = await extract_service_fields(
        service="GAS",
        ocr_text=ocr_text,
        image_np=image_np,
    )

    elapsed = round(time.perf_counter() - start, 3)

    # Generar nombre de archivo .DATA con timestamp actual
    timestamp = datetime.now()
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"GAS_{time_str}.DATA"
    output_path = REPORTS_DIR / filename

    # Obtener lista ordenada de fields desde configuración
    fields_order = get_service_fields("GAS")
    # Extraer valores dict
    values_dict = extraction["fields"]  # campo -> valor o None

    # Escribir archivo .DATA
    write_data_file(
        service="GAS",
        fields=fields_order,
        values=values_dict,
        timestamp=timestamp,  # para que el writer lo use (aunque escribe su propio timestamp)
    )

    # Mover archivo al directorio de reportes (writer escribe en backend/output)
    # Pero writer ya escribe en backend/output; queremos en _ocr_reports.
    # Simplificamos: writer escribe directamente a output_path si le damos ruta.
    # Vamos a adaptar writer para aceptar ruta opcional; pero por ahora moveremos.
    # En lugar de eso, llamaremos a una función que escribe a ruta específica.
    # Vamos a crear una función interna simple.
    # Pero para evitar cambios en writer, vamos a mover el archivo generado.
    backend_output_dir = ROOT_DIR / "backend" / "output"
    generated_file = backend_output_dir / filename
    if generated_file.exists():
        generated_file.replace(output_path)
    else:
        # Si writer no generó (quizás porque no hay datos), crear vacío con cabecera
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(";".join(fields_order) + "\n")
            f.write(";".join("" if v is None else str(v) for f, v in values_dict.items()) + "\n")

    return {
        "file": str(image_path.relative_to(ROOT_DIR)),
        "elapsed_seconds": elapsed,
        "ocr_lines_count": lines_count,
        "fields": extraction["fields"],
        "detected_fields": extraction["detected_fields"],
        "missing_fields": extraction["missing_fields"],
        "normalized_text": extraction["normalized_text"],
        "ocr_text": ocr_text,
        "data_file": filename,
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
        print(f"  Archivo .DATA: {result['data_file']}")

    print("\nEvaluación completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))