# Adopción incremental de Template v2.0.0

## Objetivo

Adoptar la gobernanza y el lifecycle de Template v2.0.0 en GI-OCR sin
reemplazar la arquitectura funcional OCR ni sus contratos de integración.

## Alcance

Incorporar CONSTITUTION, STATUS, .audit, ASSESS, SDD adaptativo LIGHT/
STANDARD/FULL, roles Planner/Builder/Reviewer, work units, evidencias,
convergencia, integridad, release readiness, guard de develop, CI y
adaptadores generados.

## Compatibilidad preservada

Se mantienen backend/, frontend/, storage_bridge/, RapidOCR, fallback
EasyOCR, FastAPI, services.ini, formatos `.DATA`/JSON confirmado, hashes,
idempotencia, estados OCR, contratos HTTP y runs históricos.

## Fuera de alcance

No cambia funcionalidad OCR, proveedores de OCR, despliegue productivo,
SaaS multitenant, Skills artificiales ni servidores MCP sin caso de uso.

## Criterios de aceptación

- Los scripts v2 y sus contratos pasan sus tests deterministas.
- Planner, Builder y Reviewer son roles agnósticos de proveedor/modelo.
- `reviewDecision == APPROVED` y el workflow_dispatch single-maintainer
  existente permanecen operativos.
- CI ejecuta producto y circuito con acciones fijadas por SHA.
- `check-integrity`, `check-status`, adaptadores y supply chain pasan.
- Se crean `docs/tecnica/adopcion-template-v2.md`,
  `docs/usuario/adopcion-template-v2.md`, `decision.md` y sus enlaces exactos.
- La suite de producto OCR permanece verde.
