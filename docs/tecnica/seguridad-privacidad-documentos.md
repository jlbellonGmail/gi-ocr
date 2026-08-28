# Seguridad y Privacidad de Documentos

Endurece el ciclo de vida de los archivos subidos/almacenados por el
sistema (`POST /api/v1/jobs`, `output/uploads/`, `output/jobs/`,
`output/confirmed/`, `inbound/` de raíz, `storage_bridge/{inbound,ready,
failed}/`) en seis dimensiones: validación de uploads (firma real +
Content-Type + tamaño), nombres de archivo aleatorios, permisos de
filesystem restrictivos, retención/purga configurable, redacción de datos
sensibles en errores expuestos por la API, y anonimización de metadata
EXIF. Ver `runs/14-seguridad-privacidad-documentos/spec.md` para el spec
aprobado completo y el detalle de alcance excluido (cifrado en reposo,
auth/TLS, logging estructurado completo, purga de `storage_bridge/ready/`,
anonimización del contenido de negocio extraído por OCR).

## 1. Validación de uploads (`backend/app/upload_validation.py`)

### Tabla de firmas de archivo (magic bytes)

Tabla estática, sin dependencia nueva (los 4 tipos soportados tienen
cabeceras estables y bien documentadas):

| Familia | Firma(s) (prefijo de bytes)                    |
|---------|-------------------------------------------------|
| `jpeg`  | `FF D8 FF`                                       |
| `png`   | `89 50 4E 47 0D 0A 1A 0A`                         |
| `tiff`  | `49 49 2A 00` (little-endian) o `4D 4D 00 2A` (big-endian) |
| `pdf`   | `25 50 44 46 2D` (`%PDF-`)                        |

`upload_validation.detect_signature(content)` devuelve la familia
detectada o `None` si el contenido no corresponde a ninguna. Solo
inspecciona la cabecera: no garantiza que el resto del contenido esté
íntegro (un archivo con firma correcta y cuerpo truncado/corrupto pasa
esta validación — limitación aceptada explícitamente en el spec, no es
un escaneo de integridad completo ni antivirus).

### Criterio de contraste Content-Type / magic bytes

`upload_validation.validate_upload_content(filename, content, content_type)`
aplica, en orden:

1. **Vacío** (`len(content) == 0`) → rechazo `empty_file` (400), antes de
   intentar leer firma.
2. **Tamaño** > `max_upload_bytes()` → rechazo `file_too_large` (413).
3. **Firma** no reconocida entre los 4 tipos soportados → rechazo
   `signature_mismatch` (415), **incluso si la extensión declarada está
   en `ALLOWED_EXTS`** (caso: `.txt` renombrado a `.jpg`).
4. **Content-Type declarado** vs. familia detectada: si el `Content-Type`
   es `None`, cadena vacía o `application/octet-stream` (genérico), **no
   se considera** — el sistema confía únicamente en la firma real. Para
   cualquier otro valor, se mapea a una familia esperada
   (`CONTENT_TYPE_FAMILY`) y se compara contra la familia detectada; si no
   coinciden (o el valor declarado no mapea a ninguna familia conocida),
   rechazo `content_type_mismatch` (415).

Este orden importa: el archivo nunca se escribe a disco antes de pasar
las 4 validaciones (`main._save_upload` lee todo el contenido a memoria,
valida, y solo entonces escribe en `output/uploads/`) — un intento
rechazado no deja rastro en `output/uploads/`.

**Caso borde documentado — Content-Type ausente/genérico para `.tif`/
`.tiff`:** los navegadores suelen reportar `Content-Type` vacío para TIFF
(`f.type === ''` en el objeto `File` del input HTML), y
`frontend/src/app.js` lo reenvía tal cual sin fijarlo manualmente. Tratar
esa ausencia como mismatch produciría falsos positivos de rechazo sobre
cargas legítimas — por eso el paso 4 se salta explícitamente para
Content-Type ausente/genérico.

