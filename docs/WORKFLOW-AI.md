# AI Workflow

Este proyecto se trabaja con agentes de IA, pero bajo control humano.

## Fórmula de trabajo

Cada pedido al agente debe incluir:

1. Contexto y rol.
2. Consulta o tarea.
3. Especificaciones.
4. Criterios de calidad.
5. Formato de respuesta.
6. Verificación.

## Prompt base para tareas

```md
# Contexto y rol

Actúa como agente técnico del proyecto Smart Invoice Capture.

Debes respetar:

- README.md
- ROADMAP.md
- GOVERNANCE.md
- CONTRIBUTING.md
- AGENTS.md
- governance/current-task.md
- governance/decisions.md

# Consulta / tarea

Ejecuta únicamente la tarea definida en governance/current-task.md.

# Especificaciones

- No trabajes directo en main.
- No hagas cambios fuera de alcance.
- No hagas refactors grandes.
- No cambies OCR, frontend o bridge si la tarea no lo pide.
- No versiones archivos generados.

# Criterios de calidad

La tarea debe quedar validada, documentada y con propuesta de commit.

# Formato de respuesta

Responder con:

## Resumen
## Archivos modificados
## Validaciones ejecutadas
## Evidencia
## Riesgos o pendientes
## Propuesta de commit

# Verificación

Antes de responder, verificar:

- rama actual;
- estado de Git;
- archivos modificados;
- validación local;
- cumplimiento de GOVERNANCE.md.
```

## Regla clave

El agente no decide el roadmap. El agente ejecuta la tarea activa.