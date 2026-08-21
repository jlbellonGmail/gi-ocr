import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WAIT_PR_CI = ROOT / "scripts" / "wait-pr-ci.ps1"


def powershell() -> str:
    candidates = ["powershell.exe", "pwsh"] if os.name == "nt" else ["pwsh", "powershell"]
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    pytest.skip("PowerShell no esta disponible")


def git_env(extra_path: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "NUL" if os.name == "nt" else "/dev/null"
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra_path:
        env["PATH"] = str(extra_path) + os.pathsep + env["PATH"]
    return env


def run_file(args: list[str], cwd: Path, env: dict[str, str] | None = None):
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WAIT_PR_CI), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def git(repo: Path, *args: str, check: bool = True):
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        env=git_env(),
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr + result.stdout)
    return result


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "checkout", "-b", "feature/99-demo")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Tests")
    (repo / "readme.md").write_text("demo\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "init")
    return repo


def write_fake_gh(bin_dir: Path, mode: str) -> None:
    bin_dir.mkdir()
    if os.name == "nt":
        gh = bin_dir / "gh.cmd"
        if mode == "pr_exists":
            gh.write_text(
                "@echo off\n"
                'echo %* | findstr /C:"pr view" >nul && (\n'
                '  echo {"number":77,"url":"https://example.test/pull/77","state":"OPEN","mergeStateStatus":"CLEAN"}\n'
                "  exit /b 0\n"
                ")\n"
                'echo %* | findstr /C:"--watch" >nul && (\n'
                "  echo all checks passed\n"
                "  exit /b 0\n"
                ")\n"
                'echo %* | findstr /C:"pr checks" >nul && (\n'
                "  echo check-a\tpass\t1s\n"
                "  exit /b 0\n"
                ")\n"
                "echo unexpected args: %* 1>&2\n"
                "exit /b 1\n",
                encoding="utf-8",
            )
        elif mode == "pr_missing":
            gh.write_text(
                "@echo off\n"
                'echo %* | findstr /C:"pr view" >nul && (\n'
                "  echo no pull requests found for branch 1>&2\n"
                "  exit /b 1\n"
                ")\n"
                "echo unexpected args: %* 1>&2\n"
                "exit /b 1\n",
                encoding="utf-8",
            )
        elif mode == "watch_success":
            gh.write_text(
                "@echo off\n"
                'echo %* | findstr /C:"--watch" >nul && (\n'
                "  echo all checks passed\n"
                "  exit /b 0\n"
                ")\n"
                "echo unexpected args: %* 1>&2\n"
                "exit /b 1\n",
                encoding="utf-8",
            )
        elif mode == "watch_failure":
            gh.write_text(
                "@echo off\n"
                'echo %* | findstr /C:"--watch" >nul && (\n'
                "  echo some checks failed 1>&2\n"
                "  exit /b 1\n"
                ")\n"
                "echo unexpected args: %* 1>&2\n"
                "exit /b 1\n",
                encoding="utf-8",
            )
        else:
            raise ValueError(mode)
    else:
        gh = bin_dir / "gh"
        if mode == "pr_exists":
            gh.write_text(
                "#!/bin/sh\n"
                'case "$*" in\n'
                '  *\'pr view\'*) echo \'{"number":77,"url":"https://example.test/pull/77",'
                '"state":"OPEN","mergeStateStatus":"CLEAN"}\'; exit 0;;\n'
                "  *'--watch'*) echo 'all checks passed'; exit 0;;\n"
                "  *'pr checks'*) printf 'check-a\\tpass\\t1s\\n'; exit 0;;\n"
                '  *) echo "unexpected args: $*" >&2; exit 1;;\n'
                "esac\n",
                encoding="utf-8",
            )
        elif mode == "pr_missing":
            gh.write_text(
                "#!/bin/sh\n"
                'case "$*" in\n'
                "  *'pr view'*) echo 'no pull requests found for branch' >&2; exit 1;;\n"
                '  *) echo "unexpected args: $*" >&2; exit 1;;\n'
                "esac\n",
                encoding="utf-8",
            )
        elif mode == "watch_success":
            gh.write_text(
                "#!/bin/sh\n"
                'case "$*" in\n'
                "  *'--watch'*) echo 'all checks passed'; exit 0;;\n"
                '  *) echo "unexpected args: $*" >&2; exit 1;;\n'
                "esac\n",
                encoding="utf-8",
            )
        elif mode == "watch_failure":
            gh.write_text(
                "#!/bin/sh\n"
                'case "$*" in\n'
                "  *'--watch'*) echo 'some checks failed' >&2; exit 1;;\n"
                '  *) echo "unexpected args: $*" >&2; exit 1;;\n'
                "esac\n",
                encoding="utf-8",
            )
        else:
            raise ValueError(mode)
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)


def test_snapshot_reports_pr_and_checks_without_blocking(tmp_path: Path):
    repo = make_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    write_fake_gh(bin_dir, "pr_exists")

    result = run_file(["-Snapshot"], repo, git_env(bin_dir))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PR #77" in result.stdout
    assert "https://example.test/pull/77" in result.stdout
    assert "OPEN" in result.stdout
    assert "CLEAN" in result.stdout
    assert "check-a" in result.stdout


def test_snapshot_reports_missing_pr_with_nonzero_exit(tmp_path: Path):
    repo = make_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    write_fake_gh(bin_dir, "pr_missing")

    result = run_file(["-Snapshot"], repo, git_env(bin_dir))

    assert result.returncode != 0
    assert "No existe PR para" in result.stdout
    assert "todavia" in result.stdout


def test_watch_mode_still_succeeds_when_checks_pass(tmp_path: Path):
    repo = make_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    write_fake_gh(bin_dir, "watch_success")

    result = run_file([], repo, git_env(bin_dir))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CI verde" in result.stdout


def test_watch_mode_still_fails_when_checks_fail(tmp_path: Path):
    repo = make_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    write_fake_gh(bin_dir, "watch_failure")

    result = run_file([], repo, git_env(bin_dir))

    assert result.returncode != 0
    assert "no terminaron en verde" in (result.stdout + result.stderr)
