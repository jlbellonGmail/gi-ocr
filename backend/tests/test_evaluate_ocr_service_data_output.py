"""Tests for the generic OCR local evaluator that generates .DATA output."""

import asyncio
from pathlib import Path
from unittest import mock

import pytest

from scripts import evaluate_ocr_service as evaluator
from scripts.evaluate_ocr_service import evaluate_image


def test_cli_defaults_are_kept():
    """The evaluator must keep the existing no-argument behavior."""
    args = evaluator.parse_args([])

    assert args.service == "GAS"
    assert args.samples == "_local_samples/gas"
    assert args.output == "_ocr_reports"


def test_cli_accepts_explicit_arguments():
    """The evaluator must accept service, samples and output CLI arguments."""
    args = evaluator.parse_args(
        [
            "--service",
            "GAS",
            "--samples",
            "_local_samples\\gas",
            "--output",
            "_ocr_reports",
        ]
    )

    assert args.service == "GAS"
    assert args.samples == "_local_samples\\gas"
    assert args.output == "_ocr_reports"


def test_main_uses_cli_arguments(tmp_path, monkeypatch):
    """The CLI arguments must be passed to the generic evaluator flow."""
    samples_dir = tmp_path / "samples"
    output_dir = tmp_path / "reports"
    samples_dir.mkdir(parents=True, exist_ok=True)

    calls = {}

    def fake_list_images(received_samples_dir):
        calls["samples_dir"] = received_samples_dir
        return [received_samples_dir / "sample.jpg"]

    async def fake_evaluate_image(image_path, service, output_dir):
        calls["image_path"] = image_path
        calls["service"] = service
        calls["output_dir"] = output_dir
        return {
            "elapsed_seconds": 0.001,
            "ocr_lines_count": 1,
            "detected_fields": ["importe"],
            "missing_fields": [],
            "data_file": "GAS_20260623_000000.DATA",
        }

    monkeypatch.setattr(evaluator, "list_images", fake_list_images)
    monkeypatch.setattr(evaluator, "evaluate_image", fake_evaluate_image)

    exit_code = asyncio.run(
        evaluator.main(
            [
                "--service",
                "gas",
                "--samples",
                str(samples_dir),
                "--output",
                str(output_dir),
            ]
        )
    )

    assert exit_code == 0
    assert calls["samples_dir"] == samples_dir
    assert calls["image_path"] == samples_dir / "sample.jpg"
    assert calls["service"] == "GAS"
    assert calls["output_dir"] == output_dir


def test_evaluator_generates_data_filename(tmp_path, monkeypatch):
    """Verify that a .DATA file with the correct naming pattern is created."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    with mock.patch("scripts.evaluate_ocr_service.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_ocr_service.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 12)

            with mock.patch("scripts.evaluate_ocr_service.extract_service_fields") as mock_extract_fields:
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

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_ocr_service.REPORTS_DIR", reports_dir)

                result = asyncio.run(evaluate_image(mock_image_path))

                assert result["service"] == "GAS"
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

    with mock.patch("scripts.evaluate_ocr_service.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_ocr_service.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 5)

            with mock.patch("scripts.evaluate_ocr_service.extract_service_fields") as mock_extract_fields:
                mock_extract_fields.return_value = fake_extraction

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_ocr_service.REPORTS_DIR", reports_dir)

                result = asyncio.run(evaluate_image(mock_image_path))

                data_file_path = reports_dir / result["data_file"]
                assert data_file_path.exists()
                content = data_file_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                assert len(lines) == 2
                assert lines[0] == "importe;cliente;nro_medidor;a_pagar_hasta;periodo"
                assert lines[1] == "100,00;045-987654;34572;20/06/2026;01/2026"


def test_evaluator_preserves_empty_missing_fields(tmp_path, monkeypatch):
    """Fields that are missing should appear as empty entries in the DATA file."""
    mock_image_path = mock.Mock()
    mock_image_path.suffix = ".jpg"
    mock_image_path.relative_to.return_value = Path("mock_gas.jpg")

    mock_image = mock.Mock()
    mock_image.convert.return_value = mock.Mock()
    mock_image.__enter__ = mock.Mock(return_value=mock_image)
    mock_image.__exit__ = mock.Mock(return_value=False)

    with mock.patch("scripts.evaluate_ocr_service.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_ocr_service.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 3)

            with mock.patch("scripts.evaluate_ocr_service.extract_service_fields") as mock_extract_fields:
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

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_ocr_service.REPORTS_DIR", reports_dir)

                result = asyncio.run(evaluate_image(mock_image_path))

                data_file_path = reports_dir / result["data_file"]
                assert data_file_path.exists()
                content = data_file_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                assert lines[0] == "importe;cliente;nro_medidor;a_pagar_hasta;periodo"
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

    with mock.patch("scripts.evaluate_ocr_service.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_ocr_service.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 5)

            with mock.patch("scripts.evaluate_ocr_service.extract_service_fields") as mock_extract_fields:
                mock_extract_fields.return_value = fake_extraction

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_ocr_service.REPORTS_DIR", reports_dir)

                result = asyncio.run(evaluate_image(mock_image_path))

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

    with mock.patch("scripts.evaluate_ocr_service.Image.open", return_value=mock_image):
        with mock.patch("scripts.evaluate_ocr_service.extract_text_from_image") as mock_extract_text:
            mock_extract_text.return_value = ("sample OCR text", 5)

            with mock.patch("scripts.evaluate_ocr_service.extract_service_fields") as mock_extract_fields:
                mock_extract_fields.return_value = fake_extraction

                reports_dir = tmp_path / "_ocr_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                monkeypatch.setattr("scripts.evaluate_ocr_service.REPORTS_DIR", reports_dir)

                asyncio.run(evaluate_image(mock_image_path))

                json_files = list(reports_dir.glob("*.json"))
                assert len(json_files) == 0, f"Found unexpected JSON files: {json_files}"
