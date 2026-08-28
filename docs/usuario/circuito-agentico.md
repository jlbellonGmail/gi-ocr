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
