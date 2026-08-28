# Contrato de Integración Legacy v2 — Guía de usuario

## Propósito

Este documento describe cómo consumir la salida estructurada que gi-ocr genera para integración con sistemas externos/legacy. Cubre el formato `.DATA` v2 (archivo plano legado) y el JSON confirmado v2 (API), ambos versionados contractualmente.

## Flujo general

1. Usuario sube comprobante → job en cola
2. OCR + extracción + validación → resultado `ready`
3. Usuario revisa/confirma en consola → `POST /api/v1/jobs/{job_id}/confirm`
4. Sistema genera:
   - **JSON confirmado** → `output/confirmed/<job_id>.confirmed.json` (descargable vía API)
   - **`.DATA` v2** → `storage_bridge/ready/SERVICIO_YYYYMMDD_HHMMSS.DATA` (para sistema legacy)
   - **`.CONFIDENCE.json`** → `storage_bridge/ready/...CONFIDENCE.json` (trazabilidad confianza)

## Formato `.DATA` v2 (para sistema legacy)

### Especificación

```
VERSION=2
campo1;campo2;campo3
valor1;valor2;valor3
```

- **Encoding**: UTF-8 sin BOM
- **Separador**: Punto y coma (`;`)
- **Línea 1**: `VERSION=2` (identifica contrato v2)
- **Línea 2**: Nombres de campos en orden de `services.ini`
- **Línea 3**: Valores correspondientes
- **Valores vacíos**: Campo presente pero vacío (`;;`)
- **Prohibido en valores**: `;`, saltos de línea

### Ejemplo real (GAS)

Archivo: `storage_bridge/ready/GAS_20260826_153045.DATA`

```
VERSION=2
importe;cliente;nro_medidor;a_pagar_hasta;periodo
23.345,56;045-987654;34572;20/06/2026;01/2026
```

### Nomenclatura

`SERVICIO_YYYYMMDD_HHMMSS[.seq].DATA`

- `SERVICIO`: Mayúsculas (ej. `GAS`, `CEVT`)
- Timestamp: UTC
- `.seq`: `_001`, `_002` si colisión mismo segundo

## JSON Confirmado v2 (API)

### Endpoint de descarga

```
GET /api/v1/jobs/{job_id}/download
```

**Requiere**: Job confirmado (`POST /api/v1/jobs/{job_id}/confirm` previo)

**Response**: `application/json` con `Content-Disposition: attachment; filename="GAS_abc12345.json"`

### Estructura

```json
{
  "job_id": "abc123def456...",
  "document_type": "GAS",
  "confirmed_fields": {
    "importe": "23.345,56",
    "cliente": "045-987654",
    "nro_medidor": "34572",
    "a_pagar_hasta": "20/06/2026",
    "periodo": "01/2026"
  },
  "validated_fields": { ... },
  "corrections": ["importe"],
  "summary": {
    "confirmed_count": 4,
    "corrected_count": 1,
    "unresolved_count": 0
  },
  "confirmation_metadata": {
    "final_filename": "GAS_abc12345.json",
    "confirmed_at": "2026-08-26T15:30:45.123456+00:00",
    "original_source": "output/uploads/random_name.jpg",
    "confidence_at_review": {
      "importe": { "ocr_score": 0.92, "extraction_score": 1.0, "final_score": 0.95, "decision": "auto_accepted", ... }
    },
    "decision_at_review": { "importe": "corrected", "cliente": "confirmed", ... },
    "correction_reasons": { "importe": "OCR leyó 23.345,66" },
    "audit_trail": [
      { "field": "importe", "operator_id": "op1", "operator_role": "reviewer", "original_value": "23.345,66", "final_value": "23.345,56", "action": "corrected", "reason": "OCR leyó 23.345,66", "timestamp": "2026-08-26T15:30:45.123456+00:00" }
    ],
    "contract_version": 2,
    "data_file": "storage_bridge/ready/GAS_20260826_153045.DATA",
    "confidence_file": "storage_bridge/ready/GAS_20260826_153045.CONFIDENCE.json",
    "data_hash": "sha256:a1b2c3d4e5f6..."
  },
  "original_result_ref": "abc123def456..."
}
```

### Campos clave para integración

| Campo | Descripción |
|-------|-------------|
| `confirmed_fields` | Valores finales tras revisión humana (fuente de verdad) |
| `confirmation_metadata.contract_version` | Versión del contrato (2) |
| `confirmation_metadata.data_file` | Path al `.DATA` en `storage_bridge/ready/` |
| `confirmation_metadata.data_hash` | SHA-256 del contenido `.DATA` para verificación de integridad |
| `confirmation_metadata.audit_trail` | Trazabilidad completa: quién cambió qué, valor original/final, motivo, cuándo |

