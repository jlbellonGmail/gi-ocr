```yaml
status: approved
attempt: 1
feedback:
  - "No bloqueante / informativo: en este worktree (D:\\proyectos\\worktrees\\04-cierre-operativo-circuito-agentico) no existe un .venv propio (el repo comparte .venv en la raíz D:\\proyectos\\gi-ocr), por lo que 'preflight.ps1' sin -Slug reporta correctamente [BLOCKING] '.venv no existe' al correrlo parado en este worktree. No es un bug: preflight.ps1 evalúa el .venv del repositorio raíz que contiene el working tree actual (Get-RepositoryRoot), y en este entorno de trabajo con git worktrees ese .venv efectivamente no existe ahí. El criterio 1 ('repo sano') se valida igual mediante los tests sintéticos de tests/test_preflight_script.py (test_generic_mode_ok_on_healthy_repo, PASSED), que construyen un repo de prueba con .venv completo; no hace falta que el worktree de QA en sí mismo tenga .venv para que el criterio quede demostrado."
```

# Test Report — 04-cierre-operativo-circuito-agentico (intento 1)

## Contexto de esta corrida de QA

Esta feature fue renombrada de `03-cierre-operativo-circuito-agentico` a
`04-cierre-operativo-circuito-agentico` (rama, worktree, `runs/`, docs,
comentarios de script) **antes** de este paso de QA, para no dejar dos
entradas `03-*` colisionando con `03-empaquetado-despliegue` en
`ROADMAP.md` (`develop` avanzó en paralelo al cerrarse
`02-mejora-precision-ocr`). El spec (`spec.md`) y las auditorías
(`audit-1.md` rejected, `audit-2.md` approved) siguen siendo válidos en
contenido — solo cambió el número/slug de la feature, verificado abajo
contra el estado real del código y del `ROADMAP.md` de este worktree, no
solo contra lo que dice `decision.md`.

## 1. Suite de tests completa (`pytest`)

Comando corrido desde la raíz del worktree, con `--basetemp` propio
(el `%TEMP%\pytest-of-<user>` por defecto no dio problemas de permisos en
esta corrida, pero se usó `--basetemp` igual por seguridad frente a
procesos concurrentes de otras sesiones trabajando en el mismo repo):

```
D:/proyectos/gi-ocr/.venv/Scripts/pytest.exe tests/ -v \
  --basetemp="C:/Users/jlbel/AppData/Local/Temp/qa-04-cierre/run1"
```

