"""
Escritor de salida OCR en formato .DATA plano.

Genera un archivo por extracción con nombre:
    SERVICE_YYYYMMDD_HHMMSS.DATA

Contenido:
    Línea 1: nombres de campos separados por ;
    Línea 2: valores extraídos separados por ; (vacío si no encontrado)

No se usa JSON ni comas como separador de columnas.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def ensure_output_dir(output_dir: Path) -> None:
    """Crea el directorio de salida si no existe."""
    output_dir.mkdir(parents=True, exist_ok=True)


def write_data_file(
    service: str,
    fields: List[str],
    values: Dict[str, Optional[str]],
    timestamp: Optional[datetime] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Escribe un archivo .DATA con la extracción de un servicio.

    Args:
        service: Nombre del servicio (ej. "GAS")
        fields: Lista ordenada de nombres de campos
        values: Dict campo -> valor (None o string)
        timestamp: datetime a usar (para testing); si None, usa ahora
        output_dir: Directorio de salida; si None, usa DEFAULT_OUTPUT_DIR

    Returns:
        Path al archivo creado
    """
    out_dir = output_dir or DEFAULT_OUTPUT_DIR
    ensure_output_dir(out_dir)
    ts = timestamp or datetime.now()
    # Formato: YYYYMMDD_HHMMSS
    time_str = ts.strftime("%Y%m%d_%H%M%S")
    filename = f"{service.upper()}_{time_str}.DATA"
    filepath = out_dir / filename

    # Construir líneas
    header_line = ";".join(fields)
    values_line = ";".join("" if values.get(field) is None else str(values.get(field)) for field in fields)

    # Escribir archivo
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header_line + "\n")
        f.write(values_line + "\n")

    return filepath


def write_data_file_from_dict(
    service: str,
    data_dict: Dict[str, Optional[str]],
    timestamp: Optional[datetime] = None,
) -> Path:
    """
    Variante que acepta un dict directamente (asume que las keys son los campos ordenados).
    Para garantizar orden, se ordenan las keys alfabéticamente.
    Nota: se prefiere write_data_file con lista explícita de campos.
    """
    fields = sorted(data_dict.keys())
    return write_data_file(service, fields, data_dict, timestamp)
