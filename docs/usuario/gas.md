# GAS — documentación de usuario

Flujo end-to-end para procesar un comprobante de GAS desde el frontend
web o directamente por HTTP.

## Flujo completo (T4, MVP operable)

```text
seleccionar imagen → preview → procesar → revisar accepted/missing →
editar/corregir campos → confirmar → descargar JSON final
```

Un solo comando levanta frontend + API en el mismo origen:

```powershell
uvicorn backend.app.main:app
```

- Frontend: `http://localhost:8000/`
- API: `http://localhost:8000/api/v1/...`

## 1. Procesar una imagen

```http
POST /api/v1/process
Content-Type: multipart/form-data

file=<imagen GAS: png, jpg, jpeg, tif o tiff>
```

Respuesta (`200 OK`):

```json
{
  "job_id": "3f9c1e2a4b5d6e7f8091a2b3c4d5e6f7",
  "confirm_url": "/api/v1/process/3f9c.../confirm",
  "original_preview_url": "/api/v1/process/3f9c.../original",
  "final_download_url": "/api/v1/process/3f9c.../json",
  "result": {
    "raw_ocr_text": "...",
    "structured_output": {
      "document_type": "GAS",
      "candidate_fields": { "importe": "23.345,56", "cliente": "045-987654", "...": "..." },
      "validated_fields": { "importe": "23.345,56", "...": "..." },
      "rejected_fields": {},
      "missing_fields": { "nro_medidor": "..." }
    },
    "field_report": {
      "accepted_fields": ["importe", "cliente"],
      "rejected_fields": [],
      "missing_fields": ["nro_medidor"],
      "summary_counts": { "accepted_count": 2, "rejected_count": 0, "missing_count": 1 }
    }
  }
}
```

El JSON devuelto acá es el resultado **original** (técnico): todavía no
es descargable como "final" (ver paso 3).

## 2. Confirmar la revisión humana

Para cada campo, el frontend permite fijar un estado y, si corresponde,
un valor corregido:

```http
POST /api/v1/process/{job_id}/confirm
Content-Type: application/json

{
  "confirmed_fields": [
    { "field": "importe", "state": "confirmed" },
    { "field": "nro_medidor", "state": "corrected", "final_value": "34572" }
  ]
}
```

Estados válidos:

- `confirmed`: se acepta el valor original tal cual (el servidor lo
  fuerza; ignora cualquier `final_value` enviado por el cliente).
- `corrected`: requiere `final_value` distinto del original y válido
  según el tipo de campo (fecha, monto, texto — ver
  [docs/tecnica/gas.md](../tecnica/gas.md)). Devuelve `400` si el valor
  no es válido.
- `unresolved`: el campo queda sin valor final.

Respuesta (`200 OK`): resumen con `review_state` (`confirmed` si no queda
ningún campo `unresolved`, `partial` en caso contrario) y
`final_download_url`.

## 3. Descargar el JSON final confirmado

```http
GET /api/v1/process/{job_id}/json
```

- `200 OK` con el JSON confirmado (`Content-Disposition` con nombre de
  archivo seguro) si ya se confirmó la revisión.
- `409 Conflict` si todavía no se confirmó — evita descargar un resultado
  no revisado como si fuera "final".

## Otros endpoints

- `GET /api/v1/process/{job_id}/original`: JSON original sin confirmar
  (inspección técnica).
- `GET /api/v1/process/{job_id}/status`: `{ "processed": true, "confirmed": bool, "review_state": "..." }`.
- `POST /api/v1/capture` (legacy, sin cambios): extracción por zonas de
  imagen, conservada para compatibilidad.

## Formatos soportados

`png`, `jpg`, `jpeg`, `tif`, `tiff`. PDF no está soportado.