Resultado real (log completo capturado, no resumido de memoria):

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 51 items / 1 skipped
...
================== 51 passed, 1 skipped in 393.71s (0:06:33) ==================
```

- `SKIPPED [1] tests/e2e/test_e2e_playwright.py:19`: preexistente, no
  relacionado con esta feature (`playwright` no instalado en `.venv`; no
  es parte del alcance de `04-cierre-operativo-circuito-agentico`).
- **51/51 tests relevantes PASSED**, incluidos:
  - `tests/test_preflight_script.py` — 19 tests: modo genérico (repo
    sano, `git`+`gh` ausentes simultáneos, python viejo+`.venv` ausente
    simultáneos, `develop` sucio sin auto-fix, invariante de solo
    lectura) y modo `-Slug` (las 9 filas de la matriz worktree/rama/
    ROADMAP requeridas por el criterio 4: `pending` OK/OK-informativo,
    `ready` OK-informativo/BLOCKING×2, `done` OK/WARNING×2/BLOCKING,
    entrada duplicada BLOCKING, entrada ausente BLOCKING, slug inválido,
    worktree fuera de convención WARNING, worktree huérfano en disco
    WARNING, lock de reconciliador muerto con log de error WARNING).
    Cuenta: 5 tests `BLOCKING` dedicados + 5 tests `WARNING` dedicados
    ≥ el mínimo de 8 exigido por el criterio 4 (4 filas BLOCKING + 4
    WARNING en la matriz del spec).
  - `tests/test_feature_contract_scripts.py` — 9 tests, incluye
    `test_ready_for_pr_blocks_real_gh_error` **PASSED** (la nota no
    bloqueante de `audit-2.md` se verifica resuelta: el mensaje de aborto
    de `Assert-ToolchainReady` sigue propagando el stderr crudo de `gh
    auth status`, confirmado leyendo `feature-contract.ps1` líneas
    443-444 y el test pasa sin haber sido modificado en sus aserciones
    según `git diff develop -- tests/test_feature_contract_scripts.py`)
    y `test_ready_for_pr_blocks_before_touching_roadmap_when_toolchain_check_fails`
    (test nuevo del criterio 15b).
  - `tests/test_local_reconciler_scripts.py` — 7 tests de comportamiento
    (arranque desde checkout principal y desde worktree enlazado, no
    duplicación mientras corre, reemplazo de lock obsoleto, limpieza de
    worktree/rama al detectar cierre remoto, limpieza acotada solo al
    slug objetivo, no-borrado con cambios sin commitear), todos PASSED
    sin modificación de aserciones de negocio (criterio 8).
  - `tests/test_close_feature_script.py` — 10 tests, incluye el test
    nuevo dedicado al criterio 9
    (`test_retries_pending_push_when_close_commit_exists_locally_but_not_pushed`)
    y el test de regresión de idempotencia real
    (`test_already_closed_feature_is_idempotent_and_does_not_create_empty_commit`),
    ambos PASSED.
  - `tests/test_wait_pr_ci_script.py` — 4 tests: `-Snapshot` con PR
    existente (no bloqueante, exit 0), `-Snapshot` sin PR (exit distinto
    de 0, mensaje explícito), y dos tests de regresión del modo `--watch`
    existente (éxito y fallo), sin cambios de comportamiento.

No hubo necesidad de usar `--basetemp` por `PermissionError` en esta
corrida puntual (no se observó el problema conocido de entorno), pero se
usó de todas formas por higiene frente a corridas concurrentes.

## 2. Verificación manual de los 15 criterios de aceptación (no solo lo que dice `decision.md`)

**Criterio 1** (`preflight.ps1` sin parámetros, repo sano, exit 0,
`PREFLIGHT: OK`): verificado indirectamente por
`test_generic_mode_ok_on_healthy_repo` (repo sintético completo, PASSED).
Corrida real manual desde este worktree (`D:\proyectos\worktrees\04-cierre-operativo-circuito-agentico`)
da `[BLOCKING] .venv no existe` porque este worktree en particular no
tiene `.venv` propio (comparte el de la raíz `D:\proyectos\gi-ocr` por
convención local de desarrollo, no por el repo). No es un defecto del
script: `Get-ToolchainDiagnostics` evalúa el `.venv` del repositorio
(`Get-RepositoryRoot`) que contiene el working tree actual, correctamente
en este caso. El criterio queda demostrado por el test sintético, que sí
controla las condiciones de "repo sano" de punta a punta.

**Criterio 2** (múltiples problemas simultáneos, exit 1, cada línea con
acción concreta): verificado por
`test_generic_mode_reports_missing_git_and_gh_simultaneously` y
`test_generic_mode_reports_old_python_and_missing_venv_simultaneously`
(PASSED). Revisé el código de `Get-ToolchainDiagnostics`
(`feature-contract.ps1` líneas 401-576): no hace `return` temprano en
ningún chequeo, acumula todos los resultados en `$results` y los
devuelve juntos; cada `Add-ToolResult` con severidad `BLOCKING` lleva un
`$Action` no vacío.

**Criterio 3** (`develop` sucio → `BLOCKING`, exit 1, sin auto-fix):
verificado por `test_generic_mode_reports_blocking_for_dirty_develop_without_auto_fixing`
(PASSED). Código (`Get-DevelopBranchDiagnostics`, líneas 104-165 de
`preflight.ps1`): solo llama `git status --porcelain` (lectura) y
`git fetch` (lectura); ningún `git stash`/`git checkout`/`git commit` en
todo el script — confirmado con `grep` sobre `preflight.ps1` completo, no
aparece ningún verbo mutante de `git` salvo `fetch`.

**Criterio 4** (matriz completa con severidad/acción, ≥1 test por fila
BLOCKING/WARNING): 19 tests dedicados en `test_preflight_script.py`
cubren las 9 combinaciones de la matriz (ver arriba), todos PASSED.
Revisé `Get-FeatureMatrixDiagnostics` (`preflight.ps1` líneas 237-350)
línea por línea contra la tabla del spec: los `switch` de `pending`/
`ready`/`done` reproducen exactamente las condiciones y mensajes de
severidad/acción de la tabla (incluyendo el caso `[x]`/worktree-sin-rama
como `BLOCKING`, y el caso de worktree fuera de convención como
`WARNING` no bloqueante).

**Criterio 5** (`preflight.ps1` nunca muta el repo):
`test_preflight_never_mutates_the_repository` PASSED, compara
`git rev-parse HEAD` y `git worktree list` antes/después de una corrida
con `-Slug`. Revisé el código completo de `preflight.ps1`: el único
verbo `git` que no es de solo lectura sería `fetch`, permitido
explícitamente por el criterio. No hay `git add`/`commit`/`push`/
`branch -d`/`worktree remove` en ningún punto del script.

**Criterio 6** (`Get-FeatureContractStatus` no-throwing + `Assert-FeatureContract`
sigue lanzando + test con ≥2 artefactos faltantes a la vez):
`test_feature_contract_status_reports_multiple_missing_artifacts_without_throwing`
PASSED (nuevo, cubre `decision.md` + enlace en `docs/usuario/index.md`
faltantes simultáneamente). `test_ready_gate_fails_when_decision_or_index_link_is_missing`
sigue PASSED sin modificar sus aserciones (confirmado por `git diff
develop -- tests/test_feature_contract_scripts.py`, que solo agrega
tests nuevos, no toca los existentes).

**Criterio 7** (`wait-pr-ci.ps1 -Snapshot`): 4 tests PASSED. Verificación
manual real corrida en este worktree (`scripts/wait-pr-ci.ps1 -Snapshot`,
sin PR real todavía para esta rama): exit code `1`, mensaje `"No existe
PR para 'feature/04-cierre-operativo-circuito-agentico' todavia (gh no
pudo resolverla)."` — coincide exactamente con lo que exige el criterio.

