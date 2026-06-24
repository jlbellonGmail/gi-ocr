from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

SEPARATOR = ";"

DEFAULT_BRIDGE_DIR = Path("storage_bridge")
DEFAULT_INBOUND_DIR = DEFAULT_BRIDGE_DIR / "inbound"
DEFAULT_READY_DIR = DEFAULT_BRIDGE_DIR / "ready"
DEFAULT_FAILED_DIR = DEFAULT_BRIDGE_DIR / "failed"


def normalize_service_name(service: str) -> str:
    normalized = service.strip().upper()

    if not normalized:
        raise ValueError("service must not be empty")

    invalid_chars = {"/", "\\", ":", "*", "?", '"', "<", ">", "|", ".", " "}
    if any(char in normalized for char in invalid_chars):
        raise ValueError(f"invalid service name for DATA filename: {service!r}")

    return normalized


def build_data_filename(service: str, timestamp: datetime) -> str:
    normalized_service = normalize_service_name(service)
    return f"{normalized_service}_{timestamp.strftime('%Y%m%d_%H%M%S')}.DATA"


def _validate_token(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} must not be empty")

    if SEPARATOR in value:
        raise ValueError(f"{name} must not contain semicolon separator")

    if "\n" in value or "\r" in value:
        raise ValueError(f"{name} must not contain line breaks")


def _normalize_value(field: str, value: object) -> str:
    if value is None:
        return ""

    normalized = str(value)

    if SEPARATOR in normalized:
        raise ValueError(f"value for field {field!r} must not contain semicolon separator")

    if "\n" in normalized or "\r" in normalized:
        raise ValueError(f"value for field {field!r} must not contain line breaks")

    return normalized


def build_data_content(fields: Sequence[str], values: Mapping[str, object]) -> str:
    field_names = [field.strip() for field in fields]

    if not field_names:
        raise ValueError("fields must not be empty")

    for field in field_names:
        _validate_token("field", field)

    header_line = SEPARATOR.join(field_names)
    values_line = SEPARATOR.join(_normalize_value(field, values.get(field)) for field in field_names)

    return f"{header_line}\n{values_line}\n"


def write_atomic_data_file(
    *,
    service: str,
    fields: Sequence[str],
    values: Mapping[str, object],
    timestamp: datetime | None = None,
    inbound_dir: str | Path = DEFAULT_INBOUND_DIR,
    ready_dir: str | Path = DEFAULT_READY_DIR,
    failed_dir: str | Path = DEFAULT_FAILED_DIR,
) -> Path:
    effective_timestamp = timestamp or datetime.now()
    filename = build_data_filename(service, effective_timestamp)
    content = build_data_content(fields, values)

    inbound_path = Path(inbound_dir)
    ready_path = Path(ready_dir)
    failed_path = Path(failed_dir)

    inbound_path.mkdir(parents=True, exist_ok=True)
    ready_path.mkdir(parents=True, exist_ok=True)
    failed_path.mkdir(parents=True, exist_ok=True)

    temp_file = inbound_path / f"{filename}.tmp"
    final_file = ready_path / filename
    failed_file = failed_path / f"{filename}.tmp"

    if final_file.exists():
        raise FileExistsError(f"ready DATA file already exists: {final_file}")

    with temp_file.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)

    try:
        os.replace(temp_file, final_file)
    except Exception:
        if temp_file.exists():
            os.replace(temp_file, failed_file)
        raise

    return final_file