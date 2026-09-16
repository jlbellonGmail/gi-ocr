from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "post-hitl-merge-gate.yml"
SCRIPT = ROOT / "scripts" / "complete-approved-pr.ps1"


def test_workflow_dispatch_declares_explicit_inputs_and_mode_selection():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in content
    for name in ("pr_number", "expected_branch", "expected_base", "expected_head_sha", "hitl_intent", "confirmation"):
        assert f"      {name}:" in content
    assert "github.event_name == 'workflow_dispatch'" in content
    assert "SingleMaintainer" in content
    assert "HITL_EVENT_NAME: ${{ github.event_name }}" in content
    assert "actions: read" in content


def test_review_mode_and_single_maintainer_event_are_separate():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "github.event_name == 'pull_request_review'" in content
    assert "github.event.review.state == 'approved'" in content
    assert "github.event_name == 'pull_request'" in content
    assert "github.event.action == 'synchronize'" in content
    assert "HITL_MODE: ${{ github.event_name == 'workflow_dispatch' && 'SingleMaintainer' || 'Review' }}" in content
    assert "github.event_name == 'workflow_dispatch'" in content
    assert "-Mode $env:HITL_MODE" in content


def test_single_maintainer_is_fail_closed_and_requires_exact_inputs():
    content = SCRIPT.read_text(encoding="utf-8")
    for value in (
        '"workflow_dispatch"',
        "SINGLE_MAINTAINER_HITL_ACTORS",
        '"MERGE"',
        '"I_CONFIRM_HITL_MERGE"',
        '"^[0-9a-fA-F]{40}$"',
        '"OPEN"',
        "expected_head_sha",
        '"--match-head-commit"',
    ):
        assert value in content
    assert "-cnotcontains $Actor" in content
    assert "if ($allowed.Count -eq 0)" in content
    assert "headRefOid -ne $ExpectedHeadSha" in content


def test_required_checks_are_allowlisted_by_ci_job_and_exact_sha():
    content = SCRIPT.read_text(encoding="utf-8")
    assert '@{ Workflow = "CI"; Job = "test"; Id = "CI/test" }' in content
    assert '@{ Workflow = "CI"; Job = "quality"; Id = "CI/quality" }' in content
    assert '"--workflow", "ci.yml"' in content
    assert '"--commit", $ExpectedHeadSha' in content
    assert '"Post-HITL merge gate"' in content
    assert "databaseId,status,conclusion,headSha" in content
    assert '$check.Status -ne "completed"' in content
    assert '$check.Conclusion -ne "success"' in content


def test_required_checks_reject_non_success_states_and_exclude_gate():
    content = SCRIPT.read_text(encoding="utf-8")
    assert 'Status = "missing"' in content
    for state in ("completed", "success", "Post-HITL merge gate"):
        assert state in content
    start = content.index("function Get-RequiredCiChecks")
    end = content.index("function Assert-PrSnapshot")
    assert "Wait-PrChecks" not in content[start:end]


def test_all_single_maintainer_identity_and_pr_guards_are_explicit():
    content = SCRIPT.read_text(encoding="utf-8")
    for value in (
        "-cnotcontains $Actor",
        "if ($allowed.Count -eq 0)",
        'if ($Pr.state -ne "OPEN")',
        "baseRefName",
        "headRefName",
        "headRefOid",
        "if ($expectedBaseName -ne $BaseBranch)",
    ):
        assert value in content


def test_hitl_summary_contains_auditable_metadata_without_branch_file():
    content = SCRIPT.read_text(encoding="utf-8")
    for value in (
        "Timestamp UTC",
        "Expected HEAD SHA",
        "Observed HEAD SHA",
        "Authorization source: vars.SINGLE_MAINTAINER_HITL_ACTORS",
        "GITHUB_STEP_SUMMARY",
        "merge executed",
    ):
        assert value in content


def test_single_maintainer_report_serializes_check_array_as_text():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "function Get-GateReportDetails" in content
    assert 'if ($ModeName -eq "SingleMaintainer")' in content
    assert "-Details (Get-GateReportDetails -ModeName $Mode -Checks $checks)" in content


def test_stale_head_is_revalidated_immediately_before_merge():
    content = SCRIPT.read_text(encoding="utf-8")
    assert content.count("Get-PrSnapshot -GitHubCliPath $ghPath -PrRef $prRef") >= 2
    assert "final validation passed" in content
    assert '"--match-head-commit", $expectedSha' in content


def test_no_human_authorization_file_is_created_by_implementation():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "human-authorization.md" not in content
