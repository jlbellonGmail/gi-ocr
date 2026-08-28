"""
Test suite for T3.3 - Field Reporting Processor.

Tests for generate_field_report, classify_fields_from_t32_output, and differentiate_field_states functions.
Simple unit tests to verify T3.3 field reporting functionality.
"""

import pytest
from backend.app.field_reporting_processor import (
    generate_field_report,
    classify_fields_from_t32_output,
    differentiate_field_states
)


# Test data
SUCCESS_TEST_DATA = {
    'raw_ocr_text': 'Cliente: 12345\nImporte: S/ 100.00\nPeriodo: 01/2023',
    'candidate_fields': {
        'cliente': '12345',
        'importe': 'S/ 100.00',
        'periodo': '01/2023',
    },
    'validated_fields': {
        'cliente': '12345',
        'importe': 'S/ 100.00',
        'periodo': '01/2023',
    },
    'rejected_fields': {},
    'missing_fields': {},
    'document_type': 'invoice',
    'source_document_reference': 'test.pdf',
}

INVALID_TEST_DATA = {
    'raw_ocr_text': 'Cliente: INVALID\nImporte: S/ LETRAS\nFecha: 01/2023',
    'candidate_fields': {
        'cliente': 'INVALID',
        'importe': 'S/ LETRAS',
        'fecha': '01/2023',
    },
    'validated_fields': {
        'cliente': 'INVALID',
        'importe': None,
        'fecha': '01/2023',
    },
    'rejected_fields': {
        'importe': {'value': 'S/ LETRAS', 'reason': 'invalid'},
    },
    'missing_fields': {},
    'document_type': 'invoice',
    'source_document_reference': 'test.pdf',
}

MISSING_TEST_DATA = {
    'raw_ocr_text': 'Cliente: 12345\nImporte: S/ 100.00',
    'candidate_fields': {
        'cliente': '12345',
        'importe': 'S/ 100.00',
    },
    'validated_fields': {
        'cliente': '12345',
        'importe': 'S/ 100.00',
    },
    'rejected_fields': {},
    'missing_fields': {
        'periodo': None,
    },
    'document_type': 'invoice',
    'source_document_reference': 'test.pdf',
}

REGRESSION_TEST_DATA = {
    'raw_ocr_text': 'Cliente: X12345\nImporte: S/ 99.99\nPeriodo: 01/2024',
    'candidate_fields': {
        'cliente': 'X12345',
        'importe': 'S/ 99.99',
        'periodo': '01/2024',
    },
    'validated_fields': {
        'cliente': 'X12345',
        'importe': 'S/ 99.99',
        'periodo': '01/2024',
    },
    'rejected_fields': {},
    'missing_fields': {},
    'document_type': 'invoice',
    'source_document_reference': 'test.pdf',
}


@pytest.fixture
def success_test_case():
    """Provide test data for success scenario."""
    return SUCCESS_TEST_DATA


@pytest.fixture
def invalid_test_case():
    """Provide test data for invalid scenario."""
    return INVALID_TEST_DATA


@pytest.fixture
def missing_test_case():
    """Provide test data for missing scenario."""
    return MISSING_TEST_DATA


@pytest.fixture
def regression_test_case():
    """Provide test data for regression scenario."""
    return REGRESSION_TEST_DATA



def test_generate_field_report_success(success_test_case):
    """Test field report generation for valid fields."""
    report = generate_field_report(**success_test_case)

    assert report['document_type'] == 'invoice'
    assert report['source_document_reference'] == 'test.pdf'
    assert 'accepted_fields' in report
    assert 'rejected_fields' in report
    assert 'missing_fields' in report
    assert 'summary_counts' in report
    assert 'validation_metadata' in report
    assert 'execution_metadata' in report

    assert set(report['accepted_fields']) == {'cliente', 'importe', 'periodo'}
    assert len(report['rejected_fields']) == 0
    assert len(report['missing_fields']) == 0
    assert report['summary_counts']['accepted_count'] == 3
    assert report['summary_counts']['rejected_count'] == 0
    assert report['summary_counts']['missing_count'] == 0


def test_generate_field_report_invalid(invalid_test_case):
    """Test field report generation for invalid fields."""
    report = generate_field_report(**invalid_test_case)

    assert report['document_type'] == 'invoice'
    assert 'accepted_fields' in report
    assert 'rejected_fields' in report
    assert 'missing_fields' in report

    assert len(report['rejected_fields']) == 1
    assert report['rejected_fields'][0]['field'] == 'importe'

    assert report['summary_counts']['rejected_count'] == 1


def test_generate_field_report_missing(missing_test_case):
    """Test field report generation for missing fields."""
    report = generate_field_report(**missing_test_case)

    assert 'missing_fields' in report
    assert 'periodo' in report['missing_fields']
    assert report['summary_counts']['missing_count'] == 1


