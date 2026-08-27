"""Tests for atomic storage bridge .DATA writer."""

import hashlib
import os
import time
from datetime import datetime
from pathlib import Path

import pytest
from backend.app.storage_bridge_writer import (
    build_data_content,
    build_data_filename,
    compute_data_hash,
    write_atomic_data_file,
    write_atomic_data_file_with_retry,
    reconcile_storage_bridge,
    CONTRACT_VERSION,
)


def test_build_data_filename_uses_legacy_contract():
    timestamp = datetime(2026, 6, 23, 15, 30, 45)

    filename = build_data_filename("gas", timestamp)

    assert filename == "GAS_20260623_153045.DATA"


def test_build_data_content_uses_semicolon_and_preserves_empty_values():
    fields = ["importe", "cliente", "periodo"]
    values = {
        "importe": "100,00",
        "cliente": "045-987654",
        "periodo": None,
    }

    content = build_data_content(fields, values)

    assert content.splitlines() == [
        f"VERSION={CONTRACT_VERSION}",
        "importe;cliente;periodo",
        "100,00;045-987654;",
    ]
    assert "," not in content.splitlines()[1]


def test_write_atomic_data_file_writes_tmp_then_moves_to_ready(tmp_path, monkeypatch):
    inbound_dir = tmp_path / "storage_bridge" / "inbound"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    failed_dir = tmp_path / "storage_bridge" / "failed"
    timestamp = datetime(2026, 6, 23, 15, 30, 45)

    original_replace = os.replace
    replace_calls = []

    def tracked_replace(src, dst):
        replace_calls.append((Path(src), Path(dst)))
        original_replace(src, dst)

    monkeypatch.setattr("backend.app.storage_bridge_writer.os.replace", tracked_replace)

    final_path = write_atomic_data_file(
        service="GAS",
        fields=["importe", "cliente"],
        values={"importe": "100,00", "cliente": "045-987654"},
        timestamp=timestamp,
        inbound_dir=inbound_dir,
        ready_dir=ready_dir,
        failed_dir=failed_dir,
    )

    assert final_path == ready_dir / "GAS_20260623_153045.DATA"
    assert final_path.exists()
    assert not (inbound_dir / "GAS_20260623_153045.DATA.tmp").exists()
    assert replace_calls == [
        (
            inbound_dir / "GAS_20260623_153045.DATA.tmp",
            ready_dir / "GAS_20260623_153045.DATA",
        )
    ]

    assert final_path.read_text(encoding="utf-8").splitlines() == [
        f"VERSION={CONTRACT_VERSION}",
        "importe;cliente",
        "100,00;045-987654",
    ]


def test_write_atomic_data_file_does_not_leave_partial_ready_file_on_replace_failure(
    tmp_path,
    monkeypatch,
):
    inbound_dir = tmp_path / "storage_bridge" / "inbound"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    failed_dir = tmp_path / "storage_bridge" / "failed"
    timestamp = datetime(2026, 6, 23, 15, 30, 45)

    original_replace = os.replace

    def failing_ready_replace(src, dst):
        destination = Path(dst)
        if destination.parent == ready_dir:
            raise RuntimeError("simulated atomic move failure")
        original_replace(src, dst)

    monkeypatch.setattr("backend.app.storage_bridge_writer.os.replace", failing_ready_replace)

    with pytest.raises(RuntimeError, match="simulated atomic move failure"):
        write_atomic_data_file(
            service="GAS",
            fields=["importe", "cliente"],
            values={"importe": "100,00", "cliente": "045-987654"},
            timestamp=timestamp,
            inbound_dir=inbound_dir,
            ready_dir=ready_dir,
            failed_dir=failed_dir,
        )

    assert not (ready_dir / "GAS_20260623_153045.DATA").exists()
    assert not (inbound_dir / "GAS_20260623_153045.DATA.tmp").exists()
    assert (failed_dir / "GAS_20260623_153045.DATA.tmp").exists()


def test_write_atomic_data_file_rejects_invalid_payload_before_writing(tmp_path):
    inbound_dir = tmp_path / "storage_bridge" / "inbound"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    failed_dir = tmp_path / "storage_bridge" / "failed"

    with pytest.raises(ValueError, match="semicolon separator"):
        write_atomic_data_file(
            service="GAS",
            fields=["importe", "cliente"],
            values={"importe": "100;00", "cliente": "045-987654"},
            timestamp=datetime(2026, 6, 23, 15, 30, 45),
            inbound_dir=inbound_dir,
            ready_dir=ready_dir,
            failed_dir=failed_dir,
        )

    assert not inbound_dir.exists()
    assert not ready_dir.exists()
    assert not failed_dir.exists()


