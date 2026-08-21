"""Purga/retención de archivos por antigüedad (mtime), configurable por
variables de entorno.

Targets y defaults (ver `docs/tecnica/seguridad-privacidad-documentos.md`
para el diseño completo, incluyendo por qué `storage_bridge/ready/` queda
explícitamente fuera de esta purga):

- `output/uploads/`: `GI_OCR_UPLOAD_RETENTION_DAYS`, default 7.
- `output/jobs/` + `output/confirmed/`: `GI_OCR_JOB_RETENTION_DAYS`, default 90.
- `storage_bridge/failed/`: `GI_OCR_FAILED_RETENTION_DAYS`, default 30.
- `inbound/` de raíz: mismo valor que `GI_OCR_UPLOAD_RETENTION_DAYS`.

Un valor de retención `<= 0` deshabilita la purga de ese target (no borra
"todo inmediatamente" — ver caso borde del spec). Nunca borra `.gitkeep` ni
`README.md`. Nunca borra el archivo fuente de un job `queued`/`processing`
cuando se le provee una referencia a `JobStore` (ver `purge_all`).

Invocable como script (`python -m backend.app.retention`, standalone, sin
acceso al estado en memoria de un servidor corriendo) o importable desde
una tarea periódica externa (cron/systemd timer del contenedor de
despliegue — ADR-009 no define un scheduler propio, queda a criterio del
operador). No agrega un scheduler propio ni un endpoint HTTP: el criterio
de aceptación pide "invocable", no "automatizado dentro del proceso".
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

_PROTECTED_NAMES = frozenset({".gitkeep", "readme.md", ".gitignore"})

_SECONDS_PER_DAY = 86400


def _retention_days(env_var: str, default: int) -> Optional[int]:
    """Días de retención desde la variable de entorno `env_var`, o
    `default` si no está definida/no es un entero válido. Devuelve `None`
    si el valor resultante es <= 0 (purga deshabilitada para ese target)."""
    raw = os.environ.get(env_var)
    if raw is None or not raw.strip():
        days = default
    else:
        try:
            days = int(raw.strip())
        except ValueError:
            days = default
    return days if days > 0 else None


def upload_retention_days() -> Optional[int]:
    return _retention_days("GI_OCR_UPLOAD_RETENTION_DAYS", 7)


def job_retention_days() -> Optional[int]:
    return _retention_days("GI_OCR_JOB_RETENTION_DAYS", 90)


def failed_retention_days() -> Optional[int]:
    return _retention_days("GI_OCR_FAILED_RETENTION_DAYS", 30)


def inbound_root_retention_days() -> Optional[int]:
    """Mismo valor que `GI_OCR_UPLOAD_RETENTION_DAYS` (ver spec, criterio 7:
    `inbound/` de raíz comparte umbral con `output/uploads/`)."""
    return upload_retention_days()


def _is_protected_name(name: str) -> bool:
    return name.lower() in _PROTECTED_NAMES


def purge_directory(
    directory: Path,
    retention_days: Optional[int],
    *,
    now: Optional[float] = None,
    is_protected: Optional[Callable[[Path], bool]] = None,
) -> List[Path]:
    """Elimina archivos de `directory` (no desciende a subdirectorios) cuyo
    `mtime` supera `retention_days`. Devuelve la lista de paths eliminados.

    No hace nada si `retention_days` es `None` (deshabilitado) o el
    directorio no existe. Nunca borra `.gitkeep`/`README.md`. Si se provee
    `is_protected`, los archivos para los que devuelva `True` tampoco se
    borran (independientemente de su antigüedad) — usado para no eliminar
    el archivo fuente de un job `queued`/`processing`.

    Basado exclusivamente en `mtime`, no en el formato del nombre del
    archivo (ver caso borde del spec sobre archivos con el esquema de
    nombre anterior `{timestamp}_{nombre}`).
    """
    removed: List[Path] = []
    if retention_days is None:
        return removed
    if not directory.exists():
        return removed

    effective_now = now if now is not None else time.time()
    threshold = effective_now - (retention_days * _SECONDS_PER_DAY)

    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if _is_protected_name(path.name):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= threshold:
            continue
        if is_protected is not None and is_protected(path):
            continue
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            continue
    return removed


def _active_upload_paths(store) -> set:
    """Paths (resueltos) de archivos fuente de jobs `queued`/`processing`,
    a partir de un `JobStore` en memoria de un servidor corriendo. Devuelve
    un set vacío si `store` es `None` (modo standalone: ver limitación
    documentada en `docs/tecnica/seguridad-privacidad-documentos.md`,
    aceptada porque el estado `queued`/`processing` es exclusivamente en
    memoria y los umbrales de purga son de días, no de segundos)."""
    active: set = set()
    if store is None:
        return active
    for job in store.all():
        if job.get("status") in ("queued", "processing"):
            fp = job.get("file_path")
            if not fp:
                continue
            try:
                active.add(Path(fp).resolve())
            except OSError:
                pass
    return active


def purge_all(
    output_dir: Path,
    root_inbound_dir: Path,
    bridge_dir: Path,
    *,
    store=None,
    now: Optional[float] = None,
) -> Dict[str, List[Path]]:
    """Ejecuta la purga sobre los 4 targets configurados del spec.

    - `output_dir`: carpeta `output/` (contiene `uploads/`, `jobs/`,
      `confirmed/`).
    - `root_inbound_dir`: carpeta `inbound/` de raíz (watcher).
    - `bridge_dir`: carpeta `storage_bridge/` (solo se purga `failed/`;
      `ready/` e `inbound/` del bridge NUNCA se tocan aquí — ver
      "Riesgos/supuestos" del spec).
    - `store`: `JobStore` opcional para no purgar el archivo fuente de un
      job `queued`/`processing` en `output/uploads/` (ver limitación del
      modo standalone en `_active_upload_paths`).

    Devuelve un dict `{target: [paths eliminados]}` para logging/reporte.
    """
    active_paths = _active_upload_paths(store)

    def _upload_protected(path: Path) -> bool:
        try:
            return path.resolve() in active_paths
        except OSError:
            return False

    return {
        "uploads": purge_directory(
            output_dir / "uploads",
            upload_retention_days(),
            now=now,
            is_protected=_upload_protected,
        ),
        "jobs": purge_directory(output_dir / "jobs", job_retention_days(), now=now),
        "confirmed": purge_directory(output_dir / "confirmed", job_retention_days(), now=now),
        "failed": purge_directory(bridge_dir / "failed", failed_retention_days(), now=now),
        "inbound_root": purge_directory(root_inbound_dir, inbound_root_retention_days(), now=now),
    }


def _default_paths() -> Dict[str, Path]:
    base_dir = Path(__file__).resolve().parents[2]
    return {
        "output_dir": base_dir / "output",
        "root_inbound_dir": base_dir / "inbound",
        "bridge_dir": base_dir / "storage_bridge",
    }


def main() -> None:  # pragma: no cover - entrypoint CLI, cubierto vía purge_all/purge_directory
    """Entrypoint CLI: `python -m backend.app.retention`.

    Modo standalone (sin `JobStore`): no protege archivos de jobs
    `queued`/`processing` en `output/uploads/` (ver docstring de
    `_active_upload_paths`). Pensado para invocarse desde una tarea
    periódica externa (cron/systemd timer) en el contenedor de despliegue.
    """
    paths = _default_paths()
    results = purge_all(paths["output_dir"], paths["root_inbound_dir"], paths["bridge_dir"])
    for target, removed in results.items():
        print(f"[retention] {target}: {len(removed)} archivo(s) eliminado(s)")
        for path in removed:
            print(f"  - {path}")


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = [
    "upload_retention_days",
    "job_retention_days",
    "failed_retention_days",
    "inbound_root_retention_days",
    "purge_directory",
    "purge_all",
    "main",
]
