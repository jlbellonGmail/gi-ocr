"""
Tests para T3.5 — Document Result Exporter.

Verifica que la capa de exportación:
- Guarda JSON parseable
- Preserva estructura completa
- Maneja errores de escritura
- Soporta round-trip (save/load)
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

from backend.app.document_result_exporter import save_json_result, load_json_result


class TestSaveJsonResult:
    """Tests for save_json_result function."""

    def test_save_creates_valid_json(self, tmp_path):
        """Verificar que save_json_result crea JSON parseable."""
        result = {
            "raw_ocr_text": "test text",
            "structured_output": {
                "candidate_fields": {"cliente": "123"},
                "validated_fields": {"cliente": "123"},
                "rejected_fields": {},
                "missing_fields": {}
            },
            "field_report": {
                "summary_counts": {"accepted_count": 1, "rejected_count": 0, "missing_count": 0}
            },
            "processing_metadata": {"timestamp": "2024-01-01T00:00:00Z"}
        }

        output_file = tmp_path / "output.json"
        save_json_result(result, str(output_file))

        # Verificar archivo creado
        assert output_file.exists()

        # Verificar JSON parseable
        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == result

    def test_save_preserves_unicode(self, tmp_path):
        """Verificar que el JSON preserva caracteres Unicode."""
        result = {
            "raw_ocr_text": "Importe $123.45 — Total",
            "field_report": {"summary_counts": {"accepted_count": 1}}
        }

        output_file = tmp_path / "unicode_output.json"
        save_json_result(result, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        assert "Importe $123.45" in content
        assert "Total" in content

    def test_save_creates_parent_directories(self, tmp_path):
        """Verificar que save_json_result crea directorios padre."""
        result = {"test": "data"}

        output_file = tmp_path / "subdir" / "nested" / "output.json"
        save_json_result(result, str(output_file))

        assert output_file.exists()

    def test_save_overwrites_existing_file(self, tmp_path):
        """Verificar que save_json_result sobrescribe archivo existente."""
        old_data = {"old": "data"}
        new_data = {"new": "data"}

        output_file = tmp_path / "output.json"

        # Escribir datos viejos
        save_json_result(old_data, str(output_file))

        # Sobreescribir con nuevos
        save_json_result(new_data, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == new_data

    def test_save_full_t34_structure(self, tmp_path):
        """Verificar que save_json_result preserva estructura T3.4 completa."""
        result = {
            "raw_ocr_text": "OCR text here",
            "structured_output": {
                "document_type": "invoice",
                "source_document_reference": "test.jpg",
                "candidate_fields": {"importe": "123.45", "cliente": "12345678"},
                "validated_fields": {"importe": "123.45", "cliente": "12345678"},
                "rejected_fields": {},
                "missing_fields": {"periodo": None}
            },
            "field_report": {
                "document_type": "invoice",
                "accepted_fields": ["importe", "cliente"],
                "rejected_fields": [],
                "missing_fields": ["periodo"],
                "summary_counts": {"accepted_count": 2, "rejected_count": 0, "missing_count": 1}
            },
            "processing_metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "pipeline_version": "T3.2+T3.3"
            }
        }

        output_file = tmp_path / "t34_output.json"
        save_json_result(result, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["raw_ocr_text"] == "OCR text here"
        assert loaded["structured_output"]["candidate_fields"]["importe"] == "123.45"
        assert loaded["field_report"]["summary_counts"]["accepted_count"] == 2
        assert loaded["processing_metadata"]["pipeline_version"] == "T3.2+T3.3"


class TestLoadJsonResult:
    """Tests for load_json_result function."""

    def test_load_returns_dict(self, tmp_path):
        """Verificar que load_json_result retorna un diccionario."""
        data = {"test": "value", "nested": {"key": "val"}}

        output_file = tmp_path / "test.json"
        save_json_result(data, str(output_file))

        loaded = load_json_result(str(output_file))

        assert isinstance(loaded, dict)
        assert loaded == data

    def test_round_trip(self, tmp_path):
        """Verificar round-trip save/load preserva datos."""
        original = {
            "raw_ocr_text": "test",
            "structured_output": {"validated_fields": {"cliente": "123"}},
            "field_report": {"summary_counts": {"accepted_count": 1}}
        }

        output_file = tmp_path / "round_trip.json"
        save_json_result(original, str(output_file))
        loaded = load_json_result(str(output_file))

        assert loaded == original

    def test_load_nonexistent_file_raises(self):
        """Verificar que cargar archivo inexistente lanza error."""
        with pytest.raises(FileNotFoundError):
            load_json_result("nonexistent_file.json")


class TestErrorHandling:
    """Tests de manejo de errores."""

    def test_save_to_unwritable_path_raises(self):
        """Verificar que escribir en ruta no escribible lanza error."""
        result = {"test": "data"}

        # Mock Path.open to simulate write failure
        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
            with pytest.raises((OSError, PermissionError)):
                save_json_result(result, "/nonexistent_root_dir/permission_denied/output.json")