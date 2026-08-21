# Empaquetado y Despliegue

Empaqueta el backend FastAPI de gi-ocr (que sirve además `frontend/` por
`StaticFiles`, mismo origen) en una imagen Docker reproducible, para
llevarlo a probar a distintos clientes en un servidor o equipo propio que
el usuario administra, sin instalar Python/venv/dependencias a mano.

Decisión de infraestructura fija (dato de entrada del dueño del
producto, no reabierta por esta feature): destino de despliegue = Docker
en servidor/equipo propio, sin PaaS gestionado (Railway/Render/Fly.io)
ni Kubernetes/orquestador. Ver ADR-009 en
[arquitectura.md](arquitectura.md#adr-009--empaquetado-docker-y-pipeline-de-release).

## Arquitectura de la imagen

`Dockerfile` en la raíz del repo, base `python:3.12-slim` (Debian):

1. Instala dependencias de sistema mínimas en tiempo de ejecución
   (`libglib2.0-0`, `libgl1`), requeridas por `opencv-python-headless`
   para operaciones de imagen sin entorno gráfico. No instala
   herramientas de compilación: no hace falta porque no se compila nada
   desde fuente (ver "Por qué se descarta Alpine").
2. Instala `backend/requirements.txt` **excluyendo** la línea `easyocr`
   (ver "Por qué se excluye EasyOCR/torch").
3. Copia `backend/` y `frontend/` (código de aplicación) al `WORKDIR
   /app`.
4. Crea (`mkdir -p`) `storage_bridge/{inbound,ready,failed}`, `output/`
   e `inbound/` dentro de la imagen, para que el contenedor arranque
   incluso sin volúmenes montados — mismo comportamiento que en
   desarrollo local, donde `storage_bridge_writer.py`,
   `job_store.py` (`JobStore.__init__`) e `inbound_watcher.py`
   (`InboundWatcher.__init__`) ya crean esas carpetas con
   `mkdir(parents=True, exist_ok=True)` si faltan.
5. Expone el puerto `8000` y arranca con
   `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` — `0.0.0.0`
   es obligatorio (no `127.0.0.1`, que solo serviría dentro del propio
   contenedor y quedaría inalcanzable desde el mapeo de puerto del host).

### Por qué se descarta Alpine

`onnxruntime` y `opencv-python-headless` distribuyen wheels manylinux
(glibc). Alpine usa musl; instalar esas dependencias ahí forzaría
compilar desde fuente (o no encontrar wheel compatible), lo que no vale
la pena para el alcance de esta feature. `python:3.12-slim` (Debian) usa
glibc y consume los wheels ya publicados sin compilación.

### Por qué se excluye EasyOCR/torch

`backend/requirements.txt` declara `easyocr>=1.7.1`, que a su vez arrastra
`torch` como dependencia transitiva de PyPI (no está listado
explícitamente en `requirements.txt`, pero `pip` lo resuelve igual al
instalar `easyocr`). Desde ADR-006 (`docs/tecnica/arquitectura.md`),
RapidOCR (PP-OCRv3) + ONNX Runtime es el motor OCR principal y EasyOCR
queda como fallback interno **opcional, deshabilitado por defecto** —
nunca se usa en el flujo activo del pipeline. Cargar `torch` en una
imagen pensada para distribuirse a servidores/equipos de cliente no se
justifica: aumenta significativamente el tamaño de la imagen y el tiempo
de build sin beneficio funcional en el camino activo.

El `Dockerfile` filtra la línea `easyocr` del propio
`backend/requirements.txt` en tiempo de build (`grep -v -E '^easyocr'`),
en vez de mantener un segundo archivo `requirements-docker.txt`
duplicado a sincronizar a mano en cada cambio de dependencias. Esto es
una decisión de **empaquetado**, no reabre ADR-006: RapidOCR/ONNX sigue
siendo el único motor instalado y activo, tanto dentro como fuera del
contenedor. Verificado en build real (ver "Verificación"):
`python -c "import easyocr"` falla con `ModuleNotFoundError` dentro de
la imagen, y `python -c "import rapidocr_onnxruntime"` no falla.

Si en el futuro se necesita EasyOCR disponible como fallback real en
producción, hace falta una imagen alternativa o un flag de build — fuera
de esta feature (ver spec, "Riesgos/supuestos").

## Los tres volúmenes persistentes

Verificado en el código real (`backend/app/main.py`, líneas 33-35), el
runtime del API escribe estado persistente en **tres** rutas distintas,
no solo `storage_bridge/`:

| Directorio (host) | Ruta dentro del contenedor | Qué persiste | Por qué falta sin volumen |
|---|---|---|---|
| `./storage_bridge` | `/app/storage_bridge` | Integración por filesystem con el sistema externo/legacy (`inbound/`, `ready/`, `failed/`, ADR-001/ADR-005). | Se pierden los `.DATA` generados y los archivos pendientes de consumir. |
| `./output` | `/app/output` | `JobStore` (`DATA_DIR = BASE_DIR / "output"`): historial de jobs (`output/jobs/`) y documentos confirmados por revisión humana (`output/confirmed/`). | Se pierde el historial de jobs y confirmaciones previas del cliente al recrear el contenedor. |
| `./inbound` | `/app/inbound` | `InboundWatcher` (`INBOUND_DIR = BASE_DIR / "inbound"`, **distinto** de `storage_bridge/inbound/`): carpeta observada para encolar documentos nuevos automáticamente. | Queda vacía en cada recreación; documentos dejados ahí por el cliente para ser observados no sobreviven. |

Si solo se montara `storage_bridge/`, un `docker compose down && up` (o
una actualización de imagen) perdería el historial de jobs y dejaría la
carpeta de watch vacía — una regresión operativa real para el caso de
uso de "llevarlo a probar a un cliente": el cliente esperaría que sus
jobs y confirmaciones previas sigan disponibles. Por eso
`docker-compose.yml` monta los tres, con rutas relativas al propio
archivo (`./storage_bridge`, `./output`, `./inbound`) para funcionar
igual en Windows (Docker Desktop) y Linux (Docker Engine) sin edición
manual de rutas absolutas.

Ninguno de los tres falla si la carpeta de host está vacía en un
checkout nuevo: el contenedor las crea/subcarpeta si faltan, con el
mismo `mkdir(parents=True, exist_ok=True)` que ya usan
`storage_bridge_writer.py`, `inbound_watcher.py` y `job_store.py` en
desarrollo local.

## `services.ini`: montado, no horneado

`backend/config/services.ini` (ADR-007, configuración de extracción por
servicio en texto plano) se monta como **bind mount de archivo
individual** (`./backend/config/services.ini:/app/backend/config/services.ini`
en `docker-compose.yml`), no se hornea fijo dentro de la imagen.

Motivo: el caso de uso real es "probar el sistema en distintos
clientes", cada uno con su propia configuración de campos/regex por
servicio. Hornear `services.ini` en la imagen obligaría a reconstruirla
por cada cliente para cambiar un campo o una zona OCR. Montarlo como
archivo externo permite editar la configuración en el host y reiniciar
el contenedor (sin reconstruir la imagen) para que el cambio tome
efecto.

La ruta de montaje dentro del contenedor (`/app/backend/config/services.ini`)
coincide exactamente con la que resuelve
`backend/app/services_config.py` en tiempo de ejecución:
`SERVICES_INI = CONFIG_DIR / "services.ini"`, donde
`CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"` — resuelto
por ruta relativa al paquete instalado (`/app/backend/app/services_config.py`
→ `parents[1]` = `/app/backend` → `/app/backend/config`), **no** por
variable de entorno. El `Dockerfile` fija `WORKDIR /app` y copia
`backend/` completo (incluyendo `backend/config/services.ini` versionado
en el repo) antes de que el bind mount lo reemplace en runtime, así que
la ruta siempre existe con contenido real como fuente del mount, incluso
antes de que el usuario decida sobrescribirla con su propia copia (ver
"Troubleshooting").

**Importante:** el bind mount del host siempre gana sobre lo horneado en
la imagen. Si el `services.ini` versionado en el repo cambia entre
releases pero un cliente tiene su propio archivo montado con
configuración custom, actualizar la imagen (`docker pull` + recrear el
contenedor) **no** actualiza la configuración de ese cliente — el
archivo del host sigue siendo la fuente de verdad. Si se necesita
propagar un cambio de `services.ini` por defecto a un cliente ya
desplegado, hay que copiar el archivo actualizado a mano a la ruta
montada en su host.

## Pipeline de `release.yml`

`.github/workflows/release.yml`:

- Trigger: `on: push: tags: ['v*']` — **nunca** en cada commit ni en
  push/PR a `develop`/`main` (eso lo cubre `ci.yml`, sin overlap). El
  humano tagea manualmente después de mergear a `main`
  (`git tag vX.Y.Z && git push origin vX.Y.Z`, ver `AGENTS.md`, sección
  Versionado) — los agentes nunca crean tags.
- Valida explícitamente que el tag pusheado matchea el patrón semver
  `^v[0-9]+\.[0-9]+\.[0-9]+$` antes de construir o publicar nada; si no
  matchea, el job falla con `exit 1` y un mensaje claro
  (`::error::Tag '<tag>' no matchea el patrón semver vX.Y.Z...`) — evita
  publicar una imagen con un tag ambiguo (ver "Casos borde" del spec).
- Login en `ghcr.io` vía `docker/login-action`, usando
  `${{ secrets.GITHUB_TOKEN }}` (token efímero de Actions, sin secret
  adicional a configurar por el humano) con permiso `packages: write`
  declarado en el bloque `permissions:` del workflow.
- Build + push con `docker/build-push-action`, usando el mismo
  `Dockerfile` de esta feature, contra
  `ghcr.io/<owner>/<repo>` (nombre de imagen en minúsculas, requerido por
  GHCR — `github.repository` se normaliza con `tr '[:upper:]' '[:lower:]'`
  porque GHCR no acepta mayúsculas en el path de la imagen aunque el
  nombre del repo de GitHub las tenga). Publica dos tags: el tag de git
  exacto (`vX.Y.Z`) y `latest`.

La visibilidad pública/privada del paquete en GHCR es configuración
manual humana fuera de este circuito, análoga al setup manual de GitHub
Pages ya documentado en `AGENTS.md` — por defecto el paquete hereda la
visibilidad (privada) del repositorio; si una máquina cliente necesita
`docker pull` sin autenticarse contra GitHub, alguien debe hacer el
paquete público a mano en GitHub (Settings del paquete en GHCR).

Este workflow no valida que el archivo `VERSION` del repo coincida con
el tag de git pusheado — una posible desincronización entre ambos queda
como riesgo menor documentado, no bloqueante (ver spec,
"Riesgos/supuestos").

## Troubleshooting

### Bind mount de `services.ini` inexistente

Si `backend/config/services.ini` no existe en el host al primer
`docker compose up` (por ejemplo, se borró a mano o se apunta a una ruta
distinta sin copiar el archivo), Docker **crea un directorio vacío** en
esa ruta dentro del contenedor en vez de fallar el mount. El backend
rompe al arrancar: `services_config.py._load_parser()` llama a
`cfg.read(SERVICES_INI, ...)` sobre lo que Docker le presenta como un
directorio, no un archivo — `IsADirectoryError`/error de lectura.

Mitigación: el repo versiona `backend/config/services.ini` (no está en
`.gitignore`), así que en un checkout normal del repo el archivo siempre
existe antes del primer `docker compose up`. Si se eliminó o el usuario
apunta el volumen a una ruta fuera del checkout, hay que **crear/copiar
el archivo antes de levantar el contenedor por primera vez** — nunca
dejar que Docker cree el directorio vacío. Si ya ocurrió: `docker compose
down`, borrar el directorio vacío creado por Docker en la ruta de host
(o dentro del volumen anónimo si aplica), asegurar el archivo real, y
`docker compose up` de nuevo.

### `linux/arm64` no garantizado

`rapidocr-onnxruntime==1.2.3` y `onnxruntime==1.28.0` están fijados por
versión exacta en `backend/requirements.txt` (comentario explícito sobre
incompatibilidad de API interna en versiones más nuevas: versiones
posteriores de `rapidocr-onnxruntime` cambian atributos internos
(`text_detector`/`text_recognizer`) de los que depende
`backend/app/ocr_engine.py` para el two-pass ROI-focalizada). No está
garantizado que existan wheels manylinux para `linux/arm64` en esas
versiones exactas (Apple Silicon vía Docker Desktop, servidores ARM). El
build se garantiza solo para `linux/amd64` en esta ronda; si el `pip
install` falla en un host ARM por falta de wheel, la opción es correr el
contenedor bajo emulación `amd64` (más lento) o esperar una futura
revisión de esta feature que evalúe versiones de `rapidocr-onnxruntime`/
`onnxruntime` con soporte ARM real, sin romper el two-pass ROI (ver
ADR-006).

### Restart con jobs en `processing`

El estado de `JobQueue` vive en memoria de proceso, no persiste en
`output/jobs/` de forma continua durante el procesamiento. Si el
contenedor se recrea (`docker compose down && up`, actualización de
imagen) mientras hay jobs en estado `processing`, ese job puede quedar
con estado desactualizado sin reanudarse solo. Limitación conocida, no
resuelta en esta feature (ver spec, "Casos borde" y "Explícitamente NO
incluye") — el usuario debe reintentar la carga de esos documentos
manualmente tras un restart.

### Windows (Docker Desktop) vs. Linux (Docker Engine) como host

Las rutas absolutas de host difieren entre plataformas. `docker-compose.yml`
usa exclusivamente rutas relativas al propio archivo (`./storage_bridge`,
`./output`, `./inbound`, `./backend/config/services.ini`), así que
`docker compose up` funciona igual en ambos sistemas operativos sin
edición manual de rutas.

### Docker CLI presente sin daemon corriendo (`npipe` / Docker Desktop)

En Windows, el CLI `docker` puede estar instalado (`docker --version`
responde) sin que el servicio `com.docker.service` (Docker Desktop
Engine) esté corriendo. Cualquier comando que hable con el daemon
(`docker build`, `docker run`, `docker info`, `docker ps`) falla con:

```
ERROR: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine:
check if the path is correct and if the daemon is running
```

Solución: abrir Docker Desktop (o `Start-Service com.docker.service` con
permisos de administrador) y esperar a que el ícono de la bandeja indique
"Engine running" antes de reintentar. Ver "Verificación real de esta
feature" para el detalle de qué se pudo y no se pudo correr durante el
desarrollo.

## Verificación real de esta feature

El `Dockerfile`, `.dockerignore` y `docker-compose.yml` de esta feature
**no pudieron construirse ni ejecutarse realmente** durante el desarrollo:
el entorno de ejecución del `builder-agent` tenía el CLI `docker`
instalado pero el servicio `com.docker.service` (Docker Desktop Engine)
detenido, sin permisos para iniciarlo (`Start-Service` falló por falta de
privilegios). Evidencia exacta del intento, el error real obtenido y el
resultado de `pytest -v` (sin depender de Docker) queda documentada en
`runs/03-empaquetado-despliegue/decision.md` — no se afirma acá ni ahí
que el build funcionó, porque no se corrió de verdad. Queda pendiente que
QA o el humano confirmen el build/`docker compose up` en un entorno con
el daemon de Docker disponible.
