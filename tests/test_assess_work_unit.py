import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "assess-work-unit.ps1"


def powershell():
    for candidate in ("powershell.exe", "pwsh") if os.name == "nt" else ("pwsh", "powershell"):
        if shutil.which(candidate):
            return candidate
    pytest.skip("PowerShell no esta disponible")


def run_assess(*args):
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def payload(result):
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_sensitive_change_is_full_and_deterministic(tmp_path):
    evidence = tmp_path / "assess.jsonl"
    result = run_assess("-ChangedPath", "scripts/close-feature.ps1", "-EvidencePath", str(evidence))
    data = payload(result)
    assert data["deterministic"] is True
    assert data["risk"] == "HIGH"
    assert data["depth"] == "FULL"
    assert json.loads(evidence.read_text(encoding="utf-8"))["assessment"] == "ASSESS"


def test_simple_documentation_change_is_light(tmp_path):
    result = run_assess("-ChangedPath", "docs/usuario/ejemplo.md", "-NoEvidence")
    data = payload(result)
    assert data["risk"] == "LOW"
    assert data["depth"] == "LIGHT"


def test_implementation_change_is_standard(tmp_path):
    result = run_assess("-ChangedPath", "src/feature.py", "-NoEvidence")
    data = payload(result)
    assert data["risk"] == "MEDIUM"
    assert data["depth"] == "STANDARD"


def test_comma_separated_paths_are_counted_individually():
    result = run_assess("-ChangedPath", "src/a.py,docs/a.md", "-NoEvidence")
    data = payload(result)
    assert data["fileCount"] == 2


def test_missing_evidence_fails_closed():
    result = run_assess("-NoEvidence")
    assert result.returncode != 0
    assert "Falta evidencia" in result.stderr or "no contiene archivos" in result.stderr
