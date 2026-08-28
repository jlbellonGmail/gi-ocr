#!/usr/bin/env python3
"""
T3.5 — CLI para procesamiento documental local con exportación JSON.

Adaptador delgado que invoca el pipeline T3.4 existente y exporta el resultado completo.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app.t3_2_orchestrator import orquestar_documento_controlado
from backend.app.field_reporting_processor import classify_fields_from_t32_output
from backend.app.document_result_exporter import save_json_result


def run_pipeline(input_path: str) -> dict:
    """
    Ejecuta el pipeline completo T3.4 (T3.2 + T3.3) y retorna el resultado integrado.

    Args:
        input_path: Ruta al archivo de documento a procesar

    Returns:
        dict: Resultado completo con raw_ocr_text, structured_output, field_report, processing_metadata
    """
    # Step 1: T3.2 pipeline (document to structured output)
    t32_result = orquestar_documento_controlado(input_path)

    # Step 2: T3.3 field report from T3.2 output
    field_report = classify_fields_from_t32_output(
        t32_result=t32_result,
        document_type="invoice",
        source_document_reference=input_path,
        validation_rules=["format_validation", "semantic_check"]
    )

    # Step 3: Build final JSON output (same structure as T3.4)
    final_output = {
        "raw_ocr_text": t32_result.get("raw_ocr_text", ""),
        "structured_output": {
            "document_type": t32_result.get("document_type", "invoice"),
            "source_document_reference": t32_result.get("fixture_source", input_path),
            "candidate_fields": t32_result.get("candidate_fields", {}),
            "validated_fields": t32_result.get("validated_fields", {}),
            "rejected_fields": t32_result.get("rejected_fields", {}),
            "missing_fields": t32_result.get("missing_fields", {}),
        },
        "field_report": field_report,
        "processing_metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "T3.2+T3.3",
            "fixture_path": input_path,
        }
    }

    return final_output


def print_summary(result: dict, input_path: str, output_path: str) -> None:
    """Imprime resumen legible en stdout."""
    field_report = result.get("field_report", {})
    summary = field_report.get("summary_counts", {})
    accepted = summary.get("accepted_count", 0)
    rejected = summary.get("rejected_count", 0)
    missing = summary.get("missing_count", 0)

    # Extraer cliente e importe de validated_fields
    validated = result.get("structured_output", {}).get("validated_fields", {})
    cliente = validated.get("cliente", "N/A")
    importe = validated.get("importe", "N/A")

    # Determinar si importe fue aceptado
    accepted_fields = field_report.get("accepted_fields", [])
    importe_aceptado = "importe" in accepted_fields
    importe_status = "(aceptado)" if importe_aceptado else "(rechazado)"

    print(f"Procesamiento completado: {Path(input_path).name} -> {Path(output_path).name}")
    print(f"Campos aceptados: {accepted} | Rechazados: {rejected} | No encontrados: {missing}")
    print(f"Cliente: {cliente} | Importe: {importe} {importe_status}")


def main() -> int:
    """Main entry point for T3.5 CLI."""
    parser = argparse.ArgumentParser(
        description="Procesa un documento y exporta resultado JSON completo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/process_document.py --input fixtures/gas_sample.jpg --output resultado.json
  python scripts/process_document.py --input /ruta/documento.png --output /ruta/salida.json
        """
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Ruta al archivo de documento a procesar (imagen/PDF)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Ruta del archivo JSON de salida"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Validar entrada
    if not input_path.exists():
        print(f"ERROR: Archivo no encontrado: {input_path}", file=sys.stderr)
        return 1

    if not input_path.is_file():
        print(f"ERROR: No es un archivo: {input_path}", file=sys.stderr)
        return 1

    # Ejecutar pipeline
    try:
        result = run_pipeline(str(input_path))
    except Exception as e:
        print(f"ERROR: Fallo en procesamiento: {e}", file=sys.stderr)
        return 3

    # Exportar resultado
    try:
        save_json_result(result, str(output_path))
    except Exception as e:
        print(f"ERROR: No se puede escribir: {output_path} - {e}", file=sys.stderr)
        return 2

    # Imprimir resumen
    print_summary(result, str(input_path), str(output_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())