# Decision: 18-calidad-ci-supply-chain

## Estado

Implementación `builder-agent` lista para QA. No se marca `ROADMAP.md` y
no se crea PR en esta etapa.

## Evidencia De Entrada

- `runs/18-calidad-ci-supply-chain/spec.md`: exige agregar un job
  `quality` en `.github/workflows/ci.yml` (`ruff check`, `ruff format
  --check`, `mypy backend/app`, `pip-audit` gate sobre
  `backend/requirements.txt`, `pip-audit` informativo sobre
  `backend/requirements-dev.txt`), fijar (`==`) todas las dependencias
  directas de `backend/requirements.txt`, extender (no reemplazar)
  `backend/requirements-dev.txt` existente, crear `pyproject.toml` con
  `[tool.ruff]`/`[tool.mypy]` sin `[build-system]`, y documentación
  técnica/usuario.
- `runs/18-calidad-ci-supply-chain/audit-1.md` y `audit-2.md`: `rejected`
  en intento 1 (tres puntos: descripción imprecisa de
  `requirements-dev.txt`, falta de justificación de excluir ese árbol del
  gate de `pip-audit`, y falta de exigencia de revisión periódica de
  excepciones), `approved` en intento 2 tras resolver los tres puntos de
  forma verificable.

## Decisiones Tomadas

- **Herramientas**: `ruff` (lint + formato, reemplaza cualquier
  combinación previa de linter/formatter) + `mypy` (type-check
  permisivo) + `pip-audit` (auditoría de vulnerabilidades), las tres
  fijadas a versión exacta en `backend/requirements-dev.txt`
  (`ruff==0.16.4`, `mypy==2.3.1`, `pip-audit==2.10.1`), tal como exige el
  criterio 8.
- **Alcance de lint/type-check**: `ruff check`/`ruff format --check`
  cubren `backend/app`, `backend/tests`, `scripts`, `tests` (criterios
  2-3); `mypy` se limita a `backend/app` (criterio 4, alcance permisivo
  declarado en el spec: `ignore_missing_imports = true`,
  `disallow_untyped_defs = false`).
- **Reglas de `ruff` activas**: solo `E`/`F`/`W`/`I` (estilo, Pyflakes,
  whitespace, orden de imports) en esta primera iteración, sin `B`/`UP`/
  `C90`/`ANN`/`D`, para no forzar una reescritura masiva no pedida por el
  spec; queda declarado como mejora incremental futura en
  `docs/tecnica/calidad-ci-supply-chain.md`.
- **`per-file-ignores` de `E402`**: puntual y justificado en comentarios
  (`scripts/*.py` y los archivos de test que hacen
  `sys.path.insert()`/`importorskip()` previo a imports), no un `ignore`
  global.
- **`backend/requirements.txt` fijado a `==`**: se fijaron las 12
  dependencias directas del criterio 7 exactamente a las versiones que
  ya estaban instalables/resueltas en el entorno de desarrollo
  (`fastapi==0.141.1`, `uvicorn==0.52.4`, `python-multipart==0.0.32`,
  `pydantic==2.13.4`, `pydantic-settings==2.15.0`, `Pillow==12.3.0`,
  `numpy==2.5.2`, `opencv-python-headless==5.0.0.93`,
  `pypdfium2==5.13.0`, `easyocr==1.7.2`, `pytest==9.1.1`,
  `httpx==0.28.1`), sin tocar el pin/comentario ya existente de
  `rapidocr-onnxruntime==1.2.3`/`onnxruntime==1.28.0`. Se verificó
  instalando `backend/requirements-dev.txt` completo en un `.venv` nuevo
  (Python 3.14.7): las 12 versiones se resuelven e instalan sin
  conflicto.
- **`backend/requirements-dev.txt` extendido, no reemplazado**: conserva
  `-r requirements.txt` intacto, elimina `pytest>=8.0.0` y
  `httpx>=0.27.0` (redundantes, ya fijados vía `-r requirements.txt`),
  agrega `ruff`/`mypy`/`pip-audit` fijados, deja `playwright>=1.40.0` sin
  fijar (pertenece al scaffolding de la feature 17, aún `[ ]` pendiente
  en `ROADMAP.md`, verificado con grep).
