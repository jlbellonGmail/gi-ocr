"""Tests de integración del pipeline de captura con facturas privadas locales (gated).

Sólo corre si existen backend/tests/fixtures/_local_samples/real/{GAS.jpeg,cevt.jpeg}
y el contrato expected.local.json (gitignored). No hardcodea valores en el extractor:
el contrato se lee desde expected.local.json.
"""
import json
from pathlib import Path

import pytest

from backend.app import capture_pipeline, ocr_engine

REAL = Path(__file__).resolve().parent / "fixtures" / "_local_samples" / "real"
CONTRACT = REAL / "expected.local.json"

pytestmark = pytest.mark.skipif(
    not (REAL / "GAS.jpeg").exists() or not (REAL / "cevt.jpeg").exists() or not CONTRACT.exists(),
    reason="Muestras privadas locales no disponibles (gitignored).",
)


@pytest.fixture(scope="module")
def contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def engine_warm():
    ocr_engine.warmup()
    return ocr_engine.get_engine()


def _run(doc_key, contract):
    doc = contract["documents"][doc_key]
    img = REAL / doc["image"]
    res = capture_pipeline.process_document(str(img), doc["image"])
    return res, doc


def test_gas_fields(contract, engine_warm):
    res, doc = _run("GAS_LITORAL", contract)
    sv = res["structured_output"]["validated_fields"]
    exp = doc["fields"]
    # campos auto extraíbles (periodo se corrige por HITL, se admite missing aquí)
    for k in ["provider", "cliente", "comprobante", "fecha_emision", "vencimiento", "total"]:
        if k == "total":
            assert abs(float(sv[k]) - float(exp[k])) < 0.01
        else:
            assert sv[k] == exp[k], f"{k}: {sv[k]} != {exp[k]}"
    # periodo: se admite missing (ilegible para PP-OCRv3) -> HITL lo corrige
    assert "periodo" in res["structured_output"]["missing_fields"] or sv.get("periodo") == exp["periodo"]


def test_cevt_all_fields(contract, engine_warm):
    res, doc = _run("CEVT", contract)
    sv = res["structured_output"]["validated_fields"]
    exp = doc["fields"]
    for k in ["provider", "cliente", "medidor", "periodo", "comprobante", "fecha_emision", "vencimiento", "codigo_pago_electronico", "total"]:
        if k == "total":
            assert abs(float(sv[k]) - float(exp[k])) < 0.01
        else:
            assert sv[k] == exp[k], f"{k}: {sv[k]} != {exp[k]}"
    assert res["structured_output"]["missing_fields"] == {}


def test_no_gas_confusion_for_cevt(contract, engine_warm):
    res, _ = _run("CEVT", contract)
    assert res["processing_metadata"]["provider_detected"] == "CEVT"
    sv = res["structured_output"]["validated_fields"]
    assert sv.get("service") == "ELECTRICITY"
    assert sv.get("service") != "GAS"


def test_unknown_not_gas(tmp_path):
    # imagen sin anclas claras no debe clasificarse como GAS por defecto
    from PIL import Image
    import numpy as np
    img = Image.new("RGB", (400, 600), "white")
    p = tmp_path / "blank.png"
    img.save(p)
    res = capture_pipeline.process_document(str(p), "blank.png")
    assert res["processing_metadata"]["provider_detected"] == "UNKNOWN"