"""OCR Component — API de compatibilidad implementada sobre el motor RapidOCR/ONNX.

Mantiene la firma histórica (extract_text_from_image, extract_text_from_zone,
extract_fields_from_zones, parse_zones_from_config, preprocess_image) para que el
pipeline legacy y los tests T3.1–T3.5 funcionen sobre el nuevo motor local, sin EasyOCR.
"""
from __future__ import annotations

import asyncio
import re
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from . import ocr_engine


def preprocess_image(image_np: np.ndarray) -> np.ndarray:
    """Preprocesa la imagen: escala de grises + CLAHE + denoising (no destructivo)."""
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10, templateWindowSize=7, searchWindowSize=21)
    return denoised


async def extract_text_from_image(image_np: np.ndarray, use_preprocessing: bool = True) -> Tuple[str, int]:
    """Extrae texto completo de la imagen con RapidOCR (fallback legacy)."""
    if use_preprocessing and image_np.ndim == 3:
        image_np = preprocess_image(image_np)
    loop = asyncio.get_event_loop()
    result, _ = await loop.run_in_executor(None, ocr_engine.ocr_full_page, image_np)
    lines = [r["text"] for r in result] if result else []
    text = "\n".join(lines)
    return text, len(lines)


async def extract_text_from_zone(
    image_np: np.ndarray,
    zone_coords: tuple,
    use_preprocessing: bool = True,
) -> str:
    """Extrae texto de una zona (coords en porcentaje 0-100) recortando y OCR."""
    height, width = image_np.shape[:2]
    x1 = int(zone_coords[0] * width / 100)
    y1 = int(zone_coords[1] * height / 100)
    x2 = int(zone_coords[2] * width / 100)
    y2 = int(zone_coords[3] * height / 100)
    zone = image_np[y1:y2, x1:x2]
    if use_preprocessing and zone.ndim == 3:
        zone = preprocess_image(zone)
    loop = asyncio.get_event_loop()
    result, _ = await loop.run_in_executor(None, ocr_engine.ocr_full_page, zone)
    texts = [r["text"] for r in result] if result else []
    return " ".join(texts).strip()


def extract_fields_from_zones(zone_texts: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Extracción genérica por nombre de campo (compatibilidad hacia atrás)."""
    extracted: Dict[str, Optional[str]] = {}
    for field, text in zone_texts.items():
        value: Optional[str] = None
        text_clean = (text or "").strip()
        if not text_clean:
            value = None
        elif "cliente" in field.lower():
            match = re.search(r"(\d{8,10})", text_clean)
            value = match.group(1) if match else text_clean[:10]
        elif "medidor" in field.lower():
            match = re.search(r"(\d{4,6}[-]?\d{6,8}|\d{7,15})", text_clean)
            value = match.group(1) if match else text_clean[:15]
        elif "periodo" in field.lower() or "período" in field.lower():
            match = re.search(r"(\d{1,2}[/-]\d{4})", text_clean)
            value = match.group(1) if match else text_clean[:10]
        elif "pagar" in field.lower() or "vencimiento" in field.lower():
            match = re.search(r"(\d{1,2}[/\-\.\*]\d{1,2}[/\-\.\*]\d{2,4})", text_clean)
            value = match.group(1) if match else None
        elif "importe" in field.lower() or "total" in field.lower():
            match = re.search(r"(\d{1,3}[.,]\d{3}[.,]\d{2}|\d+[.,]\d{2})", text_clean)
            value = match.group(1) if match else text_clean[:15]
        else:
            value = text_clean[:50]
        extracted[field] = value
    return extracted


def parse_zones_from_config(zones_str: str) -> Dict[str, tuple]:
    """Parsea zonas desde config: field_name:x1,y1,x2,y2 (porcentaje)."""
    zones: Dict[str, tuple] = {}
    if not zones_str or not zones_str.strip():
        return zones
    for line in zones_str.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        field, coords_str = line.split(":", 1)
        try:
            coords = tuple(float(x.strip()) for x in coords_str.split(","))
            if len(coords) == 4:
                zones[field.strip()] = coords
        except ValueError:
            continue
    return zones


def parse_patterns_from_config(patterns_str: str) -> Dict[str, str]:
    patterns: Dict[str, str] = {}
    if not patterns_str or not patterns_str.strip():
        return patterns
    for line in patterns_str.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        field, pattern = line.split(":", 1)
        patterns[field.strip()] = pattern.strip()
    return patterns


def format_extraction_result(
    ocr_text: str,
    extracted_data: Dict[str, Optional[str]],
    fields_requested: List[str],
    engine_used: str,
    filename: str,
    raw_lines_count: int,
    execution_time: float,
) -> Dict:
    return {
        "status": "success",
        "extracted_data": extracted_data,
        "process_log": {
            "Engine": engine_used,
            "Archivo": filename,
            "Lineas": raw_lines_count,
            "Tiempo_s": execution_time,
            "OCR_Leido": ocr_text,
            "Campos_Solicitados": fields_requested,
            "Valores": {k: v if v is not None else "(no encontrado)" for k, v in extracted_data.items()},
        },
    }


__all__ = [
    "preprocess_image",
    "extract_text_from_image",
    "extract_text_from_zone",
    "extract_fields_from_zones",
    "parse_zones_from_config",
    "parse_patterns_from_config",
    "format_extraction_result",
]