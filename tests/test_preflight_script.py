import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "preflight.ps1"
SLUG = "99-demo"
BRANCH = f"feature/{SLUG}"

pytestmark = pytest.mark.skipif(
    os.name != "nt" or shutil.which("powershell.exe") is None,
    reason="Requiere Windows con PowerShell 5.1",
)


def powershell() -> str:
    path = shutil.which("powershell.exe")
    if not path:
        pytest.skip("PowerShell no esta disponible")
    return path


def base_env(extra_path: str | None = None, program_files: str | None = None) -> dict[str, str]:
    # os.environ.copy() devuelve un dict plano (case-sensitive), a
    # diferencia de os.environ (case-insensitive en Windows). Si dejamos
    # conviviendo 'PROGRAMFILES' (heredado de os.environ) y 'ProgramFiles'
    # (agregado aca), Windows recibe DOS entradas de env distintas para
    # variantes de la misma variable, y el hijo puede terminar leyendo la
    # original en vez de la sobreescrita. Por eso se borran explicitamente
    # todas las variantes de casing antes de fijar la nueva.
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    if extra_path is not None:
        for key in [k for k in env if k.upper() == "PATH"]:
            del env[key]
        env["PATH"] = extra_path
    if program_files is not None:
        for key in [k for k in env if k.upper() == "PROGRAMFILES"]:
            del env[key]
        env["ProgramFiles"] = program_files
    return env


def run(command, cwd, env=None, check=False):
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env if env is not None else base_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"Command failed: {command}\n{result.stdout}\n{result.stderr}")
    return result


def git(repo: Path, *args: str, check: bool = True):
    return run(["git", *args], repo, check=check)


def run_preflight(cwd: Path, args: list[str] | None = None, env: dict[str, str] | None = None):
    command = [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PREFLIGHT)]
    if args:
        command.extend(args)
    return run(command, cwd, env=env)


def write_roadmap(repo: Path, line: str) -> None:
    (repo / "ROADMAP.md").write_text(line, encoding="utf-8")


def make_repo(tmp_path: Path, roadmap_line: str = f"- [ ] {SLUG} - Demo\n"):
    origin = tmp_path / "origin.git"
    main = tmp_path / "main"
    run(["git", "init", "-q", "-b", "develop", str(main)], tmp_path, check=True)
    git(main, "config", "user.email", "tests@example.invalid")
    git(main, "config", "user.name", "Tests")
    write_roadmap(main, roadmap_line)
    git(main, "add", "ROADMAP.md")
    git(main, "commit", "-q", "-m", "init")
    run(["git", "init", "-q", "--bare", str(origin)], tmp_path, check=True)
    git(main, "remote", "add", "origin", str(origin))
    git(main, "push", "-q", "-u", "origin", "develop")
    return origin, main


def make_worktree(main: Path, tmp_path: Path, name: str = "wt-demo", push: bool = False) -> Path:
    worktree = tmp_path / name
    git(main, "worktree", "add", "-q", str(worktree), "-b", BRANCH)
    if push:
        git(main, "push", "-q", "-u", "origin", BRANCH)
    return worktree


def repo_snapshot(main: Path) -> tuple[str, str]:
    head = git(main, "rev-parse", "HEAD").stdout.strip()
    worktrees = git(main, "worktree", "list", "--porcelain").stdout
    return head, worktrees


# ---------------------------------------------------------------------------
# Modo generico (sin -Slug): criterios 1, 2, 3, 5.
# ---------------------------------------------------------------------------


def test_generic_mode_ok_on_healthy_repo(tmp_path: Path):
    _, main = make_repo(tmp_path)

    result = run_preflight(main)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PREFLIGHT: OK" in result.stdout