**Motivo expuesto:** cada rechazo devuelve
`HTTPException(status_code, detail={"reason": ..., "message": ...})`. El
campo `reason` es estable (`empty_file`, `file_too_large`,
`signature_mismatch`, `content_type_mismatch`, o `400`/extensión no
soportada del check previo en `main._validate_upload`, sin cambios).

**Límite conocido (no cubierto por esta feature):** la firma detectada no
se contrasta contra la *extensión* declarada de forma independiente del
Content-Type — un archivo con firma real de un tipo soportado distinto al
implícito por su extensión (p. ej. un PDF real subido como `.jpg`) pasa
esta validación mientras el Content-Type declarado (si está presente) sea
coherente con la firma real detectada. El criterio 1 del spec exige
rechazar únicamente firmas que no correspondan a **ninguno** de los 4
tipos soportados, no una inconsistencia extensión-vs-firma entre tipos
soportados distintos; ampliar ese chequeo queda fuera de esta ronda.

### Tamaño máximo configurable

`GI_OCR_MAX_UPLOAD_BYTES` (entero, bytes). Si no está definida, está vacía
o no es un entero válido, aplica el default `30 * 1024 * 1024` (30 MB,
igual al valor previo hardcodeado). Un valor definido pero `<= 0` también
cae al default (evita una config inválida que rechace todo sin
explicación).

### Esquema de nombre aleatorio (criterio 5)

`upload_validation.random_upload_name(ext)` genera
`f"{secrets.token_hex(16)}{ext.lower()}"` — 128 bits de entropía
criptográficamente segura (`secrets`, no `random`), sin derivar nada del
nombre original ni de un timestamp. El nombre original sanitizado
(`sanitize_name`, sin cambios) sigue disponible como metadato del job
(`original_name`), pero deja de ser parte de la ruta de almacenamiento —
antes: `output/uploads/{timestamp}_{nombre_sanitizado}` (predecible,
podía contener PII como `DNI_Juan_Perez.jpg`); ahora:
`output/uploads/{32 hex chars}.jpg`.

## 2. Permisos de filesystem (`backend/app/fs_permissions.py`)

Target real de despliegue: contenedor Linux (ADR-009). `secure_file(path)`
aplica `os.chmod(path, 0o600)` (rw-------) y `secure_dir(path)` aplica
`os.chmod(path, 0o700)` (rwx------), ambos **solo en POSIX**
(`os.name == "posix"`); en Windows (entorno de desarrollo de este repo)
son no-ops explícitos que no rompen el arranque ni los tests. Ambas
funciones son best-effort: si el `chmod` falla (`OSError`), no relanzan —
nunca deben romper el flujo de escritura que las invoca.

Aplicado en los puntos de escritura reales de la app:

- `main._save_upload`: `secure_dir` sobre `output/uploads/`, `secure_file`
  sobre el archivo final.
- `job_store.JobStore.__init__`: `secure_dir` sobre `output/jobs/` y
  `output/confirmed/`. `save_original`/`save_confirmed`: `secure_file`
  sobre el `.json` escrito.
- `storage_bridge_writer.write_atomic_data_file`: `secure_dir` sobre
  `inbound/`, `ready/`, `failed/` de `storage_bridge/`; `secure_file`
  sobre el `.tmp` antes del `os.replace` y sobre el archivo final (o el
  `.tmp` movido a `failed/` si el `replace` falla).
- `inbound_watcher.InboundWatcher.__init__`: `secure_dir` sobre `inbound/`
  de raíz, `secure_file` sobre `.gitkeep`. Los documentos que llegan a
  `inbound/` los deposita un actor externo (no la app), por lo que no hay
  un punto de escritura propio de la app sobre esos archivos concretos —
  ver caso borde más abajo.

## 3. Retención / purga (`backend/app/retention.py`)

