# Convergencia Builder–Reviewer

F04 agrega `scripts/convergence.ps1`, un gate determinístico que coordina el
estado de un ciclo Builder → tests/evidencia → Reviewer. No invoca ni
reclasifica ASSESS: valida y consume su profundidad, junto con la profundidad
materializada por SDD.

## Contrato

La entrada JSON contiene `assessment` (o `assessmentPath`), `sdd` (o
`sddPath`), `iteration`, `reviewer`, `tests` y opcionalmente `previous`.
Reviewer aporta `verdict` (`APPROVED`, `CHANGES_REQUESTED` o `BLOCKED`) y
findings con `id`, severidad, descripción y estado (`OPEN`, `RESOLVED`,
`ACCEPTED` o `RATIONALE`). El Builder no puede producir aprobación.

La salida conserva el fingerprint de findings abiertos, contadores, progreso,
no-progreso, presupuesto y escalamiento. `CHANGES_REQUESTED` es intermedio;
los estados terminales son `APPROVED`, `NEEDS_HUMAN_DECISION`, `BLOCKED` y
`FAILED_SAFELY`. Un review nuevo siempre debe evaluar el estado vigente; el
estado previo sólo se usa para detectar estancamiento.

## Política proporcional

El presupuesto por defecto es LIGHT=2, STANDARD=4 y FULL=6 iteraciones, con
`-MaxIterations` como extensión explícita. El límite evita loops y el script
termina de forma segura si el fingerprint de findings no cambia, si falla la
ejecución o si existe una dependencia externa. Planner sólo reingresa mediante
`needsPlanner`/`materialDecision`; el script escala esas condiciones y no
elige una solución funcional.

La separación lógica del Reviewer se expresa en la salida (`reviewerIndependent`
y `builderMayApprove`), sin exigir un proveedor o modelo concreto.
