# Cierre Operativo del Circuito Agéntico

Endurece el uso cotidiano del circuito descrito en `AGENTS.md` con
herramientas de diagnóstico y recuperación, sin cambiar su forma (4
agentes, un solo HITL). Implementa el spec
`runs/03-cierre-operativo-circuito-agentico/spec.md` (aprobado en el
intento 2, tras resolver en el intento 1 un conflicto de diseño entre el
criterio 4 y el criterio 15 — ver más abajo).

## Alcance de esta feature

- `scripts/preflight.ps1` (nuevo): diagnóstico de solo lectura, dos modos
  (genérico y `-Slug <NN-slug>`).
- `scripts/feature-contract.ps1`: agrega `Get-FeatureContractStatus`
  (reporte no-throwing), `Get-ToolchainDiagnostics`/`Assert-ToolchainReady`
  (diagnóstico genérico de herramientas compartido), y las versiones
  no-throwing `Find-GitHubCliPath`/`Find-PowerShellPath` (con
  `Get-GitHubCliPath`/`Get-PowerShellPath` como wrappers throwing, mismo
  comportamiento externo que antes).
- `scripts/wait-pr-ci.ps1`: agrega `-Snapshot` (consulta puntual no
  bloqueante). El modo `--watch` original no cambia.
- `scripts/start-local-reconciler.ps1`: arranque del proceso en segundo
  plano sin ventana visible.
- `scripts/close-feature.ps1`: reintenta el push pendiente cuando el
  estado local ya es "already-closed" pero el commit no llegó a
  `origin/<base>`.
- `scripts/ready-for-pr.ps1`: invoca `Assert-ToolchainReady` al inicio,
  antes de tocar `ROADMAP.md`; deja de definir localmente
  `Get-GitHubCliPath`/`Get-PowerShellPath`.

No cambia la topología de 4 agentes, no automatiza la decisión humana
`MERGE`/`NO MERGE`, y no reescribe ningún script existente desde cero (ver
"Explícitamente fuera de alcance" del spec).

## `scripts/preflight.ps1`

Script de **solo lectura**: nunca commitea, nunca pushea (salvo
`git fetch`, que es de solo lectura), nunca crea ni borra ramas o
worktrees. Toda acción de recuperación queda delegada a los scripts ya
existentes (`close-feature.ps1`, `start-local-reconciler.ps1`, o comandos
`git` manuales que el propio reporte sugiere) — decisión de diseño
explícita del spec ("Riesgos / supuestos"): es la opción más segura y más
fácil de testear de forma determinística.

### Exit codes

- `0`: no hay problemas `BLOCKING` (puede haber `WARNING`). El resumen
  final imprime `PREFLIGHT: OK (<n> advertencia(s))`.
- `1`: al menos un problema `BLOCKING`. El resumen final imprime
  `PREFLIGHT: BLOCKING (<n> problema(s) bloqueante(s), <m> advertencia(s))`.

No hay una tabla de códigos numéricos por tipo de error (decisión de
diseño del spec): binario, igual que el resto de los scripts del repo
(throw/no-throw). La clasificación de severidad vive en el texto del
reporte (`[OK]`/`[WARNING]`/`[BLOCKING]` por línea), no en el exit code.

### Modo genérico (sin `-Slug`)

Diagnostica, en una sola corrida (sin abortar en el primer problema):

