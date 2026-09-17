# Operational readiness docs

## Para quién es

- Quien administra el repositorio real de GitHub del proyecto (necesita
  rol de administrador para el checklist de branch protection).
- Quien opera el circuito agéntico localmente en Windows (necesita el
  procedimiento de troubleshooting si el reconciliador local queda
  bloqueado).

Ninguno de los dos puntos es código de producto ni cambia cómo se corre
el circuito agéntico normal (analista → auditor → implementador → QA →
code reviewer). Son documentación de setup/mantenimiento.

## Checklist de branch protection: cuándo correrlo

Corré el comando `gh api` documentado en `AGENTS.md` (sección "Setup
manual (una sola vez, no automatizable)", bullet "Branch protection de
GitHub") una sola vez, al adoptar el circuito en un repositorio real de
GitHub, después de haber configurado el remoto (bullet "Remoto GitHub").
Volvé a correrlo si:

- Cambia el nombre del status check de CI (por ejemplo, si la feature
  `04-ci-wiring-product-tests` ya se mergeó y renombró el job de `test`
  a otro nombre). En ese caso, verificá primero el nombre real vigente en
  la pestaña Actions de una PR reciente antes de aplicar el comando.
- Necesitás ajustar cualquiera de los 4 requisitos (PR obligatoria,
  status check en verde, al menos 1 aprobación, descartar aprobaciones
  obsoletas).

**Antes de volver a correr el `PUT`**, corré primero el comando `GET` de
solo lectura (también documentado en el mismo bullet) para revisar qué
hay configurado en ese momento en `develop`. El `PUT` reemplaza toda la
configuración de branch protection existente, no la fusiona: si alguien
activó manualmente otra protección desde la UI de GitHub (por ejemplo
"require signed commits" o "require linear history") y volvés a correr
el `PUT` sin incluir esas reglas en el payload, se pierden en silencio.

El payload fija `enforce_admins: true`: si tenés rol de administrador en
el repositorio, vos también vas a quedar sujeto a esta protección — no
vas a poder pushear directo a `develop` saltándote PR, aprobación o CI,
ni siquiera en un incidente operativo excepcional, salvo que cambies la
configuración manualmente antes. Es una decisión confirmada
explícitamente (no un valor por defecto elegido sin consultar), ver
`runs/v1.1.0/05-operational-readiness-docs/decision.md`.

Si preferís no correr el comando o no tenés `gh` disponible, el mismo
bullet documenta la alternativa equivalente paso a paso en la UI de
GitHub (Settings → Branches → Add branch protection rule).

## Qué hacer si el reconciliador local queda bloqueado (Windows)

Si estás en Windows con un EDR/antivirus agresivo y notás que el
worktree de una feature ya mergeada no se limpia solo después de que la
PR se cerró (el proceso de fondo `local-feature-reconcile.ps1` puede
haber quedado bloqueado por el software de seguridad), seguí el
procedimiento documentado en `docs/tecnica/circuito-agentico.md`, sección
"Troubleshooting: EDR/antivirus agresivo bloquea el reconciliador local
(Windows)":

1. Si el worktree bloqueado sigue siendo accesible, revisá `git status`
   ahí primero — el paso siguiente descarta cualquier cambio sin
   commitear.
2. `git worktree remove --force <path-del-worktree-bloqueado>`
3. `git worktree add <path-nuevo> <rama-de-la-feature>`

No hace falta matar el proceso bloqueado a mano antes: el estado del
reconciliador vive fuera de cualquier worktree, así que no interfiere con
la remoción. Este bloqueo es exclusivamente local a tu máquina — nunca
afecta el estado real de la PR, el CI ni el merge, que ya corrieron (o
van a correr) en GitHub Actions de forma independiente.

## Qué NO cambia

- El único punto de aprobación humana del circuito sigue siendo la
  decisión `MERGE`/`NO MERGE` sobre la PR. Nada de esto agrega un
  checkpoint nuevo.
- No hay stack, backend ni dependencia nueva: ambas piezas son
  documentación Markdown, y `gh` ya era una herramienta local requerida.
- Ningún script del circuito (`ready-for-pr.ps1`,
  `local-feature-reconcile.ps1`, `complete-approved-pr.ps1`,
  `close-feature.ps1`) cambia de comportamiento ni de interfaz por esta
  feature.
