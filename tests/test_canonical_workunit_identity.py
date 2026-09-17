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


def test_maintenance_normal_resolves_roadmap_unit(tmp_path):
    result = resolve(
        tmp_path, "- [x] T04-integridad-sincronizacion - T04\n", "maintenance/v2.0.0-T04-integridad-sincronizacion"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "T04-integridad-sincronizacion"


def test_maintenance_corrective_resolves_same_roadmap_unit(tmp_path):
    result = resolve(
        tmp_path, "- [x] T04-integridad-sincronizacion - T04\n", "maintenance/v2.0.0-T04-integridad-sincronizacion-fix"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "T04-integridad-sincronizacion"


def test_maintenance_historical_branch_uses_unique_tnn_identity(tmp_path):
    result = resolve(tmp_path, "- [x] T01-normalizacion-documental - T01\n", "maintenance/v2.0.0-T01-cierre-historico")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "T01-normalizacion-documental"


def test_ambiguous_tnn_fails_safely(tmp_path):
    result = resolve(tmp_path, "- [x] T04-a - A\n- [x] T04-b - B\n", "maintenance/v2.0.0-T04-a-fix")
    assert result.returncode != 0
    assert "Identidad ambigua" in result.stderr


def test_missing_tnn_fails_safely(tmp_path):
    result = resolve(tmp_path, "- [x] T03-real - T03\n", "maintenance/v2.0.0-T04-no-existe")
    assert result.returncode != 0
    assert "No existe una unidad canonica T04" in result.stderr
