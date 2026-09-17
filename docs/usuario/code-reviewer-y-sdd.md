# Code Reviewer y Spec-Driven Development (SDD)

## Qué cambia

El circuito agéntico pasa de 4 a 5 roles. El orden ahora es:

**Analyst → Reviewer → Builder → QA → Code Reviewer → `READY_FOR_PR`**

- **Analyst** ahora entrega tres archivos por feature, no uno:
  `spec.md` (qué se construye y por qué), `plan.md` (cómo se va a
  construir) y `tasks.md` (las tareas concretas y verificables, cada una
  ligada a un criterio de aceptación de `spec.md`). Esto se llama
  Spec-Driven Development (SDD): antes de escribir código, queda
  explícito el plan de implementación, no solo el pedido.
- **Reviewer** audita los tres archivos juntos antes de que nadie
  implemente nada.
- **Code Reviewer** es el agente nuevo. Corre DESPUÉS de que QA aprueba
  los tests, nunca antes: revisa el diff final completo (código, tests,
  scripts, configuración, documentación técnica) y deja su veredicto en
  `code-review-N.md`, con el mismo formato que ya usan `audit-N.md` y
  `test-report-N.md`. Es de solo lectura: no corrige nada, solo aprueba
  o rechaza con feedback concreto.
- Si Code Reviewer rechaza, la corrección vuelve a Builder — no hay que
  repetir todo el circuito desde Analyst.

Nada de esto agrega un checkpoint humano nuevo. El único punto de
intervención humana sigue siendo la decisión `MERGE` / `NO MERGE` sobre
la PR ya creada y con CI verde.

## Cómo verlo

Por cada feature nueva, en `runs/<NN>-<slug>/` vas a encontrar ahora:

- `spec.md`, `plan.md`, `tasks.md` (producidos por Analyst)
- `audit-N.md` (Reviewer, sobre los tres anteriores)
- `test-report-N.md` (QA)
- `code-review-N.md` (Code Reviewer, sobre el diff final)
- `decision.md`

`decision.md` ya no dice "MERGE aprobado" en ningún caso: dice
"Estado tecnico: ready_for_pr" y aclara que la aprobación de merge es
exclusivamente tuya, vía la revisión de la PR en GitHub. El circuito
agéntico nunca la otorga por sí solo.

La PR que crea `scripts/ready-for-pr.ps1` ahora también lista
`code-review-N.md` (y `plan.md`/`tasks.md`) en su sección de evidencias,
así que al revisar la PR para decidir `MERGE`/`NO MERGE` tenés a la
vista también el veredicto técnico de Code Reviewer, no solo el de QA.

## Cómo usarlo

No hay ningún comando nuevo que tengas que correr vos como humano: el
circuito lo maneja igual que antes (`scripts/ready-for-pr.ps1`,
`scripts/wait-pr-ci.ps1`, la aprobación de la PR en GitHub). Lo único que
cambia es que ahora hay una etapa técnica más antes de que una feature
llegue a `READY_FOR_PR`, y vas a ver un artefacto más
(`code-review-N.md`) en la evidencia de cada feature.

Si sos quien mantiene la configuración del circuito (`.agentic/`) y
agregás o modificás algún rol, seguí regenerando los adaptadores después
de editar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

`code-reviewer-agent` ya está registrado igual que los otros cuatro
roles: se genera automáticamente `.claude/agents/code-reviewer-agent.md`,
`.codex/code-reviewer-agent.config.toml` y la entrada
`agent.code-reviewer-agent` en `opencode.json`, sin tocar nada a mano.

## Qué NO cambió

- Seguís siendo el único punto de aprobación humana: nada de esto agrega
  un segundo checkpoint. `MERGE`/`NO MERGE` sobre la PR sigue siendo la
  única decisión que tomás vos.
- No hay stack ni backend nuevo: esto sigue siendo pura configuración y
  scripts del propio circuito agéntico.
- `ROADMAP.md` sigue sin marcarse `[x]` antes del merge real a `develop`.
