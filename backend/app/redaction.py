"""Helper de redacción reutilizable para mensajes que puedan filtrar datos
sensibles del servidor o del cliente antes de exponerlos vía API o
persistirlos.

Alcance de esta feature (`14-seguridad-privacidad-documentos`): se aplica
como mínimo al único punto real donde hoy una excepción cruda llega a la
API (`JobQueue._process` -> `job["error"]`, ver `docs/tecnica/
seguridad-privacidad-documentos.md`). No construye un pipeline de logging
estructurado — eso es el ítem de roadmap `13-observabilidad-operacion`;
este helper existe para que esa feature futura pueda reutilizarlo sin
tener que re-decidir la política de qué es sensible.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# Ruta absoluta estilo POSIX (/algo/algo), Windows (C:\algo\algo,
# C:/algo/algo) o UNC (\\server\share\algo). Se detiene en el primer
# espacio o comilla para no engullir el resto de una frase en español.
_ABS_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\[^\s'\"]+\\|/)[^\s'\"]*")

_REDACTED_PLACEHOLDER = "[ruta_omitida]"


def redact_message(message: Optional[str]) -> str:
    """Reemplaza cualquier ruta absoluta del filesystem detectada en
    `message` por el nombre base del archivo/carpeta referenciado, sin la
    ruta completa del servidor. El resto del texto no se modifica.

    Ejemplos:
        >>> redact_message("Archivo no encontrado: /srv/gi-ocr/output/uploads/a1b2c3.jpg")
        'Archivo no encontrado: a1b2c3.jpg'
        >>> redact_message("Error en C:\\\\Users\\\\op\\\\AppData\\\\Local\\\\Temp\\\\tmpXYZ\\\\doc.pdf")
        'Error en doc.pdf'
        >>> redact_message("Extensión no soportada: .exe")
        'Extensión no soportada: .exe'
    """
    if not message:
        return message or ""

    def _replace(match: "re.Match[str]") -> str:
        raw = match.group(0)
        name = Path(raw).name
        return name or _REDACTED_PLACEHOLDER

    return _ABS_PATH_RE.sub(_replace, message)


def redact_exception(exc: BaseException) -> str:
    """Atajo: `redact_message(str(exc))`, para usar directo en un `except`."""
    return redact_message(str(exc))


__all__ = ["redact_message", "redact_exception"]
