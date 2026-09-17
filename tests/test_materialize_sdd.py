# ruff: noqa: E501
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSESS = ROOT / "scripts" / "assess-work-unit.ps1"
MATERIALIZE = ROOT / "scripts" / "materialize-sdd.ps1"


def powershell():
    for candidate in ("powershell.exe", "pwsh") if os.name == "nt" else ("pwsh", "powershell"):
        if shutil.which(candidate):
            return candidate
    pytest.skip("PowerShell no esta disponible")


def run(script, *args):
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assessment(tmp_path, path):
    evidence = tmp_path / "assess.jsonl"
    result = run(ASSESS, "-ChangedPath", path, "-EvidencePath", str(evidence))
    assert result.returncode == 0, result.stderr
    return evidence


@pytest.mark.parametrize(
    ("changed", "depth", "expected_steps", "expected_gates"),
    [
        ("docs/usuario/example.md", "LIGHT", ["objective", "mini-spec", "build", "tests", "review"], []),
        (
            "src/feature.py",
            "STANDARD",
            ["objective", "light-plan", "spec", "plan/tasks-proportional", "build", "tests", "review"],
            [],
        ),
        (
            "scripts/close-feature.ps1",
            "FULL",
            ["objective", "planning", "spec", "plan", "tasks", "validations", "build", "tests", "review", "gates"],
            ["required-validations", "contract-proportional"],
        ),
    ],
)
def test_materializes_the_depth_produced_by_assess(tmp_path, changed, depth, expected_steps, expected_gates):
    evidence = assessment(tmp_path, changed)
    output = tmp_path / "sdd.json"
    result = run(
        MATERIALIZE, "-AssessmentPath", str(evidence), "-Objective", "Implementar la unidad", "-OutputPath", str(output)
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["depth"] == depth
    assert data["steps"] == expected_steps
    assert data["gates"] == expected_gates
    assert json.loads(output.read_text(encoding="utf-8"))["sourceAssessment"] == str(evidence)


def test_rejects_non_assess_or_reclassifies_nothing(tmp_path):
    evidence = tmp_path / "bad.jsonl"
    evidence.write_text(
        json.dumps({"assessment": "OTHER", "depth": "FULL", "deterministic": True}) + "\n", encoding="utf-8"
    )
    result = run(MATERIALIZE, "-AssessmentPath", str(evidence), "-Objective", "x")
    assert result.returncode != 0
    assert "salida determinista de ASSESS" in result.stderr


def test_consumes_latest_jsonl_observation(tmp_path):
    evidence = assessment(tmp_path, "docs/usuario/example.md")
    with evidence.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "assessment": "ASSESS",
                    "deterministic": True,
                    "depth": "STANDARD",
                    "risk": "MEDIUM",
                    "changedFiles": ["src/a.py"],
                }
            )
            + "\n"
        )
    result = run(MATERIALIZE, "-AssessmentPath", str(evidence), "-Objective", "x")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["depth"] == "STANDARD"