## Reconciliación (Admin)

### Endpoint

```
POST /api/v1/admin/reconcile
```

**Requiere**: Role ADMIN

### Response

```json
{
  "generated_at": "2026-08-26T15:35:00.000000+00:00",
  "contract_version": 2,
  "missing_in_ready": [
    { "job_id": "abc123...", "service": "GAS", "expected_timestamp": "20260826_153045" }
  ],
  "orphan_in_ready": [
    { "ready_key": "GAS_20260826_153045", "service": "GAS", "timestamp": "20260826_153045", "path": "storage_bridge/ready/GAS_20260826_153045.DATA" }
  ],
  "content_mismatch": [],
  "summary": {
    "total_confirmed_v2": 100,
    "total_ready_v2": 98,
    "missing_count": 2,
    "orphan_count": 1,
    "mismatch_count": 0
  },
  "report_path": "output/reconciliation/reconciliation_20260826_153500.json"
}
```

### Interpretación

- **missing_in_ready**: Jobs confirmados que NO tienen `.DATA` en `ready/` → investigar fallo de escritura
- **orphan_in_ready**: Archivos `.DATA` en `ready/` SIN job confirmado correspondiente → posible residuo de reintentos o procesamiento manual
- **content_mismatch**: Mismo job correlacionado, pero contenido `.DATA` difiere del JSON confirmado → posible carrera de condición o re-procesamiento parcial

## Garantías contractuales v2

| Garantía | Descripción |
|----------|-------------|
| **Versionado** | `VERSION=2` en `.DATA`, `contract_version: 2` en JSON |
| **Idempotencia** | Mismo contenido → mismo archivo en `ready/` (no duplicados) |
| **Reintentos** | Escritura con backoff exponencial (100/200/400/800ms) |
| **Atomicidad** | Escritura tmp → rename atómico (nunca archivos parciales) |
| **Trazabilidad** | Hash SHA-256 en JSON y `.CONFIDENCE.json` |
| **Reconciliación** | Endpoint admin para detectar desfasajes |
| **Errores** | Registrados en `storage_bridge/failed/*_error.json` |

## Migración desde v1

| v1 (implícito) | v2 (explícito) |
|----------------|----------------|
| Sin línea VERSION | `VERSION=2` primera línea |
| Sin hash | `data_hash` SHA-256 |
| Sin reintentos | Backoff exponencial |
| Sin errores estructurados | `failed/*_error.json` |
| Sin reconciliación | Endpoint `/admin/reconcile` |

**Compatibilidad**: Lectores v1 que esperan header en línea 1 deben saltar la primera línea si empieza con `VERSION=`. Escritores v1 no existen (solo v2 en producción).

## Ejemplo completo: Confirmar y descargar

```bash
# 1. Confirmar revisión (ejemplo con curl)
curl -X POST "http://localhost:8000/api/v1/jobs/abc123def456/confirm" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "confirmed_fields": [
      {"field": "importe", "state": "corrected", "final_value": "23.345,56", "reason": "OCR leyó 23.345,66"},
      {"field": "cliente", "state": "confirmed"},
      {"field": "nro_medidor", "state": "confirmed"},
      {"field": "a_pagar_hasta", "state": "confirmed"},
      {"field": "periodo", "state": "confirmed"}
    ]
  }'

# Response incluye data_file, confidence_file, data_hash

# 2. Descargar JSON confirmado
curl -X GET "http://localhost:8000/api/v1/jobs/abc123def456/download" \
  -H "Authorization: Bearer <token>" \
  -o GAS_abc12345.json

# 3. Verificar integridad del .DATA (opcional)
# Leer data_hash del JSON y comparar con hash del archivo en storage_bridge/ready/
```

## Preguntas frecuentes

**¿Por qué `VERSION=2` en una línea separada?**
Para no romper parsers simples que leen línea 1 = header, línea 2 = valores. Lectores v2 detectan la línea de versión y la saltan.

**¿Qué pasa si el sistema legacy borra/mueve archivos de `ready/`?**
La reconciliación lo detecta como `orphan_in_ready` (si legacy mueve) o `missing_in_ready` (si legacy borra tras leer). gi-ocr no re-escribe automáticamente; requiere intervención manual o re-confirmación.

**¿Puedo desactivar la escritura en `storage_bridge/`?**
No en v2 — es parte del contrato. Para desactivar, no confirmar la revisión (el JSON confirmado no se genera sin confirmación).

**¿El hash `data_hash` cubre el `.CONFIDENCE.json` también?**
No, solo el contenido del `.DATA`. El `.CONFIDENCE.json` tiene su propia trazabilidad.