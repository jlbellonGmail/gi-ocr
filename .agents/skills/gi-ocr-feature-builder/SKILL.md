# Skill: gi-ocr-feature-builder

## Propósito

Ejecutar una feature real de GI-OCR con Spec-Driven Development, cambios pequeños, tests y evidencia verificable.

## Cuándo usar

Usar cuando el usuario pida implementar una tarea funcional o documental concreta del roadmap.

No usar para auditorías read-only ni recovery.

## Entrada mínima esperada

- ID o nombre de tarea.
- Objetivo.
- Alcance.
- Fuera de alcance.
- Archivos esperados, si se conocen.
- Validaciones esperadas.

Si falta información no crítica, inferir con prudencia desde ROADMAP.md, specs/ y código existente. No abrir otra tarea.

## Procedimiento obligatorio

1. Gate inicial:
   - git status --short
   - git branch --show-current
   - git log --oneline --decorate -5

2. Inspección:
   - leer ROADMAP.md
   - leer governance/current-task.md si existe
   - buscar archivos relevantes
   - identificar tests existentes
   - confirmar que no hay cambios accidentales

3. Especificación:
   - objetivo
   - alcance
   - fuera de alcance
   - archivos esperados
   - criterios de aceptación
   - validaciones

4. Plan:
   - pasos mínimos
   - riesgos
   - estrategia de tests
   - impacto OCR/DATA/storage si aplica

5. Implementación:
   - cambios pequeños
   - no refactors no pedidos
   - no hardcodear reglas de negocio
   - no dependencias nuevas salvo justificación
   - mantener separación OCR/extracción/validación/evaluación/storage

6. Tests:
   - caso exitoso
   - caso inválido cuando aplique
   - regresión relevante
   - fixture/documento usado si es OCR

7. Validación:
   - pytest relevante
   - python scripts/validate_project.py si aplica
   - git diff --check
   - validadores específicos si existen

8. Revisión:
   - git diff --stat
   - git diff
   - confirmar archivos modificados

9. Commit:
   - crear commit local solo si todo pasa y el alcance lo permite
   - no push
   - mensaje convencional, por ejemplo feat(ocr): ...
   - si no se commitea, explicar por qué

10. Cierre:
   - usar formato de cierre de AGENTS.md
   - próxima tarea solo como elegible

## Reglas OCR específicas

Para cualquier extracción OCR reportar:

- texto bruto OCR
- candidato
- validado
- rechazado
- no encontrado
- fixture usado
- falsos positivos evitados

## Prohibiciones

- No abrir T3.1 o T3.2 salvo pedido explícito.
- No declarar PASS sin salida real.
- No tocar .venv ni cachés.
- No borrar legacy sin permiso.
- No push.
- No mezclar tareas.
