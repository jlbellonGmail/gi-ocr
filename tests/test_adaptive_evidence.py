"""Escenarios del contrato adaptativo F05.

La suite comprueba semantica de evidencia, no la presencia historica de todos
los nombres de archivo.
"""
# ruff: noqa: E501

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "scripts" / "feature-contract.ps1"
SLUG = "99-demo-feature"


def pwsh():
    for name in ("pwsh", "powershell.exe", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    pytest.skip("PowerShell no esta disponible")


def run_ps(command: str, repo: Path):
    return subprocess.run(
        [pwsh(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "NUL" if os.name == "nt" else "/dev/null"},
    )


def verdict():
    return "```yaml\nstatus: approved\nattempt: 1\nfeedback:\n  - ok\n```\n"


def summary():
    return """# Demo feature
Estado: en validacion
Versión: v2.0.0
Tipo: Feature
SDD: ADAPTIVE
PR: pendiente
Merge: pendiente

## Objetivo
Objetivo.
## Resultado
Resultado.
## Cambios principales
Cambios.
## Validación
Validacion.
## Decisiones
Decisiones.
## Incidencias
Ninguna.
## Detalle
Detalle.
"""


def make_run(tmp_path: Path, depth: str):
    run = tmp_path / "runs" / SLUG
    run.mkdir(parents=True)
    (run / "sdd.json").write_text(json.dumps({"sdd": "ADAPTIVE", "depth": depth}), encoding="utf-8")
    (run / "SUMMARY.md").write_text(summary(), encoding="utf-8")
    (run / "code-review-1.md").write_text(verdict(), encoding="utf-8")
    if depth in {"STANDARD", "FULL"}:
        (run / "spec.md").write_text("# Spec\nIntencion verificable.\n", encoding="utf-8")
        (run / "plan.md").write_text("# Plan\nPlan proporcional.\n", encoding="utf-8")
        for section in ("tecnica", "usuario"):
            directory = tmp_path / "docs" / section
            directory.mkdir(parents=True)
            name = "demo-feature.md"
            (directory / name).write_text("# Demo\n", encoding="utf-8")
            (directory / "index.md").write_text(
                "<!-- FEATURE_LINKS_START -->\n- [Demo feature](demo-feature.md)\n<!-- FEATURE_LINKS_END -->\n",
                encoding="utf-8",
            )
    if depth == "FULL":
        for name in ("tasks.md", "decision.md"):
            (run / name).write_text(f"# {name}\n", encoding="utf-8")
        (run / "audit-1.md").write_text(verdict(), encoding="utf-8")
    return run


def contract(repo: Path):
    return run_ps(f". '{CONTRACT}'; Assert-FeatureContract -Slug '{SLUG}' -Title 'Demo feature'", repo)


def test_light_is_minimal_and_does_not_require_plan_or_audit(tmp_path):
    make_run(tmp_path, "LIGHT")
    result = contract(tmp_path)
    assert result.returncode == 0, result.stderr


def test_summary_is_required_for_adaptive_runs(tmp_path):
    run = make_run(tmp_path, "LIGHT")
    (run / "SUMMARY.md").unlink()
    result = contract(tmp_path)
    assert result.returncode != 0
    assert "SUMMARY" in result.stderr


def test_standard_requires_proportional_spec_plan_qa_and_docs(tmp_path):
    run = make_run(tmp_path, "STANDARD")
    result = contract(tmp_path)
    assert result.returncode != 0
    assert "test-report" in result.stderr
    (run / "test-report-1.md").write_text(verdict(), encoding="utf-8")
    assert contract(tmp_path).returncode == 0


def test_full_requires_audit_tasks_and_decision(tmp_path):
    run = make_run(tmp_path, "FULL")
    (run / "audit-1.md").unlink()
    result = contract(tmp_path)
    assert result.returncode != 0
    assert "audit" in result.stderr.lower()


def test_required_placeholder_is_rejected(tmp_path):
    run = make_run(tmp_path, "FULL")
    (run / "tasks.md").write_text("   \n", encoding="utf-8")
    result = contract(tmp_path)
    assert result.returncode != 0
    assert "tasks.md" in result.stderr


def test_convergence_json_is_consumed_when_present(tmp_path):
    run = make_run(tmp_path, "FULL")
    (run / "test-report-1.md").write_text(verdict(), encoding="utf-8")
    (run / "convergence.json").write_text(
        json.dumps({"convergence": "CONVERGENCE", "verdict": "APPROVED"}), encoding="utf-8"
    )
    assert contract(tmp_path).returncode == 0
