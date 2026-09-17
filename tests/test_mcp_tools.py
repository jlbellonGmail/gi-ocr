# ruff: noqa: E501
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / ".agentic/schemas/mcp.schema.json"
SCRIPT = ROOT / "scripts/mcp-tools.ps1"


def ps():
    for name in ("pwsh", "powershell"):
        if shutil.which(name):
            return name
    pytest.skip("PowerShell no disponible")


def run(command, cwd=ROOT):
    return subprocess.run([ps(), "-NoProfile", "-Command", command], cwd=cwd, text=True, capture_output=True)


def test_catalog_schema_and_reference_are_valid():
    catalog = json.loads((ROOT / ".agentic/mcp.json").read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validate(catalog, schema)
    assert (ROOT / ".agentic" / catalog["$schema"]).is_file()
    assert catalog["servers"] == {}


def test_schema_rejects_eager_loading_and_unknown_mode():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    base = {
        "type": "remote",
        "capability": "docs",
        "mode": "read-only",
        "risk": "low",
        "permissions": ["NETWORK_READ"],
        "optional": True,
        "load": "on-demand",
    }
    broken = {
        "$schema": "./schemas/mcp.schema.json",
        "schemaVersion": 1,
        "servers": {"docs": {**base, "load": "always"}},
    }
    with pytest.raises(ValidationError):
        validate(broken, schema)
    broken["servers"]["docs"]["load"] = "on-demand"
    broken["servers"]["docs"]["mode"] = "execute"
    with pytest.raises(ValidationError):
        validate(broken, schema)


def test_empty_catalog_is_safe_and_optional_capability_falls_back(tmp_path):
    catalog = tmp_path / "mcp.json"
    catalog.write_text(json.dumps({"schemaVersion": 1, "servers": {}}), encoding="utf-8")
    command = f'. "{SCRIPT}"; (Get-McpCapabilityDecision -Server docs -Scope "15-mcp-herramientas" -CatalogPath "{catalog}").Decision'
    result = run(command)
    assert result.returncode == 0, result.stderr
    assert "FALLBACK" in result.stdout


def test_write_requires_scoped_authorization_and_secret_is_not_printed(tmp_path):
    catalog = tmp_path / "mcp.json"
    catalog.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "servers": {
                    "writer": {
                        "type": "remote",
                        "capability": "remote-write",
                        "mode": "write",
                        "risk": "high",
                        "permissions": ["EXTERNAL_WRITE", "SECRET_ACCESS"],
                        "requirements": {"secretEnv": "MCP_TOKEN"},
                        "optional": False,
                        "load": "on-demand",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    command = f'. "{SCRIPT}"; (Get-McpCapabilityDecision -Server writer -Scope "15-mcp-herramientas" -Profile LIGHT -Operation write -CatalogPath "{catalog}").Decision'
    denied = run(command)
    assert denied.returncode == 0 and "DENY" in denied.stdout
    assert "MCP_TOKEN" not in denied.stderr


def test_required_missing_secret_blocks_and_invalid_catalog_is_actionable(tmp_path):
    catalog = tmp_path / "mcp.json"
    catalog.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "servers": {
                    "writer": {
                        "type": "remote",
                        "capability": "remote-write",
                        "mode": "write",
                        "risk": "high",
                        "permissions": ["EXTERNAL_WRITE"],
                        "requirements": {"secretEnv": "MCP_TOKEN"},
                        "optional": False,
                        "load": "on-demand",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    command = f'. "{SCRIPT}"; (Get-McpCapabilityDecision -Server writer -Scope "15-mcp-herramientas" -Profile STANDARD -Operation write -AuthorizationPath "{ROOT / "runs/v2.0.0/15-mcp-herramientas/authorization-example.md"}" -CatalogPath "{catalog}").Decision'
    result = run(command)
    assert "BLOCKED" in result.stdout or result.returncode != 0
    bad = tmp_path / "bad.json"
    bad.write_text('{"schemaVersion": 1, "servers": {"bad": {"mode": "read-only"}}}', encoding="utf-8")
    invalid = run(f'. "{SCRIPT}"; Get-McpCatalog -Path "{bad}"')
    assert invalid.returncode != 0 and "falta" in (invalid.stdout + invalid.stderr)
