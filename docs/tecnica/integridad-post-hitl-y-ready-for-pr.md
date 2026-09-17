# Integridad post-HITL y ready-for-pr

Esta feature (`02-integridad-post-hitl-y-ready-for-pr`) cierra tres gaps
de integridad conocidos del motor del circuito agéntico, sin agregar
stack ni herramientas nuevas. Ver
`runs/v1.1.0/02-integridad-post-hitl-y-ready-for-pr/spec.md`, `plan.md` y
`tasks.md` para el detalle completo de criterios de aceptación (`AC-N`) y
tareas.

## GAP A — `scripts/complete-approved-pr.ps1`: aprobación HITL vinculada al commit vigente

### Por qué comparar contra `headRefOid` y no solo `reviewDecision`

`reviewDecision: APPROVED` solo dice que la última decisión agregada de
GitHub es "aprobado"; no dice sobre qué commit se emitió esa aprobación.
Si `develop` no tiene configurado "dismiss stale reviews" / "require
approval of the most recent reviewable push" (configuración manual de
GitHub, fuera de alcance de este repo — ver "Riesgos / supuestos" de
`spec.md`), un push posterior a la aprobación (por ejemplo, un fix de
`builder-agent` respondiendo a un `post-hitl-gate-N.md` rechazado) puede
dejar `reviewDecision` en `APPROVED` mientras el código que se mergearía
es distinto del que el humano vio. Comparar el `commit_id` de la última
review `APPROVED` contra el `headRefOid` actual de la PR es la única
forma de detectar esto sin depender de esa configuración de GitHub.

Se agregó `headRefOid` a los campos `--json` que ya pedía `gh pr view`
(`scripts/complete-approved-pr.ps1`), junto a la nueva función
`Get-LatestApprovedReviewCommit`, invocada entre la comprobación existente
`reviewDecision -ne "APPROVED"` y `Wait-PrChecks`.

### `gh api .../reviews --paginate --slurp`: por qué `--slurp` es obligatorio

`gh api repos/:owner/:repo/pulls/{n}/reviews` devuelve un array JSON por
página. Sin `--slurp`, `--paginate` imprime los arrays de cada página uno
después del otro (`[...][...]`), lo cual **no es un único valor JSON
válido** — `ConvertFrom-Json` fallaría al intentar parsearlo como una
sola estructura (confirmado contra `gh 2.97.0`, ver observación 1 de
`audit-1.md`). `--slurp` envuelve todas las páginas en un array exterior,
de modo que el resultado siempre es un array de arrays (una página =
un elemento = un array de reviews), incluso con una sola página. Por eso
`Get-LatestApprovedReviewCommit` aplana explícitamente ese array de
arrays antes de filtrar, en vez de asumir que el resultado ya es una
lista plana de reviews.

### Selección de la review relevante

- Filtra por `state -eq "APPROVED"` sobre el historial completo devuelto
  (que incluye `DISMISSED`, `CHANGES_REQUESTED`, `COMMENTED`, `PENDING`
  de cualquier revisor).
- Ordena por `submitted_at` descendente y toma el `commit_id` de la
  primera: cubre el caso de múltiples revisores aprobando en momentos
  distintos, usando siempre la aprobación más reciente para decidir
  stale/no-stale.
- Si el conjunto filtrado queda vacío, devuelve `$null` (caso defensivo:
  no debería ocurrir con `reviewDecision: APPROVED` en GitHub real, pero
  el script no lo asume y falla cerrado igual).

### Comportamiento al detectar una aprobación obsoleta

Si el `commit_id` de la última `APPROVED` no coincide con `headRefOid`
(o no hay ninguna `APPROVED`), el gate:

- **no** invoca `gh pr merge`;
- escribe `runs/<slug>/post-hitl-gate-N.md` con `status: rejected` y un
  mensaje explícito de que la aprobación quedó obsoleta y se requiere que
  el humano vuelva a aprobar sobre el commit vigente (no una corrección
  de `builder-agent`);
- respeta `-CommentOnFailure` para comentar la PR, igual que el camino ya
  existente de checks fallidos;
- termina con `throw`, código de salida distinto de cero.

### Esto no agrega un segundo HITL

