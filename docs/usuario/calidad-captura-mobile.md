# Calidad de captura mobile — documentación de usuario

## Propósito

Cuando se saca una foto de un comprobante con el celular, es fácil que
salga borrosa, con mala luz, con reflejos, cortada en el encuadre o
inclinada. Antes de esta mejora, esas fotos igual se procesaban de punta a
punta por el motor OCR y recién en la pantalla de revisión se veía que
faltaban casi todos los campos — sin ningún aviso previo, y habiendo
gastado cómputo OCR en una foto que nunca iba a andar bien.

Con esta mejora, cada foto (no PDF) pasa por un control de calidad
**antes** de llegar al OCR, que evalúa 8 señales (desenfoque, resolución,
reflejos, sombras, documento cortado, mala perspectiva, mala iluminación,
encuadre insuficiente) y devuelve uno de tres resultados:

- **`ok`**: la foto está bien. Se procesa normalmente, sin ningún aviso.
- **`warn`**: la foto tiene algún problema menor (por ejemplo, un poco de
  desenfoque o inclinación). Se procesa igual, pero el resultado incluye
  un aviso de "posible baja confianza" para que quien revise sepa que
  conviene prestar más atención a los campos extraídos.
- **`reject`**: la foto tiene un problema serio (por ejemplo, está cortada,
  demasiado oscura, o el reflejo tapa el texto). **No se gasta OCR en
  ella**: el documento queda en un estado especial pidiendo una foto
  nueva, con el motivo concreto de qué está mal, para que el usuario pueda
  volver a sacarla mientras todavía tiene el comprobante a mano.

## Qué NO cambia

- El endpoint de subida (`POST /api/v1/jobs`) es el mismo de siempre, con
  el mismo contrato de request.
- Una foto que pasa el control de calidad sin problemas (`ok`) se procesa
  exactamente igual que antes de esta mejora.
- Los PDF no pasan por este control (se renderizan a imagen de otra forma
  y no es el caso de uso que motiva esta mejora — una foto de celular
  apurada).
- La confirmación de revisión humana y la descarga del resultado final
  (`POST /confirm`, `GET /download`) siguen funcionando igual para
  documentos que sí llegaron a procesarse (`ok`/`warn`).

## Ejemplo de uso HTTP

El flujo de subida es el mismo de siempre
(`docs/usuario/captura-ocr-local-agil.md`): se sube el documento y se
consulta el resultado del job. Lo que cambia es lo que trae ese resultado
según el veredicto de calidad.

### Caso 1 — veredicto `ok`

**1. Subir la foto** (sin cambios respecto al flujo general):

```http
POST /api/v1/jobs
Content-Type: multipart/form-data

files=<foto_comprobante_gas.jpg>
```

Respuesta (`200 OK`):

```json
{
  "created": [
    { "job_id": "a1b2c3d4e5f6", "filename": "foto_comprobante_gas.jpg" }
  ],
  "queued": 1
}
```

**2. Consultar el resultado del job:**

```http
GET /api/v1/jobs/a1b2c3d4e5f6
```

