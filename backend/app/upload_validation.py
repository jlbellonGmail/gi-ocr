"""Validación de seguridad de uploads: firma de archivo (magic bytes),
Content-Type declarado vs. contenido real, tamaño máximo configurable y
generación de nombre aleatorio no predecible.

Separado de `main.py` (capa HTTP) para mantener la lógica de validación
testeable de forma independiente del framework FastAPI. `main.py` sigue
siendo responsable de la validación de extensión (`ALLOWED_EXTS`, sin
cambios) y de traducir `UploadValidationError` a `HTTPException`.

Ver `docs/tecnica/seguridad-privacidad-documentos.md` para la tabla de
firmas completa, el criterio de contraste Content-Type/magic-bytes y el
esquema de nombre aleatorio elegido.
"""
from __future__ import annotations

import os
import secrets
from typing import Optional

DEFAULT_MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB, igual al valor previo hardcodeado.

# --- Tabla estática de firmas de archivo (magic bytes) ---
# Sin dependencia nueva: los 4 tipos soportados hoy tienen cabeceras
# estables y bien conocidas (ver "Riesgos/supuestos" del spec).
SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "tiff": (b"II*\x00", b"MM\x00*"),
    "pdf": (b"%PDF-",),
}

# Content-Type declarado -> familia de firma implícita.
CONTENT_TYPE_FAMILY: dict[str, str] = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/pjpeg": "jpeg",
    "image/png": "png",
    "image/tiff": "tiff",
    "image/tif": "tiff",
    "application/pdf": "pdf",
}

# Content-Type que NO se consideran una declaración real de tipo: el
# sistema confía únicamente en la firma detectada (ver caso borde .tif/.tiff
# del spec: los navegadores suelen reportar Content-Type vacío para TIFF).
GENERIC_CONTENT_TYPES = frozenset({"", "application/octet-stream"})


class UploadValidationError(Exception):
    """Error de validación de upload con motivo explícito y código HTTP sugerido.

    `reason` es un identificador corto y estable (usado en el cuerpo de la
    respuesta HTTP), no un mensaje para humanos.
    """

    def __init__(self, reason: str, message: str, status_code: int = 400):
        self.reason = reason
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def max_upload_bytes() -> int:
    """Tamaño máximo de upload, configurable vía `GI_OCR_MAX_UPLOAD_BYTES`.

    Si la variable no está definida, es vacía o no es un entero válido,
    aplica el default (30 MB, igual al valor previo hardcodeado). Un valor
    definido pero <= 0 también cae al default: no tiene sentido operativo
    un límite de tamaño nulo o negativo, y evita una config inválida que
    rechace todos los uploads sin explicación clara.
    """
    raw = os.environ.get("GI_OCR_MAX_UPLOAD_BYTES")
    if raw is None or not raw.strip():
        return DEFAULT_MAX_UPLOAD_BYTES
    try:
        value = int(raw.strip())
    except ValueError:
        return DEFAULT_MAX_UPLOAD_BYTES
    return value if value > 0 else DEFAULT_MAX_UPLOAD_BYTES


def detect_signature(content: bytes) -> Optional[str]:
    """Familia de tipo ('jpeg'|'png'|'tiff'|'pdf') detectada por magic bytes,
    o `None` si el contenido no corresponde a ninguna firma conocida.

    Solo inspecciona la cabecera: no garantiza que el resto del contenido
    esté íntegro (ver caso borde documentado en
    `docs/tecnica/seguridad-privacidad-documentos.md`).
    """
    for family, magics in SIGNATURES.items():
        for magic in magics:
            if content.startswith(magic):
                return family
    return None


def validate_upload_content(filename: str, content: bytes, content_type: Optional[str]) -> str:
    """Valida tamaño, contenido vacío, firma real y consistencia de
    Content-Type. Devuelve la familia de tipo detectada (`'jpeg'|'png'|
    'tiff'|'pdf'`) si la validación pasa. Lanza `UploadValidationError` con
    motivo explícito si falla.

    No valida extensión: eso sigue siendo responsabilidad de
    `main._validate_upload` (`ALLOWED_EXTS`, sin cambios de comportamiento).
    """
    if len(content) == 0:
        raise UploadValidationError("empty_file", "Archivo vacío (0 bytes)", 400)

    max_bytes = max_upload_bytes()
    if len(content) > max_bytes:
        raise UploadValidationError(
            "file_too_large",
            f"Archivo '{filename}' demasiado grande (máx {max_bytes} bytes)",
            413,
        )

    family = detect_signature(content)
    if family is None:
        raise UploadValidationError(
            "signature_mismatch",
            f"El contenido de '{filename}' no corresponde a ningún tipo soportado (JPEG/PNG/TIFF/PDF)",
            415,
        )

    declared = (content_type or "").strip().lower()
    if declared not in GENERIC_CONTENT_TYPES:
        declared_family = CONTENT_TYPE_FAMILY.get(declared)
        if declared_family != family:
            raise UploadValidationError(
                "content_type_mismatch",
                f"Content-Type declarado ('{content_type}') no coincide con el contenido real de '{filename}' (detectado: {family})",
                415,
            )

    return family


def random_upload_name(ext: str) -> str:
    """Nombre de archivo aleatorio no predecible para persistir en
    `output/uploads/`, con la extensión saneada (ya validada por
    `main._validate_upload`) como único componente derivado del original.

    128 bits de entropía (`secrets.token_hex(16)`, criptográficamente
    seguro) — no derivado del nombre del cliente ni de timestamp.
    """
    return f"{secrets.token_hex(16)}{ext.lower()}"


__all__ = [
    "DEFAULT_MAX_UPLOAD_BYTES",
    "SIGNATURES",
    "CONTENT_TYPE_FAMILY",
    "GENERIC_CONTENT_TYPES",
    "UploadValidationError",
    "max_upload_bytes",
    "detect_signature",
    "validate_upload_content",
    "random_upload_name",
]
