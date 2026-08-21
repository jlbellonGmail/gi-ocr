```yaml
status: approved
attempt: 1
feedback: []
```

# Test report — 16-administracion-servicios-documentos (intento 1)

## Resumen

Suite completa de `pytest` (`backend/tests/` + `tests/`) corrida contra el
worktree `D:\proyectos\worktrees\16-administracion-servicios-documentos`,
rama `feature/16-administracion-servicios-documentos`, commit
`82e2b79` (verificado con `git log --oneline -5` al inicio de esta
sesión). No existe `.venv` propio del worktree; se usó el intérprete del
`.venv` de `D:\proyectos\gi-ocr` (mismo repo, mismas dependencias
instaladas — `backend/requirements.txt` no cambió en esta feature).

Nota de entorno: no se reprodujo el problema de permisos de
`tmp_path`/`C:\Users\jlbel\AppData\Local\Temp\pytest-of-jlbellon` reportado
por el builder-agent en esta corrida (posiblemente ya limpio de una
corrida anterior). Por prolijidad se usó igualmente `--basetemp` propio
apuntando al scratchpad de esta sesión, para evitar cualquier colisión.

```
293 passed, 6 skipped, 31 warnings in 528.28s (0:08:48)
```

6 skips, todos por motivos de entorno ya documentados/preexistentes, no
relacionados con esta feature:
- `test_e2e_playwright.py` (falta el paquete `playwright`, no instalado).
- 5 tests de `test_api_jobs.py`/`test_local_samples_real.py` (muestras
  privadas locales no disponibles, `.gitignore`d por diseño).

Cero fallos. Corrida focalizada de los tests nuevos y de los archivos de
regresión explícitamente listados en el spec (criterio 16), para
verificación adicional y con salida legible:

```
backend/tests/test_services_config_schema.py — 23 passed
backend/tests/test_services_admin_api.py — 8 passed
Total tests nuevos: 31 passed, 0 failed

backend/tests/test_document_services_inventory.py — 8 passed
backend/tests/test_gas_extractor.py — 16 passed
backend/tests/test_empty_text.py — 5 passed
backend/tests/test_evaluate_ocr_service_data_output.py — 18 passed
Total regresión explícita del spec: 47 passed, 0 failed
```

## Verificación de criterios de aceptación

Verificación hecha leyendo el código real (`backend/app/services_config.py`,
`backend/app/extraction_engine.py`, `backend/app/main.py`) y los tests
nuevos línea por línea, no solo confiando en el reporte del builder-agent
ni en los nombres de archivo/test.

