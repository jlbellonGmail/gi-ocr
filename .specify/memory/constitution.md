# GI-OCR Constitution

## Principios

1. Spec-Driven Development.
2. Una tarea por vez.
3. Evidencia real antes de cierre.
4. Cambios pequeños y reversibles.
5. Tests para cambios funcionales.
6. Separación OCR, extracción, validación, evaluación y storage.
7. Sin push automático.
8. Sin refactors no pedidos.
9. Sin artefactos generados en commits.
10. Sin hardcoding de reglas de negocio.

## Calidad OCR

Toda mejora OCR debe poder responder:

- qué campo extrae
- desde qué documento
- con qué fixture
- qué salida produce
- cómo se valida
- qué falso positivo evita

## Cierre mínimo

Una tarea solo puede considerarse cerrada cuando existe evidencia de:

- alcance respetado
- validaciones ejecutadas
- diff revisado
- estado Git explicado
- commit local si corresponde
- riesgos documentados
