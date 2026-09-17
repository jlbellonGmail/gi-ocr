# Arquitectura de roles

F03 reduce los roles conceptuales a Planner, Builder y Reviewer. Un rol es
una responsabilidad estable; una capacidad es una habilidad; una herramienta
es un mecanismo y un modelo es intercambiable.

Planner interpreta intención, consume la salida determinística de ASSESS y
elige la profundidad SDD ya materializada por F02. Builder implementa, prueba
y corrige sin autoaprobarse. Reviewer verifica independientemente intención,
diff, tests, evidencia y criterios; sus capacidades incluyen spec review, QA,
code review, regresiones, arquitectura y seguridad según riesgo.

Los aliases `analyst-agent`, `qa-agent` y `code-reviewer-agent` sólo permiten
migrar invocaciones históricas hacia el rol canónico correspondiente. No se
generan adaptadores para ellos. Si Builder y Reviewer usan el mismo modelo, la
separación se conserva mediante contexto/sesión independiente y evidencia.

F03 no implementa el loop de convergencia, límites de iteración ni políticas
de stop: quedan para F04.