1. **Diagnóstico genérico de herramientas** (`Get-ToolchainDiagnostics` en
   `feature-contract.ps1`, compartido con `ready-for-pr.ps1`, ver más
   abajo):
   - `git`: presente en PATH (`Get-Command git`).
   - `gh`: binario presente (PATH o `%ProgramFiles%\GitHub CLI\gh.exe`) y,
     si está presente, autenticado (`gh auth status`, combinando
     stdout+stderr). "Binario ausente" y "binario presente pero no
     autenticado" son problemas `BLOCKING` distintos, con mensajes que no
     los confunden (casos borde del spec: "no instalado" vs "no
     autenticado", incluida sesión expirada — el exit code de
     `gh auth status` no distingue de forma confiable "nunca logueado" de
     "token expirado" entre todas las versiones de `gh`, así que el
     mínimo exigido por el spec —no confundir binario ausente con
     autenticación fallida— se cumple sin inventar una heurística frágil
     sobre el texto exacto de cada versión de `gh`).
   - PowerShell: al menos una de `pwsh`/`powershell.exe` en PATH.
   - Python: `python`/`python3` en PATH, versión `>= 3.12` (parseada de
     `python --version`). **Solo se evalúa si existe
     `backend/requirements.txt` en la raíz del repositorio actual** (ver
     "Decisión: chequeo de Python/.venv condicionado a
     `backend/requirements.txt`" más abajo).
   - `.venv`: mismo condicionamiento que Python. Si `backend/requirements.txt`
     existe: `.venv` ausente, `.venv` presente pero con intérprete que no
     arranca (`.venv/Scripts/python.exe` o `.venv/bin/python` corrupto —
     `BLOCKING` distinto de "ausente", casos borde del spec), o `.venv`
     presente pero con paquetes de `backend/requirements.txt` faltantes
     **por nombre** (comparación case-insensitive, `_`/`-` normalizados,
     contra `pip freeze` del intérprete del venv) son todos `BLOCKING`
     con mensajes distintos y accionables.
   - Cada problema `BLOCKING` incluye una acción concreta (comando o
     instrucción) para resolverlo.
2. **Estado de `develop`** (`Get-DevelopBranchDiagnostics`, específico de
   `preflight.ps1`, no compartido con `ready-for-pr.ps1` — ver criterio 15
   más abajo):
   - Ubica, vía `git worktree list --porcelain`, el worktree/checkout que
     tiene `develop` activa (sin cambiar de rama: nunca hace
     `git checkout`). Si ninguno la tiene activa: `WARNING`.
   - Si la tiene activa: `git -C <path> status --porcelain` (solo lectura).
     Cambios sin commitear → `BLOCKING` mencionando explícitamente
     `develop` y "sin commitear"; no intenta arreglarlo (no hace
     `git stash`/`git checkout` automático — criterio 3 del spec).
   - `git fetch origin develop` (solo lectura). Si falla (sin red):
     `WARNING` "no se pudo contactar a origin", y el resto de los
     chequeos que no requieren red se siguen reportando (no crashea con
     traza cruda de PowerShell — caso borde del spec).
   - Si el fetch funciona: compara `develop` vs `origin/develop` con
     `git rev-list --left-right --count`. Detrás de `origin/develop`:
     `WARNING` "sincroniza con `git pull --ff-only`". Adelante (por
     ejemplo, un cierre con commit local pero push pendiente): `WARNING`
     sugiriendo verificar si falta pushear.

### Modo por feature (`-Slug <NN-slug>`)

Adicional al modo genérico. Slug inválido (no cumple
`^[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*$`): reutiliza `Get-FeatureInfo` (mismo
mensaje "Slug invalido...", sin duplicar la validación de formato — caso
borde del spec) y el script aborta con ese mensaje.

#### Matriz de consistencia worktree / rama / ROADMAP

"Local branch" = `git branch --list feature/<slug>`. "Worktree" = entrada
en `git worktree list --porcelain` cuyo `branch` es `feature/<slug>` y
cuyo directorio existe en disco. "Remote branch" = `git ls-remote
--exit-code origin refs/heads/feature/<slug>` (exit `0` existe, exit `2`
no existe; cualquier otro exit code se reporta como `WARNING` de
conectividad, sin asumir "no existe"). "ROADMAP" = estado exacto de la
entrada `<slug>` en el `ROADMAP.md` del working tree actual (el mismo
directorio desde el que se invoca `preflight.ps1`).

| ROADMAP (local) | Local branch | Worktree | Remote branch | Severidad | Acción recomendada |
|---|---|---|---|---|---|
| `[ ]` | no | no | no | OK | Feature no iniciada. |
| `[ ]` | sí | sí | no o sí | OK (informativo) | Feature en progreso, normal. |
| `[-]` | sí | sí | sí | OK (informativo) | En camino a PR/CI; se agrega una línea informativa adicional con el snapshot de PR/CI (`gh pr view`, best-effort). |
| `[-]` | sí | sí | **no** | BLOCKING | `git push -u origin feature/<slug>` y re-correr `ready-for-pr.ps1 <slug>` (idempotente). |
| `[-]` | no | no | sí o no | BLOCKING | Recrear el worktree: `git worktree add ../worktrees/<slug> feature/<slug>`. |
| `[x]` | no | no | — | OK | Todo limpio. |
| `[x]` | sí | sí | — | WARNING | El reconciliador no limpió. `start-local-reconciler.ps1 -Slug <slug>` o borrar a mano. |
| `[x]` | sí | no | — | WARNING | Rama local huérfana. `git branch -d feature/<slug>`. |
| `[x]` | no | sí | — | BLOCKING | Worktree sin rama asociada (estado roto). `git worktree remove --force <ruta>` tras confirmar que no hay cambios sin commitear. |
| entrada ausente o duplicada | — | — | — | BLOCKING | Debe haber exactamente una entrada `<slug>` en `ROADMAP.md`. |
| worktree fuera de `../worktrees/<slug>/` | — | sí (otra ruta) | — | WARNING | No sigue la convención de `AGENTS.md`; no bloquea. |
| worktree registrado pero directorio ausente en disco | — | — | — | WARNING | Entrada administrativa huérfana: `git worktree prune`. |

Adicionalmente, siempre que exista un lock de reconciliador
(`<git-common-dir>/feature-reconcilers/<slug>.pid`):

- Proceso vivo (`cmd`/`powershell`/`pwsh` con ese PID): `OK` informativo
  "reconciliador activo, PID `<n>`" — dos agentes/humanos corriendo
  `ready-for-pr.ps1`/reconciliador en paralelo para la misma slug ya está
  mitigado por este lock; `preflight.ps1` lo reporta como informativo, no
  como error (caso borde del spec).
- Proceso muerto (lock obsoleto) y `<slug>.err.log` con contenido:
  `WARNING` "terminó con error, revisar `<slug>.err.log`". Proceso muerto
  sin contenido de error: `WARNING` genérico de lock obsoleto. Esto
  distingue "terminó con error" (lock vivo hasta que el `finally` de
  `reconcile-local-feature.ps1` lo limpia, salvo un `taskkill /F` u otra
  muerte forzada) de "nunca se lanzó" (lock inexistente desde el inicio),
  caso borde explícito del spec.

**Nota de simplificación de diseño — snapshot de PR/CI.** Cuando la fila
es `[-]/sí/sí/sí` (en camino a PR/CI), se agrega una línea informativa
adicional con `gh pr view <branch> --json number,url,state,mergeStateStatus`
(best-effort: si `gh` no está disponible o la consulta falla, la línea lo
dice explícitamente en vez de fallar todo el diagnóstico) y un puntero a
`scripts/wait-pr-ci.ps1 -Snapshot -PrRef <branch>` para el detalle de
checks.

**Nota de diseño — no se cruza `ROADMAP.md` local contra
`origin/develop:ROADMAP.md` fila por fila.** El párrafo introductorio de
la matriz en el spec menciona que "ROADMAP" puede leerse tanto del
working tree actual como de `origin/develop:ROADMAP.md` "cuando aplica".
En la práctica, la fila `[x]` solo puede observarse corriendo
`preflight.ps1` desde un checkout que **ya tiene** `develop` con esa
entrada en `[x]` (un worktree de la propia rama de feature nunca llega a
ver `[x]` en su propio `ROADMAP.md`, porque ese commit vive solo en
`develop`). Por eso la matriz usa una sola lectura (la del working tree
actual) para clasificar la fila, sin duplicar lógica de comparación
remota — la comparación contra `origin/develop` ya se hace, de forma
independiente, en la sección "Estado de `develop`" del modo genérico.

## Criterio 15 — resolución del conflicto con el criterio 4

**Decisión (heredada del spec, opción "b" de las tres evaluadas en la
auditoría del intento 1):** `ready-for-pr.ps1` reutiliza de
`preflight.ps1` **exclusivamente** el diagnóstico genérico de
herramientas (`Assert-ToolchainReady`: git, gh binario+autenticación,
PowerShell, Python, `.venv`), corrido al inicio del script, antes de
cualquier verificación propia de rama/commits y en particular antes de
marcar `ROADMAP.md` como `[-]`. **Nunca** ejecuta la matriz completa
`-Slug` sobre sí mismo.

**Motivo (verificado contra el código real de `ready-for-pr.ps1`):**
el script marca `ROADMAP.md` como `[-]` y commitea (antes del cambio de
esta feature, líneas ~163-178; después del cambio, esas líneas no se
tocaron) **antes** de pushear (`git push -u origin $currentBranch`,
antes ~182-183). En el estado normal de cualquier primera corrida, justo
antes del push existe exactamente: `ROADMAP.md` local `[-]`, rama y
worktree locales existentes, rama remota **inexistente**. Ese estado
coincide con la fila `BLOCKING` de la matriz (`[-]/sí/sí/no`). Si el
chequeo compartido incluyera esa fila de la matriz, insertarlo en
cualquier punto entre "marcar `[-]`" y "pushear" habría producido un
deadlock de diseño: el camino feliz de **toda** feature futura abortaría
con la acción sugerida "hacé `git push` y re-corré `ready-for-pr.ps1`" —
pero pushear es exactamente el paso que el script está a punto de
ejecutar.

El diagnóstico genérico de herramientas (git/gh/PowerShell/Python/.venv)
no depende en absoluto de la existencia de la rama remota, así que puede
correr en cualquier punto del flujo sin generar ese falso positivo — se
ubica al inicio para fallar lo más temprano posible. La matriz `-Slug`
completa sigue disponible como comando **standalone**
(`preflight.ps1 -Slug <slug>`), para diagnóstico externo antes de iniciar
una corrida, o después de confirmar que una corrida anterior se
interrumpió de verdad (proceso ya no vivo).

**Limitación aceptada (documentada explícitamente por el spec, no
resuelta por esta feature):** correr `preflight.ps1 -Slug <slug>` en la
brevísima ventana en que `ready-for-pr.ps1` ya marcó `[-]` pero todavía no
terminó de pushear (típicamente sub-segundo) puede reportar `BLOCKING` de
forma transitoria y "correcta" según la propia definición de la matriz,
aun cuando el push vaya a completarse enseguida. No se resuelve con
detección de proceso vivo (explícitamente fuera de alcance de esta
feature). No es el mismo caso que una interrupción real (proceso muerto,
rama remota que nunca llega a existir): ese caso sigue siendo `BLOCKING`
sin ambigüedad.

**Mecanismo de reutilización:** dot-sourcing de `feature-contract.ps1`
(mismo patrón que `ready-for-pr.ps1` ya usaba antes de esta feature para
`Get-FeatureInfo`/`Assert-FeatureContract`), no invocación de
`preflight.ps1` como proceso hijo — evita doble parseo de salida entre
procesos (decisión explícita del spec, "Riesgos / supuestos").

**Propagación del mensaje de error de `gh` (nota de la auditoría del
intento 2, no bloqueante pero exigida por el criterio 15(a)):** el
mensaje de `BLOCKING` para "gh no autenticado" en
`Get-ToolchainDiagnostics` propaga el texto crudo combinado
(stdout+stderr) de `gh auth status`, igual patrón que ya usaba
`Get-ExistingPr` (`"...: $($result.StdErr)"`). Esto es lo que mantiene en
verde `test_ready_for_pr_blocks_real_gh_error` en
`tests/test_feature_contract_scripts.py`: el test fija con el `gh` falso
un `exit 2` con `"auth failed"` en stderr para **cualquier** subcomando,
así que tanto el chequeo antiguo (`gh pr view`, dentro de
`Get-ExistingPr`) como el nuevo (`gh auth status`, dentro de
`Assert-ToolchainReady`, corrido antes) producen el mismo texto
`"auth failed"` en el mensaje de error final.

## Decisión: chequeo de Python/.venv condicionado a `backend/requirements.txt`

`Get-ToolchainDiagnostics` solo evalúa Python/`.venv` si existe
`backend/requirements.txt` en la raíz del repositorio actual
(`Get-RepositoryRoot`). Si no existe, esos dos chequeos se omiten por
completo (ni `OK` ni `BLOCKING`) — no es una laguna del spec, es una
decisión técnica del builder no explicitada en el spec original (a
documentar en `decision.md`): los tests de regresión existentes de
`ready-for-pr.ps1` (`tests/test_feature_contract_scripts.py`) corren el
script dentro de repositorios git sintéticos de un solo directorio
(`runs/`, `docs/`, `ROADMAP.md`), sin la estructura completa del proyecto
real (`backend/`, `.venv`). Si el chequeo de Python/`.venv` fuera
incondicional, esos tests de regresión fallarían siempre con `.venv`
`BLOCKING` — rompiendo el criterio 15(a) ("los tests existentes siguen
pasando sin modificar sus aserciones"). Condicionar el chequeo a la
presencia de `backend/requirements.txt` resuelve el conflicto sin tocar
esos tests: en el repositorio real de `gi-ocr` (que sí tiene
`backend/requirements.txt`), el chequeo se sigue ejecutando con todo su
rigor (ver `tests/test_preflight_script.py`, que construye repos
sintéticos con `backend/requirements.txt` presente específicamente para
ejercitar las ramas `BLOCKING` de Python/`.venv`).

## Decisión: ventana oculta del reconciliador (criterio 8)

`scripts/start-local-reconciler.ps1` lanza el proceso en segundo plano vía
WMI (`Win32_Process.Create`). Antes de esta feature, la llamada no pasaba
información de arranque, lo que podía dejar una consola visible corriendo
hasta `MaxMinutes` (1440 por defecto = 24 horas).

**Intento inicial (revertido, documentado por transparencia).** La
primera implementación usó los cmdlets modernos de CIM, tal como sugería
el spec:

```powershell
$startupInfo = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{
    ShowWindow = 0
    CreateFlags = 0x08000000
}
$created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $cmdLine
    CurrentDirectory = $mainRoot
    ProcessStartupInformation = $startupInfo
}
```

Verificado con la suite completa de `tests/test_local_reconciler_scripts.py`
corrida localmente: esto **rompía el arranque del reconciliador** en este
entorno (Windows PowerShell 5.1) — `Invoke-CimMethod` fallaba con
`"Los tipos no coinciden"` (`HRESULT 0x80041005`, `InvalidType`) al pasar
el objeto `ProcessStartupInformation` embebido, sin importar si llevaba
`ShowWindow`, `CreateFlags`, ambos o ninguno seteado — un problema conocido
de la capa MI (Management Infrastructure) de los cmdlets CIM al pasar
instancias `-ClientOnly` como parámetros de método embebidos. El fallo no
generaba una consola visible: directamente impedía que el reconciliador
arrancara (6 de 7 tests de esa suite fallaban con logs nunca creados),
mucho peor que el problema original.

**Implementación final.** Se reemplaza `Invoke-CimMethod`/`New-CimInstance`
por el wrapper WMI clásico (`[wmiclass]`), que sí acepta el objeto
embebido en este entorno — sigue siendo WMI/`Win32_Process`, sin cambiar
el mecanismo de lanzamiento de fondo, solo la familia de cmdlets usada
para invocarlo:

```powershell
$startupInfo = ([wmiclass]"Win32_ProcessStartup").CreateInstance()
$startupInfo.ShowWindow = [uint16] 0

$processClass = [wmiclass]"Win32_Process"
$created = $processClass.Create($cmdLine, $mainRoot, $startupInfo)
```

`ShowWindow = 0` es `SW_HIDE`. **No se agrega `CreateFlags`
(`CREATE_NO_WINDOW` = `0x08000000`).** Verificado empíricamente en este
entorno: pasar `CreateFlags = 0x08000000` a `Win32_Process.Create` (con
cualquiera de los dos mecanismos, CIM o `[wmiclass]`) devuelve
`ReturnValue = 21` (`Invalid Parameter`) — `Win32_ProcessStartup.CreateFlags`
no acepta ese valor en este entorno, aunque `CREATE_NO_WINDOW` es un valor
válido de la API `CreateProcess` nativa. `ShowWindow = 0` (`SW_HIDE`) por
sí solo alcanza para el objetivo del criterio 8 (esconder la ventana del
proceso en segundo plano) y no produce ese error; es además el mecanismo
más citado en la práctica para este caso de uso concreto (ocultar
consolas lanzadas vía `Win32_Process.Create`). Esta es exactamente la
situación que la sección "Riesgos / supuestos" del spec anticipó y
autorizó resolver a discreción del builder si el mecanismo sugerido no
alcanzaba en el entorno real de ejecución.

**Verificación aceptada para este criterio puntual (decisión explícita
del spec, no del builder):** no se agrega un test automatizado que falle
si en el futuro se rompe esta configuración. Motivo: `tests/test_local_reconciler_scripts.py`
completo ya se salta en CI (`pytestmark = pytest.mark.skipif(os.name != "nt" or ...)`),
y `.github/workflows/ci.yml` corre en `runs-on: ubuntu-latest`, donde
`os.name` es `"posix"` — un test ejecutable de este detalle puntual
tampoco correría en CI hoy. La verificación real es esta cita textual del
parámetro exacto, más la suite completa de
`tests/test_local_reconciler_scripts.py` (arranque, log, lock,
deduplicación, limpieza, no-borrado si hay cambios sin commitear)
corrida localmente en Windows como parte de esta feature, sin modificar
sus aserciones de negocio.

## `scripts/wait-pr-ci.ps1 -Snapshot`

Consulta puntual, no bloqueante: `gh pr view <ref> --json number,url,state,mergeStateStatus`
y `gh pr checks <ref>` (sin `--watch`), una sola vez cada una. Siempre
termina en exit `0`, sin importar si los checks están en verde, en rojo o
pendientes — es una foto, no un gate. Si la PR no existe todavía para la
rama (`gh pr view` retorna código distinto de `0`): exit distinto de `0`
y mensaje explícito ("No existe PR para `<ref>` todavia"). El modo actual
sin `-Snapshot` (bloqueante, `--watch`) no cambió su comportamiento.

## `scripts/close-feature.ps1` — reintento de push pendiente

Antes de esta feature: si el estado local ya era `"already-closed"`
(`ROADMAP.md` local con `[x] <slug>`), el script saltaba directo a la
verificación remota (`Assert-RoadmapClosedOnce` contra
`origin/<base>:ROADMAP.md`), sin reintentar el push. Si el commit de
cierre había quedado hecho localmente pero el `git push origin develop`
había fallado (corte de red), cada reejecución fallaba con "validación
fallida en `origin/develop`" sin nunca resolver la causa real.

Corrección: en la rama `"already-closed"`, el script ahora hace
`git fetch origin <base>` y compara el estado de `<slug>` en
`origin/<base>:ROADMAP.md`. Si `origin/<base>` todavía no tiene el
commit de cierre (`Done -ne 1`), reintenta el push
(`git push origin <base>`) antes de continuar a la verificación final.
Si `origin/<base>` ya lo tiene (caso "already-closed" real, el más
común), no hace ningún push adicional — sigue siendo idempotente sin
duplicar commits ni generar pushes de más en reintentos múltiples
seguidos.

## Nota operativa — entrada de `ROADMAP.md` faltante

Al implementar esta feature, `ROADMAP.md` (en el punto de partida de esta
rama, heredado de `develop`) no tenía ninguna entrada para el slug
`03-cierre-operativo-circuito-agentico` — el backlog solo llegaba hasta
`03-empaquetado-despliegue`, y los slugs futuros que el spec aprobado ya
cita explícitamente en su sección "Explícitamente fuera de alcance"
(`10-calidad-ci-lint-formato`, `11-empaquetado-despliegue`,
`12-release-versionado-productivo`) tampoco existían todavía en el
backlog. El `builder-agent` agregó la entrada `[ ]` mínima necesaria para
que `ready-for-pr.ps1`/`Assert-FeatureContract` puedan operar sobre esta
feature (requisito técnico duro del circuito, no una decisión de
producto), sin renumerar ni tocar la entrada preexistente
`03-empaquetado-despliegue` (que no es responsabilidad de esta feature).
Ver `runs/03-cierre-operativo-circuito-agentico/decision.md`, sección
"Nota sobre ROADMAP.md", para el detalle completo señalado al humano.

## Cobertura de tests y su alcance en CI

- `tests/test_feature_contract_scripts.py`: extendido con
  `Get-FeatureContractStatus` (reporte con 2+ artefactos faltantes
  simultáneos, sin lanzar) y con el caso de `ready-for-pr.ps1` abortando
  por herramientas antes de tocar `ROADMAP.md`. Corre en CI
  (`ubuntu-latest`, con `pwsh`).
- `tests/test_wait_pr_ci_script.py` (nuevo): `-Snapshot` con PR existente,
  `-Snapshot` con PR inexistente, y regresión del modo `--watch` (éxito y
  fallo). Corre en CI (`gh` falso multiplataforma, igual patrón que
  `tests/test_feature_contract_scripts.py`).
- `tests/test_close_feature_script.py`: agrega
  `test_retries_pending_push_when_close_commit_exists_locally_but_not_pushed`
  (criterio 9). Corre en CI.
- `tests/test_local_reconciler_scripts.py`: sin cambios de aserciones;
  sigue verificando arranque/log/lock/deduplicación/limpieza tras el
  cambio de ventana oculta. **Ya se salta en CI** (`ubuntu-latest`, ver
  criterio 8 más abajo).
- `tests/test_preflight_script.py` (nuevo): un test dedicado por cada fila
  `BLOCKING`/`WARNING` de la matriz (8 filas), más casos `OK`
  representativos, el invariante de solo-lectura (criterio 5), y el modo
  genérico (criterios 1-3). Se gatea igual que
  `tests/test_local_reconciler_scripts.py`
  (`pytestmark = pytest.mark.skipif(os.name != "nt" or ...)`), porque
  construye múltiples worktrees reales y compara rutas en formato
  Windows. **Se salta en CI** por el mismo motivo que la suite del
  reconciliador local — no es una laguna nueva de esta feature, es
  consistente con la limitación ya aceptada del proyecto. La evidencia
  real de esta suite (20 tests en verde) es local, en Windows, documentada
  en `runs/03-cierre-operativo-circuito-agentico/decision.md`.

## Tabla de interrupción/recuperación por paso del circuito

| Paso | Qué puede interrumpirlo | Cómo se retoma | Trabajo perdido/duplicado si se retoma bien |
|---|---|---|---|
| `builder-agent` (código + docs en worktree) | Cierre de sesión, corte de red, error no manejado | `git status --short` y `git log feature/<slug> ^develop` muestran qué se commiteó. `preflight.ps1 -Slug` reporta el contrato de artefactos faltante. | Ninguno: git es la fuente de verdad. |
| `qa-agent` / `ready-for-pr.ps1` | Corte de red/`gh` durante push o creación de PR, o falla del diagnóstico genérico de herramientas al inicio (`Assert-ToolchainReady`) | `ready-for-pr.ps1` es idempotente: si `[-]` ya está marcado no repite el commit; si ya existe PR la reusa (`Get-ExistingPr`). Un agente puede correr `preflight.ps1 -Slug <slug>` por separado para confirmar si falta el push antes de re-correr `ready-for-pr.ps1`. | Ninguno (script no reescrito). |
| `wait-pr-ci.ps1` (espera de CI) | Matar el proceso que corre `--watch` | No hay estado local: CI sigue en GitHub. Se retoma con `wait-pr-ci.ps1` de nuevo (bloqueante) o `-Snapshot` (no bloqueante) para decidir si conviene volver a esperar. | Ninguno: consulta remota repetible. |
| `start-local-reconciler.ps1` / `reconcile-local-feature.ps1` | Reinicio de máquina, cierre de sesión, `taskkill` accidental | El lock queda con un PID muerto. `preflight.ps1` (genérico o `-Slug`) lo detecta y recomienda relanzar `start-local-reconciler.ps1 -Slug <slug>` (seguro: reemplaza lock obsoleto, no duplica si el proceso sigue vivo). | Ninguno si se relanza vía el script: solo polling read-only hasta ver `[x]` en `origin/develop`. |
| `close-feature.ps1` (cierre post-merge) | Falla de red entre el commit de cierre y el push | Antes de esta feature: fallaba en la verificación final sin reintentar. Después: una reejecución simple resuelve el push pendiente sin intervención manual (criterio 9). | Ninguno tras la corrección: no se duplica el commit de cierre. |
