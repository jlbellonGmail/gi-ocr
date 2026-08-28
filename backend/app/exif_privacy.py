"""Anonimización de metadata EXIF en imágenes subidas (JPEG, TIFF).

Elimina tags EXIF identificatorios (GPS, fabricante/modelo de dispositivo,
software, autor, etc.) antes de persistir en `output/uploads/`, preservando
intacto el tag `Orientation` (tag EXIF 274) del que depende la feature
`05-correccion-orientacion-exif` (pendiente de build, ya especificada).

Diseño (ver `docs/tecnica/seguridad-privacidad-documentos.md` para el
detalle completo, incluyendo por qué JPEG y TIFF usan estrategias
distintas):

- **JPEG**: el bloque EXIF (segmento APP1) es metadata *separada* de los
  datos de píxel — ningún tag EXIF es necesario para decodificar la
  imagen. Se usa Pillow (`Image.getexif()` + `Image.save(quality="keep")`)
  para reconstruir un objeto Exif que conserva únicamente `Orientation` y
  se re-escribe sin recomprimir los píxeles (`quality="keep"` reutiliza las
  tablas de cuantización originales).
- **TIFF**: el "IFD" de un TIFF mezcla tags estructurales imprescindibles
  para decodificar la imagen (`ImageWidth`, `StripOffsets`, `Compression`,
  etc.) con tags descriptivos identificatorios (`Make`, `Model`, `GPSInfo`,
  etc.) en el mismo directorio. Además, Pillow aplica automáticamente la
  corrección de orientación (transpone los píxeles y BORRA el tag
  `Orientation`) apenas se decodifica el archivo (`TiffImagePlugin.
  load_end` -> `ImageOps.exif_transpose`), lo que haría imposible preservar
  el tag `Orientation` sin modificar si se usara el mismo camino
  Image.open()+Image.save() que en JPEG. Por eso, para TIFF se edita
  directamente el IFD0 a nivel de bytes (sin decodificar píxeles): se
  eliminan solo las entradas de tags identificatorios de una lista
  explícita, dejando el resto del archivo (incluyendo todos los datos de
  píxel) byte a byte sin modificar.
"""

from __future__ import annotations

import io
import struct
from typing import Optional

from PIL import Image

ORIENTATION_TAG_ID = 274

# Tags EXIF/TIFF identificatorios eliminados del IFD0 de un TIFF (ver
# criterio 9 del spec). No incluye tags estructurales imprescindibles para
# decodificar la imagen (ImageWidth, StripOffsets, Compression, etc.), que
# se preservan siempre.
TIFF_IDENTIFYING_TAG_IDS: frozenset[int] = frozenset(
    {
        271,  # Make
        272,  # Model
        305,  # Software
        315,  # Artist
        33432,  # Copyright
        306,  # DateTime
        34853,  # GPSInfo (puntero a sub-IFD GPS completo)
        34665,  # ExifIFD (puntero a sub-IFD Exif; puede anidar más tags identificatorios)
        316,  # HostComputer
        42032,  # CameraOwnerName
        42033,  # BodySerialNumber
        42036,  # LensSerialNumber
        42016,  # ImageUniqueID
    }
)

_ANONYMIZABLE_FAMILIES = ("jpeg", "tiff")


def anonymize_upload_bytes(content: bytes, family: str) -> bytes:
    """Devuelve una copia de `content` sin tags EXIF identificatorios.

    `family`: familia de tipo ya detectada por `upload_validation.
    detect_signature` ('jpeg'|'png'|'tiff'|'pdf'). No-op (devuelve
    `content` sin cambios) para 'png'/'pdf' (no llevan bloque EXIF
    estándar) y para cualquier imagen sin metadata EXIF presente.

    Nunca lanza: cualquier error de lectura/escritura de metadata cae a un
    fallback seguro (ver funciones internas) y, en última instancia,
    devuelve el contenido original sin modificar antes que romper el
    upload completo.
    """
    if family not in _ANONYMIZABLE_FAMILIES:
        return content
    if family == "jpeg":
        return _anonymize_jpeg(content)
    return _anonymize_tiff(content)


# --- JPEG ---


def _anonymize_jpeg(content: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(content))
        exif = img.getexif()
    except Exception:
        return content

    if not exif or len(exif) == 0:
        # Sin bloque EXIF: no-op seguro, no introduce metadata nueva.
        return content

    orientation = exif.get(ORIENTATION_TAG_ID)

    try:
        for tag_id in list(exif.keys()):
            if tag_id != ORIENTATION_TAG_ID:
                del exif[tag_id]
        if orientation is not None:
            exif[ORIENTATION_TAG_ID] = orientation
        out = io.BytesIO()
        img.save(out, format=img.format or "JPEG", exif=exif, quality="keep")
        return out.getvalue()
    except Exception:
        return _anonymize_jpeg_fallback(content, orientation)


