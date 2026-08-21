# Roadmap: gi-ocr (Smart Invoice Capture)

Cada feature nueva se implementa siguiendo el circuito agéntico de
[AGENTS.md](AGENTS.md): Analyst → Reviewer → Builder → QA →
`[-] READY_FOR_PR` → PR → CI verde → HITL (único punto de aprobación
humana) → Merge → `[x]`, con su carpeta de evidencia en
`runs/<NN>-<slug>/` y su documentación en `docs/tecnica/<slug>.md` +
`docs/usuario/<slug>.md`.

Este archivo refleja el estado **verificado** del proyecto (código, tests
corridos, `git log`), no expectativas. No se marca `[x]` antes del merge
a `develop` (ver estados más abajo).

## Propósito del producto

Capturar un comprobante (inicialmente `GAS`) desde un frontend web
mobile-first, procesarlo con OCR, extraer campos configurados por
servicio, validarlos semánticamente, permitir revisión/corrección humana
trazable, y generar una salida estructurada (`.DATA` + JSON confirmado)
para integración con un sistema externo/legacy vía `storage_bridge/`.

---

## Historial (features cerradas antes de este circuito)

Las siguientes etapas están **mergeadas en `main`/`develop`**
(verificado: `main` y `develop` apuntan al mismo commit,
`70a912d docs(governance): formally close T3.5 (HITL_APPROVED)`) y se
gobernaron con el circuito HITL-intensivo anterior (`GOVERNANCE.md`,
`governance/current-task.md`), ya reemplazado por `AGENTS.md`. No se
renumeran retroactivamente al esquema `NN-slug`; quedan documentadas acá
como contexto histórico.

- **Fase 0 — Baseline controlado**: estructura base, versionado, `VERSION`,
  `CHANGELOG.md`. Cerrada.
- **T2.x — Pipeline DATA interno**: escritura atómica del bridge
  (`storage_bridge_writer.py`), inventario de documentos/servicios,
  validación específica por servicio, evaluador DATA, métricas de campos
  rechazados. Cerrada como infraestructura interna (no como demo visible).
- **T3.1–T3.2 — Demo E2E y pipeline controlado**: documento/servicio
  controlado → salida estructurada (`document_processing_service.py`,
  `t3_2_orchestrator.py`). Cerrada.
- **T3.3 — Reporte de campos**: `accepted_fields`/`rejected_fields`/
  `missing_fields`/`summary_counts` (`field_reporting_processor.py`).
  Cerrada (`4a64188` → merge `70fe3b0`).
- **T3.4 — Flujo visible JSON**: imagen → OCR → candidatos → validación →
  `field_report` → JSON final, vía script reproducible
  (`scripts/t3_4_visible_flow.py`). Cerrada.
- **T3.5 — CLI de documento**: `scripts/process_document.py` con
  exportación JSON. Cerrada (`fd114ad`, cierre `70a912d`).

Validaciones reportadas en el cierre de T3.5: `pytest` en verde,
`validate_project.py` (removido en esta migración, ver
`docs/tecnica/arquitectura.md`) en verde.

---

## Estado actual verificado (2026-08-18)

**T4 — MVP web operable end-to-end (EasyOCR)** quedó **archivada sin
mergear**: estaba implementada y testeada en `feature/t4-mvp-web-operable`
(154 tests en verde), pero el mismo día se decidió explícitamente
priorizar una línea de trabajo distinta y más avanzada (ver abajo). El
commit se preserva en el tag `archive/t4-mvp-web-operable`; la rama se
eliminó. No se mezcla con el trabajo activo.

**01-captura-ocr-local-agil** es la línea real hacia el MVP operable:
reemplaza EasyOCR por RapidOCR/ONNX (2.35–2.57s por documento medido, vs
~30s de EasyOCR), agrega soporte multi-proveedor (GAS + CEVT), PDF, cola
de jobs y frontend nuevo. Existía como commit único local
(`feature/captura-ocr-local-agil`, nunca pusheado) desde el 2026-08-13;
se migró a `feature/01-captura-ocr-local-agil` en worktree propio
(`../worktrees/01-captura-ocr-local-agil/`), siguiendo el circuito
completo:

- `spec.md`/`audit-1.md` (approved)/`test-report-1.md` (approved)/
  `decision.md` en `runs/01-captura-ocr-local-agil/`.
- `docs/tecnica/captura-ocr-local-agil.md` +
  `docs/usuario/captura-ocr-local-agil.md`, enlazados en ambos índices.
- **Evidencia real (worktree, `.venv` sincronizado con el
  `backend/requirements.txt` de la rama):
  `pytest -q` → 197 passed, 6 skipped (motivo verificado: `playwright` no
  instalado, muestras privadas de facturas no disponibles), 0 failed.**
