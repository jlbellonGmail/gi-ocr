# Calidad de CI y Supply Chain

## Para qué sirve

Esta feature no agrega ni cambia ningún endpoint HTTP ni flujo de usuario
final del frontend: es infraestructura de calidad de código para quien
mantiene o contribuye al repositorio `gi-ocr`. A partir de esta feature,
cada `push`/`pull request` hacia `develop` o `main` corre, además de los
tests (`pytest`, sin cambios), un segundo job de CI (`quality`) que
verifica automáticamente:

- que el código nuevo o modificado no rompe reglas básicas de estilo
  (`ruff check`) ni de formato (`ruff format --check`);
- que `backend/app/` no tiene errores de tipo evidentes (`mypy`);
- que las dependencias declaradas en `backend/requirements.txt` (las que
  sí llegan a producción) no tienen vulnerabilidades conocidas sin
  excepción documentada (`pip-audit`, gate);
- de forma informativa (sin bloquear), que las dependencias de
  desarrollo (`backend/requirements-dev.txt`, incluye `playwright`) no
  tienen vulnerabilidades conocidas.

Si el job `quality` falla en una PR, el merge queda bloqueado igual que
si fallara `pytest` (ver `AGENTS.md`, paso 7 del circuito: "CI verde" es
condición previa a la decisión humana de `MERGE`).

## Cómo correr los mismos chequeos localmente antes de commitear

Con el entorno virtual activado desde la raíz del repo:

```bash
pip install -r backend/requirements-dev.txt
```

Esto instala `ruff`, `mypy`, `pip-audit` (fijados a versión exacta) más
todo lo que ya trae `backend/requirements.txt` (fijado también, vía `-r
requirements.txt`) y `playwright>=1.40.0` (sin fijar, scaffolding de la
feature 17-pruebas-e2e-mobile-real).

### 1. Lint

```bash
ruff check backend/app backend/tests scripts tests
```

Salida esperada en caso de éxito:

```
All checks passed!
```

### 2. Formato

```bash
ruff format --check backend/app backend/tests scripts tests
```

Salida esperada en caso de éxito (el número exacto de archivos varía con
el estado del repo):

```
65 files already formatted
```

Si este comando reporta archivos que serían reformateados, corré `ruff
format backend/app backend/tests scripts tests` (sin `--check`) para
aplicar el formato antes de commitear.

### 3. Chequeo de tipos

```bash
mypy backend/app
```

Salida esperada en caso de éxito:

```
Success: no issues found in 24 source files
```

### 4. Auditoría de vulnerabilidades (runtime, la misma que corre como gate en CI)

```bash
pip-audit -r backend/requirements.txt
```

En caso de éxito y sin vulnerabilidades, termina con código de salida `0`
y un resumen sin filas. Si `backend/config/pip-audit-ignore.txt` tiene
excepciones activas, replicá el comportamiento exacto de CI agregando
`--ignore-vuln <ID>` por cada línea no vacía y no comentada de ese
archivo (ver `docs/tecnica/calidad-ci-supply-chain.md`, sección
"Política de excepciones de `pip-audit`", para el detalle completo de
cuándo y cómo se agrega una excepción).

**Nota de entorno:** si tu red bloquea o intercepta el acceso HTTPS a
`pypi.org` (por ejemplo, detrás de un proxy corporativo sin el
certificado instalado), este comando puede fallar con un error de
verificación de certificado SSL en vez de reportar vulnerabilidades. Eso
es un problema de conectividad de tu entorno, no un resultado de
"sin vulnerabilidades" — no lo interpretes como éxito. El paso equivalente
en GitHub Actions corre con acceso real a `pypi.org`.

### 5. Auditoría de vulnerabilidades (desarrollo, informativa)

```bash
pip-audit -r backend/requirements-dev.txt
```

Este comando es el equivalente local del paso informativo de CI: no se
exige código de salida `0` (puede reportar hallazgos sobre `playwright`
sin fijar, por ejemplo), alcanza con que la ejecución termine sin error
de arranque del propio comando.

## Qué pasa si alguno falla

- `ruff check` con errores: corré `ruff check --fix backend/app
  backend/tests scripts tests` para aplicar las correcciones automáticas
  seguras, y revisá a mano el resto (por ejemplo, variables no usadas
  genuinas o violaciones que `ruff` marca como no fixeable
  automáticamente).
- `ruff format --check` con diffs pendientes: corré `ruff format
  backend/app backend/tests scripts tests` (sin `--check`).
- `mypy` con errores: agregá o corregí anotaciones de tipo en
  `backend/app/`. Si un error es un falso positivo genuino (stubs
  incompletos de una librería de terceros), usá `# type: ignore[<código>]`
  puntual **con un comentario que explique el motivo** — no un `# type:
  ignore` sin código de error ni justificación.
- `pip-audit` (paso gate) con una vulnerabilidad real reportada: primero
  intentá actualizar la dependencia afectada en `backend/requirements.txt`
  a una versión con fix. Si no es posible (por ejemplo, por la
  incompatibilidad ya documentada de `rapidocr-onnxruntime`/`onnxruntime`
  en el propio `requirements.txt`), agregá una excepción justificada en
  `backend/config/pip-audit-ignore.txt` con el ID de la vulnerabilidad y
  el motivo — nunca deshabilites el paso de CI para esconder el
  hallazgo.