**Criterio 8** (ventana oculta del reconciliador): revisado en código
real, no solo en `decision.md`. `scripts/start-local-reconciler.ps1`
líneas 82-88 usan `[wmiclass]"Win32_ProcessStartup"` con
`$startupInfo.ShowWindow = [uint16] 0` y `[wmiclass]"Win32_Process"` para
`Create`. **No** se pasa `CreateFlags = CREATE_NO_WINDOW`. Esto es
coherente con lo que permite el spec: la sección "Riesgos / supuestos"
autoriza explícitamente reemplazar el mecanismo si `CreateFlags` no
alcanza en el entorno real ("el builder puede reemplazarlo... dejando la
decisión técnica documentada en decision.md"), y el criterio 8 en sí
mismo ofrece la alternativa `Start-Process -WindowStyle Hidden` como
mecanismo equivalente aceptado. Aquí no se cambió de mecanismo (se
mantiene WMI/`Win32_Process.Create`), solo se omitió un parámetro que
`decision.md` documenta como roto en este entorno (`ReturnValue=21,
Invalid Parameter`) — decisión técnica explícita y justificada, dentro
de lo que el spec permite. `docs/tecnica/cierre-operativo-circuito-agentico.md`
documenta la decisión con cita del parámetro exacto, cumpliendo la
verificación aceptada del criterio 8 (revisión estructural documentada,
sin exigir test ejecutable — justificado porque
`tests/test_local_reconciler_scripts.py` completo se salta en CI,
`runs-on: ubuntu-latest`). Los 7 tests de comportamiento de
`test_local_reconciler_scripts.py` pasan sin modificar aserciones de
negocio (confirmado por `git diff develop -- tests/test_local_reconciler_scripts.py`,
que no toca ese archivo).

**Criterio 9** (`close-feature.ps1` reintenta push pendiente en
already-closed): revisado en código, líneas 264-276 de
`close-feature.ps1`: en el branch `already-closed`, hace
`git fetch origin $baseBranch`, lee `origin/$baseBranch:ROADMAP.md`, y si
`$remoteStatePreCheck.Done -ne 1` reintenta `git push origin
$baseBranch` **antes** de caer en la verificación final (líneas 299-302,
compartida con el otro branch). Test dedicado
`test_retries_pending_push_when_close_commit_exists_locally_but_not_pushed`
PASSED. Test de regresión `test_already_closed_feature_is_idempotent_and_does_not_create_empty_commit`
PASSED sin modificar aserciones.

**Criterio 10** (`docs/tecnica/cierre-operativo-circuito-agentico.md`,
436 líneas, no vacío): confirmado no vacío y con la matriz completa,
códigos de salida, tabla de interrupción/recuperación, decisión de
ventana oculta y decisión del conflicto criterio 4/15 (verificado
abriendo el archivo).

**Criterio 11** (`docs/usuario/cierre-operativo-circuito-agentico.md`,
156 líneas, no vacío, con ejemplos de invocación y caso BLOCKING):
confirmado no vacío.

**Criterio 12** (`runs/04-cierre-operativo-circuito-agentico/decision.md`
existe, patrón `New-DecisionFile`): confirmado, 68 líneas, con
"## Estado", "## Evidencias revisadas", "## Decisiones demostrables",
"## Resultado" (mismo patrón que otras features del circuito).

**Criterio 13** (enlace exacto en `docs/tecnica/index.md`): confirmado —
`- [Cierre Operativo del Circuito Agentico](cierre-operativo-circuito-agentico.md)`
en línea 11.

**Criterio 14** (enlace exacto en `docs/usuario/index.md`, mismo
título): confirmado — `- [Cierre Operativo del Circuito Agentico](cierre-operativo-circuito-agentico.md)`
en línea 9. Título idéntico carácter por carácter al de `docs/tecnica/index.md`.

**Criterio 15** (`ready-for-pr.ps1` invoca `Assert-ToolchainReady` al
inicio, antes de tocar `ROADMAP.md`; deja de definir
`Get-GitHubCliPath`/`Get-PowerShellPath` localmente): confirmado en
código — `scripts/ready-for-pr.ps1` línea 114 llama `Assert-ToolchainReady`,
y recién en la línea 141+ se toca `ROADMAP.md` por primera vez (comentario
explícito en línea 42-44 de que `Get-GitHubCliPath`/`Get-PowerShellPath`
se reutilizan de `feature-contract.ps1` vía dot-sourcing, no se
redefinen). `test_ready_for_pr_blocks_real_gh_error` PASSED sin modificar
sus aserciones (confirmado por diff). Test nuevo
`test_ready_for_pr_blocks_before_touching_roadmap_when_toolchain_check_fails`
PASSED.

## 3. Contrato de artefactos (`Assert-FeatureContract`)

Corrida real vía `feature-contract.ps1` dot-sourced, `Assert-FeatureContract
-Slug '04-cierre-operativo-circuito-agentico' -Title 'Cierre Operativo del
Circuito Agentico'`:

- Antes de crear este `test-report-1.md`: falla con
  `"Falta al menos un test-report-N.md en runs/04-cierre-operativo-circuito-agentico."`
  — comportamiento correcto y esperado (todavía no existía).
- Con este archivo commiteado, el contrato queda completo: `spec.md`,
  `audit-1.md`, `audit-2.md`, `test-report-1.md`, `decision.md`,
  `docs/tecnica/cierre-operativo-circuito-agentico.md`,
  `docs/usuario/cierre-operativo-circuito-agentico.md`, enlaces exactos
  en ambos índices, entrada `04-cierre-operativo-circuito-agentico` en
  `ROADMAP.md`.

## 4. `ROADMAP.md`

`git grep -n "04-cierre-operativo-circuito-agentico\|03-empaquetado-despliegue" ROADMAP.md`
confirma exactamente una entrada `- [ ] 03-empaquetado-despliegue` (sin
tocar) y exactamente una entrada `- [ ] 04-cierre-operativo-circuito-agentico`
(la de esta feature, estado `[ ]` correcto en esta etapa del circuito —
todavía no pasó por `ready-for-pr.ps1`, que es quien la marcará `[-]`).
`decision.md` documenta con transparencia la renumeración de `03` a `04`
por colisión detectada contra `origin/develop` en tiempo real; verificado
que es consistente con el estado actual del `ROADMAP.md` de este
worktree.

## 5. Alcance de archivos tocados

`git diff develop --stat` (19 archivos): `ROADMAP.md`, `docs/tecnica/`
+ `docs/usuario/` (archivo nuevo + índice cada uno), `runs/04-cierre-operativo-circuito-agentico/`
(4 archivos), `scripts/{close-feature,feature-contract,preflight,
ready-for-pr,start-local-reconciler,wait-pr-ci}.ps1`,
`tests/{test_close_feature_script,test_feature_contract_scripts,
test_preflight_script,test_wait_pr_ci_script}.py`. **Cero archivos bajo
`backend/app/` o `backend/config/`** — confirmado, coincide con el
alcance declarado en el spec ("esta feature no toca `backend/app/` ni
`backend/config/`").

## Conclusión

Los 15 criterios de aceptación están verificados contra el código real
(no solo contra `decision.md`), la suite completa de tests pasa en verde
(51 passed, 1 skipped preexistente y no relacionado), el contrato de
artefactos queda completo tras agregar este reporte, `ROADMAP.md` está
correcto (una sola entrada `04-*`, `03-empaquetado-despliegue` intacto), y
el alcance de archivos tocados respeta la exclusión de `backend/app/` y
`backend/config/`. Se aprueba.
