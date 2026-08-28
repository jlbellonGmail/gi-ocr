# Spec: Calidad de CI y Supply Chain

## Alcance

Incluye:

- **Lint**: incorporar `ruff check` como gate de CI sobre `backend/app/`,
  `backend/tests/`, `scripts/` y `tests/`. Si el código base actual tiene
  violaciones preexistentes, el builder debe resolverlas (fix o exclusión
  explícita y justificada por archivo/regla, no un `ignore` global de
  reglas core como `F` sin motivo) antes de activar el gate, para cumplir
  "sin romper el baseline actual".
- **Formato**: incorporar `ruff format --check` como gate de CI. Si
  reformatear el código existente genera un diff masivo, aplicarlo en un
  commit dedicado dentro de la misma feature (no mezclado con cambios de
  lógica), para que el reviewer pueda diferenciar reformateo de cambios
  funcionales.
- **Type checks**: incorporar `mypy` sobre `backend/app/` (no sobre
  `backend/tests/`, `scripts/` ni `tests/` en esta primera iteración,
  ver "Riesgos / supuestos"). Configuración inicial permisiva (permite
  funciones sin anotar, foco en detectar errores de tipo evidentes, no
  una migración a tipado estricto completo) para no bloquear CI el mismo
  día de adopción.
- **Dependencias fijadas**: convertir `backend/requirements.txt` de
  rangos abiertos (`>=`) a versiones exactas (`==`), preservando los
  comentarios existentes que documentan por qué `rapidocr-onnxruntime` y
  `onnxruntime` están fijados. Se fijan las versiones actualmente
  instaladas y probadas en CI/desarrollo, no versiones arbitrarias.
- **Auditoría básica de vulnerabilidades**: incorporar `pip-audit` como
  paso de CI contra las dependencias resueltas de
  `backend/requirements.txt` (gate obligatorio). Si al momento de
  implementar existen vulnerabilidades conocidas sin fix disponible en el
  baseline actual (por ejemplo, en una dependencia fijada como
  `rapidocr-onnxruntime==1.2.3` por incompatibilidad documentada), deben
  quedar declaradas explícitamente en una lista de excepciones de
  `pip-audit` con justificación (CVE, motivo de no poder actualizar,
  referencia a la nota ya existente en `requirements.txt`), nunca
  silenciadas sin registro ni logradas deshabilitando el paso completo.
  Esa lista de excepciones se revisa —no solo se documenta una vez— cada
  vez que se modifica `backend/requirements.txt` (ver criterio 5).
  Además, se agrega un segundo paso de `pip-audit`, **informativo, no
  gate**, contra las dependencias resueltas de
  `backend/requirements-dev.txt` (que incluye `playwright`, superficie de
  automatización de navegador no trivial): reporta hallazgos en el log
  del job sin fallar el build (ver criterio 6 y "Riesgos / supuestos"
  para la justificación de por qué no es gate).
- **CI reproducible**: mantener el job `pytest` actual sin romperlo,
  agregar los pasos de lint/formato/type-check/auditoría al mismo
  workflow `.github/workflows/ci.yml` (o jobs adicionales dentro de él),
  de forma que un mismo push/PR ejecute una build determinística con
  versiones fijadas.
- **Herramientas de desarrollo separadas del runtime**: `backend/requirements-dev.txt`
  **ya existe** en el repo (creado como scaffolding de la feature
  17-pruebas-e2e-mobile-real, aún `[ ]` pendiente en `ROADMAP.md`), con
  el contenido actual:
  ```
  # Dependencias de desarrollo / testing locales (no requeridas en runtime).
  -r requirements.txt
  pytest>=8.0.0
  httpx>=0.27.0
  playwright>=1.40.0
  ```
  Esta feature **extiende** ese archivo existente, no lo crea ni lo
  reemplaza. Ver criterio 8 para el contenido resultante exacto exigido
  (qué líneas se eliminan, cuáles se agregan fijadas y cuál se deja
  intacta). El objetivo se mantiene: declarar `ruff`, `mypy` y
  `pip-audit` como herramientas de desarrollo, sin bloatear la imagen
  Docker de producción (`Dockerfile`, ver ADR-009) ni introducir
  dependencias de tooling en el entorno de ejecución del backend.
