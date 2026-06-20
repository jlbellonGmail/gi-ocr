import uuid
import configparser
import time
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from PIL import Image

from .ocr import (
    extract_text_from_image,
    extract_text_from_zone,
    extract_fields_from_zones,
    format_extraction_result,
    parse_zones_from_config
)

app = FastAPI(
    title="Smart Invoice Capture API",
    version="1.1.0",
    description="Backend OCR real con extracción de datos configurables por servicio"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
READY_DIR = BASE_DIR / "storage_bridge" / "ready"
CONFIG_DIR = BASE_DIR / "backend" / "config"
SERVICES_INI = CONFIG_DIR / "services.ini"

for p in (READY_DIR, CONFIG_DIR):
    p.mkdir(parents=True, exist_ok=True)


def _load_config() -> configparser.ConfigParser:
    """Load services configuration from services.ini"""
    if not SERVICES_INI.exists():
        SERVICES_INI.parent.mkdir(parents=True, exist_ok=True)
        SERVICES_INI.touch()
    cfg = configparser.ConfigParser()
    cfg.read(SERVICES_INI, encoding="utf-8")
    return cfg


@app.get("/api/v1")
async def api_root():
    return {"status": "ok", "message": "Smart Invoice Capture API conectado correctamente"}


@app.get("/api/v1/services")
async def list_services():
    """List all configured services"""
    cfg = _load_config()
    result = {}
    for section in cfg.sections():
        result[section] = dict(cfg[section])
    return {"services": result}


@app.post("/api/v1/services")
async def add_service(payload: dict):
    """Add a new service configuration"""
    name = payload.get("name")
    fields = payload.get("fields", "")

    if not name:
        raise HTTPException(status_code=400, detail="Falta el nombre del servicio")

    cfg = _load_config()
    if cfg.has_section(name):
        raise HTTPException(status_code=409, detail=f"El servicio '{name}' ya existe")

    cfg.add_section(name)
    cfg.set(name, "fields", fields)

    with open(SERVICES_INI, "w", encoding="utf-8") as f:
        cfg.write(f)
    return {"status": "created", "service": name, "fields": fields}


@app.delete("/api/v1/services/{service_name}")
async def delete_service(service_name: str):
    """Delete a service configuration"""
    cfg = _load_config()
    if not cfg.has_section(service_name):
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    cfg.remove_section(service_name)
    with open(SERVICES_INI, "w", encoding="utf-8") as f:
        cfg.write(f)
    return {"status": "deleted", "service": service_name}


@app.post("/api/v1/capture")
async def capture(file: UploadFile = File(...)):
    """
    Capture and extract data from uploaded image.
    - Detects service from OCR content or filename
    - Extracts configured fields based on services.ini
    - Writes data to output file if extraction successful
    """
    start_time = time.time()

    # Validate file format
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".pdf")):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")

    engine_used = "EasyOCR Nativo"
    ocr_text = ""
    raw_lines_count = 0

    # Step 1: Extract text from image
    try:
        image = Image.open(file.file)
        image_np = np.array(image)

        # Extract text with preprocessing
        ocr_text, raw_lines_count = await extract_text_from_image(image_np, use_preprocessing=True)

        if not ocr_text.strip():
            raise ValueError("EasyOCR returned empty text")

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        engine_used = "Hybrid Mode (OCR failed)"
        ocr_text = f"Error: {str(e)}"

    # Step 2: Detect service from OCR content or filename
    cfg = _load_config()
    detected_service = "Generico"
    configured_fields = []
    service_zones = {}

    filename_lower = file.filename.lower()
    for section in cfg.sections():
        sec_lower = section.lower()
        if sec_lower in ocr_text.lower() or sec_lower in filename_lower:
            detected_service = section
            fields_str = cfg.get(section, "fields", fallback="")
            fields_str = fields_str.strip('"')
            configured_fields = [f.strip() for f in fields_str.split(",") if f.strip()]

            # Load zones for this service if they exist
            zones_str = cfg.get(section, "zones", fallback="")
            service_zones = parse_zones_from_config(zones_str)
            break

    # Step 3: Extract values from zones
    extracted_data = {}
    zone_texts = {}

    if service_zones and configured_fields:
        # Extract OCR text from each zone
        for field in configured_fields:
            if field in service_zones:
                zone_coords = service_zones[field]
                text = await extract_text_from_zone(image_np, zone_coords, use_preprocessing=True)
                zone_texts[field] = text
                print(f"[ZONE DEBUG] {field}: '{text}'")

        # Parse extracted zone texts
        extracted_data = extract_fields_from_zones(zone_texts)
    else:
        # Fallback: no zones defined, just return empty
        extracted_data = {field: None for field in configured_fields}

    # Step 4: Write to output file if we have real data
    has_real_data = any(v is not None for v in extracted_data.values())

    timestamp = datetime.now().isoformat()
    file_id = str(uuid.uuid4())[:8]
    output_path = READY_DIR / f"{detected_service}.txt"
    data_written = False

    if has_real_data and configured_fields:
        header_line = ",".join(configured_fields)
        values_list = [
            str(extracted_data.get(field, "")) if extracted_data.get(field) is not None else ""
            for field in configured_fields
        ]
        values_line = ",".join(values_list)

        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"--- CAPTURA {timestamp} (ID: {file_id}) ---\n")
            f.write(header_line + "\n")
            f.write(values_line + "\n")
            f.write("\n")
        data_written = True

    elapsed = round(time.time() - start_time, 3)

    # Step 5: Format and return response
    return format_extraction_result(
        ocr_text=ocr_text,
        extracted_data=extracted_data,
        fields_requested=configured_fields,
        engine_used=engine_used,
        filename=file.filename,
        raw_lines_count=raw_lines_count,
        execution_time=elapsed
    )
