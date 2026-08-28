"""Tests de utilidades PDF (texto nativo + render). Genera un PDF en memoria."""

from pathlib import Path

import pytest

pypdfium2 = pytest.importorskip("pypdfium2")
from backend.app import pdf_util


def _make_pdf_blank(tmp_path: Path) -> Path:
    pdf = pypdfium2.PdfDocument.new()
    pdf.new_page(600, 800)
    out = tmp_path / "blank.pdf"
    pdf.save(str(out))
    pdf.close()
    return out


def test_is_pdf():
    assert pdf_util.is_pdf("a.pdf")
    assert not pdf_util.is_pdf("a.jpg")


def test_extract_text_and_render(tmp_path):
    p = _make_pdf_blank(tmp_path)
    pages = pdf_util.extract_text_and_render(str(p))
    assert len(pages) == 1
    assert "page" in pages[0]
    # página en blanco -> sin texto nativo -> needs_ocr True + imagen renderizada
    assert pages[0]["needs_ocr"] is True
    assert pages[0]["image"] is not None


def test_render_all_pages(tmp_path):
    p = _make_pdf_blank(tmp_path)
    imgs = pdf_util.render_all_pages(str(p), scale=1.0)
    assert len(imgs) == 1
    assert imgs[0].ndim == 3
