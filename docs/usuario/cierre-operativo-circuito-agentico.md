# Cierre Operativo del Circuito Agéntico

## Para qué sirve

Un solo comando (`scripts/preflight.ps1`) responde a la pregunta "¿está
este repositorio listo para arrancar o retomar una feature del circuito
de `AGENTS.md`, o hay algo roto?", sin tener que inspeccionar a mano
`git status`, `git worktree list`, `git branch`, `ROADMAP.md` y
`gh auth status` en varios pasos.

Es de **solo lectura**: nunca commitea, nunca pushea (salvo
`git fetch`, de solo lectura), nunca crea ni borra ramas o worktrees. Si
detecta un problema, te dice qué comando correr para resolverlo — no lo
resuelve por vos.

Además, esta feature agrega tres mejoras puntuales al resto del tooling
del circuito:

- `scripts/wait-pr-ci.ps1 -Snapshot`: una foto rápida y no bloqueante del
  estado de PR/CI, en vez de tener que esperar bloqueado a que termine
  `--watch`.
- `scripts/start-local-reconciler.ps1`: el reconciliador local ya no deja
  una ventana de consola visible corriendo en segundo plano.
- `scripts/close-feature.ps1`: si un corte de red interrumpe el cierre
  justo después de commitear pero antes de pushear, una simple
  reejecución resuelve el push pendiente en vez de fallar en loop.

## Cómo se usa

### `preflight.ps1` sin `-Slug` (diagnóstico general del repositorio)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/preflight.ps1
```

**Salida esperada en un repositorio sano** (git/gh/PowerShell/Python OK,
`.venv` con las dependencias de `backend/requirements.txt`, `develop`
limpia y sincronizada con `origin/develop`):

```
==> Diagnostico generico de herramientas
[OK] git disponible en C:\Program Files\Git\mingw64\bin\git.exe.
[OK] gh disponible en C:\Program Files\GitHub CLI\gh.exe y autenticado.
[OK] PowerShell disponible en C:\...\pwsh.exe.
[OK] python 3.12 disponible en C:\...\python.exe.
[OK] .venv contiene los paquetes declarados en backend/requirements.txt.

==> Estado de 'develop'
[OK] 'develop' esta limpio en D:\proyectos\gi-ocr.
[OK] 'develop' esta sincronizado con origin/develop.

PREFLIGHT: OK (0 advertencia(s))
```

Exit code `0`.

**Salida esperada con problemas** (por ejemplo, `gh` no autenticado y
`.venv` desactualizado):

```
==> Diagnostico generico de herramientas
[OK] git disponible en C:\Program Files\Git\mingw64\bin\git.exe.
[BLOCKING] gh esta instalado (...) pero no esta autenticado (o la sesion expiro): ... Accion: Corre 'gh auth login' (o 'gh auth refresh' si la sesion expiro) para autenticar GitHub CLI.
[OK] PowerShell disponible en C:\...\pwsh.exe.
[OK] python 3.12 disponible en C:\...\python.exe.
[BLOCKING] .venv existe pero faltan paquetes de backend/requirements.txt: fastapi, pytest. Accion: Instala las dependencias: .venv/Scripts/pip install -r backend/requirements.txt

==> Estado de 'develop'
[OK] 'develop' esta limpio en D:\proyectos\gi-ocr.
[OK] 'develop' esta sincronizado con origin/develop.

PREFLIGHT: BLOCKING (2 problema(s) bloqueante(s), 0 advertencia(s))
```

Exit code `1`. Cada línea `[BLOCKING]` trae su `Accion:` — el comando o
instrucción concreta para resolverlo. `preflight.ps1` **no** corre esos
comandos por vos.

### `preflight.ps1 -Slug <NN-slug>` (diagnóstico de una feature puntual)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/preflight.ps1 -Slug 03-cierre-operativo-circuito-agentico
```

Corre todo lo del modo general, y además evalúa la matriz
worktree/rama/`ROADMAP.md` de esa feature puntual, el contrato de
artefactos (spec/audit/test-report/docs/decision/índices), y el estado
del reconciliador local si corresponde.

