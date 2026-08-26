# Auditoría y Permisos de Operador

## Para qué sirve

Esta feature añade **trazabilidad completa** de quién revisa y corrige cada campo de un comprobante, y **control de acceso por rol** para cuando el sistema opere con múltiples usuarios.

- **Auditoría**: cada confirmación registra operador, valor original (del OCR/validación automática), valor final, fecha/hora, motivo y acción (confirmado/corregido/sin resolver).
- **Permisos**: tres roles con permisos mínimos — operador (sus docs), revisor (todos), admin (todo + config).

## Roles y Permisos

| Acción | Operador | Revisor | Admin |
|--------|:--------:|:-------:|:-----:|
| Cargar documentos | ✅ | ✅ | ✅ |
| Ver cola y detalles | ✅ | ✅ | ✅ |
| Confirmar revisión | Solo propios | Todos | Todos |
| Reintentar job fallido | Solo propios | Todos | Todos |
| Configurar inbound | ❌ | ❌ | ✅ |
| Exportar lote JSON | ❌ | ❌ | ✅ |
| Ver servicios (catálogo) | ✅ | ✅ | ✅ |

> **Nota**: "Propios" = documentos cargados por ese operador (header `X-Operator-Id`). Jobs del watcher inbound tienen owner `system` (rol admin).

## Configuración del Operador (Frontend)

Al abrir la app por primera vez, se muestra un modal obligatorio:

1. **ID Operador**: identificador único (ej: `operador1`, `juan.perez`, `OP-001`)
2. **Rol**: `operator` | `reviewer` | `admin`

Se guarda en `localStorage` (clave `gi_ocr_operator`) y se envía automáticamente en todas las peticiones.

## Uso de la API (Headers Requeridos)

Todas las peticiones mutantes requieren dos headers:

```
X-Operator-Id: operador1
X-Operator-Role: operator
```

### Ejemplo: Confirmar revisión

**Request**
```http
POST /api/v1/jobs/abc123def456/confirm
Content-Type: application/json
X-Operator-Id: operador1
X-Operator-Role: operator

{
  "confirmed_fields": [
    { "field": "importe", "state": "corrected", "final_value": "$ 23.350,00", "reason": "Error centavos OCR" },
    { "field": "cliente", "state": "confirmed", "final_value": "045-987654" },
    { "field": "periodo", "state": "unresolved", "final_value": "", "reason": "No legible en imagen" }
  ]
}
```

**Response (200 OK)**
```json
{
  "job_id": "abc123def456",
  "review_state": "partial",
  "document_type": "GAS",
  "final_filename": "GAS_abc123de.json",
  "final_download_url": "/api/v1/jobs/abc123def456/download",
  "confirmed_fields": {
    "importe": "$ 23.350,00",
    "cliente": "045-987654",
    "periodo": ""
  },
  "corrections": ["importe"],
  "summary": { "confirmed_count": 1, "corrected_count": 1, "unresolved_count": 1 },
  "confirmed_path": "output/confirmed/abc123def456.confirmed.json",
  "correction_reasons": {
    "importe": "Error centavos OCR",
    "periodo": "No legible en imagen"
  },
  "audit_trail": [
    {
      "field": "importe",
      "operator_id": "operador1",
      "operator_role": "operator",
      "original_value": "$ 23.345,56",
      "final_value": "$ 23.350,00",
      "action": "corrected",
      "reason": "Error centavos OCR",
      "timestamp": "2026-08-26T15:30:45.123Z"
    },
    {
      "field": "cliente",
      "operator_id": "operador1",
      "operator_role": "operator",
      "original_value": "045-987654",
      "final_value": "045-987654",
      "action": "confirmed",
      "reason": null,
      "timestamp": "2026-08-26T15:30:45.123Z"
    },
    {
      "field": "periodo",
      "operator_id": "operador1",
      "operator_role": "operator",
      "original_value": "01/2026",
      "final_value": "",
      "action": "unresolved",
      "reason": "No legible en imagen",
      "timestamp": "2026-08-26T15:30:45.123Z"
    }
  ]
}
```

### Códigos de Error Comunes

| Código | Causa |
|--------|-------|
| 400 | Falta header `X-Operator-Id` o `X-Operator-Role` |
| 403 | Rol inválido, o operador intentando actuar en job ajeno |
| 404 | Job no encontrado |
| 409 | Job no reintentable (ya ready/confirmed) |

## Auditoría en Archivo Confirmado

El JSON confirmado (`output/confirmed/{job_id}.confirmed.json`) incluye:

```json
{
  "confirmation_metadata": {
    "final_filename": "GAS_abc123de.json",
    "confirmed_at": "2026-08-26T15:30:45.123Z",
    "audit_trail": [ ... ],
    "confidence_at_review": { ... },
    "decision_at_review": { ... },
    "correction_reasons": { ... }
  }
}
```

Este archivo se replica automáticamente a `storage_bridge/ready/` para el sistema legacy.

## Cambiar de Operador/Rol

En el frontend: limpiar `localStorage` (DevTools → Application → Local Storage → `gi_ocr_operator` → Delete) y recargar. O usar:
```js
localStorage.removeItem("gi_ocr_operator"); location.reload();
```

## Limitaciones Actuales

- **Headers de confianza**: no hay autenticación criptográfica (JWT/OIDC). Válido para entorno local/controlado.
- **localStorage manipulable**: el usuario puede cambiar su ID/rol en el navegador.
- **Sin gestión de usuarios**: no hay CRUD de operadores ni asignación de roles en UI.
- **Matriz fija**: permisos no configurables por servicio/documento.