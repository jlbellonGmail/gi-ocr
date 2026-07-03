# CLAUDE.md — GI-OCR Local Operating Notes

Este repositorio usa AGENTS.md como estándar operativo principal.

Para trabajar en GI-OCR:

1. Leer AGENTS.md.
2. Usar skills locales en .agents/skills/.
3. Usar prompts compactos en .agents/prompts/.
4. Usar templates livianos en .specify/templates/.
5. Crear specs por feature en specs/ cuando aplique.
6. Mantener una sola tarea abierta.
7. No inventar evidencia.
8. No hacer push sin instrucción explícita.

Comandos base esperados:

- git status --short
- git branch --show-current
- git log --oneline --decorate -5
- python scripts/validate_project.py
- pytest
- git diff --stat
- git diff

Para features reales usar:

- .agents/skills/feature-builder/SKILL.md
- .agents/prompts/feature-execution.prompt.md

Para fallos o ejecuciones sospechosas usar:

- .agents/skills/recovery/SKILL.md
- .agents/prompts/recovery.prompt.md

Para auditoría read-only usar:

- .agents/skills/evidence-inspector/SKILL.md
- .agents/prompts/evidence-inspection.prompt.md
