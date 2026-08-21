# Decision: 16-administracion-servicios-documentos - Administración de servicios/documentos

## Estado

Implementación completa por `builder-agent`, lista para revisión de
`qa-agent`. No es una decisión de merge (eso corresponde al HITL final
sobre la PR); este documento registra las decisiones demostrables
tomadas durante spec → auditoría → implementación, tal como exige
`AGENTS.md`.

## Evidencias revisadas

- `runs/16-administracion-servicios-documentos/spec.md` (intento 2,
  aprobado).
- `runs/16-administracion-servicios-documentos/audit-1.md` (rechazado,
  dos motivos concretos).
- `runs/16-administracion-servicios-documentos/audit-2.md` (aprobado,
  ambos motivos verificados como corregidos).
- Código real leído directamente antes de implementar:
  `backend/app/services_config.py`, `backend/app/extraction_engine.py`,
  `backend/app/document_services.py`, `backend/app/main.py`,
  `backend/config/services.ini`.

## Decisiones demostrables

### 1. `Regex` obligatoria por campo; `Patterns` opcional y puramente documental

Origen: rechazo del intento 1 del spec (`audit-1.md`, segundo punto de
feedback) — el intento 1 dejaba el esquema aceptando "Patterns o Regex"
mientras el arreglo de comportamiento solo conectaba `Regex`, lo que
permitía que un campo declarado solo con `Patterns` pasara la validación
"profesional" y siguiera cayendo para siempre en el fallback genérico
(`_extract_generic`), reproduciendo el mismo defecto de "documentación
muerta" que la feature dice corregir.

Corrección adoptada en el intento 2 del spec y verificada por
`reviewer-agent` en `audit-2.md`: `Field.<nombre>.Regex` es obligatoria
para todo campo (`services_config._validate_field_block`, criterio 9);
`Field.<nombre>.Patterns` es opcional, y si está presente solo se exige
que no esté vacía — no se valida su formato ni se conecta a extracción.

Implementado en `backend/app/services_config.py::_validate_field_block`:
un campo sin `Field.<nombre>.Regex` (ausente, vacía, o sin bloque) falla
la validación con un mensaje que dice explícitamente que declarar
únicamente `Patterns` no es suficiente. Verificado que el `services.ini`
real (`GAS`, `CEVT`, 10 campos) no se rompe: los 10 ya declaraban
`Regex` con grupo de captura antes de esta feature (test de regresión
`test_real_services_ini_passes_schema_validation`).

Justificación técnica (por qué no conectar `Patterns` en su lugar, ya
documentada en el spec y re-verificada durante la implementación): los
valores reales de `Field.<nombre>.Patterns` (ej.
`cliente|nro cliente|n° cliente|numero cliente`) son alternancias de
palabras clave sin grupo de captura. Conectarlos tal cual a
`extraction_engine._extract_with_patterns` devolvería `match.group(0)`
(el texto del ancla matcheado) en vez del valor real — produciría
salidas incorrectas, no una alternativa funcional. Rediseñar `Patterns`
para que sea funcional es trabajo nuevo, no pedido por el ítem `16` de
`ROADMAP.md`.

### 2. Corrección del bug de desconexión: `field_regex` nuevo en `get_service_config`, usado por `extraction_engine.py`

Origen: contexto del spec, verificado por trazado directo del código
antes de implementar (no asumido) — `get_service_config()` solo exponía
`fields`/`zones`/`patterns`; `zones`/`patterns` leen claves de sección en
minúscula que ningún `services.ini` real declara, por lo que quedaban
siempre vacías y `extraction_engine.py` nunca llegaba a aplicar
`Field.<nombre>.Regex`.

Decisión de implementación: agregar `get_service_field_regex(service)`
(función nueva) y la clave `"field_regex"` a `get_service_config()`
(extensión, sin remover `zones`/`patterns` — se conservan por
compatibilidad hacia atrás y quedan documentadas como mecanismo muerto).
`extraction_engine.py::extract_service_fields()` se modificó para
intentar `_extract_with_field_regex` (función nueva) **antes** del
fallback `_extract_generic()`, preservando el orden de resolución
existente para zonas/patrones legados y dejando `_extract_generic` sin
cambios como red de seguridad final.

Verificado con el caso de dominio exacto pedido por el criterio 11 del
spec (`"Medidor 12345678 Cliente 045-987654"`, servicio `GAS`):

- `_extract_generic("cliente", texto)` devuelve `"12345678"` (el número
  de medidor, sin anclaje de contexto) — reproducido literalmente en
  `test_extract_generic_reproduces_the_documented_bug`.
