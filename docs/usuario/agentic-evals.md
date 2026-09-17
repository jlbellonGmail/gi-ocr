# Agentic Evals

La suite permite comprobar de forma repetible si el circuito toma decisiones
proporcionales y termina de forma segura. No requiere conocer el proveedor ni
el modelo que produzca una observación.

Ejecuta el perfil `smoke` para una comprobación rápida, `normal` para los diez
escenarios representativos o `full` para todos los fixtures disponibles. El
archivo JSONL contiene un registro por escenario y un resumen final; un
escenario fallido incluye la diferencia exacta y `-FailOnFailure` devuelve
código de salida 1.

La suite no inicia F08 ni decide routing. Los resultados pueden archivarse y
compararse por `suiteVersion`, `scenario` y `RunId`.
