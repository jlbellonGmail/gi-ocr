# Fuente unica router modelos

## Proposito tecnico

Esta feature elimina la duplicacion entre configuraciones de Claude Code,
Codex y OpenCode en este repo. La fuente editable vive en `.agentic/` y
los archivos propios de cada herramienta (`.claude/agents/*.md`,
`.codex/*.toml`, `.mcp.json`, `opencode.json`) se tratan como adaptadores
generados, no como fuente de verdad.

## Fuente canonica

- `.agentic/agents.json`: roles, descripciones, permisos, modelos y
  esfuerzo por herramienta.
- `.agentic/roles/*.md`: prompt funcional de cada agente, incluidas las
  reglas de dominio OCR ya vigentes en este repo (`backend/app/`,
  `storage_bridge/`, `backend/config/services.ini`).
- `.agentic/models.json`: allowlists, variantes y fallback OpenCode.
- `.agentic/mcp.json`: servidores MCP canonicos (vacio hoy: este repo no
  tiene servidores MCP reales configurados).
- `.agents/skills/`: skills portables.

Los adaptadores se regeneran con:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
```

Y se validan con:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

## Router OpenCode

`scripts/resolve-agentic-model.ps1` resuelve el modelo antes de una etapa
OpenCode. Lee `runs/<NN>-<slug>/run.yaml` si existe, valida modelo y
variante contra `.agentic/models.json`, exige marcas de disponibilidad o
credenciales externas y escribe evidencia en `model-routing.jsonl`.

El default configurado hoy es `anthropic/claude-sonnet-4-5` (modelo ya en
uso real por este repo antes de esta adopcion). El fallback autorizado es
Go -> Zen -> OpenRouter explicito, declarado pero todavia no conectado.
OpenRouter no se usa si no aparece en `run.yaml` o en el parametro
`-Fallback`.

## Gate post-HITL

`scripts/complete-approved-pr.ps1` se invoca desde
`.github/workflows/post-hitl-merge-gate.yml` cuando el humano aprueba una
PR contra `develop`. El gate vuelve a esperar checks de Actions despues
de la aprobacion:

- si quedan verdes, ejecuta el merge;
- si fallan o expiran, no mergea y produce
  `runs/<NN>-<slug>/post-hitl-gate-N.md` con feedback para builder.

El cierre `[x]` de `ROADMAP.md` sigue reservado al workflow post-merge
(`post-merge-close-feature.yml` + `scripts/close-feature.ps1`); la
limpieza local del worktree sigue a cargo de
`scripts/reconcile-local-feature.ps1` / `scripts/start-local-reconciler.ps1`,
sin cambios respecto de antes de esta adopcion.