| Target                                  | Variable de entorno              | Default |
|------------------------------------------|-----------------------------------|---------|
| `output/uploads/`                         | `GI_OCR_UPLOAD_RETENTION_DAYS`    | 7       |
| `output/jobs/` + `output/confirmed/`      | `GI_OCR_JOB_RETENTION_DAYS`       | 90      |
| `storage_bridge/failed/`                  | `GI_OCR_FAILED_RETENTION_DAYS`    | 30      |
| `inbound/` de raíz                        | (mismo valor que `GI_OCR_UPLOAD_RETENTION_DAYS`) | 7 |

Un valor `<= 0` (incluyendo no numérico) deshabilita la purga de ese
target — nunca se interpreta como "purgar todo inmediatamente" (caso
borde explícito del spec, para que una config inválida no borre todo por
accidente).

`purge_directory(directory, retention_days, now=None, is_protected=None)`
elimina, **basado exclusivamente en `mtime`** (no en el formato del
nombre del archivo — soporta archivos con el esquema de nombre anterior
`{timestamp}_{nombre}`), los archivos de `directory` cuyo `mtime` supera
el umbral. Nunca borra `.gitkeep`/`README.md`/`.gitignore` (por nombre,
case-insensitive). Si se provee `is_protected(path) -> bool`, los
archivos para los que devuelve `True` tampoco se borran.

`purge_all(output_dir, root_inbound_dir, bridge_dir, store=None, now=None)`
orquesta los 5 targets (`uploads`, `jobs`, `confirmed`, `failed`,
`inbound_root`). **`storage_bridge/ready/` nunca aparece como target**:
el sistema legacy es responsable de consumirlo y rotarlo (ADR-001/
ADR-009); este sistema no tiene hoy ninguna señal de "el legacy ya lo
leyó" (sin ack, sin move-on-consume), así que una purga por antigüedad
ciega sobre `ready/` podría borrar un `.DATA` no leído todavía, rompiendo
el contrato de integración. Resolver eso requiere una señal de consumo,
que es alcance del ítem de roadmap `12-contrato-integracion-legacy-v2`.

**Protección de jobs `queued`/`processing`:** `output/jobs/` y
`output/confirmed/` están naturalmente a salvo sin necesidad de estado en
memoria — `JobQueue._process` solo invoca `store.save_original` (que
escribe `output/jobs/{job_id}.json`) en el camino de éxito, así que
cualquier archivo que exista ahí pertenece a un job que ya llegó a
`ready`/`confirmed`, nunca a uno `queued`/`processing`. Para
`output/uploads/`, en cambio, el archivo fuente existe desde el momento
del upload y sigue siendo `job["file_path"]` durante todo el ciclo de
vida — por eso `purge_all` acepta un `store: JobStore` opcional: si se
provee (proceso vivo del servidor), excluye los archivos de jobs
`queued`/`processing` activos vía `_active_upload_paths`. En modo
standalone (script sin acceso al estado en memoria de un servidor
corriendo) esa exclusión no aplica — aceptado como riesgo de baja
probabilidad porque el estado `queued`/`processing` es exclusivamente en
memoria (no persistido) y los umbrales de purga son de días, no de
segundos (mismo razonamiento que la concurrencia purga/descarga,
documentada como riesgo aceptado en el spec).

**Invocación:** `python -m backend.app.retention` (CLI standalone) o
`from backend.app.retention import purge_all` desde una tarea periódica
externa (cron/systemd timer del contenedor de despliegue — ADR-009 no
define un scheduler propio; queda a criterio del operador, igual que TLS
o auth). No se agrega un scheduler propio dentro del proceso ni un
endpoint HTTP: el criterio de aceptación pide un mecanismo "invocable",
no una automatización dentro del proceso.

## 4. Redacción de datos sensibles (`backend/app/redaction.py`)

`redact_message(message)` reemplaza cualquier ruta absoluta detectada
(POSIX `/algo/algo`, Windows `C:\algo\algo` / `C:/algo/algo`, o UNC
`\\server\share\algo`) por el nombre base (`Path(...).name`) del
archivo/carpeta referenciado, dejando el resto del texto intacto.
`redact_exception(exc)` es el atajo `redact_message(str(exc))`.

