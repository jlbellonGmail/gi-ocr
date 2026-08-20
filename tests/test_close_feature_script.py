import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "close-feature.ps1"
SLUG = "06-patente"
BRANCH = f"feature/{SLUG}"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
WHITESPACE_RE = re.compile(r"\s+")


def powershell() -> str:
    candidates = ["powershell.exe", "pwsh"] if os.name == "nt" else ["pwsh", "powershell"]
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    pytest.skip("PowerShell no esta disponible")


def command_env(extra_path: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    if extra_path:
        env["PATH"] = str(extra_path) + os.pathsep + env["PATH"]
    return env


def plain_output(output: str) -> str:
    without_ansi = ANSI_ESCAPE_RE.sub("", output)
    return WHITESPACE_RE.sub(" ", without_ansi).strip()


def captured_output(result: subprocess.CompletedProcess[str]) -> str:
    return plain_output("\n".join(part for part in [result.stdout, result.stderr] if part))


def exception_message(result: subprocess.CompletedProcess[str]) -> str:
    return plain_output(result.stderr)


def ps_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None, check: bool = True):
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env or command_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"Command failed: {command}\n{captured_output(result)}")
    return result


def git(repo: Path, *args: str, check: bool = True):
    return run(["git", *args], repo, check=check)


def write_fake_gh(bin_dir: Path, state: str = "MERGED", base: str = "develop") -> None:
    bin_dir.mkdir()
    payload = (
        f'{{"state":"{state}","mergedAt":"2026-08-17T19:00:00Z",'
        f'"baseRefName":"{base}","headRefName":"{BRANCH}"}}'
    )
    if os.name == "nt":
        gh = bin_dir / "gh.cmd"
        gh.write_text(f"@echo off\necho {payload}\n", encoding="utf-8")
    else:
        gh = bin_dir / "gh"
        gh.write_text(f"#!/bin/sh\necho '{payload}'\n", encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)


def make_case(tmp_path: Path, roadmap: str, gh_state: str = "MERGED", gh_base: str = "develop"):
    remote = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktrees" / SLUG
    bin_dir = tmp_path / "bin"

    run(["git", "init", "--bare", str(remote)], tmp_path)
    run(["git", "init", str(repo)], tmp_path)
    git(repo, "checkout", "-b", "develop")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Tests")
    (repo / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    git(repo, "add", "ROADMAP.md")
    git(repo, "commit", "-m", "initial roadmap")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "develop")
    git(repo, "checkout", "-b", BRANCH)
    git(repo, "push", "-u", "origin", BRANCH)
    git(repo, "checkout", "develop")
    git(repo, "worktree", "add", str(worktree), BRANCH)
    write_fake_gh(bin_dir, gh_state, gh_base)
    return repo, remote, worktree, bin_dir


