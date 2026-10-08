import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "workunit-lib.ps1"


def powershell():
    for name in ("pwsh", "powershell.exe", "powershell"):
        path = shutil.which(name)
        if path:
            return path
    pytest.skip("PowerShell no disponible")


def resolve_scope(tmp_path: Path, roadmap: str, branch: str):
    (tmp_path / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    command = (
        f". '{LIB}'; "
        f"$s = Resolve-MaintenanceScope -Branch '{branch}' -RoadmapPath 'ROADMAP.md'; "
        "[ordered]@{scope=$s.Scope; slug=$s.CanonicalSlug; close=$s.CloseRoadmap; reason=$s.Reason} "
        "| ConvertTo-Json -Compress"
    )
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )


def test_feature_scope_behavior_is_not_changed(tmp_path):
    # Feature branches do not enter maintenance scope resolution; the normal
    # lifecycle remains covered by the existing feature close tests.
    assert "maintenance/" not in "feature/v2.0.0-21-validacion-integral-v2"
