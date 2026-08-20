# Spec: Cierre operativo del circuito agéntico

## Alcance

Endurecer el uso cotidiano del circuito descrito en `AGENTS.md` con
herramientas de diagnóstico y recuperación, sin cambiar su forma. Incluye:

- **Script nuevo `scripts/preflight.ps1`**, de solo lectura (nunca muta el
  repo: no commitea, no pushea, no borra ramas/worktrees), con dos modos:
  - Modo genérico (sin parámetros): diagnostica herramientas locales
    (`git`, `gh`, PowerShell, Python, `.venv`) y el estado de la rama base
    (`develop`).
  - Modo por feature (`-Slug <NN-slug>`): además del modo genérico,
    diagnostica consistencia de worktree/rama/`ROADMAP.md` para esa
    feature puntual, el estado del contrato de artefactos
    (`Assert-FeatureContract` en modo reporte, sin abortar en el primer
    faltante), el estado de PR/CI, y el estado del reconciliador local.
- **Extensión de `scripts/feature-contract.ps1`**: agregar una función de
  reporte no-throwing (`Get-FeatureContractStatus` o equivalente) que
  devuelva qué artefactos están/faltan sin lanzar excepción en el primer
  problema; `Assert-FeatureContract` pasa a ser un wrapper que llama a esa
  función y lanza si hay algo faltante — comportamiento externo sin
  cambios para quien ya la usa (`ready-for-pr.ps1`, tests existentes).
  Además se agrega, en el mismo archivo o en `preflight.ps1`, una función
  compartida de **diagnóstico genérico de herramientas** (`git`, `gh`
  binario + autenticación, PowerShell, Python, `.venv`) que reutilizan
  tanto `preflight.ps1` (modo sin `-Slug`) como `ready-for-pr.ps1` (ver
  criterio 15).
- **Extensión de `scripts/wait-pr-ci.ps1`**: agregar modo `-Snapshot` que
  consulta el estado actual de PR/CI una sola vez (sin `--watch`) y
  siempre retorna un reporte legible, sin bloquear ni exigir CI verde.
  El modo actual (`--watch`, bloqueante) no cambia.
- **Extensión de `scripts/start-local-reconciler.ps1`**: el proceso en
  segundo plano lanzado vía `Win32_Process.Create` debe arrancar sin
  ventana de consola visible, pasando explícitamente información de
  arranque oculta (`ProcessStartupInformation.ShowWindow = 0` +
  `CreateFlags` con `CREATE_NO_WINDOW` = `0x08000000`, o un mecanismo
  equivalente que garantice la misma propiedad si se reemplaza WMI).
- **Extensión puntual de `scripts/close-feature.ps1`**: cuando el estado
  local ya es "already-closed" (ROADMAP local con `[x]`) pero el commit
  de cierre todavía no llegó a `origin/<base>` (por ejemplo, un intento
  previo commiteó localmente pero el `git push` falló por red), el script
  debe intentar el push pendiente antes de la verificación final, en vez
  de saltar directo a una verificación que siempre va a fallar.
- **Extensión puntual de `scripts/ready-for-pr.ps1`** (ver criterio 15):
  invoca el diagnóstico genérico de herramientas antes de tocar
  `ROADMAP.md`, reutilizando la función compartida en vez de sus
  definiciones locales de `Get-GitHubCliPath`/`Get-PowerShellPath`.
- **Documentación** (`docs/tecnica/`, `docs/usuario/`) de: la matriz de
  estados worktree/rama/ROADMAP con severidad y acción recomendada por
  cada caso, los códigos de salida y mensajes de `preflight.ps1`, y la
  tabla de "qué paso del circuito puede interrumpirse y cómo se retoma".

**Explícitamente fuera de alcance:**

- Cambiar la topología de 4 agentes (`analyst-agent` → `reviewer-agent` →
  `builder-agent` → `qa-agent`).
- Automatizar la decisión humana `MERGE`/`NO MERGE`. El HITL sigue siendo
  el único punto de aprobación humana del circuito.
- Reescribir desde cero cualquiera de los scripts existentes
  (`feature-contract.ps1`, `ready-for-pr.ps1`, `wait-pr-ci.ps1`,
  `close-feature.ps1`, `start-local-reconciler.ps1`,
  `reconcile-local-feature.ps1`, `update-doc-indexes.ps1`). Solo se
  extienden puntualmente, o se agrega `preflight.ps1` como script nuevo.
- Crear un mecanismo de auto-arranque de `start-local-reconciler.ps1`
  tras un reinicio de máquina (p. ej. tarea programada de Windows). El
  gap de "nadie relanza el reconciler tras una interrupción" se resuelve
  con **detección + recomendación explícita** vía `preflight.ps1`, no con
  un supervisor automático nuevo.
- Detectar en tiempo real si `ready-for-pr.ps1` está corriendo en ese
  instante desde otro proceso (p. ej. inspeccionar procesos vivos para
  distinguir "está a punto de pushear" de "se interrumpió de verdad").
  Esta feature acepta una limitación conocida y acotada en su lugar (ver
  criterio 15 y "Casos borde a contemplar").
