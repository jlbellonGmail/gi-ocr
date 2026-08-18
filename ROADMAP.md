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

**T4 — MVP web operable end-to-end** está **implementado y testeado en la
rama `feature/t4-mvp-web-operable`, pero todavía NO mergeado a `develop`
ni a `main`** (verificado: `git log main..feature/t4-mvp-web-operable`
muestra 3 commits propios de T4 que `main`/`develop` no tienen).

Lo que ya existe en esa rama (verificado con `pytest -q`: **154 passed, 0
failed** en `backend/tests/` con el `.venv` del proyecto):

- Endpoints tipados `POST /api/v1/process`, `POST /api/v1/process/{job_id}/confirm`,
  `GET /api/v1/process/{job_id}/json` (409 si no confirmado),
  `GET /api/v1/process/{job_id}/original`, `GET /api/v1/process/{job_id}/status`.
- Servicio de confirmación de revisión humana
  (`backend/app/review_confirmation_service.py`): preserva originales,
  traza correcciones, valida por tipo de campo, genera nombre de archivo
  seguro.
- Frontend (`frontend/`) con preview, estados visuales y edición de
  campos, servido por FastAPI en el mismo origen.
- `/api/v1/capture` legacy conservado sin modificar.
- Spec de la etapa: `specs/t4-mvp-web-operable.md` (pre-circuito).

Lo que falta para que T4 pueda cerrarse **por este circuito** (no es
código nuevo, es completar el contrato de `AGENTS.md`):

- `runs/01-mvp-web-operable/spec.md`, `audit-N.md`, `test-report-N.md`,
  `decision.md`.
- `docs/tecnica/mvp-web-operable.md` y `docs/usuario/mvp-web-operable.md`
  (distinto de `docs/tecnica/gas.md`/`docs/usuario/gas.md`, que documentan
  el servicio GAS en sí, no el flujo web de confirmación).
- Enlaces exactos en `docs/tecnica/index.md` y `docs/usuario/index.md`.
- PR de `feature/t4-mvp-web-operable` (o de una rama `feature/01-mvp-web-operable`
  que retome ese trabajo) hacia `develop`, con CI verde.
- Decisión HITL final (`MERGE`/`NO MERGE`).

No se marca `[-]` todavía porque ese contrato de artefactos no existe: no
hay que inventar avance de proceso que no ocurrió.

---

## Backlog (circuito `AGENTS.md`)

- [ ] 01-mvp-web-operable — Cerrar el MVP web operable end-to-end (T4)
      por el circuito de `AGENTS.md`: producir `spec.md`/`audit-N.md`/
      `test-report-N.md`/`decision.md` en `runs/01-mvp-web-operable/`,
      escribir `docs/tecnica/mvp-web-operable.md` +
      `docs/usuario/mvp-web-operable.md`, y llevar la implementación ya
      existente (rama `feature/t4-mvp-web-operable`) a PR contra `develop`
      con CI verde para la decisión HITL final. Es la etapa que cierra el
      "MVP operable" descripto en el propósito del producto.
- [ ] 02-mejora-precision-ocr — Preprocesamiento de imagen, recorte/guía
      visual, métrica simple de confianza, comparación de resultados
      antes/después con fixtures por servicio (continúa la antigua Fase 5
      del roadmap pre-circuito).
- [ ] 03-evaluacion-motor-ocr — Matriz comparativa de motores (EasyOCR
      actual vs. Tesseract, PaddleOCR, Google Document AI, Azure Document
      Intelligence) con fixtures reales y decisión documentada en
      `docs/tecnica/arquitectura.md` (continúa la antigua Fase 6).
- [ ] 04-servicio-cevt — Activar el segundo servicio ya configurado en
      `backend/config/services.ini` (`[CEVT]`) end-to-end (extracción,
      validación semántica, salida `.DATA`, docs), como primera prueba de
      que agregar un servicio es solo configuración (ADR-007) y no
      requiere un extractor Python nuevo.
- [ ] 05-empaquetado-despliegue — Decisión de despliegue (Dockerfile,
      `release.yml`, destino) una vez que exista una decisión de
      infraestructura concreta. No se inicia sin esa decisión (ver
      `docs/tecnica/arquitectura.md`).

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
