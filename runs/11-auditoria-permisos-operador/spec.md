# Spec: 11-auditoria-permisos-operador

## Alcance

**Incluye:**
1. **Auditoría completa de correcciones humanas**: extender el endpoint de confirmación de revisión (`/api/v1/jobs/{job_id}/confirm`) para registrar, por cada campo corregido/rechazado/confirmado: operador (identidad), valor original (del OCR/validación automática), valor final (ingresado por operador), fecha/hora UTC, motivo (ya existe `reason`), acción (confirmado/corregido/sin resolver). El registro debe ser inmutable y trazable.
2. **Modelo de permisos mínimos por rol**: definir tres roles (operador, revisor, admin) con matriz de permisos para cuando el producto deje de ser monousuario local. Implementar enforcement en backend (middleware/dependencies) y gating en frontend (UI condicional).
3. **Persistencia de auditoría**: almacenar traza de auditoría junto al resultado confirmado (`output/confirmed/{job_id}.confirmed.json`) y replicar en `storage_bridge/ready/` como parte del expediente para el sistema legacy.

**NO incluye:**
- Autenticación/autorización completa (login, tokens, SSO, OAuth) — solo modelo de roles y enforcement básico; la identidad del operador se pasa como header `X-Operator-Id` y `X-Operator-Role` en esta fase (preparación para auth futuro).
- Gestión de usuarios/roles en UI (CRUD de usuarios, asignación de roles) — solo enforcement de lo que ya existe en request.
- Cambios en el formato `.DATA` de salida legacy — solo auditoría en JSON confirmado.
- Cambios en motor OCR, extracción, validación semántica, ni pipeline de preprocesamiento.

## Contexto

El producto hoy es **monousuario local**: no hay autenticación, cualquiera que acceda al frontend puede subir, revisar y confirmar documentos. La feature **10-consola-revision-humana-profesional** ya implementa la UI de revisión con estados `confirmed`/`corrected`/`unresolved` y motivo obligatorio. El backend (`review_service.confirm_review`) persiste `correction_reasons`, `confidence_at_review`, `decision_at_review`, `confirmed_at`.

**Gap actual**: no se registra **quién** hizo la corrección, **qué valor original** tenía el campo (antes de la corrección), ni hay **control de permisos** por rol. Para operación real (multioperador, trazabilidad legal, auditoría), se necesita:
- Identidad del operador en cada acción de revisión.
- Valor original inmutable (candidato OCR o validado automático) vs valor final.
- Roles con permisos mínimos: operador (carga + corrige propios), revisor (aprueba/corrige cualquier), admin (todo + config).

Esta feature prepara la base para multi-tenancy futuro (item 26 del roadmap) sin implementar auth completo hoy.

## Criterios de aceptación

1. **Endpoint de confirmación extendido**: `POST /api/v1/jobs/{job_id}/confirm` acepta headers `X-Operator-Id` (string, requerido) y `X-Operator-Role` (enum: `operator`|`reviewer`|`admin`, requerido). Valida que el rol tenga permiso para la acción solicitada (ver matriz abajo). Rechaza con 403 si no tiene permiso.
2. **Registro de auditoría por campo**: en `confirmation_metadata.audit_trail` (nuevo array), cada entrada contiene: `field`, `operator_id`, `operator_role`, `original_value`, `final_value`, `action` (`confirmed`|`corrected`|`unresolved`), `reason`, `timestamp` (ISO 8601 UTC). `original_value` se toma de `validated_fields` (resultado automático previo a revisión) o `candidate_fields` si no hubo validación.
3. **Matriz de permisos (enforcement backend)**:
   - `operator`: puede `confirm` (confirmar sin cambios), `correct` (corregir campos), `unresolve` (marcar sin resolver) **solo en jobs propios** (jobs creados por ese operator_id). No puede confirmar jobs de otros.
   - `reviewer`: permisos de `operator` + puede `confirm`/`correct`/`unresolve` **en cualquier job**. Puede forzar `confirmed` en campos `unresolved` de operadores.
   - `admin`: permisos de `reviewer` + acceso a endpoints de configuración (`/api/v1/services`, `/api/v1/inbound/config`), gestión de cola (retry, cancel), export batch.
