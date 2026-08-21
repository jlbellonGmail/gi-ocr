# Fuente canonica agentica

`.agentic/` contiene la configuracion canonica del circuito agentico que
no pertenece a una herramienta concreta.

- `agents.json`: metadatos por rol, modelos por herramienta y permisos de
  adaptador.
- `roles/*.md`: definicion funcional canonica de cada rol (incluye las
  reglas de dominio OCR propias de gi-ocr).
- `models.json`: router minimo de modelos para OpenCode, allowlists,
  credenciales esperadas y fallbacks autorizados. El default actual es
  `anthropic/claude-sonnet-4-5` (el modelo ya en uso por este repo); Go,
  Zen y OpenRouter quedan declarados como fallback autorizado para cuando
  se conecten.
- `mcp.json`: fuente canonica de servidores MCP de este repo. Arranca
  vacia a proposito; no se inventan servidores.
- `run.example.yaml`: declaracion minima previa a `spec.md` para elegir
  modelo, variante y fallback.

Editar estos archivos y luego ejecutar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

Los adaptadores en `.claude/`, `.codex/`, `.opencode/` y `opencode.json`
se regeneran desde esta fuente. No editarlos manualmente.