Ejemplos:

```python
>>> redact_message("Archivo no encontrado: /srv/gi-ocr/output/uploads/a1b2c3d4.jpg")
'Archivo no encontrado: a1b2c3d4.jpg'
>>> redact_message(r"Error en C:\Users\op\AppData\Local\Temp\tmpXYZ\doc.pdf")
'Error en doc.pdf'
>>> redact_message("Extensión no soportada: .exe")
'Extensión no soportada: .exe'
```

**Aplicado en:** `job_queue.JobQueue._process`, en el `except` que marca
un job como `failed` — `job["error"]` (expuesto vía
`GET /api/v1/jobs/{job_id}`) y el payload de la notificación SSE
(`/api/v1/stream`) usan `redact_exception(e)` en vez de `str(e)`.

**Por qué solo ese punto (alcance deliberado):** el repo no tiene hoy
ningún logging estructurado (`grep` de `logging|logger\.|print\(` sobre
`backend/app/` no devuelve resultados; eso es el ítem de roadmap
`13-observabilidad-operacion`, pendiente). `JobQueue._process` es el
único lugar real donde una excepción cruda del servidor llega hoy hasta
la API. El helper queda diseñado para ser reutilizable por esa feature
futura sin tener que re-decidir la política de qué es sensible.

**Límite documentado — jobs `failed` no se persisten a disco:**
`store.save_original` solo se invoca en el camino de éxito de
`_process` (dentro del `try`); el camino `except` únicamente actualiza el
`JobStore` en memoria vía `store.put(job)`. Por lo tanto, la redacción
solo puede verificarse hoy sobre `job["error"]` vía
`GET /api/v1/jobs/{job_id}` (el `JobStore` en memoria) — no existe un
`output/jobs/{job_id}.json` que verificar para el caso de falla, porque
esta feature no cambia ese comportamiento (fuera de su alcance declarado).

## 5. Anonimización de metadata EXIF (`backend/app/exif_privacy.py`)

Aplica a JPEG y TIFF (los únicos de los 4 tipos soportados con bloque
EXIF estándar; PNG y PDF son no-op). Se ejecuta en `main._save_upload`
**antes** de escribir a `output/uploads/`, sobre los bytes ya validados
(post `validate_upload_content`).

**Tags eliminados:** para JPEG, se elimina el bloque EXIF completo
**excepto** el tag `Orientation` (274) — ningún tag EXIF es necesario
para decodificar un JPEG (la información estructural vive en sus propios
marcadores SOF/DQT/DHT, separados del segmento EXIF APP1), así que no
hace falta una lista de tags "seguros de eliminar": todo lo que no sea
`Orientation` se descarta, incluyendo `GPSInfo` completo (vía el puntero
al sub-IFD, tag 34853), `Make` (271), `Model` (272), `Software` (305),
`Artist` (315), `Copyright` (33432), `DateTime`/`DateTimeOriginal` y el
puntero al sub-IFD `ExifIFD` (34665, que de estar presente arrastra
consigo cualquier tag anidado adicional).

Para TIFF, el IFD0 mezcla tags estructurales imprescindibles para
decodificar la imagen (`ImageWidth`, `ImageLength`, `Compression`,
`StripOffsets`, `StripByteCounts`, `PhotometricInterpretation`, etc.) con
tags descriptivos identificatorios en el mismo directorio — por eso se
usa una lista explícita de exclusión
(`exif_privacy.TIFF_IDENTIFYING_TAG_IDS`: `Make`, `Model`, `Software`,
`Artist`, `Copyright`, `DateTime`, `GPSInfo`, `ExifIFD`, `HostComputer`,
`CameraOwnerName`, `BodySerialNumber`, `LensSerialNumber`,
`ImageUniqueID`) en vez de un strip total, para no corromper el archivo.