- `Assert-FeatureContract` (`scripts/feature-contract.ps1`) → **PASS**.
- Resuelve, con evidencia medida, la decisión de motor OCR pendiente en
  `docs/tecnica/arquitectura.md` (ADR-006), y el ítem que antes figuraba
  como `04-servicio-cevt` (CEVT ya viene soportado en las plantillas de
  esta feature) — ambos se retiran del backlog abajo para no dejar
  pendientes duplicados.

Sigue pendiente: PR contra `develop`, CI verde, y decisión HITL final
(`MERGE`/`NO MERGE`) — no se marca `[-]` en este archivo hasta que
`scripts/ready-for-pr.ps1` lo haga como parte de ese paso del circuito.

---

## Backlog (circuito `AGENTS.md`)

- [x] 01-captura-ocr-local-agil — Ver "Estado actual verificado" arriba.
- [x] 02-mejora-precision-ocr — Validar con datos reales lo que el
      two-pass ROI de `01-captura-ocr-local-agil` todavía no verificó:
      benchmark de lote (`scripts/benchmark_captura.py`, 400 documentos,
      p50/p95, memoria) y robustez con facturas reales adicionales más
      allá del fixture usado en desarrollo.
- [x] 03-empaquetado-despliegue — Decisión de despliegue (Dockerfile,
      `release.yml`, destino) una vez que exista una decisión de
      infraestructura concreta. No se inicia sin esa decisión (ver
      `docs/tecnica/arquitectura.md`).
- [x] 04-cierre-operativo-circuito-agentico — Endurecer el uso cotidiano
      del circuito (`AGENTS.md`) con `scripts/preflight.ps1` (diagnostico
      de herramientas y matriz worktree/rama/ROADMAP), `-Snapshot` no
      bloqueante en `wait-pr-ci.ps1`, arranque sin ventana visible en
      `start-local-reconciler.ps1`, reintento de push pendiente en
      `close-feature.ps1`, y reutilizacion del diagnostico generico de
      herramientas en `ready-for-pr.ps1`. Entrada de backlog agregada
      durante la implementacion al detectar que faltaba (ver
      `runs/04-cierre-operativo-circuito-agentico/decision.md`, seccion
      "Nota sobre ROADMAP.md"): el `ROADMAP.md` de `develop` al momento de
      arrancar esta feature ya no traia el backlog extendido que el spec
      aprobado asumia (solo llegaba hasta `03-empaquetado-despliegue`,
      tras el cierre de `02-mejora-precision-ocr`); se numero como `04`
      (siguiente NN libre) en vez de reusar `03` para no colisionar con
      `03-empaquetado-despliegue`, que se deja intacto.
- [ ] 05-correccion-orientacion-exif — Aplicar correctamente EXIF
      Orientation antes de OCR para fotos reales de celular. Debe cubrir
      orientaciones 90/180/270 y espejadas, tests sinteticos con EXIF,
      reemplazo o subordinacion de la heuristica actual por lectura
      confiable del tag, y evidencia de que RapidOCR recibe la imagen en
      orientacion correcta.
- [ ] 06-calidad-captura-mobile — Agregar control de calidad previo al OCR
      para fotos tomadas rapido: blur, baja resolucion, reflejos, sombras,
      documento cortado, mala perspectiva, mala iluminacion o encuadre
      insuficiente. Debe definir cuando procesar, cuando advertir y cuando
      pedir nueva foto.
- [ ] 07-preprocesamiento-documental-no-destructivo — Formalizar el
      pipeline de imagen preservando siempre el original y generando
      versiones preparadas trazables. Debe registrar transformaciones
      aplicadas: EXIF, deskew, perspectiva, escala, contraste y
      normalizacion, evitando que una mejora visual destruya ROI o datos
      utiles.
- [ ] 08-regresion-dataset-ocr — Crear suite permanente de regresion
      OCR/extraccion con fixtures anonimos o sinteticos controlados y
      expected outputs por proveedor, documento y campo. Debe funcionar
      como gate futuro para no romper precision ya validada.
- [ ] 09-confianza-y-enrutamiento-hitl — Definir scores y umbrales por
      campo: autoaceptar alta confianza, enviar baja confianza a revision
      humana y bloquear falsos positivos sensibles. Debe registrar
      confianza OCR, confianza de extraccion, validacion semantica y
      decision final.
- [ ] 10-consola-revision-humana-profesional — Completar la UI mobile de
      revision: imagen, texto OCR, candidatos, campos validados,
      rechazados y no encontrados, edicion manual, motivo de
      correccion/rechazo y confirmacion final antes de exportar.
- [ ] 11-auditoria-permisos-operador — Registrar quien corrigio que, valor
      original, valor final, fecha, motivo y accion. Preparar permisos
      minimos por rol operador/revisor/admin si el producto deja de ser
      monousuario local.
- [ ] 12-contrato-integracion-legacy-v2 — Versionar formalmente `.DATA` +
      JSON confirmado: encoding, separador, orden de campos, nombres de
      archivo, idempotencia, duplicados, reintentos, estados `ready/failed`
      y reconciliacion con el sistema externo.
