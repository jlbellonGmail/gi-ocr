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

## Sincronización Post-Aprobación De QA Con `develop` (2026-08-21)

### Motivo

Después de que QA aprobó la implementación (`test-report-1.md`, commit
`63ca062`) y se creó la PR #10 hacia `develop`, se detectó que la rama
`feature/18-calidad-ci-supply-chain` estaba basada en un punto de
`develop` ~20 commits atrás, sin las features `03-empaquetado-despliegue`,
`05-correccion-orientacion-exif`, `14-seguridad-privacidad-documentos` y
`16-administracion-servicios-documentos`, ya mergeadas. La PR quedó con
`mergeable_state: dirty` (conflictos reales) y CI nunca corrió sobre una
versión mergeable. Esta sección documenta el merge de sincronización que
resuelve eso, sin reimplementar la feature.

### Conflictos Encontrados Y Resolución

- **`ROADMAP.md`**: conflicto trivial de una línea en blanco al final del
  archivo (ambas ramas tocaron el mismo punto de EOF por separado); todas
  las entradas de features (`03`, `05`, `14`, `16`, `18`) ya convivían sin
  conflicto real en el resto del archivo. Se resolvió tomando el contenido
  sin la línea en blanco duplicada. El estado `[-] 18-calidad-ci-supply-chain`
  se preservó intacto; no se tocó el estado de ninguna otra feature.
- **`backend/app/image_prep.py`**: HEAD (feature 18) agregaba
  `from __future__ import annotations`; `develop` (feature 05) agregaba
  `from typing import Optional, Tuple` para el nuevo
  `apply_exif_orientation() -> Tuple[Image.Image, bool]`. Se verificó que
  `Optional` no se usa en ningún lugar del archivo (ni en esta rama ni en
  `develop`) — import muerto ya presente en `develop`. Resolución: se
  combinaron ambos imports (`from __future__ import annotations` +
  `from typing import Tuple`, sin `Optional`), preservando la lógica real
  de `apply_exif_orientation`/`correct_orientation`/`deskew`/
  `correct_perspective` tal como vienen de `develop`, sin revertir nada.
