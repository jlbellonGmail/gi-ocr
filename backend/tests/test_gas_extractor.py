"""Tests for the GAS field extractor."""

from __future__ import annotations

import asyncio

from backend.app.extraction_engine import extract_service_fields
from backend.app.gas_extractor import extract_gas_fields


def test_extract_importe():
    """Should extract amount from various formats."""
    test_cases = [
        ("Importe: $123.45", "123.45"),
        ("Total: S/ 1.234,56", "1.234,56"),
        ("Saldo: 999.99", "999.99"),
        ("A pagar: $50", "50"),
        ("TOTAL: 1,000.00", "1,000.00"),
    ]

    for text, expected in test_cases:
        result = extract_gas_fields(text)
        assert result["fields"]["importe"] == expected, f"Failed for: {text}"


def test_extract_cliente():
    """Should extract client number."""
    test_cases = [
        ("Cliente: 12345678", "12345678"),
        ("Nro Cliente 87654321", "87654321"),
        ("Numero Cliente: 1122334455", "1122334455"),
        ("Cuenta 99999999", "99999999"),
    ]

    for text, expected in test_cases:
        result = extract_gas_fields(text)
        assert result["fields"]["cliente"] == expected, f"Failed for: {text}"


def test_extract_a_pagar_hasta():
    """Should extract due date."""
    test_cases = [
        ("Pagar hasta: 15/06/2026", "15/06/2026"),
        ("Vencimiento 30-05-26", "30-05-26"),
        ("Fecha de vencimiento: 01/12/2025", "01/12/2025"),
        ("Vence: 31/01/2026", "31/01/2026"),
    ]

    for text, expected in test_cases:
        result = extract_gas_fields(text)
        assert result["fields"]["a_pagar_hasta"] == expected, f"Failed for: {text}"


def test_extract_periodo():
    """Should extract period."""
    test_cases = [
        ("Periodo: 05/2026", "05/2026"),
        ("Período 06-2026", "06-2026"),
        ("Periodo: 12/25", "12/25"),
    ]

    for text, expected in test_cases:
        result = extract_gas_fields(text)
        assert result["fields"]["periodo"] == expected, f"Failed for: {text}"


def test_extract_nro_medidor():
    """Should extract meter number."""
    test_cases = [
        ("Nro Medidor: 123456789012", "123456789012"),
        ("Medidor 9876543210", "9876543210"),
        ("Numero Medidor: 1111222233334444", "1111222233334444"),
    ]

    for text, expected in test_cases:
        result = extract_gas_fields(text)
        assert result["fields"]["nro_medidor"] == expected, f"Failed for: {text}"


def test_no_fields_found():
    """Should return empty fields when no matches found."""
    text = "This is a random text without any gas receipt data."
    result = extract_gas_fields(text)

    # All fields should be None
    for field_value in result["fields"].values():
        assert field_value is None

    # No detected fields
    assert result["detected_fields"] == []

    # All fields should be missing
    assert set(result["missing_fields"]) == {
        "importe",
        "a_pagar_hasta",
        "cliente",
        "periodo",
        "nro_medidor",
    }


def test_empty_text():
    """Should handle empty text gracefully."""
    result = extract_gas_fields("")

    # All fields should be None
    for field_value in result["fields"].values():
        assert field_value is None

    # Empty normalized text
    assert result["normalized_text"] == ""

    # No detected fields
    assert result["detected_fields"] == []

    # All fields missing
    assert set(result["missing_fields"]) == {
        "importe",
        "a_pagar_hasta",
        "cliente",
        "periodo",
        "nro_medidor",
    }


def test_semantic_validation_rejects_comprobant():
    """Should reject COMPROBANT for a_pagar_hasta field."""
    text = "a pagar hasta COMPROBANT"
    result = asyncio.run(extract_service_fields("GAS", text))
    # Should reject COMPROBANT completely
    assert result["fields"]["a_pagar_hasta"] is None


def test_semantic_validation_accepts_date_with_slash():
    """Should accept valid date with / separator."""
    text = "Pagar hasta: 20/06/2026"
    result = asyncio.run(extract_service_fields("GAS", text))
    assert result["fields"]["a_pagar_hasta"] == "20/06/2026"


def test_semantic_validation_accepts_date_with_dash():
    """Should accept valid date with - separator."""
    text = "Vencimiento 20-06-2026"
    result = asyncio.run(extract_service_fields("GAS", text))
    assert result["fields"]["a_pagar_hasta"] == "20-06-2026"


def test_semantic_validation_accepts_date_with_dot():
    """Should accept valid date with . separator."""
    text = "a pagar hasta 20.06.2026"
    result = asyncio.run(extract_service_fields("GAS", text))
    assert result["fields"]["a_pagar_hasta"] == "20.06.2026"


def test_semantic_validation_accepts_date_with_asterisk():
    """Should accept valid date with * separator."""
    text = "pagar hasta 20*06*2026"
    result = asyncio.run(extract_service_fields("GAS", text))
    assert result["fields"]["a_pagar_hasta"] == "20*06*2026"


def test_semantic_validation_extracts_date_from_comprobant_text():
    """Should extract date from 'COMPROBANT DD/MM/YYYY' text."""
    text = "COMPROBANT 20/06/2026"
    result = asyncio.run(extract_service_fields("GAS", text))
    # Should extract the date, not COMPROBANT
    assert result["fields"]["a_pagar_hasta"] == "20/06/2026"


def test_semantic_validation_missing_date_returns_none():
    """Should return None when no valid date is found."""
    text = "a pagar hasta COMPROBANT"
    result = asyncio.run(extract_service_fields("GAS", text))
    # Deterministic: field should be None when no valid date
    assert result["fields"]["a_pagar_hasta"] is None
    # Should be in missing_fields list
    assert "a_pagar_hasta" in result["missing_fields"]
