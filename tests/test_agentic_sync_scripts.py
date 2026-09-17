import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts" / "sync-agentic-adapters.ps1"


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


def run_sync(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SYNC),
            *args,
        ],
        cwd=repo,
        env=command_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def make_agentic_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / ".agentic", repo / ".agentic")
    (repo / ".claude" / "skills").mkdir(parents=True)
    (repo / ".opencode" / "skills").mkdir(parents=True)
    (repo / ".agents" / "skills").mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, env=command_env(), check=True, capture_output=True)
    return repo


def test_sync_generates_adapters_and_is_idempotent(tmp_path: Path):
    repo = make_agentic_repo(tmp_path)

    first = run_sync(repo)
    second = run_sync(repo)
    check = run_sync(repo, "-Check")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert check.returncode == 0, check.stderr
    assert {p.stem for p in (repo / ".claude" / "agents").glob("*.md")} == {"planner", "builder", "reviewer"}
    assert (repo / ".codex" / "planner.config.toml").exists()
    assert not (repo / ".codex" / "prompts" / "analyst-agent.md").exists()
    assert not (repo / ".opencode" / "agent" / "analyst-agent.md").exists()

    opencode = json.loads((repo / "opencode.json").read_text(encoding="utf-8"))
    assert opencode["instructions"] == ["AGENTS.md", ".claude/rules/*.md"]
    assert opencode["agent"]["planner"]["prompt"] == "{file:./.agentic/roles/planner.md}"
    assert opencode["mcp"]["servers"] == {}


def test_sync_generates_read_only_reviewer_adapter(tmp_path: Path):
    repo = make_agentic_repo(tmp_path)

    result = run_sync(repo)
    check = run_sync(repo, "-Check")

    assert result.returncode == 0, result.stderr
    assert check.returncode == 0, check.stderr

    claude_agent = repo / ".claude" / "agents" / "reviewer.md"
    assert claude_agent.exists()
    frontmatter = claude_agent.read_text(encoding="utf-8")
    assert "tools: Read, Grep, Glob" in frontmatter
    assert "Write" not in frontmatter.split("---")[1]
    assert "Edit" not in frontmatter.split("---")[1]
    assert "Bash" not in frontmatter.split("---")[1]

    assert (repo / ".codex" / "reviewer.config.toml").exists()

    opencode = json.loads((repo / "opencode.json").read_text(encoding="utf-8"))
    code_reviewer = opencode["agent"]["reviewer"]
    assert code_reviewer["prompt"] == "{file:./.agentic/roles/reviewer.md}"
    assert code_reviewer["permission"]["edit"] == "deny"
    assert code_reviewer["permission"]["bash"] == "deny"


def test_check_detects_generated_adapter_divergence(tmp_path: Path):
    repo = make_agentic_repo(tmp_path)
    result = run_sync(repo)
    assert result.returncode == 0, result.stderr

    agent = repo / ".claude" / "agents" / "planner.md"
    agent.write_text(agent.read_text(encoding="utf-8") + "\nCambio manual\n", encoding="utf-8")

    check = run_sync(repo, "-Check")

    assert check.returncode != 0
    assert "divergente" in check.stderr


def test_check_detects_opencode_json_divergence(tmp_path: Path):
    repo = make_agentic_repo(tmp_path)
    result = run_sync(repo)
    assert result.returncode == 0, result.stderr

    opencode_path = repo / "opencode.json"
    opencode = json.loads(opencode_path.read_text(encoding="utf-8"))
    opencode["model"] = "manual-edit-not-in-agentic-source"
    opencode_path.write_text(json.dumps(opencode, indent=2), encoding="utf-8")

    check = run_sync(repo, "-Check")

    assert check.returncode != 0
    assert "opencode.json" in check.stderr
    assert "divergente" in check.stderr


def test_check_detects_legacy_prompt_adapters(tmp_path: Path):
    repo = make_agentic_repo(tmp_path)
    result = run_sync(repo)
    assert result.returncode == 0, result.stderr
    legacy = repo / ".codex" / "prompts" / "analyst-agent.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("legacy copy\n", encoding="utf-8")

    check = run_sync(repo, "-Check")

    assert check.returncode != 0
    assert "legacy" in check.stderr


def test_skills_are_mirrored_from_agents_source(tmp_path: Path):
    repo = make_agentic_repo(tmp_path)
    skill = repo / ".agents" / "skills" / "demo-skill" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo-skill\ndescription: Use when testing skill mirroring.\n---\n\n# Demo\n",
        encoding="utf-8",
    )

    result = run_sync(repo)
    check = run_sync(repo, "-Check")

    assert result.returncode == 0, result.stderr
    assert check.returncode == 0, check.stderr
    assert (repo / ".claude" / "skills" / "demo-skill" / "SKILL.md").read_bytes() == skill.read_bytes()
    assert (repo / ".opencode" / "skills" / "demo-skill" / "SKILL.md").read_bytes() == skill.read_bytes()