def test_write_atomic_data_file_does_not_overwrite_existing_ready_file(tmp_path):
    inbound_dir = tmp_path / "storage_bridge" / "inbound"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    failed_dir = tmp_path / "storage_bridge" / "failed"
    ready_dir.mkdir(parents=True)

    existing_file = ready_dir / "GAS_20260623_153045.DATA"
    existing_file.write_text(f"VERSION={CONTRACT_VERSION}\nexisting\ncontent\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        write_atomic_data_file(
            service="GAS",
            fields=["importe", "cliente"],
            values={"importe": "100,00", "cliente": "045-987654"},
            timestamp=datetime(2026, 6, 23, 15, 30, 45),
            inbound_dir=inbound_dir,
            ready_dir=ready_dir,
            failed_dir=failed_dir,
        )

    assert existing_file.read_text(encoding="utf-8") == "existing\ncontent\n"


def test_build_data_content_includes_version_line():
    fields = ["importe", "cliente"]
    values = {"importe": "100,00", "cliente": "045-987654"}

    content = build_data_content(fields, values)
    lines = content.splitlines()

    assert lines[0] == f"VERSION={CONTRACT_VERSION}"
    assert lines[1] == "importe;cliente"
    assert lines[2] == "100,00;045-987654"
    assert len(lines) == 3
    assert content.endswith("\n")


def test_compute_data_hash_deterministic():
    fields = ["importe", "cliente", "periodo"]
    values = {
        "importe": "100,00",
        "cliente": "045-987654",
        "periodo": "01/2026",
    }

    hash1 = compute_data_hash("GAS", fields, values)
    hash2 = compute_data_hash("gas", fields, values)  # case insensitive service
    hash3 = compute_data_hash("GAS", ["cliente", "importe", "periodo"], values)  # different order

    assert hash1 == hash2  # service normalized
    assert hash1 != hash3  # field order matters
    assert len(hash1) == 64  # SHA-256 hex


def test_write_atomic_data_file_with_retry_idempotent_by_hash(tmp_path):
    inbound_dir = tmp_path / "storage_bridge" / "inbound"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    failed_dir = tmp_path / "storage_bridge" / "failed"
    timestamp = datetime(2026, 6, 23, 15, 30, 45)

    # Primera escritura
    path1 = write_atomic_data_file_with_retry(
        service="GAS",
        fields=["importe", "cliente"],
        values={"importe": "100,00", "cliente": "045-987654"},
        timestamp=timestamp,
        inbound_dir=inbound_dir,
        ready_dir=ready_dir,
        failed_dir=failed_dir,
    )

    # Segunda escritura con mismo contenido (distinto timestamp) → debe retornar el mismo archivo
    path2 = write_atomic_data_file_with_retry(
        service="GAS",
        fields=["importe", "cliente"],
        values={"importe": "100,00", "cliente": "045-987654"},
        timestamp=datetime(2026, 6, 23, 15, 30, 46),  # distinto segundo
        inbound_dir=inbound_dir,
        ready_dir=ready_dir,
        failed_dir=failed_dir,
    )

    assert path1 == path2
    assert path1.exists()
    # Solo un archivo en ready/
    data_files = list(ready_dir.glob("*.DATA"))
    assert len(data_files) == 1


def test_write_atomic_data_file_with_retry_backoff(tmp_path, monkeypatch):
    inbound_dir = tmp_path / "storage_bridge" / "inbound"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    failed_dir = tmp_path / "storage_bridge" / "failed"
    timestamp = datetime(2026, 6, 23, 15, 30, 45)

    call_count = 0
    original_replace = os.replace

    def failing_replace(src, dst):
        nonlocal call_count
        call_count += 1
        destination = Path(dst)
        if destination.parent == ready_dir and call_count <= 3:
            raise PermissionError("simulated permission error")
        original_replace(src, dst)

    monkeypatch.setattr("backend.app.storage_bridge_writer.os.replace", failing_replace)
    monkeypatch.setattr("backend.app.storage_bridge_writer.time.sleep", lambda x: None)  # no real sleep

    with pytest.raises(PermissionError, match="simulated permission error"):
        write_atomic_data_file_with_retry(
            service="GAS",
            fields=["importe"],
            values={"importe": "100,00"},
            timestamp=timestamp,
            max_retries=3,
            base_delay_ms=100,
            inbound_dir=inbound_dir,
            ready_dir=ready_dir,
            failed_dir=failed_dir,
        )

    # 4 intentos totales (1 inicial + 3 reintentos)
    assert call_count == 4

    # Error registrado en failed/
    error_files = list(failed_dir.glob("*_error.json"))
    assert len(error_files) == 1
    import json
    error_data = json.loads(error_files[0].read_text(encoding="utf-8"))
    assert error_data["service"] == "GAS"
    assert error_data["attempts"] == 4
    assert error_data["error_type"] == "PermissionError"
    assert "values_hash" in error_data


