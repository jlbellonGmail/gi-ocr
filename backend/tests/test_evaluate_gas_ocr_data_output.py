"""Tests for the OCR local evaluator that generates .DATA output.

Import pytest, pathlib, mock.
Import evaluate_image from scripts.evaluate_gas_ocr.

Define minimal tests fulfilling requirements:

- test_evaluator_generates_data_filename
- test_evaluator_writes_header_and_values
- test_evaluator_uses_semicolon_separator
- test_evaluator_does_not_generate_json_output
- test_evaluator_preserves_empty_missing_fields

Each test uses tmp_path fixture, monkeypatch, avoids real _ocr_reports, avoids JSON,
no capfipe, no fixtures besides tmp_path and monkeypatch.

Implementation follows approach: mock Image.open, extract_text_from_image,
extract_service_fields, set REPORTS_DIR to temporary directory,
call evaluate_image via asyncio.run, inspect generated .DATA file.

All tests are pure unit tests, no external files, no real images.
"""
import pytest
from pathlib import Path
from unittest import mock

# Import the function to test
from scripts.evaluate_gas_ocr import evaluate_image


def test_evaluator_generates_data_filename(tmp_path, monkeypatch):
    """Verify that a .DATA file with the correct naming pattern is created."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    # Mock PIL Image.open
    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    with mock.patch("scripts.evaluate_gas_ocr.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_gas_ocr.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 12)

            with mock.patch("scripts.evaluate_gas_ocr.extract_service_fields") as mock_extract_fields:
                fake_extraction = {
                    "fields": {
                        "importe": "100,00",
                        "cliente": "045-987654",
                        "nro_medidor": "34572",
                        "a_pagar_hasta": "20/06/2026",
                        "periodo": "01/2026",
                    },
                    "detected_fields": ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"],
                    "missing_fields": [],
                    "normalized_text": "sample OCR text",
                }
                mock_extract_fields.return_value = fake_extraction

                # Set REPORTS_DIR to a temporary directory
                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_gas_ocr.REPORTS_DIR", reports_dir)

                import asyncio
                result = asyncio.run(evaluate_image(mock_image_path))

                assert result["data_file"].startswith("GAS_")
                assert result["data_file"].endswith(".DATA")
                assert not result["data_file"].endswith(".json")


def test_evaluator_writes_header_and_values(tmp_path, monkeypatch):
    """Verify that the .DATA file contains the correct header and values."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    fake_extraction = {
        "fields": {
            "importe": "100,00",
            "cliente": "045-987654",
            "nro_medidor": "34572",
            "a_pagar_hasta": "20/06/2026",
            "periodo": "01/2026",
        },
        "detected_fields": ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"],
        "missing_fields": [],
        "normalized_text": "sample OCR text",
    }

    with mock.patch("scripts.evaluate_gas_ocr.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_gas_ocr.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 5)

            with mock.patch("scripts.evaluate_gas_ocr.extract_service_fields") as mock_extract_fields:
                mock_extract_fields.return_value = fake_extraction

                # Set temporary reports dir
                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_gas_ocr.REPORTS_DIR", reports_dir)

                import asyncio
                result = asyncio.run(evaluate_image(mock_image_path))

                # Read the generated .DATA file from the temporary directory
                data_file_path = reports_dir / result["data_file"]
                assert data_file_path.exists()
                content = data_file_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                assert len(lines) == 2  # header + values
                assert lines[0] == "importe;cliente;nro_medidor;a_pagar_hasta;periodo"
                expected_values_line = "100,00;045-987654;34572;20/06/2026;01/2026"
                assert lines[1] == expected_values_line


def test_evaluator_preserves_empty_missing_fields(tmp_path, monkeypatch):
    """Fields that are missing should appear as empty entries in the DATA file."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    with mock.patch("scripts.evaluate_gas_ocr.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_gas_ocr.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 3)

            with mock.patch("scripts.evaluate_gas_ocr.extract_service_fields") as mock_extract_fields:
                # Return a result where 'periodo' is missing
                fake_extraction = {
                    "fields": {
                        "importe": "100,00",
                        "cliente": "045-987654",
                        "nro_medidor": "34572",
                        "a_pagar_hasta": "20/06/2026",
                    },
                    "detected_fields": ["importe", "cliente", "nro_medidor", "a_pagar_hasta"],
                    "missing_fields": ["periodo"],
                    "normalized_text": "sample OCR text",
                }
                mock_extract_fields.return_value = fake_extraction

                # Set temporary reports dir
                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_gas_ocr.REPORTS_DIR", reports_dir)

                import asyncio
                result = asyncio.run(evaluate_image(mock_image_path))

                # Read the generated .DATA file
                data_file_path = reports_dir / result["data_file"]
                assert data_file_path.exists()
                content = data_file_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                assert lines[0] == "importe;cliente;nro_medidor;a_pagar_hasta;periodo"
                # Missing field should be an empty entry (trailing semicolon present after previous value)
                assert lines[1] == "100,00;045-987654;34572;20/06/2026;"


def test_evaluator_uses_semicolon_separator(tmp_path, monkeypatch):
    """Verify that the separator used in .DATA files is semicolon, not comma."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    fake_extraction = {
        "fields": {
            "importe": "100,00",  # note: comma inside value is ok
            "cliente": "045-987654",
            "nro_medidor": "34572",
            "a_pagar_hasta": "20/06/2026",
            "periodo": "01/2026",
        },
        "detected_fields": ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"],
        "missing_fields": [],
        "normalized_text": "sample OCR text",
    }

    with mock.patch("scripts.evaluate_gas_ocr.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_gas_ocr.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 5)

            with mock.patch("scripts.evaluate_gas_ocr.extract_service_fields") as mock_extract_fields:
                mock_extract_fields.return_value = fake_extraction

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_gas_ocr.REPORTS_DIR", reports_dir)

                import asyncio
                result = asyncio.run(evaluate_image(mock_image_path))

                # Check the generated file
                data_file_path = reports_dir / result["data_file"]
                assert data_file_path.exists()
                content = data_file_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                assert len(lines) == 2
                header_parts = lines[0].split(";")
                value_parts = lines[1].split(";")
                assert len(header_parts) == 5
                assert len(value_parts) == 5
                assert header_parts == ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"]
                assert value_parts == ["100,00", "045-987654", "34572", "20/06/2026", "01/2026"]


def test_evaluator_does_not_generate_json_output(tmp_path, monkeypatch):
    """Verify that no JSON files are generated during evaluation."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    fake_extraction = {
        "fields": {
            "importe": "100,00",
            "cliente": "045-987654",
            "nro_medidor": "34572",
            "a_pagar_hasta": "20/06/2026",
            "periodo": "01/2026",
        },
        "detected_fields": ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"],
        "missing_fields": [],
        "normalized_text": "sample OCR text",
    }

    with mock.patch("scripts.evaluate_gas_ocr.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_gas_ocr.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 5)

            with mock.patch("scripts.evaluate_gas_ocr.extract_service_fields") as mock_extract_fields:
                mock_extract_fields.return_value = fake_extraction

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_gas_ocr.REPORTS_DIR", reports_dir)

                import asyncio
                result = asyncio.run(evaluate_image(mock_image_path))

                # No JSON files should be present in the reports dir
                json_files = list(reports_dir.glob("*.json"))
                assert len(json_files) == 0, f"Found unexpected JSON files: {json_files}"