- [ ] 13-observabilidad-operacion — Agregar logs estructurados, metricas y
      trazabilidad por job/documento: tiempos OCR, estado de cola, errores
      por etapa, campos aceptados/rechazados/no encontrados,
      health/readiness y runbook operativo.
- [-] 14-seguridad-privacidad-documentos — Endurecer uploads y
      almacenamiento: extension, MIME, firma de archivo, tamaño maximo,
      nombres aleatorios, permisos, retencion, anonimizacion y redaccion de
      datos sensibles en logs.
- [ ] 15-accesibilidad-ux-mobile — Alinear frontend mobile con buenas
      practicas de accesibilidad: errores claros, estados accesibles,
      contraste, reflow, targets tactiles, confirmaciones, foco visible y
      reduccion de entrada repetida.
- [ ] 16-administracion-servicios-documentos — Profesionalizar altas de
      proveedores/documentos en `services.ini`: validacion, documentacion
      automatica, campos requeridos/opcionales, reglas semanticas,
      ejemplos y tests contractuales.
- [ ] 17-pruebas-e2e-mobile-real — Agregar E2E con Playwright/perfiles
      mobile para upload, captura, polling de jobs, revision humana y
      confirmacion. Debe contemplar fixtures publicos y saltos explicitos
      para muestras privadas.
- [ ] 18-calidad-ci-supply-chain — Incorporar lint, formato, type checks,
      dependencias fijadas, auditoria basica de vulnerabilidades y CI
      reproducible, sin romper el baseline actual.
- [ ] 19-operacion-cola-reintentos-dlq — Robustecer cola/jobs:
      persistencia, reintentos configurables, dead-letter queue,
      backpressure, reanudacion tras reinicio y diagnostico de jobs
      trabados.
- [ ] 20-expediente-auditoria-documental — Crear un expediente unico por
      documento que agrupe foto original, imagen normalizada, texto OCR
      bruto, candidatos, campos validados/rechazados/no encontrados, JSON
      confirmado, `.DATA`, timestamps, operador y decisiones humanas. Debe
      incluir `document_id`, checksums/hash, manifest auditable y
      trazabilidad completa.
- [ ] 21-politica-almacenamiento-retencion — Definir donde vive cada dato
      y por cuanto tiempo: originales, imagenes preparadas, JSON, `.DATA`,
      logs, auditoria y temporales. Debe soportar modo local seguro,
      limpieza automatica, retencion configurable, exportacion para
      auditoria y borrado controlado.
- [ ] 22-sesion-captura-operador — Modelar apertura/cierre de sesion
      operativa: sesion de carga/revision, documentos asociados, operador,
      inicio, cierre, estado final, errores y resumen. Debe permitir saber
      que lote proceso cada operador, que quedo confirmado, pendiente o
      exportado.
- [ ] 23-backup-retencion-archivado — Implementar politica de backup,
      restore probado, archivado y limpieza. Debe cubrir expedientes,
      salidas legacy, JSON, configuracion critica y evidencia de auditoria,
      sin respaldar basura temporal ni datos fuera de politica.
- [ ] 24-mejora-continua-datos — Convertir correcciones humanas en mejora
      operativa: casos nuevos para dataset, reporte de drift, ranking de
      campos problematicos, proveedores con mas fallos y propuestas de
      ajuste de plantillas/reglas.
- [ ] 25-release-versionado-productivo — Formalizar releases: SemVer,
      changelog, PR `develop` → `main`, tags humanos, artefactos esperados,
      checklist, rollback y separacion clara entre merge de feature y
      release productivo.
- [ ] 26-version-cloud-multitenant — Diseñar una version v2
      SaaS/multitenant para clientes pagos en la nube. Debe definir
      aislamiento por tenant, autenticacion, roles, billing, limites de
      uso, almacenamiento seguro por cliente, cifrado, auditoria, backups,
      monitoreo, escalabilidad de OCR/jobs, costos por documento,
      cumplimiento legal y migracion desde modo local/on-premise. No
      bloquea el MVP local.

## Cómo se usa este archivo

1. El humano mantiene el backlog: agrega, renombra o reordena items.
2. Ningún item se marca `[x]` antes del merge a `develop`.
3. Después de QA aprobado, la automatización cambia `[ ]` → `[-]` en la
   rama de la feature (`scripts/ready-for-pr.ps1`) y lo lleva dentro de
   la PR.
4. Después del merge, GitHub Actions ejecuta
   `post-merge-close-feature.yml`, que invoca `scripts/close-feature.ps1`
   desde `develop` para cambiar `[-]` → `[x]`, commitear y pushear a
   `origin/develop`.
5. Al arrancar una feature se usa el número/slug de este archivo para
   crear `runs/<NN>-<slug>/` y la rama `feature/<NN>-<slug>` (en worktree
   propio bajo `../worktrees/<slug>/`).

**Patrón del ítem**: `NN` (dos dígitos, numeración secuencial), `slug` en
minúsculas con guiones, seguido de `—` y descripción corta en español.