Cuando el gate rechaza por aprobación obsoleta, la resolución es la misma
persona volviendo a apretar "Approve" en GitHub sobre el commit vigente —
el mismo botón de siempre, no un mecanismo nuevo de checkpoint.
`post-hitl-merge-gate.yml` ya se dispara también en
`pull_request: synchronize` (push nuevo a la PR), así que un push del
humano re-aprobando no requiere ningún cambio de workflow. Esta feature
no toca `.github/workflows/*.yml` (fuera de alcance explícito de
`spec.md`).

### Recomendación operativa (no automatizada)

Configurar en GitHub, sobre la rama `develop`, "Require approval of the
most recent reviewable push" es la defensa nativa equivalente y evita
depender de este chequeo en script. Esta feature es la compensación
defensiva para cuando esa configuración no está activa o no alcanza (por
ejemplo, revisores externos a la organización); no la reemplaza.

## GAP B — `scripts/ready-for-pr.ps1`: orden transaccional

### Problema

`scripts/ready-for-pr.ps1` mutaba y commiteaba `ROADMAP.md`
(`[ ]`/`[~]` → `[-]`) **antes** de la única validación real del contrato
completo (`Assert-FeatureContract`/`Assert-WorkUnitContract
-RequireReadyRoadmap`, que exige `decision.md`, docs técnica/usuario,
enlaces de índice y el último veredicto aprobado de auditoría/QA/code
review). Si esa validación fallaba después de la mutación, quedaba un
commit local con `ROADMAP.md` en `[-]` sin que el contrato realmente
hubiera pasado.

### Por qué no se tocó `Assert-FeatureContract`/`Assert-WorkUnitContract`

El switch `-RequireReadyRoadmap` ya era aditivo: sin él, ambas funciones
ya validan todo lo "caro" (decisión, docs, índices, último veredicto
aprobado) sin exigir ningún estado particular de `ROADMAP.md`; con él,
agregan exclusivamente el chequeo de que `ROADMAP.md` ya refleje el
estado esperado. Por eso la corrección es puramente de **orden de
llamadas** dentro de `ready-for-pr.ps1`, no un cambio de firma ni de
lógica de `scripts/feature-contract.ps1`:

1. Guard clauses de solo lectura que ya existían (`ya está [x]` → throw,
   `ya está en READY_FOR_PR` → log informativo) se mantienen sin cambios:
   no mutan nada.
2. **Nueva llamada temprana**, sin `-RequireReadyRoadmap`, antes de
   cualquier `Set-Content`/`git add`/`git commit` sobre `ROADMAP.md`. Si
   lanza excepción, el proceso termina sin haber tocado el archivo.
3. Solo si (2) no lanzó excepción, corre el bloque de mutación + commit
   ya existente, sin cambios.
4. La llamada final ya existente, con `-RequireReadyRoadmap`, se mantiene
   después de la mutación como confirmación de integridad post-mutación
   (por ejemplo, detecta entradas duplicadas o ambiguas que el reemplazo
   por regex no vería por sí solo).

### Simetría Feature/Milestone

La observación 2 de `audit-1.md` señaló que el plan solo justificaba
explícitamente el caso "todos ya Ready" para Milestone. La implementación
aplica el mismo criterio en ambas ramas de forma simétrica: en Feature,
la validación temprana corre también en la rama "ya está en
READY_FOR_PR" (que puede seguir hacia push/creación de PR más adelante en
el script); en Milestone, corre también en la rama "todos los items ya
están Ready". Ninguna rama de ninguno de los dos modos llega al bloque de
push/PR sin haber pasado primero por la validación completa del
contrato.

### Qué no cambia

`Assert-RoadmapItemsTransition` (en `scripts/workunit-lib.ps1`) sigue
siendo la única fuente de la garantía "todo o nada" para la transición de
**estado** de `ROADMAP.md` en Milestone; esta feature no la toca. GAP B
extiende la garantía transaccional hacia atrás en el tiempo (contrato
completo antes de tocar `ROADMAP.md`), no reemplaza esa función.

## GAP C — `scripts/ready-for-pr.ps1`: evidencia real en el body de la PR

El bloque `$evidenceSection` (Feature y Milestone) usaba los literales
fijos `audit-N.md`/`test-report-N.md`/`code-review-N.md`, obligando a
quien revisa la PR a adivinar el número de intento real aprobado. Ahora,
inmediatamente después de que la validación de contrato (GAP B) ya
garantizó que el último intento de cada veredicto existe y está
`approved`, se resuelve el path real con la función ya existente
`Get-LatestVerdictArtifact -Directory $info.RunDir -Prefix "audit"` (y
análogas para `test-report`/`code-review`).

