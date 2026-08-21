# Spec: Seguridad y Privacidad de Documentos

## Alcance

Endurecer el ciclo de vida de archivos subidos/almacenados por el sistema
(`POST /api/v1/jobs`, `output/uploads/`, `output/jobs/`, `output/confirmed/`,
`inbound/` de raíz, `storage_bridge/{inbound,ready,failed}/`) en las
siguientes dimensiones:

1. **Validación de uploads**: extensión (ya existe), Content-Type
   declarado, firma de archivo real (magic bytes) y tamaño máximo
   configurable, con rechazo claro (`HTTPException` con motivo explícito)
   y sin dejar rastro persistente del archivo inválido.
2. **Nombres de archivo**: los archivos subidos por el flujo web se
   persisten en `output/uploads/` con nombre aleatorio no predecible; el
   nombre original del cliente (sanitizado) se conserva solo como
   metadato del job, nunca como parte de la ruta de almacenamiento.
3. **Permisos de filesystem**: los archivos escritos por la app en
   `output/uploads/`, `output/jobs/`, `output/confirmed/`,
   `storage_bridge/{inbound,ready,failed}/` e `inbound/` de raíz se crean
   con permisos restrictivos (solo dueño) en filesystems POSIX — target de
   despliegue real según ADR-009 (contenedor Docker en servidor/equipo
   propio del usuario) —, sin romper el arranque en Windows (entorno de
   desarrollo).
4. **Retención**: política de purga automática configurable por variable
   de entorno para `output/uploads/`, `output/jobs/` + `output/confirmed/`,
   `storage_bridge/failed/` e `inbound/` de raíz, sin borrar jobs
   `queued`/`processing` y sin tocar `storage_bridge/ready/` (ver
   "Riesgos/supuestos").
5. **Redacción de datos sensibles**: helper de redacción reutilizable
   aplicado como mínimo al único punto actual donde una excepción cruda
   puede llegar a la API (`JobQueue._process` → `job["error"]`), que evita
   filtrar nombre de archivo original del cliente o rutas absolutas del
   filesystem del servidor.
6. **Anonimización de metadata EXIF**: las imágenes subidas que puedan
   portar bloque EXIF (JPEG, TIFF) se anonimizan al persistirse en
   `output/uploads/`, eliminando tags EXIF identificatorios (GPS,
   fabricante/modelo de dispositivo, software, autor) antes de escribir a
   disco, preservando intacto el tag `Orientation` (ver "Riesgos/supuestos"
   sobre por qué se preserva ese tag puntual y por qué se incluye este
   punto como criterio en vez de excluirlo), **sin degradar la calidad de
   la imagen JPEG resultante** (ver "Riesgos/supuestos" y criterio 9 sobre
   por qué esto es necesario y cómo se evita).

**Explícitamente NO incluye:**

- Cifrado en reposo de `output/`/`storage_bridge/` (no pedido en el ítem
  de roadmap, y el modelo de despliegue actual —ADR-009— no define un
  requisito de cifrado a nivel de disco).
