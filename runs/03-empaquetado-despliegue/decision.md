# Decision: 03-empaquetado-despliegue

## Estado

Implementación `builder-agent` lista para QA. No se marca `ROADMAP.md` y
no se crea PR en esta etapa.

## Evidencia De Entrada

- `runs/03-empaquetado-despliegue/spec.md`: exige `Dockerfile` +
  `.dockerignore` + `docker-compose.yml` + `.github/workflows/release.yml`
  para empaquetar el backend FastAPI en Docker, destino de despliegue
  fijo (servidor/equipo propio, sin PaaS/orquestador), exclusión de
  `easyocr`/`torch`, volúmenes para los tres directorios de estado real
  (`storage_bridge/`, `output/`, `inbound/`), `services.ini` montado no
  horneado, y documentación técnica/usuario + ADR-009.
- `runs/03-empaquetado-despliegue/audit-1.md`: `approved` en intento 1,
  sin observaciones bloqueantes. Nota menor no bloqueante: el mecanismo
  para excluir `easyocr`/`torch` del build queda a criterio del
  `builder-agent`.

## Decisiones Tomadas

- **Exclusión de `easyocr`/`torch` en el build**: se filtra la línea
  `easyocr` de `backend/requirements.txt` en tiempo de build dentro del
  propio `Dockerfile` (`grep -v -E '^easyocr' /tmp/requirements.txt >
  /tmp/requirements-docker.txt`), en vez de mantener un
  `requirements-docker.txt` versionado aparte. Motivo: un solo archivo de
  dependencias como fuente de verdad, sin riesgo de que ambos archivos se
  desincronicen en un cambio futuro de `requirements.txt`. `torch` no
  está declarado explícitamente en `requirements.txt`: es dependencia
  transitiva de PyPI de `easyocr`, así que al no instalar `easyocr`
  tampoco se instala `torch`.
- **Base de imagen**: `python:3.12-slim` (Debian), tal como fija el spec.
  Se agregan `libglib2.0-0`/`libgl1` como dependencias de sistema mínimas
  en runtime (requeridas por `opencv-python-headless`), sin herramientas
  de compilación — no hace falta compilar nada porque los wheels
  manylinux de `onnxruntime`/`opencv-python-headless` corren sobre glibc.
- **`WORKDIR /app`**: fija la ruta de `services.ini` en runtime a
  `/app/backend/config/services.ini`, que es exactamente el bind mount
  que declara `docker-compose.yml`. Se verificó leyendo
  `backend/app/services_config.py` (no asumido): `SERVICES_INI =
  CONFIG_DIR / "services.ini"`, `CONFIG_DIR = Path(__file__).resolve()
  .parents[1] / "config"` — resuelto por ruta relativa al paquete
  copiado dentro de la imagen (`backend/app/services_config.py` →
  `parents[1]` = `backend/` → `backend/config/`), no por variable de
  entorno.
- **Los tres volúmenes**: `docker-compose.yml` monta `./storage_bridge`,
  `./output`, `./inbound` (más `./backend/config/services.ini` como
  bind mount de archivo), confirmando en el código real
  (`backend/app/main.py`, líneas 33-35) que `DATA_DIR = BASE_DIR /
  "output"` e `INBOUND_DIR = BASE_DIR / "inbound"` son rutas runtime
  distintas de `storage_bridge/`.
- **`services.ini` versionado en el repo**: se confirmó con `git ls-files
  backend/config/` que `backend/config/services.ini` ya está commiteado
  (no está en `.gitignore`), así que el bind mount de archivo individual
  siempre tiene una fuente real en un checkout normal — mitiga
  directamente el caso borde de "bind mount de archivo inexistente" del
  spec sin necesitar lógica adicional.
- **`.dockerignore`**: replica las mismas exclusiones que `.gitignore`
  para `storage_bridge/{inbound,ready,failed}/*` (preservando
  `.gitkeep`/`README.md`), más `.venv/`, `.git/`, `runs/`, `output/`,
  `/inbound/`, `_local_samples/`, `e2e_evidence/`, `.playwright/`,
  `site/`, `tests/`, `backend/tests/`, `_bench/`, `_ocr_reports/`.
  También excluye el propio `Dockerfile`/`.dockerignore`/
  `docker-compose.yml` del contexto copiado (no hace falta que viajen
  dentro de la imagen).
- **`release.yml`**: trigger exclusivo `on: push: tags: ['v*']`, permisos
  mínimos (`contents: read`, `packages: write`), autenticación solo con
  `secrets.GITHUB_TOKEN` (sin secret adicional), validación explícita de
  que el tag matchea `^v[0-9]+\.[0-9]+\.[0-9]+$` antes de construir/
  publicar nada (falla con `exit 1` y mensaje claro si no matchea, en vez
  de publicar con un tag ambiguo), normalización a minúsculas del nombre
  de imagen (`ghcr.io/<owner>/<repo>`, requerido por GHCR aunque el
  nombre del repo de GitHub tenga mayúsculas), y publica dos tags: el tag
  de git exacto y `latest`.
- **ADR-009**: reemplaza la sección "Nota sobre release/despliegue" de
  `docs/tecnica/arquitectura.md` por un ADR formal, sin reabrir ADR-006
  (motor OCR) ni ADR-007 (config texto plano) — ambos se citan como
  contexto, no se modifican.

## Verificación Real Ejecutada (no inventada)

