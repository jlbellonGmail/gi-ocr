"""Suite de regresión permanente de precisión OCR/extracción (feature
`08-regresion-dataset-ocr`, `runs/08-regresion-dataset-ocr/spec.md`).

Ejercita el pipeline real de captura
(`backend/app/capture_pipeline.process_document`, motor RapidOCR/ONNX
two-pass ROI, ADR-006) contra un dataset mínimo de fixtures sintéticas
deterministas (`backend/tests/fixtures/synthetic_ocr_documents.py`), con
expected outputs campo por campo para los dos proveedores ya configurados
(`LITORAL_GAS`/`GAS`, `CEVT`/`ELECTRICITY`, ver
`backend/app/templates/providers.py`).

Corre sin condición de skip como parte de `pytest -q`/`pytest -v`, la misma
invocación de `.github/workflows/ci.yml`: no depende de
`backend/tests/fixtures/_local_samples/real/` ni de ningún archivo
gitignored/privado (a diferencia de `test_local_samples_real.py`). Si el
motor OCR real no está disponible en el entorno, falla con un error claro
(mismo comportamiento que `test_ocr_gas.py`), no se salta en silencio.

Cada caso verifica explícitamente, por separado, los cinco estados de campo
que exige la regla de dominio OCR de `AGENTS.md`: texto bruto OCR
(`raw_ocr_text`), campo candidato (`structured_output.candidate_fields`),
campo validado (`validated_fields`), campo rechazado (`rejected_fields`,
con motivo) y campo no encontrado (`missing_fields`).

Criterio de comparación de valores esperados: reutiliza (importa)
`values_match` de `scripts/benchmark_captura.py` (tolerancia numérica
`abs_tol=0.01` para montos, `strip().lower()` para texto) -- no introduce
un segundo criterio divergente (criterio 9 del spec).

Ver `docs/tecnica/regresion-dataset-ocr.md` para el diseño completo,
incluida la decisión de generar las fixtures en tiempo de test (no
versionadas como archivo) y la calibración de brillo/nitidez frente a
`quality_gate.evaluate`.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from backend.app import capture_pipeline, ocr_engine
from backend.app.templates.providers import cevt_template, litoral_gas_template
from backend.tests.fixtures.synthetic_ocr_documents import (
    build_cevt_image,
    build_litoral_gas_image,
    build_unknown_document_image,
)
from scripts.benchmark_captura import values_match


@pytest.fixture(scope="module")
def engine_warm():
    """Carga el singleton RapidOCR una sola vez para toda la suite (mismo
    patrón que `test_local_samples_real.py`/`test_quality_gate.py`): evita
    pagar el costo de carga de modelos en cada test y deja evidencia de que
    el motor real está disponible en el entorno (si no lo está, este
    fixture falla con un error claro, no se salta)."""
    ocr_engine.warmup()
    return ocr_engine.get_engine()


def _process(tmp_path, image, name: str) -> Dict[str, Any]:
    path = tmp_path / f"{name}.png"
    image.save(path)
    return capture_pipeline.process_document(str(path), name)


def _assert_validated_matches(structured: Dict[str, Any], field: str, expected: Any) -> None:
    validated = structured["validated_fields"]
    assert field in validated, f"'{field}' esperado en validated_fields, ausente. validated={validated}"
    assert values_match(validated[field], expected), (
        f"'{field}' validado con valor inesperado: obtenido={validated[field]!r} esperado={expected!r}"
    )
    assert field not in structured["rejected_fields"], (
        f"'{field}' no debería estar en rejected_fields: {structured['rejected_fields'].get(field)}"
    )
    assert field not in structured["missing_fields"], f"'{field}' no debería estar en missing_fields"
    assert structured["candidate_fields"].get(field) is not None, (
        f"'{field}' debería tener un valor candidato (no None) antes de validar"
    )


class TestLitoralGasValidDocument:
    """Caso de regresión: `LITORAL_GAS` válido completo (criterio 7,
    spec). Todos los `required_fields` de `litoral_gas_template()` deben
    terminar en `validated_fields` con el valor esperado."""

    @pytest.fixture(scope="class")
    @classmethod
    def result(cls, tmp_path_factory, engine_warm):
        image, expected = build_litoral_gas_image()
        tmp_path = tmp_path_factory.mktemp("litoral_gas_valid")
        return _process(tmp_path, image, "litoral_gas_valid"), expected

    def test_raw_ocr_text_is_not_empty(self, result):
        res, _expected = result
        assert res["raw_ocr_text"].strip() != "", "raw_ocr_text (texto bruto OCR) no debería estar vacío"
        assert "litoral" in res["raw_ocr_text"].lower(), "el texto bruto debería incluir el encabezado del proveedor"

    def test_all_required_fields_validated_with_expected_value(self, result):
        res, expected = result
        structured = res["structured_output"]
        required = litoral_gas_template().required_fields
        assert set(required) == set(expected), "el fixture debe cubrir exactamente los required_fields de la plantilla"
        for field in required:
            _assert_validated_matches(structured, field, expected[field])

    def test_no_unexpected_rejected_or_missing_fields(self, result):
        res, _expected = result
        structured = res["structured_output"]
        rejected = structured["rejected_fields"]
        assert rejected == {}, f"no se esperaban campos rechazados: {rejected}"
        assert structured["missing_fields"] == {}, f"no se esperaban campos faltantes: {structured['missing_fields']}"

    def test_provider_detected_and_service(self, result):
        res, _expected = result
        assert res["processing_metadata"]["provider_detected"] == "LITORAL_GAS"
        assert res["structured_output"]["validated_fields"]["service"] == "GAS"

    def test_quality_gate_does_not_reject(self, result):
        """Ver runs/08-regresion-dataset-ocr/audit-2.md: verificación
        explícita de que el fixture no dispara `reject` de
        `quality_gate.evaluate` con el motor OCR real."""
        res, _expected = result
        assert res["processing_metadata"]["quality_gate"]["verdict"] != "reject"


class TestCevtValidDocument:
    """Caso de regresión: `CEVT` válido completo (criterio 7, spec)."""

    @pytest.fixture(scope="class")
    @classmethod
    def result(cls, tmp_path_factory, engine_warm):
        image, expected = build_cevt_image()
        tmp_path = tmp_path_factory.mktemp("cevt_valid")
        return _process(tmp_path, image, "cevt_valid"), expected

    def test_raw_ocr_text_is_not_empty(self, result):
        res, _expected = result
        assert res["raw_ocr_text"].strip() != "", "raw_ocr_text (texto bruto OCR) no debería estar vacío"

    def test_all_required_fields_validated_with_expected_value(self, result):
        res, expected = result
        structured = res["structured_output"]
        required = cevt_template().required_fields
        assert set(required) == set(expected), "el fixture debe cubrir exactamente los required_fields de la plantilla"
        for field in required:
            _assert_validated_matches(structured, field, expected[field])

    def test_no_unexpected_rejected_or_missing_fields(self, result):
        res, _expected = result
        structured = res["structured_output"]
        rejected = structured["rejected_fields"]
        assert rejected == {}, f"no se esperaban campos rechazados: {rejected}"
        assert structured["missing_fields"] == {}, f"no se esperaban campos faltantes: {structured['missing_fields']}"

    def test_provider_detected_and_service(self, result):
        res, _expected = result
        assert res["processing_metadata"]["provider_detected"] == "CEVT"
        assert res["structured_output"]["validated_fields"]["service"] == "ELECTRICITY"

    def test_quality_gate_does_not_reject(self, result):
        res, _expected = result
        assert res["processing_metadata"]["quality_gate"]["verdict"] != "reject"


class TestLitoralGasInvalidPeriod:
    """Caso de regresión: `LITORAL_GAS` con `periodo` semánticamente
    inválido (criterio 7, spec): debe terminar en `rejected_fields`, nunca
    en `validated_fields` ni ausente sin más (falso positivo evitado real,
    no un simple `missing`)."""

    INVALID_PERIOD = "13/2026"

    @pytest.fixture(scope="class")
    @classmethod
    def result(cls, tmp_path_factory, engine_warm):
        image, expected = build_litoral_gas_image(periodo=cls.INVALID_PERIOD)
        tmp_path = tmp_path_factory.mktemp("litoral_gas_invalid_period")
        return _process(tmp_path, image, "litoral_gas_invalid_period"), expected

    def test_raw_ocr_text_contains_the_invalid_value(self, result):
        res, _expected = result
        assert res["raw_ocr_text"].strip() != ""
        assert self.INVALID_PERIOD in res["raw_ocr_text"], (
            "el texto bruto OCR debería contener el valor inválido inyectado en el fixture"
        )

    def test_periodo_candidate_carries_the_invalid_value(self, result):
        res, _expected = result
        candidate = res["structured_output"]["candidate_fields"]
        assert candidate.get("periodo") == self.INVALID_PERIOD, (
            f"candidate_fields['periodo'] debería ser '{self.INVALID_PERIOD}', obtenido {candidate.get('periodo')!r}"
        )

    def test_periodo_is_rejected_with_non_empty_reason(self, result):
        res, _expected = result
        rejected = res["structured_output"]["rejected_fields"]
        assert "periodo" in rejected, f"'periodo' debería estar en rejected_fields, obtenido: {rejected}"
        assert rejected["periodo"].get("reason"), "el motivo de rechazo de 'periodo' no debería estar vacío"
        assert rejected["periodo"].get("value") == self.INVALID_PERIOD

    def test_periodo_never_validated_nor_missing(self, result):
        res, _expected = result
        structured = res["structured_output"]
        assert "periodo" not in structured["validated_fields"], "'periodo' inválido nunca debe terminar validado"
        assert "periodo" not in structured["missing_fields"], (
            "'periodo' inválido fue candidato y rechazado, no debe reportarse también como 'missing'"
        )

    def test_other_required_fields_still_validated(self, result):
        """El campo inválido no debe arrastrar al resto: el resto de los
        `required_fields` sigue extrayéndose y validándose con normalidad."""
        res, expected = result
        structured = res["structured_output"]
        required = litoral_gas_template().required_fields
        for field in required:
            if field == "periodo":
                continue
            _assert_validated_matches(structured, field, expected[field])


class TestUnknownDocument:
    """Caso de regresión: documento "no reconocido" (criterio 7, spec):
    texto legible/nítido, misma calidad de imagen que los fixtures válidos,
    sin ninguna `classify_keyword` de `LITORAL_GAS` ni `CEVT`. Debe llegar a
    clasificar proveedor (no cortar por `quality_gate.reject`) y resultar en
    `provider_detected == "UNKNOWN"` sin campos inventados."""

    @pytest.fixture(scope="class")
    @classmethod
    def result(cls, tmp_path_factory, engine_warm):
        image = build_unknown_document_image()
        tmp_path = tmp_path_factory.mktemp("unknown_document")
        return _process(tmp_path, image, "unknown_document")

    def test_raw_ocr_text_is_not_empty(self, result):
        assert result["raw_ocr_text"].strip() != "", (
            "raw_ocr_text no debería estar vacío: el documento es legible, sólo no coincide con ningún proveedor"
        )

    def test_quality_gate_does_not_reject(self, result):
        """Distingue explícitamente este caso ('no reconocido', con OCR
        exitoso) del camino de `quality_gate` rechazado (feature
        `06-calidad-captura-mobile`), que nunca llega a
        `provider_detected` -- ver runs/08-regresion-dataset-ocr/spec.md,
        "Riesgos / supuestos"."""
        quality_gate = result["processing_metadata"]["quality_gate"]
        assert quality_gate["verdict"] != "reject", (
            f"el fixture 'no reconocido' no debería disparar reject de calidad: {quality_gate}"
        )

    def test_provider_detected_is_unknown(self, result):
        assert result["processing_metadata"]["provider_detected"] == "UNKNOWN"

    def test_no_candidate_fields_for_any_known_provider(self, result):
        structured = result["structured_output"]
        assert structured["candidate_fields"] == {}, (
            f"no se esperaban campos candidatos para un documento UNKNOWN: {structured['candidate_fields']}"
        )

    def test_no_validated_fields_for_any_known_provider(self, result):
        structured = result["structured_output"]
        known_fields = set(litoral_gas_template().required_fields) | set(cevt_template().required_fields)
        validated_known = known_fields & set(structured["validated_fields"])
        assert not validated_known, f"no se esperaban campos de LITORAL_GAS ni CEVT validados: {validated_known}"
        assert structured["validated_fields"] == {}, (
            f"no se esperaba ningún campo validado para un documento UNKNOWN: {structured['validated_fields']}"
        )

    def test_no_rejected_and_no_missing_fields(self, result):
        """`unknown_template()` define `required_fields=[]`: no hay nada que
        pueda quedar `missing`, y no hay validador que pueda rechazar nada."""
        structured = result["structured_output"]
        assert structured["rejected_fields"] == {}
        assert structured["missing_fields"] == {}


def test_synthetic_fixtures_are_deterministic():
    """Determinismo de fixtures (criterio 10 del spec): generar la misma
    fixture dos veces produce exactamente los mismos bytes de imagen, sin
    aleatoriedad no controlada."""
    img_a, expected_a = build_litoral_gas_image()
    img_b, expected_b = build_litoral_gas_image()
    assert img_a.tobytes() == img_b.tobytes()
    assert expected_a == expected_b

    cevt_a, cevt_expected_a = build_cevt_image()
    cevt_b, cevt_expected_b = build_cevt_image()
    assert cevt_a.tobytes() == cevt_b.tobytes()
    assert cevt_expected_a == cevt_expected_b

    unknown_a = build_unknown_document_image()
    unknown_b = build_unknown_document_image()
    assert unknown_a.tobytes() == unknown_b.tobytes()