| # | Criterio | Cumplido | Evidencia |
|---|---|---|---|
| 1 | `services.ini` real (GAS/CEVT) válido sin cambios | Sí | `test_real_services_ini_passes_schema_validation` (pasa); releída `services_config.validate_services_schema()`: no lanza para 0 violaciones. |
| 2 | `Fields` vacío/ausente falla nombrando sección+clave | Sí | `test_missing_fields_key_fails_naming_section_and_key`, `test_empty_fields_key_fails`; código en `_validate_section_schema` (líneas 287-292 de `services_config.py`) nombra `[section]` y `'Fields'` explícitamente. |
| 3 | Campo en `Fields` sin bloque `Field.<nombre>.*` falla nombrando sección+campo | Sí | `test_field_without_block_fails_naming_section_and_field`; `_validate_field_block` levanta con sección+campo en el primer chequeo (`Label` faltante) cuando no existe ningún bloque. |
| 4 | Bloque huérfano falla nombrando sección+campo huérfano | Sí | `test_orphan_field_block_fails`; `_iter_field_block_names` + diff contra `Fields` en `_validate_section_schema` (líneas 310-319). |
| 5 | `Type` fuera de `{text,amount,date}` falla listando tipos permitidos | Sí | `test_invalid_type_fails_listing_allowed_types`; mensaje incluye los 3 tipos vía `', '.join(ALLOWED_FIELD_TYPES)`. |
| 6 | `Required` fuera de `true`/`false` falla (sin default silencioso) | Sí | `test_invalid_required_value_fails` parametrizado (`si`, vacío, clave ausente — 3 casos); código usa `required_raw is None or ... not in ALLOWED_REQUIRED_VALUES`, no asume `false`. |
| 7 | `Regex` inválida (no compila) falla con mensaje de `re.error` | Sí | `test_invalid_regex_fails_with_re_error_message`; `except re.error as exc` envuelve el mensaje de `re.error` en el `ServicesConfigError`. |
| 8 | `Regex` válida sin grupo de captura falla explicando la razón | Sí — verificado leyendo código, no solo el test | `compiled.groups < 1` (línea 264 `services_config.py`) levanta con "al menos un grupo de captura, para no capturar el match completo (incluyendo texto de anclaje)". `test_regex_without_capture_group_fails` usa `Regex=\d{4,15}` (sin paréntesis) y verifica el string "grupo de captura" en el mensaje. |
| 9 | Campo sin `Regex` (solo `Patterns`) falla explícitamente | Sí — verificado leyendo código, no solo el test | `_validate_field_block`: `if not regex_raw: raise ...` ocurre **antes** de cualquier chequeo de `Patterns`, es decir declarar solo `Patterns` nunca es suficiente. `test_missing_regex_with_only_patterns_fails` reproduce exactamente ese caso (`Field.cliente.Patterns` sin `Field.cliente.Regex`) y verifica que el mensaje mencione tanto `Regex` como `Patterns`. |
| 10 | Nombres duplicados en `Fields` falla nombrando el duplicado | Sí | `test_duplicate_field_names_in_fields_fails`; comparación case-insensitive con `set` en `_validate_section_schema` (líneas 301-308). |
| 11 | Bug de desconexión corregido: `extraction_engine` usa `Field.<nombre>.Regex` real | Sí — verificado leyendo código y trazando el caso a mano | `extract_service_fields()` en `extraction_engine.py` (líneas 87-88) intenta `_extract_with_field_regex` **antes** de `_extract_with_patterns`/`_extract_generic`. Trazado manual: `_extract_generic("cliente", "Medidor 12345678 Cliente 045-987654")` → `re.search(r"(\d{8,10})", ...)` matchea `"12345678"` primero (confirmado, coincide con `test_extract_generic_reproduces_the_documented_bug`). `extract_service_fields("GAS", texto)["fields"]["cliente"]` → `"045-987654"` vía `Field.cliente.Regex=(?:cliente|nro cliente|n° cliente|numero cliente)\D{0,40}([0-9\-]{6,20})`, ancla a "Cliente" y captura el grupo — confirmado con `test_extract_service_fields_gas_cliente_uses_declared_regex`, que además hace `assert ... != "12345678"` explícito. Caso adicional CEVT (`medidor_numero == "12345"`) también pasa. Fallback a `_extract_generic` sin `Regex` declarada verificado con `test_extract_generic_still_used_as_fallback_without_declared_regex`. |
| 12 | `GET /api/v1/services`/`GET /api/v1/services/{id}`, 404 para inexistente, 200 con lista vacía sin servicios | Sí — verificado leyendo código y ejecutando requests reales vía `TestClient` | `main.py` líneas 120-146: `list_services()` → `try/except ServicesConfigError → HTTPException(500,...)`; `get_service(service_id)` normaliza con `normalize_service_id` y usa `except ServiceNotFoundError → 404` / `except ServicesConfigError → 500` (nunca deja pasar un 500 sin `str(e)` en el detail). Tests: `test_get_unknown_service_returns_404_not_500` (404, mensaje incluye el id), `test_list_services_empty_ini_returns_200_with_empty_list` (200, `{"services": []}`), `test_list_services_invalid_section_does_not_return_bare_500`/`test_get_service_invalid_section_does_not_return_bare_500` (500 pero con sección+clave en el detail, sin `Traceback`) — todos pasan. |
| 13 | Guía de alta en `docs/usuario/administracion-servicios-documentos.md`: ejemplo correcto, incorrecto con error real y mensaje exacto, CLI, HTTP request+response | Sí | Doc contiene sección `[AGUA]` correcta (líneas 21-41), incorrecta sin `Field.cuenta.Regex` con el mensaje textual exacto que produce `_validate_field_block` (líneas 56-87), comando CLI de `evaluate_ocr_service.py --service AGUA --samples ...` (línea 109), y ejemplos HTTP completos request+response de ambos endpoints contra `services.ini` real (líneas 131-219). |
| 14 | `docs/tecnica/administracion-servicios-documentos.md` no vacío, con esquema, algoritmo, bug corregido, relación con `document_services.json`, aclaración pipeline en vivo, `Patterns` documental, tercer mecanismo muerto | Sí | Documento de 348 líneas cubre las 8 secciones exigidas explícitamente (verificado leyendo el archivo completo). |
| 15 | `decision.md` + enlaces exactos en ambos índices | Sí | `decision.md` no vacío (166 líneas, decisiones demostrables trazables a `audit-1.md`/`audit-2.md`/código). `Assert-IndexLink` corrida manualmente con `Title="Administracion de Servicios y Documentos"` confirma un único enlace exacto `- [Administracion de Servicios y Documentos](administracion-servicios-documentos.md)` en `docs/tecnica/index.md` y `docs/usuario/index.md`. |
| 16 | Tests contractuales cubren 1-12, corren en verde, sin regresión | Sí | Ver conteos arriba: 31/31 tests nuevos passed, 47/47 tests de regresión explícitamente listados passed, 293/293 de la suite completa passed (6 skips por entorno, no por código). |

