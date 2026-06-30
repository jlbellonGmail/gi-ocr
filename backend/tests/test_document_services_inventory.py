"""Tests for the document services inventory T2.4."""
import json
from pathlib import Path

import pytest


INVENTORY_PATH = Path(__file__).resolve().parents[1] / "config" / "document_services.json"


def test_inventory_file_exists():
    """The inventory file must exist at the expected path."""
    assert INVENTORY_PATH.exists(), f"Inventory file not found at {INVENTORY_PATH}"


def test_inventory_is_valid_json():
    """The inventory file must contain valid JSON."""
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    assert isinstance(data, list), "Inventory must be a JSON array"


def test_gas_service_exists_in_inventory():
    """GAS service must exist in the inventory."""
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    ids = [s["id"] for s in data]
    assert "GAS" in ids, "GAS service must be present in inventory"


def test_gas_service_is_enabled_for_data_evaluator():
    """GAS service must be enabled for DATA evaluator."""
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    gas_service = next(s for s in data if s["id"] == "GAS")
    assert gas_service.get("data_evaluator_enabled") is True, "GAS must have data_evaluator_enabled=true"


def test_cevt_service_exists_in_inventory():
    """CEVT service must exist in the inventory."""
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    ids = [s["id"] for s in data]
    assert "CEVT" in ids, "CEVT service must be present in inventory"


def test_unknown_service_not_in_inventory():
    """An unknown service must not appear in the inventory as supported."""
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    ids = [s["id"] for s in data]
    assert "UNKNOWN_SERVICE" not in ids, "Unknown service should not be in inventory"


def test_inventory_entry_has_required_fields():
    """Each inventory entry must have all required fields."""
    required_fields = {"id", "title", "document_type", "status", "data_evaluator_enabled", "expected_fields"}
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    for entry in data:
        missing = required_fields - set(entry.keys())
        assert not missing, f"Entry {entry.get('id', 'unknown')} missing fields: {missing}"


def test_inventory_data_evaluator_contract_t23():
    """Regression test: T2.3 DATA evaluator contract still works.

    The inventory must be consumable by the DATA evaluator and
    the services defined must match the services.ini configuration.
    """
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)

    # Load services from services.ini
    from backend.app.services_config import list_services, get_service_fields

    inventory_ids = {s["id"] for s in data}
    config_ids = set(list_services())

    # All inventory services must exist in services.ini
    for service_id in inventory_ids:
        assert service_id in config_ids, f"Service {service_id} in inventory but not in services.ini"

    # Check that expected_fields match actual fields from services.ini
    for service in data:
        service_id = service["id"]
        inventory_fields = set(service.get("expected_fields", []))
        config_fields = set(get_service_fields(service_id))
        assert inventory_fields == config_fields, (
            f"Service {service_id}: inventory fields {inventory_fields} "
            f"don't match config fields {config_fields}"
        )