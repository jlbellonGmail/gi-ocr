from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

from .fs_permissions import secure_dir, secure_file

SEPARATOR = ";"
CONTRACT_VERSION = 2

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

    return f"VERSION={CONTRACT_VERSION}\n{header_line}\n{values_line}\n"


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
    secure_dir(inbound_path)
    secure_dir(ready_path)
    secure_dir(failed_path)

    temp_file = inbound_path / f"{filename}.tmp"
    final_file = ready_path / filename
    failed_file = failed_path / f"{filename}.tmp"

    if final_file.exists():
        raise FileExistsError(f"ready DATA file already exists: {final_file}")

    with temp_file.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    secure_file(temp_file)

    try:
        os.replace(temp_file, final_file)
        secure_file(final_file)
    except Exception:
        if temp_file.exists():
            os.replace(temp_file, failed_file)
            secure_file(failed_file)
        raise

    return final_file


def write_confidence_file(
    *,
    service: str,
    field_confidence: Mapping[str, Mapping[str, object]],
    timestamp: datetime | None = None,
    ready_dir: str | Path = DEFAULT_READY_DIR,
) -> Path:
    """Escribe archivo compañero .CONFIDENCE.json con trazabilidad de confianza por campo.

    Feature 09-confianza-y-enrutamiento-hitl: persiste field_confidence junto al .DATA
    para auditoría completa en el sistema legacy.
    """
    effective_timestamp = timestamp or datetime.now()
    filename = build_data_filename(service, effective_timestamp)
    confidence_filename = filename.replace(".DATA", ".CONFIDENCE.json")

    ready_path = Path(ready_dir)
    ready_path.mkdir(parents=True, exist_ok=True)
    secure_dir(ready_path)

    confidence_file = ready_path / confidence_filename

    # Serializar field_confidence a JSON
    serializable_confidence = {field: {k: v for k, v in conf.items()} for field, conf in field_confidence.items()}
    payload = {
        "service": service,
        "timestamp": effective_timestamp.isoformat(),
        "field_confidence": serializable_confidence,
    }

    with confidence_file.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    secure_file(confidence_file)

    return confidence_file


def compute_data_hash(service: str, fields: Sequence[str], values: Mapping[str, object]) -> str:
    """Genera hash SHA-256 del contenido normalizado para detección de duplicados lógicos.

    Normaliza: servicio uppercase, campos ordenados según fields, valores normalizados.
    """
    normalized_service = normalize_service_name(service)
    field_names = [field.strip() for field in fields]
    header_line = SEPARATOR.join(field_names)
    values_line = SEPARATOR.join(_normalize_value(field, values.get(field)) for field in field_names)
    content = f"VERSION={CONTRACT_VERSION}\n{header_line}\n{values_line}\n"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _find_existing_by_hash(
    ready_dir: Path,
    target_hash: str,
) -> Path | None:
    """Escanea ready/ buscando un .DATA v2 con el mismo hash de contenido."""
    if not ready_dir.exists():
        return None
    for data_file in ready_dir.glob("*.DATA"):
        try:
            text = data_file.read_text(encoding="utf-8")
            if text.startswith(f"VERSION={CONTRACT_VERSION}\n"):
                file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if file_hash == target_hash:
                    return data_file
        except Exception:
            continue
    return None


def _write_error_record(
    *,
    service: str,
    timestamp: datetime,
    error: Exception,
    attempts: int,
    fields: Sequence[str],
    values: Mapping[str, object],
    failed_dir: Path,
) -> Path:
    """Registra error en failed/<timestamp>_<service>_error.json."""
    failed_dir.mkdir(parents=True, exist_ok=True)
    secure_dir(failed_dir)

    error_filename = f"{normalize_service_name(service)}_{timestamp.strftime('%Y%m%d_%H%M%S')}_error.json"
    error_file = failed_dir / error_filename

    payload = {
        "service": service,
        "timestamp": timestamp.isoformat(),
        "error": str(error),
        "error_type": type(error).__name__,
        "attempts": attempts,
        "fields": list(fields),
        "values_hash": compute_data_hash(service, fields, values),
    }

    with error_file.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    secure_file(error_file)

    return error_file


