# Operational readiness docs

Esta feature (`05-operational-readiness-docs`) agrega dos piezas de
documentación operativa que no existían: un checklist ejecutable para
configurar branch protection real de GitHub sobre `develop`, y una nota
de troubleshooting para un bloqueo local conocido en Windows con
EDR/antivirus agresivo. No toca código de producto (no existe), ni
`scripts/*.ps1`, ni `.github/workflows/*.yml`. Ver
`runs/v1.1.0/05-operational-readiness-docs/spec.md`, `plan.md` y `tasks.md` para
el detalle completo de criterios de aceptación (`AC-N`) y tareas.

## Branch protection de GitHub (`AGENTS.md`, sección "Setup manual")

### Por qué `gh api` en vez de solo pasos de UI

Aplicar branch protection vía
`gh api --method PUT repos/{owner}/{repo}/branches/develop/protection`
es una operación declarativa sobre configuración del repositorio (no
sobre datos, código ni historial), reversible (se puede volver a aplicar
con otro payload o desactivar desde la misma API/UI). Documentarla como
comando ejecutable copy-paste reduce el riesgo de que un humano se salte
un checkbox al reproducir los 4 requisitos a mano, y es reproducible entre
repos que adopten este template. Por eso se documenta el comando `gh api`
como vía primaria, con la alternativa manual de UI como respaldo si el
operador no confía en el comando o `gh` no está disponible en su máquina
(`gh` ya es herramienta local requerida, ver `AGENTS.md` sección
"Herramientas locales requeridas" — no se agrega dependencia nueva).

### Por qué `develop` y no `main`

