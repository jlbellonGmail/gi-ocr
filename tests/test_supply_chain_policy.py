"""Pruebas enfocadas del gate de supply chain de F12."""
# ruff: noqa: E501

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-supply-chain.ps1"


def run_gate(root: Path):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-Root", str(root)],
        text=True,
        capture_output=True,
    )


def test_gate_accepts_repository():
    result = run_gate(ROOT)
    assert result.returncode == 0, result.stderr


def test_gate_rejects_floating_action(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "name: test\npermissions:\n  contents: read\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements-dev.txt").write_text("pytest==8.3.5\n", encoding="utf-8")
    (tmp_path / "requirements-docs.txt").write_text("mkdocs-material==9.6.18\n", encoding="utf-8")
    result = run_gate(tmp_path)
    assert result.returncode != 0 and "SHA inmutable" in result.stderr


def test_gate_rejects_unpinned_dependency(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "name: test\npermissions:\n  contents: read\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements-dev.txt").write_text("pytest>=8.0\n", encoding="utf-8")
    (tmp_path / "requirements-docs.txt").write_text("mkdocs-material==9.6.18\n", encoding="utf-8")
    result = run_gate(tmp_path)
    assert result.returncode != 0 and "dependencia no fijada" in result.stderr
