# Plan — <FEATURE_ID> <TITULO>

## Gate inicial

- git status --short
- git branch --show-current
- git log --oneline --decorate -5

## Plan de ejecución

1. Inspeccionar archivos relevantes.
2. Confirmar alcance y fuera de alcance.
3. Implementar cambio mínimo.
4. Agregar o actualizar tests.
5. Ejecutar validaciones.
6. Revisar diff.
7. Cerrar con evidencia.

## Comandos previstos

- pytest
- python scripts/validate_project.py
- git diff --check
- git diff --stat
- git diff

## Validación requerida

- [ ] Unit/integration tests relevantes
- [ ] Validator interno
- [ ] Diff check
- [ ] Estado Git final

## Resultado esperado

<Resultado observable y medible.>