- **Configuración de herramientas**: un `pyproject.toml` nuevo en la raíz
  del repo, usado únicamente para las secciones `[tool.ruff]` y
  `[tool.mypy]` (y opcionalmente `[tool.pytest.ini_options]` si conviene
  centralizar la config actual de pytest). No incluye sección
  `[build-system]` ni migra el proyecto a un backend de build/paquetería
  (Poetry, Hatch, pip-tools). El gestor de paquetes sigue siendo `pip` +
  `backend/requirements.txt`/`backend/requirements-dev.txt`, conforme a
  `AGENTS.md` ("Gestor de paquetes: pip + entorno virtual").

Explícitamente NO incluye:

- Migrar de `pip` a Poetry, PDM o pip-tools/hashes (`--require-hashes`).
  Esto sería un cambio de gestor de paquetes y requeriría su propia
  decisión de arquitectura documentada en `docs/tecnica/arquitectura.md`
  como ADR nuevo — está fuera de alcance de esta feature.
- Tipado estricto completo (`mypy --strict`) de todo el repo, incluidos
  `backend/tests/`, `scripts/` y `tests/`. Se deja como mejora incremental
  futura (ver "Riesgos / supuestos").
- Cambiar el motor OCR, el formato `.DATA`/`services.ini` o la separación
  OCR/extracción/validación/storage (no se toca ninguna de estas
  decisiones, ver `docs/tecnica/arquitectura.md`, ADR-006 y ADR-007).
- Agregar un job de seguridad de contenedor/imagen Docker (escaneo de
  imagen tipo Trivy) — la Feature 03/ADR-009 ya cubre empaquetado; el
  escaneo de imagen queda fuera de este alcance salvo que se agregue
  explícitamente como ítem de roadmap futuro.
- Pre-commit hooks (`pre-commit` framework). El gate vive en CI; agregar
  hooks locales queda como mejora opcional no bloqueante, fuera de
  alcance salvo que el builder lo considere trivial y no cambie el
  contrato de CI.
- Resolver deuda de dependencias no fijadas de forma automática con
  Dependabot/Renovate. Puede proponerse como tarea de roadmap futura, no
  se implementa acá.
