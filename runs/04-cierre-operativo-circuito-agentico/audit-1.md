```yaml
status: rejected
attempt: 1
feedback:
  - "Conflicto lógico entre el criterio 4 (matriz worktree/rama/ROADMAP de preflight.ps1) y el criterio 15 (ready-for-pr.ps1 reutiliza esa misma matriz 'antes de pushear/crear la PR'): la fila `[-]/sí/sí/no → BLOCKING` de la matriz ('algo se hizo a mano o el push se perdió') se dispara exactamente en el estado normal en que hoy queda ready-for-pr.ps1 justo antes de pushear (ROADMAP ya marcado `[-]` localmente en la línea 174 de ready-for-pr.ps1, rama y worktree locales existentes, rama remota todavía inexistente porque el push (línea 183) todavía no corrió). Si el criterio 15 se implementa literalmente insertando el chequeo compartido de preflight -Slug en cualquier punto entre el paso 3 (marcar `[-]`) y el paso 5 (push) del flujo actual, **la primera ejecución de ready-for-pr.ps1 para cualquier feature futura abortaría siempre con BLOCKING**, con la acción sugerida de la propia matriz ('git push -u origin feature/<slug> y re-correr ready-for-pr.ps1') — pero pushear es justamente el trabajo que ready-for-pr.ps1 está a punto de hacer, generando un deadlock circular en el camino feliz del circuito, no solo en un caso borde. La spec debe resolver explícitamente uno de estos puntos antes de pasar a builder: (a) el chequeo compartido debe correr ANTES de marcar ROADMAP `[-]` (mientras sigue en `[ ]`, donde la matriz sí da OK/informativo independientemente de la rama remota), y aclarar qué pasa en reintentos donde ROADMAP ya quedó `[-]` de una corrida previa fallida; o (b) el subconjunto de chequeos que ready-for-pr.ps1 reutiliza de preflight.ps1 excluye explícitamente la fila de la matriz que depende de la existencia de la rama remota cuando el propio script todavía no pescó; o (c) la matriz necesita una fila/estado distinto para 'ready-for-pr.ps1 en curso, todavía no pusheó', distinguible del caso genuino de push perdido. Cualquiera de las tres es aceptable, pero la spec actual no elige ninguna y tal como está el criterio 15 es contradictorio con el criterio 4 tal como está descrito hoy."
  - "Inexactitud técnica menor en 'Contexto': la spec afirma que 'Get-GitHubCliPath/Get-PowerShellPath están duplicadas en ready-for-pr.ps1, wait-pr-ci.ps1 y close-feature.ps1'. Verificado en el código: `Get-GitHubCliPath` sí está duplicada de forma idéntica en las tres (ready-for-pr.ps1 L42-54, wait-pr-ci.ps1 L7-19, close-feature.ps1 L58-70), pero `Get-PowerShellPath` **solo existe en ready-for-pr.ps1** (L56-68); wait-pr-ci.ps1 y close-feature.ps1 no la tienen porque no lanzan procesos de PowerShell hijos. No es bloqueante por sí solo, pero corregir esta afirmación evita que el builder intente 'deduplicar' una función que no está duplicada donde la spec dice que está."
  - "Punto a confirmar (no bloqueante, pero merece decisión explícita del analyst en la próxima vuelta): el criterio 8 permite satisfacer la verificación de ventana oculta con 'test o revisión estructural documentada en docs/tecnica/...', es decir, acepta que no haya ningún test automatizado ejecutable que falle si alguien rompe `ShowWindow`/`CreateFlags` en el futuro. Dado que `tests/test_local_reconciler_scripts.py` ya se salta por completo en CI (`ubuntu-latest`, condición `os.name != 'nt'`), esto es consistente con la limitación real del proyecto, pero conviene que la spec lo diga explícitamente como decisión aceptada (ej. en 'Riesgos/supuestos') en vez de dejarlo ambiguo entre 'test' y 'revisión documentada', para que reviewer y QA no discutan en la siguiente vuelta si alcanza con la revisión estructural."
```

# Auditoría — 03-cierre-operativo-circuito-agentico (intento 1)

## Resumen

La spec es, en general, notablemente rigurosa: cubre con precisión el gap real de `close-feature.ps1` (verificado en el código: en el estado `already-closed` el script salta directo a la verificación remota sin reintentar el push — `scripts/close-feature.ps1` líneas 264-292), el gap real de `start-local-reconciler.ps1` (verificado: la llamada `Invoke-CimMethod -ClassName Win32_Process -MethodName Create` en líneas 74-82 no pasa `ShowWindow`/`CreateFlags`, por lo que la afirmación de la spec es exacta), y cita con exactitud nombres de funciones y tests existentes (`Assert-FeatureContract`, `New-DecisionFile`, `Get-ExistingPr`, `Assert-RoadmapCanClose`, `test_ready_gate_fails_when_decision_or_index_link_is_missing` en `tests/test_feature_contract_scripts.py`, `test_already_closed_feature_is_idempotent_and_does_not_create_empty_commit` en `tests/test_close_feature_script.py`). Los criterios de aceptación son en su mayoría verificables (exit codes concretos, mensajes esperados, tests de regresión nombrados), el alcance está delimitado con una sección "fuera de alcance" explícita y razonable, los casos borde son apropiados para el dominio de tooling de circuito (no aplica el checklist de OCR porque la feature no toca `backend/app/` ni `backend/config/`, y la spec lo declara explícitamente), y cumple el requisito no negociable de `AGENTS.md`: exige `docs/tecnica/cierre-operativo-circuito-agentico.md` (criterio 10), `docs/usuario/cierre-operativo-circuito-agentico.md` (criterio 11), `runs/03-cierre-operativo-circuito-agentico/decision.md` (criterio 12), y enlaces exactos en ambos índices (criterios 13-14).

