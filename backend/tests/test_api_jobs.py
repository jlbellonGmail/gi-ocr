"""Tests de integración de la APIREST (TestClient): carga, procesamiento, confirmación, descarga."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

c = TestClient(app)

REAL = __import__("pathlib").Path(__file__).resolve().parent / "fixtures" / "_local_samples" / "real"


def test_health():
    r = c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["engine_loaded"] is True


def test_jobs_empty():
    r = c.get("/api/v1/jobs")
    assert r.status_code == 200
    assert "jobs" in r.json()


def test_upload_rejects_bad_ext():
    r = c.post("/api/v1/jobs",
               files={"files": ("bad.exe", b"\x00\x00", "application/octet-stream")})
    assert r.status_code == 400


def test_job_id_validation():
    bad = "not-a-uuid"
    assert c.get(f"/api/v1/jobs/{bad}").status_code == 400
    assert c.post(f"/api/v1/jobs/{bad}/confirm", json={"confirmed_fields": []}).status_code == 400


@pytest.mark.skipif(not (REAL / "cevt.jpeg").exists(), reason="muestra privada local no disponible")
def test_full_flow_cevt():
    with open(REAL / "cevt.jpeg", "rb") as f:
        r = c.post("/api/v1/jobs", files={"files": ("cevt.jpeg", f, "image/jpeg")})
    assert r.status_code == 200
    jid = r.json()["created"][0]["job_id"]
    j = _wait_ready(jid, timeout=60)
    assert j["status"] == "ready"
    sv = j["result"]["structured_output"]["validated_fields"]
    assert sv["provider"] == "CEVT"
    assert sv["comprobante"] == "0009-03883672"
    assert sv["total"] == "47061.59"
    # confirmar
    corrections = [{"field": f, "state": "confirmed", "final_value": str(v)} for f, v in sv.items()]
    rc = c.post(f"/api/v1/jobs/{jid}/confirm", json={"confirmed_fields": corrections})
    assert rc.status_code == 200
    assert rc.json()["review_state"] == "confirmed"
    # descargar
    dl = c.get(f"/api/v1/jobs/{jid}/download")
    assert dl.status_code == 200
    fp = c.get(f"/api/v1/jobs/{jid}/original")
    assert fp.status_code == 200


def test_export_batch():
    r = c.get("/api/v1/export")
    assert r.status_code == 200
    assert "batch" in r.json()


def test_inbound_status():
    r = c.get("/api/v1/inbound/status")
    assert r.status_code == 200
    assert "inbound_dir" in r.json()


def _wait_ready(jid, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = c.get(f"/api/v1/jobs/{jid}").json()
        if j["status"] in ("ready", "failed"):
            return j
        time.sleep(1)
    return c.get(f"/api/v1/jobs/{jid}").json()