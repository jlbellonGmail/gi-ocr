```yaml
status: approved
attempt: 1
feedback:
  - Todos los criterios de aceptación verificados de forma independiente con comandos reales (ver evidencia abajo). No se detectaron fallos.
  - pip-audit contra backend/requirements.txt y requirements-dev.txt no pudo ejecutarse contra el índice real de PyPI en este entorno (mismo bloqueo de red/TLS ya documentado por el builder en backend/config/pip-audit-ignore.txt y docs/tecnica/calidad-ci-supply-chain.md). Reproducido de forma independiente, no es un fallo de la implementación. Queda pendiente confirmar el primer resultado real en el job `quality` de CI (GitHub Actions) antes de dar el criterio 5 por cerrado con evidencia end-to-end — ya señalado también por el builder en decision.md, sección "Riesgo Documentado, No Resuelto En Esta Feature".
```

# Test Report 1: 18-calidad-ci-supply-chain

QA independiente de la implementación del builder (commit `ec7262d`),
worktree `D:\proyectos\worktrees\18-calidad-ci-supply-chain`, rama
`feature/18-calidad-ci-supply-chain`.

## 1. Suite completa de pytest

Comando corrido (usando `.venv` del worktree, con `--basetemp` propio
para evitar el `PermissionError` conocido del `TEMP` por defecto de
Windows en este equipo — mismo problema documentado en el `decision.md`
de `03-empaquetado-despliegue` y en el de esta misma feature):

```
.venv/Scripts/python.exe -m pytest -v --basetemp=<scratch>/pytest-basetemp
```

Resultado real (no asumido del reporte del builder, corrido de nuevo por
QA):

```
262 passed, 6 skipped, 31 warnings in 487.33s (0:08:07)
```

Los 6 `skip` son los esperados y ya documentados: Playwright no instalado
como paquete de navegador real (`tests/e2e/test_e2e_playwright.py`) y
muestras privadas locales gitignored
(`backend/tests/test_api_jobs.py`, `backend/tests/test_local_samples_real.py`
x4). 0 fallos. Cumple criterio 11: el job `pytest` original sigue pasando
sin cambios de comportamiento.

## 2. Criterios 1, 5, 6 — job `quality` en CI

Inspección de `.github/workflows/ci.yml`: el job `test` (pytest) queda
intacto sin modificaciones de comportamiento. Se agregó un job `quality`
independiente con 6 pasos: instalar `backend/requirements-dev.txt`,
`ruff check backend/app backend/tests scripts tests`, `ruff format
--check backend/app backend/tests scripts tests`, `mypy backend/app`,
`pip-audit` gate contra `backend/requirements.txt` (lee excepciones
de `backend/config/pip-audit-ignore.txt` línea por línea, ignorando
comentarios/líneas vacías, y las pasa como `--ignore-vuln <ID>`), y
`pip-audit` informativo contra `backend/requirements-dev.txt` con
`continue-on-error: true`. Los primeros cuatro son gate (fallan el job);
el quinto no. Cumple criterios 1, 5, 6.

## 3. Criterios 2/3 — ruff sobre las rutas del spec

```
.venv/Scripts/ruff.exe check backend/app backend/tests scripts tests
→ All checks passed!  (exit 0)

.venv/Scripts/ruff.exe format --check backend/app backend/tests scripts tests
→ 65 files already formatted  (exit 0)
```

## 4. Criterio 4 — mypy sobre backend/app

```
.venv/Scripts/mypy.exe backend/app
→ Success: no issues found in 24 source files  (exit 0)
```

## 5. Criterio 10 — comandos literales desde la raíz del worktree

```
.venv/Scripts/ruff.exe check .          → All checks passed!  (exit 0)
.venv/Scripts/ruff.exe format --check . → 90 files already formatted  (exit 0)
```

Confirmado con `git status --short` inmediatamente después: sin cambios,
ningún archivo bajo `runs/` ni `docs/` fue tocado/reescrito por `ruff
format --check .` — el `extend-exclude = ["runs", "docs"]` en
`pyproject.toml` funciona como documenta el builder (evita reescribir
`runs/03-empaquetado-despliegue/test-report-1.md`, evidencia de otra
feature ya cerrada).

`pip-audit -r backend/requirements.txt` y
`pip-audit -r backend/requirements-dev.txt` (equivalente local del
criterio 10 para el paso informativo): reproducido el mismo error de
entorno documentado por el builder —
`ERROR:pip_audit._cli:Failed to upgrade pip` (bloqueo de red/TLS del
entorno de desarrollo, no error de configuración). No se trata como
bloqueante, según lo acordado en el contexto de esta tarea y lo ya
documentado en `backend/config/pip-audit-ignore.txt` y
`docs/tecnica/calidad-ci-supply-chain.md`.

## 6. Criterios 7/8 — contenido de requirements.txt y requirements-dev.txt

