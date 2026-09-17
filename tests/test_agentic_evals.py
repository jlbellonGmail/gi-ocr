"""Pruebas del runner de comportamiento F07; no sustituyen tests deterministas."""
# ruff: noqa: E501

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agentic-evals.ps1"
FIXTURES = ROOT / "evals" / "scenarios.json"


def pwsh():
    for name in ("pwsh", "powershell.exe", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    pytest.skip("PowerShell no esta disponible")


def run_eval(tmp_path, *args):
    profile = args[1] if len(args) > 1 and args[0] == "-Profile" else "normal"
    output = tmp_path / f"{profile}.jsonl"
    command = [
        pwsh(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-ScenarioPath",
        str(FIXTURES),
        "-OutputPath",
        str(output),
        *args,
    ]
    result = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, env={**os.environ, "GIT_CONFIG_GLOBAL": "NUL"}, timeout=30
    )
    return result, output


def test_normal_profile_evaluates_ten_representative_scenarios(tmp_path):
    result, output = run_eval(tmp_path, "-Profile", "normal", "-RunId", "test-1", "-FailOnFailure")
    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 11
    assert records[-1]["scenarioCount"] == 10
    assert records[-1]["passRate"] == 1
    assert all(record["providerAgnostic"] for record in records)
    assert all(record["modelAgnostic"] for record in records)


def test_profiles_are_deterministic_subsets(tmp_path):
    smoke, smoke_file = run_eval(tmp_path, "-Profile", "smoke", "-RunId", "same")
    full, full_file = run_eval(tmp_path, "-Profile", "full", "-RunId", "same")
    assert smoke.returncode == full.returncode == 0
    smoke_records = [json.loads(line) for line in smoke_file.read_text(encoding="utf-8").splitlines()]
    full_records = [json.loads(line) for line in full_file.read_text(encoding="utf-8").splitlines()]
    assert smoke_records[-1]["scenarioCount"] == 3
    assert full_records[-1]["scenarioCount"] == 10
    assert [r["scenario"] for r in smoke_records[:-1]] == ["A-trivial", "C-high-risk", "G-no-progress"]


def test_failure_is_explained_and_can_fail_the_gate(tmp_path):
    altered = tmp_path / "altered.json"
    document = json.loads(FIXTURES.read_text(encoding="utf-8"))
    document["scenarios"][0]["actual"]["depth"] = "FULL"
    altered.write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "failure.jsonl"
    result = subprocess.run(
        [
            pwsh(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-ScenarioPath",
            str(altered),
            "-OutputPath",
            str(output),
            "-Profile",
            "smoke",
            "-FailOnFailure",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1
    first = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
    assert first["pass"] is False and "depth" in first["reason"]


def test_fixture_has_no_provider_or_model_identity():
    document = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for scenario in document["scenarios"]:
        assert "provider" not in scenario and "model" not in scenario
        assert "provider" not in scenario["expected"] and "model" not in scenario["expected"]
        assert "provider" not in scenario["actual"] and "model" not in scenario["actual"]
