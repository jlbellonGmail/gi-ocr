# Codex agent profiles

`AGENTS.md` is the shared normative source for the project circuit. This
directory only contains Codex-specific execution wiring:

- `config.toml`: repo-local Codex defaults.
- `<role>.config.toml`: per-role Codex profile loaded with `-p <role>`.
- `prompts/<role>.md`: minimal role prompt used when delegating from the
  Main Agent.

Use this directory as `CODEX_HOME` to make the profiles reproducible from
the repo:

```powershell
$env:CODEX_HOME = (Resolve-Path .\.codex).Path
Get-Content .\.codex\prompts\analyst-agent.md -Raw | codex exec -p analyst-agent -C . -
Get-Content .\.codex\prompts\reviewer-agent.md -Raw | codex exec -p reviewer-agent -C . -
Get-Content .\.codex\prompts\builder-agent.md -Raw | codex exec -p builder-agent -C . -
Get-Content .\.codex\prompts\qa-agent.md -Raw | codex exec -p qa-agent -C . -
```

Profiles:

| Role | Model | Reasoning effort |
| --- | --- | --- |
| `analyst-agent` | `gpt-5.5` | `high` |
| `reviewer-agent` | `gpt-5.5` | `high` |
| `builder-agent` | `gpt-5.5` | `high` |
| `qa-agent` | `gpt-5.5` | `medium` |

The Main Agent delegates by selecting the matching profile and piping the
matching prompt. Codex profiles provide reproducible model and reasoning
settings; the role boundaries and circuit rules remain in `AGENTS.md`.
