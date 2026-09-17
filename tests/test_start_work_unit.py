import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "start-work-unit.ps1"

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
WHITESPACE_RE = re.compile(r"\s+")


def plain_output(output: str) -> str:
    # pwsh en Linux envuelve mensajes de error largos al ancho de terminal
    # e inserta un marcador "|" al inicio de cada linea continuada (el
    # "gutter" del formateador de errores). Se quita antes de colapsar
    # espacios para que el mensaje quede como una sola frase comparable.
    without_ansi = ANSI_ESCAPE_RE.sub("", output)
    without_pipes = without_ansi.replace("|", " ")
    return WHITESPACE_RE.sub(" ", without_pipes).strip()


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
    return env


def git(repo: Path, *args: str, check: bool = True):
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False, env=command_env())
    if check and result.returncode != 0:
        raise AssertionError(result.stderr + result.stdout)
    return result


def run_file(args: list[str], cwd: Path):
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=command_env(),
    )


def make_repo(tmp_path: Path, roadmap_lines: list[str]) -> Path:
    remote = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], cwd=tmp_path, check=True)
    subprocess.run(["git", "init", str(repo)], cwd=tmp_path, check=True)
    git(repo, "checkout", "-b", "develop")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Tests")
    (repo / "ROADMAP.md").write_text("\n".join(roadmap_lines) + "\n", encoding="utf-8")
    git(repo, "add", "ROADMAP.md")
    git(repo, "commit", "-m", "roadmap inicial")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "develop")
    return repo


# --------------------------------------------------------------------------
# Feature mode
# --------------------------------------------------------------------------


def test_feature_happy_path_creates_branch_and_worktree(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno"])

    result = run_file(["-Mode", "Feature", "-Slug", "02-item-a"], repo)

    assert result.returncode == 0, result.stdout + result.stderr
    worktree = tmp_path / "worktrees" / "02-item-a"
    assert worktree.exists()
    assert git(repo, "rev-parse", "--verify", "--quiet", "feature/02-item-a", check=False).returncode == 0


def test_feature_item_already_non_pending_is_rejected(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [-] 02-item-a - Uno"])

    result = run_file(["-Mode", "Feature", "-Slug", "02-item-a"], repo)

    assert result.returncode != 0
    assert "no esta pendiente" in plain_output(result.stdout + result.stderr)
    assert not (tmp_path / "worktrees" / "02-item-a").exists()


def test_feature_rejects_items_param(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno"])

    result = run_file(["-Mode", "Feature", "-Slug", "02-item-a", "-Items", "02-item-a"], repo)

    assert result.returncode != 0
    assert "no aplica en Mode=Feature" in plain_output(result.stdout + result.stderr)


def test_dirty_develop_blocks_start(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno"])
    (repo / "dirty.txt").write_text("uncommitted", encoding="utf-8")

    result = run_file(["-Mode", "Feature", "-Slug", "02-item-a"], repo)

    assert result.returncode != 0
    assert "sin commitear" in plain_output(result.stdout + result.stderr)


def test_must_run_from_main_checkout_not_worktree(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno", "- [ ] 03-item-b - Dos"])
    other_worktree = tmp_path / "worktrees" / "03-item-b"
    git(repo, "worktree", "add", "-b", "feature/03-item-b", str(other_worktree), "develop")

    result = run_file(["-Mode", "Feature", "-Slug", "02-item-a"], other_worktree)

    assert result.returncode != 0
    assert "checkout principal" in plain_output(result.stdout + result.stderr)


# --------------------------------------------------------------------------
# Milestone mode
# --------------------------------------------------------------------------


def test_milestone_happy_path_with_two_items(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno", "- [ ] 03-item-b - Dos"])

    result = run_file(
        ["-Mode", "Milestone", "-Slug", "mi-milestone", "-Items", "02-item-a,03-item-b"],
        repo,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    worktree = tmp_path / "worktrees" / "mi-milestone"
    assert worktree.exists()
    manifest_path = worktree / "runs" / "milestone-mi-milestone" / "work-unit.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["items"] == ["02-item-a", "03-item-b"]
    assert manifest["mode"] == "milestone"


def test_milestone_item_already_claimed_by_existing_manifest_is_rejected(tmp_path: Path):
    repo = make_repo(
        tmp_path,
        ["- [ ] 02-item-a - Uno", "- [ ] 03-item-b - Dos", "- [ ] 04-item-c - Tres"],
    )
    first = run_file(
        ["-Mode", "Milestone", "-Slug", "milestone-uno", "-Items", "02-item-a,03-item-b"],
        repo,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    git(repo, "checkout", "develop")

    second = run_file(
        ["-Mode", "Milestone", "-Slug", "milestone-dos", "-Items", "03-item-b,04-item-c"],
        repo,
    )

    assert second.returncode != 0
    assert "ya esta reclamado" in plain_output(second.stdout + second.stderr)
    assert not (tmp_path / "worktrees" / "milestone-dos").exists()


def test_milestone_duplicate_item_in_same_list_is_rejected(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno"])

    result = run_file(
        ["-Mode", "Milestone", "-Slug", "mi-milestone", "-Items", "02-item-a,02-item-a"],
        repo,
    )

    assert result.returncode != 0
    assert "duplicados" in plain_output(result.stdout + result.stderr).lower()


def test_milestone_item_not_in_roadmap_is_rejected(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno"])

    result = run_file(
        ["-Mode", "Milestone", "-Slug", "mi-milestone", "-Items", "02-item-a,09-no-existe"],
        repo,
    )

    assert result.returncode != 0
    assert "no existe en ROADMAP.md" in plain_output(result.stdout + result.stderr)
    assert not (tmp_path / "worktrees" / "mi-milestone").exists()


def test_milestone_requires_items_param(tmp_path: Path):
    repo = make_repo(tmp_path, ["- [ ] 02-item-a - Uno"])

    result = run_file(["-Mode", "Milestone", "-Slug", "mi-milestone"], repo)

    assert result.returncode != 0
    assert "obligatorio en Mode=Milestone" in plain_output(result.stdout + result.stderr)
