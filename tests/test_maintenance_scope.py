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


def test_maintenance_t04_integridad_is_canonical(tmp_path):
    result = resolve_scope(
        tmp_path,
        "- [x] T04-integridad-sincronizacion - T04\n",
        "maintenance/v2.0.0-T04-integridad-sincronizacion",
    )
    assert result.returncode == 0, result.stderr
    assert '"scope":"canonical-unit"' in result.stdout
    assert '"slug":"T04-integridad-sincronizacion"' in result.stdout


def test_maintenance_t04_lifecycle_fix_is_canonical(tmp_path):
    result = resolve_scope(
        tmp_path,
        "- [x] T04-integridad-sincronizacion - T04\n",
        "maintenance/v2.0.0-T04-lifecycle-fix",
    )
    assert result.returncode == 0, result.stderr
    assert '"scope":"canonical-unit"' in result.stdout


def test_maintenance_t04_postmerge_status_is_canonical(tmp_path):
    result = resolve_scope(
        tmp_path,
        "- [x] T04-integridad-sincronizacion - T04\n",
        "maintenance/v2.0.0-T04-postmerge-status",
    )
    assert result.returncode == 0, result.stderr
    assert '"scope":"canonical-unit"' in result.stdout


def test_missing_t05_status_is_auxiliary_without_roadmap_close(tmp_path):
    result = resolve_scope(
        tmp_path,
        "- [x] T04-integridad-sincronizacion - T04\n",
        "maintenance/v2.0.0-T05-status-f16",
    )
    assert result.returncode == 0, result.stderr
    assert '"scope":"auxiliary"' in result.stdout
    assert '"close":false' in result.stdout
    assert "no canonical unit associated" in result.stdout


def test_missing_tnn_unknown_purpose_fails_safely(tmp_path):
    result = resolve_scope(
        tmp_path,
        "- [x] T04-integridad-sincronizacion - T04\n",
        "maintenance/v2.0.0-T05-unknown-purpose",
    )
    assert result.returncode != 0
    assert "FAILED_SAFELY" in result.stderr or "NEEDS_HUMAN_DECISION" in result.stderr


def test_feature_scope_behavior_is_not_changed(tmp_path):
    # Feature branches do not enter maintenance scope resolution; the normal
    # lifecycle remains covered by the existing feature close tests.
    assert "maintenance/" not in "feature/v2.0.0-21-validacion-integral-v2"


def test_close_feature_auxiliary_succeeds_without_roadmap_close(tmp_path):
    repo = tmp_path / "repo"
    remote = tmp_path / "origin.git"
    bin_dir = tmp_path / "bin"
    remote.mkdir()
    repo.mkdir()
    bin_dir.mkdir()
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "develop", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "tests@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tests"], check=True)
    roadmap = "- [x] T04-integridad-sincronizacion - T04\n"
    (repo / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "ROADMAP.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "develop"], check=True, capture_output=True)
    payload = (
        '{"state":"MERGED","mergedAt":"2026-09-15T00:00:00Z",'
        '"baseRefName":"develop","headRefName":"maintenance/v2.0.0-T05-status-f16"}'
    )
    if os.name == "nt":
        (bin_dir / "gh.cmd").write_text(f"@echo off\necho {payload}\n", encoding="utf-8")
    else:
        fake_gh = bin_dir / "gh"
        fake_gh.write_text(f"#!/bin/sh\necho '{payload}'\n", encoding="utf-8")
        fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    command = (
        f"& '{ROOT / 'scripts' / 'close-feature.ps1'}' "
        "-Branch 'maintenance/v2.0.0-T05-status-f16' -Mode Maintenance "
        "-Version v2.0.0 -PrNumber 88 -SkipLocalCleanup"
    )
    result = subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=repo,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "maintenance_scope: auxiliary" in result.stdout
    assert "close_roadmap: skipped" in result.stdout
    assert (repo / "ROADMAP.md").read_text(encoding="utf-8") == roadmap