Respuesta (`200 OK`) una vez procesado — foto de buena calidad, pipeline
normal completo, sin ningún aviso:

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "ready",
  "confirmed": false,
  "result": {
    "processing_metadata": {
      "provider_detected": "LITORAL_GAS",
      "provider_confidence": 1.0,
      "engine": "RapidOCR-ONNX-PP-OCRv3",
      "quality_gate": {
        "verdict": "ok",
        "reasons": [],
        "signals": {
          "blur": { "metric": 1842.3, "verdict": "ok" },
          "low_resolution": { "metric": 1600.0, "verdict": "ok" },
          "glare": { "metric": 0.0, "verdict": "ok" },
          "uneven_lighting": { "metric": 6.1, "verdict": "ok" },
          "poor_lighting": { "metric": 198.4, "verdict": "ok" },
          "document_cropped": { "metric": 0.71, "verdict": "ok" },
          "bad_perspective": { "metric": 1.03, "verdict": "ok" },
          "insufficient_framing": { "metric": 0.74, "verdict": "ok" }
        }
      }
    },
    "raw_ocr_text": "COMPROBANTE GAS\nLitoral Gas - Servicio de Gas Natural\nN Cliente: 12345678\n...",
    "structured_output": {
      "document_type": "GAS",
      "candidate_fields": { "cliente": "12345678", "periodo": "05/2026" },
      "validated_fields": { "cliente": "12345678", "periodo": "05/2026" },
      "rejected_fields": {},
      "missing_fields": {}
    }
  }
}
```

### Caso 2 — veredicto `warn`

Misma subida (`POST /api/v1/jobs`), pero la foto tenía, por ejemplo, un
desenfoque leve. El job igual llega a `status: "ready"` (se procesó
normalmente), pero `quality_gate.verdict` avisa del problema:

```http
GET /api/v1/jobs/b2c3d4e5f6a1
```

Respuesta (`200 OK`):

```json
{
  "job_id": "b2c3d4e5f6a1",
  "status": "ready",
  "confirmed": false,
  "result": {
    "processing_metadata": {
      "provider_detected": "LITORAL_GAS",
      "provider_confidence": 1.0,
      "engine": "RapidOCR-ONNX-PP-OCRv3",
      "quality_gate": {
        "verdict": "warn",
        "reasons": [
          {
            "signal": "blur",
            "severity": "warn",
            "message": "La imagen se ve algo borrosa; el resultado puede ser menos preciso."
          }
        ],
        "signals": {
          "blur": { "metric": 62.4, "verdict": "warn" },
          "low_resolution": { "metric": 1200.0, "verdict": "ok" },
          "glare": { "metric": 0.0, "verdict": "ok" },
          "uneven_lighting": { "metric": 8.2, "verdict": "ok" },
          "poor_lighting": { "metric": 187.1, "verdict": "ok" },
          "document_cropped": { "metric": 0.68, "verdict": "ok" },
          "bad_perspective": { "metric": 1.05, "verdict": "ok" },
          "insufficient_framing": { "metric": 0.7, "verdict": "ok" }
        }
      }
    },
    "raw_ocr_text": "COMPROBANTE GAS\n...",
    "structured_output": {
      "document_type": "GAS",
      "candidate_fields": { "cliente": "12345678" },
      "validated_fields": { "cliente": "12345678" },
      "rejected_fields": {},
      "missing_fields": { "periodo": null }
    }
  }
}
```

El frontend (`frontend/src/app.js`, `renderReady`) muestra en este caso un
aviso visible ("Aviso de calidad: posible baja confianza en los
resultados") con el motivo concreto, junto a los campos extraídos — no
bloquea la revisión, solo advierte.

### Caso 3 — veredicto `reject`

Misma subida (`POST /api/v1/jobs`), pero la foto está cortada en el
encuadre y además demasiado oscura. El OCR **no llega a ejecutarse**: el
job queda en el estado `needs_new_photo`.

```http
GET /api/v1/jobs/c3d4e5f6a1b2
```

Respuesta (`200 OK`):

```json
{
  "job_id": "c3d4e5f6a1b2",
  "status": "needs_new_photo",
  "confirmed": false,
  "result": {
    "processing_metadata": {
      "engine": null,
      "quality_gate": {
        "verdict": "reject",
        "reasons": [
          {
            "signal": "document_cropped",
            "severity": "reject",
            "message": "El documento está cortado en el encuadre. Volvé a fotografiarlo completo, sin que se salga del cuadro."
          },
          {
            "signal": "poor_lighting",
            "severity": "reject",
            "message": "La foto está demasiado oscura o sobreexpuesta para leerse. Buscá mejor luz."
          }
        ],
        "signals": {
          "blur": { "metric": 210.5, "verdict": "ok" },
          "low_resolution": { "metric": 1200.0, "verdict": "ok" },
          "glare": { "metric": 0.0, "verdict": "ok" },
          "uneven_lighting": { "metric": 3.1, "verdict": "ok" },
          "poor_lighting": { "metric": 22.7, "verdict": "reject" },
          "document_cropped": { "metric": 0.63, "verdict": "reject" },
          "bad_perspective": { "metric": null, "verdict": "not_evaluable" },
          "insufficient_framing": { "metric": null, "verdict": "not_evaluable" }
        }
      }
    },
    "raw_ocr_text": "",
    "structured_output": {
      "document_type": null,
      "candidate_fields": {},
      "validated_fields": {},
      "rejected_fields": {},
      "missing_fields": {}
    }
  }
}
```

Notas sobre este caso:

- `status` es `"needs_new_photo"` — distinto de `"ready"` y de
  `"failed"`. El frontend lo muestra con el mismo estilo visual que
  `"failed"` (una etiqueta y un cuadro de error), listando cada motivo de
  rechazo.
- `bad_perspective`/`insufficient_framing` quedan `"not_evaluable"`: no se
  pudo detectar un cuadrilátero de documento claro (consistente con que
  esté cortado), así que esas señales no agregan una razón redundante por
  la misma causa raíz.
- **Intentar confirmar este job da 404**, porque no hay resultado OCR que
  confirmar:

  ```http
  POST /api/v1/jobs/c3d4e5f6a1b2/confirm
  Content-Type: application/json

  {"confirmed_fields": []}
  ```

  ```json
  { "detail": "Job no encontrado" }
  ```
  (`404 Not Found`)

- **Se puede reintentar** (por ejemplo, si el usuario reemplazó el archivo
  original, aunque lo típico es subir una foto nueva por separado):

  ```http
  POST /api/v1/jobs/c3d4e5f6a1b2/retry
  ```

  ```json
  { "job_id": "c3d4e5f6a1b2", "status": "queued" }
  ```

  Al reprocesar el mismo archivo, el control de calidad es determinístico:
  vuelve a dar el mismo veredicto y las mismas razones.

## Qué hacer ante un `needs_new_photo`

El mensaje de cada razón (`reasons[].message`) ya es apto para mostrar
directo al usuario final: indica qué corregir (mejorar la luz, encuadrar
el documento completo, evitar reflejos, sostener el celular firme, etc.).
La recomendación operativa es sacar una foto nueva del comprobante y
subirla como un job nuevo (`POST /api/v1/jobs`), en vez de reintentar el
mismo archivo — el reintento (`retry`) existe principalmente para volver a
intentar tras un problema transitorio, no para "arreglar" una foto que
objetivamente tiene un problema de captura.

## Ver también

- Flujo completo de subida/revisión/confirmación:
  [docs/usuario/captura-ocr-local-agil.md](captura-ocr-local-agil.md).
- Detalle técnico de las 8 señales, los umbrales por defecto y el riesgo
  de calibración conocido:
  [docs/tecnica/calidad-captura-mobile.md](../tecnica/calidad-captura-mobile.md).
