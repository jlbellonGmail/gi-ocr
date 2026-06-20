# Governance

Este archivo es la fuente única de reglas operativas del proyecto.

No debe contener decisiones arquitectónicas detalladas, ejemplos de payload, documentación técnica extendida ni reglas duplicadas. Las decisiones técnicas se registran en `governance/decisions.md`.

## Regla principal

El proyecto se trabaja por tareas pequeñas, controladas y versionadas.

Ningún agente puede modificar varias áreas sin autorización explícita.

## Flujo obligatorio por tarea

Antes de modificar archivos:

1. Leer:
   - `README.md`
   - `ROADMAP.md`
   - `AGENTS.md`
   - `GOVERNANCE.md`
   - `CONTRIBUTING.md`
   - `governance/current-task.md`

2. Confirmar cuál es la tarea activa.

3. Si la tarea activa no está definida, detenerse y solicitar definición.

4. Si hay cambios pendientes no explicados, responder:

```text
STOP HUMAN REQUIRED
```

Durante la tarea:

1. Modificar solo archivos relacionados con la tarea activa.
2. No hacer refactors grandes.
3. No cambiar motor OCR sin aprobación.
4. No cambiar arquitectura sin registrar decisión.
5. No avanzar a otra tarea.
6. Agregar prueba, validador o evidencia manual cuando corresponda.

Antes de cerrar la tarea:

1. Ejecutar validación local.
2. Mostrar archivos modificados.
3. Mostrar comandos ejecutados.
4. Mostrar resultado.
5. Mostrar riesgos o pendientes.
6. Proponer commit futuro si Git ya está inicializado.
7. No hacer commit sin aprobación humana.

## Prohibiciones

- No trabajar varias tareas al mismo tiempo.
- No modificar archivos fuera del alcance definido.
- No hacer `git add .` sin revisar antes.
- No versionar `.venv/`.
- No versionar `__pycache__/`.
- No versionar archivos generados en `storage_bridge/ready/`.
- No versionar archivos generados en `storage_bridge/inbound/`.
- No versionar archivos generados en `storage_bridge/failed/`.
- No versionar imágenes reales de comprobantes.
- No borrar archivos sin explicar impacto.
- No duplicar reglas entre archivos.
- No cambiar alcance del MVP sin aprobación.
- No copiar comandos PowerShell dentro de archivos Markdown.
- No mezclar limpieza estructural, OCR, frontend y bridge en una misma tarea.

## Definición de tarea completada

Una tarea está completa solo si:

- cumple el criterio de aceptación definido;
- mantiene el alcance;
- no rompe el flujo existente;
- tiene validación local;
- no deja archivos vacíos innecesarios;
- no deja archivos generados versionables;
- tiene documentación mínima si cambia comportamiento;
- tiene propuesta clara de siguiente paso.

## Estado de Git

Git todavía no debe asumirse como inicializado durante la limpieza estructural actual.

Cuando se habilite Git formalmente, se aplicarán estas reglas:

- `main` será la rama estable.
- Cada tarea se trabajará en una rama `feature/*`.
- Los commits deberán usar Conventional Commits.
- No se harán commits sin aprobación humana.

## Convención futura de commits

Formato:

```text
tipo(alcance): descripción breve
```

Ejemplos:

```text
chore(project): clean baseline structure
docs(governance): define ai-native workflow
feat(ocr): add gas receipt extraction baseline
fix(frontend): correct service list rendering
test(bridge): validate atomic file writing
```