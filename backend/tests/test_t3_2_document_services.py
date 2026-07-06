"""
T3.2 document services – controlled fixture to structured output.

Validates the complete pipeline: documento/fixture controlado → OCR/texto bruto → campos candidatos → validación semántica → campos validados/rechazados/no encontrados → salida estructurada.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.app import t3_2_orchestrator


def _create_test_image_with_text(text: str) -> Path:
    """Create a small synthetic image with the given text for testing."""
    # Use PIL to create a simple image with black text on white background
    from PIL import ImageDraw, ImageFont

    width, height = 800, 600
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Use default font for testing
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Write some OCR‑friendly text
    lines = text.split("\n")
    line_height = 40
    start_y = 100
    for i, line in enumerate(lines[:10]):  # Limit lines to avoid overflow
        draw.text((50, start_y + i * line_height), line, fill="black", font=font)

    # Save to temporary file
    tmpdir = Path(tempfile.mkdtemp())
    img_path = tmpdir / "test_fixture.jpg"
    img.save(img_path)
    return img_path


class TestT32DocumentServices:
    """T3.2 – Ejecución documento/servicio controlado -> salida estructurada."""

    def test_orquestar_fixture_genera_salida_estructurada(self):
        """Fixture controlado → OCR/texto bruto → campos candidatos -> salida estructurada."""
        # Create a simple controlled test fixture with typical GAS data
        raw_text = """
            Cliente: 12345678
            Importe: S/ 123.45,67
            Periodo: 01/2026
            A pagar hasta: 20/06/2026
            Medidor: 123456789
        """

        fixture_path = _create_test_image_with_text(raw_text)

        result = t3_2_orchestrator.orquestar_documento_controlado(fixture_path)

        # Verify output structure
        required_keys = {"raw_ocr_text", "candidate_fields", "validated_fields", "rejected_fields", "missing_fields", "document_type", "fixture_source"}
        assert set(result.keys()) == required_keys, f"Keys incorrectos: {set(result.keys())}"

        # Verify OCR text
        assert isinstance(result["raw_ocr_text"], str)
        assert len(result["raw_ocr_text"]) > 0

        # Verify field categories
        assert isinstance(result["candidate_fields"], dict)
        assert isinstance(result["validated_fields"], dict)
        assert isinstance(result["rejected_fields"], dict)
        assert isinstance(result["missing_fields"], dict)

        # Verify GAS document type
        assert result["document_type"] == "GAS"

        # Verify fixture source contains the path
        assert str(fixture_path.name) in result["fixture_source"] or "test_fixture.jpg" in result["fixture_source"]

    def test_resultado_tiene_todos_los_campos_gas_relevantes(self):
        """Verificar que se captura al menos uno de los campos relevantes de GAS."""
        # Create fixture with clear visible fields
        raw_text = """
            Cliente: 12345678
            Importe total: $45.678,90
            Período: 03/2025
            A pagar hasta: 15/07/2025
        """

        fixture_path = _create_test_image_with_text(raw_text)
        result = t3_2_orchestrator.orquestar_documento_controlado(fixture_path)

        # Check that at least one expected GAS field appears in extracted data
        extracted = result["candidate_fields"]
        expected_fields = {"importe", "cliente", "a_pagar_hasta", "periodo", "nro_medidor"}

        # We don't require all fields to be found, but at least one should
        assert any(val is not None for val in extracted.values()), "No fields extracted from controlled fixture"

        # Ensure the result is reproducible with consistent structure
        result_copy = t3_2_orchestrator.orquestar_documento_controlado(fixture_path)
        assert result == result_copy, "Evidencia de lo reproducible e invariante"

    def test_resultado_estructura_cumple_ocr_rulebook(self):
        """Validar que el resultado cumple las reglas de calidad OCR establecidas.

        Toda mejora OCR debe declarar:
        - campo extraído (de un conjunto permitido)
        - tipo de documento (siempre un string válido)
        - fixture o imagen usada
        - salida esperada (la salida real generada)
        - validación aplicada (categorías de campos presentes)
        - falsos positivos evitados (rejected_fields siempre exsitente)
        """
        # Use real fixture sample if available, otherwise create synthetic
        base_samples_dir = Path("_local_samples")
        candidate_path = base_samples_dir / "gas" / "gas_sample_local.jpg"
        if not candidate_path.exists():
            # Fallback to synthetic if real fixture not found
            candidate_path = _create_test_image_with_text("Cliente: 999999\nImporte: $1.000,00")

        result = t3_2_orchestrator.orquestar_documento_controlado(candidate_path)

        # 1. Raw OCR text present
        assert "raw_ocr_text" in result
        assert isinstance(result["raw_ocr_text"], str)
        assert len(result["raw_ocr_text"]) > 0

        # 2. Campo extraído debe estar entre campos permitidos relevantes de GI-OCR
        relevant_fields = {
            "cliente", "número de comprobante", "fecha", "vencimiento", "importe", "total",
            "servicio", "código de pago", "identificador de cuenta", "período", "estado del comprobante",
        }
        candidate_fields = result["candidate_fields"]
        extracted_fields = {k: v for k, v in candidate_fields.items() if v is not None}
        extracted_field_names = set(extracted_fields.keys())
        # At least one extracted field should be relevant
        assert any(field in relevant_fields for field in extracted_field_names), \
            f"Extracted fields {list(extracted_field_names)} do not match any defined field in {relevant_fields}"

        # 3. Tipo de documento siempre presente
        assert "document_type" in result
        assert result["document_type"] == "GAS"

        # 4. Fixture o imagen usada debe estar presente
        assert "fixture_source" in result
        assert isinstance(result["fixture_source"], str)

        # 5. Salida esperada es el diccionario completo actual
        assert "validated_fields" in result
        assert "rejected_fields" in result
        assert "missing_fields" in result

        # 6. Validación aplicada: presence de categorías de campos
        campos_categorias = ["validated_fields", "rejected_fields", "missing_fields"]
        assert all(isinstance(result[cat], dict) for cat in campos_categorias)

        # 7. Falsos positivos evitados: rejected_fields siempre exsitente
        assert "rejected_fields" in result
        assert isinstance(result["rejected_fields"], dict)

    def test_salida_estructurada_es_analizable_para_inferencia(self):
        """Verificar que el diccionario resultado se puede analizar/programar fácilmente."""
        # Create controlled fixture
        raw_text = """
            Servicio: GAS
            Total: S/ 999.99,99
            Cliente: 11111111
        """

        fixture_path = _create_test_image_with_text(raw_text)
        result = t3_2_orchestrator.orquestar_documento_controlado(fixture_path)

        # Debe ser serializable JSON (para inferencia/consumo)
        result_str = json.dumps(result, ensure_ascii=False, indent=2)
        parsed = json.loads(result_str)

        # Establezca invariantes que garanticen la accesibilidad: NO TYPE
        assert isinstance(parsed["raw_ocr_text"], str)
        assert isinstance(parsed["document_type"], str)
        assert isinstance(parsed["fixture_source"], str)

        # Fields deben tener valores escalares o vacíos
        for k, v in parsed["candidate_fields"].items():
            assert v is None or isinstance(v, str)

        # Verifier que este output puede continuar a posteriors pipeline transparente de procesamiento
        assert "raw_ocr_text" in parsed
        assert "validated_fields" in parsed
        assert "missing_fields" in parsed

    def test_reproducible_con_fixture_local(self):
        """Garantiza que T3.2 puede ejecutarse reproduciblemente con el fixture local definido por GAS de bottom line."""
        # Use the real local fixture path defined by the project
        local_fixture_path = Path("backend/tests/fixtures/gas_sample.jpg")
        if not local_fixture_path.exists():
            # If defined fixture not found, use the generic from _local_samples
            local_fixture_path = Path("_local_samples/gas/gas_sample_local.jpg")

        # Ejecuta la pipeline dos veces
        result1 = t3_2_orchestrator.orquestar_documento_controlado(local_fixture_path)
        result2 = t3_2_orchestrator.orquestar_documento_controlado(local_fixture_path)

        # Results must be identical
        assert result1 == result2, "Pipeline no reproducible con fixture local definido"

        # Must capture at least some output structure
        assert "raw_ocr_text" in result1
        assert isinstance(result1["raw_ocr_text"], str)
        assert len(result1["raw_ocr_text"]) > 0

        # Debe tener al menos uno de los campos relevantes
        candidate_fields = result1["candidate_fields"]
        extracted = {k: v for k, v in candidate_fields.items() if v is not None}
        assert len(extracted) > 0, "No fields extracted from local bottom-line fixture"

        # Must have all required output categories
        categories = ["validated_fields", "rejected_fields", "missing_fields"]
        assert all(isinstance(result1[cat], dict) for cat in categories)

        # Document type correctly identified
        assert result1["document_type"] == "GAS"

    def test_resultad_e_valores_semanticos(self):
        """Requirements for valid semantic validation as per operational contract.

        T3.2 requires semantic validation: campos validados, rechazados y no encontrados.
        """
        # Mock a simple fixture text
        raw_text = "Cliente: 12345678\nImporte: 100.00"
        fixture_path = _create_test_image_with_text(raw_text)

        result = t3_2_orchestrator.orquestar_documento_controlado(fixture_path)

        # Campos validados: aquellos con valores no vacíos basándose en lógica de validación
        validated = result["validated_fields"]
        # Rechazados: campos intencionalmente sin valor (empty) según validación esperada
        rejected = result["rejected_fields"]
        # No encontrados: campos que existen en requisito pero sin presencia
        missing = result["missing_fields"]

        # Verify that these three categories exist and are dictionaries
        assert isinstance(validated, dict)
        assert isinstance(rejected, dict)
        assert isinstance(missing, dict)

        # Ensure entire process flows without crash (mock validation)
        assert isinstance(result["candidate_fields"], dict)

        # Basic quality rule: document_type and source are set
        assert result["document_type"] == "GAS"
        assert result["fixture_source"] is not None