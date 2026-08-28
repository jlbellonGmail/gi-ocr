import json

import pytest
from backend.app.document_services import (
    DisabledDataEvaluatorServiceError,
    UnsupportedDocumentServiceError,
    get_document_service,
    is_data_evaluator_enabled,
    load_document_services,
    normalize_service_id,
    validate_data_evaluator_service,
)


def test_normalize_service_id():
    assert normalize_service_id("GAS") == "GAS"
    assert normalize_service_id(" gas ") == "GAS"
    assert normalize_service_id("CEVT") == "CEVT"

    with pytest.raises(UnsupportedDocumentServiceError):
        normalize_service_id("    ")

    with pytest.raises(UnsupportedDocumentServiceError):
        normalize_service_id("")


def test_load_document_services():
    services = load_document_services()
    assert isinstance(services, list)

    gas_exists = any(s.get("id") == "GAS" for s in services)
    assert gas_exists, "GAS service should exist in the inventory"


def test_validate_data_evaluator_service_accepts_enabled_gas():
    service = validate_data_evaluator_service("GAS")
    assert service["id"] == "GAS"
    assert service["data_evaluator_enabled"] is True


def test_validate_data_evaluator_service_accepts_enabled_cevt():
    service = validate_data_evaluator_service("CEVT")
    assert service["id"] == "CEVT"
    assert service["data_evaluator_enabled"] is True


def test_get_document_service_rejects_unknown():
    with pytest.raises(UnsupportedDocumentServiceError, match="UNKNOWN_SERVICE"):
        get_document_service("UNKNOWN_SERVICE")


def test_is_data_evaluator_enabled_for_gas():
    assert is_data_evaluator_enabled("GAS") is True
    assert is_data_evaluator_enabled("gas") is True


def test_validate_data_evaluator_service_rejects_disabled_service(tmp_path):
    inventory_path = tmp_path / "document_services.json"
    inventory_data = [{"id": "GAS", "name": "Gas", "data_evaluator_enabled": False, "expected_fields": []}]
    inventory_path.write_text(json.dumps(inventory_data), encoding="utf-8")

    with pytest.raises(DisabledDataEvaluatorServiceError) as exc_info:
        validate_data_evaluator_service("GAS", path=str(inventory_path))

    assert "disabled" in str(exc_info.value)