- Cambiar motor OCR, formato `.DATA`/`services.ini`, ni la separación
  OCR/extracción/validación/storage (`docs/tecnica/arquitectura.md`,
  ADR-006/ADR-007). Esta feature no toca `backend/app/` ni
  `backend/config/`.
- Empaquetado/despliegue (Docker, `release.yml`) — eso es
  `11-empaquetado-despliegue`/`12-release-versionado-productivo`, no esta
  feature.
- Lint/formato de código (`10-calidad-ci-lint-formato`).

## Contexto

El circuito de `AGENTS.md` ya funciona: quedó demostrado end-to-end en
`01-captura-ocr-local-agil` (spec → review → build → QA → ready-for-pr →
PR → CI verde → merge → cierre automático). Pero varias piezas dependen
hoy de que el agente/humano recuerde comandos y estados de memoria:

- No hay un solo comando que diga "¿está este repo listo para arrancar
  una feature, o hay algo roto?" — hoy hay que inspeccionar `git status`,
  `git worktree list`, `git branch`, `ROADMAP.md` y `gh auth status` a
  mano, en varios pasos.
- `Get-GitHubCliPath` está duplicada de forma idéntica en
  `ready-for-pr.ps1` (líneas 42-54), `wait-pr-ci.ps1` (líneas 7-19) y
  `close-feature.ps1` (líneas 58-70) — cada script falla recién cuando
  llega a necesitar `gh`, no antes, y con mensajes que no cubren todos
  los problemas de una sola vez. **Corrección respecto del intento 1 de
  esta spec:** `Get-PowerShellPath` **no** está duplicada en los tres
  scripts — verificado en el código, solo existe en `ready-for-pr.ps1`
  (líneas 56-68), porque es el único de los tres que lanza un proceso de
  PowerShell hijo (el reconciliador local, vía
  `start-local-reconciler.ps1`); `wait-pr-ci.ps1` y `close-feature.ps1`
  no la necesitan. El intento 1 de esta spec afirmaba incorrectamente que
  estaba duplicada en los tres; se corrige acá para que el builder no
  intente deduplicar una función que no está duplicada donde se decía.
- El estado de PR/CI solo se puede consultar en modo bloqueante
  (`wait-pr-ci.ps1`, `gh pr checks --watch`) o manualmente con `gh`. No
  hay una foto rápida no bloqueante para que un agente decida si conviene
  esperar o seguir con otra cosa.
- `start-local-reconciler.ps1` lanza un proceso de PowerShell en segundo
  plano vía WMI (`Win32_Process.Create`, verificado en líneas 74-82: no
  pasa `ShowWindow`/`CreateFlags`) sin especificar arranque oculto de
  ventana; según el usuario que ejecuta el circuito, esto puede dejar una
  consola visible corriendo hasta 24 horas (`MaxMinutes` por defecto =
  1440), lo cual es justamente el tipo de UX que esta feature debe evitar
  en cualquier script que se dispare en background/automatización.
- `close-feature.ps1` es en general idempotente (ver
  `tests/test_close_feature_script.py`), pero tiene un caso de
  interrupción sin cubrir: si el commit de cierre queda hecho localmente
  pero el `git push origin develop` falla (por ejemplo, corte de red), una
  reejecución detecta `closeState -eq "already-closed"` y **salta
  directamente a la verificación remota sin reintentar el push**
  (verificado: líneas 264-292 del script), produciendo un error de
  "validación fallida en origin/develop" en cada reintento, sin nunca
  resolver la causa real (falta pushear).
- Nadie relanza `start-local-reconciler.ps1` si el proceso murió (crash,
  reinicio de máquina) mientras esperaba el merge — el lock/log quedan en
  `<git-common-dir>/feature-reconcilers/`, pero solo se limpian recién
  cuando alguien vuelve a correr `ready-for-pr.ps1` para esa misma
  feature.

Esta feature no agrega pasos al circuito ni cambia quién decide qué;
agrega **diagnóstico** (preflight), **visibilidad** (estado de PR/CI sin
bloquear) y **endurece la recuperación** de las dos piezas del circuito
que hoy son procesos de fondo sin supervisión (`start-local-reconciler.ps1`,
`close-feature.ps1`).

### Matriz de consistencia worktree / rama / ROADMAP (modo `-Slug`)

`preflight.ps1 -Slug <NN-slug>` debe evaluar la siguiente tabla y reportar
la fila que corresponde, con severidad y acción recomendada. "Local
branch" = `git branch --list feature/<slug>`; "Worktree" = entrada en
`git worktree list` bajo `../worktrees/<slug>/`; "Remote branch" =
`git ls-remote origin feature/<slug>`; "ROADMAP" = estado exacto de la
entrada `<slug>` en el `ROADMAP.md` del working tree actual **y**, cuando
aplica, en `origin/develop:ROADMAP.md` (son lecturas distintas porque
pueden diferir mientras la feature está en curso).