- Implementar, completar o decidir el contenido/versiones de Playwright
  de la feature 17-pruebas-e2e-mobile-real. Esta feature (18) no fija la
  versión de `playwright>=1.40.0` en `requirements-dev.txt`: esa decisión
  (incluida la elección de versión de navegadores compatible) le
  corresponde a la feature 17 cuando se implemente (ver "Riesgos /
  supuestos").

## Contexto

El pipeline OCR de gi-ocr (`backend/app/`) ya está probado con `pytest`
en CI (`.github/workflows/ci.yml`), pero ese workflow solo corre tests:
no hay lint, ni formato, ni verificación de tipos, ni auditoría de
dependencias. `backend/requirements.txt` fija dos dependencias críticas
(`rapidocr-onnxruntime`, `onnxruntime`) por motivos de compatibilidad
documentados en el propio archivo, pero el resto de las dependencias
(FastAPI, Pydantic, Pillow, numpy, opencv, pypdfium2, easyocr, pytest,
httpx) usa rangos abiertos (`>=`), lo que permite que una build futura
instale versiones nunca probadas contra este código sin previo aviso —
justo el tipo de deriva que rompió `rapidocr-onnxruntime` en el pasado
según el comentario ya presente en el archivo.

`AGENTS.md` deja constancia explícita de que el lint quedó pendiente a
propósito ("no se agrega sin antes dejar el código base limpio para
evitar romper el CI el mismo día de la adopción del circuito"): esta
feature (18) es la que salda esa deuda declarada. No toca el pipeline de
negocio (OCR/extracción/validación/storage_bridge) ni el frontend
funcionalmente; es infraestructura de calidad de todo el repo Python
(`backend/`, `scripts/`, `tests/`).

Además, `backend/requirements-dev.txt` ya existe como scaffolding
adelantado de la feature 17 (aún no implementada, no referenciado hoy por
CI ni por el `Dockerfile`). Esta feature 18 es la primera en darle uso
real (vía CI), por lo que le corresponde dejarlo en un estado consistente
con "dependencias fijadas" para las herramientas que sí introduce (ruff,
mypy, pip-audit), sin invadir decisiones que pertenecen a la feature 17
(fijar `playwright`, elegir navegadores, etc.).

## Criterios de aceptación

1. `.github/workflows/ci.yml` ejecuta, además del job `pytest` ya
   existente (que debe seguir pasando sin cambios de comportamiento),
   pasos que corren `ruff check`, `ruff format --check`, `mypy
   backend/app/`, `pip-audit` contra `backend/requirements.txt` (gate) y
   `pip-audit` contra `backend/requirements-dev.txt` (informativo, no
   gate). Los cuatro primeros pasos son gate obligatorio (fallan el job
   si no pasan), salvo las excepciones explícitas de `pip-audit`
   documentadas en el punto 5. El quinto paso (`pip-audit` sobre
   `requirements-dev.txt`) nunca falla el job por sí mismo (ver
   criterio 6).
2. `ruff check` sobre `backend/app/`, `backend/tests/`, `scripts/` y
   `tests/` no reporta errores en el HEAD de la rama de la feature (el
   código existente fue corregido o las exclusiones puntuales están
   documentadas con justificación en `pyproject.toml` mediante
   comentarios o `# noqa: <regla> — <motivo>` en el propio código, no un
   `ignore` global sin motivo).
3. `ruff format --check` sobre las mismas rutas no reporta diffs
   pendientes.
4. `mypy backend/app/` corre sin errores con la configuración inicial
   definida por esta feature (nivel permisivo, ver Alcance). Si algún
   módulo requiere `# type: ignore` puntual, debe llevar comentario con
   el motivo.
5. `pip-audit` corre contra las dependencias resueltas de
   `backend/requirements.txt` (no contra `requirements-dev.txt`, ver
   criterio 6 para ese árbol) como gate obligatorio. Si al momento de
   implementar existe alguna vulnerabilidad conocida sin parche
   disponible en las versiones fijadas, existe una lista de excepciones
   explícita (archivo de configuración de `pip-audit` o flags
   documentados en el propio workflow) con el CVE/ID y el motivo de no
   poder actualizar; el job sigue siendo gate para cualquier
   vulnerabilidad nueva no exceptuada. Esta lista de excepciones **no es
   una declaración de una sola vez**: el propio archivo de excepciones
   (o su sección correspondiente) y `docs/tecnica/calidad-ci-supply-chain.md`
   deben incluir, como texto explícito y verificable (por ejemplo,
   mediante un grep/test que confirme la presencia de la frase), la
   política de que la lista se revisa cada vez que se modifica
   `backend/requirements.txt` (no solo se escribe una vez al crearla).
6. Existe un paso adicional de `pip-audit` en CI, **informativo y no
   bloqueante**, ejecutado contra las dependencias resueltas de
   `backend/requirements-dev.txt` (incluye `ruff`, `mypy`, `pip-audit`
   fijados por esta feature, más `pytest`/`httpx` vía `-r
   requirements.txt`, y `playwright>=1.40.0` sin fijar). Este paso:
   - se implementa de forma que su código de salida no afecte el
     resultado del job (por ejemplo `continue-on-error: true` en GitHub
     Actions, o capturando la salida con `|| true` y publicándola en el
     log/summary del job);
   - es verificable inspeccionando la definición del paso en
     `.github/workflows/ci.yml` (debe existir y estar marcado como no
     bloqueante) y confirmando en un run real de CI que el job global
     pasa aunque este paso reporte hallazgos;
   - existe para dar visibilidad sobre una superficie de dependencias de
     desarrollo no trivial (automatización de navegador vía Playwright),
     sin convertir esta feature en la que decide fijar o resolver
     vulnerabilidades de una dependencia que pertenece a la feature 17
     (ver "Riesgos / supuestos").
7. `backend/requirements.txt` fija (`==`, no `>=`) la versión de cada
   dependencia directa (`fastapi`, `uvicorn`, `python-multipart`,
   `pydantic`, `pydantic-settings`, `Pillow`, `numpy`,
   `opencv-python-headless`, `pypdfium2`, `easyocr`, `pytest`, `httpx`),
   preservando sin modificar el pin y los comentarios ya existentes de
   `rapidocr-onnxruntime` y `onnxruntime`.
8. `backend/requirements-dev.txt` (archivo **ya existente**, no se crea
   de cero) queda extendido, no reemplazado, con el siguiente resultado
   verificable:
   - conserva la línea `-r requirements.txt` sin modificar;
   - **elimina** las líneas `pytest>=8.0.0` y `httpx>=0.27.0`: quedan
     redundantes porque `-r requirements.txt` ya las incluye, y una vez
     que el criterio 7 las fija a `==` en `backend/requirements.txt`,
     mantener un rango abierto duplicado en `requirements-dev.txt` para
     las mismas dependencias no aporta nada y contradice el objetivo de
     "dependencias fijadas" de esta feature;
   - **agrega** `ruff`, `mypy` y `pip-audit`, cada uno fijado a versión
     exacta (`==`), igual que en `backend/requirements.txt`;
   - **deja intacta, sin fijar**, la línea `playwright>=1.40.0`: no se
     toca su versión ni se agrega ninguna dependencia adicional de
     Playwright (por ejemplo navegadores/browsers), porque pertenece al
     scaffolding de la feature 17-pruebas-e2e-mobile-real, todavía `[ ]`
     pendiente en `ROADMAP.md`, y fijar su versión es una decisión que le
     corresponde a esa feature cuando se implemente;
   - el `Dockerfile` de producción (Feature 03/ADR-009) sigue instalando
     únicamente `backend/requirements.txt` y no se modifica su
     comportamiento de build.
9. Existe `pyproject.toml` en la raíz con `[tool.ruff]` y `[tool.mypy]`
   (y, si el builder lo considera conveniente sin romper nada, migración
   de la config actual de pytest a `[tool.pytest.ini_options]`). No
   contiene sección `[build-system]` ni cambia el mecanismo de
   instalación del proyecto.
10. Ejecutar localmente, con el entorno virtual activado desde la raíz
    del repo: `pip install -r backend/requirements-dev.txt`, luego `ruff
    check .`, `ruff format --check .`, `mypy backend/app/`, `pip-audit -r
    backend/requirements.txt` — los cuatro comandos terminan con código
    de salida 0 (salvo excepciones documentadas de `pip-audit`). Además,
    `pip-audit -r backend/requirements-dev.txt` corre sin error de
    ejecución (puede reportar hallazgos; no se exige código de salida 0
    para este comando, es el equivalente local del paso informativo del
    criterio 6).
11. El job `pytest` original sigue pasando sin modificaciones de
    comportamiento (mismo comando `pytest -v`, misma cobertura de
    `backend/tests/` + `tests/`); esta feature no debe requerir cambios
    en tests existentes para pasar CI salvo que un fix de lint/formato
    toque un archivo de test (permitido, siempre que no cambie
    aserciones ni lógica de test).
12. Debe existir `docs/tecnica/calidad-ci-supply-chain.md`, no vacío, con
    el detalle de qué corre cada paso de CI, la configuración elegida de
    `ruff`/`mypy` (reglas activas, exclusiones y su justificación), la
    estrategia de fijado de versiones, la política de excepciones de
    `pip-audit` (incluida la revisión obligatoria cada vez que cambia
    `backend/requirements.txt`), y el tratamiento dado a
    `backend/requirements-dev.txt` (extensión del archivo existente,
    remoción de duplicados, `playwright` sin fijar y por qué, paso
    informativo de `pip-audit` sobre ese árbol).
13. Debe existir `docs/usuario/calidad-ci-supply-chain.md`, no vacío, con
    el propósito de esta feature para quien mantiene o contribuye al
    repo (no hay endpoint HTTP nuevo ni cambio de flujo de usuario final,
    ver "Riesgos / supuestos"), y al menos un ejemplo concreto de uso:
    los comandos exactos para correr lint/formato/type-check/auditoría
    localmente antes de un commit, junto con la salida esperada en caso
    de éxito (equivalente funcional al par request/response exigido para
    features con endpoint).
14. Debe existir `runs/18-calidad-ci-supply-chain/decision.md` con las
    decisiones tomadas (elección de `ruff`+`mypy`+`pip-audit`, alcance de
    `mypy` limitado a `backend/app/`, separación
    `requirements.txt`/`requirements-dev.txt`, manejo de excepciones de
    `pip-audit` si aplicaron, tratamiento de
    `backend/requirements-dev.txt` existente y su relación con la
    feature 17) y evidencia de que el contrato del circuito
    (`scripts/feature-contract.ps1`) pasa.
15. Debe existir un enlace exacto a `calidad-ci-supply-chain.md` en
    `docs/tecnica/index.md` y otro en `docs/usuario/index.md`, siguiendo
    el mismo formato de lista que las entradas existentes (por ejemplo
    `- [Calidad de CI y Supply Chain](calidad-ci-supply-chain.md)`).

Nota: esta feature no toca extracción OCR (no hay campo extraído, tipo de
documento, fixture ni validación semántica involucrados), por lo que los
criterios adicionales de dominio OCR de `AGENTS.md` no aplican.

## Casos borde a contemplar

- **Ruleset de `ruff` demasiado estricto de entrada**: si se activa el
  ruleset por defecto completo, el volumen de violaciones preexistentes
  puede ser grande. El builder debe decidir un subconjunto de reglas
  razonable para la primera iteración (por ejemplo `E`, `F`, `W`, `I`) y
  documentar en `docs/tecnica/calidad-ci-supply-chain.md` qué categorías
  quedaron fuera y por qué, en vez de forzar una reescritura masiva no
  pedida por esta feature.
- **`mypy` sobre código con `Any` implícito extendido** (por ejemplo,
  resultados de OCR/OpenCV sin stubs de tipo): puede requerir
  `# type: ignore` puntuales o `disallow_untyped_defs = false` inicial;
  documentar cada ignore con motivo, no acumular ignores sin registro.
- **`pip-audit` sin conexión a internet** (entorno CI aislado, rate
  limiting del índice de vulnerabilidades): el paso gate (contra
  `backend/requirements.txt`) debe fallar de forma clara y distinguible
  de "vulnerabilidad encontrada", no como falso verde ni bloqueo
  silencioso; documentar el comportamiento esperado. El paso informativo
  (contra `requirements-dev.txt`) puede degradar a "sin resultado" sin
  bloquear el job, pero debe quedar visible en el log que no pudo
  completarse (no confundirse con "sin vulnerabilidades").
- **`rapidocr-onnxruntime==1.2.3` u `onnxruntime==1.28.0` con
  vulnerabilidad conocida sin upgrade posible** (por la incompatibilidad
  ya documentada en `ocr_engine.py`): debe quedar en la lista de
  excepciones de `pip-audit` con referencia cruzada al comentario
  existente en `requirements.txt`, no debe romper CI de forma
  sorpresiva.
- **`easyocr` como dependencia pesada** (arrastra `torch`): el paso de
  `pip-audit`/`pip install` de `requirements-dev.txt` puede aumentar
  notablemente el tiempo de CI; verificar que el tiempo total del job
  siga siendo razonable y, si no, documentar la degradación como riesgo
  aceptado (no como bloqueo de esta feature).
- **Diferencia de terminador de línea (CRLF/LF)**: el entorno de
  desarrollo primario es Windows (PowerShell); `ruff format` normaliza
  finales de línea. Verificar que no entre en conflicto con
  `.gitattributes` (si existe) ni genere diffs espurios recurrentes entre
  Windows y CI (`ubuntu-latest`).
- **Reformateo masivo mezclado con lógica**: si `ruff format` reescribe
  muchos archivos, ese commit debe quedar separado de cualquier cambio de
  comportamiento, para que `reviewer-agent`/QA puedan diferenciar ambos
  tipos de diff.
- **Fijado de versiones rompe una dependencia transitiva no compatible**
  entre sí (por ejemplo, `numpy` fijado vs. una versión de `opencv` que
  requiere otra): validar `pytest -v` completo después de fijar
  versiones, no asumir que fijar automáticamente preserva compatibilidad.
- **`backend/requirements-dev.txt` filtrándose al `Dockerfile`**: agregar
  un caso de test/verificación manual (o nota explícita en
  `docs/tecnica/`) de que el build de imagen sigue instalando solo
  `backend/requirements.txt`, para no aumentar el tamaño de la imagen de
  producción con `mypy`/`ruff`/`pip-audit`/`torch` de `easyocr`/`playwright`
  (`easyocr` ya excluido del Dockerfile según ADR-009, no cambia acá).
- **Editar `backend/requirements-dev.txt` sin notar que ya existe**: es
  exactamente el problema que motivó este intento 2 del spec. El builder
  debe partir del contenido real del archivo (no asumir que está vacío o
  que no existe), preservar `-r requirements.txt` y `playwright>=1.40.0`
  tal cual, y solo tocar las líneas descriptas en el criterio 8, para no
  pisar en silencio el scaffolding de la feature 17 aún pendiente.
- **Excepción de `pip-audit` usada para ocultar deuda real** en vez de
  una vulnerabilidad genuinamente sin fix: el criterio de aceptación 5
  exige justificación explícita por excepción y su revisión periódica
  ligada a cambios de `requirements.txt`, exactamente para evitar este
  caso borde.

## Riesgos / supuestos

- **Herramientas elegidas**: se opta por `ruff` (lint + formato en una
  sola herramienta, ya sugerido como estándar del stack Python 3.12) y
  `mypy` (más establecido que `pyright` en proyectos que no usan VSCode
  como único entorno) y `pip-audit` (mantenido por PyPA, coherente con
  `pip` como gestor de paquetes ya adoptado). Si el reviewer prefiere
  `pyright` o `safety` en su lugar, es una objeción válida a este spec,
  no un defecto de implementación.
- **Alcance inicial de `mypy` limitado a `backend/app/`**: se decide no
  tipar `backend/tests/`, `scripts/` ni `tests/` en esta primera
  iteración para no ampliar el esfuerzo de esta feature a una migración
  de tipado completa del repo. Se documenta como decisión explícita, no
  como omisión silenciosa; puede ampliarse en una feature de roadmap
  futura.
- **No se adopta pip-tools/hashes ni se cambia de gestor de paquetes**:
  `AGENTS.md` fija "Gestor de paquetes: pip + entorno virtual (.venv)"
  como parte del stack. Fijar versiones con `==` en
  `backend/requirements.txt` cumple el criterio "dependencias fijadas"
  del ítem 18 del `ROADMAP.md` sin requerir ese cambio de arquitectura.
  Si en el futuro se decide adoptar lockfiles con hashes, debe declararse
  como ADR nuevo en `docs/tecnica/arquitectura.md`, conforme a la regla
  dura de `AGENTS.md` sobre no cambiar el gestor de paquetes sin
  dejarlo explícito como decisión de arquitectura.
- **`backend/requirements-dev.txt` ya existe: se extiende, no se
  recrea**: verificado leyendo el archivo real del repo (contenido:
  `-r requirements.txt`, `pytest>=8.0.0`, `httpx>=0.27.0`,
  `playwright>=1.40.0`), es scaffolding de la feature
  17-pruebas-e2e-mobile-real (`[ ]` pendiente en `ROADMAP.md`, no
  referenciado hoy por CI ni por el `Dockerfile`). Decisiones tomadas
  explícitamente para esta feature 18:
  - `pytest>=8.0.0` y `httpx>=0.27.0` se **eliminan** de
    `requirements-dev.txt` por redundantes: ya llegan vía
    `-r requirements.txt`, y esta feature los fija a `==` ahí (criterio
    7). Mantenerlos duplicados con rango abierto en `requirements-dev.txt`
    no aporta nada y va en contra del objetivo de "dependencias
    fijadas".
  - `playwright>=1.40.0` **no se fija** a versión exacta en esta feature:
    es scaffolding de una feature todavía no implementada (17), y fijar
    su versión implica decisiones que exceden el alcance de esta feature
    (versión de navegadores, estrategia de instalación de Playwright en
    CI). Se documenta como decisión explícita para que la feature 17, al
    implementarse, decida su propio fijado sin que esta feature 18 se lo
    haya adelantado a ciegas.
  - Si el reviewer prefiere fijar `playwright` igual (por consistencia
    total de "todo `requirements-dev.txt` fijado"), es una objeción
    válida; se optó por no hacerlo para no tomar una decisión de
    contenido que pertenece a otra feature aún sin diseñar.
- **Alcance de `pip-audit` gate limitado a runtime, con paso informativo
  agregado sobre dev**: se decide NO dejar `backend/requirements-dev.txt`
  completamente fuera de cualquier auditoría (que era el hueco señalado
  en `audit-1.md`), pero tampoco convertirlo en gate obligatorio en esta
  iteración. Motivos:
  - Las dependencias de `requirements-dev.txt` no llegan a producción
    (no se instalan en el `Dockerfile`), por lo que una vulnerabilidad
    ahí no es explotable en el sistema desplegado con la misma urgencia
    que una de runtime — de ahí que no sea gate.
  - Sin embargo, `requirements-dev.txt` incluye `playwright`
    (automatización de navegador, superficie no trivial) y, tras esta
    feature, `pip-audit` mismo — dejarlo sin ninguna visibilidad
    contradice el propósito de la feature 18 ("auditoría básica de
    vulnerabilidades"). De ahí el paso informativo (criterio 6): visible
    en cada corrida de CI, sin bloquear el build.
  - No se hace gate obligatorio sobre `requirements-dev.txt` en esta
    iteración porque `playwright` no está fijado a versión exacta (ver
    punto anterior): un gate sobre un árbol con rango abierto sería
    inestable (una vulnerabilidad nueva en una versión de Playwright
    todavía no elegida podría romper CI de forma ajena a esta feature,
    sin que nadie en el repo haya decidido todavía qué versión usar). Una
    vez que la feature 17 fije `playwright`, promover este paso a gate es
    una mejora natural de esa feature o de una futura, no de esta.
- **Política de revisión de excepciones de `pip-audit`**: se exige
  (criterio 5) que la lista de excepciones declare explícitamente, como
  texto verificable, que debe revisarse cada vez que cambie
  `backend/requirements.txt`, no solo una vez al crearla. Se elige no
  automatizar esa revisión con un script propio en esta feature (por
  ejemplo, comparando fecha de última modificación de ambos archivos)
  para no ampliar el alcance de "básica" declarado en `ROADMAP.md`; la
  verificación de que la revisión efectivamente ocurrió queda a cargo del
  reviewer humano de cada PR futura que toque `requirements.txt`, apoyado
  en la política escrita. Si en el futuro se detecta que esto no es
  suficiente, automatizarlo es una mejora de roadmap, no de esta feature.
- **Slug de documentación**: se usa `calidad-ci-supply-chain` (el mismo
  slug del `ROADMAP.md`, sin el número de feature), siguiendo el patrón
  ya usado por features de infraestructura previas no ligadas a un
  servicio/documento OCR específico (`empaquetado-despliegue.md`,
  `extensionn-roadmap.md`, `cierre-operativo-circuito-agentico.md`). No
  se inventa un nombre alternativo.
- **Ejemplo "HTTP" en `docs/usuario/`**: esta feature no agrega ni
  modifica ningún endpoint HTTP. Se interpreta el requisito de "al menos
  un ejemplo de uso HTTP (request + response)" del contrato de
  `AGENTS.md` como equivalente funcional para features sin endpoint: un
  ejemplo concreto de comando + salida esperada, siguiendo el precedente
  ya aceptado en `docs/usuario/extensionn-roadmap.md` (feature de
  infraestructura sin ejemplo HTTP porque no toca la API). Si el reviewer
  considera que el contrato exige literalmente un ejemplo HTTP incluso
  acá, es una objeción válida y debería resolverse agregando, por
  ejemplo, el `GET /api/v1/health` ya documentado en
  `docs/usuario/empaquetado-despliegue.md` como referencia de que el CI
  no rompió el arranque del servicio — decisión que dejo abierta al
  reviewer en vez de forzarla sin necesidad real.
- **`ruleset` de `ruff` y configuración de `mypy` no se prescriben en
  detalle en este spec** (qué reglas exactas activar, qué nivel de
  `mypy`): es una decisión de implementación razonable delegada al
  builder, dentro de los límites de "sin romper el baseline actual" y
  "documentar toda exclusión". Spec ≠ diseño de código; se fija el
  resultado esperado (CI verde, código limpio o exclusiones
  justificadas), no la configuración línea por línea.
- **No se toca `backend/config/services.ini` ni ningún formato de
  configuración de dominio OCR**: la única configuración nueva
  (`pyproject.toml` para tooling) es texto plano (TOML), no JSON,
  consistente con la regla de `AGENTS.md` sobre no usar JSON como
  configuración persistente. Esta regla aplica en origen a la
  configuración de extracción OCR; se respeta igual acá por consistencia
  de stack, aunque `pyproject.toml` no es configuración de dominio OCR.
- **No se toca el motor OCR, el formato `.DATA`/`services.ini` ni la
  separación OCR/extracción/validación/storage**: confirmado, ninguna
  decisión de esta feature reabre ADR-006 ni ADR-007 de
  `docs/tecnica/arquitectura.md`.
