"""Tests contractuales del endpoint de introspección de servicios.

Cubre el criterio de aceptación 12 de
runs/16-administracion-servicios-documentos/spec.md:
GET /api/v1/services y GET /api/v1/services/{service_id}.
"""

from __future__ import annotations

from backend.app import services_config
from backend.app.main import app
from fastapi.testclient import TestClient

c = TestClient(app)


def _write_ini(tmp_path, content: str, monkeypatch):
    ini_path = tmp_path / "services.ini"
    ini_path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(services_config, "SERVICES_INI", ini_path)
    return ini_path


# ---------------------------------------------------------------------------
# Contra services.ini real (GAS, CEVT)
# ---------------------------------------------------------------------------


def test_list_services_returns_gas_and_cevt_with_schema():
    r = c.get("/api/v1/services")
    assert r.status_code == 200
    body = r.json()
    ids = {s["id"] for s in body["services"]}
    assert {"GAS", "CEVT"} <= ids

    gas = next(s for s in body["services"] if s["id"] == "GAS")
    assert gas["title"] == "Servicio de Gas"
    field_names = {f["name"] for f in gas["fields"]}
    assert field_names == {"importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"}

    cliente = next(f for f in gas["fields"] if f["name"] == "cliente")
    assert cliente["label"] == "Cliente"
    assert cliente["type"] == "text"
    assert cliente["required"] is True
    assert cliente["example"] == "045-987654"


def test_get_service_detail_gas():
    r = c.get("/api/v1/services/GAS")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "GAS"
    assert body["title"] == "Servicio de Gas"
    assert len(body["fields"]) == 5


def test_get_service_detail_normalizes_lowercase():
    r = c.get("/api/v1/services/gas")
    assert r.status_code == 200
    assert r.json()["id"] == "GAS"


def test_get_service_detail_normalizes_surrounding_spaces():
    r = c.get("/api/v1/services/%20gas%20")
    assert r.status_code == 200
    assert r.json()["id"] == "GAS"


def test_get_unknown_service_returns_404_not_500():
    r = c.get("/api/v1/services/UNKNOWN_SERVICE")
    assert r.status_code == 404
    assert "UNKNOWN_SERVICE" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Casos borde: archivo vacío / sección inválida
# ---------------------------------------------------------------------------


def test_list_services_empty_ini_returns_200_with_empty_list(tmp_path, monkeypatch):
    _write_ini(tmp_path, "", monkeypatch)
    r = c.get("/api/v1/services")
    assert r.status_code == 200
    assert r.json() == {"services": []}


def test_list_services_invalid_section_does_not_return_bare_500(tmp_path, monkeypatch):
    _write_ini(tmp_path, "[BAD]\nTitle=Bad\n", monkeypatch)  # falta Fields
    r = c.get("/api/v1/services")
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "BAD" in detail
    assert "Fields" in detail
    assert "Traceback" not in detail


def test_get_service_invalid_section_does_not_return_bare_500(tmp_path, monkeypatch):
    _write_ini(tmp_path, "[BAD]\nTitle=Bad\n", monkeypatch)  # falta Fields
    r = c.get("/api/v1/services/BAD")
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "BAD" in detail
    assert "Fields" in detail
    assert "Traceback" not in detail
