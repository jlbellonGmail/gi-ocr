# Seguridad y Privacidad de Documentos

## Para qué sirve

Protege los documentos que subís (comprobantes, facturas, etc.) durante
todo su ciclo de vida en el sistema:

- **Valida que el archivo sea realmente lo que dice ser**: no alcanza con
  que la extensión sea `.jpg`; el sistema revisa el contenido real
  (firma/"magic bytes") y lo contrasta contra lo declarado por tu
  navegador. Un archivo falsificado se rechaza antes de guardarse.
- **No expone el nombre de tu archivo en el servidor**: el archivo que
  subís se guarda con un nombre aleatorio, no con el nombre que le
  pusiste (que puede contener datos personales, p. ej. `DNI_Juan_Perez.
  jpg`). Tu nombre original sigue visible como dato del trámite (`GET
  /api/v1/jobs/{id}`), pero no queda expuesto en la ruta de
  almacenamiento del servidor.
- **Borra automáticamente la ubicación GPS y el modelo de tu celular**:
  si subís una foto tomada con el celular, el sistema elimina esos datos
  del archivo antes de guardarlo — conserva únicamente la orientación
  (para que la imagen se vea derecha), no el resto de la metadata de la
  cámara.
- **Limita cuánto tiempo se guardan los archivos**: los archivos viejos
  se eliminan automáticamente según los plazos configurados (ver más
  abajo), para no acumular comprobantes/documentos indefinidamente.
- **No filtra rutas internas del servidor en los mensajes de error**: si
  un documento falla al procesarse, el mensaje de error que ves no revela
  la estructura de carpetas del servidor.

Esta feature no agrega autenticación de usuarios, HTTPS ni cifrado de los
archivos guardados — eso son decisiones ya documentadas por separado (ver
`docs/tecnica/arquitectura.md`, ADR-009).

## Variables de entorno configurables

| Variable                          | Qué controla                                      | Valor por defecto |
|-------------------------------------|----------------------------------------------------|--------------------|
| `GI_OCR_MAX_UPLOAD_BYTES`           | Tamaño máximo de un archivo subido, en bytes        | `31457280` (30 MB) |
| `GI_OCR_UPLOAD_RETENTION_DAYS`      | Días que se conservan los archivos originales subidos (`output/uploads/`) y los archivos en `inbound/` de raíz antes de purgarse | `7`  |
| `GI_OCR_JOB_RETENTION_DAYS`         | Días que se conservan los resultados de jobs (`output/jobs/`, `output/confirmed/`) antes de purgarse | `90` |
| `GI_OCR_FAILED_RETENTION_DAYS`      | Días que se conservan los archivos fallidos en `storage_bridge/failed/` antes de purgarse | `30` |

Un valor `0` o negativo en cualquiera de las variables de retención
**deshabilita** la purga de ese destino (no borra todo de inmediato).

La purga se ejecuta manualmente o desde una tarea periódica (cron/systemd
timer del servidor donde corre el contenedor):

```bash
python -m backend.app.retention
```

## Ejemplo de uso HTTP: rechazo de upload inválido

### Archivo con firma falsificada (extensión `.jpg`, contenido de texto plano)

**Request:**

```http
POST /api/v1/jobs HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----boundary

------boundary
Content-Disposition: form-data; name="files"; filename="comprobante.jpg"
Content-Type: image/jpeg

esto es texto plano, no una imagen JPEG
------boundary--
```

**Response:**

```json
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json

{
  "detail": {
    "reason": "signature_mismatch",
    "message": "El contenido de 'comprobante.jpg' no corresponde a ningún tipo soportado (JPEG/PNG/TIFF/PDF)"
  }
}
```

No queda ningún archivo nuevo en el servidor tras este intento.

### Content-Type declarado inconsistente con el contenido real

**Request:** un archivo `x.jpg` cuyo contenido real es un PDF, declarado
como `Content-Type: image/jpeg`.

**Response:**

```json
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json

{
  "detail": {
    "reason": "content_type_mismatch",
    "message": "Content-Type declarado ('image/jpeg') no coincide con el contenido real de 'x.jpg' (detectado: pdf)"
  }
}
```

### Archivo demasiado grande

**Response:**

```json
HTTP/1.1 413 Payload Too Large
Content-Type: application/json

{
  "detail": "Archivo demasiado grande (máx 31457280 bytes)"
}
```

### Caso que sí se acepta: TIFF sin Content-Type declarado

Los navegadores suelen no poder inferir el tipo MIME de un archivo
`.tif`/`.tiff` (el objeto `File` del input HTML reporta `type === ''`).
El sistema **no** rechaza este caso por mismatch — confía en la firma real
del archivo:

**Request:**

```http
POST /api/v1/jobs HTTP/1.1
Content-Type: multipart/form-data; boundary=----boundary

------boundary
Content-Disposition: form-data; name="files"; filename="escaneo.tif"
Content-Type:

<bytes con firma TIFF válida>
------boundary--
```

**Response:**

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "created": [{"job_id": "a1b2c3d4e5f6...", "filename": "escaneo.tif"}],
  "queued": 1
}
```

## Qué no cambia para quien usa el frontend

El flujo de captura/carga desde `frontend/` sigue siendo el mismo (subís
una foto o archivo, el sistema lo procesa y te muestra los campos para
confirmar). Estos controles operan de forma transparente: no requieren
ninguna acción adicional de tu parte, salvo que tu archivo sea
efectivamente del tipo que dice ser.
