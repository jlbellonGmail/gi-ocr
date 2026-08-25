"""
Mock OCR for regression testing.
Provides a fast, deterministic OCR simulation based on expected fixture data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

EXPECTED_DIR = Path(__file__).parent / "fixtures" / "regression" / "expected"
METADATA_FILE = Path(__file__).parent / "fixtures" / "regression" / "metadata.json"


def load_metadata() -> Dict[str, Any]:
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_expected_text_for_image(image_path: Path) -> str:
    """Genera texto OCR simulado basado en expected outputs, 
    formateado para coincidir con los patrones regex de services.ini."""
    # Find corresponding expected file
    rel_path = image_path.relative_to(Path(__file__).parent / "fixtures" / "regression" / "images")
    provider = rel_path.parts[0]
    doc_id = rel_path.stem
    
    expected_path = EXPECTED_DIR / provider / f"{doc_id}.json"
    if not expected_path.exists():
        return ""
    
    with open(expected_path, 'r', encoding='utf-8') as f:
        expected = json.load(f)
    
    provider_upper = expected["provider"].upper()
    doc_type = expected["document_type"].upper()
    fields = expected.get("fields", {})
    
    # Build synthetic OCR text that matches regex patterns from services.ini
    lines = []
    lines.append(f"{provider_upper} - {doc_type}")
    lines.append("=" * 40)
    
    # Provider-specific formatting based on services.ini patterns
    if provider == "gas":
        # GAS patterns: importe|total|saldo|a pagar, cliente|nro cliente|n° cliente|numero cliente
        # medidor|nro medidor|n° medidor|numero medidor, a pagar hasta|pagar hasta|vencimiento|vence
        # periodo|período
        importe = fields.get("importe", {}).get("value", "")
        if isinstance(importe, (int, float)):
            importe = f"$ {importe:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        lines.append(f"Importe Total: {importe}")
        lines.append(f"Cliente: {fields.get('cliente', {}).get('value', '')}")
        lines.append(f"Nro Medidor: {fields.get('nro_medidor', {}).get('value', '')}")
        # a_pagar_hasta expects DD/MM/YYYY format
        a_pagar = fields.get('a_pagar_hasta', {}).get('value', '')
        if '/' in a_pagar and len(a_pagar.split('/')[0]) == 4:
            # Convert YYYY/MM/DD to DD/MM/YYYY
            parts = a_pagar.split('/')
            a_pagar = f"{parts[2]}/{parts[1]}/{parts[0]}"
        lines.append(f"A pagar hasta: {a_pagar}")
        # periodo expects MM/YYYY format
        periodo = fields.get('periodo', {}).get('value', '')
        if '/' in periodo and len(periodo.split('/')[0]) == 4:
            # Convert YYYY/MM to MM/YYYY
            parts = periodo.split('/')
            periodo = f"{parts[1]}/{parts[0]}"
        lines.append(f"Periodo: {periodo}")
    
    elif provider == "cevt":
        # CEVT patterns - order matters for regex matching
        # Put codigo_pago_electronico early to avoid header matching
        lines.append(f"Código de Pago Electrónico: {fields.get('codigo_pago_electronico', {}).get('value', '')}")
        lines.append(f"Medidor: {fields.get('medidor_numero', {}).get('value', '')}")
        lines.append(f"Periodo: {fields.get('periodo', {}).get('value', '')}")
        lines.append(f"Vencimiento: {fields.get('vencimiento', {}).get('value', '')}")
        total = fields.get('total_a_pagar', {}).get('value', '')
        if isinstance(total, (int, float)):
            total = f"$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        lines.append(f"Total a Pagar: {total}")
    
    else:
        # Generic fallback
        for field, field_data in fields.items():
            value = field_data.get("value", "")
            label = field.replace("_", " ").title()
            lines.append(f"{label}: {value}")
    
    return "\n".join(lines)


# Global flag to enable mock mode
MOCK_MODE = True


def enable_mock_mode():
    global MOCK_MODE
    MOCK_MODE = True


def disable_mock_mode():
    global MOCK_MODE
    MOCK_MODE = False