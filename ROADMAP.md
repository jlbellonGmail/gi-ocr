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
- [ ] 03-empaquetado-despliegue — Decisión de despliegue (Dockerfile,
      `release.yml`, destino) una vez que exista una decisión de
      infraestructura concreta. No se inicia sin esa decisión (ver
      `docs/tecnica/arquitectura.md`).
- [-] 04-cierre-operativo-circuito-agentico — Endurecer el uso cotidiano
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





