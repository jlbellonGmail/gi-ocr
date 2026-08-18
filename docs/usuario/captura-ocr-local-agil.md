# Captura OCR Local Ágil — documentación de usuario

Captura y procesa comprobantes (imagen o PDF) de forma local y rápida
(~2.5 s por documento en caliente), con revisión humana antes de
descargar el resultado final. Soporta los proveedores `LITORAL_GAS`
(GAS) y `CEVT` (ELECTRICITY).

Un solo comando levanta frontend + API en el mismo origen:

```powershell
uvicorn backend.app.main:app
```

- Frontend: `http://localhost:8000/`
- API: `http://localhost:8000/api/v1/...`

## 1. Cargar uno o varios documentos

```http
POST /api/v1/jobs
Content-Type: multipart/form-data

files=<imagen o PDF>
files=<otro documento, opcional — se pueden subir varios a la vez>
```

Respuesta (`200 OK`) — no bloqueante, los documentos quedan encolados:

```json
{
  "created": [
    { "job_id": "a1b2c3...", "filename": "factura_gas.jpg" }
  ],
  "queued": 1
}
```

## 2. Consultar el estado de la cola o de un job

```http
GET /api/v1/jobs
GET /api/v1/jobs/{job_id}
```

Estados posibles: `queued`, `processing`, `ready`, `confirmed`, `failed`.

## 3. Reintentar un job fallido

```http
POST /api/v1/jobs/{job_id}/retry
```

`409 Conflict` si el job no existe o ya está listo.

## 4. Confirmar la revisión humana

```http
POST /api/v1/jobs/{job_id}/confirm
Content-Type: application/json

{
  "confirmed_fields": [
    { "field": "cliente", "state": "confirmed" },
    { "field": "periodo", "state": "corrected", "final_value": "01/2026" }
  ]
}
```

`404 Not Found` si el job no existe.

## 5. Descargar el resultado

```http
GET /api/v1/jobs/{job_id}/download
```

- `200 OK` con el JSON confirmado si ya se confirmó la revisión.
- `409 Conflict` si todavía no se confirmó.

Para inspeccionar el resultado **original** (sin confirmar, uso técnico):

```http
GET /api/v1/jobs/{job_id}/original
```

## 6. Exportar el lote completo

```http
GET /api/v1/export
```

Devuelve un JSON con todos los jobs ya confirmados
(`{"batch": [...], "count": N}`).

## 7. Carpeta de ingesta automática (`inbound/`)

```http
GET /api/v1/inbound/status
```

Si se colocan documentos directamente en la carpeta `inbound/` local
(gitignored), el watcher los detecta y encola automáticamente, sin
necesidad de subirlos por el frontend.

## 8. Progreso en vivo (Server-Sent Events)

```http
GET /api/v1/stream
```

Conexión persistente que emite eventos de progreso de la cola en tiempo
real (usado por el frontend para actualizar el estado sin polling).

## Formatos soportados

Imágenes y PDF. En PDF, si la página tiene texto nativo (no escaneada),
se usa ese texto directamente — el OCR solo se aplica a páginas
escaneadas sin texto utilizable.

## Nota sobre el endpoint legacy

El endpoint anterior `/api/v1/capture` (extracción por zonas, existente
en `develop`) **no está disponible** en esta versión: el flujo de jobs
(`/api/v1/jobs*`) lo reemplaza con más capacidad (cola, múltiples
documentos a la vez, confirmación humana, exportación de lote). Ver
[docs/tecnica/captura-ocr-local-agil.md](../tecnica/captura-ocr-local-agil.md)
para el detalle técnico de este cambio.
