# Changelog


## Unreleased

### Added
- Circuito agéntico AI-Native (`AGENTS.md`, `.claude/agents/`, `.opencode/`,
  `.codex/`, `opencode.json`, `scripts/*.ps1`, `runs/`, `docs/tecnica/`,
  `docs/usuario/`, `mkdocs.yml`, workflows de CI/docs/cierre post-merge),
  adoptado desde el template de referencia `gi-utils-fiscal-ar`.
- T2.9: integración de métricas de campos rechazados en el evaluador/pipeline, derivadas desde `rejected_fields`, sin modificar contrato `.DATA`.

### Changed
- Se reemplaza el circuito HITL-intensivo anterior (`GOVERNANCE.md`,
  `CONTRIBUTING.md`, `governance/`, `.agents/`, `.specify/`, `OPENCLAW.md`,
  `scripts/validate_project.py`) por el circuito Analyst → Reviewer →
  Builder → QA → PR → HITL final único, documentado en `AGENTS.md`. Las
  decisiones técnicas de `governance/decisions.md` (ADR-001 a ADR-008) se
  migran íntegras a `docs/tecnica/arquitectura.md`.
- `ROADMAP.md` reescrito con verificación real de código/tests/historial
  Git (ver sección Historial e Instant Task).
- Roadmap y governance reconciliados con el historial Git después del cierre de T2.9.

## [0.1.0] - 2026-06-20

### Changed

- Se ordena la estructura base del proyecto.
- Se consolida la gobernanza mínima AI-native.
- Se eliminan fuentes duplicadas de reglas heredadas.
- Se define flujo simple con Git, ramas `feature/*` y validación local.

### Notes

- Esta versión no certifica todavía OCR funcional.
- Esta versión no certifica todavía escritura atómica del bridge.
- Esta versión deja el proyecto preparado para avanzar por tareas pequeñas y controladas.