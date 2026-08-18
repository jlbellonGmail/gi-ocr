"""E2E real en navegador con Playwright (no TestClient).

Levanta el servidor uvicorn en un proceso separado, abre Chromium, carga las facturas
privadas locales (si existen), verifica accepted/rejected/missing, edita+corrige el
periodo de GAS, confirma y descarga. Genera capturas en e2e_evidence/ (gitignored).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
REAL = ROOT / "backend" / "tests" / "fixtures" / "_local_samples" / "real"
EVID = ROOT / "e2e_evidence"
EVID.mkdir(exist_ok=True)

pytestmark = pytest.mark.skipif(
    not (REAL / "GAS.jpeg").exists() or not (REAL / "cevt.jpeg").exists(),
    reason="Muestras privadas locales no disponibles (gitignored).",
)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["GI_OCR_ORT_THREADS"] = "3"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    # esperar arranque
    for _ in range(60):
        try:
            import urllib.request
            urllib.request.urlopen(base + "/api/v1", timeout=1)
            break
        except Exception:
            time.sleep(1)
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


def _upload_and_wait(page, base, file_path, name, timeout=90):
    page.goto(base + "/")
    page.wait_for_selector("#pick-btn")
    before = set(page.evaluate("async () => (await (await fetch('/api/v1/jobs')).json()).jobs.map(j => j.job_id)"))
    page.set_input_files("#file-input", str(file_path))
    # el handler onchange del input sube el archivo
    deadline = time.time() + timeout
    while time.time() < deadline:
        jobs = page.evaluate("async () => (await (await fetch('/api/v1/jobs')).json()).jobs")
        new_ids = [j["job_id"] for j in jobs if j["job_id"] not in before]
        if new_ids:
            job_id = new_ids[0]
            j = page.evaluate(f"async () => (await fetch('/api/v1/jobs/{job_id}')).json()")
            if j["status"] in ("ready", "failed"):
                return job_id
        time.sleep(1)
    assert False, f"el job de {name} no quedó ready"


def test_e2e_litoral_gas(server, tmp_path):
    base = server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        job_id = _upload_and_wait(page, base, REAL / "GAS.jpeg", "GAS")
        page.screenshot(path=str(EVID / "01_gas_loaded.png"), full_page=True)
        # abrir detalle
        resp = page.evaluate(f"async () => (await fetch('/api/v1/jobs/{job_id}')).json()")
        sv = resp["result"]["structured_output"]["validated_fields"]
        assert sv["provider"] == "LITORAL_GAS"
        assert sv["comprobante"] == "0081-57501806"
        assert sv["total"] == "13429.89"
        # periodo debe estar missing (ilegible) y se corrige por HITL
        assert "periodo" in resp["result"]["structured_output"]["missing_fields"]
        # corregir periodo
        page.click("#refresh-btn")
        page.click(f".qitem >> nth=0")
        page.wait_for_selector("input[data-f='periodo']")
        page.fill("input[data-f='periodo']", "01/2026")
        page.select_option("select[data-state='periodo']", "corrected")
        page.click("#confirm-btn")
        page.wait_for_function("() => document.querySelector('.sbadge.ok') !== null", timeout=15000)
        page.screenshot(path=str(EVID / "02_gas_confirmed.png"), full_page=True)
        # descargar JSON final
        dl = page.evaluate(f"async () => (await fetch('/api/v1/jobs/{job_id}/download')).text()")
        doc = json.loads(dl)
        assert doc["confirmed_fields"]["periodo"] == "01/2026"
        assert doc["confirmed_fields"]["total"] == "13429.89"
        browser.close()


def test_e2e_cevt_all_fields(server):
    base = server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        job_id = _upload_and_wait(page, base, REAL / "cevt.jpeg", "CEVT")
        page.screenshot(path=str(EVID / "03_cevt_loaded.png"), full_page=True)
        resp = page.evaluate(f"async () => (await fetch('/api/v1/jobs/{job_id}')).json()")
        sv = resp["result"]["structured_output"]["validated_fields"]
        assert sv["provider"] == "CEVT"
        assert sv["service"] == "ELECTRICITY"
        assert sv["comprobante"] == "0009-03883672"
        assert sv["medidor"] == "0006071353"
        assert sv["total"] == "47061.59"
        # confirmar todos
        page.click("#refresh-btn")
        page.click(f".qitem >> nth=0")
        page.wait_for_selector("#confirm-btn")
        page.click("#confirm-btn")
        page.wait_for_function("() => document.querySelector('.sbadge.ok') !== null", timeout=15000)
        page.screenshot(path=str(EVID / "04_cevt_confirmed.png"), full_page=True)
        browser.close()


def test_e2e_no_cevt_gas_confusion(server):
    base = server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        job_id = _upload_and_wait(page, base, REAL / "cevt.jpeg", "CEVT2")
        resp = page.evaluate(f"async () => (await fetch('/api/v1/jobs/{job_id}')).json()")
        sv = resp["result"]["structured_output"]["validated_fields"]
        # no debe ser GAS ni LITORAL_GAS
        assert sv["provider"] == "CEVT"
        assert sv.get("service") != "GAS"
        browser.close()