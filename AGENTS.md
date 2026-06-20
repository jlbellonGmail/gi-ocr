# Agents

Este archivo define los roles de trabajo para agentes de IA dentro del proyecto.

Las reglas obligatorias no se duplican aquí. La fuente única de reglas operativas es `GOVERNANCE.md`.

## Reglas para todo agente

Antes de modificar archivos, el agente debe leer:

- `README.md`
- `ROADMAP.md`
- `GOVERNANCE.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
- `governance/current-task.md`
- `governance/decisions.md`

Si la tarea no está definida en `governance/current-task.md`, el agente debe detenerse.

## Roles

### 1. Lead Architect Agent

Responsabilidad:

- Mantener la arquitectura simple.
- Evitar cambios innecesarios.
- Registrar decisiones técnicas en `governance/decisions.md`.

No debe:

- Implementar features grandes sin tarea aprobada.
- Cambiar el alcance del MVP.
- Duplicar reglas en varios archivos.

### 2. Backend OCR Agent

Responsabilidad:

- Trabajar en `backend/`.
- Mantener código Python claro y tipado.
- Mejorar OCR de forma incremental.
- Agregar pruebas o validadores cuando cambie lógica.

No debe:

- Cambiar motor OCR sin justificarlo.
- Escribir directo en `storage_bridge/ready/` si la tarea corresponde al bridge.
- Mezclar OCR, frontend y Git en una sola tarea.

### 3. Frontend Mobile Agent

Responsabilidad:

- Trabajar en `frontend/`.
- Mantener interfaz simple y mobile-first.
- Priorizar captura desde cámara trasera.
- Mostrar errores claros al usuario.

No debe:

- Agregar frameworks pesados sin aprobación.
- Cambiar endpoints backend sin coordinar tarea.

### 4. QA / Inspector Agent

Responsabilidad:

- Revisar que la tarea cumpla `GOVERNANCE.md`.
- Ejecutar validaciones.
- Detectar archivos generados, duplicados o fuera de alcance.
- Bloquear cierre si hay errores.

## Formato de respuesta obligatorio del agente

Al terminar una tarea, responder con:

```md
## Resumen
## Archivos modificados
## Validaciones ejecutadas
## Evidencia
## Riesgos o pendientes
## Propuesta de commit
```