- `extract_service_fields("GAS", texto)["fields"]["cliente"]` devuelve
  `"045-987654"` tras la corrección — verificado en
  `test_extract_service_fields_gas_cliente_uses_declared_regex`.
- Caso de regresión adicional con `CEVT` (pedido explícitamente por el
  criterio 11): `medidor_numero` extraído correctamente vía
  `Field.medidor_numero.Regex` —
  `test_extract_service_fields_cevt_uses_declared_regex`.

Se verificó además que las pruebas preexistentes que llaman a
`extract_service_fields`/`_extract_generic` directamente
(`backend/tests/test_empty_text.py`,
`backend/tests/test_gas_extractor.py`) siguen pasando sin modificación,
trazando manualmente cada caso contra el nuevo orden de resolución antes
de correr la suite (documentado en el reporte de QA).

### 3. Endpoint HTTP nuevo `GET /api/v1/services[/{service_id}]`, sin autenticación

Origen: Riesgos/supuestos del spec — se evaluó agregar el endpoint en
vez de limitarse a ejemplos de CLI para `docs/usuario/`, dado que esta
feature (validación de config + DATA evaluator) no tenía ningún endpoint
HTTP existente al que enganchar un ejemplo real.

Decisión: agregar los dos endpoints de solo lectura en
`backend/app/main.py`, construidos sobre
`services_config.list_services_schema()`/`get_service_schema()` (que
reusan la misma validación de esquema del punto 1 — no hay dos caminos
de validación divergentes). Sin autenticación: es de solo lectura, no
expone datos de comprobantes ni de clientes, y el resto de `/api/v1/*`
tampoco tiene auth hoy (`14-seguridad-privacidad-documentos` queda
pendiente en el backlog para eso).

Casos borde resueltos explícitamente en la implementación (criterio 12
del spec):

- `services.ini` sin secciones → `GET /api/v1/services` responde `200`
  con `{"services": []}`, no error (`test_list_services_empty_ini_returns_200_with_empty_list`).
- Servicio no configurado → `404` con mensaje claro
  (`test_get_unknown_service_returns_404_not_500`), nunca `500`.
- Sección inválida según esquema → `500`, pero con el mismo mensaje
  accionable (sección, campo, clave) que produce la validación de carga,
  nunca una traza cruda
  (`test_list_services_invalid_section_does_not_return_bare_500`,
  `test_get_service_invalid_section_does_not_return_bare_500`).
- Normalización de `service_id` igual que
  `document_services.normalize_service_id` (`strip().upper()`):
  `gas`, `GAS`, `%20gas%20` resuelven al mismo servicio
  (`test_get_service_detail_normalizes_lowercase`,
  `test_get_service_detail_normalizes_surrounding_spaces`).

### 4. No se toca el pipeline HTTP en vivo ni `gas_extractor.py`

Confirmado por grep antes de implementar: ningún módulo del pipeline en
vivo (`capture_pipeline.py`, `classifier.py`, `templates/providers.py`)
ni `gas_extractor.py` importa `services_config`/`extraction_engine`. Los
cambios de esta feature (services_config.py, extraction_engine.py,
main.py) no tienen ninguna superficie de impacto sobre esos módulos,
confirmando la separación documentada en el spec y en
`docs/tecnica/administracion-servicios-documentos.md`.

### 5. Mensajes de error de esquema: siempre sección + campo + clave, nunca traza cruda

Implementado sistemáticamente en `services_config.py`: toda excepción de
esquema es `ServicesConfigError` (subclase de `ValueError`, nunca
`KeyError`/`configparser.Error`/`re.error` sin envolver) con mensaje que
nombra la sección entre corchetes, el nombre de campo entre comillas
simples, y la clave `Field.<nombre>.<Clave>` exacta. Se envuelven
también los errores de bajo nivel de `configparser`
(`DuplicateSectionError`, `DuplicateOptionError`) y `UnicodeDecodeError`
en `_load_parser()`, con el mismo criterio de mensaje accionable.

## Resultado

Implementación, tests contractuales
(`backend/tests/test_services_config_schema.py`,
`backend/tests/test_services_admin_api.py`) y documentación
(`docs/tecnica/administracion-servicios-documentos.md`,
`docs/usuario/administracion-servicios-documentos.md`) completas en la
rama `feature/16-administracion-servicios-documentos`. Queda para
`qa-agent` correr la suite completa y verificar el contrato de artefactos
(`Assert-FeatureContract`) antes de marcar `ROADMAP.md` como
`READY_FOR_PR`.
