# Routing dinámico

El router separa `role`, `capabilities`, `implementation` y `provider`.
`.agentic/models.json` declara implementaciones con alias, capacidades,
calidad, costo, latencia, contexto, disponibilidad y perfiles de seguridad.

`resolve-agentic-model.ps1` recibe `-Capabilities`, `-Risk`, `-SddLevel`,
`-ContextTokens`, `-SecurityProfile` y `-EvalEvidencePath`. Primero descarta
opciones incompatibles; después aplica pesos determinísticos: LIGHT favorece
eficiencia, STANDARD equilibrio y FULL calidad. Los empates usan alias.

F07 se consume sólo como señal relativa y auditable. La falta de evidencia no
inventa resultados: continúa con la política declarada. Si no hay candidato
compatible, el router falla con `BLOCKED`. Las resoluciones incluyen las
señales principales en `model-routing.jsonl`.