def _anonymize_jpeg_fallback(content: bytes, orientation: Optional[int]) -> bytes:
    """Fallback documentado (ver criterio 9 del spec y casos borde):

    - EXIF corrupto/parcialmente ilegible: el comportamiento seguro es
      eliminar el bloque EXIF entero en vez de fallar el upload.
    - `quality="keep"` no aplicable a este archivo concreto (limitación
      real de Pillow, p. ej. JPEG progresivo con tablas de cuantización no
      estándar): se usa `quality=95` explícito en vez de fallar.

    Si ninguno de los dos intentos funciona, devuelve el contenido
    original sin modificar (nunca rompe el upload).
    """
    try:
        img = Image.open(io.BytesIO(content))
        exif = Image.Exif()
        if orientation is not None:
            exif[ORIENTATION_TAG_ID] = orientation
        out = io.BytesIO()
        img.save(out, format=img.format or "JPEG", exif=exif, quality=95)
        return out.getvalue()
    except Exception:
        return content


# --- TIFF ---


def _anonymize_tiff(content: bytes) -> bytes:
    try:
        stripped = _strip_tiff_ifd0(content)
    except Exception:
        stripped = None

    if stripped is not None:
        return stripped

    # Fallback: estructura de IFD no parseable de forma segura -> intentar
    # eliminar el bloque EXIF completo por la vía de Pillow (acepta la
    # limitación de que Pillow aplica+descarta la orientación al
    # decodificar TIFF -- ver docstring del módulo), documentado como
    # último recurso antes de dejar el archivo sin tocar.
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
        out = io.BytesIO()
        img.save(out, format="TIFF")
        return out.getvalue()
    except Exception:
        return content


def _strip_tiff_ifd0(content: bytes) -> Optional[bytes]:
    """Elimina del IFD0 de un TIFF las entradas cuyo tag esté en
    `TIFF_IDENTIFYING_TAG_IDS`, sin decodificar ni re-codificar los datos de
    píxel: solo reescribe la tabla de directorio (agregando la versión
    reducida al final del archivo y actualizando el puntero del header),
    dejando todos los demás bytes (incluidos los de imagen) sin modificar.

    Devuelve `None` si el archivo no tiene una estructura TIFF reconocible
    o parseable de forma segura (el llamador debe aplicar el fallback).
    Devuelve `content` sin cambios si no hay ningún tag identificatorio
    presente (no-op seguro, incluye el caso "sin bloque EXIF").
    """
    if len(content) < 8:
        return None

    byte_order = content[0:2]
    if byte_order == b"II":
        endian = "<"
    elif byte_order == b"MM":
        endian = ">"
    else:
        return None

    magic = struct.unpack(endian + "H", content[2:4])[0]
    if magic != 42:
        return None  # BigTIFF u otra variante: fuera de alcance de esta feature.

    ifd_offset = struct.unpack(endian + "I", content[4:8])[0]
    if ifd_offset < 8 or ifd_offset + 2 > len(content):
        return None

    num_entries = struct.unpack(endian + "H", content[ifd_offset : ifd_offset + 2])[0]
    entries = []
    for i in range(num_entries):
        entry_offset = ifd_offset + 2 + i * 12
        if entry_offset + 12 > len(content):
            return None
        tag, typ, count = struct.unpack(endian + "HHI", content[entry_offset : entry_offset + 8])
        value_bytes = content[entry_offset + 8 : entry_offset + 12]
        entries.append((tag, typ, count, value_bytes))

    next_ifd_pos = ifd_offset + 2 + num_entries * 12
    if next_ifd_pos + 4 > len(content):
        return None
    next_ifd_offset = struct.unpack(endian + "I", content[next_ifd_pos : next_ifd_pos + 4])[0]

    kept_entries = [e for e in entries if e[0] not in TIFF_IDENTIFYING_TAG_IDS]
    if len(kept_entries) == len(entries):
        # No hay ningún tag identificatorio presente: no-op seguro.
        return content

    new_ifd = bytearray()
    new_ifd += struct.pack(endian + "H", len(kept_entries))
    for tag, typ, count, value_bytes in kept_entries:
        new_ifd += struct.pack(endian + "HHI", tag, typ, count) + value_bytes
    # Solo se procesa el IFD0 (primera página); un TIFF multi-página
    # conserva su cadena de IFDs siguientes intacta (ver docs/tecnica,
    # límite conocido de esta feature para TIFF multi-página).
    new_ifd += struct.pack(endian + "I", next_ifd_offset)

    out = bytearray(content)
    new_ifd_offset = len(out)
    out += bytes(new_ifd)
    out[4:8] = struct.pack(endian + "I", new_ifd_offset)
    return bytes(out)


__all__ = [
    "ORIENTATION_TAG_ID",
    "TIFF_IDENTIFYING_TAG_IDS",
    "anonymize_upload_bytes",
]
