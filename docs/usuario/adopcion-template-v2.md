# Operar la gobernanza Template v2.0.0

Para iniciar una unidad se evalúa el riesgo con `scripts/assess-work-unit.ps1`
y se materializa SDD con `scripts/materialize-sdd.ps1`. El estado operativo se
regenera con `scripts/update-status.ps1` y se verifica con
`scripts/check-status.ps1`.

Antes de una PR se ejecutan los tests, `feature-contract.ps1`,
`sync-agentic-adapters.ps1 -Check`, `check-integrity.ps1` y
`validate-supply-chain.ps1`. El merge multi-maintainer conserva la review de
GitHub; el caso single-maintainer usa exclusivamente el workflow_dispatch
explícito ya implementado y validado por SHA.