def test_write_error_record_on_exhausted_retries(tmp_path):
    from backend.app.storage_bridge_writer import _write_error_record
    failed_dir = tmp_path / "storage_bridge" / "failed"
    timestamp = datetime(2026, 6, 23, 15, 30, 45)

    error_path = _write_error_record(
        service="GAS",
        timestamp=timestamp,
        error=RuntimeError("test error"),
        attempts=3,
        fields=["importe"],
        values={"importe": "100,00"},
        failed_dir=failed_dir,
    )

    assert error_path.exists()
    assert error_path.name == "GAS_20260623_153045_error.json"
    import json
    data = json.loads(error_path.read_text(encoding="utf-8"))
    assert data["service"] == "GAS"
    assert data["attempts"] == 3
    assert data["error"] == "test error"
    assert data["error_type"] == "RuntimeError"
    assert data["fields"] == ["importe"]
    assert "values_hash" in data


def test_reconcile_storage_bridge_missing_orphan_mismatch(tmp_path):
    from backend.app.storage_bridge_writer import write_confidence_file
    confirmed_dir = tmp_path / "output" / "confirmed"
    ready_dir = tmp_path / "storage_bridge" / "ready"
    output_dir = tmp_path / "output" / "reconciliation"

    confirmed_dir.mkdir(parents=True)
    ready_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    # 1) Confirmado v2 con .DATA correspondiente (match)
    import json
    conf1 = {
        "job_id": "job1",
        "confirmation_metadata": {
            "contract_version": 2,
            "confirmed_at": "2026-08-26T15:30:45.123456+00:00",
        },
        "structured_output": {
            "service": "GAS",
            "validated_fields": {"importe": "100,00", "cliente": "045-987654"},
        },
    }
    (confirmed_dir / "job1.confirmed.json").write_text(json.dumps(conf1), encoding="utf-8")

    # Escribir .DATA v2 correspondiente
    write_atomic_data_file_with_retry(
        service="GAS",
        fields=["importe", "cliente"],
        values={"importe": "100,00", "cliente": "045-987654"},
        timestamp=datetime(2026, 8, 26, 15, 30, 45),
        ready_dir=ready_dir,
        inbound_dir=tmp_path / "storage_bridge" / "inbound",
        failed_dir=tmp_path / "storage_bridge" / "failed",
    )

    # 2) Confirmado v2 SIN .DATA en ready (missing_in_ready)
    conf2 = {
        "job_id": "job2",
        "confirmation_metadata": {
            "contract_version": 2,
            "confirmed_at": "2026-08-26T15:31:00.123456+00:00",
        },
        "structured_output": {
            "service": "GAS",
            "validated_fields": {"importe": "200,00", "cliente": "045-987654"},
        },
    }
    (confirmed_dir / "job2.confirmed.json").write_text(json.dumps(conf2), encoding="utf-8")

    # 3) .DATA v2 en ready SIN confirmado (orphan_in_ready)
    write_atomic_data_file_with_retry(
        service="CEVT",
        fields=["medidor_numero", "total_a_pagar"],
        values={"medidor_numero": "12345", "total_a_pagar": "1.234,56"},
        timestamp=datetime(2026, 8, 26, 15, 32, 00),
        ready_dir=ready_dir,
        inbound_dir=tmp_path / "storage_bridge" / "inbound",
        failed_dir=tmp_path / "storage_bridge" / "failed",
    )

    # 4) .DATA v1 legacy (sin VERSION=) → debe ignorarse
    legacy_data = ready_dir / "GAS_20260826_153300.DATA"
    legacy_data.write_text("importe;cliente\n100,00;045-987654\n", encoding="utf-8")

    # Ejecutar reconciliación
    report = reconcile_storage_bridge(
        confirmed_dir=confirmed_dir,
        ready_dir=ready_dir,
        output_dir=output_dir,
    )

    assert report["contract_version"] == CONTRACT_VERSION
    assert report["summary"]["total_confirmed_v2"] == 2
    assert report["summary"]["total_ready_v2"] == 2  # solo v2 contados
    assert report["summary"]["missing_count"] == 1  # job2
    assert report["summary"]["orphan_count"] == 1  # CEVT
    assert report["summary"]["mismatch_count"] == 0

    missing = report["missing_in_ready"]
    assert len(missing) == 1
    assert missing[0]["job_id"] == "job2"
    assert missing[0]["service"] == "GAS"

    orphans = report["orphan_in_ready"]
    assert len(orphans) == 1
    assert orphans[0]["service"] == "CEVT"

    # Reporte persistido
    assert report["report_path"]
    report_file = Path(report["report_path"])
    assert report_file.exists()
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["summary"]["missing_count"] == 1
