# Decision: 03-cierre-operativo-circuito-agentico - Cierre Operativo del Circuito Agentico

## Estado

MERGE aprobado por evidencias del circuito agéntico.

## Evidencias revisadas

- `runs/03-cierre-operativo-circuito-agentico/spec.md`
- `runs/03-cierre-operativo-circuito-agentico/audit-1.md` (rejected, intento 1: conflicto criterio 4/15)
- `runs/03-cierre-operativo-circuito-agentico/audit-2.md` (approved, intento 2)
- `runs/03-cierre-operativo-circuito-agentico/test-report-N.md` (a generar por qa-agent)

## Decisiones demostrables

- Criterio 4/15: ready-for-pr.ps1 reutiliza EXCLUSIVAMENTE el diagnostico generico de herramientas de preflight.ps1 (Assert-ToolchainReady: git, gh binario+autenticacion, PowerShell, Python, .venv), nunca la matriz -Slug completa, tal como resolvio el spec aprobado (opcion b de audit-1.md) para evitar el deadlock detectado en el intento 1.
- Get-ToolchainDiagnostics solo evalua Python/.venv si existe backend/requirements.txt en la raiz del repositorio actual (Get-RepositoryRoot); si no existe, esos dos chequeos se omiten. Decision tecnica no explicitada en el spec: sin esto, los tests de regresion de ready-for-pr.ps1 (repos sinteticos sin backend/) romperian siempre con .venv BLOCKING, violando el criterio 15(a).
- Assert-ToolchainReady propaga el stderr crudo de gh auth status en el mensaje BLOCKING de gh (mismo patron que Get-ExistingPr), preservando test_ready_for_pr_blocks_real_gh_error sin modificar sus aserciones (nota no bloqueante de audit-2.md).
- preflight.ps1 es de solo lectura: nunca commitea, nunca pushea (salvo git fetch), nunca crea/borra ramas o worktrees; toda accion de recuperacion se delega a scripts existentes o comandos git manuales sugeridos en el propio reporte.
- start-local-reconciler.ps1 arranca el proceso en segundo plano con Win32_ProcessStartup.ShowWindow=0 (SW_HIDE) sobre el mismo mecanismo WMI existente (Win32_Process.Create), sin cambiar de mecanismo de lanzamiento. Decision tecnica no anticipada por el spec, descubierta durante la implementacion (ver bullet siguiente): NO se agrega CreateFlags=CREATE_NO_WINDOW (0x08000000) porque ese valor especifico rompe la llamada en este entorno (ReturnValue=21, Invalid Parameter); ShowWindow=0 solo ya cumple el objetivo del criterio 8.
- Bug real encontrado y corregido durante la implementacion (regresion detectada por tests, no en revision manual): la primera version de la ventana oculta usaba Invoke-CimMethod + New-CimInstance -ClientOnly (tal como sugeria el spec), que fallaba con "Los tipos no coinciden" (HRESULT 0x80041005) al pasar el objeto ProcessStartupInformation embebido en este entorno (Windows PowerShell 5.1) -- 6 de 7 tests de tests/test_local_reconciler_scripts.py fallaban porque el reconciliador nunca llegaba a arrancar. Se reemplazo por el wrapper WMI clasico ([wmiclass]"Win32_Process"/[wmiclass]"Win32_ProcessStartup".CreateInstance()), que si acepta el objeto embebido, sin cambiar el mecanismo de fondo (sigue siendo WMI/Win32_Process.Create). Ver docs/tecnica/cierre-operativo-circuito-agentico.md, seccion "Decision: ventana oculta del reconciliador", para el detalle completo incluida la evidencia empirica (ReturnValue por combinacion de parametros probada).
- close-feature.ps1: en el estado already-closed, reintenta git push origin <base> si origin/<base> todavia no tiene el commit de cierre, antes de la verificacion final, en vez de fallar directo.
- Bug real encontrado y corregido durante la implementacion: Assert-ToolchainReady no lanzaba excepcion cuando Get-ToolchainDiagnostics devolvia exactamente UN problema BLOCKING, porque `$blocking.Count` sobre un solo PSCustomObject (no array) evalua a `$null`, y `$null -gt 0` es `$false` en PowerShell; se corrigio forzando array con `@(...)`. Detectado con una repro manual contra un repo sintetico antes de confiar en la suite automatizada.
- ROADMAP.md no tenia ninguna entrada para el slug 03-cierre-operativo-circuito-agentico en el punto de partida de esta rama (heredado de develop); se agrego la entrada [ ] minima necesaria para que ready-for-pr.ps1/Assert-FeatureContract puedan operar, sin renumerar la entrada preexistente 03-empaquetado-despliegue. Ver seccion Nota sobre ROADMAP.md mas abajo.
- tests/test_preflight_script.py se gatea a Windows con powershell.exe (mismo patron que tests/test_local_reconciler_scripts.py, ya existente), porque construye repos git con multiples worktrees y compara rutas en formato Windows: se salta en CI (ubuntu-latest). El criterio 4 ("al menos un test dedicado por cada fila BLOCKING/WARNING") se cumple igual: la suite completa (8 filas BLOCKING/WARNING + casos OK + invariante de solo-lectura) corrio en verde localmente en Windows como parte de esta feature, documentado aca como evidencia, ya que no es visible en el log de CI.

## Nota sobre ROADMAP.md (señalado al humano, no una suposición grande resuelta en silencio)

Al empezar la implementación, `ROADMAP.md` (heredado de `develop` en el
punto de partida de esta rama) no tenía ninguna entrada para el slug
`03-cierre-operativo-circuito-agentico`: el backlog llegaba hasta
`03-empaquetado-despliegue`, y los slugs futuros que el spec aprobado ya
cita textualmente en "Explícitamente fuera de alcance"
(`10-calidad-ci-lint-formato`, `11-empaquetado-despliegue`,
`12-release-versionado-productivo`) tampoco existían todavía en el
backlog. Esto es una precondición de circuito faltante (una entrada de
`ROADMAP.md` que normalmente el humano agrega antes de que
`analyst-agent` escriba el spec), no una decisión de producto ni una
ambigüedad del spec en sí.

Acción tomada por `builder-agent`: se agregó la entrada `[ ]` mínima
necesaria en `ROADMAP.md` para que `ready-for-pr.ps1`/`Assert-FeatureContract`
puedan operar sobre esta feature (ver commit correspondiente), **sin**
renumerar ni tocar la entrada preexistente `03-empaquetado-despliegue`
(coincide en el prefijo `03`, pero son slugs distintos y ningún script
del circuito asume unicidad de `NN` entre slugs — solo unicidad de la
entrada exacta por slug completo, que sí se cumple). Queda señalado
explícitamente para que el humano decida si renumerar
`03-empaquetado-despliegue` (por ejemplo a `11-empaquetado-despliegue`,
como ya anticipa el spec) al revisar la PR.

## Resultado

La feature queda apta para integrarse/cerrarse cuando GitHub confirme merge contra `develop` y el cierre automatico marque `ROADMAP.md`.
