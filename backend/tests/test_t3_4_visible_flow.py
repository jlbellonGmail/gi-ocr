"""
Test suite for T3.4 — Visible Document Processing Flow.

Tests for the integration of T3.2 orchestrator and T3.3 field reporting into a final JSON output.
"""

import json

from backend.app.t3_2_orchestrator import orquestar_documento_controlado

FIXTURE_PATH = "backend/tests/fixtures/gas_sample.jpg"


def test_t34_visible_flow_generates_json():
    """Test that T3.4 visible flow produces valid JSON output with all required keys."""
    from scripts.t3_4_visible_flow import run_t34_visible_flow

    result = run_t34_visible_flow(FIXTURE_PATH)

    # Verify JSON structure
    assert isinstance(result, dict)

    # Verify required top-level keys
    assert "raw_ocr_text" in result
    assert "structured_output" in result
    assert "field_report" in result

    # Verify raw_ocr_text is a string
    assert isinstance(result["raw_ocr_text"], str)
    assert len(result["raw_ocr_text"]) > 0


def test_t34_visible_flow_json_serializable():
    """Test that T3.4 output is JSON serializable."""
    from scripts.t3_4_visible_flow import run_t34_visible_flow

    result = run_t34_visible_flow(FIXTURE_PATH)

    # Should be serializable without errors
    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    # Should be deserializable
    parsed = json.loads(json_str)
    assert parsed == result


def test_t34_field_report_integrates_t33():
    """Test that field_report contains T3.3 required structure."""
    from scripts.t3_4_visible_flow import run_t34_visible_flow

    result = run_t34_visible_flow(FIXTURE_PATH)

    field_report = result["field_report"]

    # Verify field_report structure
    assert "accepted_fields" in field_report
    assert "rejected_fields" in field_report
    assert "missing_fields" in field_report
    assert "summary_counts" in field_report

    # Verify accepted_fields is a list
    assert isinstance(field_report["accepted_fields"], list)

    # Verify rejected_fields is a list
    assert isinstance(field_report["rejected_fields"], list)

    # Verify missing_fields is a list
    assert isinstance(field_report["missing_fields"], list)

    # Verify summary_counts has required counts
    assert "accepted_count" in field_report["summary_counts"]
    assert "rejected_count" in field_report["summary_counts"]
    assert "missing_count" in field_report["summary_counts"]


def test_t34_uses_t32_orchestrator():
    """Test that T3.4 uses actual T3.2 orchestrator output."""
    from scripts.t3_4_visible_flow import run_t34_visible_flow

    result = run_t34_visible_flow(FIXTURE_PATH)

    # Verify structured_output matches T3.2 orchestrator output
    t32_result = orquestar_documento_controlado(FIXTURE_PATH)

    assert result["raw_ocr_text"] == t32_result["raw_ocr_text"]
    assert result["structured_output"]["document_type"] == t32_result["document_type"]


def test_t34_visible_flow_handles_missing_fixture():
    """Test that T3.4 visible flow fails gracefully with missing fixture."""
    # Attempt to process non-existent fixture
    import sys

    from scripts.t3_4_visible_flow import main

    old_argv = sys.argv
    sys.argv = ["t3_4_visible_flow.py", "nonexistent_fixture.jpg"]

    try:
        exit_code = main()
        assert exit_code == 1  # Should return error code
    finally:
        sys.argv = old_argv


def test_t34_validates_count_consistency():
    """Test that field_report counts are consistent with field lists."""
    from scripts.t3_4_visible_flow import run_t34_visible_flow

    result = run_t34_visible_flow(FIXTURE_PATH)

    field_report = result["field_report"]
    summary = field_report["summary_counts"]

    assert summary["accepted_count"] == len(field_report["accepted_fields"])
    assert summary["rejected_count"] == len(field_report["rejected_fields"])
    assert summary["missing_count"] == len(field_report["missing_fields"])


def test_t34_recognizes_valid_fields():
    """Test that T3.4 correctly identifies validated fields from pipeline."""
    from scripts.t3_4_visible_flow import run_t34_visible_flow

    result = run_t34_visible_flow(FIXTURE_PATH)

    field_report = result["field_report"]

    # The GAS sample should have some accepted fields
    assert len(field_report["accepted_fields"]) > 0

    # At least cliente and nro_medidor are typically extracted
    accepted = field_report["accepted_fields"]
    assert isinstance(accepted, list)
