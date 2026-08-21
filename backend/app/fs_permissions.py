"""Permisos de filesystem restrictivos para directorios/archivos gestionados
por la app.

Target real de despliegue: contenedor Linux (ADR-009, Docker en
servidor/equipo propio del usuario) — por eso el enforcement real de estos
permisos ocurre en POSIX. En Windows (entorno de desarrollo local de este
repo) ambas funciones son un no-op documentado: no rompen el arranque ni
los tests, simplemente no aplican ninguna restricción (Windows no usa el
mismo modelo de permisos owner/group/other que POSIX; ver
`docs/tecnica/seguridad-privacidad-documentos.md`).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Union

_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR  # 0o600, rw-------
_DIR_MODE = stat.S_IRWXU  # 0o700, rwx------

IS_POSIX = os.name == "posix"

PathLike = Union[str, "Path"]


def secure_file(path: PathLike) -> None:
    """Restringe permisos de un archivo a lectura/escritura solo del dueño
    del proceso (0o600). No-op en Windows. No lanza si el archivo no existe
    o el chmod falla (best-effort, nunca debe romper el flujo de escritura
    que lo invoca)."""
    if not IS_POSIX:
        return
    try:
        os.chmod(path, _FILE_MODE)
    except OSError:
        pass


def secure_dir(path: PathLike) -> None:
    """Restringe permisos de un directorio a lectura/escritura/ejecución
    solo del dueño del proceso (0o700). No-op en Windows. No lanza si el
    directorio no existe o el chmod falla."""
    if not IS_POSIX:
        return
    try:
        os.chmod(path, _DIR_MODE)
    except OSError:
        pass


__all__ = ["IS_POSIX", "secure_file", "secure_dir"]
