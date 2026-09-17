import copy
import json
from pathlib import Path

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / ".agentic" / "schemas"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_agents_json_is_valid_against_its_schema():
    schema = load_json(SCHEMAS_DIR / "agents.schema.json")
    document = load_json(ROOT / ".agentic" / "agents.json")

    validate(instance=document, schema=schema)


def test_agents_json_referenced_schema_path_exists():
    document = load_json(ROOT / ".agentic" / "agents.json")
    assert document["$schema"] == "./schemas/agents.schema.json"
    resolved = (ROOT / ".agentic" / document["$schema"]).resolve()
    assert resolved.is_file()


def test_agents_schema_rejects_role_without_description():
    schema = load_json(SCHEMAS_DIR / "agents.schema.json")
    document = load_json(ROOT / ".agentic" / "agents.json")
    broken = copy.deepcopy(document)
    del broken["roles"]["planner"]["description"]

    with pytest.raises(ValidationError):
        validate(instance=broken, schema=schema)


def test_agents_schema_rejects_unknown_field_inside_claude_block():
    schema = load_json(SCHEMAS_DIR / "agents.schema.json")
    document = load_json(ROOT / ".agentic" / "agents.json")
    broken = copy.deepcopy(document)
    broken["roles"]["planner"]["claude"]["unexpectedField"] = "nope"

    with pytest.raises(ValidationError):
        validate(instance=broken, schema=schema)


def test_models_json_is_valid_against_its_schema():
    schema = load_json(SCHEMAS_DIR / "models.schema.json")
    document = load_json(ROOT / ".agentic" / "models.json")

    validate(instance=document, schema=schema)


def test_models_json_referenced_schema_path_exists():
    document = load_json(ROOT / ".agentic" / "models.json")
    assert document["$schema"] == "./schemas/models.schema.json"
    resolved = (ROOT / ".agentic" / document["$schema"]).resolve()
    assert resolved.is_file()


def test_models_schema_rejects_document_without_providers():
    schema = load_json(SCHEMAS_DIR / "models.schema.json")
    document = load_json(ROOT / ".agentic" / "models.json")
    broken = copy.deepcopy(document)
    del broken["providers"]

    with pytest.raises(ValidationError):
        validate(instance=broken, schema=schema)


def test_models_schema_rejects_role_fallback_without_variant():
    schema = load_json(SCHEMAS_DIR / "models.schema.json")
    document = load_json(ROOT / ".agentic" / "models.json")
    broken = copy.deepcopy(document)
    del broken["roles"]["reviewer"]["fallback"][0]["variant"]

    with pytest.raises(ValidationError):
        validate(instance=broken, schema=schema)


def test_work_unit_manifest_is_valid_against_its_schema():
    schema = load_json(SCHEMAS_DIR / "work-unit.schema.json")
    manifest = {
        "schemaVersion": 1,
        "mode": "milestone",
        "slug": "mi-milestone",
        "items": ["02-item-a", "03-item-b"],
    }

    validate(instance=manifest, schema=schema)


def test_work_unit_schema_rejects_empty_items():
    schema = load_json(SCHEMAS_DIR / "work-unit.schema.json")
    manifest = {
        "schemaVersion": 1,
        "mode": "milestone",
        "slug": "mi-milestone",
        "items": [],
    }

    with pytest.raises(ValidationError):
        validate(instance=manifest, schema=schema)


def test_work_unit_schema_rejects_non_milestone_mode():
    schema = load_json(SCHEMAS_DIR / "work-unit.schema.json")
    manifest = {
        "schemaVersion": 1,
        "mode": "feature",
        "slug": "mi-milestone",
        "items": ["02-item-a"],
    }

    with pytest.raises(ValidationError):
        validate(instance=manifest, schema=schema)


def test_work_unit_schema_rejects_item_without_number_prefix():
    schema = load_json(SCHEMAS_DIR / "work-unit.schema.json")
    manifest = {
        "schemaVersion": 1,
        "mode": "milestone",
        "slug": "mi-milestone",
        "items": ["item-sin-prefijo"],
    }

    with pytest.raises(ValidationError):
        validate(instance=manifest, schema=schema)