**Por qué el tag `Orientation` se preserva intacto:**
`05-correccion-orientacion-exif` (`ROADMAP.md`, todavía `[ ]` pendiente,
ya especificado en `runs/05-correccion-orientacion-exif/spec.md`) depende
de leer ese tag para corregir rotación. Aunque `image_prep.
correct_orientation` hoy usa una heurística geométrica y no lee EXIF
todavía, esta feature no debe eliminar un tag del que una feature ya
especificada va a depender, sin importar el orden de implementación
relativo entre ambas.

### JPEG: por qué `quality="keep"` (sin recompresión con pérdida)

El archivo resultante en `output/uploads/` es exactamente el que
`JobQueue._process` pasa al pipeline OCR completo vía `job['file_path']`.
El `quality` por defecto de Pillow al re-guardar un JPEG es `75`,
sensiblemente menor que la calidad típica de una foto de celular
(85-95) — recomprimir sin cuidar este parámetro degradaría la imagen
fuente de la que depende toda la extracción de campos. Por eso, el
camino normal usa `Image.save(..., exif=exif_modificado, quality="keep")`
(reutiliza las tablas de cuantización JPEG originales del archivo fuente,
evitando una segunda pasada de compresión con pérdida sobre los píxeles).

**Fallback documentado:** si `quality="keep"` no es aplicable a un
archivo concreto (limitación real de Pillow, p. ej. un JPEG progresivo
con tablas de cuantización no estándar) o el bloque EXIF está corrupto/
parcialmente ilegible, `_anonymize_jpeg` cae a `_anonymize_jpeg_fallback`:
reintenta con `quality=95` explícito (documentado como excepción al
camino normal, no un valor elegido para el caso general). Si ese segundo
intento también falla, se devuelve el contenido original sin modificar —
nunca se rompe el upload completo por un problema de metadata.

**Por qué TIFF no tiene el mismo riesgo:** tal como esta feature
re-escribe TIFF (ver más abajo, sin habilitar compresión JPEG embebida),
no hay un parámetro de calidad con pérdida equivalente — el riesgo de
recompresión con pérdida es específico de JPEG.

### TIFF: por qué se edita el IFD a nivel de bytes, no vía `Image.open`+`Image.save`

Verificado empíricamente contra Pillow instalado (`Pillow==12.2.0`,
dentro del rango `Pillow>=10.2.0` de `requirements.txt`):
`TiffImagePlugin.load_end()` invoca automáticamente
`ImageOps.exif_transpose(self, in_place=True)` **y luego borra el tag
`Orientation` de `tag_v2`** apenas se decodifica un TIFF (en cualquier
`.load()`, incluido el que dispara `Image.save()` internamente). Esto
hace que el camino `Image.open(...).save(...)` (usado para JPEG) sea
**inviable** para TIFF: transpone físicamente los píxeles según la
orientación original y elimina el tag, exactamente lo contrario de lo que
exige el criterio 9 (`Orientation` preservado **intacto**, píxeles **sin
modificar**).

Por eso, para TIFF, `_anonymize_tiff`/`_strip_tiff_ifd0` edita
directamente el IFD0 a nivel de bytes, **sin decodificar los píxeles en
ningún momento**:

1. Parsea el header TIFF (byte order `II`/`MM`, magic `42`, offset del
   IFD0) y la tabla de entradas del IFD0 (12 bytes por entrada: tag, tipo,
   count, valor/offset) directamente con `struct`.
2. Descarta las entradas cuyo tag esté en `TIFF_IDENTIFYING_TAG_IDS`
   (incluye `Orientation` en la lista de **preservados**, no en la de
   eliminados).
3. Escribe la tabla de entradas resultante (más chica) **al final del
   archivo original**, sin tocar ningún byte previo — incluidos todos los
   datos de píxel, sin importar dónde estén ubicados en el archivo — y
   actualiza únicamente el puntero de offset del IFD0 en el header (bytes
   4-8) para que apunte a la nueva tabla.
