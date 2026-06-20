# Current Task

## ID

T0.1

## Nombre

Limpieza y baseline controlado

## Objetivo

Corregir la estructura base del proyecto para eliminar redundancia, archivos vacíos, reglas duplicadas y contenido mal pegado.

## Alcance

Corregir:

- `.gitignore`
- `.env.example`
- `README.md`
- `ROADMAP.md`
- `GOVERNANCE.md`
- `AGENTS.md`
- `CONTRIBUTING.md`
- `VERSION`
- `CHANGELOG.md`
- `governance/decisions.md`
- documentación en `docs/`
- scripts de soporte en `scripts/`

Eliminar o mover:

- archivos vacíos que no participan todavía;
- carpetas mal nombradas;
- artefactos generados;
- configuraciones locales versionables.

## Fuera de alcance

- No corregir OCR todavía.
- No corregir frontend todavía.
- No implementar bridge atómico todavía.
- No cambiar `backend/app/main.py` en esta tarea.
- No cambiar `backend/app/ocr.py` en esta tarea.
- No cambiar `backend/config/services.ini` en esta tarea.

## Criterios de aceptación

- No existe `.ai/`.
- No existe `.cursorrules`.
- No existe `app/` en raíz.
- No existe `zones_detected.png`.
- `.gitignore` no contiene comandos PowerShell.
- `AGENTS.md` no referencia `.ai/`.
- `CONTRIBUTING.md` no tiene contenido duplicado.
- `GOVERNANCE.md` no duplica decisiones arquitectónicas.
- `governance/decisions.md` solo contiene decisiones.
- `VERSION` contiene `0.1.0`.
- `scripts/validate_project.py` ejecuta correctamente.