- Autenticación/autorización de usuarios ni permisos por rol
  operador/revisor/admin — eso es el ítem de roadmap
  `11-auditoria-permisos-operador`, no éste. El sistema sigue siendo
  monousuario local/por-cliente, tal como está documentado hoy
  (ADR-009: "Autenticación, TLS/HTTPS o reverse proxy... se documenta
  como recomendación operativa, no se implementa").
- TLS/HTTPS o reverse proxy delante del contenedor (ADR-009, sin
  cambios).
- Logging estructurado / métricas / trazabilidad completa por job — eso
  es el ítem de roadmap `13-observabilidad-operacion`. Esta feature
  entrega únicamente el **helper de redacción** como utilidad reutilizable
  para que esa feature futura no tenga que re-decidir la política de qué
  es sensible; no construye el pipeline de logging estructurado en sí.
- Versionado formal del contrato `.DATA`/JSON confirmado, idempotencia,
  reintentos, reconciliación con el sistema externo — eso es el ítem
  `12-contrato-integracion-legacy-v2`.
- Purga/rotación automática de `storage_bridge/ready/` — sigue siendo
  responsabilidad del sistema legacy consumirla, tal como ya declara
  ADR-001/ADR-009 ("Backup/rotación automática de `storage_bridge/ready/`:
  sigue siendo responsabilidad del sistema legacy"). Ver "Riesgos/supuestos"
  para el detalle de por qué esta feature no lo reabre.
- Escaneo antivirus/malware de contenido de archivos más allá de
  extensión/Content-Type/firma de tipo — validar que un PDF/imagen tenga
  la firma correcta no es lo mismo que garantizar que esté libre de
  payloads maliciosos; queda fuera de esta ronda.
- Rate limiting / protección DoS sobre `POST /api/v1/jobs`.
- Anonimización del contenido semántico extraído por OCR (nombres, DNI,
  direcciones u otros datos dentro de los campos capturados/validados) —
  es el dato de negocio que el sistema existe para capturar; anonimizarlo
  rompería el propósito funcional del pipeline de extracción/validación.
  Esta feature cubre únicamente metadata técnica incidental embebida en
  el archivo original (EXIF), no el contenido de negocio extraído ni los
  campos persistidos en `output/jobs/`/`output/confirmed/`.
- Cambiar el motor OCR (ADR-006), el formato `.DATA`/`services.ini`
  (ADR-007) ni la separación OCR/extracción/validación/storage — esta
  feature no toca ninguna de esas piezas y no reabre esos ADR.

## Contexto

`backend/app/main.py` (`_validate_upload`, `_save_upload`) ya valida
extensión (`ALLOWED_EXTS`) y tamaño (`MAX_BYTES = 30MB`, hardcodeado, no
configurable), y `backend/app/job_store.sanitize_name` ya previene path
traversal en nombres de archivo. Lo que falta, verificado en el código
real:

- No hay validación de **Content-Type declarado vs. contenido real**, ni
  de **firma de archivo (magic bytes)** — un `.txt` renombrado a `.jpg`
  pasa la validación actual (`test_upload_rejects_bad_ext` solo prueba
  extensión no soportada, no contenido falsificado).
- `_save_upload` persiste el upload en `output/uploads/` con el nombre
  `{timestamp}_{nombre_sanitizado}` — predecible y conserva el nombre
  original del cliente en la ruta de almacenamiento (puede contener PII,
  ej. `DNI_Juan_Perez.jpg`).
- No hay ningún `os.chmod`/control de permisos en ninguna escritura de
  archivo del proyecto (`job_store.py`, `storage_bridge_writer.py`,
  `inbound_watcher.py`, `main.py`).
- No existe ningún mecanismo de purga/expiración: `output/uploads/`,
  `output/jobs/`, `output/confirmed/`, `storage_bridge/failed/` e
  `inbound/` de raíz crecen indefinidamente.
- No existe ningún framework de logging estructurado en `backend/app/`
  (`grep` de `logging|logger\.|print\(` sobre `backend/app/` no devuelve
  resultados). El único punto donde una excepción cruda queda expuesta vía
  API es `JobQueue._process`, que guarda `job["error"] = str(e)` — por
  ejemplo un `FileNotFoundError` puede incluir la ruta absoluta completa
  del archivo en el servidor, visible luego vía `GET /api/v1/jobs/{id}`.
  Confirmado en `backend/app/job_queue.py::_process`: `store.save_original`
  solo se invoca dentro del bloque `try` (camino de éxito); el bloque
  `except` (camino de job `failed`) solo hace `store.put(job)` en memoria
  y nunca escribe `output/jobs/{job_id}.json`.
- No existe hoy ningún manejo de metadata EXIF en el pipeline de subida.
  `grep` de `exif|Exif|EXIF` sobre `backend/app/` no devuelve resultados:
  ni `image_prep.py` ni `capture_pipeline.py` leen o eliminan ningún tag
  EXIF. La corrección de orientación actual (`image_prep.correct_orientation`)
  es puramente geométrica/heurística sobre el array de imagen ya
  decodificado, no usa metadata EXIF. El ítem `05-correccion-orientacion-exif`
  (`ROADMAP.md`, todavía `[ ]` pendiente) ya tiene spec propio
  (`runs/05-correccion-orientacion-exif/spec.md`) que especifica leer el
  tag EXIF `Orientation` como mecanismo de corrección — por lo tanto,
  aunque hoy el código no lo lea, existe una dependencia futura declarada
  sobre ese tag puntual. Consecuencia de seguridad real hoy: una foto de
  celular subida vía el flujo web conserva GPS y modelo de dispositivo
  embebidos en el archivo persistido en `output/uploads/`, sin que nada
  del pipeline actual lo toque.
- El despliegue real objetivo (ADR-009, ya resuelto) es Docker en un
  servidor o equipo propio del usuario, sin PaaS/orquestador, sin
  auth/TLS. Esta feature diseña permisos de filesystem para ese target
  (contenedor Linux), no para el entorno de desarrollo Windows del
  repositorio.
- `backend/requirements.txt` no incluye ninguna librería de detección de
  tipo de archivo por contenido (`python-magic`, `filetype`, etc.); los
  cuatro tipos soportados hoy (JPEG, PNG, TIFF, PDF) tienen firmas de
  cabecera bien conocidas y estables, verificables con una tabla estática
  en la propia app sin agregar una dependencia nueva. `requirements.txt`
  ya incluye `Pillow>=10.2.0`, suficiente para leer/reescribir tags EXIF
  (`Image.getexif()`/`Image.info["exif"]`) sin agregar dependencia nueva
  para el punto 6. Importante: el valor por defecto de `quality` que usa
  Pillow al re-guardar un JPEG con `Image.save()` es `75` — sensiblemente
  menor que la calidad típica de una foto de celular (85-95). Como el
  archivo resultante en `output/uploads/` (ya anonimizado) es el mismo
  que `JobQueue._process` pasa al pipeline OCR vía `job['file_path']`,
  re-guardar sin cuidar este parámetro degradaría la imagen fuente de la
  que depende toda la extracción de campos del sistema. Esto se resuelve
  explícitamente en el criterio 9 (ver también "Riesgos/supuestos").

## Criterios de aceptación

1. `POST /api/v1/jobs` rechaza (código 400/415, con motivo explícito en
   el cuerpo de la respuesta, p. ej. `signature_mismatch`) un archivo cuyo
   contenido (magic bytes) no corresponde a ninguno de los tipos
   soportados (JPEG, PNG, TIFF, PDF), incluso si su extensión está en
   `ALLOWED_EXTS`. Test: subir un archivo de texto plano renombrado a
   `.jpg` y confirmar rechazo, y que no queda ningún archivo nuevo en
   `output/uploads/` después del intento.
2. El rechazo actual por extensión no soportada sigue funcionando sin
   regresión (`test_upload_rejects_bad_ext` sigue en verde).
3. El tamaño máximo de upload es configurable por variable de entorno
   (p. ej. `GI_OCR_MAX_UPLOAD_BYTES`), con el valor por defecto igual al
   actual (30 MB) si la variable no está definida. Test: bajar el límite
   vía variable de entorno y confirmar que un archivo que hoy pasaría
   (menor a 30MB) es rechazado con 413 al superar el nuevo límite.
4. El `Content-Type` declarado en el `multipart/form-data` se contrasta
   contra la familia de tipo implícita en la firma de archivo detectada;
   una combinación inconsistente (p. ej. `Content-Type: image/jpeg` con
   bytes de cabecera de PDF) se rechaza con motivo explícito. Cuando el
   `Content-Type` declarado está ausente, vacío o es genérico
   (`application/octet-stream`), NO se considera mismatch: el sistema
   confía únicamente en la firma de archivo detectada (ver caso borde de
   `.tif`/`.tiff` en "Casos borde a contemplar"). Test: (a)
   `files={"files": ("x.jpg", <bytes con firma PDF>, "image/jpeg")}` →
   rechazo; (b) `files={"files": ("x.tif", <bytes con firma TIFF
   válida>, "")}` (Content-Type vacío) → aceptado, sin rechazo por
   mismatch.
5. Los archivos subidos por el flujo web se persisten en
   `output/uploads/` con un nombre generado aleatoriamente (no derivado
   del nombre del cliente ni de un patrón de timestamp+nombre de baja
   entropía). El nombre original sanitizado sigue disponible como
   metadato del job (`original_name`, ya expuesto hoy), pero no forma
   parte del componente de ruta escrito a disco. Test: subir dos archivos
   con el mismo nombre original y confirmar que los dos nombres de
   archivo resultantes en `output/uploads/` son distintos entre sí y no
   contienen el nombre sanitizado como substring.
6. Los archivos creados por la app en `output/uploads/`, `output/jobs/`,
   `output/confirmed/`, `storage_bridge/{inbound,ready,failed}/` e
   `inbound/` de raíz quedan con permisos restrictivos (lectura/escritura
   solo para el dueño del proceso) en filesystems POSIX; en Windows la
   restricción es un no-op documentado que no rompe la escritura ni los
   tests. Test (gateado a POSIX, `skipif` en Windows con motivo explícito,
   igual patrón que otros tests de este repo): crear un archivo a través
   del camino de escritura real de la app y verificar los bits de permiso
   resultantes.
7. Existe un mecanismo de purga/retención (invocable como script o tarea
   periódica) configurable por variables de entorno con estos targets y
   valores por defecto (ver "Riesgos/supuestos" sobre por qué estos
   números son una decisión de este spec, no un dato fijo del roadmap):
   - `output/uploads/`: `GI_OCR_UPLOAD_RETENTION_DAYS`, default `7`.
   - `output/jobs/` + `output/confirmed/`: `GI_OCR_JOB_RETENTION_DAYS`,
     default `90`.
   - `storage_bridge/failed/`: `GI_OCR_FAILED_RETENTION_DAYS`, default
     `30`.
   - `inbound/` de raíz: mismo valor que `GI_OCR_UPLOAD_RETENTION_DAYS`.
   La purga nunca borra `.gitkeep`/`README.md`, nunca borra el archivo
   fuente de un job cuyo estado en `JobStore`/`JobQueue` sea `queued` o
   `processing`, y nunca toca `storage_bridge/ready/` (excluido
   explícitamente, ver "Riesgos/supuestos"). Test: crear archivos con
   `mtime` simulado/retrocedido más allá y más acá del umbral configurado
   y confirmar que la purga elimina solo los que superan el umbral.
8. Se implementa un helper de redacción (p. ej.
   `backend/app/redaction.py` o ubicación equivalente que decida
   `builder-agent`) que reemplaza nombre de archivo original del cliente y
   rutas absolutas del filesystem del servidor por una forma no
   identificable (hash corto, placeholder o solo el nombre base sin ruta
   completa) al construir el mensaje de error persistido/expuesto por
   `JobQueue._process` (`job["error"]`). Test: forzar una falla cuyo
   mensaje de excepción original contenga una ruta absoluta con un marcador
   conocido (p. ej. una carpeta temporal con un nombre único) y verificar
   que el marcador/ruta absoluta completa no aparece en el `job["error"]`
   devuelto por `GET /api/v1/jobs/{job_id}`. Nota: `JobQueue._process` no
   persiste jobs `failed` a disco (`store.save_original` solo se invoca en
   el camino de éxito, dentro del bloque `try`; el bloque `except`
   únicamente actualiza el `JobStore` en memoria vía `store.put(job)`) —
   por lo tanto este test no verifica (ni puede verificar) ausencia del
   marcador en `output/jobs/{job_id}.json` para el caso de falla, porque
   ese archivo no se escribe en ese camino. Esta feature no cambia ese
   comportamiento (ver "Riesgos/supuestos").
9. Las imágenes subidas que puedan portar metadata EXIF (JPEG, TIFF —
   los únicos de los 4 tipos soportados con bloque EXIF estándar; PNG y
   PDF no lo llevan y no requieren este paso) se anonimizan al
   persistirse en `output/uploads/`: se eliminan del archivo final los
   tags EXIF identificatorios (`GPSInfo` completo, `Make`, `Model`,
   `Software`, `Artist`, `Copyright`, y cualquier otro tag EXIF no
   esencial para el procesamiento), preservando intacto y sin modificar
   el tag `Orientation` (tag EXIF 274), del cual depende
   `05-correccion-orientacion-exif` (`ROADMAP.md`, todavía `[ ]`
   pendiente, pero ya especificado en `runs/05-correccion-orientacion-exif/spec.md`
   como lectura de ese tag).

   **Sin degradación de calidad de imagen (JPEG):** dado que el archivo
   resultante en `output/uploads/` (ya anonimizado) es el mismo que
   `JobQueue._process` pasa al pipeline OCR completo vía
   `job['file_path']`, el mecanismo de stripping de EXIF para JPEG NO
   debe recomprimir con pérdida el contenido de píxeles. La forma
   requerida de lograrlo es guardar con el parámetro `quality="keep"` de
   Pillow (reutiliza las tablas de cuantización JPEG originales del
   archivo fuente al re-escribir, evitando una recompresión con pérdida
   adicional), o, si `builder-agent` encuentra una limitación técnica
   real que impida usar `quality="keep"` para algún caso, fijar un
   `quality` explícito `>= 95` con la limitación documentada y justificada
   en `docs/tecnica/seguridad-privacidad-documentos.md`. TIFF, tal como
   Pillow lo re-escribe por defecto en esta feature (sin habilitar
   compresión JPEG embebida), no tiene un parámetro de calidad con
   pérdida equivalente, por lo que este riesgo específico aplica a JPEG.

   Test (JPEG): subir una imagen JPEG fixture con EXIF `GPSInfo`, `Make`,
   `Model` y `Orientation=6` seteados explícitamente; leer el archivo
   resultante en `output/uploads/` (p. ej. con `PIL.Image.getexif()`) y
   confirmar que `GPSInfo`/`Make`/`Model` ya no están presentes, mientras
   que `Orientation` sigue siendo `6`. Adicionalmente, verificar ausencia
   de recompresión con pérdida comparando las tablas de cuantización JPEG
   del archivo fuente y del archivo resultante (`PIL.Image.open(path).quantization`
   debe ser idéntico antes y después de la anonimización) — no alcanza con
   verificar solo la ausencia de tags EXIF.

   Test (TIFF): mismo caso con una imagen TIFF fixture con EXIF
   `GPSInfo`, `Make`, `Model` y `Orientation=6` seteados explícitamente
   (Pillow soporta `Image.getexif()` sobre TIFF de forma equivalente a
   JPEG desde una versión anterior a la ya fijada en `requirements.txt`,
   `Pillow>=10.2.0`); confirmar la misma eliminación selectiva de tags y
   la preservación de `Orientation`. Como TIFF no tiene el riesgo de
   recompresión con pérdida de JPEG, la verificación de ausencia de
   degradación para este formato se hace comparando dimensiones (`size`)
   y modo de color (`mode`) del archivo fuente contra el resultante, que
   deben ser idénticos.
10. `backend/tests/test_security.py` (o un módulo nuevo dedicado, p. ej.
    `backend/tests/test_upload_security.py`) cubre los criterios 1, 3, 4,
    5, 8 y 9 (incluyendo ambas ramas JPEG y TIFF del criterio 9) con tests
    nuevos, y la suite completa (`pytest -v` sobre `backend/tests/` +
    `tests/`) sigue en verde sin regresiones.
11. Debe existir `docs/tecnica/seguridad-privacidad-documentos.md`, no
    vacío, con: la tabla de firmas de archivo usada, el criterio de
    contraste Content-Type/magic-bytes (incluyendo el caso de
    Content-Type ausente/genérico), el esquema de nombre aleatorio
    elegido, el mecanismo de permisos por plataforma (POSIX vs. Windows),
    el diseño del mecanismo de purga (targets, defaults, exclusiones), el
    diseño del helper de redacción con ejemplos de entrada/salida, y el
    diseño de la anonimización EXIF (tags eliminados, tag `Orientation`
    preservado y por qué, formatos afectados, la decisión de
    `quality="keep"`/no-recompresión para JPEG y por qué no aplica el
    mismo riesgo a TIFF).
12. Debe existir `docs/usuario/seguridad-privacidad-documentos.md`, no
    vacío, con el propósito de estos controles (qué protegen y por qué),
    las variables de entorno configurables con sus valores por defecto, y
    al menos un ejemplo de uso HTTP real (request + response) mostrando
    un rechazo de upload inválido, p. ej. `POST /api/v1/jobs` con un
    archivo con firma falsificada → respuesta 400/415 con el motivo.
13. Debe existir `runs/14-seguridad-privacidad-documentos/decision.md`
    (creado por `builder-agent`), y enlaces exactos hacia
    `seguridad-privacidad-documentos.md` en `docs/tecnica/index.md` y
    `docs/usuario/index.md`, con el mismo título en ambos índices
    (recomendado: **"Seguridad y Privacidad de Documentos"**, vía
    `scripts/update-doc-indexes.ps1 14-seguridad-privacidad-documentos
    "Seguridad y Privacidad de Documentos"`).
14. `Assert-FeatureContract` (`scripts/feature-contract.ps1`) pasa para
    `14-seguridad-privacidad-documentos` antes de marcar `ROADMAP.md`
    como `[-] READY_FOR_PR`.

## Casos borde a contemplar

- Archivo de 0 bytes: debe rechazarse antes de intentar leer firma
  (mensaje de error distinto a `signature_mismatch`, p. ej. `empty_file`).
- Archivo con extensión/Content-Type correctos pero cabecera de firma
  correcta y resto del contenido corrupto/truncado: la validación de
  magic bytes solo garantiza el tipo de archivo por cabecera, no la
  integridad completa del contenido — limitación aceptada, documentada
  explícitamente en `docs/tecnica/`, no un criterio de esta feature.
- `Content-Type` ausente, vacío o genérico (`application/octet-stream`)
  en el `multipart/form-data`: caso real y frecuente para `.tif`/`.tiff`,
  porque los navegadores suelen no poder inferir ese MIME type (el objeto
  `File` de `<input type=file>` puede reportar `f.type === ''`, y
  `frontend/src/app.js` lo reenvía tal cual vía `FormData`, sin fijar
  Content-Type manualmente). El sistema NO debe tratar esta
  ausencia/genericidad como mismatch contra la firma detectada — debe
  confiar únicamente en la firma de archivo real para aceptar/rechazar,
  evitando un falso positivo de rechazo sobre una carga legítima de TIFF.
- Lote multi-archivo (`POST /api/v1/jobs` acepta `List[UploadFile]`) con
  un archivo inválido entre varios válidos: se preserva el comportamiento
  actual (aborta el lote completo en el primer archivo inválido, ver
  `backend/app/main.py::create_jobs`), no se cambia a "aceptar parcial" en
  esta feature — pero el motivo de rechazo debe identificar cuál archivo
  falló y por qué.
- Archivos ya existentes en `output/uploads/` con el esquema de nombre
  anterior (`{timestamp}_{nombre}`) al momento de desplegar esta feature:
  el mecanismo de purga debe poder procesarlos igual (basado en `mtime`
  del archivo, no en el formato del nombre), sin fallar por nombre
  inesperado.
- Job en estado `queued`/`processing` cuyo archivo fuente cae dentro del
  umbral de purga por antigüedad del propio job (caso extremo, poco
  realista dado que la purga opera en escala de días y el procesamiento
  en segundos): la purga debe consultar el estado actual del job antes de
  borrar y nunca eliminar el archivo fuente de un job no terminado.
- Entorno Windows de desarrollo: los tests de permisos POSIX deben
  saltarse con motivo explícito (mismo patrón de skip ya usado en este
  repo para muestras privadas), nunca fallar ni reportar `PASS` sin
  correr.
- `inbound/` de raíz (watcher) vs. `storage_bridge/inbound/` (bridge): son
  carpetas distintas (ya documentado en ADR-009/Contexto de
  `03-empaquetado-despliegue`); esta feature aplica retención/permisos a
  ambas por separado, pero **no** aplica el esquema de nombre aleatorio a
  los archivos que caen en `inbound/` de raíz vía `InboundWatcher`, porque
  su lógica de dedupe (`InboundWatcher._seen`) está indexada por nombre +
  hash de contenido y renombrar rompería esa lógica sin rediseñarla — se
  documenta como límite de esta feature, no como omisión silenciosa.
- Variable de entorno de retención en `0` o negativa: debe tratarse como
  "purga deshabilitada" (no como "purgar todo inmediatamente"), para
  evitar que una config inválida borre todo por accidente.
- Concurrencia entre la purga y una descarga (`GET
  /api/v1/jobs/{id}/download`) en curso sobre un archivo justo en el
  límite del umbral: aceptar la carrera como riesgo de baja probabilidad
  dado que los umbrales son de días, no de segundos; no se implementa
  locking adicional en esta feature.
- Imagen sin bloque EXIF en absoluto (PNG generado por captura de
  pantalla o editor, o JPEG ya sin metadata): el paso de anonimización
  EXIF no debe fallar ni introducir metadata nueva — debe ser un no-op
  seguro.
- PDF subido: no lleva EXIF de imagen estándar; el paso de anonimización
  EXIF no aplica y no debe intentar parsear/leer EXIF de un PDF.
- Imagen con bloque EXIF corrupto o parcialmente ilegible: el intento de
  anonimización no debe hacer fallar el upload completo; el
  comportamiento de fallback seguro es eliminar el bloque EXIF entero en
  vez de fallar, documentado explícitamente en `docs/tecnica/`.
- Imagen ya procesada por una corrección de orientación EXIF (si
  `05-correccion-orientacion-exif` se implementa antes o después que esta
  feature, en cualquier orden): el paso de anonimización debe correr sin
  importar el orden relativo, siempre y cuando se preserve el tag
  `Orientation` intacto en el archivo persistido en `output/uploads/`, que
  es el que consumirá esa corrección.
- Imagen JPEG cuyo `quality="keep"` no pueda aplicarse por alguna
  limitación técnica real de Pillow sobre el archivo fuente concreto
  (caso poco frecuente, p. ej. JPEG progresivo con tablas de cuantización
  no estándar): debe existir un fallback explícito y documentado (fijar
  `quality` alto, p. ej. `95`, en vez de fallar el upload completo), y
  ese fallback debe quedar registrado en `docs/tecnica/` como excepción
  al camino normal, no como comportamiento silencioso.

## Riesgos / supuestos

- **Ambigüedad resuelta — números de retención por defecto:** el ítem de
  roadmap pide "retención" sin especificar plazos. Elegí `7` días para
  `output/uploads/` (contenido más sensible: imágenes originales de
  comprobantes), `90` días para `output/jobs/`+`output/confirmed/`
  (registro operativo ya revisado/confirmado, útil para auditoría de más
  plazo) y `30` días para `storage_bridge/failed/` (archivos ya fallidos,
  sin valor operativo pasado cierto punto). Son valores configurables por
  variable de entorno específicamente para que el reviewer u operador
  real los pueda objetar/ajustar sin tocar código.
- **Ambigüedad resuelta — `storage_bridge/ready/` queda fuera de la
  purga automática de esta feature:** el roadmap pide "retención" para
  "almacenamiento" en general, lo que podría interpretarse como
  incluyendo `ready/`. Decidí excluirlo explícitamente porque ADR-001/
  ADR-009 ya establecen que el sistema legacy es responsable de consumir
  y rotar `ready/`, y este sistema no tiene hoy ninguna señal de "el
  legacy ya lo consumió" (no hay ack, no hay mecanismo de move-on-consume
  documentado) — implementar una purga por antigüedad ciega sobre
  `ready/` podría borrar un `.DATA` que el sistema externo todavía no leyó,
  rompiendo el contrato de integración (ADR-001). Resolver eso
  correctamente requiere una señal de consumo, que es del resorte del
  ítem `12-contrato-integracion-legacy-v2`, no de este. El reviewer puede
  objetar esta exclusión si considera que hay evidencia de que el legacy
  sí señaliza consumo de algún modo no documentado en este repo.
- **Ambigüedad resuelta — alcance del helper de redacción:** el roadmap
  menciona "redacción de datos sensibles en logs", pero el repo no tiene
  hoy ningún logging estructurado (`13-observabilidad-operacion` sigue
  pendiente). Decidí entregar un helper de redacción reutilizable y
  aplicarlo al único punto real donde hoy se filtra una excepción cruda
  hacia la API (`JobQueue._process`), en vez de construir logging
  estructurado completo — eso evita que esta feature invada el alcance
  del ítem 13 sin resolverlo del todo. El reviewer puede objetar si
  considera que "redacción en logs" exige más cobertura que ese único
  punto actual.
- **Corrección explícita (atendiendo audit-1) — jobs `failed` no se
  persisten a disco, y esta feature no lo cambia:** verificado en
  `job_queue.py::_process` que `store.save_original` solo se invoca en el
  camino de éxito. Decidí no agregar esa persistencia como parte de esta
  feature porque no fue pedida por el roadmap y ampliaría el alcance sin
  justificación clara; en consecuencia, el criterio de redacción (8) se
  verifica exclusivamente vía `GET /api/v1/jobs/{job_id}` (el `JobStore`
  en memoria), que es el único canal real por el que hoy se expone
  `job["error"]`. Si en el futuro se decide persistir jobs failed a
  disco, la verificación de redacción sobre ese archivo debe agregarse
  como criterio explícito de esa feature futura, no asumirse aquí.
- **Ambigüedad resuelta (atendiendo audit-1) — "anonimización" del
  roadmap se interpreta como stripping de metadata EXIF identificatoria
  incidental (GPS, fabricante/modelo de dispositivo), no como
  anonimización del contenido/PII de negocio extraído por OCR:** decidí
  incluirlo como criterio concreto (punto 9) en vez de excluirlo, porque
  es un gap de privacidad real y verificable hoy contra el código (`grep`
  de `exif` sobre `backend/app/` no devuelve resultados: ninguna imagen
  subida pierde su GPS/modelo de dispositivo antes de persistirse en
  `output/uploads/`), y encaja directamente en el dominio de esta feature
  (seguridad/privacidad de archivos ya persistidos), a diferencia de
  anonimizar el contenido de negocio, que sí excluí explícitamente porque
  rompería el propósito funcional del sistema. Decidí preservar
  explícitamente el tag `Orientation` porque `05-correccion-orientacion-exif`
  (`ROADMAP.md`, todavía `[ ]` pendiente) ya tiene spec propio
  (`runs/05-correccion-orientacion-exif/spec.md`) que especifica leer ese
  tag como mecanismo de corrección de rotación — aunque el código actual
  de `image_prep.correct_orientation` todavía no lo lee (usa una
  heurística geométrica), esta feature no debe eliminar un tag del que
  una feature ya especificada (pendiente de build, no de decisión) va a
  depender, sin importar el orden en que ambas se implementen. El
  reviewer puede objetar el alcance elegido (p. ej. si prefiere excluirlo
  y tratarlo en una feature separada de metadata/privacidad de imagen),
  pero la decisión tomada fue resolver el gap señalado en audit-1 dentro
  de esta misma feature, por ser el punto de menor fricción y mayor
  cohesión con el resto del alcance ya definido aquí.
- **Corrección explícita (atendiendo audit-2) — evitar recompresión con
  pérdida de JPEG al strippear EXIF, porque degradaría la imagen fuente
  del pipeline OCR:** el criterio 9 introdujo un riesgo no declarado en
  la versión anterior: strippear EXIF con Pillow sin agregar dependencia
  nueva requiere `Image.open()` + `Image.save()`, y el `quality` por
  defecto de Pillow al guardar JPEG es `75`, por debajo de la calidad
  típica de una foto de celular (85-95). Como el archivo resultante en
  `output/uploads/` es exactamente el que `JobQueue._process` pasa al
  pipeline OCR (`job['file_path']`), esa recompresión degradaría la
  fuente de la que depende toda la extracción de campos. Decidí resolverlo
  exigiendo `quality="keep"` (feature nativa de Pillow que reutiliza las
  tablas de cuantización JPEG del archivo original al re-guardar, evitando
  una segunda pasada de compresión con pérdida sobre el contenido de
  píxeles) como mecanismo por defecto, con un fallback documentado
  (`quality>=95` explícito) solo para el caso borde en que `quality="keep"`
  no sea aplicable técnicamente. Elegí verificar esto con un test que
  compara las tablas de cuantización (`Image.quantization`) del archivo
  fuente y del resultante, en vez de solo verificar tamaño en bytes,
  porque es la evidencia más directa y determinística de que no hubo
  recompresión con pérdida (un test de tamaño de archivo podría dar falso
  positivo/negativo por la sola eliminación de bytes EXIF, que también
  reduce el tamaño total sin relación con la calidad de los píxeles). El
  reviewer puede objetar el umbral de `quality>=95` del fallback si lo
  considera insuficientemente alto o insuficientemente justificado caso
  por caso.
- **Corrección explícita (atendiendo audit-2) — se agrega test TIFF
  explícito al criterio 9 en vez de excluir TIFF de esta ronda:** el
  criterio 9 ya declaraba explícitamente que aplica a "JPEG, TIFF" por
  igual, así que excluir TIFF del test sería inconsistente con el propio
  texto del criterio. Evalué la complejidad real antes de decidir: Pillow
  expone `Image.getexif()` de forma equivalente para TIFF y JPEG desde
  versiones anteriores a la ya fijada en `requirements.txt`
  (`Pillow>=10.2.0`), así que no hay una limitación técnica real que
  justifique una exclusión — por eso decidí agregar el test TIFF con el
  mismo nivel de detalle que el JPEG (misma fixture con `GPSInfo`, `Make`,
  `Model`, `Orientation=6`) en vez de acotar el alcance. Como TIFF, en el
  modo en que esta feature lo re-escribe (sin habilitar compresión JPEG
  embebida), no tiene el mismo riesgo de recompresión con pérdida que
  JPEG, la verificación de "no degradación" para TIFF se hace por
  dimensiones/modo de color en vez de tablas de cuantización, que es la
  verificación equivalente aplicable a ese formato. El reviewer puede
  objetar si durante la implementación aparece una limitación real de
  Pillow para TIFF no anticipada aquí; en ese caso corresponde volver a
  este spec con el hallazgo concreto, no resolverlo en silencio en el
  build.
- **Ambigüedad resuelta — sin nueva dependencia para magic bytes ni para
  anonimización EXIF:** los 4 tipos soportados (JPEG, PNG, TIFF, PDF)
  tienen firmas de cabecera estables y bien documentadas; decidí no
  agregar `python-magic` u otra librería de terceros y usar una tabla
  estática de firmas conocidas dentro de la propia app. Para el stripping
  de EXIF, `Pillow` (ya presente en `requirements.txt`) es suficiente
  (`Image.getexif()` / re-guardar sin bloque `exif`), sin agregar
  dependencia nueva — consistente con mantener la imagen Docker liviana
  (ADR-009). Si en el futuro se agregan tipos de archivo con firmas menos
  triviales de distinguir, puede justificarse revisar esta decisión — no
  es una restricción permanente, solo la elegida para el alcance actual
  (4 tipos).
- **Supuesto — target de permisos es el contenedor Linux de despliegue,
  no el Windows de desarrollo:** ADR-009 ya fija Docker en servidor/equipo
  propio del usuario como destino real. Los tests de permisos POSIX se
  gatean/saltan en Windows con motivo explícito, sin bloquear CI ni
  desarrollo local en este repo (que corre en Windows según el entorno
  documentado).
- **No reabre ningún ADR existente:** esta feature no cambia el motor OCR
  (ADR-006), no cambia el formato `.DATA`/`services.ini` (ADR-007), no
  cambia la separación OCR/extracción/validación/storage, y no reabre la
  decisión de infraestructura de despliegue (ADR-009: Docker sin
  auth/TLS/PaaS). Se declara explícitamente por la regla dura de
  `AGENTS.md` sobre no tocar esas decisiones sin dejarlo dicho, aunque
  ninguna de ellas está en discusión en este spec.
- **Supuesto — comportamiento de lote parcial no cambia:** mantener el
  "abortar lote completo en el primer archivo inválido" (comportamiento
  actual de `create_jobs`) es una decisión de no-cambio deliberada para
  no ampliar el alcance de esta feature hacia UX de carga por lote —
  queda documentado como caso borde, no como criterio nuevo.
