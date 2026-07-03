# Skill: recovery

## Propósito

Recuperar una ejecución fallida, incompleta o sospechosa verificando el estado real antes de continuar.

## Cuándo usar

Usar cuando:

- una ejecución fue interrumpida
- hay salida contradictoria
- hay working tree sucio
- no se sabe si una tarea quedó cerrada
- tests o commits fueron declarados sin evidencia suficiente
- hay riesgo de cambios accidentales

## Procedimiento obligatorio

1. No modificar archivos al inicio.
2. Ejecutar gate:
   - git status --short
   - git branch --show-current
   - git log --oneline --decorate -10
   - git diff --stat
   - git diff

3. Identificar:
   - rama actual
   - commits nuevos
   - archivos modificados
   - archivos untracked
   - artefactos generados
   - tests existentes
   - tarea real abierta

4. Clasificar estado:
   - CLEAN_READY
   - DIRTY_RECOVERABLE
   - DIRTY_BLOCKED
   - CLOSED_WITH_EVIDENCE
   - CLAIM_UNVERIFIED
   - OUT_OF_SCOPE_CHANGES

5. Recomendar acción:
   - continuar
   - validar
   - revertir archivo específico
   - limpiar artefacto generado
   - crear commit
   - bloquear y pedir decisión

6. Solo implementar corrección si el usuario lo pidió o si está dentro de recovery seguro.

## Salida esperada

# Diagnóstico
# Evidencia observada
# Estado de la tarea
# Problemas detectados
# Acción recomendada
# Comando siguiente

## Prohibiciones

- No inventar estado.
- No asumir commit exitoso.
- No borrar cambios sin explicar.
- No hacer push.
- No abrir tarea nueva.