4. Los bytes de la tabla de directorio original y de cualquier dato
   externo referenciado solo por las entradas eliminadas (p. ej. el
   sub-IFD de `GPSInfo`, o strings largos de `Make`/`Model`) quedan
   huérfanos en el archivo (bytes sin referencia activa, ignorados por
   cualquier lector TIFF que solo siga punteros vivos desde el IFD
   vigente) — no se recorta el archivo para simplificar la implementación
   y evitar reubicar offsets de datos de píxel.

Esto garantiza preservación **byte a byte** de los datos de imagen, ya
que la implementación nunca decodifica ni reescribe los píxeles (no hay
ninguna llamada a `Image.load()`/`Image.save()` en el camino principal
`_strip_tiff_ifd0`). El test correspondiente
(`test_exif_anonymization_tiff_preserves_size_and_mode`) verifica la
ausencia de degradación comparando `.size` y `.mode` del archivo fuente
contra el resultante — la verificación suficiente para este formato,
tal como lo define el spec — y preservación exacta del tag
`Orientation` (no pasa nunca por el camino de `load_end()` que lo
transpondría/eliminaría).

**Fallback (estructura no parseable de forma segura):** si el header/IFD
no tiene una estructura TIFF reconocible (`II`/`MM` + magic `42`) o los
límites de las entradas exceden el tamaño del archivo, `_anonymize_tiff`
cae a un intento vía Pillow (`Image.open().load()` + `Image.save(format=
"TIFF")`, sin pasar `exif`) — acepta la limitación de que Pillow aplica y
descarta la orientación al decodificar (ver arriba), documentado como
último recurso: "eliminar el bloque EXIF entero en vez de fallar" (texto
literal del spec para este caso borde). Si ese intento también falla,
devuelve el contenido original sin modificar.

**Límite conocido — TIFF multi-página:** solo se procesa el IFD0 (primera
página); un TIFF multi-página conserva su cadena de IFDs siguientes
intacta (el puntero "next IFD" se copia sin modificar), por lo que
páginas subsiguientes no pierden sus tags identificatorios propios. Fuera
de los fixtures de test de esta feature (imágenes de una sola página),
documentado como límite conocido, no como omisión silenciosa.

**BigTIFF:** no soportado (magic distinto de `42`); `_strip_tiff_ifd0`
devuelve `None` y cae al fallback de Pillow descrito arriba.

### Casos borde de EXIF cubiertos

- Imagen sin bloque EXIF (PNG de captura de pantalla, JPEG/TIFF ya sin
  metadata): no-op seguro, no introduce metadata nueva (`if not exif:
  return content`, o para TIFF `len(kept_entries) == len(entries)` →
  `return content`).
- PDF: no aplica, `anonymize_upload_bytes` retorna inmediatamente para
  familias fuera de `("jpeg", "tiff")`.
- EXIF corrupto/parcialmente ilegible: fallback documentado arriba (JPEG:
  reintento con `quality=95`; TIFF: reintento vía Pillow sin `exif`);
  nunca falla el upload completo.
- Orden relativo con `05-correccion-orientacion-exif`: no importa en qué
  orden se implementen ambas features — esta feature garantiza que
  `Orientation` llega intacto a `output/uploads/`, que es el archivo que
  esa corrección futura va a leer.

## Alcance explícitamente excluido (sin cambios respecto al spec)

Cifrado en reposo, autenticación/autorización de usuarios, TLS/reverse
proxy, logging estructurado completo, versionado del contrato `.DATA`,
purga de `storage_bridge/ready/`, escaneo antivirus/malware de contenido,
rate limiting, y anonimización del contenido semántico extraído por OCR.
Ver `runs/14-seguridad-privacidad-documentos/spec.md`, sección
"Explícitamente NO incluye", para la justificación completa de cada
exclusión.