def close_feature(repo: Path, worktree: Path, bin_dir: Path):
    command = (
        "$ErrorActionPreference = 'Stop'; "
        "try { "
        f"& {ps_quote(SCRIPT)} -Slug {ps_quote(SLUG)} -WorktreeDir {ps_quote(worktree)}; "
        "exit $LASTEXITCODE "
        "} catch { "
        "[Console]::Error.WriteLine($_.Exception.Message); "
        "exit 1 "
        "}"
    )
    return run(
        [
            powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        repo,
        env=command_env(bin_dir),
        check=False,
    )


def roadmap(repo: Path, ref: str = "develop") -> str:
    return git(repo, "show", f"{ref}:ROADMAP.md").stdout


def commit_count(repo: Path) -> str:
    return git(repo, "rev-list", "--count", "develop").stdout.strip()


def short_status(repo: Path) -> str:
    lines = git(repo, "status", "--short").stdout.splitlines()
    return "\n".join(line for line in lines if not line.startswith("warning: ")).strip()


def assert_not_cleaned(repo: Path, worktree: Path) -> None:
    assert worktree.exists()
    assert git(repo, "rev-parse", "--verify", "--quiet", BRANCH, check=False).returncode == 0


def test_closes_ready_feature_once_and_cleans_after_remote_validation(tmp_path: Path):
    repo, _, worktree, bin_dir = make_case(tmp_path, f"- [-] {SLUG} - Validacion\n")

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode == 0, result.stdout
    assert f"- [x] {SLUG} - Validacion" in roadmap(repo, "origin/develop")
    assert f"- [-] {SLUG}" not in roadmap(repo, "origin/develop")
    assert not worktree.exists()
    assert git(repo, "rev-parse", "--verify", "--quiet", BRANCH, check=False).returncode != 0
    assert short_status(repo) == ""


def test_already_closed_feature_is_idempotent_and_does_not_create_empty_commit(tmp_path: Path):
    repo, _, worktree, bin_dir = make_case(tmp_path, f"- [x] {SLUG} - Validacion\n")
    before = commit_count(repo)

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode == 0, result.stdout
    assert commit_count(repo) == before
    assert f"- [x] {SLUG} - Validacion" in roadmap(repo, "origin/develop")


@pytest.mark.parametrize(
    ("roadmap_text", "expected"),
    [
        ("- [ ] 07-feriados - Consulta\n", "No existe una entrada exacta"),
        (f"- [-] {SLUG} - Uno\n- [-] {SLUG} - Dos\n", "mas de una coincidencia"),
        (f"- [-] {SLUG} - Uno\n- [x] {SLUG} - Dos\n", "mas de una coincidencia"),
    ],
)
def test_invalid_roadmap_states_fail_before_cleanup(
    tmp_path: Path, roadmap_text: str, expected: str
):
    repo, _, worktree, bin_dir = make_case(tmp_path, roadmap_text)

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode != 0
    assert expected in exception_message(result)
    assert_not_cleaned(repo, worktree)


def test_pending_feature_fails_because_only_ready_can_be_closed(tmp_path: Path):
    repo, _, worktree, bin_dir = make_case(tmp_path, f"- [ ] {SLUG} - Validacion\n")

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode != 0
    assert "no esta en READY_FOR_PR" in exception_message(result)
    assert_not_cleaned(repo, worktree)


def test_pr_not_merged_fails_before_cleanup(tmp_path: Path):
    repo, _, worktree, bin_dir = make_case(
        tmp_path, f"- [-] {SLUG} - Validacion\n", gh_state="OPEN"
    )

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode != 0
    assert "no esta mergeada" in exception_message(result)
    assert_not_cleaned(repo, worktree)


def test_pr_merged_into_another_base_stops_without_cleanup(tmp_path: Path):
    repo, _, worktree, bin_dir = make_case(
        tmp_path, f"- [-] {SLUG} - Validacion\n", gh_base="main"
    )

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode != 0
    output = exception_message(result)
    assert BRANCH in output
    assert "mergeada contra 'main'" in output
    assert "no contra 'develop'" in output
    assert_not_cleaned(repo, worktree)


def test_push_failure_does_not_cleanup_or_claim_success(tmp_path: Path):
    repo, remote, worktree, bin_dir = make_case(tmp_path, f"- [-] {SLUG} - Validacion\n")
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

    result = close_feature(repo, worktree, bin_dir)

    assert result.returncode != 0
    assert "Command failed: git push origin develop" in exception_message(result)
    assert f"- [-] {SLUG}" in roadmap(repo, "origin/develop")
    assert_not_cleaned(repo, worktree)


def test_retries_pending_push_when_close_commit_exists_locally_but_not_pushed(
    tmp_path: Path,
):
    # Simula un corte de red: el commit de cierre queda hecho localmente
    # (Set-Content + git commit ya corrieron) pero 'git push origin develop'
    # falla por el hook. La segunda corrida debe detectar que el commit ya
    # existe localmente (already-closed), reintentar el push pendiente en
    # vez de saltar directo a la verificacion remota, y terminar en exit 0
    # sin generar un commit de cierre duplicado.
    repo, remote, worktree, bin_dir = make_case(tmp_path, f"- [-] {SLUG} - Validacion\n")
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

    first = close_feature(repo, worktree, bin_dir)
    assert first.returncode != 0
    assert f"- [x] {SLUG} - Validacion" in roadmap(repo)
    assert f"- [-] {SLUG}" in roadmap(repo, "origin/develop")
    before = commit_count(repo)
    assert_not_cleaned(repo, worktree)

    hook.unlink()

    second = close_feature(repo, worktree, bin_dir)

    assert second.returncode == 0, second.stdout
    assert commit_count(repo) == before
    assert f"- [x] {SLUG} - Validacion" in roadmap(repo, "origin/develop")
    assert f"- [-] {SLUG}" not in roadmap(repo, "origin/develop")
    assert not worktree.exists()
    assert git(repo, "rev-parse", "--verify", "--quiet", BRANCH, check=False).returncode != 0


def test_rerun_after_success_does_not_create_commit(tmp_path: Path):
    repo, _, worktree, bin_dir = make_case(tmp_path, f"- [-] {SLUG} - Validacion\n")
    first = close_feature(repo, worktree, bin_dir)
    assert first.returncode == 0, first.stdout
    before = commit_count(repo)

    second = close_feature(repo, worktree, bin_dir)

    assert second.returncode == 0, second.stdout
    assert "sin commit vacio" in captured_output(second)
    assert commit_count(repo) == before
