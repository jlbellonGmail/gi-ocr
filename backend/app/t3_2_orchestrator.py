"""Orchestrator for T3.2 – controlled document to structured output."""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
from backend.app import gas_extractor, ocr
from PIL import Image


def orquestar_documento_controlado(gas_image_path: str | Path) -> dict:
    """Process a control fixture image and return structured OCR output.

    The returned dictionary contains the raw OCR text, candidate fields as
    extracted by ``gas_extractor`` and a simple validation stage that flags
    missing fields.
    """
    # Load image
    img_path = Path(gas_image_path)
    img = Image.open(img_path)
    img_np = np.array(img)

    # Perform OCR using asyncio.run() for proper event loop handling
    async def _run_ocr():
        return await ocr.extract_text_from_image(img_np)

    ocr_text, _ = asyncio.run(_run_ocr())

    # Extract GAS specific fields
    extraction = gas_extractor.extract_gas_fields(ocr_text)
    fields = extraction["fields"]
    missing = extraction["missing_fields"]

    result = {
        "raw_ocr_text": ocr_text,
        "candidate_fields": fields,
        "validated_fields": {k: v for k, v in fields.items() if v is not None},
        "rejected_fields": {},
        "missing_fields": {k: None for k in missing},
        "document_type": "GAS",
        "fixture_source": str(img_path),
    }
    return result


__all__ = ["orquestar_documento_controlado"]