El circuito automatizado (`ready-for-pr.ps1`, `complete-approved-pr.ps1`,
los workflows de Actions) solo crea y mergea PRs contra `develop` por
feature (`AGENTS.md`, sección "Git": "`main` — solo recibe merges desde
`develop` vía PR, cuando se decide hacer un release"). `develop` es la
rama donde el único HITL del circuito (la decisión `MERGE`/`NO MERGE`
sobre la PR) es efectivo; proteger `main` es una decisión de release del
humano, fuera de este circuito por feature, y queda fuera de alcance
explícito de esta feature.

### Por qué `enforce_admins: true` — Fase CLARIFY resuelta

El ítem de `ROADMAP.md` que originó esta feature solo pedía 4 requisitos
(PR obligatoria, status check en verde, 1 aprobación, dismiss stale
approvals); no especificaba `enforce_admins`. El intento 1 de esta spec
(ver `runs/v1.1.0/05-operational-readiness-docs/audit-1.md`) dejó ese valor en
`false` como "supuesto conservador", y `reviewer-agent` lo rechazó
correctamente: es una decisión de seguridad/permisos que admite dos
respuestas válidas, no un detalle técnico inferible sin más de evidencia
existente, y estaba en tensión directa con la regla dura ya documentada
en `AGENTS.md` sección "Git" ("Nunca commitear directo a `develop`... ni
nunca directo a `main`") — con `enforce_admins: false`, un admin sí
podría pushear directo a `develop` saltándose PR/aprobación/CI, exactamente
lo que esa regla prohíbe.

La corrección pasó por Fase CLARIFY real con el humano (ver
`spec.md`, sección "Clarificaciones realizadas", y
`runs/v1.1.0/05-operational-readiness-docs/decision.md`):

- **Pregunta**: ¿`enforce_admins` debe ser `true` o `false`?
- **Respuesta**: `true`. Los administradores también quedan sujetos a la
  protección, sin bypass, consistente con la regla dura existente de
  `AGENTS.md`, aceptando que en un incidente operativo excepcional no
  haya bypass automático disponible para admins.

El payload documentado en `AGENTS.md` y el equivalente de UI ("Include
administrators" / "Do not allow bypassing the above settings", ver más
abajo) reflejan ese valor final.

### Por qué el `PUT` reemplaza y cómo se mitiga

El endpoint `PUT .../branches/develop/protection` de GitHub sobrescribe
por completo la configuración de branch protection vigente de la rama con
el payload enviado; no hace un merge incremental con reglas activadas
manualmente desde la UI que no estén en ese payload (por ejemplo "require
signed commits", "require linear history", restricciones de push por
equipo/usuario). Si esas reglas existieran y se reaplica el `PUT`
documentado sin incluirlas, se pierden silenciosamente. Esto quedó como
caso borde explícito de `spec.md` (agregado en la versión 2, a pedido de
`audit-1.md`) y como `AC-4`.

Mitigación documentada en el mismo bullet de `AGENTS.md`: correr primero
el comando `GET` de solo lectura (`gh api
repos/{owner}/{repo}/branches/develop/protection`, sin efectos
secundarios) para revisar qué hay configurado antes de reemplazar,
especialmente antes de una re-ejecución para actualizar el nombre del
status check (ver "Nombre del status check" abajo). El `PUT` sí es
idempotente respecto de sí mismo (reenviar el mismo payload dos veces
seguidas no falla ni duplica nada) — esa idempotencia es una propiedad
distinta de la no-aditividad respecto de configuración externa, y el
bullet distingue ambas explícitamente.

### Nombre del status check (dependencia con la feature `04`)

El nombre documentado (`test`) corresponde al job único y actual de
`.github/workflows/ci.yml` en este worktree al momento de esta feature.
La feature `04-ci-wiring-product-tests`, en curso en paralelo, puede
renombrar o separar ese job (por ejemplo a `circuit-tests`); si eso ya
ocurrió al momento de aplicar este checklist, el operador debe verificar
el nombre real vigente en la pestaña Actions de una PR reciente antes de
correr el `PUT` (aplicar el comando con un nombre de check que ya no
existe dejaría un status check requerido que nunca se reporta, bloqueando
todo merge futuro contra `develop`). Esta es una dependencia declarada
explícitamente entre features en paralelo, no una ambigüedad material
bloqueante (confirmado en `audit-1.md` y `audit-2.md`).

### Por qué el troubleshooting de EDR vive en `circuito-agentico.md`

`docs/tecnica/circuito-agentico.md` ya es la fuente técnica del
comportamiento de `local-feature-reconcile.ps1`/`ready-for-pr.ps1` y del
gate post-HITL (sección "Gate post-HITL", donde ya se documenta que la
limpieza local queda en manos del reconciliador local). Agregar un
archivo nuevo solo para una nota de troubleshooting habría fragmentado
documentación relacionada sin necesidad; la nueva sección se agrega al
final de ese mismo archivo.

### Esto cierra una deuda documentada previamente

`docs/tecnica/integridad-post-hitl-y-ready-for-pr.md` (feature `02`) dejó
explícitamente fuera de alcance "configurar branch protection / rulesets
reales de GitHub" y documentó una "Recomendación operativa (no
automatizada)" pidiendo activar en `develop` protección equivalente a
"Require approval of the most recent reviewable push". Esta feature
atiende esa deuda con el checklist de los 4 requisitos clásicos del ítem
`05` (que no es exactamente "most recent reviewable push", una capacidad
más nueva de GitHub Rulesets, pero cubre el mismo objetivo de fondo: que
el único HITL del circuito sea efectivo y no se pueda saltear).

## Troubleshooting de EDR (`docs/tecnica/circuito-agentico.md`)

El contenido completo (síntoma, causa, alcance, solución) vive en la
sección "Troubleshooting: EDR/antivirus agresivo bloquea el reconciliador
local (Windows)" de ese archivo. Puntos de diseño relevantes:

- El alcance se documenta explícitamente como **exclusivamente local**:
  no corrompe git, no afecta CI, gate post-HITL ni el cierre remoto de
  `ROADMAP.md`, porque esos tres corren en GitHub Actions, independientes
  del proceso PowerShell local afectado.
- La solución (`git worktree remove --force` + `git worktree add`) es
  segura incluso si el lock file del reconciliador
  (`<git-common-dir>/feature-reconcilers/`) sigue "vivo" pero apuntando a
  un proceso muerto o bloqueado: ese estado vive fuera de cualquier
  worktree (confirmado leyendo `Get-FeatureStateDir` en
  `scripts/feature-contract.ps1`), así que removerlo con `--force` no lo
  corrompe ni requiere matar el proceso a mano primero.
- Se advierte explícitamente que `--force` descarta cualquier cambio sin
  commitear en ese worktree, con la recomendación de revisar `git status`
  ahí antes de forzar, si el worktree sigue siendo accesible.

## Casos borde cubiertos

- **Repo sin remoto de GitHub configurado**: el comando `gh api` falla si
  no hay remoto GitHub válido; el bullet lo advierte, coherente con el
  bullet "Remoto GitHub" ya existente en la misma sección.
- **Usuario sin permisos de administrador**: el endpoint exige permisos
  admin; `gh api` devuelve 403/404. Advertido explícitamente, sin
  prometer que el comando funciona con cualquier nivel de permiso.
- **Nombre de status check desactualizado**: ver "Nombre del status
  check" arriba.
- **Reemplazo total de configuración existente vs. re-ejecución
  idempotente**: ver "Por qué el `PUT` reemplaza" arriba — son dos
  propiedades distintas, documentadas por separado.
- **JSON del payload inválido por error de tipeo**: el bullet documenta
  el paso `$branchProtection | ConvertFrom-Json | Out-Null` como
  validación local sin credenciales, antes de invocar la API real.
- **Lock file del reconciliador apuntando a un proceso muerto/bloqueado
  por el EDR**: cubierto arriba, en "Troubleshooting de EDR".
- **Cambios sin commitear en el worktree bloqueado**: cubierto arriba,
  advertencia explícita antes de recomendar `--force`.
- **Accesibilidad/responsive**: no aplica — ambos artefactos son
  documentación Markdown en texto plano, sin UI ni componente visual
  nuevo.

## Fuera de alcance (deliberado)

- Ejecutar el comando `gh api` contra un repositorio GitHub real: es un
  paso manual del humano, no una automatización del circuito agéntico.
- Configurar branch protection sobre `main`.
- Modificar `.github/workflows/ci.yml` o cualquier otro workflow.
- Escribir o modificar `scripts/local-feature-reconcile.ps1` o
  `scripts/ready-for-pr.ps1`: el troubleshooting de EDR es un
  procedimiento manual, no un cambio de comportamiento de esos scripts.
- Un mecanismo automático que detecte o repare bloqueos de EDR.

Ver `runs/v1.1.0/05-operational-readiness-docs/spec.md` (sección "Explícitamente
NO incluye") para el detalle completo.