def test_generic_mode_reports_missing_git_and_gh_simultaneously(tmp_path: Path):
    _, main = make_repo(tmp_path)

    # 'git' y 'gh' deliberadamente ausentes del PATH restringido; ademas
    # ProgramFiles apunta a un directorio inexistente para que el fallback
    # hardcodeado de 'gh' tampoco lo encuentre. PowerShell debe seguir
    # disponible para poder ejecutar el propio script.
    #
    # Nota de implementacion: la restriccion de PATH/ProgramFiles se aplica
    # DESDE DENTRO del proceso de PowerShell que corre preflight.ps1 (via
    # $env:X = ...), no vía el diccionario 'env=' de subprocess.run: en
    # este entorno de pruebas, pasar un dict de entorno reemplazado a
    # subprocess.run no siempre logra pisar 'ProgramFiles' de forma
    # confiable para el proceso hijo (particularidad de Windows/.NET al
    # construir el bloque de entorno), mientras que reasignar $env:X ya
    # con el proceso corriendo si es confiable.
    powershell_dir = str(Path(powershell()).parent)
    restricted_path = os.pathsep.join([powershell_dir, r"C:\Windows\System32"])
    fake_program_files = str(tmp_path / "no-program-files")
    prelude = (
        f"$env:PATH = '{restricted_path}'; "
        f"$env:ProgramFiles = '{fake_program_files}'; "
        f"& '{PREFLIGHT}'; "
        "exit $LASTEXITCODE"
    )

    result = run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", prelude],
        main,
        env=base_env(),
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "PREFLIGHT: BLOCKING" in result.stdout
    assert "[BLOCKING] git no esta disponible" in result.stdout
    assert "Instala Git" in result.stdout
    assert "[BLOCKING] GitHub CLI (gh) no esta instalado" in result.stdout
    assert "Accion:" in result.stdout


