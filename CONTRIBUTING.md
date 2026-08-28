# Contributing

Este proyecto usa un flujo simple para el MVP.

## Rama estable

- `main`: rama estable del proyecto.

## Ramas de trabajo

Cada tarea se trabaja en una rama independiente con prefijo:

```text
feature/
```

Ejemplo:

```text
feature/baseline-controlado
feature/ocr-gas-baseline
feature/bridge-atomico
feature/frontend-mobile-capture
```

## Estado actual

En esta fase todavía se está ordenando el baseline del proyecto.

La inicialización formal de Git, GitHub, ramas y versionado se realizará después de cerrar la limpieza estructural.

## Antes de trabajar una tarea

Leer:

- `README.md`
- `ROADMAP.md`
- `GOVERNANCE.md`
- `AGENTS.md`
- `governance/current-task.md`
- `governance/decisions.md`

## Durante el trabajo

- Trabajar solo la tarea activa.
- No mezclar limpieza, OCR, frontend y bridge en el mismo cambio.
- No subir archivos generados.
- No subir imágenes reales de comprobantes.
- No duplicar reglas entre archivos.
- No cambiar el alcance del MVP sin aprobación.

## Validación mínima actual

Mientras Git todavía no esté inicializado, ejecutar:

```powershell
python scripts/validate_project.py
```

## Validación posterior

Cuando Git ya esté inicializado, se agregará validación de:

- rama actual;
- estado de trabajo;
- archivos preparados para commit;
- tags de versión;
- push a GitHub.

## Commits futuros

Cuando se habilite Git, los commits deberán usar Conventional Commits:

```text
chore(project): clean baseline structure
docs(governance): define workflow rules
feat(ocr): add gas extraction baseline
fix(frontend): correct service list rendering
test(bridge): validate atomic output
```

## Prohibido versionar

- `.venv/`
- `__pycache__/`
- `.env`
- imágenes reales de comprobantes
- archivos generados en `storage_bridge/inbound/`
- archivos generados en `storage_bridge/ready/`
- archivos generados en `storage_bridge/failed/`

