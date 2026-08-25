#!/usr/bin/env python3
"""
Suite de regresión OCR/extracción con fixtures sintéticos controlados.
Valida que cambios en el pipeline no degraden la precisión por proveedor,
documento y campo.
"""

import json

# Importar desde la app (sin pasar por HTTP)
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.services_config import load_regression_config

# Enable mock OCR for fast, deterministic testing
from backend.tests.mock_ocr import enable_mock_mode
from backend.tests.regression_helpers import run_full_pipeline

enable_mock_mode()


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "regression"
EXPECTED_DIR = FIXTURES_DIR / "expected"
IMAGES_DIR = FIXTURES_DIR / "images"
METADATA_FILE = FIXTURES_DIR / "metadata.json"


@dataclass
class FieldComparison:
    field_name: str
    expected_value: Any
    extracted_value: Any
    expected_confidence: float
    extracted_confidence: float
    match: bool
    accuracy: float


@dataclass
class ComparisonResult:
    global_accuracy: float
    by_field: Dict[str, FieldComparison]
    passed: bool


def load_metadata() -> Dict[str, Any]:
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def discover_test_cases(metadata: Dict[str, Any]) -> List[tuple]:
    """Descubre casos de test válidos (imagen + expected output)."""
    cases = []
    # Load regression config to get enabled providers
    try:
        from backend.app.services_config import load_regression_config

        regression_config = load_regression_config()
        enabled_providers = {p for p, enabled in regression_config.get("providers", {}).items() if enabled}
    except Exception:
        enabled_providers = set()

    for img_meta in metadata.get("images", []):
        # Skip providers not enabled in regression config
        if enabled_providers and img_meta["provider"] not in enabled_providers:
            continue
        expected_path = EXPECTED_DIR / img_meta["provider"] / f"{img_meta['document_id']}.json"
        image_path = IMAGES_DIR / img_meta["path"]
        if expected_path.exists() and image_path.exists():
            cases.append((img_meta, expected_path, image_path))
    return cases


def compare_values(expected: Any, extracted: Any, field_name: str) -> tuple:
    """
    Compara valores esperados vs extraídos.
    Retorna (match: bool, accuracy: float).
    """
    if expected is None and extracted is None:
        return True, 1.0
    if expected is None or extracted is None:
        return False, 0.0

    # Normalización por tipo de campo
    if field_name == "importe_total":
        try:
            exp_val = float(expected)
            ext_val = float(extracted)
            # Tolerancia del 1%
            diff = abs(exp_val - ext_val) / max(abs(exp_val), 1)
            return diff <= 0.01, max(0.0, 1.0 - diff)
        except (ValueError, TypeError):
            return False, 0.0

    elif field_name in ["fecha_emision", "periodo_facturado"]:
        return str(expected) == str(extracted), 1.0 if str(expected) == str(extracted) else 0.0

    elif field_name in ["cuit_emisor", "cuit_receptor", "numero_comprobante", "numero_linea"]:
        # Normalizar: solo dígitos y guiones
        exp_norm = "".join(c for c in str(expected) if c.isdigit() or c == "-")
        ext_norm = "".join(c for c in str(extracted) if c.isdigit() or c == "-")
        return exp_norm == ext_norm, 1.0 if exp_norm == ext_norm else 0.0

    elif field_name in ["consumo_kwh", "consumo_m3"]:
        try:
            exp_val = float(str(expected).split()[0])
            ext_val = float(str(extracted).split()[0])
            diff = abs(exp_val - ext_val) / max(abs(exp_val), 1)
            return diff <= 0.05, max(0.0, 1.0 - diff)
        except (ValueError, TypeError, IndexError):
            return False, 0.0

    else:
        # Comparación de strings normalizada
        exp_str = str(expected).strip().upper()
        ext_str = str(extracted).strip().upper()
        if exp_str == ext_str:
            return True, 1.0
        # Similitud simple
        from difflib import SequenceMatcher

        similarity = SequenceMatcher(None, exp_str, ext_str).ratio()
        return similarity >= 0.9, similarity


def run_pipeline(image_path: Path, provider: str) -> Dict[str, Any]:
    """Ejecuta el pipeline OCR completo: OCR -> Extracción -> Validación."""
    return run_full_pipeline(image_path, provider)


def compare_fields(validated: Dict[str, Any], expected_fields: Dict[str, Any]) -> ComparisonResult:
    """Compara campos extraídos contra expected outputs."""
    comparisons = {}
    total_accuracy = 0.0
    matched_fields = 0

    all_fields = set(expected_fields.keys()) | set(validated.keys())

    for field_name in all_fields:
        expected_field = expected_fields.get(field_name, {})
        extracted_field = validated.get(field_name, {})

        expected_value = expected_field.get("value")
        extracted_value = extracted_field.get("value")
        expected_confidence = expected_field.get("confidence", 0.0)
        extracted_confidence = extracted_field.get("confidence", 0.0)

        match, accuracy = compare_values(expected_value, extracted_value, field_name)

        comparisons[field_name] = FieldComparison(
            field_name=field_name,
            expected_value=expected_value,
            extracted_value=extracted_value,
            expected_confidence=expected_confidence,
            extracted_confidence=extracted_confidence,
            match=match,
            accuracy=accuracy,
        )

        total_accuracy += accuracy
        if match:
            matched_fields += 1

    global_accuracy = total_accuracy / len(all_fields) if all_fields else 0.0

    return ComparisonResult(
        global_accuracy=global_accuracy, by_field=comparisons, passed=matched_fields == len(all_fields)
    )


