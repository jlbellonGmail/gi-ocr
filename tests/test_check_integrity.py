# ruff: noqa: E501
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-integrity.ps1"


def powershell():
    for name in ("pwsh", "powershell.exe", "powershell"):
        if path := shutil.which(name):
            return path
    pytest.skip("PowerShell no disponible")


def env():
    result = os.environ.copy()
    result["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    result["GIT_TERMINAL_PROMPT"] = "0"
    return result


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True, env=env()
    ).stdout.strip()


def run_checker(repo):
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-Version", "v2.0.0"],
        cwd=repo,
        text=True,
        capture_output=True,
        env=env(),
        check=False,
    )


def make_repo(tmp_path, roadmap, run_id=None, summary=None):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "checkout", "-b", "develop")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Tests")
    (repo / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    (repo / "STATUS.md").write_text("# Estado\n", encoding="utf-8")
    if run_id:
        run_dir = repo / "runs" / "v2.0.0" / run_id
        run_dir.mkdir(parents=True)
        if summary is not None:
            (run_dir / "SUMMARY.md").write_text(summary, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    return repo


ROADMAP = "# ROADMAP\n\n## Intervenciones\n- [x] T02-reconciliar-status-paralelo — reconciliación\n"


def test_closed_txx_without_run_fails(tmp_path):
    result = run_checker(make_repo(tmp_path, ROADMAP))
    assert result.returncode == 1
    assert "sin run" in result.stdout


def test_txx_without_summary_fails(tmp_path):
    repo = make_repo(tmp_path, ROADMAP, "T02-reconciliar-status-paralelo")
    result = run_checker(repo)
    assert result.returncode == 1
    assert "SUMMARY.md faltante" in result.stdout


def test_orphan_run_fails(tmp_path):
    repo = make_repo(
        tmp_path, "# ROADMAP\n\n## Intervenciones\n", "T02-reconciliar-status-paralelo", "# T02 — orphan\n"
    )
    result = run_checker(repo)
    assert result.returncode == 1
    assert "falta en ROADMAP" in result.stdout


def test_identity_mismatch_fails(tmp_path):
    summary = "# T03 — wrong identity\n\nEstado: DONE\nPR: #70\nMerge: 1234567\n"
    repo = make_repo(tmp_path, ROADMAP, "T02-reconciliar-status-paralelo", summary)
    result = run_checker(repo)
    assert result.returncode == 1
    assert "identidad inconsistente" in result.stdout


def test_coherent_closed_txx_passes(tmp_path):
    repo = make_repo(
        tmp_path, ROADMAP, "T02-reconciliar-status-paralelo", "# T02 — ok\n\nEstado: DONE\nPR: #1\nMerge: PLACEHOLDER\n"
    )
    merge = git(repo, "rev-parse", "HEAD")
    summary = repo / "runs" / "v2.0.0" / "T02-reconciliar-status-paralelo" / "SUMMARY.md"
    summary.write_text(summary.read_text(encoding="utf-8").replace("PLACEHOLDER", merge), encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "summary")
    result = run_checker(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS integridad global" in result.stdout
