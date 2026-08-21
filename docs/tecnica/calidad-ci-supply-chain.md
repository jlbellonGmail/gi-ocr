# Calidad de CI y Supply Chain

Agrega gates de calidad de código y de cadena de suministro (supply
chain) al workflow `.github/workflows/ci.yml`, que hasta esta feature
solo corría `pytest`: lint (`ruff check`), formato (`ruff format
--check`), chequeo de tipos (`mypy`) y auditoría de vulnerabilidades de
dependencias (`pip-audit`). No toca el pipeline de negocio
(OCR/extracción/validación/`storage_bridge`) ni el frontend
funcionalmente — es infraestructura de calidad de todo el repo Python
(`backend/`, `scripts/`, `tests/`).

`AGENTS.md` dejaba constancia explícita de que el lint quedó pendiente a
propósito ("no se agrega sin antes dejar el código base limpio para
evitar romper el CI el mismo día de la adopción del circuito"): esta
feature salda esa deuda.

## Jobs de `ci.yml`

El workflow tiene dos jobs independientes (no hay dependencia entre
ellos, corren en paralelo):

- **`test`** (sin cambios de comportamiento): instala
  `backend/requirements.txt` y corre `pytest -v` sobre `backend/tests/` +
  `tests/`. Mismo comando que antes de esta feature.
- **`quality`** (nuevo): instala `backend/requirements-dev.txt` (que
  incluye `backend/requirements.txt` vía `-r`, más `ruff`, `mypy`,
  `pip-audit` y `playwright` sin fijar) y corre, en este orden:
  1. `ruff check backend/app backend/tests scripts tests`
  2. `ruff format --check backend/app backend/tests scripts tests`
  3. `mypy backend/app`
  4. `pip-audit -r backend/requirements.txt` + excepciones de
     `backend/config/pip-audit-ignore.txt` (**gate**)
  5. `pip-audit -r backend/requirements-dev.txt` (**informativo**, paso
     con `continue-on-error: true`: un hallazgo ahí no tumba el job)

Los pasos 1 a 4 son gate obligatorio: si fallan, el job `quality` falla y
bloquea el merge de la PR (ver `AGENTS.md`, paso 7 del circuito). El paso
5 nunca falla el job por sí mismo.

## Alcance de rutas

Las cuatro herramientas (excepto `mypy`, ver más abajo) cubren
`backend/app/`, `backend/tests/`, `scripts/` y `tests/`: todo el código
Python fuente del repo, salvo `backend/config/` (no es código Python) y
artefactos generados (`storage_bridge/`, `output/`, `.venv/`). Se pasan
rutas explícitas en cada comando de CI (no `ruff check .`) para que el
alcance quede fijo y auditable en el propio workflow, sin depender de
exclusiones implícitas de `pyproject.toml`.

## Reglas de `ruff`

Configuración en `pyproject.toml`, sección `[tool.ruff]` /
`[tool.ruff.lint]`:

- `line-length = 120`. El default de `ruff` es 88; con 88 el código
  existente reportaba 287 violaciones `E501` (línea larga) solo por ese
  motivo, la mayoría en docstrings/asserts descriptivos en español o
  f-strings de reporte, sin valor real en acortarlas agresivamente. Con
  120 (convención también usada por otros proyectos, ej. Django: 119)
  bajan a 15, resueltas manualmente sin perder legibilidad.
- `select = ["E", "F", "W", "I"]`: subconjunto deliberadamente acotado
  para esta primera iteración, tal como sugiere el spec de esta feature
  ("por ejemplo E, F, W, I"):
  - `E`/`W` — pycodestyle (estilo/espaciado/EOF).
  - `F` — Pyflakes (imports/variables no usadas, errores lógicos
    evidentes).
  - `I` — isort (orden de imports).
  - **No** se activan `B` (bugbear), `UP` (pyupgrade), `C90`
    (complejidad), `ANN` (anotaciones obligatorias), `D` (docstrings) ni
    otras categorías en esta iteración, para no forzar una reescritura
    masiva no pedida por el spec. Queda declarado como mejora incremental
    futura de roadmap, no deuda oculta.
- `[tool.ruff.lint.per-file-ignores]`: excepción puntual de `E402`
  (import no ubicado al inicio del archivo) para:
  - `scripts/*.py`: todos los scripts ejecutables standalone insertan la
    raíz del repo en `sys.path` **antes** de importar `backend.app.*` o
    `scripts.*` propios, para poder correrse sin instalar el paquete
    (`python scripts/proceso.py`). Es un patrón intencional repetido en
    varios scripts, no deuda de lint.
  - `backend/tests/test_document_result_exporter.py`,
    `backend/tests/test_process_document_cli.py`: mismo patrón
    `sys.path.insert()` antes del import, en tests que ejecutan código de
    `scripts/`/`backend/app` fuera del paquete instalado.
  - `backend/tests/test_pdf_util.py`: import condicionado a un
    `pytest.importorskip("pypdfium2")` previo (el import solo debe
    ejecutarse si el guard no saltó el módulo).
  - `tests/e2e/test_e2e_playwright.py`: mismo patrón con
    `pytest.importorskip("playwright")` (scaffolding de la feature
    17-pruebas-e2e-mobile-real, aún `[ ]` pendiente).

  Ninguna exclusión es un `ignore` global de una categoría completa (ej.
  desactivar todo `F` o todo `E`); son excepciones puntuales por
  archivo/regla con justificación en el propio `pyproject.toml`.

### Volumen de violaciones preexistentes y cómo se resolvieron

Con el ruleset elegido y `line-length = 120`, el código existente
reportaba 462 violaciones antes de esta feature (con `line-length = 88`
por defecto de `ruff`). Desglose y tratamiento:

| Regla | Cantidad | Tratamiento |
|---|---:|---|
| `E501` línea larga | 287 (15 con `line-length=120`) | 151 quedaron dentro del límite de 120 automáticamente; las 15 restantes se reformatearon a mano (multilínea) sin cambiar lógica ni asserts. |
| `F401` import no usado | 65 | `ruff check --fix` (autofix seguro: eliminación de imports realmente no referenciados). |
| `W292` sin newline final | 47 | `ruff check --fix`. |
| `I001` imports desordenados | 31 | `ruff check --fix` (más una segunda pasada tras ediciones manuales). |
| `E402` import no al inicio | 21 (20 tras autofix) | Excepciones documentadas por archivo (ver arriba), patrón `sys.path.insert`/`importorskip` intencional. |
| `W293` línea en blanco con espacios | 4 | `ruff check --fix`. |
| `F541` f-string sin placeholders | 3 | `ruff check --fix`. |
| `F841` variable local no usada | 3 | Revisadas una por una: una era dead code genuino en `t3_2_orchestrator.py` (se eliminó); dos en tests eran variables de resultado sin assert asociado — se corrigieron sin tocar aserciones (una se prefijó `_` para conservar el ejercicio de la llamada async, otra se eliminó por ser un literal sin uso). |
| `E713` `not in` | 1 | `ruff check --fix`. |

El reformateo automático de `ruff format` (57 archivos con diffs, 8 ya
formateados) y el autofix de lint (157 violaciones) se separaron en
commits dedicados de "reformateo automático" distintos del commit que
agrega la configuración de CI y de los commits con fixes manuales que sí
tocan lógica (variables no usadas, líneas largas reescritas, tipado),
para que el diff de reformateo puro no se mezcle con cambios de
comportamiento (ver spec, caso borde "Reformateo masivo mezclado con
lógica").

## Alcance y configuración de `mypy`

`mypy backend/app` — **solo** `backend/app/`, no `backend/tests/`,
`scripts/` ni `tests/`. Decisión explícita del spec ("Alcance inicial de
mypy limitado a backend/app/"), no una omisión silenciosa: ampliar el
tipado a tests/scripts es una migración de esfuerzo mayor, fuera de
alcance de esta primera iteración; queda como mejora incremental futura
de roadmap.

Configuración en `pyproject.toml`, sección `[tool.mypy]`, deliberadamente
permisiva:

```toml
[tool.mypy]
python_version = "3.12"
files = ["backend/app"]
ignore_missing_imports = true
disallow_untyped_defs = false
check_untyped_defs = false
warn_unused_ignores = true
warn_redundant_casts = true
```

- `ignore_missing_imports = true`: varias dependencias (`cv2`,
  `rapidocr_onnxruntime`, `easyocr`, `pypdfium2`) no publican stubs de
  tipo; sin este flag, mypy fallaría solo por no encontrar `.pyi`, sin
  relación con errores reales del código propio.
- `disallow_untyped_defs = false` / `check_untyped_defs = false`: no se
  exige anotar todas las funciones ni se chequean los cuerpos de las que
  no están anotadas. Foco en errores de tipo evidentes en el código que
  ya tiene anotaciones (la mayoría de `backend/app/` usa
  `from __future__ import annotations` y type hints), no una migración a
  tipado estricto completo (`mypy --strict`, explícitamente fuera de
  alcance del spec).
- `warn_unused_ignores = true`: evita que un `# type: ignore` quede
  "vivo" después de que el error que lo motivó ya no existe (deuda
  invisible).

### Errores encontrados y cómo se resolvieron (12 en 6 archivos)

Todos se corrigieron con anotaciones/guards reales, ninguno se silenció
con un `# type: ignore` sin necesidad — solo un caso usó `type: ignore`
puntual, documentado:

- `service_data_validation.py`: el diccionario `result` se infería como
  `dict[str, object]` por mezclar valores `str`/`bool`/`dict`/`list` sin
  anotación. Fix: `result: Dict[str, Any] = {...}`.
- `templates/providers.py`: `FieldTemplate.validator` declaraba
  `Callable[[str], Tuple[Optional[str], Optional[str]]]`, pero
  `validators.validate_amount` (usado en los campos `total`) devuelve
  `Tuple[Optional[float], Optional[str]]` — un mismatch real de tipos
  declarados vs. reales, no un bug de runtime (el llamador en
  `capture_pipeline.py` ya hace `str(value)` sobre el resultado). Fix:
  ampliar el tipo declarado a `Tuple[Optional[str] | Optional[float],
  Optional[str]]`, con comentario explicando por qué el valor normalizado
  puede ser `str` o `float` según el campo.
- `ocr_engine.py`: `_IMPORT_ERROR` se asignaba `None` en la rama `else`
  del `try/except` después de asignarse `e: Exception` en el `except`;
  mypy infería el tipo desde la primera asignación vista y marcaba la
  segunda como incompatible. Fix: anotación explícita
  `_IMPORT_ERROR: Exception | None = None` antes del `try`.
- `image_prep.py`: `~gray` (invert bit a bit) sobre el resultado de
  `cv2.cvtColor(..., COLOR_RGB2GRAY)` — los stubs de `cv2`/`numpy` no
  tipan ese resultado como `uint8` puro, mypy infiere un dtype que
  incluye `floating`, para el cual `__invert__` no está definido. En
  runtime `gray` siempre es `uint8` (es la salida de una conversión a
  escala de grises). Único `# type: ignore[misc]` de esta feature, con
  comentario explicando el motivo (falso positivo de stubs, no un bug
  real).
- `job_queue.py`: `self._queue: "asyncio.Queue[str]" = None` declaraba un
  tipo no-opcional pero se inicializaba en `None` (creado recién en
  `start()`). Fix: `Optional["asyncio.Queue[str]"]`, más un guard
  adicional (`if self._loop and self._queue:`) en los dos call sites que
  llaman `self._queue.put_nowait(...)`, ya que ambos atributos se crean
  juntos en el mismo método pero mypy no puede inferir esa invariante
  entre atributos de instancia.
- `main.py`: dos errores relacionados:
  - `InboundWatcher(..., on_new=lambda p: queue.enqueue(...))`: el
    `lambda` devolvía el `str` (`job_id`) de `enqueue()`, pero
    `on_new` está tipado `Callable[[Path], None]`. Fix: reemplazar el
    `lambda` por una función nombrada `_on_new_inbound(p: Path) -> None`
    que descarta el valor de retorno explícitamente (mejora de
    legibilidad además de fix de tipo).
  - `download_confirmed`: `store.load_confirmed(job_id)` devuelve
    `Optional[Dict[str, Any]]`; el código accedía `doc.get(...)`
    asumiendo que nunca es `None` (aunque `confirmed_exists(job_id)` ya
    se había chequeado antes). Fix: guard explícito `if doc is None:
    raise HTTPException(404, ...)` — además de resolver el error de tipo,
    cubre una carrera improbable pero real (el archivo desaparece entre
    el chequeo `confirmed_exists()` y la lectura).

## Estrategia de fijado de versiones

`backend/requirements.txt` pasa de rangos abiertos (`>=`) a versiones
exactas (`==`) para todas las dependencias directas (`fastapi`,
`uvicorn`, `python-multipart`, `pydantic`, `pydantic-settings`, `Pillow`,
`numpy`, `opencv-python-headless`, `pypdfium2`, `easyocr`, `pytest`,
`httpx`), preservando sin modificar el pin y el comentario ya existentes
de `rapidocr-onnxruntime==1.2.3` / `onnxruntime==1.28.0` (ver
`docs/tecnica/captura-ocr-local-agil.md` para el motivo original de ese
pin: `ocr_engine.py` depende de atributos internos de
`text_detector`/`text_recognizer` que cambiaron en versiones más nuevas
de `rapidocr-onnxruntime`).

Las versiones fijadas son las resueltas por `pip install -r
backend/requirements.txt` en un entorno limpio durante la implementación
de esta feature (instaladas y verificadas con `pytest -v` completo
pasando en ese mismo entorno), no versiones arbitrarias elegidas a mano.

`backend/requirements-dev.txt` (archivo ya existente, scaffolding de la
feature 17-pruebas-e2e-mobile-real) queda extendido, no reemplazado:

- conserva `-r requirements.txt` sin modificar;
- **elimina** `pytest>=8.0.0` y `httpx>=0.27.0`: quedaban redundantes una
  vez que el criterio 7 los fija (`==`) en `backend/requirements.txt`
  (que ya se incluye vía `-r`); mantener un rango abierto duplicado ahí
  contradecía el objetivo de "dependencias fijadas";
- **agrega** `ruff==0.16.4`, `mypy==2.3.1`, `pip-audit==2.10.1` (últimas
  versiones estables publicadas al momento de implementar esta feature);
- **deja intacta, sin fijar**, `playwright>=1.40.0`: pertenece al
  scaffolding de la feature 17-pruebas-e2e-mobile-real, aún `[ ]`
  pendiente en `ROADMAP.md`. Fijar su versión (y la de los navegadores
  compatibles) es una decisión de esa feature, no de esta.

El `Dockerfile` de producción (Feature 03/ADR-009) sigue instalando
únicamente `backend/requirements.txt` (excluyendo `easyocr` vía `grep
-v`, sin cambios de esta feature): `ruff`/`mypy`/`pip-audit`/`playwright`
nunca llegan a la imagen de producción.

## Política de excepciones de `pip-audit`

El gate obligatorio (`pip-audit -r backend/requirements.txt`) admite
excepciones explícitas vía `backend/config/pip-audit-ignore.txt`: un
archivo de texto plano, un ID de vulnerabilidad (CVE/GHSA) por línea con
motivo en comentario, traducido a flags `--ignore-vuln <ID>` en el paso
de CI (`.github/workflows/ci.yml`, job `quality`). Ninguna vulnerabilidad
se silencia deshabilitando el paso completo o bajando su severidad fuera
de este archivo.

**Esta lista de excepciones no es una declaración de una sola vez: debe
revisarse cada vez que se modifica `backend/requirements.txt`** —
agregar, quitar o cambiar de versión cualquier dependencia obliga a
confirmar que cada excepción activa sigue siendo necesaria (no quedó
obsoleta por un upgrade ya disponible) y que no se introdujeron
vulnerabilidades nuevas sin registrar. Esta política está declarada como
texto explícito tanto en el propio archivo
(`backend/config/pip-audit-ignore.txt`) como aquí, de forma verificable
(ver `backend/tests/test_data_file_emptiness.py` y el resto de la suite
para el patrón de verificación por grep/test usado en este repo; la
verificación puntual de esta frase queda a cargo del reviewer humano de
cada PR que toque `requirements.txt`, apoyado en el texto de la
política — no se automatizó con un script propio en esta iteración, ver
spec, "Riesgos/supuestos").

Al momento de implementar esta feature, **no hay excepciones activas**:
`backend/config/pip-audit-ignore.txt` documenta la política y queda listo
para recibir entradas si una vulnerabilidad futura en una dependencia
fijada (por ejemplo `rapidocr-onnxruntime==1.2.3` u
`onnxruntime==1.28.0`, ya fijadas por la incompatibilidad documentada en
`ocr_engine.py`) no tuviera upgrade disponible.

## Casos borde

### `pip-audit` sin conexión a internet

Durante la implementación de esta feature, el entorno de desarrollo local
usado por el `builder-agent` no pudo completar `pip-audit -r
backend/requirements.txt` contra el índice real de PyPI: la conexión
HTTPS a `pypi.org` falló con `SSLCertVerificationError` (certificado no
verificable, típico de un entorno con proxy/sandbox de red restringido),
tanto con la configuración SSL por defecto como apuntando explícitamente
al bundle de certifi. No es un falso verde: el comando terminó con
traceback y código de salida distinto de 0, de forma claramente
distinguible de "sin vulnerabilidades encontradas". En GitHub Actions
(`ubuntu-latest`, con acceso real a `pypi.org`), se espera que el paso
gate corra normalmente; su primer resultado real debe revisarse en el
primer run de CI de la PR de esta feature, y esa primera revisión cuenta
como el punto de partida de la política de excepciones descripta arriba.
El paso informativo (`requirements-dev.txt`) tiene el mismo riesgo, pero
al ser `continue-on-error: true` no bloquea el job aunque no pueda
completarse.

### Diferencia de terminador de línea (CRLF/LF)

`.gitattributes` ya normaliza `*.py` a `eol=lf` en el repo (independiente
del entorno de desarrollo primario en Windows). `ruff format` no generó
diffs relacionados con finales de línea distintos de lo que ya normaliza
Git; no hizo falta configuración adicional.

### Reformateo masivo separado de cambios de lógica

Ver "Volumen de violaciones preexistentes" arriba: el commit de `ruff
format` (57 archivos) se mantiene separado de los commits que sí cambian
comportamiento o tipos.

### `backend/requirements-dev.txt` no se filtra al `Dockerfile`

Verificado leyendo `Dockerfile`: sigue copiando únicamente
`backend/requirements.txt` (con el filtro `grep -v -E '^easyocr'` ya
existente de la Feature 03), sin referencia a
`backend/requirements-dev.txt`. `ruff`, `mypy`, `pip-audit`, `playwright`
y `torch` (vía `easyocr`, ya excluido) no llegan a la imagen de
producción.

### `easyocr`/`torch` como dependencia pesada en el job `quality`

Igual que el job `test` (sin cambios de esta feature), `pip install -r
backend/requirements-dev.txt` arrastra `torch` vía `easyocr` (declarado
en `backend/requirements.txt`, incluido en `requirements-dev.txt` vía
`-r`). Esto aumenta el tiempo de instalación del job `quality` de forma
comparable al job `test` ya existente; se acepta como riesgo conocido, no
bloqueante para esta feature (ver spec, "Casos borde").
