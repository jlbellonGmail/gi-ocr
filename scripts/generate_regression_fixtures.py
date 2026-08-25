#!/usr/bin/env python3
"""
Generador de fixtures sintéticos para regresión OCR.
Genera imágenes PNG con texto renderizado sobre plantillas base,
simulando comprobantes de diferentes proveedores.

Los campos por proveedor se leen desde backend/config/services.ini
para garantizar que los expected outputs coincidan con lo que
el motor de extracción produce.
"""

import argparse
import configparser
import json
import os
import random
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services_config import get_service_fields, get_service_config


FONTS = [
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
]

NOISE_LEVELS = [0.02, 0.05, 0.08, 0.1]
ROTATIONS = [0, -1, 1, -2, 2]
DPIS = [200, 300, 400]

# Provider metadata for template rendering
PROVIDER_TEMPLATES = {
    "gas": {
        "document_types": ["factura"],
        "display_name": "ECOGAS S.A.",
        "cuit": "30-12345678-9",
        "direccion": "Av. Siempre Viva 123, CABA",
        "extra_fields": {
            "consumo_m3": lambda: f"{random.randint(5, 100)} m³",
        }
    },
    "cevt": {
        "document_types": ["factura"],
        "display_name": "CEVT S.A.",
        "cuit": "30-87654321-5",
        "direccion": "Av. Corrientes 456, CABA",
        "extra_fields": {}
    },
    "luz": {
        "document_types": ["factura"],
        "display_name": "EDESUR S.A.",
        "cuit": "30-87654321-5",
        "direccion": "Av. Corrientes 456, CABA",
        "extra_fields": {
            "consumo_kwh": lambda: f"{random.randint(50, 1500)} kWh",
        }
    },
    "agua": {
        "document_types": ["factura"],
        "display_name": "AYSA S.A.",
        "cuit": "30-11223344-7",
        "direccion": "Av. Rivadavia 789, CABA",
        "extra_fields": {
            "consumo_m3": lambda: f"{random.randint(5, 100)} m³",
        }
    },
    "telefono": {
        "document_types": ["factura"],
        "display_name": "TELECOM ARGENTINA S.A.",
        "cuit": "30-55667788-2",
        "direccion": "Av. Santa Fe 321, CABA",
        "extra_fields": {
            "numero_linea": lambda: f"011-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
        }
    },
    "factura_a": {
        "document_types": ["factura_a"],
        "display_name": "PROVEEDOR S.A.",
        "cuit": "30-99887766-4",
        "direccion": "Av. Belgrano 555, CABA",
        "extra_fields": {
            "cuit_receptor": lambda: generate_cuit(),
            "iva_21": lambda: f"${generate_amount() * 0.21:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "iva_10_5": lambda: f"${generate_amount() * 0.105:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "razon_social_receptor": lambda: "CLIENTE S.A.",
        }
    },
    "factura_b": {
        "document_types": ["factura_b"],
        "display_name": "COMERCIO LOCAL S.R.L.",
        "cuit": "30-44332211-8",
        "direccion": "Av. Callao 777, CABA",
        "extra_fields": {
            "razon_social_receptor": lambda: "CONSUMIDOR FINAL",
        }
    },
    "ticket": {
        "document_types": ["ticket"],
        "display_name": "SUPERMERCADO EXPRESS",
        "cuit": "30-11112222-3",
        "direccion": "Av. Pueyrredon 888, CABA",
        "extra_fields": {}
    }
}

FONTS = [
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
]

NOISE_LEVELS = [0.02, 0.05, 0.08, 0.1]
ROTATIONS = [0, -1, 1, -2, 2]
DPIS = [200, 300, 400]


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Obtiene una fuente disponible, con fallback."""
    font_name = random.choice(FONTS)
    if bold and "Bold" not in font_name:
        font_name = font_name.replace(".ttf", "-Bold.ttf")
    try:
        return ImageFont.truetype(font_name, size)
    except OSError:
        return ImageFont.load_default()


def generate_random_string(length: int, chars: str = string.ascii_uppercase + string.digits) -> str:
    return ''.join(random.choices(chars, k=length))


def generate_cuit() -> str:
    return f"{random.randint(20, 34):02d}-{random.randint(10000000, 99999999):08d}-{random.randint(0, 9)}"


def generate_date(start_year: int = 2024, end_year: int = 2026) -> str:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    random_date = start + timedelta(days=random.randint(0, (end - start).days))
    return random_date.strftime("%Y-%m-%d")


def generate_comprobante_number(provider: str) -> str:
    if provider in ["factura_a", "factura_b"]:
        return f"{random.randint(1, 9999):04d}-{random.randint(1, 99999999):08d}"
    elif provider == "ticket":
        return f"TK-{random.randint(100000, 999999)}"
    else:
        return f"{random.randint(1, 9999):04d}-{random.randint(1, 99999999):08d}"


def generate_amount() -> float:
    return round(random.uniform(100.0, 50000.0), 2)


def generate_period() -> str:
    year = random.randint(2024, 2026)
    month = random.randint(1, 12)
    return f"{year}-{month:02d}"


def get_provider_fields(provider: str) -> List[str]:
    """Obtiene los campos configurados para un proveedor desde services.ini."""
    try:
        fields = get_service_fields(provider.upper())
        return fields if fields else []
    except Exception:
        # Fallback for providers not in services.ini
        return []


def get_provider_template(provider: str) -> Dict[str, Any]:
    """Obtiene la plantilla de rendering para un proveedor."""
    return PROVIDER_TEMPLATES.get(provider, {})


def render_template(provider: str, doc_type: str, variant: str, dpi: int):
    """Renderiza una plantilla base para el proveedor."""
    width = int(2480 * dpi / 300)  # A4 width at 300 DPI
    height = int(3508 * dpi / 300)  # A4 height at 300 DPI
    
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    template = get_provider_template(provider)
    
    # Header
    y = int(50 * dpi / 300)
    draw.text((int(50 * dpi / 300), y), template.get("display_name", provider.upper()), fill='black', font=get_font(int(24 * dpi / 300), bold=True))
    y += int(35 * dpi / 300)
    draw.text((int(50 * dpi / 300), y), template.get("direccion", ""), fill='black', font=get_font(int(16 * dpi / 300)))
    y += int(35 * dpi / 300)
    draw.text((int(50 * dpi / 300), y), f"CUIT: {template.get('cuit', '')}", fill='black', font=get_font(int(16 * dpi / 300)))
    y += int(50 * dpi / 300)
    
    # Separator
    draw.line([(int(50 * dpi / 300), y), (width - int(50 * dpi / 300), y)], fill='black', width=2)
    y += int(30 * dpi / 300)
    
# Get fields from services.ini
    fields = get_provider_fields(provider)
    
    # Generate field data based on template - map to services.ini field names
    field_data = {}
    extra_fields = template.get("extra_fields", {})
    cuit = template.get("cuit", "")
    
    # Map our generated data to services.ini field names
    comprobante_num = generate_comprobante_number(provider)
    fecha_emision = generate_date()
    importe_val = f"${generate_amount():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    periodo_val = generate_period()
    
    # Standard mapping for common fields
    field_mapping = {
        # GAS fields
        "importe": importe_val,
        "cliente": comprobante_num.split('-')[1] if '-' in comprobante_num else comprobante_num[-8:],
        "nro_medidor": comprobante_num.split('-')[0] if '-' in comprobante_num else comprobante_num[:4],
        "a_pagar_hasta": fecha_emision.replace('-', '/'),
        "periodo": periodo_val.replace('-', '/'),
        # CEVT fields
        "medidor_numero": comprobante_num.split('-')[0] if '-' in comprobante_num else comprobante_num[:4],
        "vencimiento": fecha_emision.replace('-', '/'),
        "codigo_pago_electronico": f"CEVT{random.randint(100000, 999999)}",
        "total_a_pagar": importe_val,
        # Generic fields
        "numero_comprobante": comprobante_num,
        "fecha_emision": fecha_emision,
        "importe_total": importe_val,
        "cuit_emisor": cuit,
        "periodo_facturado": periodo_val,
    }
    
    # Add extra fields from template
    for field_name, generator in extra_fields.items():
        field_mapping[field_name] = generator()
    
    # Only keep fields that are in services.ini for this provider
    for field in fields:
        if field in field_mapping:
            field_data[field] = field_mapping[field]
    
    # Field labels for display
    field_labels = {
        "importe": "Importe:",
        "cliente": "Cliente:",
        "nro_medidor": "Nro Medidor:",
        "a_pagar_hasta": "A pagar hasta:",
        "periodo": "Periodo:",
        "medidor_numero": "Medidor N°:",
        "vencimiento": "Vencimiento:",
        "codigo_pago_electronico": "Código de Pago Electrónico:",
        "total_a_pagar": "Total a Pagar:",
        "numero_comprobante": "Número de Comprobante:",
        "fecha_emision": "Fecha de Emisión:",
        "importe_total": "Importe Total:",
        "cuit_emisor": "CUIT Emisor:",
        "periodo_facturado": "Período Facturado:",
        "consumo_kwh": "Consumo (kWh):",
        "consumo_m3": "Consumo (m³):",
        "numero_linea": "Número de Línea:",
        "cuit_receptor": "CUIT Receptor:",
        "iva_21": "IVA 21%:",
        "iva_10_5": "IVA 10.5%:",
        "razon_social_receptor": "Razón Social Receptor:",
    }
    
    # Render only fields that are in services.ini
    for field in fields:
        if field in field_data:
            label = field_labels.get(field, field.replace("_", " ").title() + ":")
            value = field_data[field]
            draw.text((int(50 * dpi / 300), y), label, fill='black', font=get_font(int(16 * dpi / 300), bold=True))
            draw.text((int(300 * dpi / 300), y), value, fill='black', font=get_font(int(16 * dpi / 300)))
            y += int(30 * dpi / 300)
    
    # Footer
    y += int(50 * dpi / 300)
    draw.line([(int(50 * dpi / 300), y), (width - int(50 * dpi / 300), y)], fill='gray', width=1)
    y += int(20 * dpi / 300)
    draw.text((int(50 * dpi / 300), y), "Documento generado automáticamente para testing de regresión OCR", fill='gray', font=get_font(int(12 * dpi / 300)))
    
    return img, field_data


def apply_noise(img: Image.Image, noise_level: float) -> Image.Image:
    """Aplica ruido gaussiano a la imagen."""
    if noise_level <= 0:
        return img
    
    img_array = img.copy()
    enhancer = ImageEnhance.Sharpness(img_array)
    img_array = enhancer.enhance(1.0 - noise_level * 0.5)
    
    # Add slight blur for higher noise
    if noise_level > 0.05:
        img_array = img_array.filter(ImageFilter.GaussianBlur(radius=noise_level * 2))
    
    return img_array


def apply_rotation(img: Image.Image, degrees: float) -> Image.Image:
    """Aplica rotación leve."""
    if degrees == 0:
        return img
    return img.rotate(degrees, expand=True, fillcolor='white')


def generate_fixtures(
    provider: str,
    count: int,
    output_dir: Path,
    templates_dir: Path,
    expected_dir: Path,
    metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Genera fixtures para un proveedor específico."""
    doc_type = get_provider_template(provider).get("document_types", ["factura"])[0]
    generated = []
    
    for i in range(count):
        variant = "standard"
        noise_level = random.choice(NOISE_LEVELS)
        rotation = random.choice(ROTATIONS)
        dpi = random.choice(DPIS)
        
        doc_id = f"{doc_type}_{i+1:02d}"
        filename = f"{doc_id}.png"
        
        # Render template
        img, field_data = render_template(provider, doc_type, variant, dpi)
        img = apply_noise(img, noise_level)
        img = apply_rotation(img, rotation)
        
        # Save image
        img_path = output_dir / provider / filename
        img.save(img_path, dpi=(dpi, dpi))
        
        # Generate expected output using fields from services.ini
        fields = get_provider_fields(provider)
        expected = {
            "fixtures_version": metadata["fixtures_version"],
            "provider": provider,
            "document_type": doc_type,
            "document_id": doc_id,
            "fields": {}
        }
        
        for field in fields:
            if field in field_data:
                # Normalize value for comparison - use validator output format
                value = field_data[field]
                if field in ["importe_total", "total_a_pagar", "iva_21", "iva_10_5", "importe"]:
                    # Parse amount (AR format: $ 33.867,30 -> 33867.30)
                    value = float(value.replace("$", "").replace(".", "").replace(",", ".").strip())
                elif field in ["consumo_kwh", "consumo_m3"]:
                    value = value.split()[0]
                elif field in ["a_pagar_hasta", "fecha_emision", "vencimiento"]:
                    # Normalize to DD/MM/YYYY (validator output format)
                    # Input is YYYY/MM/DD, convert to DD/MM/YYYY
                    if '/' in value and len(value.split('/')[0]) == 4:
                        parts = value.split('/')
                        value = f"{parts[2]}/{parts[1]}/{parts[0]}"
                elif field == "periodo":
                    # Normalize to MM/YYYY (validator output format)
                    # Input is YYYY/MM, convert to MM/YYYY
                    if '/' in value and len(value.split('/')[0]) == 4:
                        parts = value.split('/')
                        value = f"{parts[1]}/{parts[0]}"
                elif field == "codigo_pago_electronico":
                    # Regex captures only alphanumeric part after anchor, not the prefix
                    # e.g., "CEVT584714" -> "584714" (only trailing digits/alphanum after prefix)
                    import re
                    # Try to extract trailing digits (most common case for CEVT)
                    match = re.search(r'(\d{6,20})$', str(value))
                    if match:
                        value = match.group(1)
                    else:
                        # Fallback: take last 6+ alphanumeric chars
                        match = re.search(r'([A-Z0-9]{6,20})$', str(value))
                        if match:
                            value = match.group(1)
                
                expected["fields"][field] = {
                    "value": value,
                    "confidence": round(random.uniform(0.85, 0.99), 2)
                }
        
        expected["validation"] = {
            "semantic_checks_passed": True,
            "warnings": []
        }
        
        expected_path = expected_dir / provider / f"{doc_id}.json"
        with open(expected_path, 'w', encoding='utf-8') as f:
            json.dump(expected, f, ensure_ascii=False, indent=2)
        
        # Metadata entry
        generated.append({
            "path": f"{provider}/{filename}",
            "provider": provider,
            "document_type": doc_type,
            "document_id": doc_id,
            "variant": variant,
            "noise_level": noise_level,
            "rotation_deg": rotation,
            "dpi": dpi
        })
    
    return generated


def load_existing_metadata(metadata_path: Path) -> Dict[str, Any]:
    """Carga metadata existente o crea nueva."""
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "fixtures_version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generator": "scripts/generate_regression_fixtures.py",
        "images": []
    }


