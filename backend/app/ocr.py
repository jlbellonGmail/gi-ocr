"""
OCR Component - Extract text and find field values with global regex search.
"""
import re
import asyncio
import numpy as np
import cv2
import easyocr
from typing import Dict, List, Optional

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['es', 'en'], gpu=False)
    return _reader


def preprocess_image(image_np: np.ndarray) -> np.ndarray:
    """Preprocess image for better OCR."""
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(
        enhanced, h=10, templateWindowSize=7, searchWindowSize=21
    )
    return denoised


async def extract_text_from_image(image_np: np.ndarray, use_preprocessing: bool = True) -> tuple[str, int]:
    """Extract text from image using EasyOCR."""
    if use_preprocessing:
        preprocessed = preprocess_image(image_np)
    else:
        preprocessed = image_np

    reader = _get_reader()
    loop = asyncio.get_event_loop()

    ocr_lines = await loop.run_in_executor(
        None,
        lambda: reader.readtext(preprocessed, detail=0, workers=0)
    )

    ocr_text = "\n".join(ocr_lines) if ocr_lines else ""
    return ocr_text, len(ocr_lines)


async def extract_text_from_zone(
    image_np: np.ndarray,
    zone_coords: tuple,
    use_preprocessing: bool = True
) -> str:
    """
    Extract text from a specific zone of the image.
    Zone coords are percentages: (x1%, y1%, x2%, y2%)
    """
    height, width = image_np.shape[:2]

    # Convert percentages to pixels
    x1 = int(zone_coords[0] * width / 100)
    y1 = int(zone_coords[1] * height / 100)
    x2 = int(zone_coords[2] * width / 100)
    y2 = int(zone_coords[3] * height / 100)

    # Crop zone
    zone_img = image_np[y1:y2, x1:x2]

    if use_preprocessing:
        zone_img = preprocess_image(zone_img)

    # Extract text from zone
    reader = _get_reader()
    loop = asyncio.get_event_loop()

    ocr_lines = await loop.run_in_executor(
        None,
        lambda: reader.readtext(zone_img, detail=0, workers=0)
    )

    text = " ".join(ocr_lines) if ocr_lines else ""
    return text.strip()


def extract_fields_from_zones(
    zone_texts: Dict[str, str]
) -> Dict[str, Optional[str]]:
    """
    Extract values from zone texts.
    Each zone already has clean OCR - just parse and clean up.
    """
    extracted = {}

    for field, text in zone_texts.items():
        value = None
        text_clean = text.strip()

        if not text_clean:
            value = None
        elif "cliente" in field.lower():
            # Extract 8-10 digit number
            match = re.search(r'(\d{8,10})', text_clean)
            value = match.group(1) if match else text_clean[:10]

        elif "medidor" in field.lower():
            # Extract meter number (7-15 digits, might have hyphens)
            match = re.search(r'(\d{4,6}[-]?\d{6,8}|\d{7,15})', text_clean)
            value = match.group(1) if match else text_clean[:15]

        elif "periodo" in field.lower():
            # Extract MM/YYYY or M/YYYY
            match = re.search(r'(\d{1,2}[/-]\d{4})', text_clean)
            value = match.group(1) if match else text_clean[:10]

        elif "pagar" in field.lower() or "vencimiento" in field.lower():
            # Extract date DD/MM/YYYY
            match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text_clean)
            value = match.group(1) if match else text_clean[:10]

        elif "importe" in field.lower() or "total" in field.lower():
            # Extract currency amount
            match = re.search(r'([\d]{1,3}[.,][\d]{3}[.,][\d]{2}|[\d]+[.,][\d]{2})', text_clean)
            value = match.group(1) if match else text_clean[:15]

        else:
            # Generic: keep as is
            value = text_clean[:50]

        extracted[field] = value

    return extracted


def parse_zones_from_config(zones_str: str) -> Dict[str, tuple]:
    """
    Parse zone coordinates from config string format.
    Format: field_name:x1,y1,x2,y2
            field_name:x1,y1,x2,y2
    Returns: {field_name: (x1, y1, x2, y2), ...}
    """
    zones = {}
    if not zones_str or not zones_str.strip():
        return zones

    for line in zones_str.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        field, coords_str = line.split(':', 1)
        try:
            coords = tuple(float(x.strip()) for x in coords_str.split(','))
            if len(coords) == 4:
                zones[field.strip()] = coords
        except ValueError:
            continue

    return zones


def parse_patterns_from_config(patterns_str: str) -> Dict[str, str]:
    """
    Parse regex patterns from config string format.
    Format: field_name:regex_pattern\n field_name:regex_pattern
    """
    patterns = {}
    if not patterns_str or not patterns_str.strip():
        return patterns

    for line in patterns_str.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        field, pattern = line.split(':', 1)
        patterns[field.strip()] = pattern.strip()

    return patterns


def format_extraction_result(
    ocr_text: str,
    extracted_data: Dict[str, Optional[str]],
    fields_requested: List[str],
    engine_used: str,
    filename: str,
    raw_lines_count: int,
    execution_time: float
) -> Dict:
    """Format extraction result for API response."""
    return {
        "status": "success",
        "extracted_data": extracted_data,
        "process_log": {
            "🔄 Engine": engine_used,
            "📂 Archivo": filename,
            "📊 Líneas leídas": raw_lines_count,
            "⏱️ Tiempo": f"{execution_time}s",
            "💾 OCR Leído Completo": ocr_text,
            "📋 Campos Solicitados": fields_requested,
            "✅ Valores Extraídos": {
                k: v if v is not None else "(no encontrado)"
                for k, v in extracted_data.items()
            },
        }
    }