También cubre de forma concreta y verificable el requisito explícito del usuario sobre ventanas de consola: el criterio 8 no es una mención de pasada, es un criterio de aceptación propio con implementación técnica sugerida (`ShowWindow = 0` + `CREATE_NO_WINDOW = 0x08000000`) y alcance correctamente acotado al único punto del circuito que hoy lanza un proceso en segundo plano (`start-local-reconciler.ps1`, confirmado en el código que no hay otro spawn de background en el resto de los scripts tocados por esta feature).

## Motivo de rechazo

Sin embargo, encontré una contradicción de diseño no resuelta entre el **criterio 4** (la matriz worktree/rama/ROADMAP que evalúa `preflight.ps1 -Slug`) y el **criterio 15** (que exige que `ready-for-pr.ps1` reutilice esa misma matriz compartida "antes de pushear/crear la PR"). Verificado en `scripts/ready-for-pr.ps1`:

- Línea 163-178: si el slug está pendiente, `ready-for-pr.ps1` **marca `ROADMAP.md` como `[-]` y commitea, ANTES de pushear**.
- Línea 182-183: recién después llega el `git push -u origin $currentBranch`.

Esto significa que, en el estado normal de la primera corrida de `ready-for-pr.ps1` para cualquier feature futura, justo antes del push existe exactamente el estado: ROADMAP local `[-]`, rama local existente, worktree existente, rama remota **inexistente** (porque nunca se pusheó). Ese estado coincide exactamente con la fila `BLOCKING` de la matriz del criterio 4: `[-] | sí | sí | no → BLOCKING`, cuya acción sugerida es "hacer `git push` y re-correr `ready-for-pr.ps1`" — pero pushear es justamente el paso que `ready-for-pr.ps1` está a punto de ejecutar. Si el criterio 15 se implementa insertando el chequeo compartido en cualquier punto entre "marcar `[-]`" y "pushear" (lectura natural de "antes de pushear/crear la PR"), **el camino feliz del circuito quedaría roto para toda feature futura**, no solo como caso borde.

La spec no resuelve esta ambigüedad. Debe elegir y declarar explícitamente una de estas salidas antes de que builder-agent implemente:
1. El chequeo compartido corre antes de marcar `ROADMAP.md` como `[-]` (mientras sigue `[ ]`, fila que la matriz sí resuelve como OK), y la spec aclara qué pasa en reintentos donde el `[-]` ya quedó marcado de una corrida anterior fallida.
2. `ready-for-pr.ps1` reutiliza solo un subconjunto de los chequeos de `preflight.ps1` (herramientas, `gh auth`, etc.), excluyendo explícitamente la fila de la matriz que depende de la existencia de rama remota cuando el propio script todavía no pescó.
3. La matriz agrega un estado distinto para "ready-for-pr.ps1 en curso, todavía no pusheó" que la distinga del caso genuino de "push perdido".

## Otros hallazgos (no bloqueantes, pero a corregir en la siguiente vuelta)

- Inexactitud menor en "Contexto": la spec dice que `Get-PowerShellPath` está duplicada en `ready-for-pr.ps1`, `wait-pr-ci.ps1` y `close-feature.ps1`. Verificado: solo existe en `ready-for-pr.ps1` (líneas 56-68); `wait-pr-ci.ps1` y `close-feature.ps1` no la tienen. `Get-GitHubCliPath` sí está duplicada en las tres, eso es correcto.
- El criterio 8 acepta "test o revisión estructural documentada" como verificación de la ventana oculta, sin exigir un test ejecutable. Dado que `tests/test_local_reconciler_scripts.py` ya se salta en CI (`ubuntu-latest`, `os.name != 'nt'`), esto es coherente con la limitación real del proyecto, pero conviene que quede declarado como decisión aceptada en "Riesgos/supuestos" en vez de dejar la ambigüedad "test o revisión documentada" abierta para discutir en QA.

## Archivos revisados

- `D:\proyectos\gi-ocr\AGENTS.md`
- `D:\proyectos\gi-ocr\ROADMAP.md`
- `D:\proyectos\gi-ocr\runs\03-cierre-operativo-circuito-agentico\spec.md`
- `D:\proyectos\gi-ocr\scripts\feature-contract.ps1`
- `D:\proyectos\gi-ocr\scripts\ready-for-pr.ps1`
- `D:\proyectos\gi-ocr\scripts\wait-pr-ci.ps1`
- `D:\proyectos\gi-ocr\scripts\start-local-reconciler.ps1`
- `D:\proyectos\gi-ocr\scripts\reconcile-local-feature.ps1`
- `D:\proyectos\gi-ocr\scripts\close-feature.ps1`
- `D:\proyectos\gi-ocr\tests\test_feature_contract_scripts.py`
- `D:\proyectos\gi-ocr\tests\test_local_reconciler_scripts.py`
- `D:\proyectos\gi-ocr\tests\test_close_feature_script.py`
- `D:\proyectos\gi-ocr\.github\workflows\ci.yml`