- **`pytest -v` (`backend/tests/` + `tests/`), corrido en el worktree**
  (`D:\proyectos\worktrees\03-empaquetado-despliegue`) reutilizando el
  `.venv` del checkout principal
  (`/d/proyectos/gi-ocr/.venv/Scripts/python.exe -m pytest -v`):
  resultado real **`228 passed, 6 skipped, 31 warnings in 440.80s`**, sin
  fallos. Los 6 `skip` son los esperados (muestras privadas locales
  gitignored y Playwright no instalado), mismo patrón que features
  previas. Nota de entorno: la primera corrida sin `--basetemp` falló con
  77 `ERROR` por un `PermissionError: [WinError 5] Acceso denegado` sobre
  `C:\Users\jlbel\AppData\Local\Temp\pytest-of-jlbellon` — se confirmó
  que es un problema preexistente del entorno del equipo (no introducido
  por esta feature) reproduciéndolo también en el checkout principal
  (`develop`, sin cambios de esta rama) con el mismo error exacto. Se usó
  `--basetemp` apuntando a una carpeta de scratch propia para evitar ese
  directorio bloqueado y obtener la corrida real completa.
- **Validación de sintaxis YAML real** (no visual): `python -c "import
  yaml; yaml.safe_load(open('docker-compose.yml'))"` y lo mismo para
  `.github/workflows/release.yml` — ambos parsean sin error. No había
  `actionlint` disponible en este entorno (`which actionlint` → no
  encontrado) para una validación de sintaxis de Actions más estricta.
- **Build/run Docker real: NO se pudo ejecutar en este entorno.** Se
  intentó `docker build -t gi-ocr:test .` desde el worktree; el CLI
  `docker` está instalado (`docker --version` → `Docker version 29.7.2`)
  pero el daemon/engine de Docker Desktop no está corriendo en esta
  sesión: `docker info`/`docker ps`/`docker build` fallan todos con el
  mismo error real:
  ```
  ERROR: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine;
  check if the path is correct and if the daemon is running: open
  //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
  ```
  Se confirmó con `Get-Service com.docker.service` que el servicio está
  `Stopped`, y `Start-Service com.docker.service` falló por falta de
  permisos (`No se puede abrir el servicio com.docker.service`) — el
  entorno de ejecución del `builder-agent` no tiene privilegios para
  iniciar el servicio de Windows de Docker Desktop. No se afirma en
  ningún documento de esta feature que el build/`docker compose up` haya
  corrido con éxito; queda pendiente que QA o el humano lo verifiquen en
  un entorno con el daemon de Docker disponible y corriendo. Los criterios
  de aceptación 1-3, 5-7 del spec (que exigen `docker build`/`docker
  run`/`docker compose up` reales) **no están verificados con evidencia
  real en este intento** por esta limitación de entorno, no por un fallo
  del `Dockerfile`/`docker-compose.yml` en sí.
- **`Assert-FeatureContract`**: corrido vía
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
  .\scripts\feature-contract.ps1` (ver detalle de resultado más abajo,
  sección "Contrato de feature").
- **`update-doc-indexes.ps1`**: corrido con
  `03-empaquetado-despliegue "Empaquetado y Despliegue"`, agrega los
  enlaces exactos en `docs/tecnica/index.md` y `docs/usuario/index.md`.

## Riesgo Documentado, No Resuelto En Esta Feature

- Docker no pudo probarse de punta a punta en este intento por la
  limitación de entorno descrita arriba (daemon detenido, sin permisos
  para iniciarlo). El `Dockerfile`/`docker-compose.yml`/`release.yml` se
  construyeron leyendo con cuidado el código real (`main.py`,
  `services_config.py`, `job_store.py`, `inbound_watcher.py`,
  `storage_bridge_writer.py`) para que las rutas y el comportamiento
  coincidan, y se validó su sintaxis YAML, pero el `qa-agent` o el humano
  deben confirmar el build/run real en un entorno con Docker Engine
  disponible antes de dar por cerrados los criterios 1-3 y 5-7 del spec.
- Soporte `linux/arm64` sigue sin garantía (documentado en
  `docs/tecnica/empaquetado-despliegue.md`, no resuelto, tal como fija el
  spec).
- Resiliencia de `JobQueue` ante restart del contenedor: sin cambios,
  documentado como limitación conocida (spec, "Explícitamente NO
  incluye").

## Alcance No Modificado

- No se reabrió ADR-006 (motor OCR: RapidOCR/ONNX sigue siendo el único
  motor activo dentro y fuera del contenedor).
- No se reabrió ADR-007 (config texto plano: `services.ini` sigue en INI,
  sin cambios de formato).
- No se agregó autenticación, TLS ni reverse proxy.
- No se creó ningún tag de git (`vX.Y.Z`) — decisión exclusiva del
  humano.
- No se tocó `ROADMAP.md` más allá de lo que ya traía `develop`.
- No se hizo push ni se creó PR.

## Contrato de feature

Resultado real de `Get-FeatureContractStatus -Slug
'03-empaquetado-despliegue' -Title 'Empaquetado y Despliegue'`
(`scripts/feature-contract.ps1`), corrido desde el worktree: el único
problema reportado es `Falta al menos un test-report-N.md en
runs/03-empaquetado-despliegue.` — artefacto que produce el `qa-agent` en
la próxima etapa del circuito, no el `builder-agent`. El resto del
contrato (spec.md, `decision.md` no vacío, `docs/tecnica/
empaquetado-despliegue.md` y `docs/usuario/empaquetado-despliegue.md` no
vacíos, `audit-1.md`, enlaces exactos en ambos índices con el título
"Empaquetado y Despliegue") pasa sin problemas.

## Artefactos

- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `.github/workflows/release.yml`
- `docs/tecnica/empaquetado-despliegue.md`
- `docs/usuario/empaquetado-despliegue.md`
- `docs/tecnica/arquitectura.md` (ADR-009, reemplaza la nota final)
- `runs/03-empaquetado-despliegue/decision.md`
