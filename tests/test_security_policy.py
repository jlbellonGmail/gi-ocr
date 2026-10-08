# ruff: noqa: E501
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "security-policy.ps1"


def ps():
    for name in ("pwsh", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    pytest.skip("PowerShell no disponible")


def run(code):
    return subprocess.run(
        [ps(), "-NoProfile", "-File", str(SCRIPT), "-Command", code], cwd=ROOT, text=True, capture_output=True
    )


def test_scoped_authorization_rejects_other_unit_and_secret(tmp_path):
    auth = tmp_path / "authorization.md"
    auth.write_text(
        "decision: MERGE\nscope: other-unit\naction: MERGE\nbranch: feature/other\nbase: develop\nsecret: nope\n",
        encoding="utf-8",
    )
    command = f'. "{SCRIPT}"; Assert-ScopedAuthorization -Path "{auth}" -ExpectedScope "16-seguridad-profesional" -ExpectedAction MERGE -ExpectedBranch "feature/v2.0.0-16-seguridad-profesional" -ExpectedBase develop'
    result = subprocess.run([ps(), "-NoProfile", "-Command", command], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert "scope" in (result.stderr + result.stdout).lower()
