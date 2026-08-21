"""Tests de purga/retención (criterio 7 de
`14-seguridad-privacidad-documentos`): targets, defaults, exclusiones
(`storage_bridge/ready/` nunca se toca, jobs `queued`/`processing` nunca se
purgan, retención `<=0` deshabilita en vez de purgar todo)."""

from __future__ import annotations

import os
import time
from pathlib import Path

from backend.app import retention


def _set_mtime(path: Path, days_ago: float, now: float) -> None:
    ts = now - days_ago * 86400
    os.utime(path, (ts, ts))


# --- purge_directory: comportamiento base ---


def test_purge_directory_removes_only_files_past_threshold(tmp_path):
    d = tmp_path / "target"
    d.mkdir()
    old_file = d / "old.json"
    old_file.write_text("x")
    new_file = d / "new.json"
    new_file.write_text("y")
    gitkeep = d / ".gitkeep"
    gitkeep.write_text("")

    now = time.time()
    _set_mtime(old_file, 40, now)
    _set_mtime(new_file, 1, now)
    _set_mtime(gitkeep, 999, now)  # muy viejo, pero protegido por nombre

    removed = retention.purge_directory(d, retention_days=30, now=now)

    assert old_file in removed
    assert new_file not in removed
    assert not old_file.exists()
    assert new_file.exists()
    assert gitkeep.exists()


def test_purge_directory_disabled_when_retention_is_none(tmp_path):
    d = tmp_path / "target"
    d.mkdir()
    f = d / "very_old.json"
    f.write_text("x")
    _set_mtime(f, 9999, time.time())

    removed = retention.purge_directory(d, retention_days=None, now=time.time())

    assert removed == []
    assert f.exists()


def test_purge_directory_missing_dir_is_noop(tmp_path):
    missing = tmp_path / "does_not_exist"
    removed = retention.purge_directory(missing, retention_days=7, now=time.time())
    assert removed == []


def test_purge_directory_respects_is_protected_hook(tmp_path):
    d = tmp_path / "target"
    d.mkdir()
    protected = d / "protected.json"
    protected.write_text("x")
    _set_mtime(protected, 999, time.time())

    removed = retention.purge_directory(
        d, retention_days=1, now=time.time(), is_protected=lambda p: p.name == "protected.json"
    )

    assert removed == []
    assert protected.exists()


# --- variables de entorno: defaults y "0/negativo = deshabilitado" ---


def test_retention_env_defaults(monkeypatch):
    monkeypatch.delenv("GI_OCR_UPLOAD_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("GI_OCR_JOB_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("GI_OCR_FAILED_RETENTION_DAYS", raising=False)

    assert retention.upload_retention_days() == 7
    assert retention.job_retention_days() == 90
    assert retention.failed_retention_days() == 30
    assert retention.inbound_root_retention_days() == 7


def test_retention_env_zero_or_negative_disables(monkeypatch):
    monkeypatch.setenv("GI_OCR_UPLOAD_RETENTION_DAYS", "0")
    assert retention.upload_retention_days() is None

    monkeypatch.setenv("GI_OCR_UPLOAD_RETENTION_DAYS", "-5")
    assert retention.upload_retention_days() is None


def test_retention_env_custom_value(monkeypatch):
    monkeypatch.setenv("GI_OCR_JOB_RETENTION_DAYS", "14")
    assert retention.job_retention_days() == 14


# --- purge_all: targets, exclusiones ---


def test_purge_all_never_touches_storage_bridge_ready(tmp_path):
    output_dir = tmp_path / "output"
    inbound_dir = tmp_path / "inbound"
    bridge_dir = tmp_path / "storage_bridge"
    ready_dir = bridge_dir / "ready"
    ready_dir.mkdir(parents=True)
    old_ready_file = ready_dir / "GAS_20200101_000000.DATA"
    old_ready_file.write_text("x")
    _set_mtime(old_ready_file, 9999, time.time())

    results = retention.purge_all(output_dir, inbound_dir, bridge_dir, now=time.time())

    assert "ready" not in results
    assert old_ready_file.exists()


def test_purge_all_protects_active_job_upload(tmp_path):
    output_dir = tmp_path / "output"
    uploads = output_dir / "uploads"
    uploads.mkdir(parents=True)
    active_file = uploads / "active_job_source.jpg"
    active_file.write_bytes(b"x")
    _set_mtime(active_file, 9999, time.time())

    class FakeStore:
        def all(self):
            return [{"status": "processing", "file_path": str(active_file)}]

    results = retention.purge_all(
        output_dir, tmp_path / "inbound", tmp_path / "storage_bridge", store=FakeStore(), now=time.time()
    )

    assert active_file.exists()
    assert active_file not in results["uploads"]


def test_purge_all_without_store_still_purges_uploads_by_mtime(tmp_path):
    output_dir = tmp_path / "output"
    uploads = output_dir / "uploads"
    uploads.mkdir(parents=True)
    stale_file = uploads / "stale.jpg"
    stale_file.write_bytes(b"x")
    _set_mtime(stale_file, 9999, time.time())

    results = retention.purge_all(output_dir, tmp_path / "inbound", tmp_path / "storage_bridge", now=time.time())

    assert not stale_file.exists()
    assert stale_file in results["uploads"]


def test_purge_all_targets_match_spec_defaults(tmp_path):
    output_dir = tmp_path / "output"
    inbound_dir = tmp_path / "inbound"
    bridge_dir = tmp_path / "storage_bridge"

    for name, sub in (
        ("uploads", output_dir / "uploads"),
        ("jobs", output_dir / "jobs"),
        ("confirmed", output_dir / "confirmed"),
        ("failed", bridge_dir / "failed"),
    ):
        sub.mkdir(parents=True)

    results = retention.purge_all(output_dir, inbound_dir, bridge_dir, now=time.time())
    assert set(results.keys()) == {"uploads", "jobs", "confirmed", "failed", "inbound_root"}
