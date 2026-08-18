# specs/

Este directorio contiene las specs de las features implementadas **antes**
de adoptar el circuito agéntico de `AGENTS.md` (T3.1 a T4): T3.3, T3.4,
T3.5, T4. Se conservan tal cual como historial — no se reescriben ni se
mueven al nuevo formato retroactivamente.

## Features nuevas

Las features nuevas ya no usan `specs/` ni `.specify/templates/` (ambos
removidos al adoptar el circuito). Usan en cambio:

- `runs/<NN>-<slug>/spec.md`: producida por `analyst-agent`.
- `runs/<NN>-<slug>/audit-N.md`: producida por `reviewer-agent`.
- `runs/<NN>-<slug>/test-report-N.md`: producida por `qa-agent`.
- `runs/<NN>-<slug>/decision.md`: producida por `builder-agent`.
- `docs/tecnica/<slug>.md` y `docs/usuario/<slug>.md`.

Ver el circuito completo en `AGENTS.md`.
