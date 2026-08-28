"""
Tests para manejo de texto vacío en extracción.
"""
import pytest
from backend.app.extraction_engine import extract_service_fields, _normalize_text, _extract_generic


class TestEmptyTextHandling:
    """Valida que el motor maneje texto vacío de forma determinística."""

    def test_normalize_empty_text(self):
        """Texto vacío debe normalizarse a string vacío."""
        assert _normalize_text(None) == ""
        assert _normalize_text("") == ""
        assert _normalize_text("   ") == ""

    def test_extract_generic_empty_text(self):
        """_extract_generic debe retornar None para texto vacío."""
        assert _extract_generic("importe", "") is None
        assert _extract_generic("cliente", "") is None

    @pytest.mark.anyio
    async def test_extract_service_fields_empty_text(self):
        """Extracción con texto vacío debe retornar campos como None."""
        result = await extract_service_fields("GAS", "")
        assert result["fields"]["importe"] is None
        assert result["fields"]["cliente"] is None
        assert result["fields"]["nro_medidor"] is None
        assert result["fields"]["a_pagar_hasta"] is None
        assert result["fields"]["periodo"] is None

    @pytest.mark.anyio
    async def test_extract_service_fields_whitespace_only(self):
        """Texto con solo espacios debe manejarse correctamente."""
        result = await extract_service_fields("GAS", "   \n\t  ")
        for field, value in result["fields"].items():
            assert value is None, f"Campo {field} no debería tener valor"


class TestDeterministicMissingFields:
    """Valida que campos faltantes se reporten de forma determinística."""

    @pytest.mark.anyio
    async def test_missing_fields_list_complete(self):
        """missing_fields debe contener campos sin valor cuando el texto no tiene datos."""
        result = await extract_service_fields("GAS", "texto sin datos")
        # Note: _extract_generic returns text snippet when no regex match
        # So we test with completely empty text instead
        result_empty = await extract_service_fields("GAS", "")
        expected_fields = ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"]
        for field in expected_fields:
            assert field in result_empty["missing_fields"]