# Decision Log: 11-auditoria-permisos-operador

## Decisiones Demostrables desde Spec / Auditoría / Implementación

### 1. Identidad vía Headers (no JWT)
**Origen**: Spec "Riesgos / supuestos" #1, CA #1, #5
**Decisión**: Usar headers `X-Operator-Id` y `X-Operator-Role` en lugar de JWT/OIDC.
**Justificación**: 
- Fase local/controlada, no bloquear en auth completo
- Simplicidad operativa: sin gestión de tokens, refresh, expiración
- Deuda técnica explícita documentada para migración futura (roadmap item 26)
**Evidencia**: `authz.py:_get_operator_id`, `_get_operator_role`, validación 400/403

### 2. Ownership en Job Original (no en Confirmación)
**Origen**: Spec CA #3, Caso borde #1
**Decisión**: Guardar `operator_id`/`operator_role` al crear job (`POST /jobs`), no al confirmar.
**Justificación**:
- Permite mostrar owner en UI de cola antes de confirmar
- Valida permisos en confirm/retry *antes* de procesar correcciones
- Jobs inbound/legacy: default `system`/`admin` (trazabilidad)
**Evidencia**: `job_queue.py:enqueue` guarda owner; `capture_pipeline.py` propaga a `processing_metadata`; `authz.py:require_job_owner_or_reviewer` lee de job original

### 3. Estructura `audit_trail` como Array en `confirmation_metadata`
**Origen**: Spec CA #2, #6
**Decisión**: Array de objetos con campos fijos, una entrada por campo corregido/confirmado.
**Justificación**:
- Trazabilidad granular por campo (no por job)
- Inmutable: se añade en cada confirmación, no se sobrescribe
- Compatible con JSON confirmado existente y `storage_bridge_writer`
- Excluye campos internos (`provider`, `service`)
**Evidencia**: `review_service.py:confirm_review` construye `audit_trail` con 7 campos obligatorios

### 4. Matriz de Permisos Fija en Código (3 Roles)
**Origen**: Spec CA #3, Riesgo #6
**Decisión**: Roles `operator`/`reviewer`/`admin` con permisos hardcodeados en `authz.py`.
**Justificación**:
- Simplicidad: no requiere config adicional en `services.ini`
- Cubre caso de uso real: operador (carga+corrige propios), revisor (aprueba todos), admin (config+export)
- Granularidad por servicio será feature futura si se necesita
**Evidencia**: `authz.py:ROLE_HIERARCHY`, `require_role`, `require_job_owner_or_reviewer`; `main.py` aplica en endpoints

### 5. `original_value` = Validado > Candidato > Null
**Origen**: Spec CA #2, Caso borde #4
**Decisión**: Prioridad: `validated_fields` (resultado automático) → `candidate_fields` (OCR bruto) → `null`.
**Justificación**:
- Refleja lo que el operador realmente ve y corrige (valor validado automáticamente)
- Si no hubo validación, usa candidato OCR
- Campo nuevo manual = `null` (no había valor previo)
**Evidencia**: `review_service.py` línea `original_value = validated_fields.get(field, candidate_fields.get(field))`

### 6. Frontend: Modal Obligatorio + localStorage
**Origen**: Spec CA #5, Caso borde #8
**Decisión**: Modal al cargar app si no hay config; guarda en `localStorage` clave `gi_ocr_operator`.
**Justificación**:
- Fuerza configuración antes de cualquier acción
- Persiste entre sesiones sin backend de sesión
- Badge visible confirma operador/rol actual
**Evidencia**: `app.js:loadOperatorConfig`, `showOperatorModal`, `getAuthHeaders` inyecta en todos los fetch

### 7. UI Condicional: Operador no ve "Reintentar" en Jobs Ajenos
**Origen**: Spec CA #5, Matriz permisos
**Decisión**: `renderQueue` verifica `job.result.processing_metadata.operator_id` vs `operatorConfig.id`.
**Justificación**:
- Feedback visual inmediato de permisos
- Evita 403 innecesarios por clicks en botones no permitidos
**Evidencia**: `app.js:renderQueue` lógica `canRetry`

### 8. Sin Archivo Separado de Auditoría
**Origen**: Spec CA #6, Riesgo #4
**Decisión**: `audit_trail` viaja dentro del JSON confirmado, replicado a `storage_bridge/ready/`.
**Justificación**:
- `storage_bridge_writer` ya existe y copia JSON confirmado
- Un solo expediente por documento para legacy
- No duplicar infraestructura de archivos
**Evidencia**: `review_service.py` retorna `audit_trail` en response y persiste en confirmed doc

### 9. Validación Estricta de Headers (400/403)
**Origen**: Spec Casos borde #2, #3
**Decisión**: 400 si header faltante/vacío; 403 si rol no en enum válido; sin default a operator.
**Justificación**:
- Fail-fast: configuración incorrecta se detecta inmediatamente
- No asumir rol por defecto (seguridad)
**Evidencia**: `authz.py:_get_operator_id`, `_get_operator_role` lanzan HTTPException

### 10. Concurrencia: Último en Escribir Gana (sin Locking)
**Origen**: Spec Caso borde #6
**Decisión**: No implementar locking de archivos; ambos operadores generan entrada en `audit_trail`.
**Justificación**:
- Fase local, baja concurrencia esperada
- `audit_trail` captura ambas acciones (historial completo)
- Locking añade complejidad (BD, redis, file locks) fuera de scope
**Evidencia**: `job_store.py:save_confirmed` escribe directo; sin mecanismo de bloqueo

---

## Cambios en Archivos (Resumen)

### Nuevos
- `backend/app/authz.py` — middleware autorización
- `docs/tecnica/auditoria-permisos-operador.md`
- `docs/usuario/auditoria-permisos-operador.md`

### Modificados
- `backend/app/review_service.py` — `confirm_review` extendido con `operator_id`, `operator_role`, `audit_trail`
- `backend/app/job_queue.py` — `enqueue` acepta `operator_id`/`operator_role`; `_process` propaga a pipeline
- `backend/app/capture_pipeline.py` — `process_document`, `process_image`, `_process_pdf`, `_process_pdf_native`, `_quality_rejected_result` propagan operator metadata
- `backend/app/main.py` — imports authz; `create_jobs`, `confirm_job`, `retry_job`, `inbound_config`, `export_batch` con deps autorización; `_on_new_inbound` usa system/admin
- `frontend/src/app.js` — `getAuthHeaders`, `loadOperatorConfig`, modal, `renderQueue` con owner check, init flow
- `frontend/index.html` — modal HTML, badge operador
- `frontend/src/style.css` — estilos modal, badges roles, job-owner
- `docs/tecnica/index.md` — link
- `docs/usuario/index.md` — link