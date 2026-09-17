import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-adoption-conflicts.ps1"


def powershell() -> str:
    candidates = ["powershell.exe", "pwsh"] if os.name == "nt" else ["pwsh", "powershell"]
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    pytest.skip("PowerShell no esta disponible")


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    return env


def run_check(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            *args,
        ],
        cwd=ROOT,
        env=command_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def snapshot(target: Path) -> set[str]:
    """Estado del directorio destino: rutas relativas de todo lo que contiene."""
    return {str(path.relative_to(target)) for path in target.rglob("*")}


def make_collision_set(target: Path) -> None:
    """Crea al menos una ruta conocida de cada categoria del checklist."""
    (target / ".agentic").mkdir(parents=True)
    (target / ".agentic" / "placeholder.txt").write_text("dummy", encoding="utf-8")

    scripts_dir = target / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "ready-for-pr.ps1").write_text("dummy", encoding="utf-8")

    (target / "runs").mkdir(parents=True)

    docs_tecnica = target / "docs" / "tecnica"
    docs_tecnica.mkdir(parents=True)
    (docs_tecnica / "index.md").write_text("dummy", encoding="utf-8")

    docs_usuario = target / "docs" / "usuario"
    docs_usuario.mkdir(parents=True)
    (docs_usuario / "index.md").write_text("dummy", encoding="utf-8")

    (target / "AGENTS.md").write_text("dummy", encoding="utf-8")

    workflows_dir = target / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("dummy", encoding="utf-8")
    (workflows_dir / "docs.yml").write_text("dummy", encoding="utf-8")
    (workflows_dir / "post-hitl-merge-gate.yml").write_text("dummy", encoding="utf-8")
    (workflows_dir / "post-merge-close-feature.yml").write_text("dummy", encoding="utf-8")


def test_empty_target_reports_no_collisions(tmp_path: Path):
    target = tmp_path / "destino-vacio"
    target.mkdir()

    before = snapshot(target)
    result = run_check("-TargetPath", str(target))
    after = snapshot(target)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "colision" not in result.stdout.lower() or "no se detectaron colisiones" in result.stdout.lower()
    assert before == after
    assert after == set()


def test_target_with_known_paths_reports_collisions(tmp_path: Path):
    target = tmp_path / "destino-con-colisiones"
    target.mkdir()
    make_collision_set(target)

    before = snapshot(target)
    result = run_check("-TargetPath", str(target))
    after = snapshot(target)

    assert result.returncode == 1, result.stdout + result.stderr

    output_lower = result.stdout.lower()
    assert ".agentic" in output_lower
    assert "ready-for-pr.ps1" in output_lower
    assert "runs" in output_lower
    assert "docs/tecnica" in output_lower.replace("\\", "/")
    assert "docs/usuario" in output_lower.replace("\\", "/")
    assert "agents.md" in output_lower
    assert "ci.yml" in output_lower
    assert "docs.yml" in output_lower
    assert "post-hitl-merge-gate.yml" in output_lower
    assert "post-merge-close-feature.yml" in output_lower

    assert before == after


def test_nonexistent_target_fails_explicitly(tmp_path: Path):
    missing = tmp_path / "no-existe" / "tampoco-esto"

    result = run_check("-TargetPath", str(missing))

    assert result.returncode != 0
    assert not missing.exists()
    combined = (result.stdout + result.stderr).lower()
    assert "no existe" in combined


def test_target_that_is_a_file_fails_explicitly(tmp_path: Path):
    file_target = tmp_path / "esto-es-un-archivo.txt"
    file_target.write_text("dummy", encoding="utf-8")

    before = file_target.read_text(encoding="utf-8")
    result = run_check("-TargetPath", str(file_target))
    after = file_target.read_text(encoding="utf-8")

    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "no es un directorio" in combined
    assert before == after
