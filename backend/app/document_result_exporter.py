"""
Capa de exportación de resultados T3.5 — Persistencia JSON del resultado completo del pipeline.

Esta capa se encarga únicamente de persistir el resultado JSON y no de extraer,
validar ni transformar campos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_json_result(result: dict[str, Any], output_path: str) -> None:
    """
    Guarda el resultado completo del pipeline como JSON UTF-8.

    Args:
        result: Diccionario con el resultado completo (raw_ocr_text, structured_output,
                field_report, processing_metadata)
        output_path: Ruta del archivo de salida

    Raises:
        OSError: Si no se puede escribir el archivo
        TypeError: Si el resultado no es serializable a JSON
    """
    output_file = Path(output_path)

    # Crear directorio padre si no existe
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Escribir JSON con encoding UTF-8, sin escape de caracteres no-ASCII
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Verificar que el archivo se escribió correctamente
    if not output_file.exists():
        raise OSError(f"Archivo no se creó: {output_path}")


def load_json_result(input_path: str) -> dict[str, Any]:
    """
    Carga un resultado JSON previamente guardado.

    Args:
        input_path: Ruta del archivo JSON a cargar

    Returns:
        dict: Resultado deserializado

    Raises:
        FileNotFoundError: Si el archivo no existe
        json.JSONDecodeError: Si el JSON es inválido
    """
    with Path(input_path).open("r", encoding="utf-8") as f:
        return json.load(f)


__all__ = ["save_json_result", "load_json_result"]
