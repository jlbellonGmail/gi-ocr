#!/usr/bin/env python3
"""
Tests for MVP End-to-End Demo pipeline
"""

from pathlib import Path

import pytest
from scripts.demo_mvp_e2e import run_demo


def test_run_demo_returns_dict():
    """Test that run_demo returns a dictionary with required keys."""
    result = run_demo()
    assert isinstance(result, dict)
    assert "ocr_raw_text" in result
    assert "candidates" in result
    assert "validated" in result
    assert "rejected" in result
    assert "not_found" in result
    assert "summary" in result
    assert "meta" in result


def test_demo_structure_differences():
    """Test that demo output differentiates all required fields."""
    result = run_demo()

    # Check that all required categories exist
    assert "ocr_raw_text" in result
    assert "candidates" in result
    assert "validated" in result
    assert "rejected" in result
    assert "not_found" in result
    assert "summary" in result
    assert "meta" in result

    # Check that we can access the data
    assert isinstance(result["ocr_raw_text"], str)
    assert isinstance(result["candidates"], dict)
    assert isinstance(result["validated"], dict)
    assert isinstance(result["rejected"], dict)
    assert isinstance(result["not_found"], list)
    assert isinstance(result["summary"], dict)


def test_demo_with_real_fixture():
    """Test demo with the actual GAS fixture."""
    result = run_demo("backend/tests/fixtures/gas_sample.jpg")

    # Basic checks
    assert isinstance(result, dict)
    assert result["meta"]["service"] == "GAS"
    assert isinstance(result["ocr_raw_text"], str)
    assert len(result["ocr_raw_text"]) > 0

    # Check field structure
    expected_fields = {"importe", "a_pagar_hasta", "cliente", "periodo", "nro_medidor"}
    assert set(result["candidates"].keys()) == expected_fields
    assert set(result["validated"].keys()) <= expected_fields
    assert set(result["rejected"].keys()) <= expected_fields
    assert set(result["not_found"]).issubset(expected_fields)


def test_demo_no_file_persistence_in_run_demo():
    """Test that run_demo function does not write files to storage_bridge/ready."""
    # run_demo is designed not to write files, so this should pass
    initial_files = set(Path("storage_bridge/ready").glob("*.DATA"))

    result = run_demo("backend/tests/fixtures/gas_sample.jpg")

    final_files = set(Path("storage_bridge/ready").glob("*.DATA"))

    # No new .DATA files should have been created
    new_files = final_files - initial_files
    assert len(new_files) == 0, f"Unexpected .DATA files created: {new_files}"

    # Verify we got a valid result
    assert isinstance(result, dict)
    assert result["meta"]["service"] == "GAS"


def test_demo_output_is_serializable():
    """Test that demo output can be serialized to JSON."""
    import json

    result = run_demo()

    # This should not raise an exception
    json_str = json.dumps(result, default=str)
    assert isinstance(json_str, str)
    assert len(json_str) > 0


# Test parameterization
@pytest.fixture
def gas_fixture_path():
    return "backend/tests/fixtures/gas_sample.jpg"


def test_demo_with_fixture_param(gas_fixture_path):
    """Test demo using fixture parameter."""
    result = run_demo(gas_fixture_path)
    assert isinstance(result, dict)
    assert result["meta"]["service"] == "GAS"


if __name__ == "__main__":
    # Simple test runner
    print("Running demo structure tests...")

    # Test 1: Does run_demo return a dict with required keys?
    test_run_demo_returns_dict()
    print("✓ test_run_demo_returns_dict passed")

    # Test 2: Does output show differentiation of fields?
    test_demo_structure_differences()
    print("✓ test_demo_structure_differences passed")

    # Test 3: Does demo work with real fixture?
    test_demo_with_real_fixture()
    print("✓ test_demo_with_real_fixture passed")

    # Test 4: Does run_demo avoid file persistence?
    test_demo_no_file_persistence_in_run_demo()
    print("✓ test_demo_no_file_persistence_in_run_demo passed")

    # Test 5: Is output serializable?
    test_demo_output_is_serializable()
    print("✓ test_demo_output_is_serializable passed")

    print("All tests passed!")