**Corrección de un bug detectado en `code-review-1.md` (intento 1,
rechazado):** `Get-LatestVerdictArtifact.Path` (en
`scripts/feature-contract.ps1`) se construye con `$latest.File.FullName`,
y `System.IO.FileInfo.FullName` en .NET/PowerShell **siempre** devuelve
una ruta absoluta resuelta contra el directorio actual del proceso —
nunca `runs/<slug>/audit-N.md`. La primera versión de este bloque
interpolaba `$($auditArtifact.Path)` / `$($qaArtifact.Path)` /
`$($codeReviewArtifact.Path)` directamente en el cuerpo de la PR,
filtrando así la ruta absoluta del filesystem de quien corrió
`ready-for-pr.ps1` (agente local o runner de CI) al cuerpo público de la
PR en GitHub — en violación directa del caso borde de `spec.md` ("sin
rutas absolutas del entorno del agente").

La corrección deliberadamente **no** toca `Get-LatestVerdictArtifact` ni
su firma (para no afectar a su otro consumidor,
`Assert-LatestVerdictApproved`, que también usa `.Path` en sus mensajes
de error): en `scripts/ready-for-pr.ps1`, inmediatamente después de
resolver `$auditArtifact`/`$qaArtifact`/`$codeReviewArtifact`, se
recompone una ruta relativa propia (`$auditPath`, `$qaPath`,
`$codeReviewPath`) combinando `$info.RunDir` (ya relativo, ej.
`runs/<slug>` o `runs/milestone-<slug>`) con el nombre de archivo real
obtenido vía `Split-Path -Leaf $auditArtifact.Path` (ej. `audit-2.md`).
El bloque `$evidenceSection` (Feature y Milestone) y la línea del
checklist que menciona `test-report-N.md` referencian esas variables
relativas (`$auditPath`, `$qaPath`, `$codeReviewPath`), nunca `.Path`
directamente.

## Casos borde cubiertos por tests

- **GAP A**: aprobación obsoleta (`test_complete_approved_pr_rejects_stale_approval`),
  múltiples reviews `APPROVED` de distintos revisores usando la más
  reciente por `submitted_at`
  (`test_complete_approved_pr_uses_most_recent_approved_review`), y todos
  los tests preexistentes de `tests/test_complete_approved_pr_script.py`
  siguen pasando sin debilitar ninguna aserción.
- **GAP B**: `ready-for-pr.ps1` no muta `ROADMAP.md` ni deja commits
  nuevos cuando el contrato falla, en Feature
  (`test_ready_for_pr_blocks_roadmap_mutation_when_contract_fails`) y en
  Milestone con manifest de 2+ items donde falla la doc técnica de uno
  solo (`test_milestone_ready_for_pr_blocks_roadmap_mutation_when_contract_fails`).
- **GAP C**: el body de la PR contiene la ruta relativa exacta del
  intento aprobado vigente (`runs/<slug>/audit-2.md`, o
  `runs/milestone-<slug>/audit-2.md` en Milestone, cuando `audit-1.md`
  fue rechazado), no solo la subcadena `audit-2.md`, no contiene el
  literal `audit-N.md`, no contiene el separador de unidad de disco
  Windows (`:\`) y no contiene el path absoluto del repo temporal del
  propio test — en Feature
  (`test_ready_for_pr_pr_body_references_real_latest_attempt`) y en
  Milestone (`test_milestone_pr_body_references_real_latest_attempt`).
  Estas aserciones adicionales (más allá de la subcadena del nombre de
  archivo) son las que detectan una regresión del bug de ruta absoluta
  descripto arriba; la versión anterior de ambos tests pasaba igual con
  el bug presente, porque `audit-2.md` también aparece al final de una
  ruta absoluta.

## Fuera de alcance (deliberado)

- Configurar branch protection real de GitHub.
- Tocar `.github/workflows/*.yml`, `scripts/resolve-agentic-model.ps1` o
  cualquier archivo de `.agentic/`.
- Reescribir retroactivamente PRs ya creadas con el placeholder genérico
  anterior a esta feature.
- Ningún mecanismo nuevo de reintento automático de aprobación humana: la
  única resolución de una aprobación obsoleta es que el humano vuelva a
  aprobar.

Ver `runs/v1.1.0/02-integridad-post-hitl-y-ready-for-pr/spec.md` (sección
"Explícitamente NO incluye") para el detalle completo.