4. **Middleware de autorización**: nuevo `authz.py` con `require_role(roles: list[str])` y `require_job_owner_or_reviewer(job_id, operator_id, role)` como `Depends` en endpoints protegidos.
5. **Frontend**: header `X-Operator-Id` y `X-Operator-Role` configurables en `localStorage` (clave `gi_ocr_operator`), enviados en todas las llamadas a `/confirm`, `/jobs/*/retry`, `/inbound/config`, `/export`. UI muestra badge con operador/rol actual. Botones/acciones deshabilitados según rol (p.ej. operador no ve "Reintentar" en jobs ajenos).
6. **Persistencia en JSON confirmado**: `confirmation_metadata.audit_trail` escrito en `output/confirmed/{job_id}.confirmed.json` y copiado a `storage_bridge/ready/{doc_type}_{job_id[:8]}.json` (ya hace `storage_bridge_writer`).
7. **Documentación técnica**: `docs/tecnica/auditoria-permisos-operador.md` no vacía, con algoritmo de autorización, modelo de datos de auditoría, decisiones de diseño (header-based identity, no JWT aún), casos borde.
8. **Documentación de usuario**: `docs/usuario/auditoria-permisos-operador.md` no vacía, con propósito, matriz de permisos, ejemplo request/response confirmación con headers, ejemplo de audit_trail en respuesta.
9. **Enlaces en índices**: entradas exactas en `docs/tecnica/index.md` y `docs/usuario/index.md` apuntando a los .md creados.
10. **Decision.md**: `runs/11-auditoria-permisos-operador/decision.md` con decisiones demostrables (por qué header-based, por qué no JWT ahora, estructura audit_trail, matriz de permisos elegida).

## Casos borde a contemplar

1. **Job sin owner previo** (jobs creados antes de esta feature o vía inbound watcher): `operator_id` = `system`, `operator_role` = `admin`. Operadores/revisores pueden tomar ownership al confirmar primera vez.
2. **Header faltante/inválido**: rechazar 400 con mensaje claro antes de procesar correcciones.
3. **Rol desconocido**: rechazar 403, no default a operador.
4. **Campo sin valor original** (nuevo campo agregado manualmente en UI): `original_value` = `null`, `action` = `corrected`.
5. **Corrección múltiple mismo campo en una request**: solo la última cuenta; auditoría registra una entrada por campo con valor final.
6. **Concurrencia**: dos operadores confirman mismo job simultáneamente — último en escribir gana (archivo JSON), pero ambos generan entrada en audit_trail. No hay locking en esta fase.
7. **Job confirmado parcialmente (unresolved)**: revisor posterior puede corregir/confirmar campos `unresolved`; auditoría añade nuevas entradas, no sobrescribe previas.
8. **Frontend sin localStorage configurado**: mostrar modal de configuración obligatoria antes de permitir confirmar.

## Riesgos / supuestos

1. **Identidad vía headers (no JWT)**: decisión explícita para no bloquear en auth completo. Header `X-Operator-Id` es de confianza en entorno local/controlado. Documentar como deuda técnica: migrar a JWT/OIDC en feature futura (item 26).
2. **Ownership de jobs inbound**: jobs del watcher no tienen owner. Se asumen `system/admin`. Revisor/admin pueden procesarlos. Operador no puede (403) salvo que se implemente "tomar ownership" — fuera de scope.
3. **No hay BD**: persistencia en archivos JSON (`output/confirmed/`). Auditoría crece linealmente con campos confirmados. Para volúmenes altos, requerirá migración a BD (fuera de scope).
4. **Permisos en storage_bridge**: `storage_bridge_writer` ya copia JSON confirmado a `ready/`. Auditoría viaja dentro. No se agrega archivo separado de auditoría.
5. **Frontend localStorage**: no es seguro (manipulable por usuario). Aceptable para fase local; en multi-tenancy real requerirá session server-side.
6. **Matriz de permisos fija en código**: no configurable por `services.ini`. Si se necesita granularidad por servicio, será feature futura.
7. **No se modifica `services.ini`**: esta feature es transversal, no por servicio.
8. **Campo `provider`/`service` en validated_fields**: se excluye de auditoría (campo interno, no editable por operador).