- **`pyproject.toml` sin `[build-system]`**: solo configuración de
  tooling (`[tool.ruff]`, `[tool.mypy]`), el proyecto sigue usando pip +
  `requirements*.txt` como gestor de paquetes (criterio 9, ver
  `AGENTS.md`).
- **`extend-exclude = ["runs", "docs"]` agregado a `[tool.ruff]`**
  (decisión nueva de este intento, no estaba en el spec explícitamente):
  `ruff 0.16.4` formatea por defecto bloques de código Python embebidos
  en Markdown. Al correr `ruff format --check .` desde la raíz del repo
  (criterio 10), esto intentaba reformatear
  `runs/03-empaquetado-despliegue/test-report-1.md` — evidencia ya
  cerrada de otra feature, que ningún agente debe reescribir (ver
  `AGENTS.md`, "Ningún agente sobreescribe el artefacto de otro"). Se
  excluyó `runs/` (historial del circuito, no código de producción) y
  `docs/` (documentación de referencia, fuera del alcance de los
  criterios 2-3, que listan explícitamente `backend/app`,
  `backend/tests`, `scripts`, `tests`) para que el comando literal del
  criterio 10 (`ruff check .` / `ruff format --check .` desde la raíz)
  termine en código de salida 0 sin tocar artefactos fuera de alcance.
  No afecta el job `quality` de CI, que ya invocaba `ruff` con las rutas
  explícitas del criterio 2-3, no `.`.
- **Excepciones de `pip-audit`**: `backend/config/pip-audit-ignore.txt`
  se crea vacío de excepciones activas (ninguna vulnerabilidad conocida
  requirió excepción en este intento), pero con la política de revisión
  obligatoria en cada cambio de `backend/requirements.txt` documentada
  como texto explícito y verificable (criterio 5), replicada también en
  `docs/tecnica/calidad-ci-supply-chain.md`.
- **Paso informativo de `pip-audit` sobre `requirements-dev.txt`**:
  `continue-on-error: true` en el job `quality`, cubre `ruff`/`mypy`/
  `pip-audit` (fijados por esta feature) y `playwright` (sin fijar, de
  la feature 17), sin convertir esta feature en la que decide fijar o
  resolver hallazgos de una dependencia ajena (criterio 6).

## Verificación Real Ejecutada (no inventada)

- **`pytest -q` completo** (`backend/tests/` + `tests/`), corrido en el
  worktree (`D:\proyectos\worktrees\18-calidad-ci-supply-chain`) contra
  un `.venv` propio (Python 3.14.7) creado e instalado desde
  `backend/requirements-dev.txt` de esta rama: resultado real **`262
  passed, 6 skipped, 0 failed, 31 warnings in 485.33s`**. Los 6 `skip`
  son los esperados (Playwright no instalado como paquete de navegador
  real y muestras privadas locales gitignored), mismo patrón que
  features previas. Nota de entorno: la primera corrida sin
  `--basetemp` produjo 77 `ERROR` por `PermissionError: [WinError 5]
  Acceso denegado` sobre
  `C:\Users\jlbel\AppData\Local\Temp\pytest-of-jlbellon` — confirmado
  como limitación preexistente del entorno del equipo (no introducida
  por esta feature; el `decision.md` de `03-empaquetado-despliegue`
  documenta el mismo problema exacto). Se usó `--basetemp` apuntando a
  una carpeta de scratch propia para obtener la corrida real completa
  sin errores de entorno.
- **`ruff check backend/app backend/tests scripts tests`** → `All
  checks passed!` (criterio 2).
- **`ruff format --check backend/app backend/tests scripts tests`** →
  encontró 1 archivo sin formatear
  (`backend/app/main.py`, falta de línea en blanco antes de una función
  top-level). Se corrigió el archivo (cambio mínimo, sin tocar lógica) y
  se re-verificó: `65 files already formatted` (criterio 3).
- **`ruff check .` / `ruff format --check .`** desde la raíz (comando
  literal del criterio 10) → ambos en código de salida 0 tras agregar
  `extend-exclude` (ver "Decisiones Tomadas").
- **`mypy backend/app`** → `Success: no issues found in 24 source
  files` (criterio 4).
