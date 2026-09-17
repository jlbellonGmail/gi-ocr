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


def test_policy_is_deny_by_default_and_declares_capabilities():
    policy = json.loads((ROOT / ".agentic/security-policy.json").read_text(encoding="utf-8"))
    assert policy["defaultDecision"] == "deny"
    assert set(
        [
            "READ",
            "MODIFY_LOCAL",
            "EXECUTE",
            "NETWORK_READ",
            "GIT_WRITE",
            "REMOTE_WRITE",
            "MERGE",
            "DESTRUCTIVE",
            "SECRET_ACCESS",
        ]
    ).issubset(policy["capabilities"])
    assert policy["mcp"]["readOnly"] == "NETWORK_READ"
    assert policy["mcp"]["writeOrAction"] == "EXTERNAL_WRITE"


def test_policy_script_validates_and_denies_unknown_capability():
    result = subprocess.run([ps(), "-NoProfile", "-File", str(SCRIPT)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "security-policy: valid" in result.stdout


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


def test_scoped_authorization_accepts_exact_action_and_branch(tmp_path):
    auth = tmp_path / "authorization.md"
    auth.write_text(
        "decision: MERGE\nscope: 16-seguridad-profesional\naction: MERGE\nbranch: feature/v2.0.0-16-seguridad-profesional\nbase: develop\n",
        encoding="utf-8",
    )
    command = f'. "{SCRIPT}"; Assert-ScopedAuthorization -Path "{auth}" -ExpectedScope "16-seguridad-profesional" -ExpectedAction MERGE -ExpectedBranch "feature/v2.0.0-16-seguridad-profesional" -ExpectedBase develop'
    result = subprocess.run([ps(), "-NoProfile", "-Command", command], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
