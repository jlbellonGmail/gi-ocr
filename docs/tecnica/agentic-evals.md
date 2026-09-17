# Agentic Evals reproducibles

F07 agrega un runner pequeño para observar decisiones y ejecución del circuito
por capacidades. No modifica ASSESS, SDD, roles, CONVERGENCE ni `.audit`.

## Diseño

`evals/scenarios.json` es la fuente versionada de fixtures. Cada escenario
declara una pregunta, una observación `actual` y los campos `expected` que
deben coincidir. `scripts/agentic-evals.ps1` compara esos campos sin
reclasificar riesgo ni inferir resultados; emite un registro JSONL por
escenario y un resumen final. El runner no llama servicios externos, por lo
que una observación real puede ser capturada por un adaptador futuro sin
cambiar el contrato de resultados.

Los perfiles son selección, no niveles de calidad: `smoke` (3 casos),
`normal` (los 10 casos) y `full` (todos los fixtures). El `RunId` permite
identificar ejecuciones sin introducir hora ni aleatoriedad en los resultados.

## Contrato de resultado

Cada registro incluye escenario, versión, pregunta, expected, actual, pass,
reason, métricas y las banderas `providerAgnostic`/`modelAgnostic`. El último
registro resume cantidad, tasa de aprobación, decisiones correctas,
escalamientos, convergencias exitosas, loops evitados y desviaciones de
alcance detectadas. `agentic-eval-result.schema.json` documenta los registros
de escenario; el resumen se distingue por `scenarioCount`.

## Separación y límites

Los tests de `tests/` verifican el runner, perfiles y contrato de datos. Los
evals responden preguntas de comportamiento: profundidad proporcional,
escalamiento, retry, bloqueo, estancamiento, review stale, evidencia y
alcance. `.audit` permanece como evaluación global independiente. No hay
selección ni comparación de modelos/proveedores: eso queda para F08.

## Ejecución

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\agentic-evals.ps1 -Profile normal -RunId local -OutputPath .\runs\v2.0.0\12-agentic-evals\eval-results.jsonl -FailOnFailure
```