| ROADMAP (local) | Local branch | Worktree | Remote branch | Severidad | Interpretación / acción recomendada |
|---|---|---|---|---|---|
| `[ ]` | no | no | no | OK | Feature no iniciada. |
| `[ ]` | sí | sí | no o sí | OK (informativo) | Feature en progreso, normal. |
| `[-]` | sí | sí | sí | OK (informativo) | En camino a PR/CI; reportar estado de PR/CI (ver más abajo). |
| `[-]` | sí | sí | **no** | BLOCKING | `ready-for-pr.ps1` exige push antes de marcar `[-]`; algo se hizo a mano o el push se perdió. Acción sugerida: `git push -u origin feature/<slug>` y re-correr `ready-for-pr.ps1 <slug>` (idempotente: no repite el commit de `[-]`, solo reintenta push/PR). |
| `[-]` | no | no | sí o no | BLOCKING | Rama/worktree local ausentes con la feature todavía no cerrada remotamente. Acción sugerida: recrear el worktree desde `feature/<slug>` (`git worktree add ../worktrees/<slug> feature/<slug>`) antes de continuar. |
| `[x]` (local) | no | no | — | OK | Todo limpio. |
| `[x]` (local) | sí | sí | — | WARNING | El reconciliador no limpió (interrumpido o nunca se lanzó). Acción sugerida: `powershell -File scripts/start-local-reconciler.ps1 -Slug <slug>` (idempotente, no bloqueante) o, si ya se confirmó el merge, borrar a mano (`git worktree remove`, `git branch -d`). |
| `[x]` (local) | sí | no | — | WARNING | Rama local huérfana tras cierre. Acción sugerida: `git branch -d feature/<slug>`. |
| `[x]` (local) | no | sí | — | BLOCKING | Worktree sin rama asociada (estado roto, no debería ocurrir vía `git worktree remove` normal). Acción sugerida: `git worktree remove --force ../worktrees/<slug>` tras confirmar que no hay cambios sin commitear. |
| entrada ausente o duplicada en ROADMAP.md | — | — | — | BLOCKING | Mismo criterio que `Assert-FeatureContract`/`Get-FeatureInfo`: debe haber exactamente una entrada `<slug>` en `ROADMAP.md`. |
| worktree existe pero fuera de `../worktrees/<slug>/` | — | sí (otra ruta) | — | WARNING | No sigue la convención de `AGENTS.md`; no bloquea pero se reporta. |
| worktree registrado en `git worktree list` pero el directorio no existe en disco | — | — | — | WARNING | Entrada administrativa huérfana (se borró la carpeta a mano). Acción sugerida: `git worktree prune`. |

Adicionalmente, si `[-]` local y existe PR abierta: reportar snapshot de
PR/CI (ver criterio 7). Si el lock de reconciliador
(`<git-common-dir>/feature-reconcilers/<slug>.pid`) existe pero el
proceso no está vivo, y el log de error (`<slug>.err.log`) no está vacío:
WARNING "el reconciliador terminó con error, revisar
`<slug>.err.log` y relanzar si corresponde".

**Nota de alcance — resuelve el conflicto detectado en la auditoría del
intento 1 de esta spec (ver también "Riesgos / supuestos" y el criterio
15):** esta matriz la evalúa `preflight.ps1 -Slug <slug>` como comando de
diagnóstico **standalone**, invocado de forma independiente por un agente
o humano. **No** es invocada por `ready-for-pr.ps1` sobre sí mismo
durante su propia ejecución. La razón: `ready-for-pr.ps1` marca
`ROADMAP.md` como `[-]` y commitea (implementación actual, líneas
163-178) **antes** de pushear la rama (líneas 182-183). Si el chequeo
compartido de esta matriz se insertara entre esos dos pasos, el estado
normal de *cualquier* primera corrida de `ready-for-pr.ps1` coincidiría
exactamente con la fila `[-]/sí/sí/no → BLOCKING` — no por un problema
real, sino porque el push es, precisamente, el paso siguiente que el
propio script está a punto de ejecutar. Por eso `ready-for-pr.ps1`
reutiliza de `preflight.ps1` únicamente el diagnóstico genérico de
herramientas (criterio 15), y la matriz completa de esta sección queda
reservada para diagnóstico externo/posterior: correr
`preflight.ps1 -Slug <slug>` en cualquier momento en que `ready-for-pr.ps1`
**no** esté corriendo (antes de iniciar una corrida, o después de que una
corrida anterior se haya interrumpido de verdad, por ejemplo por corte de
red durante el push).

### Qué paso del circuito puede interrumpirse y cómo se retoma

