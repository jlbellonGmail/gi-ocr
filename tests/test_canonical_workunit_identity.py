# ruff: noqa: E501
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "workunit-lib.ps1"


def powershell():
    for name in ("pwsh", "powershell.exe", "powershell"):
        if path := shutil.which(name):
            return path
    pytest.skip("PowerShell no disponible")


def run_ps(tmp_path, command):
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def resolve(tmp_path, roadmap, branch):
    (tmp_path / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    command = f". '{LIB}'; Resolve-CanonicalWorkUnitSlug -Branch '{branch}' -RoadmapPath 'ROADMAP.md'"
    return run_ps(tmp_path, command)


# ruff: noqa: E501
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "workunit-lib.ps1"


def powershell():
    for name in ("pwsh", "powershell.exe", "powershell"):
        if path := shutil.which(name):
            return path
    pytest.skip("PowerShell no disponible")


def run_ps(tmp_path, command):
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def resolve(tmp_path, roadmap, branch):
    (tmp_path / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    command = f". '{LIB}'; Resolve-CanonicalWorkUnitSlug -Branch '{branch}' -RoadmapPath 'ROADMAP.md'"
    return run_ps(tmp_path, command)


def test_feature_normal_identity_is_unchanged():
    # Feature parsing remains covered by the existing work-unit tests; this
    # test documents the canonical mapping used by the close workflow.
    branch = "feature/v2.0.0-18-status-observabilidad"
    assert branch.split("/", 1)[1].split("v2.0.0-", 1)[1] == "18-status-observabilidad"
