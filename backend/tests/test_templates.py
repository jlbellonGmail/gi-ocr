"""Tests unitarios de plantillas: ROI, anclas, registro, campos requeridos."""

from backend.app.templates import all_templates, cevt_template, get_template, litoral_gas_template, unknown_template


def test_registry_keys():
    g = litoral_gas_template()
    c = cevt_template()
    assert g.provider == "LITORAL_GAS" and g.service == "GAS"
    assert c.provider == "CEVT" and c.service == "ELECTRICITY"


def test_required_fields_ga():
    t = litoral_gas_template()
    for f in ["provider", "cliente", "periodo", "comprobante", "fecha_emision", "vencimiento", "total"]:
        assert f in t.required_fields


def test_required_fields_cevt():
    t = cevt_template()
    for f in ["provider", "cliente", "medidor", "periodo", "comprobante", "fecha_emision", "vencimiento", "total"]:
        assert f in t.required_fields
    assert "codigo_pago_electronico" in [ft.name for ft in t.fields]


def test_unknown_template():
    t = unknown_template()
    assert t.provider == "UNKNOWN" and t.document_type == "MANUAL_REVIEW"


def test_bands_normalized():
    for t in all_templates():
        for f in t.fields:
            y1, y2, x1, x2 = f.band
            assert 0.0 <= y1 < y2 <= 1.0
            assert 0.0 <= x1 < x2 <= 1.0


def test_get_template_fallback():
    assert get_template("NOEXISTE").provider == "UNKNOWN"


def test_field_extract_present():
    g = litoral_gas_template()
    comp = g.field_by_name("comprobante")
    assert comp is not None and comp.extract is not None