@pytest.fixture(scope="session")
def regression_config():
    return load_regression_config()


@pytest.fixture(scope="session")
def fixtures_metadata():
    return load_metadata()


@pytest.fixture(scope="session")
def test_cases(fixtures_metadata, regression_config):
    return discover_test_cases(fixtures_metadata, regression_config)


@pytest.mark.parametrize("img_meta,expected_path,image_path", discover_test_cases(load_metadata()))
def test_regression_field_accuracy(img_meta, expected_path, image_path, regression_config):
    """Test principal: valida precisión campo a campo contra expected outputs."""
    # Cargar expected output
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Verificar versión de fixtures
    metadata = load_metadata()
    expected_version = expected.get("fixtures_version")
    metadata_version = metadata.get("fixtures_version")
    assert expected_version == metadata_version, (
        f"Versión de fixtures mismatch: expected {expected_version}, metadata {metadata_version}"
    )

    # Ejecutar pipeline
    validated = run_pipeline(image_path, img_meta["provider"])

    # Comparar
    result = compare_fields(validated, expected["fields"])

    # Obtener umbrales
    provider = img_meta["provider"]
    global_threshold = regression_config.get("min_global_accuracy", 0.95)
    field_thresholds = regression_config.get("thresholds", {})
    min_field_accuracy = regression_config.get("min_field_accuracy", 0.90)

    # Verificar umbral global
    assert result.global_accuracy >= global_threshold, (
        f"Global accuracy {result.global_accuracy:.2%} < {global_threshold:.0%} "
        f"for {img_meta['provider']}/{img_meta['document_id']} "
        f"(image: {image_path})"
    )

    # Verificar umbrales por campo
    failures = []
    for field_name, field_result in result.by_field.items():
        threshold_key = f"{provider}.{field_name}"
        threshold = field_thresholds.get(threshold_key, min_field_accuracy)

        if field_result.accuracy < threshold:
            failures.append(
                f"Field '{field_name}': accuracy {field_result.accuracy:.2%} < {threshold:.0%} "
                f"(expected: {field_result.expected_value}, got: {field_result.extracted_value})"
            )

    assert not failures, (
        f"Field threshold failures for {img_meta['provider']}/{img_meta['document_id']}:\n" + "\n".join(failures)
    )


def test_fixtures_version_consistency(fixtures_metadata):
    """Verifica que todos los expected outputs tengan la misma versión que metadata."""
    metadata_version = fixtures_metadata.get("fixtures_version")
    for img_meta in fixtures_metadata.get("images", []):
        expected_path = EXPECTED_DIR / img_meta["provider"] / f"{img_meta['document_id']}.json"
        if expected_path.exists():
            with open(expected_path, "r", encoding="utf-8") as f:
                expected = json.load(f)
            assert expected.get("fixtures_version") == metadata_version, (
                f"Version mismatch in {expected_path}: {expected.get('fixtures_version')} != {metadata_version}"
            )


def test_all_providers_have_fixtures(fixtures_metadata, regression_config):
    """Verifica que todos los proveedores habilitados tengan fixtures."""
    enabled_providers = regression_config.get("providers", {})
    providers_with_fixtures = set()

    for img_meta in fixtures_metadata.get("images", []):
        providers_with_fixtures.add(img_meta["provider"])

    for provider, enabled in enabled_providers.items():
        if enabled:
            assert provider in providers_with_fixtures, (
                f"Provider '{provider}' is enabled in config but has no fixtures"
            )


def test_expected_outputs_structure():
    """Valida estructura básica de expected outputs."""
    for expected_path in EXPECTED_DIR.rglob("*.json"):
        with open(expected_path, "r", encoding="utf-8") as f:
            expected = json.load(f)

        assert "fixtures_version" in expected, f"Missing fixtures_version in {expected_path}"
        assert "provider" in expected, f"Missing provider in {expected_path}"
        assert "document_type" in expected, f"Missing document_type in {expected_path}"
        assert "document_id" in expected, f"Missing document_id in {expected_path}"
        assert "fields" in expected, f"Missing fields in {expected_path}"
        assert "validation" in expected, f"Missing validation in {expected_path}"

        for field_name, field_data in expected["fields"].items():
            assert "value" in field_data, f"Field {field_name} missing 'value' in {expected_path}"
            assert "confidence" in field_data, f"Field {field_name} missing 'confidence' in {expected_path}"
            assert 0.0 <= field_data["confidence"] <= 1.0, (
                f"Field {field_name} confidence out of range in {expected_path}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
