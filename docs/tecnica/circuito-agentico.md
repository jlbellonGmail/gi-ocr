# Circuito agentico multiherramienta

## Fuente canonica

Las reglas compartidas siguen en `AGENTS.md`. La configuracion que cambia
por herramienta vive en `.agentic/`:

- `.agentic/roles/*.md`: prompts funcionales canonicos, incluidas las
  reglas de dominio OCR propias de este proyecto (pipeline OCR,
  extraccion, validacion semantica, `storage_bridge`, `services.ini`).
- `.agentic/agents.json`: descripciones, permisos, herramientas, modelos
  y esfuerzo por adaptador.
- `.agentic/models.json`: modelos permitidos, variantes y fallbacks de
  OpenCode.
- `.agentic/mcp.json`: servidores MCP canonicos de este repo (vacio: no
  hay servidores MCP reales configurados hoy).
- `.agents/skills/`: skills Agent Skills portables.

## Adaptadores generados

No editar manualmente:

- `.claude/agents/*.md`
- `.codex/config.toml`
- `.codex/<role>.config.toml`
- `.mcp.json`
- `opencode.json`
- mirrors de skills en `.claude/skills/` y `.opencode/skills/`

Regenerar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
```

Validar sin escribir:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

## Router OpenCode

Antes de iniciar una etapa OpenCode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\resolve-agentic-model.ps1 `
  -Role analyst-agent `
  -Feature 01-mi-feature
```

El archivo opcional `runs/<NN>-<slug>/run.yaml` puede fijar modelo,
variante y fallback antes de que exista `spec.md`:

```yaml
execution:
  model: default
  variant: high
  fallback:
    - go
    - zen
```

El default declarado en `.agentic/models.json` es
`anthropic/claude-sonnet-4-5` (el modelo ya en uso real por `opencode.json`
en este repo). Go, Zen y OpenRouter quedan como fallback autorizado para
cuando se conecten. El script no invoca modelos ni consulta catalogos
remotos: valida contra `.agentic/models.json`, exige credenciales o marcas
de disponibilidad del entorno y registra evidencia en
`model-routing.jsonl`.

## Gate post-HITL

La aprobacion humana de una PR no implica merge inmediato. El gate comun
vive en `scripts/complete-approved-pr.ps1` y se invoca desde
`.github/workflows/post-hitl-merge-gate.yml` cuando una review humana
aprueba una PR contra `develop`.

El gate valida que la PR siga abierta, pertenezca a `feature/<NN>-<slug>`,
apunte a `develop` y tenga `reviewDecision=APPROVED`. Luego consulta los
checks con `gh pr checks --json ...`, excluyendo el propio workflow
`Post-HITL merge gate` para no esperarse a si mismo.

Si algun check queda en `fail` o `cancel`, o si expira la espera, no hay
merge. Se escribe `runs/<NN>-<slug>/post-hitl-gate-N.md` con
`status: rejected` y feedback para que `builder-agent` corrija la rama y
el circuito continue desde implementacion/QA.

Si todos los checks relevantes quedan en verde, el gate ejecuta
`gh pr merge --merge --delete-branch`. El cierre remoto de `ROADMAP.md`
lo sigue haciendo `post-merge-close-feature.yml` mediante
`scripts/close-feature.ps1`; la limpieza local queda en manos de
`scripts/reconcile-local-feature.ps1`, lanzado en segundo plano por
`scripts/start-local-reconciler.ps1`, que observa `origin/develop`.