**Ejemplo — feature en camino a PR/CI, todo normal:**

```
==> Matriz worktree/rama/ROADMAP para '03-cierre-operativo-circuito-agentico'
[OK] '03-cierre-operativo-circuito-agentico' en camino a PR/CI: rama y worktree locales, rama remota presente.
[OK] PR #7 (https://github.com/.../pull/7): estado OPEN, mergeStateStatus CLEAN. Detalle de checks: scripts/wait-pr-ci.ps1 -Snapshot -PrRef feature/03-cierre-operativo-circuito-agentico

==> Contrato de artefactos para '03-cierre-operativo-circuito-agentico' (docs/decision/indices)
[OK] El contrato de artefactos de '03-cierre-operativo-circuito-agentico' esta completo (spec, audit, test-report, docs, decision, indices).

PREFLIGHT: OK (0 advertencia(s))
```

**Ejemplo con un caso `BLOCKING`** — `ROADMAP.md` marca la feature como
`READY_FOR_PR` (`[-]`) pero la rama remota no existe (por ejemplo, un
`ready-for-pr.ps1` que se interrumpió antes de terminar el push, o algo
que se hizo a mano):

```
==> Matriz worktree/rama/ROADMAP para '03-cierre-operativo-circuito-agentico'
[BLOCKING] '03-cierre-operativo-circuito-agentico' esta en READY_FOR_PR ([-]) pero no existe la rama remota 'feature/03-cierre-operativo-circuito-agentico'. ready-for-pr.ps1 exige push antes de marcar [-]; algo se hizo a mano o el push se perdio. Accion: Corre: git push -u origin feature/03-cierre-operativo-circuito-agentico ; luego re-corre: powershell -File scripts/ready-for-pr.ps1 03-cierre-operativo-circuito-agentico (es idempotente: no repite el commit de [-], solo reintenta push/PR).

PREFLIGHT: BLOCKING (1 problema(s) bloqueante(s), 0 advertencia(s))
```

Exit code `1`. La acción sugerida es directamente ejecutable: pushear y
volver a correr `ready-for-pr.ps1` (que no repite el commit, solo
reintenta push/PR).

**Nota importante:** `ready-for-pr.ps1` **no** corre esta matriz completa
sobre sí mismo durante su propia ejecución (solo reutiliza el diagnóstico
genérico de herramientas de arriba, al inicio, antes de tocar
`ROADMAP.md`). Correr `preflight.ps1 -Slug <slug>` es un diagnóstico
aparte, pensado para antes de arrancar una corrida de `ready-for-pr.ps1`
o después de confirmar que una corrida anterior se interrumpió de verdad
(ver `docs/tecnica/cierre-operativo-circuito-agentico.md` para el
detalle de esta decisión de diseño).

### `wait-pr-ci.ps1 -Snapshot` (foto no bloqueante de PR/CI)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/wait-pr-ci.ps1 -Snapshot -PrRef feature/03-cierre-operativo-circuito-agentico
```

Salida esperada (PR existente, checks en curso):

```
==> Consultando snapshot de PR/CI para 'feature/03-cierre-operativo-circuito-agentico' (no bloqueante)...
==> PR #7: https://github.com/.../pull/7
==> Estado: OPEN | mergeStateStatus: CLEAN
==> Checks (snapshot, sin --watch):
ci    pending    0s
```

Exit code `0` siempre que la PR exista, sin importar el color de los
checks (es una foto, no un gate). Si todavía no existe PR para esa rama,
termina con exit code distinto de `0` y el mensaje "No existe PR para
'`<ref>`' todavia".

### `start-local-reconciler.ps1` y `close-feature.ps1`

No cambian su forma de uso (siguen invocándose igual que antes, ver
`scripts/ready-for-pr.ps1` y `.github/workflows/post-merge-close-feature.yml`).
La diferencia observable es: el reconciliador ya no deja una consola
visible corriendo en segundo plano, y `close-feature.ps1` ya no se queda
atascado si el commit de cierre quedó hecho localmente pero el push se
cortó por una falla de red — una segunda corrida lo resuelve sola.