def write_atomic_data_file_with_retry(
    *,
    service: str,
    fields: Sequence[str],
    values: Mapping[str, object],
    timestamp: datetime | None = None,
    max_retries: int = 3,
    base_delay_ms: int = 100,
    inbound_dir: str | Path = DEFAULT_INBOUND_DIR,
    ready_dir: str | Path = DEFAULT_READY_DIR,
    failed_dir: str | Path = DEFAULT_FAILED_DIR,
) -> Path:
    """Escribe .DATA atómicamente con idempotencia por contenido y reintentos con backoff exponencial.

    Flujo:
    1. Calcula hash del contenido.
    2. Busca en ready/ archivo existente con mismo hash → si existe, lo retorna (idempotencia).
    3. Intenta escritura atómica (tmp → ready). Si final_file existe (colisión nombre), genera nuevo timestamp con sufijo secuencial.
    4. Ante fallo transitorio (IOError, PermissionError, atomic move failure), reintenta con backoff exponencial.
    5. Si agota reintentos, registra error en failed/ y lanza la última excepción.
    """
    effective_timestamp = timestamp or datetime.now()
    target_hash = compute_data_hash(service, fields, values)

    inbound_path = Path(inbound_dir)
    ready_path = Path(ready_dir)
    failed_path = Path(failed_dir)

    inbound_path.mkdir(parents=True, exist_ok=True)
    ready_path.mkdir(parents=True, exist_ok=True)
    failed_path.mkdir(parents=True, exist_ok=True)
    secure_dir(inbound_path)
    secure_dir(ready_path)
    secure_dir(failed_path)

    # Idempotencia por contenido: buscar duplicado lógico en ready/
    existing = _find_existing_by_hash(ready_path, target_hash)
    if existing:
        return existing

    attempt = 0
    delay_ms = base_delay_ms
    last_error: Exception | None = None

    while attempt <= max_retries:
        attempt += 1
        try:
            filename = build_data_filename(service, effective_timestamp)
            content = build_data_content(fields, values)

            temp_file = inbound_path / f"{filename}.tmp"
            final_file = ready_path / filename
            failed_file = failed_path / f"{filename}.tmp"

            # Colisión de nombre: si ya existe en ready/, ajustar timestamp con sufijo
            if final_file.exists():
                base_ts = effective_timestamp
                for seq in range(1, 1000):
                    seq_suffix = f"_{seq:03d}"
                    new_filename = filename.replace(".DATA", f"{seq_suffix}.DATA")
                    final_file = ready_path / new_filename
                    if not final_file.exists():
                        filename = new_filename
                        temp_file = inbound_path / f"{filename}.tmp"
                        failed_file = failed_path / f"{filename}.tmp"
                        break
                else:
                    raise RuntimeError("No se pudo generar nombre único tras 999 intentos")

            with temp_file.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            secure_file(temp_file)

            try:
                os.replace(temp_file, final_file)
                secure_file(final_file)
            except Exception as move_error:
                if temp_file.exists():
                    os.replace(temp_file, failed_file)
                    secure_file(failed_file)
                raise move_error

            # Escribir .CONFIDENCE.json compañero si hay field_confidence (opcional, caller decide)
            return final_file

        except (IOError, OSError, PermissionError, RuntimeError) as e:
            last_error = e
            if attempt > max_retries:
                break
            time.sleep(delay_ms / 1000.0)
            delay_ms *= 2

    # Agotados reintentos: registrar error en failed/
    final_timestamp = timestamp or datetime.now()
    _write_error_record(
        service=service,
        timestamp=final_timestamp,
        error=last_error,
        attempts=attempt,
        fields=fields,
        values=values,
        failed_dir=failed_path,
    )
    raise last_error


