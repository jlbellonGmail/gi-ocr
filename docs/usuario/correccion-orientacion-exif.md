# Corrección de orientación EXIF — documentación de usuario

## Propósito

Cuando se saca una foto de un comprobante con el celular sosteniéndolo de
costado o boca abajo, la cámara guarda la imagen tal como sale del sensor
y anota en la metadata EXIF (tag `Orientation`) cómo debe rotarse para
verse "derecha". Muchas apps la muestran ya rotada, pero **el archivo de
píxeles en sí sigue estando de costado**.

Antes de esta mejora, el sistema ignoraba ese dato y procesaba la imagen
tal como estaba guardada en disco: si venía de costado, el OCR la recibía
de costado, y la extracción de campos (número de cliente, período,
importe, etc.) fallaba o devolvía resultados pobres — sin que hubiera
ningún indicio visible del problema para quien subió la foto.

Con esta mejora, el sistema lee el tag EXIF antes de procesar la imagen y
la endereza automáticamente si hace falta, para las fotos donde ese dato
esté presente (la gran mayoría de fotos de celular en JPEG). El resultado
práctico: **una foto de comprobante sacada de costado o al revés ahora se
procesa igual de bien que una sacada derecha**, sin que el usuario tenga
que rotarla manualmente antes de subirla.

## Qué NO cambia

- **El contrato de la API no cambia.** No hay ningún campo nuevo en el
  request ni en la response de los endpoints existentes. La corrección es
  interna al procesamiento del documento.
- Los formatos aceptados por el endpoint de subida siguen siendo los
  mismos: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.pdf`.
- Los PDF no se ven afectados por este cambio (se renderizan a imagen y no
  traen este tipo de metadata de cámara).
- Una foto ya derecha (sin necesidad de rotación) se procesa exactamente
  igual que antes.

## Ejemplo de uso HTTP

El flujo de subida es el mismo de siempre
(`docs/usuario/captura-ocr-local-agil.md`): se sube el documento, se
consulta el resultado del job, y — si la foto venía rotada por el
celular — el resultado ya viene con el documento correctamente orientado
y sus campos extraídos, sin pasos adicionales.

### 1. Subir una foto de comprobante (venga o no rotada)

```http
POST /api/v1/jobs
Content-Type: multipart/form-data

files=<foto_comprobante_gas.jpg>
```

Respuesta (`200 OK`) — igual sea la foto derecha o rotada, la respuesta
inmediata es la misma (encolado no bloqueante):

```json
{
  "created": [
    { "job_id": "a1b2c3d4e5f6", "filename": "foto_comprobante_gas.jpg" }
  ],
  "queued": 1
}
```

### 2. Consultar el resultado del job

```http
GET /api/v1/jobs/a1b2c3d4e5f6
```

Respuesta (`200 OK`) una vez procesado. Si la foto traía el tag EXIF de
rotación (por ejemplo, `Orientation=6`, típico de sostener el celular de
costado hacia la derecha), el documento ya se corrigió antes de llegar a
OCR y los campos se extraen con normalidad:

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "ready",
  "confirmed": false,
  "result": {
    "processing_metadata": {
      "provider_detected": "LITORAL_GAS",
      "provider_confidence": 1.0,
      "engine": "RapidOCR-ONNX-PP-OCRv3"
    },
    "raw_ocr_text": "COMPROBANTE GAS\nLitoral Gas - Servicio de Gas Natural\nN Cliente: 12345678\n...",
    "structured_output": {
      "document_type": "GAS",
      "candidate_fields": { "cliente": "12345678", "periodo": "05/2026", "...": "..." },
      "validated_fields": { "cliente": "12345678", "periodo": "05/2026", "...": "..." },
      "rejected_fields": {},
      "missing_fields": {}
    }
  }
}
```

Sin esta mejora, la misma foto rotada habría llegado a OCR de costado y
`raw_ocr_text` habría salido vacío o con texto irreconocible, dejando la
mayoría de los campos en `missing_fields`.

### 3. El resto del flujo sigue igual

Confirmación de revisión humana y descarga del resultado final funcionan
exactamente como en el flujo general (ver
`docs/usuario/captura-ocr-local-agil.md`):

```http
POST /api/v1/jobs/a1b2c3d4e5f6/confirm
GET  /api/v1/jobs/a1b2c3d4e5f6/download
```

## Qué formatos se benefician de esta corrección

- **JPEG (`.jpg`/`.jpeg`)**: el caso relevante. Es el formato que producen
  las cámaras de celular y casi siempre trae el tag `Orientation`.
- **TIFF (`.tif`/`.tiff`)**: también soporta el tag y se beneficia igual,
  aunque es menos común como formato de foto de celular (más frecuente en
  escaneos).
- **PNG (`.png`)**: no suele traer esta metadata (las cámaras no producen
  PNG), así que en la práctica no cambia nada para este formato — sigue
  procesándose igual que antes.
- **PDF (`.pdf`)**: no aplica; los PDF no se ven afectados por este
  cambio.

## Ver también

- Flujo completo de subida/revisión/confirmación:
  [docs/usuario/captura-ocr-local-agil.md](captura-ocr-local-agil.md).
- Detalle técnico del algoritmo y las decisiones de diseño:
  [docs/tecnica/correccion-orientacion-exif.md](../tecnica/correccion-orientacion-exif.md).
