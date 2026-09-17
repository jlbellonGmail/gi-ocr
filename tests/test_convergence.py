# ruff: noqa: E501
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "convergence.ps1"


def run(tmp_path, payload, *extra):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(SCRIPT), "-InputPath", str(source), *extra], capture_output=True, text=True
    )


def base(verdict="APPROVED", findings=None, iteration=1, **reviewer):
    return {
        "iteration": iteration,
        "assessment": {"assessment": "ASSESS", "deterministic": True, "depth": "STANDARD"},
        "sdd": {"depth": "STANDARD"},
        "reviewer": {"verdict": verdict, "findings": findings or [], **reviewer},
        "tests": {"status": "green"},
    }


def result(r):
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_approval_and_one_correction(tmp_path):
    assert result(run(tmp_path, base()))["verdict"] == "APPROVED"
    finding = [{"id": "F-1", "severity": "HIGH", "description": "falta validacion", "status": "OPEN"}]
    assert result(run(tmp_path, base("CHANGES_REQUESTED", finding)))["verdict"] == "CHANGES_REQUESTED"


def test_stall_is_safe_and_material_decision_escalates(tmp_path):
    p = base("CHANGES_REQUESTED", [{"id": "F-1", "severity": "HIGH", "description": "x", "status": "OPEN"}], 2)
    p["previous"] = {"findingsFingerprint": "F-1:HIGH:x", "openFindings": 1}
    out = result(run(tmp_path, p))
    assert out["verdict"] == "FAILED_SAFELY" and out["noProgress"]
    assert result(run(tmp_path, base("CHANGES_REQUESTED", [], needsPlanner=True)))["verdict"] == "NEEDS_HUMAN_DECISION"


def test_depth_budget_and_safety_modes(tmp_path):
    for depth, budget in (("LIGHT", 2), ("STANDARD", 4), ("FULL", 6)):
        p = base("CHANGES_REQUESTED", [{"id": "x", "status": "OPEN"}], 1)
        p["assessment"]["depth"] = p["sdd"]["depth"] = depth
        out = result(run(tmp_path, p))
        assert out["budget"]["maxIterations"] == budget
        assert out["builderMayApprove"] is False and out["providerAgnostic"] is True


def test_external_and_technical_terminal_states(tmp_path):
    assert result(run(tmp_path, base("BLOCKED", blockedExternal=True)))["verdict"] == "BLOCKED"
    p = base()
    p["execution"] = {"status": "failed"}
    assert result(run(tmp_path, p))["verdict"] == "FAILED_SAFELY"
