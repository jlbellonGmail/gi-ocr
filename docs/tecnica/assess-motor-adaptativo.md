# ASSESS: motor adaptativo

## Propósito

Fase 01 agrega una evaluación determinista y aislada para estimar riesgo y
recomendar la profundidad futura `LIGHT`, `STANDARD` o `FULL`. La salida es
evidencia; no inicia etapas, no cambia el contrato v1.1.0 y no reemplaza el
orquestador existente.

## Contrato

`scripts/assess-work-unit.ps1` recibe `-ChangedPath` repetido o como lista,
rechaza una entrada vacía y devuelve JSON con `schemaVersion`, `risk`,
`depth`, `score`, `changedFiles`, `signals` y `deterministic: true`. Escribe
una línea JSONL en `runs/assess.jsonl` por defecto; `-NoEvidence` sirve para
validaciones efímeras. La ausencia de evidencia falla cerradamente.

Las señales actuales son conservadoras: rutas de datos, seguridad, permisos,
secretos, automatización y gobernanza elevan a `HIGH/FULL`; configuración del
circuito o implementación obtiene `MEDIUM/STANDARD`; documentación y tests
aislados obtienen `LOW/LIGHT`. El volumen distribuido agrega riesgo. Las
señales son explicativas, no una autorización para omitir SDD.

## Límites y compatibilidad

El script no invoca modelos, proveedores, MCP, roles ni pipelines. No edita
ROADMAP, contratos, adaptadores ni gates. Hasta Fase 02/05 el circuito v1
continúa exigiendo sus artefactos completos aunque ASSESS recomiende LIGHT.
La heurística es una primera política observable y podrá evolucionar mediante
otra fase con fixtures y regresiones, sin reinterpretar evidencia histórica.

## Casos borde

- Lista vacía o sin rutas: error no cero, sin recomendación.
- Rutas sensibles o de automatización: `FULL` aunque el cambio sea pequeño.
- Documentación/test aislado: `LIGHT`.
- Múltiples rutas: señal adicional de amplitud.
- JSONL se escribe UTF-8 sin BOM para interoperar con lectores estándar.
