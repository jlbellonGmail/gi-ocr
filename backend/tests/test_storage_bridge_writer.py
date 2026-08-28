"""Tests for atomic storage bridge .DATA writer."""

from datetime import datetime
import os
from pathlib import Path

import pytest

from backend.app.storage_bridge_writer import (
    build_data_content,
    build_data_filename,
    write_atomic_data_file,
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
        "importe;cliente;periodo",
        "100,00;045-987654;",
    ]
    assert "," not in content.splitlines()[0]


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
    existing_file.write_text("existing\ncontent\n", encoding="utf-8")

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