def test_generate_field_report_regression(regression_test_case):
    """Test field report generation for regression case."""
    report = generate_field_report(**regression_test_case)

    assert len(report['accepted_fields']) == 3
    assert 'summary_counts' in report
    assert report['summary_counts']['accepted_count'] == 3


def test_classify_fields_from_t32_success():
    """Test classification from T3.2 output for successful case."""
    t32_result = {
        'raw_ocr_text': 'Cliente: 12345\nImporte: S/ 100.00\nPeriodo: 01/2023',
        'candidate_fields': {
            'cliente': '12345',
            'importe': 'S/ 100.00',
            'periodo': '01/2023',
        },
        'validated_fields': {
            'cliente': '12345',
            'importe': 'S/ 100.00',
            'periodo': '01/2023',
        },
        'rejected_fields': {},
        'missing_fields': {},
    }

    report = classify_fields_from_t32_output(
        t32_result=t32_result,
        document_type='invoice',
        source_document_reference='t32_output.pdf',
    )

    assert report['document_type'] == 'invoice'
    assert 'accepted_fields' in report
    assert len(report['accepted_fields']) == 3


def test_classify_fields_from_t32_invalid():
    """Test classification from T3.2 output for invalid case."""
    t32_result = {
        'raw_ocr_text': 'Cliente: INVALID\nImporte: S/ LETRAS\nFecha: 01/2023',
        'candidate_fields': {
            'cliente': 'INVALID',
            'importe': 'S/ LETRAS',
            'fecha': '01/2023',
        },
        'validated_fields': {
            'cliente': 'INVALID',
            'importe': None,
            'fecha': '01/2023',
        },
        'rejected_fields': {
            'importe': {'value': 'S/ LETRAS', 'reason': 'invalid'},
        },
        'missing_fields': {},
    }

    report = classify_fields_from_t32_output(
        t32_result=t32_result,
        document_type='invoice',
        source_document_reference='t32_output.pdf',
    )

    assert len(report['rejected_fields']) == 1
    assert report['rejected_fields'][0]['field'] == 'importe'
    assert report['rejected_fields'][0]['reason'] == 'invalid'


def test_classify_fields_from_t32_missing():
    """Test classification from T3.2 output for missing fields."""
    t32_result = {
        'raw_ocr_text': 'Cliente: 12345\nImporte: S/ 100.00',
        'candidate_fields': {
            'cliente': '12345',
            'importe': 'S/ 100.00',
        },
        'validated_fields': {
            'cliente': '12345',
            'importe': 'S/ 100.00',
        },
        'rejected_fields': {},
        'missing_fields': {
            'periodo': None,
        },
    }

    report = classify_fields_from_t32_output(
        t32_result=t32_result,
        document_type='invoice',
        source_document_reference='t32_output.pdf',
    )

    assert 'periodo' in report['missing_fields']
    assert report['summary_counts']['missing_count'] == 1


def test_differentiate_field_states():
    """Test explicit field state differentiation."""
    raw_ocr_text = 'Cliente: 12345\nImporte: S/ 100.00'
    candidate_fields = {'cliente': '12345', 'importe': 'S/ 100.00'}
    validated_fields = {'cliente': '12345', 'importe': 'S/ 100.00'}
    rejected_fields = {}
    missing_fields = {'periodo': None}

    result = differentiate_field_states(
        raw_ocr_text=raw_ocr_text,
        candidate_fields=candidate_fields,
        validated_fields=validated_fields,
        rejected_fields=rejected_fields,
        missing_fields=missing_fields,
    )

    assert result['raw_ocr_text'] == raw_ocr_text
    assert result['candidate_fields'] == candidate_fields
    assert result['validated_fields'] == validated_fields
    assert result['rejected_fields'] == rejected_fields
    assert result['missing_fields'] == missing_fields


def test_regresson_maintains_consistency():
    """Test that regression test maintains consistency with T3.2 output."""
    # Mock T3.2 output
    t32_result = {
        'raw_ocr_text': 'Cliente: X12345\nImporte: S/ 99.99\nPeriodo: 01/2024',
        'candidate_fields': {
            'cliente': 'X12345',
            'importe': 'S/ 99.99',
            'periodo': '01/2024',
        },
        'validated_fields': {
            'cliente': 'X12345',
            'importe': 'S/ 99.99',
            'periodo': '01/2024',
        },
        'rejected_fields': {},
        'missing_fields': {},
    }

    # Generate report
    report = classify_fields_from_t32_output(
        t32_result=t32_result,
        document_type='invoice',
        source_document_reference='regression_test.pdf',
    )

    # Verify consistency
    assert len(report['accepted_fields']) == 3
    assert report['summary_counts']['accepted_count'] == 3
    assert report['summary_counts']['rejected_count'] == 0
    assert report['summary_counts']['missing_count'] == 0