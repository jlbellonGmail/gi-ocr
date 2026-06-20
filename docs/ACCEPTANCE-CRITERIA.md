# Acceptance Criteria

## Criterios generales

Una tarea se acepta solo si:

- cumple el alcance definido;
- no introduce cambios fuera de tarea;
- tiene validación;
- no deja archivos generados versionables;
- no duplica reglas;
- mantiene estructura simple;
- propone commit sin ejecutarlo.

## Baseline del proyecto

El baseline se acepta si:

- `.gitignore` no contiene comandos PowerShell;
- no existe `.ai/`;
- no existe `.cursorrules`;
- no existe `app/` en raíz;
- `AGENTS.md` no referencia `.ai/`;
- `CONTRIBUTING.md` no está duplicado;
- `GOVERNANCE.md` contiene reglas operativas;
- `governance/decisions.md` contiene solo decisiones;
- `VERSION` contiene `0.1.0`;
- `CHANGELOG.md` tiene entrada inicial;
- `scripts/validate_project.py` pasa.

## OCR baseline

Se acepta si:

- existe imagen fixture;
- se ejecuta OCR;
- se extraen campos definidos;
- se reporta tiempo de ejecución;
- se identifican campos no encontrados.

## Bridge

Se acepta si:

- no se escribe directo en `ready/`;
- se escribe primero en temporal;
- se mueve con operación atómica;
- existe test del flujo.

## Frontend

Se acepta si:

- permite cargar/capturar imagen;
- muestra estado del procesamiento;
- muestra resultado;
- muestra error claro si falla.

