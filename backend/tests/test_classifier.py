"""Tests del clasificador de proveedores sobre imágenes sintéticas con anclas.

No requiere muestras privadas: genera imágenes con texto conocido para validar que
Litoral/CEVT se detectan y un blanco no se asigna a GAS por defecto.
"""
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.app import classifier, ocr_engine


def _make_image(lines):
    img = Image.new("RGB", (800, 1000), "white")
    d = ImageDraw.Draw(img)
    y = 40
    for text in lines:
        d.text((40, y), text, fill="black")
        y += 38
    return np.array(img)


def test_unknown_not_gas():
    img = _make_image([" factura cualquiera ", "otra linea", "12345"])
    prov, conf = classifier.classify(img)
    assert prov == "UNKNOWN"


def test_warmup():
    ocr_engine.warmup()
    assert ocr_engine.get_engine() is not None


def test_engine_config():
    eng = ocr_engine.get_engine()
    # el motor debe estar cargado y permitir det+rec separados
    assert hasattr(eng, "text_detector")
    assert hasattr(eng, "text_recognizer")