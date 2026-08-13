"""Utilidades de PDF: extracción de texto nativo primero; OCR sólo en páginas sin texto.

Soporta PDF multipágina. Usa pypdfium2 (licencia BSD-3-Clause / Apache-2.0).
"""
from __future__ import annotations

from typing import List

import numpy as np


def _import_pdfium():
    try:
        import pypdfium2 as pdfium
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"pypdfium2 no disponible: {e}")
    return pdfium


def is_pdf(path: str) -> bool:
    return str(path).lower().endswith(".pdf")


def extract_text_and_render(path: str) -> List[dict]:
    """Devuelve lista por página: {"page": i, "text": str, "needs_ocr": bool, "image": np.ndarray}.

    Estrategia: extrae texto nativo; si una página tiene poco texto utilizable
    (<6 caracteres alfanuméricos), la renderiza a imagen para OCR focalizado.
    """
    pdfium = _import_pdfium()
    pages_out = []
    pdf = pdfium.PdfDocument(path)
    try:
        n = len(pdf)
        for i in range(n):
            page = pdf[i]
            textpage = page.get_textpage()
            raw = textpage.get_text_range() or ""
            textpage.close()
            alnum = sum(1 for c in raw if c.isalnum())
            needs_ocr = alnum < 6
            image = None
            if needs_ocr:
                pil = page.render(scale=2.0).to_pil().convert("RGB")
                image = np.array(pil)
            pages_out.append(
                {"page": i, "text": raw, "needs_ocr": needs_ocr, "image": image}
            )
            page.close()
    finally:
        pdf.close()
    return pages_out


def render_all_pages(path: str, scale: float = 2.0) -> List[np.ndarray]:
    """Renderiza todas las páginas a imágenes (para vista previa y OCR completo)."""
    pdfium = _import_pdfium()
    out = []
    pdf = pdfium.PdfDocument(path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            pil = page.render(scale=scale).to_pil().convert("RGB")
            out.append(np.array(pil))
            page.close()
    finally:
        pdf.close()
    return out


__all__ = ["is_pdf", "extract_text_and_render", "render_all_pages"]