`backend/requirements.txt`: las 12 dependencias directas exigidas por el
criterio 7 (`fastapi`, `uvicorn`, `python-multipart`, `pydantic`,
`pydantic-settings`, `Pillow`, `numpy`, `opencv-python-headless`,
`pypdfium2`, `easyocr`, `pytest`, `httpx`) están fijadas con `==`. El pin
y comentario de `rapidocr-onnxruntime==1.2.3` / `onnxruntime==1.28.0`
quedan intactos.

`backend/requirements-dev.txt`: conserva `-r requirements.txt` sin
modificar; **no** contiene `pytest>=8.0.0` ni `httpx>=0.27.0` (eliminadas
por redundantes); agrega `ruff==0.16.4`, `mypy==2.3.1`,
`pip-audit==2.10.1` fijados; deja `playwright>=1.40.0` intacta sin fijar.
Cumple exactamente el contenido exigido por el criterio 8.

`Dockerfile`: sigue instalando únicamente `backend/requirements.txt`
(`COPY backend/requirements.txt ...`, filtra `easyocr` para la imagen,
sin referencia a `requirements-dev.txt`). Sin diff respecto al commit
previo a esta feature (`git diff --stat b99c28a ec7262d -- Dockerfile`
sin salida).

## 7. Criterio 9 — pyproject.toml

Contiene `[tool.ruff]` y `[tool.mypy]`. Sin sección `[build-system]`
(`grep -n "build-system" pyproject.toml` solo encuentra la mención en un
comentario explicativo, no una sección real).

## 8. Criterios 12/13/15 — documentación e índices

- `docs/tecnica/calidad-ci-supply-chain.md`: 333 líneas, no vacío. Cubre
  qué corre cada paso de CI, reglas de `ruff` activas (`E`, `F`, `W`,
  `I`) y su justificación, exclusiones (`per-file-ignores` de `E402`
  documentadas), estrategia de fijado de versiones, política de
  excepciones de `pip-audit` (incluye la frase de revisión obligatoria en
  cada cambio de `requirements.txt`, verificado con grep), y tratamiento
  de `requirements-dev.txt`.
- `docs/usuario/calidad-ci-supply-chain.md`: 134 líneas, no vacío.
  Explica el propósito para quien mantiene el repo y da los 5 comandos
  exactos (`pip install -r backend/requirements-dev.txt`, `ruff check`,
  `ruff format --check`, `mypy backend/app`, `pip-audit -r
  backend/requirements.txt`, `pip-audit -r backend/requirements-dev.txt`)
  con la salida esperada de éxito de cada uno, más una nota de entorno
  sobre bloqueo de red para `pip-audit` que coincide con lo reproducido
  por QA en la sección 5 de este reporte.
- Enlaces exactos verificados: `docs/tecnica/index.md:14` y
  `docs/usuario/index.md:12` contienen
  `- [Calidad de CI y Supply Chain](calidad-ci-supply-chain.md)`.

## 9. Criterio 14 — decision.md

`runs/18-calidad-ci-supply-chain/decision.md`, 200 líneas, no vacío.
Contiene decisiones demostrables (herramientas elegidas, alcance de
`mypy`, reglas de `ruff`, tratamiento de `requirements-dev.txt`,
decisión no prevista en el spec de agregar `extend-exclude` con su
justificación completa, riesgo documentado de `pip-audit` sin ejecutar
localmente) y evidencia de verificación real ejecutada, incluyendo
`Get-FeatureContractStatus`. Revisado críticamente: no es ornamental, cada
afirmación tiene comando/resultado real citado.

## 10. Contrato común (`scripts/feature-contract.ps1`)

```
Get-FeatureContractStatus -Slug '18-calidad-ci-supply-chain' -Title 'Calidad de CI y Supply Chain'

Problems   : {Falta al menos un test-report-N.md en runs/18-calidad-ci-supply-chain.}
IsComplete : False
```

Único faltante: este mismo `test-report-1.md`, que QA produce ahora. El
resto del contrato (`spec.md`, `docs/tecnica/...`, `docs/usuario/...`,
`decision.md`, enlaces exactos en ambos índices) ya pasaba.

## Veredicto

`approved`. Los 15 criterios de aceptación del spec fueron verificados de
forma independiente con comandos reales (no reutilizando ciegamente lo
reportado por el builder): suite `pytest` completa (262 passed, 6
skipped, 0 failed), `ruff check`/`ruff format --check` en ambas
invocaciones (rutas del spec y `.` desde la raíz), `mypy backend/app`,
contenido exacto de `requirements.txt`/`requirements-dev.txt`,
`pyproject.toml` sin `[build-system]`, documentación técnica/usuario no
vacía con el contenido pedido, enlaces exactos en ambos índices,
`decision.md` con decisiones demostrables, y contrato común con el único
faltante esperado (este reporte). La única limitación encontrada
(`pip-audit` sin acceso real a PyPI en este entorno) es una limitación de
entorno ya documentada por el builder y reproducida de forma idéntica por
QA, no un defecto de la implementación; queda como verificación pendiente
en el primer run real de CI, tal como ya señala el propio `decision.md`
del builder.
