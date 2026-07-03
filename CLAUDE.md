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

- .agents/skills/gi-ocr-feature-builder/SKILL.md
- .agents/prompts/gi-ocr-feature-execution.prompt.md

Para fallos o ejecuciones sospechosas usar:

- .agents/skills/gi-ocr-recovery/SKILL.md
- .agents/prompts/gi-ocr-recovery.prompt.md

Para auditoría read-only usar:

- .agents/skills/gi-ocr-evidence-inspector/SKILL.md
- .agents/prompts/gi-ocr-evidence-inspection.prompt.md
