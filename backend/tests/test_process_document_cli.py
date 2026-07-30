"""
Tests para T3.5 — CLI Document Processing with JSON Export.

Cobertura:
- Caso exitoso con fixture válido
- Caso inválido (entrada inexistente)
- Error de exportación (ruta no escribible)
- Regresión T3.4
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path for imports
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.process_document import main, run_pipeline, print_summary


class TestProcessDocumentCLI:
    """Tests for the process_document CLI."""

    def test_success_case_with_valid_fixture(self):
        """Caso exitoso: procesar fixture válido y generar JSON."""
        fixture_path = "backend/tests/fixtures/gas_sample.jpg"
        output_path = "backend/tests/fixtures/test_output_success.json"

        try:
            # Ejecutar CLI
            with patch.object(sys, "argv", ["process_document.py", "--input", fixture_path, "--output", output_path]):
                exit_code = main()

            # Verificar exit code
            assert exit_code == 0, f"Expected exit code 0, got {exit_code}"

            # Verificar archivo creado
            assert Path(output_path).exists(), "JSON output file was not created"

            # Verificar JSON parseable
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)

            # Verificar estructura T3.4
            assert "raw_ocr_text" in data
            assert "structured_output" in data
            assert "field_report" in data
            assert "processing_metadata" in data

            # Verificar structured_output
            structured = data["structured_output"]
            assert "candidate_fields" in structured
            assert "validated_fields" in structured
            assert "rejected_fields" in structured
            assert "missing_fields" in structured

            # Verificar field_report
            report = data["field_report"]
            assert "summary_counts" in report
            assert "accepted_fields" in report
            assert "rejected_fields" in report
            assert "missing_fields" in report

            # Verificar valores específicos
            validated = structured["validated_fields"]
            assert validated.get("cliente") == "12345678", f"cliente = {validated.get('cliente')}"

            importe = validated.get("importe")
            assert importe == "123.45", f"importe = {importe}"

            summary = report["summary_counts"]
            assert summary["accepted_count"] == 3, f"accepted_count = {summary['accepted_count']}"
            assert summary["rejected_count"] == 0, f"rejected_count = {summary['rejected_count']}"
            assert summary["missing_count"] == 2, f"missing_count = {summary['missing_count']}"

        finally:
            # Cleanup
            if Path(output_path).exists():
                Path(output_path).unlink()

    def test_invalid_input_nonexistent_file(self):
        """Caso inválido: archivo de entrada que no existe."""
        with patch.object(sys, "argv", ["process_document.py", "--input", "nonexistent_fixture.jpg", "--output", "output.json"]):
            exit_code = main()

        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"

        # No debe crear archivo de salida
        assert not Path("output.json").exists(), "Output file should not be created for invalid input"

    def test_invalid_input_directory_instead_of_file(self):
        """Caso inválido: path es directorio en lugar de archivo."""
        with patch.object(sys, "argv", ["process_document.py", "--input", "backend/tests", "--output", "output.json"]):
            exit_code = main()

        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"

    def test_export_error_unwritable_path(self):
        """Error de exportación: ruta de salida no escribible."""
        fixture_path = "backend/tests/fixtures/gas_sample.jpg"
        unwritable_path = "/nonexistent_root_dir/permission_denied/output.json"

        # Mock save_json_result to simulate write failure
        with patch.object(sys, "argv", ["process_document.py", "--input", fixture_path, "--output", unwritable_path]):
            with patch("scripts.process_document.save_json_result", side_effect=OSError("Permission denied")):
                exit_code = main()

        assert exit_code == 2, f"Expected exit code 2, got {exit_code}"

    def test_pipeline_returns_complete_t34_structure(self):
        """Verificar que run_pipeline devuelve estructura completa T3.4."""
        fixture_path = "backend/tests/fixtures/gas_sample.jpg"

        result = run_pipeline(fixture_path)

        # Verificar todos los campos requeridos
        assert "raw_ocr_text" in result
        assert "structured_output" in result
        assert "field_report" in result
        assert "processing_metadata" in result

        # Verificar structured_output tiene todos los sub-campos
        structured = result["structured_output"]
        assert "document_type" in structured
        assert "source_document_reference" in structured
        assert "candidate_fields" in structured
        assert "validated_fields" in structured
        assert "rejected_fields" in structured
        assert "missing_fields" in structured


class TestPrintSummary:
    """Tests for the print_summary function."""

    def test_print_summary_outputs_correctly(self, capsys):
        """Verificar que el resumen se imprime correctamente."""
        result = {
            "structured_output": {
                "validated_fields": {"cliente": "12345678", "importe": "123.45"}
            },
            "field_report": {
                "summary_counts": {"accepted_count": 3, "rejected_count": 0, "missing_count": 2},
                "accepted_fields": ["cliente", "importe", "a_pagar_hasta"]
            }
        }

        print_summary(result, "test_document.jpg", "test_output.json")

        captured = capsys.readouterr()
        output = captured.out

        assert "Procesamiento completado" in output
        assert "Campos aceptados: 3" in output
        assert "Rechazados: 0" in output
        assert "No encontrados: 2" in output
        assert "Cliente: 12345678" in output
        assert "Importe: 123.45" in output


class TestT34Regression:
    """Tests de regresión para asegurar que T3.4 sigue funcionando."""

    def test_t34_pipeline_still_works(self):
        """Verificar que el pipeline T3.4 sigue disponible y funcional."""
        # Importar directamente T3.4
        from scripts.t3_4_visible_flow import run_t34_visible_flow

        fixture_path = "backend/tests/fixtures/gas_sample.jpg"
        result = run_t34_visible_flow(fixture_path)

        # Verificar estructura T3.4
        assert "raw_ocr_text" in result
        assert "structured_output" in result
        assert "field_report" in result
        assert "processing_metadata" in result

        # Verificar que los valores son consistentes
        report = result["field_report"]
        assert report["summary_counts"]["accepted_count"] == 3