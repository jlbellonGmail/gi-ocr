#!/usr/bin/env python3
"""
T3.4 — Flujo visible de procesamiento de comprobante a salida JSON final

Este script expone un flujo ejecutable y visible que procesa un comprobante/fixture
local y genera una salida JSON final integrando:

- raw_ocr_text (del pipeline T3.2)
- salida estructurada existente del pipeline
- field_report (de T3.3) con accepted_fields, rejected_fields, missing_fields y summary_counts

Uso:
    python scripts/t3_4_visible_flow.py [fixture_path]

Si no se especifica fixture_path, usa el fixture por defecto de GAS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Import T3.2 orchestrator
from backend.app.t3_2_orchestrator import orquestar_documento_controlado

# Import T3.3 field reporting processor
from backend.app.field_reporting_processor import (
    generate_field_report,
    classify_fields_from_t32_output,
    differentiate_field_states
)


# Default fixture path
DEFAULT_FIXTURE = "backend/tests/fixtures/gas_sample.jpg"


def create_final_json_output(
    fixture_path: str,
    t32_output: dict,
    field_report: dict,
    document_type: str = "invoice"
) -> dict:
    """
    Build the final JSON output integrating T3.2 and T3.3 outputs.

    Args:
        fixture_path: Path to the processed fixture
        t32_output: Output from T3.2 orchestrator
        field_report: Generated field report from T3.3
        document_type: Generic document type identifier

    Returns:
        dict: Final JSON structure ready for serialization
    """
    return {
        "raw_ocr_text": t32_output.get("raw_ocr_text", ""),
        "structured_output": {
            "document_type": t32_output.get("document_type", document_type),
            "source_document_reference": t32_output.get("fixture_source", fixture_path),
            "candidate_fields": t32_output.get("candidate_fields", {}),
            "validated_fields": t32_output.get("validated_fields", {}),
            "rejected_fields": t32_output.get("rejected_fields", {}),
            "missing_fields": t32_output.get("missing_fields", {}),
        },
        "field_report": field_report,
        "processing_metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "T3.2+T3.3",
            "fixture_path": fixture_path,
        }
    }


def run_t34_visible_flow(fixture_path: str = DEFAULT_FIXTURE) -> dict:
    """
    Execute the complete T3.4 visible flow.

    Process a document fixture and generate final JSON output integrating
    all pipeline stages.

    Args:
        fixture_path: Path to the image fixture to process

    Returns:
        dict: Final JSON output with all integrated stages
    """
    # Step 1: Run T3.2 pipeline (document to structured output)
    t32_result = orquestar_documento_controlado(fixture_path)

    # Step 2: Generate T3.3 field report from T3.2 output
    field_report = classify_fields_from_t32_output(
        t32_result=t32_result,
        document_type="invoice",
        source_document_reference=fixture_path,
        validation_rules=["format_validation", "semantic_check"]
    )

    # Step 3: Build final JSON output
    final_output = create_final_json_output(
        fixture_path=fixture_path,
        t32_output=t32_result,
        field_report=field_report,
        document_type="invoice"
    )

    return final_output


def main() -> int:
    """Main entry point for T3.4 visible flow."""
    # Determine fixture path from args or use default
    fixture_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FIXTURE

    # Validate fixture exists
    if not Path(fixture_path).exists():
        print(f"Error: Fixture not found: {fixture_path}", file=sys.stderr)
        print(f"Usage: python scripts/t3_4_visible_flow.py [fixture_path]", file=sys.stderr)
        return 1

    # Run the visible flow
    result = run_t34_visible_flow(fixture_path)

    # Output as formatted JSON to stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())