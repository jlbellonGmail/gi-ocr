# Fuente unica router modelos

## Para que sirve

Esta feature permite operar el circuito agentico de este repo sin editar
varias configuraciones distintas a mano. Los roles, modelos, fallback y
MCP se declaran una vez en `.agentic/` y luego se generan los adaptadores
de Claude Code, Codex y OpenCode.

## Uso habitual

1. Editar `.agentic/` cuando cambien roles, modelos, MCP o fallback.
2. Regenerar adaptadores:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
```

3. Validar que no hay divergencias:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

4. Para OpenCode, crear `runs/<NN>-<slug>/run.yaml` si una feature
   necesita fijar modelo, variante o fallback antes de `spec.md`.

## Despues de aprobar una PR

El humano no necesita volver al agente para decir que la PR fue aprobada.
Al aprobarla en GitHub, el gate post-HITL espera Actions y mergea solo si
queda verde. Si falla, deja feedback para builder y la PR no se mergea.