- **`backend/app/main.py`**: dos bloques de imports en conflicto. (1) HEAD
  agregaba `shutil`/`tempfile`/`datetime` (usados por código previo a
  feature 18 que en esta rama seguía existiendo) y `develop` agregaba
  `re` (para código de la feature 14); se verificó con grep sobre el
  archivo resultante que **ninguno** de los cinco (`shutil`, `tempfile`,
  `re`, `datetime`, y también `Any`/`Dict`/`SUPPORTED`/`timezone` del
  segundo bloque) se usa realmente en el `main.py` de `develop` post
  features 14/16 — son imports muertos que la feature 18 ya venía
  identificando y limpiando como parte de su alcance declarado ("Aplica
  fixes de lint/formato al codigo existente: imports no usados, orden de
  imports, espaciado, sin cambiar logica ni aserciones de test"). Se
  eliminaron todos. (2) HEAD tenía solo
  `from .inbound_watcher import InboundWatcher`; `develop` agregaba
  además `from .document_services import normalize_service_id`,
  `from .exif_privacy import anonymize_upload_bytes`,
  `from .fs_permissions import secure_dir, secure_file`, y
  `SUPPORTED` junto a `InboundWatcher`. Se verificó uso real de cada
  símbolo: `normalize_service_id`, `anonymize_upload_bytes`,
  `secure_dir`, `secure_file` sí se usan (feature 14/16, preservados tal
  cual); `SUPPORTED` no se usa en ningún punto del archivo — se omitió
  igual que el resto de imports muertos. El refactor propio de feature 18
  en este archivo (`_on_new_inbound` como función nombrada en vez de
  lambda inline, chequeo `doc is None` en `download_confirmed`) se
  preservó sin cambios, integrado sobre la base funcional de `develop`
  (endpoints de servicios, upload seguro, EXIF, etc.).
- **`backend/app/services_config.py`**: conflicto puramente aditivo.
  Feature 18 no había tocado nada después de `get_service_config()`;
  `develop` (feature 16) agregó ahí toda la validación de esquema formal
  (`_iter_field_block_names`, `_validate_field_block`,
  `_validate_section_schema`, `validate_services_schema`,
  `_find_section_case_insensitive`, `_build_service_schema`,
  `list_services_schema`, `get_service_schema`). Se tomó el bloque
  completo de `develop` sin modificaciones.
- **`docs/tecnica/index.md` y `docs/usuario/index.md`**: conflicto de
  listas de enlaces — HEAD solo tenía la entrada de esta feature 18;
  `develop` tenía las de `05`/`14`/`16`. Se combinaron ambos conjuntos de
  entradas (orden: primero las de `develop` en el orden que ya traían,
  después la de `18` al final), sin duplicados y sin perder ninguna.

### Limpieza De Lint/Tipos Adicional Requerida Por El Merge

El código traído por `develop` (features 05/14/16) nunca había pasado por
el gate de `ruff`/`mypy` porque ese gate no existía todavía cuando esas
features se mergearon. Al integrarlo en esta rama (que sí trae el gate),
aparecieron los siguientes hallazgos — todos fixes mecánicos de
lint/formato/tipos, sin cambiar lógica ni aserciones de test, mismo
criterio que ya aplicaba el commit original de esta feature:

- `ruff check` (7 errores): `typing.Iterable` sin usar en
  `backend/app/retention.py`; una línea de 133 caracteres (>120) en
  `backend/app/upload_validation.py`; 5 archivos de test
  (`test_upload_security.py`, `test_exif_orientation.py`,
  `test_exif_privacy.py`, `test_services_admin_api.py`,
  `test_services_config_schema.py`) con bloques de import
  desordenados (`I001`). Se corrigieron con `ruff check --fix` (6 de
  7 automáticos) y edición manual de la línea larga (se partió el
  f-string en dos literales concatenados, mismo mensaje de error final).
- `ruff format --check` (13 archivos): diferencias de formato (línea en
  blanco tras docstring antes de imports, colapso de paréntesis
  innecesarios) en los mismos archivos nuevos de features 05/14/16 más
  `test_retention.py`. Se corrigieron con `ruff format` (sin tocar
  lógica).
- `mypy backend/app` (2 errores): en `backend/app/capture_pipeline.py`,
  la variable `img` se infería como `PIL.ImageFile.ImageFile` (por
  `Image.open(path)`) y luego se reasignaba con el `Image.Image` más
  genérico que devuelve `image_prep.apply_exif_orientation()` (código de
  la feature 05). Se corrigió anotando explícitamente
  `img: Image.Image = Image.open(path)` en la primera asignación, sin
  cambiar el comportamiento en runtime.

Todos estos cambios son de la misma naturaleza que el alcance ya aprobado
de esta feature (lint/formato/tipos sobre código existente) — no
reabren ni modifican el comportamiento funcional de las features 05/14/16.

### Verificación Real Post-Merge

- `git merge origin/develop` → 6 archivos con conflicto real
  (`ROADMAP.md`, `backend/app/image_prep.py`, `backend/app/main.py`,
  `backend/app/services_config.py`, `docs/tecnica/index.md`,
  `docs/usuario/index.md`), todos resueltos manualmente como se describe
  arriba. Merge commit `84cc366`.
- `pip install -r backend/requirements-dev.txt` (mismo `.venv` de esta
  rama, Python 3.14.7) → sin cambios de versión (los `requirements*.txt`
  no cambiaron por el merge), solo instaló `playwright`/`greenlet`/`pyee`
  (dependencias de test E2E de la feature 17, ya presentes en
  `requirements-dev.txt` de `develop`, sin fijar — fuera del alcance de
  esta feature).
- `ruff check backend/app backend/tests scripts tests` → `All checks
  passed!` (tras el fix descripto arriba).
- `ruff check .` (desde la raíz, con `extend-exclude = ["runs", "docs"]`
  ya en `pyproject.toml`) → `All checks passed!`.
- `ruff format --check backend/app backend/tests scripts tests` → `76
  files already formatted` (tras aplicar `ruff format`).
- `ruff format --check .` (desde la raíz) → `101 files already
  formatted`.
- `mypy backend/app` → `Success: no issues found in 29 source files`
  (tras el fix de anotación en `capture_pipeline.py`).
- `pytest -v --basetemp=<scratch propio>` completo (`backend/tests/` +
  `tests/`) → **`341 passed, 10 skipped, 0 failed, 40 warnings in
  522.31s`**. Los 10 `skip` son los esperados: muestras privadas locales
  gitignored (features previas), permisos POSIX que no aplican en
  Windows (feature 14), y Playwright sin navegador instalado como
  paquete real (feature 17, fuera de alcance). Ningún test falló.
- `Get-FeatureContractStatus -Slug '18-calidad-ci-supply-chain' -Title
  'Calidad de CI y Supply Chain'` → `IsComplete: True`, `Problems: {}`.

### Alcance No Modificado En Esta Sincronización

- No se tocó `ROADMAP.md` más allá de resolver el conflicto de merge
  (ninguna otra entrada cambió de estado).
- No se corrió `ready-for-pr.ps1` de nuevo (la rama ya estaba marcada y
  la PR #10 ya existe).
- No se cerró ni se recreó la PR.
- No se revirtió ni se modificó ninguna lógica funcional de las features
  `03`/`05`/`14`/`16` ya mergeadas a `develop` — únicamente se
  eliminaron imports muertos, se corrigió formato y se agregó una
  anotación de tipo explícita, todo verificado con la suite de tests
  completa en verde.