def reconcile_storage_bridge(
    confirmed_dir: str | Path,
    ready_dir: str | Path = DEFAULT_READY_DIR,
    output_dir: str | Path | None = None,
) -> dict:
    """Reconcilia estado interno (confirmed/) con storage_bridge/ready/.

    Returns:
        dict con claves: missing_in_ready, orphan_in_ready, content_mismatch, report_path
    """
    confirmed_path = Path(confirmed_dir)
    ready_path = Path(ready_dir)

    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = confirmed_path.parent / "reconciliation"
    output_path.mkdir(parents=True, exist_ok=True)
    secure_dir(output_path)

    # 1) Cargar todos los confirmados v2
    confirmed_by_job: dict[str, dict] = {}
    if confirmed_path.exists():
        for conf_file in confirmed_path.glob("*.confirmed.json"):
            try:
                data = json.loads(conf_file.read_text(encoding="utf-8"))
                if data.get("confirmation_metadata", {}).get("contract_version") == CONTRACT_VERSION:
                    job_id = data.get("job_id")
                    if job_id:
                        confirmed_by_job[job_id] = data
            except Exception:
                continue

    # 2) Cargar todos los .DATA v2 en ready/
    ready_by_key: dict[str, dict] = {}  # key: "service_timestamp"
    ready_by_hash: dict[str, Path] = {}
    if ready_path.exists():
        for data_file in ready_path.glob("*.DATA"):
            try:
                text = data_file.read_text(encoding="utf-8")
                if not text.startswith(f"VERSION={CONTRACT_VERSION}\n"):
                    continue
                lines = text.strip().split("\n")
                if len(lines) < 3:
                    continue
                header = lines[1]
                fields = header.split(SEPARATOR)
                # Reconstruir valores para hash
                values_line = lines[2]
                values = dict(zip(fields, values_line.split(SEPARATOR)))
                # Extraer service y timestamp del nombre
                stem = data_file.stem
                # Formato: SERVICE_YYYYMMDD_HHMMSS[.seq]
                parts = stem.split("_")
                if len(parts) >= 3:
                    service = parts[0]
                    ts_str = "_".join(parts[1:3])
                    key = f"{service}_{ts_str}"
                    file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    ready_by_key[key] = {
                        "path": data_file,
                        "service": service,
                        "timestamp": ts_str,
                        "hash": file_hash,
                        "fields": fields,
                        "values": values,
                    }
                    ready_by_hash[file_hash] = data_file
            except Exception:
                continue

    # 3) Comparar
    missing_in_ready = []
    content_mismatch = []
    matched_ready_keys = set()

    for job_id, conf_data in confirmed_by_job.items():
        so = conf_data.get("structured_output", {})
        service = so.get("service", "").upper()
        provider = so.get("provider", "").upper()
        source_ref = so.get("source_document_reference", "")
        # Intentar extraer timestamp del source_ref o confirmation_metadata
        confirmed_at = conf_data.get("confirmation_metadata", {}).get("confirmed_at", "")
        ts_key = None
        if confirmed_at:
            try:
                dt = datetime.fromisoformat(confirmed_at.replace("Z", "+00:00"))
                ts_key = dt.strftime("%Y%m%d_%H%M%S")
            except Exception:
                pass

        # Buscar en ready por clave service_timestamp
        found = False
        for ready_key, ready_info in ready_by_key.items():
            if ready_key.startswith(f"{service}_") and (ts_key is None or ready_key.endswith(ts_key)):
                # Verificar hash de contenido
                validated = so.get("validated_fields", {})
                target_hash = compute_data_hash(service, list(validated.keys()), validated)
                if ready_info["hash"] == target_hash:
                    matched_ready_keys.add(ready_key)
                    found = True
                    break
                else:
                    content_mismatch.append({
                        "job_id": job_id,
                        "service": service,
                        "ready_key": ready_key,
                        "expected_hash": target_hash,
                        "actual_hash": ready_info["hash"],
                    })
                    found = True
                    break
        if not found:
            missing_in_ready.append({
                "job_id": job_id,
                "service": service,
                "expected_timestamp": ts_key,
            })

    # 4) Orphans en ready: .DATA v2 sin confirmed correspondiente
    orphan_in_ready = []
    for ready_key, ready_info in ready_by_key.items():
        if ready_key not in matched_ready_keys:
            orphan_in_ready.append({
                "ready_key": ready_key,
                "service": ready_info["service"],
                "timestamp": ready_info["timestamp"],
                "path": str(ready_info["path"]),
            })

    # 5) Generar reporte
    report = {
        "generated_at": datetime.now().isoformat(),
        "contract_version": CONTRACT_VERSION,
        "missing_in_ready": missing_in_ready,
        "orphan_in_ready": orphan_in_ready,
        "content_mismatch": content_mismatch,
        "summary": {
            "total_confirmed_v2": len(confirmed_by_job),
            "total_ready_v2": len(ready_by_key),
            "missing_count": len(missing_in_ready),
            "orphan_count": len(orphan_in_ready),
            "mismatch_count": len(content_mismatch),
        },
    }

    report_filename = f"reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = output_path / report_filename
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    secure_file(report_path)

    report["report_path"] = str(report_path)
    return report


__all__ = [
    "normalize_service_name",
    "build_data_filename",
    "build_data_content",
    "compute_data_hash",
    "write_atomic_data_file",
    "write_atomic_data_file_with_retry",
    "write_confidence_file",
    "reconcile_storage_bridge",
]
