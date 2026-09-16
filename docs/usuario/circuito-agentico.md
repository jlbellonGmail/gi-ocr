# Circuito agentico

Este repo usa un circuito Analyst -> Reviewer -> Builder -> QA para
llevar una feature hasta una PR lista para revision humana.

Para cambiar instrucciones de roles, modelos o fallbacks, editar
`.agentic/` y regenerar adaptadores:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

Para elegir un modelo OpenCode antes de iniciar una feature, crear
`runs/<NN>-<slug>/run.yaml` desde `.agentic/run.example.yaml`. Si no se
indica modelo, se usa el default del rol (`anthropic/claude-sonnet-4-5`
hoy). Si se permite fallback, queda registrado en
`runs/<NN>-<slug>/model-routing.jsonl`.

No guardar tokens en el repositorio. El modelo directo Anthropic usa
`ANTHROPIC_API_KEY`; OpenCode Go y Zen se conectan con `/connect`;
OpenRouter se configura fuera del repo. En automatizacion, usar variables
de entorno o marcas de disponibilidad documentadas en
`.agentic/models.json`.

## Despues de aprobar una PR

El humano solo aprueba o rechaza. Si aprueba la PR en GitHub, el workflow
`Post-HITL merge gate` espera que Actions termine en verde despues de esa
aprobacion.

Si Actions queda verde, el workflow mergea la PR automaticamente y el
cierre post-merge marca el roadmap como completado. Si Actions falla, no
mergea: deja un reporte `post-hitl-gate-N.md` en la evidencia de la
feature y comenta la PR para que el builder corrija sin pedir otro punto
de intervencion humana.

## Caso single-maintainer

Cuando el autor de la PR es también el único mantenedor, GitHub no permite
aprobar la propia PR con una Review. El circuito conserva el camino normal
`reviewDecision == APPROVED` para equipos con más de un mantenedor y ofrece
un camino alternativo manual mediante `workflow_dispatch`.

El mantenedor debe indicar la PR, branch, base, SHA completo revisado,
intención `MERGE` y la confirmación exacta `I_CONFIRM_HITL_MERGE`. El actor
debe estar en `vars.SINGLE_MAINTAINER_HITL_ACTORS`; si la variable falta,
está vacía o no coincide exactamente, la ejecución se rechaza.

El workflow comprueba que la PR siga abierta, que no haya cambiado el SHA y
que `CI/test` y `CI/quality` hayan terminado exitosamente para ese mismo SHA.
El propio Post-HITL no se cuenta como check previo. Un check faltante,
pendiente, cancelado, skipped, fallido o perteneciente a otro SHA impide el
merge. La ejecución deja actor, fecha, PR, SHA, checks e intención en los
logs y el resumen de Actions, sin registrar secretos ni texto OCR.
