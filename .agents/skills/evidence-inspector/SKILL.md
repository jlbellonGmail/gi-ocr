# Skill: evidence-inspector

## Propósito

Auditar evidencia de una tarea GI-OCR sin modificar archivos.

## Cuándo usar

Usar para revisión read-only de terminal, diff, commits, validaciones, cierre de tarea o preparación para merge.

## Modo

Read-only estricto.

Permitido:

- git status --short
- git branch --show-current
- git log --oneline --decorate -10
- git diff --stat
- git diff
- lectura de archivos
- ejecución de tests si el usuario pide auditoría con validación

No permitido:

- editar archivos
- crear commits
- hacer merge
- hacer push
- limpiar artefactos
- abrir nueva feature

## Criterios de auditoría

Verificar:

- alcance respetado
- una sola tarea
- rama correcta
- working tree limpio o explicado
- diff coherente
- tests relevantes
- validadores internos
- ausencia de artefactos generados
- evidencia suficiente
- commit coherente si existe
- próxima tarea no iniciada

## Salida esperada

# Diagnóstico
# Evidencia observada
# Estado de la tarea
# Problemas detectados
# Acción recomendada
# Comando siguiente
