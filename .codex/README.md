# Codex agent profiles

`AGENTS.md` is the shared normative source for the project circuit. The
role prompts live once in `.agentic/roles/*.md`; this directory only keeps
Codex-specific execution wiring generated from `.agentic/agents.json` and
`.agentic/mcp.json`.

- `config.toml`: repo-local Codex defaults and generated MCP config.
- `<role>.config.toml`: per-role Codex profile loaded with `-p <role>`.

Use this directory as `CODEX_HOME` and pipe the canonical role prompt:

```powershell
$env:CODEX_HOME = (Resolve-Path .\.codex).Path
Get-Content .\.agentic\roles\analyst-agent.md -Raw | codex exec -p analyst-agent -C . -
Get-Content .\.agentic\roles\reviewer-agent.md -Raw | codex exec -p reviewer-agent -C . -
Get-Content .\.agentic\roles\builder-agent.md -Raw | codex exec -p builder-agent -C . -
Get-Content .\.agentic\roles\qa-agent.md -Raw | codex exec -p qa-agent -C . -
```

Regenerate and validate adapters from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

Do not edit generated Codex profiles manually. Edit `.agentic/` instead.

Profiles:

| Role | Model | Reasoning effort |
| --- | --- | --- |
| `analyst-agent` | `gpt-5.5` | `high` |
| `reviewer-agent` | `gpt-5.5` | `high` |
| `builder-agent` | `gpt-5.5` | `high` |
| `qa-agent` | `gpt-5.5` | `medium` |