def test_generic_mode_reports_old_python_and_missing_venv_simultaneously(tmp_path: Path):
    _, main = make_repo(tmp_path)
    (main / "backend").mkdir()
    (main / "backend" / "requirements.txt").write_text("fastapi>=0.115.0\npytest>=8.0.0\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # 'python' esta en PATH pero reporta una version vieja (< 3.12); '.venv'
    # deliberadamente no se crea. git/gh siguen disponibles vía el PATH real.
    fake_python = bin_dir / "python.cmd"
    fake_python.write_text("@echo off\necho Python 3.9.0\n", encoding="utf-8")

    restricted_path = os.pathsep.join([str(bin_dir), os.environ.get("PATH", "")])
    env = base_env(extra_path=restricted_path)

    result = run_preflight(main, env=env)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "PREFLIGHT: BLOCKING" in result.stdout
    assert "python instalado es" in result.stdout
    assert "Python 3.9.0" in result.stdout
    assert ">= 3.12" in result.stdout
    assert ".venv no existe" in result.stdout
    assert "Accion:" in result.stdout


def test_generic_mode_reports_blocking_for_dirty_develop_without_auto_fixing(tmp_path: Path):
    _, main = make_repo(tmp_path)
    (main / "draft.txt").write_text("cambio sin commitear", encoding="utf-8")

    before_status = git(main, "status", "--short").stdout

    result = run_preflight(main)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "BLOCKING" in result.stdout
    assert "develop" in result.stdout
    assert "sin commitear" in result.stdout

    after_status = git(main, "status", "--short").stdout
    assert after_status == before_status
    assert (main / "draft.txt").read_text(encoding="utf-8") == "cambio sin commitear"


def test_preflight_never_mutates_the_repository(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [-] {SLUG} - Demo\n")
    make_worktree(main, tmp_path, push=True)

    before_head, before_worktrees = repo_snapshot(main)

    result_generic = run_preflight(main)
    result_slug = run_preflight(main, args=["-Slug", SLUG])

    after_head, after_worktrees = repo_snapshot(main)

    assert result_generic.returncode in (0, 1)
    assert result_slug.returncode in (0, 1)
    assert after_head == before_head
    assert after_worktrees == before_worktrees
    assert git(main, "status", "--short").stdout == ""


# ---------------------------------------------------------------------------
# Modo -Slug: matriz worktree/rama/ROADMAP (criterio 4). Un test dedicado
# por cada fila BLOCKING/WARNING, mas casos OK representativos.
# ---------------------------------------------------------------------------


def test_matrix_pending_no_branch_no_worktree_is_ok(tmp_path: Path):
    _, main = make_repo(tmp_path)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "Feature no iniciada" in result.stdout
    assert "[BLOCKING]" not in [line.split(" ", 1)[0] for line in result.stdout.splitlines() if "matriz" not in line.lower()]


def test_matrix_pending_with_branch_and_worktree_is_ok_informative(tmp_path: Path):
    _, main = make_repo(tmp_path)
    make_worktree(main, tmp_path)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "Feature en progreso (normal)" in result.stdout


def test_matrix_ready_with_remote_branch_is_ok_informative(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [-] {SLUG} - Demo\n")
    make_worktree(main, tmp_path, push=True)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "en camino a PR/CI" in result.stdout


def test_matrix_ready_without_remote_branch_is_blocking(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [-] {SLUG} - Demo\n")
    make_worktree(main, tmp_path, push=False)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 1
    assert "BLOCKING" in result.stdout
    assert "no existe la rama remota" in result.stdout
    assert f"git push -u origin {BRANCH}" in result.stdout
    assert "ready-for-pr.ps1" in result.stdout


def test_matrix_ready_without_local_branch_or_worktree_is_blocking(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [-] {SLUG} - Demo\n")

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 1
    assert "BLOCKING" in result.stdout
    assert "no hay rama ni worktree local" in result.stdout
    assert "git worktree add" in result.stdout


def test_matrix_done_no_local_artifacts_is_ok(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [x] {SLUG} - Demo\n")

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "Todo limpio" in result.stdout


def test_matrix_done_with_branch_and_worktree_is_warning(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [x] {SLUG} - Demo\n")
    make_worktree(main, tmp_path)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 0  # WARNING no bloquea
    assert "WARNING" in result.stdout
    assert "el reconciliador no limpio" in result.stdout
    assert "start-local-reconciler.ps1 -Slug 99-demo" in result.stdout


def test_matrix_done_with_orphaned_local_branch_is_warning(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [x] {SLUG} - Demo\n")
    git(main, "branch", BRANCH)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 0
    assert "WARNING" in result.stdout
    assert "rama local huerfana" in result.stdout
    assert f"git branch -d {BRANCH}" in result.stdout


def test_matrix_done_with_worktree_but_no_branch_is_blocking(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [x] {SLUG} - Demo\n")
    make_worktree(main, tmp_path)
    # Estado roto simulado: se borra la referencia de la rama a mano
    # (bypaseando 'git branch -d', que normalmente lo impediria mientras
    # esta en uso por un worktree), dejando el worktree sin rama asociada.
    (main / ".git" / "refs" / "heads" / "feature" / SLUG).unlink()

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 1
    assert "BLOCKING" in result.stdout
    assert "estado roto" in result.stdout
    assert "git worktree remove --force" in result.stdout


def test_matrix_duplicate_roadmap_entry_is_blocking(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [-] {SLUG} - Uno\n- [x] {SLUG} - Dos\n")

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 1
    assert "BLOCKING" in result.stdout
    assert "mas de una entrada" in result.stdout


def test_matrix_missing_roadmap_entry_is_blocking(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line="- [ ] 01-otra-feature - Demo\n")

    result = run_preflight(main, args=["-Slug", SLUG])

    assert result.returncode == 1
    assert "BLOCKING" in result.stdout
    assert "No hay ninguna entrada" in result.stdout


def test_matrix_worktree_off_convention_is_warning(tmp_path: Path):
    _, main = make_repo(tmp_path)
    off_convention_dir = tmp_path / "en-otro-lugar" / SLUG
    off_convention_dir.parent.mkdir(parents=True, exist_ok=True)
    git(main, "worktree", "add", "-q", str(off_convention_dir), "-b", BRANCH)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "WARNING" in result.stdout
    assert "no sigue la convencion" in result.stdout


def test_matrix_worktree_registered_but_missing_on_disk_is_warning(tmp_path: Path):
    _, main = make_repo(tmp_path)
    worktree = make_worktree(main, tmp_path)
    shutil.rmtree(worktree)

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "WARNING" in result.stdout
    assert "ya no existe en disco" in result.stdout
    assert "git worktree prune" in result.stdout


def test_matrix_invalid_slug_format_reuses_get_feature_info_message(tmp_path: Path):
    _, main = make_repo(tmp_path)

    result = run_preflight(main, args=["-Slug", "Invalido_Slug"])

    assert result.returncode != 0
    assert "Slug invalido" in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Estado del reconciliador local (lock obsoleto con log de error).
# ---------------------------------------------------------------------------


def test_matrix_reports_dead_reconciler_lock_with_error_log_as_warning(tmp_path: Path):
    _, main = make_repo(tmp_path, roadmap_line=f"- [x] {SLUG} - Demo\n")
    state_dir = main / ".git" / "feature-reconcilers"
    state_dir.mkdir(parents=True)
    (state_dir / f"{SLUG}.pid").write_text("400000001", encoding="ascii")
    (state_dir / f"{SLUG}.err.log").write_text(
        "Timeout esperando cierre remoto de 99-demo en origin/develop.", encoding="utf-8"
    )

    result = run_preflight(main, args=["-Slug", SLUG])

    assert "WARNING" in result.stdout
    assert "termino con error" in result.stdout
    assert f"{SLUG}.err.log" in result.stdout