| Paso | Qué puede interrumpirlo | Cómo un agente que retoma sabe dónde estaba | Trabajo perdido/duplicado si se retoma bien |
|---|---|---|---|
| `builder-agent` (código + docs en worktree) | Cierre de sesión, corte de red, error no manejado | `git status --short` y `git log feature/<slug> ^develop` en el worktree muestran exactamente qué se commiteó y qué quedó sin commitear. `preflight.ps1 -Slug` reporta el estado del contrato de artefactos (qué `.md` faltan). | Ninguno: git es la fuente de verdad, no hay estado oculto. |
| `qa-agent` / `ready-for-pr.ps1` | Igual que arriba, corte de red/`gh` durante push o creación de PR, o falla del diagnóstico genérico de herramientas al inicio del script (criterio 15) | `ready-for-pr.ps1` ya es idempotente: si `ROADMAP.md` ya tiene `[-] <slug>`, no repite el commit; si ya existe una PR para la rama, la reusa (`Get-ExistingPr`) en vez de crear otra. Tras una interrupción real (el proceso de `ready-for-pr.ps1` ya no está corriendo), un agente puede correr `preflight.ps1 -Slug <slug>` **por separado** para confirmar de antemano si falta el push, antes de simplemente re-correr `ready-for-pr.ps1`. | Ninguno (ya cubierto por el script actual; no se reescribe). |
| `wait-pr-ci.ps1` (espera de CI) | Matar el proceso que corre `--watch` | No hay estado local: CI sigue corriendo en GitHub. Se retoma con `wait-pr-ci.ps1` de nuevo (bloqueante) o `wait-pr-ci.ps1 -Snapshot` (no bloqueante) para ver el estado actual antes de decidir si volver a esperar. | Ninguno: es solo una consulta remota repetible. |
| `start-local-reconciler.ps1` / `reconcile-local-feature.ps1` (espera de merge + limpieza local) | Reinicio de máquina, cierre de sesión, `taskkill` accidental | El lock (`<slug>.pid`) queda con un PID que ya no corresponde a un proceso vivo. `preflight.ps1` (genérico o `-Slug`) detecta lock muerto y recomienda `start-local-reconciler.ps1 -Slug <slug>` de nuevo — el script ya soporta relanzarse de forma segura (detecta lock obsoleto y lo reemplaza; no duplica si el proceso sigue vivo). | Ninguno si se relanza vía el script: es solo polling read-only hasta detectar `[x]` en `origin/develop`. |
| `close-feature.ps1` (cierre post-merge) | Falla de red entre el commit de cierre y el push | Hoy: el script detecta "already-closed" localmente y salta el push, fallando en la verificación final sin reintentar — **este es el gap que corrige esta feature** (ver criterio 9). Después de la corrección: una reejecución simple resuelve el push pendiente sin intervención manual. | Ninguno tras la corrección: no se duplica el commit de cierre (ya usa `Assert-RoadmapCanClose`/`already-closed` para no volver a commitear). |

## Criterios de aceptación

1. Existe `scripts/preflight.ps1`. Ejecutado sin parámetros en un repo
   sano (git/gh/python/`.venv` OK, `develop` limpio y sincronizado),
   termina con exit code `0` y un resumen `PREFLIGHT: OK`.
2. `scripts/preflight.ps1` diagnostica, en una sola corrida (sin abortar
   en el primer problema), la ausencia o mala configuración de cada una
   de: `git`, `gh` (binario ausente y binario presente pero no
   autenticado son casos distintos y ambos reportados), PowerShell
   (`powershell.exe`/`pwsh`, al menos una debe existir), Python (`python`
   ausente o versión `< 3.12`), `.venv` (ausente, o presente mas con
   paquetes de `backend/requirements.txt` faltantes por nombre). Con
   varios problemas simulados a la vez, el reporte final lista **todos**,
   termina con exit code `1`, y cada línea de problema incluye una acción
   concreta (comando o instrucción) para resolverlo.
3. `scripts/preflight.ps1`, parado en `develop` con cambios sin
   commitear, reporta un problema `BLOCKING` mencionando explícitamente
   `develop` y "sin commitear", exit code `1`, y no intenta arreglarlo
   (no hace `git stash`/`git checkout` automático).
4. `scripts/preflight.ps1 -Slug <NN-slug>` evalúa y reporta correctamente,
   con severidad y acción recomendada, cada una de las filas de la matriz
   worktree/rama/ROADMAP definida en "Contexto" de esta spec, con al
   menos un test dedicado por cada fila marcada `BLOCKING` o `WARNING` en
   la tabla.
5. `scripts/preflight.ps1` nunca modifica el estado del repositorio: no
   commitea, no pushea (salvo `git fetch`, que es de solo lectura), no
   crea/borra ramas ni worktrees, en ninguno de los escenarios cubiertos
   por los tests. Verificable comparando `git rev-parse HEAD` y
   `git worktree list` antes/después de cada corrida de test.
6. `scripts/feature-contract.ps1` expone una función de reporte que
   evalúa el contrato completo de artefactos sin lanzar excepción en el
   primer faltante (devuelve la lista completa de artefactos
   presentes/ausentes). `Assert-FeatureContract` sigue lanzando excepción
   con el mismo comportamiento externo que hoy (los tests existentes en
   `tests/test_feature_contract_scripts.py`, en particular
   `test_ready_gate_fails_when_decision_or_index_link_is_missing`, siguen
   pasando sin modificar sus aserciones). Se agrega al menos un test nuevo
   que, con 2 o más artefactos faltantes simultáneamente (por ejemplo
   `decision.md` y el enlace en `docs/usuario/index.md`), verifica que el
   reporte no-throwing los liste todos.
