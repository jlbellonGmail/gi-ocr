# Auditoría y Permisos de Operador

## Propósito

Esta feature implementa:
1. **Auditoría completa de correcciones humanas**: registro inmutable de quién corrigió qué campo, valor original, valor final, fecha/hora, motivo y acción.
2. **Modelo de permisos mínimos por rol**: tres roles (operador, revisor, admin) con enforcement en backend y gating en frontend, preparando el producto para dejar de ser monousuario local.

## Algoritmo de Autorización

### Identidad (fase pre-JWT)
- Headers HTTP: `X-Operator-Id` (string, requerido) y `X-Operator-Role` (enum: `operator`|`reviewer`|`admin`, requerido)
- Validación en middleware `authz.py` → `require_role()` y `require_job_owner_or_reviewer()`
- Sin autenticación completa (login/tokens/SSO) — headers de confianza en entorno local controlado
- Deuda técnica documentada: migrar a JWT/OIDC en feature futura (roadmap item 26)

### Matriz de Permisos

| Endpoint / Acción | operator | reviewer | admin |
|-------------------|:--------:|:--------:|:-----:|
| `POST /jobs` (cargar) | ✅ | ✅ | ✅ |
| `GET /jobs` (listar) | público | público | público |
| `GET /jobs/{id}` (detalle) | público* | público* | público* |
| `POST /jobs/{id}/confirm` | own jobs | all jobs | all jobs |
| `POST /jobs/{id}/retry` | own jobs | all jobs | all jobs |
| `POST /inbound/config` | ❌ | ❌ | ✅ |
| `GET /export` | ❌ | ❌ | ✅ |
| `GET /services` | público | público | público |

*El detalle es público, pero la acción de confirmar/retry requiere autorización.

### Ownership de Jobs
- Al crear job (`POST /jobs`), se guarda `operator_id` y `operator_role` en `processing_metadata`
- Jobs inbound (watcher): `operator_id="system"`, `operator_role="admin"`
- Jobs legacy (sin owner): tratados como `system/admin`
- `operator`: solo puede confirmar/retry en jobs donde `job.operator_id == operator_id`
- `reviewer`/`admin`: sin restricción de ownership

## Modelo de Datos de Auditoría

### Estructura `audit_trail` (array en `confirmation_metadata`)

```json
{
  "field": "importe",
  "operator_id": "operador1",
  "operator_role": "operator",
  "original_value": "$ 23.345,56",
  "final_value": "$ 23.350,00",
  "action": "corrected",
  "reason": "Error de lectura OCR en centavos",
  "timestamp": "2026-08-26T15:30:45.123Z"
}
```

- `original_value`: valor en `validated_fields` (resultado automático) o `candidate_fields` (OCR bruto) o `null` si campo nuevo
- `action`: `confirmed` | `corrected` | `unresolved`
- `reason`: string (obligatorio para `corrected`/`unresolved`, opcional para `confirmed`)
- `timestamp`: ISO 8601 UTC generado en servidor

### Persistencia
- Escrito en `output/confirmed/{job_id}.confirmed.json` → `confirmation_metadata.audit_trail`
- Replicado a `storage_bridge/ready/{doc_type}_{job_id[:8]}.json` vía `storage_bridge_writer` existente
- No archivo separado de auditoría — viaja dentro del JSON confirmado

### Exclusiones
- Campos internos `provider` y `service` no se auditan (no editables por operador)

## Decisiones de Diseño

1. **Headers vs JWT**: simplicidad operativa en fase local. Headers son de confianza; no hay validación criptográfica. Documentado como deuda para migración futura.

2. **Ownership en job original**: se define al crear el job, no al confirmar. Esto permite mostrar owner en UI de cola y validar antes de permitir acciones.

3. **Matriz fija en código**: no configurable por `services.ini`. Granularidad por servicio será feature futura si se necesita.

4. **Concurrencia**: último en escribir gana (archivo JSON). Ambos generan entrada en `audit_trail`. Sin locking en esta fase.

5. **Frontend localStorage**: configurable por usuario, manipulable. Aceptable para fase local; multi-tenancy real requerirá sesión server-side.

## Casos Borde

| Caso | Comportamiento |
|------|----------------|
| Header faltante | 400 "Header X-Operator-Id requerido" / "Header X-Operator-Role requerido" |
| Rol inválido | 403 "Rol inválido: X. Valores permitidos: operator, reviewer, admin" |
| Operator en job ajeno | 403 "No tiene permiso para este job (solo jobs propios)" |
| Job sin owner (legacy/inbound) | Owner = `system`, rol = `admin`; reviewer/admin pueden actuar |
| Campo sin original (nuevo manual) | `original_value = null`, `action = corrected` |
| Múltiples correcciones mismo campo | Solo última cuenta; una entrada en audit_trail con valor final |
| Confirmación parcial (unresolved) | Revisor posterior añade entradas nuevas, no sobrescribe |
| Frontend sin config | Modal obligatorio antes de permitir confirmar |

## Integración con Pipeline Existente

- `capture_pipeline.process_document` recibe y propaga `operator_id`/`operator_role` en `processing_metadata`
- `job_queue.JobQueue.enqueue` acepta y almacena `operator_id`/`operator_role`
- `review_service.confirm_review` extendido con parámetros `operator_id`, `operator_role` y genera `audit_trail`
- `storage_bridge_writer` sin cambios — ya copia JSON confirmado a `ready/`