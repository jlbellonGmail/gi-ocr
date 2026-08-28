```yaml
status: approved
attempt: 2
feedback:
  - "No bloqueante, a validar en implementación: el criterio 15(a) exige que `test_ready_for_pr_blocks_real_gh_error` (tests/test_feature_contract_scripts.py) siga pasando sin modificar sus aserciones, y esa aserción es literal (`\"auth failed\" in result.stderr`, el texto crudo que emite el fake `gh`). Con el nuevo diseño, ese error se va a detectar en el diagnóstico genérico de herramientas al inicio del script, no en `Get-ExistingPr` como hoy. El builder debe asegurarse de que el mensaje de aborto del diagnóstico compartido siga propagando el stderr crudo de `gh auth status` (patrón ya usado en `Get-ExistingPr`: `\"...: $($result.StdErr)\"`), o ese test de regresión se rompe. No es una ambigüedad de la spec — el criterio 15(a) ya obliga a este resultado — pero conviene que quede explícito para que QA no lo pase por alto."
```

# Auditoría — 03-cierre-operativo-circuito-agentico (intento 2)

## Resumen del intento anterior y qué se pidió corregir

`audit-1.md` rechazó el intento 1 por un conflicto de diseño bloqueante entre el criterio 4 (matriz worktree/rama/ROADMAP de `preflight.ps1 -Slug`) y el criterio 15 (integración de esa misma matriz en `ready-for-pr.ps1` "antes de pushear/crear la PR"), señalando que la fila `[-]/sí/sí/no → BLOCKING` se dispararía siempre en el camino feliz de cualquier feature futura, porque `ready-for-pr.ps1` marca `ROADMAP.md` como `[-]` (commiteado) antes de pushear. También señaló, como hallazgos no bloqueantes, una afirmación incorrecta sobre `Get-PowerShellPath` estar duplicada en tres scripts, y pidió declarar explícitamente si el criterio de "ventana oculta" exige test ejecutable o alcanza con revisión documentada.

## Verificación del punto bloqueante (conflicto criterio 4 vs criterio 15)

El intento 2 declara elegir la opción (b) de las tres propuestas por la auditoría anterior: `ready-for-pr.ps1` reutiliza únicamente el **diagnóstico genérico de herramientas** (`git`, `gh` binario+autenticación, PowerShell, Python, `.venv`), sin depender de la existencia de rama remota; la matriz completa `-Slug` queda como comando standalone.

Verificado en el código real:

- `scripts/ready-for-pr.ps1` líneas 163-178: marca `ROADMAP.md` `[-]` y commitea. Líneas 182-183: recién después pushea (`Write-Host "==> Pusheando..."` en 182, `git push -u origin $currentBranch` en 183). Coincide exactamente con las líneas que cita la spec (`~163-178`, `~182-183`).
- El diagnóstico genérico que la spec describe para el criterio 15 (git/gh/PowerShell/Python/.venv) no lee ni evalúa la existencia de la rama remota (`git ls-remote origin feature/<slug>`), que es justamente el dato que dispara la fila `BLOCKING` de la matriz del criterio 4. Por lo tanto, insertar ese diagnóstico genérico al inicio del script (antes de la línea 163) no puede reproducir el deadlock detectado en el intento 1: no hay ninguna dependencia lógica entre "¿está `gh` autenticado?" y "¿existe la rama remota?".
- El criterio 15 corregido es explícito y sin ambigüedad en que la matriz del criterio 4 **no** se ejecuta dentro de `ready-for-pr.ps1`: "`ready-for-pr.ps1` NO invoca sobre sí mismo la matriz worktree/rama/ROADMAP del modo `-Slug` (criterio 4)" (línea 318-319 del spec), reforzado por la "Nota de alcance" en la sección "Contexto" (líneas 173-192) y por el desarrollo completo de las tres opciones evaluadas en "Riesgos / supuestos" (líneas 474-522), donde se explica por qué (a) y (c) tienen costos mayores y por qué (b) es la elegida.
- La spec deja además evidencia de haber pensado el caso de reintento (que fue justamente la debilidad marcada contra la opción (a) en el propio spec): con la opción (b), el diagnóstico de herramientas no varía entre primera corrida y reintento, porque nunca depende del estado de la rama remota.
- Se documenta honestamente el único costo residual aceptado: la ventana transitoria sub-segundo en que correr `preflight.ps1 -Slug` en paralelo con una corrida en curso de `ready-for-pr.ps1` puede reportar `BLOCKING` de forma momentánea (ver "Casos borde a contemplar", líneas 388-399). Esto es un caso de uso concurrente explícitamente fuera de alcance (detección de proceso vivo), no el bug estructural del intento 1, y está correctamente separado del camino feliz.

Conclusión: el conflicto bloqueante del intento 1 está genuinamente resuelto, no solo declarado. La solución es lógicamente consistente con el código real y no introduce un nuevo deadlock ni dependencia oculta.

## Verificación de los dos hallazgos no bloqueantes del intento 1

**`Get-PowerShellPath`.** Verificado en el código: la función solo existe en `scripts/ready-for-pr.ps1` (líneas 56-68). No existe en `scripts/wait-pr-ci.ps1` (leído completo, 37 líneas, sin esa función) ni en `scripts/close-feature.ps1` (leído completo, 303 líneas, sin esa función). La corrección del spec en "Contexto" (líneas 99-107) ahora es exacta y coincide con la auditoría anterior. `Get-GitHubCliPath` sí sigue confirmada como duplicada idéntica en los tres scripts: `ready-for-pr.ps1` líneas 42-54, `wait-pr-ci.ps1` líneas 7-19, `close-feature.ps1` líneas 58-70 — las tres implementaciones son textualmente idénticas, confirmado leyendo los tres archivos completos.

**Ventana oculta — test vs. revisión documentada.** El intento 2 resuelve la ambigüedad de forma explícita en "Riesgos / supuestos" (líneas 446-463): decide que el criterio 8 no exige test automatizado ejecutable, y justifica la decisión citando el código real. Verificado: `tests/test_local_reconciler_scripts.py` líneas 14-17 tienen exactamente `pytestmark = pytest.mark.skipif(os.name != "nt" or shutil.which("powershell.exe") is None, ...)`, y `.github/workflows/ci.yml` línea 11 tiene exactamente `runs-on: ubuntu-latest`. La cita es precisa carácter por carácter con el código actual. El razonamiento ("un test ejecutable de este detalle puntual tampoco correría en CI hoy") es correcto dado que `os.name` en `ubuntu-latest` es `"posix"`.

## Revisión de cero del resto del spec

- **Contrato obligatorio de `AGENTS.md`:** criterios 10-14 exigen explícitamente `docs/tecnica/cierre-operativo-circuito-agentico.md` (no vacío, con contenido específico: matriz completa, códigos de salida, tabla de interrupción/recuperación, decisión de ventana oculta y decisión del conflicto criterio 4/15), `docs/usuario/cierre-operativo-circuito-agentico.md` (no vacío, con ejemplos de invocación y salida esperada, incluyendo un caso `BLOCKING`), `runs/03-cierre-operativo-circuito-agentico/decision.md` (con el patrón de `New-DecisionFile`), y enlaces exactos en ambos índices con el formato que exige `Assert-IndexLink`/`Update-DocsIndex` (verificado contra `scripts/feature-contract.ps1` líneas 107-141 y 143-188: el formato `- [<Título>](<target>.md)` que pide la spec coincide exactamente con lo que esas funciones validan). Cumple el requisito no negociable de `AGENTS.md`.
- **Criterios de aceptación verificables:** la gran mayoría tiene exit codes concretos, texto de mensaje esperado, o un test nombrado/descrito con pasos reproducibles (criterios 1, 2, 3, 6, 7, 9, 15 en particular). El criterio 4 exige "al menos un test dedicado por cada fila marcada BLOCKING o WARNING" — hay 4 filas BLOCKING y 4 WARNING en la matriz, por lo que el criterio se traduce en un mínimo de 8 tests concretos y contables, no una vaguedad.
- **Alcance:** delimitado con una lista "Explícitamente fuera de alcance" razonable (no cambia topología de agentes, no automatiza HITL, no reescribe scripts existentes desde cero, no agrega auto-arranque tras reinicio, no detecta procesos vivos en tiempo real, no toca OCR/`services.ini`, no toca empaquetado ni lint). Cada exclusión tiene una razón explícita, no es una lista genérica.
- **Casos borde:** cubren lo esperable del dominio de tooling de circuito (sesión de `gh` expirada vs. nunca logueada, preflight corrido dentro de un worktree de feature, falla de red en `git fetch`, `.venv` corrupto vs. ausente, slug con formato inválido, features concurrentes, reconciliador con timeout vs. nunca lanzado, cierre remoto sin reconciliador local, ejecución en PowerShell 5.1 y 7, y la ventana transitoria de concurrencia ya discutida). No aplica el checklist específico de OCR porque la feature no toca `backend/app/` ni `backend/config/`, y la spec lo declara explícitamente en "Fuera de alcance" — correcto.
- **Requisito explícito del usuario sobre ventanas de consola en background:** cubierto por el criterio 8 con mecanismo técnico concreto (`ShowWindow = 0` + `CREATE_NO_WINDOW = 0x08000000` sobre `Win32_Process.Create`, con alternativa `Start-Process -WindowStyle Hidden` documentada como fallback si el mecanismo no alcanza), acotado correctamente al único punto del circuito que lanza un proceso en segundo plano (`start-local-reconciler.ps1`; confirmado que no hay otro spawn de background en los scripts tocados por esta feature).
- **Supuestos del analyst razonables:** las decisiones de diseño en "Riesgos / supuestos" (preflight de solo lectura, exit codes binarios, título exacto para índices, reinterpretación de "ejemplo HTTP" para tooling sin API, mecanismo de ventana oculta, alcance del gap de `close-feature.ps1`) están todas justificadas con razones concretas y, en varios casos, invitan explícitamente al reviewer a objetar si no está de acuerdo — buena práctica que no encontré usada de forma evasiva.

## Hallazgo nuevo (no bloqueante)

Al revisar `tests/test_feature_contract_scripts.py` completo, noté que `test_ready_for_pr_blocks_real_gh_error` (líneas 247-253) asume literalmente que el mensaje de error de `ready-for-pr.ps1` incluye el texto crudo `"auth failed"` que emite el `gh` falso del test. Con el diseño del intento 2, ese chequeo de autenticación de `gh` pasa a ocurrir en el diagnóstico genérico compartido al inicio del script (criterio 15), en lugar de en `Get-ExistingPr` como ocurre hoy. El criterio 15(a) ya exige explícitamente que este test siga pasando sin modificar sus aserciones, así que la spec no tiene una laguna aquí — pero vale la pena señalarlo para que builder/QA no lo pasen por alto: el mensaje de aborto del diagnóstico compartido debe seguir propagando el `stderr` crudo de `gh auth status` (mismo patrón que ya usa `Get-ExistingPr`: `"Error real consultando PR existente con gh: $($result.StdErr)"`). No amerita rechazo porque el criterio ya obliga a este resultado; es una nota de implementación, no un defecto de spec.

## Conclusión

El intento 2 resolvió de forma genuina y verificable el conflicto bloqueante señalado en `audit-1.md`, con una elección de diseño (opción b) que es consistente con el código real y no reintroduce el deadlock ni ningún otro nuevo. Las dos correcciones no bloqueantes pedidas (precisión sobre `Get-PowerShellPath`, decisión explícita sobre el criterio de "ventana oculta") están hechas con precisión verificada línea por línea contra el código actual. El resto del spec, revisado de cero, es sólido: cumple el contrato obligatorio de `AGENTS.md`, tiene criterios de aceptación verificables, alcance acotado, casos borde apropiados para el dominio, y cubre el requisito explícito del usuario sobre ventanas de consola. Se aprueba.

## Archivos revisados

- `D:\proyectos\gi-ocr\AGENTS.md`
- `D:\proyectos\gi-ocr\ROADMAP.md`
- `D:\proyectos\gi-ocr\runs\03-cierre-operativo-circuito-agentico\audit-1.md`
- `D:\proyectos\gi-ocr\runs\03-cierre-operativo-circuito-agentico\spec.md`
- `D:\proyectos\gi-ocr\scripts\ready-for-pr.ps1`
- `D:\proyectos\gi-ocr\scripts\wait-pr-ci.ps1`
- `D:\proyectos\gi-ocr\scripts\close-feature.ps1`
- `D:\proyectos\gi-ocr\scripts\start-local-reconciler.ps1`
- `D:\proyectos\gi-ocr\scripts\feature-contract.ps1`
- `D:\proyectos\gi-ocr\tests\test_feature_contract_scripts.py`
- `D:\proyectos\gi-ocr\tests\test_local_reconciler_scripts.py`
- `D:\proyectos\gi-ocr\.github\workflows\ci.yml`