- **`pip-audit -r backend/requirements.txt`** → **no pudo ejecutarse
  contra el índice real de PyPI en este entorno de desarrollo**: falla
  con `ERROR:pip_audit._cli:Failed to upgrade pip` antes de resolver
  ninguna dependencia (bloqueo de red/TLS del entorno de desarrollo
  usado, mismo tipo de limitación de entorno que el daemon Docker
  detenido documentado en el `decision.md` de
  `03-empaquetado-despliegue`). Documentado explícitamente en
  `backend/config/pip-audit-ignore.txt` y en
  `docs/tecnica/calidad-ci-supply-chain.md`: el paso de CI en GitHub
  Actions (con acceso real a `pypi.org`) es la primera ejecución
  efectiva del gate y debe revisarse en el primer run de la PR de esta
  feature. No se afirma en ningún documento que el gate haya pasado con
  evidencia real local — criterio 5 queda parcialmente verificado
  (config correcta, ejecución real pendiente de CI).
- **`Assert-FeatureContract`** (`scripts/feature-contract.ps1`,
  `Get-FeatureContractStatus -Slug '18-calidad-ci-supply-chain' -Title
  'Calidad de CI y Supply Chain'`): ver detalle en "Contrato de
  feature".
- **`docs/tecnica/index.md` y `docs/usuario/index.md`**: enlace exacto
  `- [Calidad de CI y Supply Chain](calidad-ci-supply-chain.md)` ya
  presente en ambos (criterio 15).

## Riesgo Documentado, No Resuelto En Esta Feature

- El gate de `pip-audit` contra `backend/requirements.txt` no se pudo
  ejecutar con éxito contra el índice real de PyPI en este entorno de
  desarrollo (bloqueo de red/TLS). El `qa-agent` o el humano deben
  confirmar el primer resultado real en el CI de GitHub Actions de la
  PR de esta feature antes de dar por cerrado el criterio 5 con
  evidencia end-to-end.
- Las versiones fijadas en `backend/requirements.txt` (`fastapi`,
  `numpy`, `opencv-python-headless`, etc.) son saltos mayores respecto a
  los rangos abiertos previos (`>=`). Se verificó que instalan y que
  `pytest` pasa completo (262 passed) contra esas versiones exactas en
  este entorno, pero no se ejecutó una batería de regresión visual/OCR
  adicional más allá de la suite existente — mismo alcance que exige el
  criterio 11 (el job `pytest` original sigue pasando sin cambios de
  comportamiento).

## Alcance No Modificado

- No se reabrió ADR-006 (motor OCR) ni ADR-007 (config texto plano).
- No se tocó el `Dockerfile` de producción (Feature 03/ADR-009): sigue
  instalando únicamente `backend/requirements.txt`.
- No se fijó ni se resolvió ninguna vulnerabilidad de `playwright`
  (pertenece a la feature 17, aún `[ ]` pendiente).
- No se tocó `ROADMAP.md` más allá de lo que ya traía `develop`.
- No se hizo push ni se creó PR.

## Contrato de feature

Resultado real de `Get-FeatureContractStatus -Slug
'18-calidad-ci-supply-chain' -Title 'Calidad de CI y Supply Chain'`
(`scripts/feature-contract.ps1`), corrido desde el worktree: antes de
este documento, el único problema reportado era la ausencia de este
mismo `decision.md` y de un `test-report-N.md` (artefacto del
`qa-agent`, próxima etapa). El resto del contrato (`spec.md`,
`docs/tecnica/calidad-ci-supply-chain.md` y
`docs/usuario/calidad-ci-supply-chain.md` no vacíos, `audit-1.md` y
`audit-2.md`, enlaces exactos en ambos índices con el título "Calidad de
CI y Supply Chain") ya pasaba sin problemas.

## Artefactos

- `.github/workflows/ci.yml` (job `quality` nuevo)
- `pyproject.toml`
- `backend/requirements.txt` (versiones fijadas a `==`)
- `backend/requirements-dev.txt` (extendido)
- `backend/config/pip-audit-ignore.txt`
- `backend/app/main.py` (fix de formato, sin cambio de lógica)
- `docs/tecnica/calidad-ci-supply-chain.md`
- `docs/usuario/calidad-ci-supply-chain.md`
- `runs/18-calidad-ci-supply-chain/decision.md`