7. `scripts/wait-pr-ci.ps1` admite `-Snapshot`: consulta el estado actual
   de la PR (`gh pr view` — número, URL, estado, `mergeStateStatus`) y el
   resumen de checks (`gh pr checks`, sin `--watch`) una sola vez, imprime
   ambos, y termina con exit code `0` sin importar si los checks están en
   verde, en rojo o pendientes (es una foto, no un gate). Si la PR no
   existe todavía para la rama, termina con exit code distinto de `0` y
   mensaje explícito ("no existe PR para `<ref>` todavía"). El modo actual
   sin `-Snapshot` (bloqueante, `--watch`) no cambia su comportamiento
   (test de regresión sobre el modo existente).
8. `scripts/start-local-reconciler.ps1`: la llamada que lanza el proceso
   en segundo plano especifica explícitamente arranque sin ventana visible
   (`ProcessStartupInformation.ShowWindow = 0` + `CreateFlags` con
   `CREATE_NO_WINDOW` = `0x08000000` sobre `Win32_Process.Create`, o
   `Start-Process -WindowStyle Hidden` si se reemplaza el mecanismo WMI).
   Los tests de comportamiento existentes en
   `tests/test_local_reconciler_scripts.py` (arranque, log, lock,
   deduplicación, limpieza, no-borrado si hay cambios sin commitear)
   siguen pasando sin modificar sus aserciones de negocio. **Verificación
   aceptada para este criterio puntual (decisión explícita, ver "Riesgos /
   supuestos"): alcanza con revisión estructural documentada en
   `docs/tecnica/cierre-operativo-circuito-agentico.md`** (cita textual o
   referencia al parámetro exacto del script que fija el arranque oculto),
   sin exigir un test automatizado ejecutable que falle si en el futuro se
   rompe esa configuración — no se agrega un test nuevo obligatorio solo
   para este punto.
9. `scripts/close-feature.ps1`: si el estado local es "already-closed"
   (`ROADMAP.md` local con `[x] <slug>`) pero `origin/<base>` todavía no
   contiene ese commit de cierre, el script pushea el commit pendiente
   antes de la verificación final, en vez de fallar directamente. Test
   dedicado: preparar un repo donde el commit de cierre existe localmente
   en `develop` pero no fue pusheado (simulando un corte de red tras el
   commit), correr `close-feature.ps1` de nuevo, y verificar que termina
   en exit code `0`, que `origin/develop:ROADMAP.md` queda con `[x]`, y
   que no se generó un commit duplicado (`git rev-list --count develop`
   no cambia respecto de antes de esta corrida). El comportamiento
   existente para "already-closed real" (remoto ya tiene el commit, ver
   `test_already_closed_feature_is_idempotent_and_does_not_create_empty_commit`)
   no cambia.
10. Debe existir `docs/tecnica/cierre-operativo-circuito-agentico.md`, no
    vacío, con: la matriz completa worktree/rama/ROADMAP (severidad +
    acción), los códigos de salida/mensajes de `preflight.ps1`, la tabla
    de interrupción/recuperación por paso del circuito, la decisión de
    diseño sobre ventana oculta del reconciliador, y la decisión de
    diseño que resuelve el conflicto entre la matriz `-Slug` y
    `ready-for-pr.ps1` (criterio 15 y "Riesgos / supuestos" de esta spec).
11. Debe existir `docs/usuario/cierre-operativo-circuito-agentico.md`, no
    vacío, con el propósito de `preflight.ps1` y al menos un ejemplo de
    uso por comando (equivalente al ejemplo HTTP request/response que
    exige `AGENTS.md` para features de endpoint — ver nota en "Riesgos /
    supuestos" sobre esta reinterpretación): un ejemplo de invocación sin
    `-Slug` con su salida esperada, y un ejemplo con `-Slug <NN-slug>`
    con su salida esperada (incluyendo al menos un caso `BLOCKING` de la
    matriz).
12. Debe existir `runs/03-cierre-operativo-circuito-agentico/decision.md`,
    generado de forma consistente con el resto del circuito (mismo patrón
    que `New-DecisionFile` en `scripts/feature-contract.ps1`).
13. Debe existir un enlace exacto a
    `docs/tecnica/cierre-operativo-circuito-agentico.md` en
    `docs/tecnica/index.md`, con el formato
    `- [<Título>](cierre-operativo-circuito-agentico.md)`.
14. Debe existir un enlace exacto a
    `docs/usuario/cierre-operativo-circuito-agentico.md` en
    `docs/usuario/index.md`, con el mismo `<Título>` exacto que en el
    punto 13 (ver "Riesgos / supuestos" sobre el título recomendado).
15. `scripts/ready-for-pr.ps1` invoca, **al inicio de su ejecución**
    (antes de cualquier verificación propia de rama/commits, y en
    particular antes de marcar `ROADMAP.md` como `[-]` o de pushear), la
    función compartida de **diagnóstico genérico de herramientas** de
    `preflight.ps1` — es decir, exclusivamente los chequeos de `git`,
    `gh` (binario + autenticación), PowerShell, Python y `.venv`
    descritos en los criterios 1-3 (modo **sin** `-Slug`) — y aborta con
    el mismo mensaje accionable que `preflight.ps1` reportaría si hay
    algún problema `BLOCKING` de herramientas.

    **`ready-for-pr.ps1` NO invoca sobre sí mismo la matriz
    worktree/rama/ROADMAP del modo `-Slug` (criterio 4).** Esa matriz
    depende de la existencia de la rama remota, que en el camino feliz de
    `ready-for-pr.ps1` todavía no existe entre el paso en que se marca
    `[-]` (líneas ~163-178 de la implementación actual) y el paso en que
    recién después se pushea (líneas ~182-183); insertar ahí el chequeo
    de la matriz produciría el conflicto identificado en la auditoría del
    intento 1 de esta spec — la matriz completa sigue disponible como
    diagnóstico standalone vía `preflight.ps1 -Slug <slug>`, corrido por
    separado (ver "Nota de alcance" en "Contexto" y "Riesgos /
    supuestos").

    Al reutilizar la función compartida, `ready-for-pr.ps1` deja de
    definir localmente `Get-GitHubCliPath`/`Get-PowerShellPath` y usa la
    misma implementación que `preflight.ps1`.

    Tests: (a) de regresión — los tests existentes de `ready-for-pr.ps1`
    en `tests/test_feature_contract_scripts.py` siguen pasando sin
    modificar sus aserciones de comportamiento actual (creación/reuso de
    PR, bloqueo por error real de `gh`); (b) nuevo — simular ausencia de
    `gh` (o `gh` presente sin autenticar) y verificar que
    `ready-for-pr.ps1` aborta **antes** de tocar `ROADMAP.md` (sin commit
    nuevo, `ROADMAP.md` sin cambios respecto del HEAD previo) con el
    mismo mensaje que reportaría `preflight.ps1` en modo genérico para
    ese problema.

## Casos borde a contemplar

- `gh` instalado pero con sesión expirada (token inválido): `gh auth
  status` retorna código de error distinto del caso "no logueado nunca";
  el mensaje debe distinguir ambos (o al menos no confundir "no
  instalado" con "no autenticado").
- Preflight corrido dentro de un worktree de feature (no el checkout
  principal): debe leer el `ROADMAP.md` del working tree actual, y
  también resolver correctamente `origin/develop:ROADMAP.md` para
  comparaciones remotas, sin mezclar ambos.
- `git fetch origin develop` falla por falta de red: `preflight.ps1` no
  debe crashear con traza cruda de PowerShell; debe reportar "no se pudo
  contactar a `origin`" como advertencia y seguir con los chequeos que no
  requieren red.
- `.venv` existe pero `python.exe` no arranca (entorno corrupto,
  permisos, etc.): debe reportarse como `BLOCKING` distinto del caso
  "`.venv` ausente".
- Slug con formato inválido pasado a `-Slug` (no cumple
  `^[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*$`): debe fallar con el mismo mensaje
  claro que ya produce `Get-FeatureInfo`, reutilizado sin duplicar la
  validación de formato.
- Dos features distintas con worktrees activos en simultáneo: el modo sin
  `-Slug` no debe reportar falsos positivos cruzados entre slugs (cada
  worktree se evalúa contra su propia entrada de `ROADMAP.md`).
- Reconciliador que terminó por timeout (`MaxMinutes` vencido) dejando
  `<slug>.err.log` con la excepción de timeout: `preflight.ps1` debe
  poder distinguir "terminó con error" de "nunca se lanzó" (lock ausente
  vs. lock ausente + log con contenido).
- Cierre remoto (`[x]` en `origin/develop`) ya ocurrido pero el
  reconciliador local nunca llegó a lanzarse (por ejemplo, porque
  `start-local-reconciler.ps1` cayó en su `catch` silencioso y solo
  emitió un `Write-Warning`): `preflight.ps1 -Slug` debe detectar este
  caso igual que el de "reconciliador murió", con el mismo mensaje de
  acción recomendada.
- Dos agentes corriendo `ready-for-pr.ps1`/reconciliador para la misma
  slug en paralelo: ya mitigado por el lock de PID existente;
  `preflight.ps1` debe reportarlo como informativo ("reconciliador activo,
  PID `<n>`"), no como error.
- `close-feature.ps1` reintentado múltiples veces seguidas tras la
  corrección del criterio 9: no debe generar más de un push adicional ni
  commits duplicados, sin importar cuántas veces se reintente.
- Ejecución en PowerShell 5.1 (`powershell.exe`) y en PowerShell 7
  (`pwsh`): todos los scripts nuevos/extendidos deben comportarse igual
  en ambos, igual que el resto del repo hoy.
- **Ejecutar `preflight.ps1 -Slug <slug>` en la brevísima ventana en que
  `ready-for-pr.ps1` ya marcó `[-]` pero todavía no terminó de pushear**
  (una corrida normal en curso, no interrumpida; la ventana dura lo que
  tarda un `git push`, típicamente sub-segundo a pocos segundos): la
  matriz puede reportar `BLOCKING` de forma transitoria y "correcta" según
  su propia definición, aun cuando `ready-for-pr.ps1` vaya a completar el
  push exitosamente enseguida. Se documenta como limitación aceptada de
  cualquier diagnóstico externo concurrente con un proceso en curso — no
  se resuelve con detección de proceso vivo (explícitamente fuera de
  alcance, ver "Alcance"). No es el mismo caso que una interrupción real
  (proceso muerto, ventana persistente indefinidamente): ese caso sí debe
  seguir siendo `BLOCKING` sin ambigüedad.

## Riesgos / supuestos

- **Decisión de diseño — `preflight.ps1` es de solo lectura.** Se decide
  que nunca mute el repo (ni siquiera para limpiar un worktree obviamente
  huérfano), delegando toda acción destructiva a los scripts ya
  existentes (`close-feature.ps1`, `start-local-reconciler.ps1`, o
  comandos `git` manuales que el propio reporte sugiere). Es la opción
  más segura y la más fácil de testear de forma determinística; si el
  reviewer prefiere que `preflight.ps1` pueda auto-reparar casos triviales
  (p. ej. `git worktree prune`), debe objetarlo explícitamente porque
  cambia el contrato de "solo diagnóstico".
- **Decisión de diseño — exit codes binarios.** `preflight.ps1` usa
  exit code `0` (sin problemas `BLOCKING`, puede haber `WARNING`) / `1`
  (al menos un problema `BLOCKING`), igual que el resto de los scripts
  del repo (que hoy son binarios throw/no-throw). Se evita inventar una
  tabla de códigos numéricos por tipo de error, para no romper la
  convención existente; la clasificación de severidad vive en el texto
  del reporte, no en el exit code.
- **Título exacto para los índices de documentación.** Se recomienda usar
  `"Cierre Operativo del Circuito Agéntico"` como `-Title` explícito,
  pasado consistentemente a `New-DecisionFile`, `update-doc-indexes.ps1`
  y `ready-for-pr.ps1` — el título que `Get-FeatureInfo` generaría por
  defecto a partir del slug sería `"Cierre Operativo Circuito Agentico"`
  (sin preposición ni tildes). Cualquiera de las dos formas es válida
  siempre que se use la **misma** de forma consistente en
  `runs/03-cierre-operativo-circuito-agentico/decision.md`,
  `docs/tecnica/index.md` y `docs/usuario/index.md`, porque
  `Assert-IndexLink` exige coincidencia exacta.
- **Reinterpretación del criterio "ejemplo de uso HTTP".** Esta feature no
  expone un endpoint HTTP; es tooling de circuito (scripts PowerShell). El
  criterio obligatorio de `docs/usuario/` se traduce a "ejemplo de
  invocación de comando + salida esperada" en lugar de request/response
  HTTP. Se deja explícito para que el reviewer lo objete si prefiere que
  de todos modos se documente algún equivalente HTTP (no existe: no hay
  API involucrada en esta feature).
- **Mecanismo de ventana oculta.** Se asume que basta con pasar
  parámetros explícitos de arranque oculto al mismo mecanismo WMI que ya
  usa `start-local-reconciler.ps1` (`Win32_Process.Create` +
  `Win32_ProcessStartup` con `ShowWindow`/`CreateFlags`), sin cambiar de
  mecanismo de lanzamiento de fondo. Si en la práctica esto no alcanza en
  el entorno real de ejecución, el builder puede reemplazarlo por
  `Start-Process -WindowStyle Hidden` apuntando a un wrapper, dejando la
  decisión técnica documentada en `decision.md` (no es un cambio de
  arquitectura del circuito, es un detalle de implementación de un script
  ya existente).
- **Verificación aceptada para "ventana oculta" (criterio 8): alcanza con
  revisión estructural documentada, no un test ejecutable.** Se decide
  explícitamente, en esta corrección de spec, que el criterio 8 **no**
  exige un test automatizado que falle si en el futuro alguien quita
  `ShowWindow`/`CreateFlags` de la llamada a `Win32_Process.Create` (o del
  mecanismo equivalente). Motivo verificado en el código: la suite
  `tests/test_local_reconciler_scripts.py` completa ya se salta en CI —
  aplica `pytestmark = pytest.mark.skipif(os.name != "nt" or
  shutil.which("powershell.exe") is None, ...)` (líneas 14-17 del archivo
  de test), y `.github/workflows/ci.yml` corre en `runs-on: ubuntu-latest`
  (línea 11), donde `os.name` es `"posix"`, no `"nt"` — por lo que un test
  ejecutable de este detalle puntual tampoco correría en CI hoy; exigirlo
  sería falso rigor. La revisión estructural documentada (cita del
  parámetro exacto en `docs/tecnica/cierre-operativo-circuito-agentico.md`)
  es la verificación real y proporcional dada esta limitación conocida del
  proyecto. Si en el futuro el proyecto agrega runners Windows al CI, este
  criterio debería revisarse para exigir el test ejecutable real en vez de
  la revisión documentada.
- **Alcance del gap de `close-feature.ps1`.** Se limita la corrección al
  caso concreto identificado (commit local sin push por interrupción de
  red), sin rediseñar el resto de la lógica de cierre, que ya está
  cubierta por tests de idempotencia (`tests/test_close_feature_script.py`)
  y no se toca.
- **No se propone cambiar motor OCR, `services.ini` ni la separación
  OCR/extracción/validación/storage** (`docs/tecnica/arquitectura.md`,
  ADR-006/ADR-007): esta feature no toca `backend/app/` ni
  `backend/config/`, es exclusivamente sobre `scripts/*.ps1` y su
  cobertura en `tests/`.
- **Resolución del conflicto entre el criterio 4 (matriz `-Slug`) y el
  criterio 15 (integración en `ready-for-pr.ps1`) — decisión explícita de
  esta corrección de spec.** El intento 1 de esta spec exigía que
  `ready-for-pr.ps1` reutilizara la matriz `-Slug` completa "antes de
  pushear/crear la PR", sin notar que el propio flujo de
  `ready-for-pr.ps1` marca `ROADMAP.md` como `[-]` (commiteado) **antes**
  de pushear, así que insertar la matriz en ese punto exacto habría hecho
  que la fila `[-]/sí/sí/no → BLOCKING` se disparara siempre, en el
  camino feliz de cualquier feature futura — un deadlock de diseño, no un
  caso borde, señalado como bloqueante por la auditoría del intento 1. Se
  evalúan las tres salidas que propuso la auditoría:
  - **(a)** correr el chequeo compartido antes de marcar `[-]` (mientras
    `ROADMAP.md` sigue en `[ ]`): resuelve la primera corrida, pero en
    reintentos donde `[-]` ya quedó marcado de una corrida previa
    interrumpida, el chequeo (si se sigue ejecutando al inicio del
    script) se encontraría con `ROADMAP.md` ya en `[-]` y rama remota
    todavía inexistente — el mismo problema, desplazado al caso de
    reintento en vez de resuelto.
  - **(b)** `ready-for-pr.ps1` reutiliza solo un subconjunto de
    `preflight.ps1` — el diagnóstico genérico de herramientas (`git`,
    `gh`, PowerShell, Python, `.venv`) —, excluyendo explícitamente la
    matriz `-Slug`, que depende de la rama remota.
  - **(c)** agregar a la matriz un estado nuevo, distinguible, para
    "`ready-for-pr.ps1` en curso, todavía no pusheó", separado del caso
    genuino de "push perdido" — requiere una señal adicional (por
    ejemplo, detectar si el proceso de `ready-for-pr.ps1` sigue vivo, o
    si el commit de `[-]` es el HEAD actual sin upstream configurado
    todavía) para diferenciar ambos casos de forma confiable.

  **Se elige la opción (b).** Es la que resuelve el problema para
  cualquier corrida (primera vez o reintento) sin necesitar detectar
  procesos vivos ni introducir un estado ambiguo nuevo en la matriz: el
  diagnóstico genérico de herramientas no depende en absoluto de la rama
  remota, así que puede correr en cualquier punto del flujo de
  `ready-for-pr.ps1` (se especifica al inicio, antes de tocar
  `ROADMAP.md`, para fallar lo más temprano posible si falta `gh`/`git`)
  sin generar falsos positivos. La matriz `-Slug` completa queda
  disponible igual que hoy, pero como comando standalone
  (`preflight.ps1 -Slug <slug>`) para diagnóstico externo — antes de
  iniciar una corrida, o después de confirmar que una corrida anterior
  realmente se interrumpió (proceso ya no vivo) —, no como gate interno
  de `ready-for-pr.ps1` sobre sí mismo. Se acepta como limitación menor
  la ventana transitoria descrita en "Casos borde a contemplar" (correr
  `preflight.ps1 -Slug` mientras `ready-for-pr.ps1` está genuinamente en
  curso, en el sub-segundo entre commit y push, puede reportar `BLOCKING`
  de forma transitoria) — no se resuelve con detección de proceso vivo,
  que queda explícitamente fuera de alcance. Si el reviewer prefiere la
  opción (c) pese al costo de detectar procesos vivos, debe objetarlo
  explícitamente en la siguiente auditoría.
- **Integración de `preflight.ps1` dentro de `ready-for-pr.ps1` (criterio
  15) — mecanismo de reutilización.** Se decide que `ready-for-pr.ps1`
  reutilice la función compartida de diagnóstico genérico de herramientas
  (dot-sourcing/función exportada, igual que ya hace con
  `feature-contract.ps1` vía `. (Join-Path $PSScriptRoot
  "feature-contract.ps1")`), no que ejecute `preflight.ps1` como proceso
  hijo separado, para evitar doble parseo de salida entre procesos. Si el
  reviewer prefiere invocación como subproceso en lugar de función
  compartida, es una objeción válida a resolver en el siguiente intento.