def save_metadata(metadata: Dict[str, Any], metadata_path: Path):
    """Guarda metadata actualizada."""
    metadata["generated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Genera fixtures sintéticos para regresión OCR")
    parser.add_argument("--provider", choices=list(PROVIDER_TEMPLATES.keys()) + ["all", "configured"], default="configured",
                        help="Proveedor a generar (default: configured - solo los de services.ini)")
    parser.add_argument("--count", type=int, default=5,
                        help="Cantidad de fixtures por proveedor (default: 5)")
    parser.add_argument("--fixtures-dir", type=Path, 
                        default=Path("backend/tests/fixtures/regression"),
                        help="Directorio base de fixtures")
    parser.add_argument("--version", type=str, default=None,
                        help="Versión de fixtures (semver)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Semilla para reproducibilidad")
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
    
    fixtures_dir = args.fixtures_dir
    images_dir = fixtures_dir / "images"
    expected_dir = fixtures_dir / "expected"
    templates_dir = fixtures_dir / "templates"
    metadata_path = fixtures_dir / "metadata.json"
    
    # Load existing metadata
    metadata = load_existing_metadata(metadata_path)
    
    if args.version:
        metadata["fixtures_version"] = args.version
    
    if args.provider == "all":
        providers_to_generate = list(PROVIDER_TEMPLATES.keys())
    elif args.provider == "configured":
        # Only providers that exist in services.ini
        from backend.app.services_config import list_services
        providers_to_generate = [s.lower() for s in list_services() if s.lower() in PROVIDER_TEMPLATES]
    else:
        providers_to_generate = [args.provider]
    
    all_generated = []
    for provider in providers_to_generate:
        print(f"Generando {args.count} fixtures para {provider}...")
        generated = generate_fixtures(
            provider, args.count, images_dir, templates_dir, expected_dir, metadata
        )
        all_generated.extend(generated)
        print(f"  Generados: {len(generated)} imágenes")
    
    # Update metadata
    metadata["images"].extend(all_generated)
    save_metadata(metadata, metadata_path)
    
    print(f"\nTotal generados: {len(all_generated)} fixtures")
    print(f"Metadata actualizada: {metadata_path}")
    print(f"Versión: {metadata['fixtures_version']}")


if __name__ == "__main__":
    main()