## Verificación del contrato común (`scripts/feature-contract.ps1`)

Ejecutado `Get-FeatureInfo`/`Assert-IndexLink`/`Assert-NonEmptyFile` desde
PowerShell contra el worktree:

- `runs/16-administracion-servicios-documentos/decision.md` — existe, no vacío.
- `runs/16-administracion-servicios-documentos/spec.md` — existe, no vacío (intento 2, aprobado en `audit-2.md`).
- `docs/tecnica/administracion-servicios-documentos.md` — existe, no vacío.
- `docs/usuario/administracion-servicios-documentos.md` — existe, no vacío.
- Al menos un `audit-N.md` en `runs/16-administracion-servicios-documentos/` — `audit-1.md` (rejected) y `audit-2.md` (approved) presentes.
- Enlace exacto en `docs/tecnica/index.md`: `- [Administracion de Servicios y Documentos](administracion-servicios-documentos.md)` — confirmado con `Assert-IndexLink` (título exacto usado por el builder-agent: "Administracion de Servicios y Documentos", distinto del título auto-derivado por defecto del slug — hay que pasar `-Title` explícito al invocar `ready-for-pr.ps1`/`Assert-FeatureContract` para que el chequeo de contrato pase).
- Enlace exacto en `docs/usuario/index.md`: ídem, confirmado.
- `test-report-N.md` — antes de esta corrida faltaba (`Assert-FeatureContract` fallaba con "Falta al menos un test-report-N.md"); se resuelve al commitear este mismo archivo.

`Assert-FeatureContract -Slug '16-administracion-servicios-documentos' -Title 'Administracion de Servicios y Documentos'` queda satisfecho una vez commiteado este `test-report-1.md`.

## Hallazgos

Ninguno que bloquee la aprobación. Un punto operativo, no de código, para
quien corra `ready-for-pr.ps1` a continuación: debe invocarse con
`-Title 'Administracion de Servicios y Documentos'` (el título exacto ya
usado en ambos índices), no con el título por defecto derivado del slug
(`ready-for-pr.ps1` lo derivaría como "Administracion Servicios
Documentos" si no se pasa `-Title`, lo cual generaría una discrepancia de
título con los enlaces ya existentes en los índices y `Assert-IndexLink`
fallaría). Se verificó explícitamente con `Assert-IndexLink` que el
título correcto y ya commiteado es "Administracion de Servicios y
Documentos".

## Veredicto

`approved`. Todos los criterios de aceptación 1-16 verificados con
evidencia directa (código leído, tests corridos con salida real, no solo
reproducción de lo reportado por el builder-agent). Sin regresiones en la
suite completa (293 passed, 6 skipped por motivos de entorno
preexistentes, 0 failed). Contrato de artefactos completo salvo este
mismo `test-report-1.md`, que se commitea como parte de este veredicto.
Queda lista para pasar a `READY_FOR_PR` en `ROADMAP.md`.
