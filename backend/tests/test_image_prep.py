"""Tests de corrección de orientación/perspectiva/escala (image_prep)."""
import numpy as np
import pytest
from PIL import Image

from backend.app import image_prep


def test_normalize_scale_no_upscale():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    out = image_prep.normalize_scale(img, max_side=1600)
    assert out.shape[:2] == (100, 100)


def test_normalize_scale_downscale():
    img = np.zeros((3000, 2000, 3), dtype=np.uint8)
    out = image_prep.normalize_scale(img, max_side=1600)
    assert max(out.shape[:2]) <= 1600


def test_to_rgb_gray():
    g = np.zeros((100, 100), dtype=np.uint8)
    rgb = image_prep.to_rgb(g)
    assert rgb.ndim == 3


def test_prepare_returns_image():
    img = np.zeros((400, 300, 3), dtype=np.uint8)
    out = image_prep.prepare(img)
    assert out.ndim == 3
    assert out.shape[0] > 0


def test_prepare_perspective_opt_out():
    img = np.zeros((400, 300, 3), dtype=np.uint8)
    a = image_prep.prepare(img, apply_perspective=False)
    b = image_prep.prepare(img, apply_perspective=True)
    assert a.shape[:2] == b.shape[:2]