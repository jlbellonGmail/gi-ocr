"""Tests for service-specific data validation."""

from backend.app.service_data_validation import (
    _is_amount_field,
    _is_date_field,
    _validate_amount,
    _validate_date,
    validate_and_filter_fields,
    validate_service_data,
)


def test_validate_amount_valid_formats():
    """Valid amount formats should pass."""
    valid, err = _validate_amount("123.456,78")
    assert valid is True
    assert err is None

    valid, err = _validate_amount("1234.56")
    assert valid is True
    assert err is None


def test_validate_amount_invalid_formats():
    """Invalid amount formats should fail."""
    valid, err = _validate_amount("ABC")
    assert valid is False
    assert "Invalid" in err


def test_validate_date_valid_formats():
    """Valid date formats should pass."""
    valid, err = _validate_date("20/06/2026")
    assert valid is True
    assert err is None

    valid, err = _validate_date("20-06-2026")
    assert valid is True
    assert err is None


def test_validate_date_invalid_formats():
    """Invalid date formats should fail."""
    valid, err = _validate_date("COMPROBANT")
    assert valid is False
    assert "Invalid" in err


def test_is_amount_field_detection():
    """Should correctly identify amount fields."""
    assert _is_amount_field("importe") is True
    assert _is_amount_field("total") is True
    assert _is_amount_field("saldo") is True
    assert _is_amount_field("cliente") is False


def test_is_date_field_detection():
    """Should correctly identify date fields."""
    assert _is_date_field("vencimiento") is True
    assert _is_date_field("fecha") is True
    assert _is_date_field("periodo") is True
    assert _is_date_field("cliente") is False


def test_validate_service_data_gas_valid():
    """GAS service with valid fields should pass."""
    fields = {
        "importe": "123.456,78",
        "cliente": "04598765",
        "nro_medidor": "12345678",
        "a_pagar_hasta": "20/06/2026",
        "periodo": "01/2026",
    }
    result = validate_service_data("GAS", fields, list(fields.keys()))

    assert result["is_valid"] is True
    assert len(result["errors"]) == 0
    assert len(result["missing_fields"]) == 0


def test_validate_service_data_gas_missing_fields():
    """GAS service with missing required fields should fail."""
    fields = {
        "importe": "123.456,78",
        "cliente": "04598765",
        # Missing nro_medidor, a_pagar_hasta, periodo
    }
    result = validate_service_data("GAS", fields, ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"])

    assert result["is_valid"] is False
    assert "nro_medidor" in result["missing_fields"]


def test_validate_service_data_gas_invalid_amount():
    """GAS service with invalid amount should be rejected."""
    fields = {
        "importe": "invalid",
        "cliente": "04598765",
        "nro_medidor": "12345678",
        "a_pagar_hasta": "20/06/2026",
        "periodo": "01/2026",
    }
    result = validate_service_data("GAS", fields, list(fields.keys()))

    assert result["is_valid"] is False
    assert "importe" in result["rejected_fields"]


def test_validate_service_data_unknown_service():
    """Unknown service should still work but may not have specific rules."""
    fields = {"field1": "value1"}
    result = validate_service_data("UNKNOWN_SERVICE", fields, ["field1"])

    # Should pass because no specific rules defined
    assert result["is_valid"] is True


def test_validate_and_filter_fields():
    """Should return both validation result and filtered fields."""
    fields = {
        "importe": "123.456,78",
        "cliente": "04598765",
        "nro_medidor": "12345678",
        "a_pagar_hasta": "20/06/2026",
        "periodo": "01/2026",
    }
    result = validate_and_filter_fields("GAS", fields, list(fields.keys()))

    assert "validation" in result
    assert "fields_for_data" in result
    assert result["validation"]["is_valid"] is True
    assert result["fields_for_data"]["importe"] == "123.456,78"
