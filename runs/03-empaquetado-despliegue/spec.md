# Spec: Empaquetado y Despliegue Docker

## Alcance

Empaquetar el sistema (backend FastAPI que sirve además el frontend
estático en el mismo origen, ver `README.md`) en una imagen Docker
reproducible, para que un usuario pueda llevarlo a probar a distintos
clientes corriendo `docker compose up` (o `docker run` equivalente) en su
propio equipo o en un servidor propio que administra, sin instalar
Python/venv/dependencias a mano.

**Decisión de infraestructura fija, no negociable en esta ronda del
circuito (dato de entrada del dueño del producto):** destino de
despliegue = servidor/equipo propio del usuario, con Docker. Sin PaaS
(Railway/Render/Fly.io), sin Kubernetes ni otro orquestador. El
`reviewer-agent` puede objetar el resto de las decisiones técnicas de
este spec, pero no esta.

Incluye:

- `Dockerfile` en la raíz del repo: imagen del backend FastAPI (sirve
  también `frontend/` por `StaticFiles`, mismo origen), instalación de
  `backend/requirements.txt` **excluyendo** `easyocr`/`torch` (ver
  criterio 3 y "Riesgos/supuestos"), exposición de puerto 8000, comando
  de arranque `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`.
- `.dockerignore`: excluye lo mismo que `.gitignore` excluye de
  `storage_bridge/{inbound,ready,failed}/`, más `.venv/`, `.git/`,
  `runs/`, artefactos de test/benchmark y datos privados, para que el
  contexto de build no filtre comprobantes reales ni infle la imagen.
- Persistencia vía volumen montado desde el host para **los tres**
  directorios de estado runtime identificados en el repo real (no solo
  `storage_bridge/`, ver "Contexto"): `storage_bridge/`, `output/`
  (estado de jobs) e `inbound/` de raíz (watcher).
- `backend/config/services.ini` montado como bind mount de archivo
  individual (config externa, no horneada en la imagen), para poder
  ajustar campos/regex por cliente sin reconstruir la imagen.
- `docker-compose.yml` en la raíz: un comando (`docker compose up -d`)
  levanta el sistema completo con los volúmenes y el mapeo de puerto ya
  resueltos, usando rutas relativas al repo para que funcione igual en
  Windows (Docker Desktop) y Linux (Docker Engine).
- `.github/workflows/release.yml`: build + publish de la imagen a GitHub
  Container Registry (`ghcr.io`), disparado únicamente por push de tag
  `v*` (no en cada commit; el humano tagea manualmente después de
  mergear a `main`, ver `ROADMAP.md` sección Versionado), usando
  `GITHUB_TOKEN` con permiso `packages: write` (sin secret adicional).
- `docs/tecnica/empaquetado-despliegue.md` y
  `docs/usuario/empaquetado-despliegue.md` (obligatorios por circuito).
- Actualización de `docs/tecnica/arquitectura.md`, sección "Nota sobre
  release/despliegue": pasa a describir el estado real (existe
  Dockerfile/compose/release.yml) y se formaliza como **ADR-009**, no
  como nota suelta desactualizada.

**Explícitamente NO incluye:**

- PaaS gestionado, Kubernetes u otro orquestador (dato fijo de entrada,
  ver arriba).
- Autenticación, TLS/HTTPS o reverse proxy delante del contenedor — se
  documenta como recomendación operativa del usuario en
  `docs/usuario/empaquetado-despliegue.md`, no se implementa.
- Resiliencia de la cola de jobs (`JobQueue`/`JobStore`) ante un restart
  del contenedor: el estado en memoria de jobs `processing` puede
  perderse hoy; esta feature no lo resuelve (ver "Casos borde").
- Backup/rotación automática de `storage_bridge/ready/`: sigue siendo
  responsabilidad del sistema legacy consumirlo (ADR-001, sin cambios).
- Garantía de soporte multi-arquitectura (`linux/arm64`): el build se
  garantiza para `linux/amd64` en esta ronda (ver "Riesgos/supuestos").
- Cambiar el motor OCR principal (RapidOCR/ONNX, ADR-006), el formato
  `.DATA`/`services.ini` (ADR-007) o la separación
  OCR/extracción/validación/storage — no se reabre ningún ADR existente.
- Decidir la visibilidad pública/privada del paquete en GHCR: es
  configuración manual humana fuera del circuito agéntico, análoga al
  setup manual de GitHub Pages ya documentado en `AGENTS.md`.

## Contexto

El MVP (`01-captura-ocr-local-agil`, `02-mejora-precision-ocr`) se opera
hoy con `uvicorn backend.app.main:app --reload --host 127.0.0.1 --port
8000` sobre un `.venv` configurado a mano (`README.md`, sección
"Ejecución local"). `ROADMAP.md` (backlog, ítem `03-empaquetado-despliegue`)
y `docs/tecnica/arquitectura.md` (nota final, previa a esta feature)
dejan explícito que empaquetar y definir destino de despliegue está
pendiente de una decisión de infraestructura concreta. Esa decisión ya
existe (ver "Alcance"): el caso de uso real es que el dueño del producto
va a llevar el sistema a probarlo en distintos clientes, en equipos o
servidores que él mismo administra.

Verificado en el código actual (no asumido): el runtime del API
(`backend/app/main.py`) escribe estado persistente en **tres** rutas
distintas relativas a la raíz del repo, no solo en `storage_bridge/`:

1. `storage_bridge/{inbound,ready,failed}/` — integración con el sistema
   externo/legacy (ADR-001, ADR-005). Hoy la usan
   `scripts/demo_mvp_e2e.py` y `scripts/evaluate_ocr_service.py`
   (`backend/app/storage_bridge_writer.py`), no el flujo de jobs del API
   web todavía.
2. `output/` (`JobStore`, `DATA_DIR = BASE_DIR / "output"`): resultados
   de jobs y documentos confirmados por revisión humana
   (`output/jobs/`, `output/confirmed/`).
3. `inbound/` en la raíz del repo (`INBOUND_DIR = BASE_DIR / "inbound"`,
   **distinto** de `storage_bridge/inbound/`): carpeta observada por
   `InboundWatcher` para encolar documentos nuevos automáticamente.

Si el contenedor se recrea (`docker compose down && up`, actualización de
imagen, etc.) y solo `storage_bridge/` estuviera montado como volumen,
se perdería el historial de jobs y la carpeta de watch quedaría vacía en
cada recreación — una regresión operativa real para el caso de uso de
"llevarlo a probar a un cliente" (el cliente esperaría que sus jobs y
confirmaciones previas sigan ahí). Por eso esta feature exige volumen
para los tres directorios, no solo para `storage_bridge/`.

`backend/config/services.ini` es la configuración de extracción por
servicio (ADR-007, texto plano, no JSON). Para el caso de uso de "probar
en distintos clientes" con configuraciones de campos distintas, hornear
esa configuración dentro de la imagen obligaría a reconstruirla por cada
cliente; se decide montarla como archivo externo.

## Criterios de aceptación

1. Existe `Dockerfile` en la raíz del repo. `docker build -t gi-ocr:test .`
   termina con código de salida `0` en un entorno con Docker Engine
   disponible. Usa como base una imagen Python 3.12+ basada en Debian
   (p. ej. `python:3.12-slim`; se descarta Alpine/musl en esta ronda por
   riesgo de romper los wheels binarios de `onnxruntime`/
   `opencv-python-headless`, ver "Riesgos/supuestos"), instala
   `backend/requirements.txt`, copia `backend/` y `frontend/`, y asegura
   (`mkdir -p` o equivalente) la existencia de `storage_bridge/`,
   `output/`, `inbound/` dentro de la imagen para que el contenedor
   arranque incluso sin volúmenes montados (igual que hoy en desarrollo
   local, donde esas carpetas se autocrean si faltan).
2. La imagen expone el puerto 8000 y su `CMD`/`ENTRYPOINT` arranca con
   `--host 0.0.0.0` (no `127.0.0.1`, que solo sirve localhost dentro del
   propio contenedor). Verificable: `docker run -p 8000:8000 gi-ocr:test`
   y luego `GET http://localhost:8000/api/v1/health` responde `200` con
   `"status": "ok"`.
3. La imagen final **no** instala `easyocr` ni `torch` (ADR-006: EasyOCR
   es fallback interno opcional deshabilitado por defecto; no justifica
   el peso de `torch` en una imagen pensada para distribuirse a
   servidores/equipos de cliente). RapidOCR/ONNX Runtime sigue siendo el
   único motor instalado y activo. Verificable:
   `docker run --rm gi-ocr:test python -c "import easyocr"` falla con
   `ModuleNotFoundError`, y `python -c "import rapidocr_onnxruntime"`
   dentro del contenedor no falla.
4. Existe `.dockerignore` en la raíz que excluye al menos: `.venv/`,
   `__pycache__/`, `.git/`, `runs/`, `storage_bridge/inbound/*`,
   `storage_bridge/ready/*`, `storage_bridge/failed/*` (preservando
   `.gitkeep`/`README.md`, igual criterio que `.gitignore`), `output/`,
   `inbound/` de raíz, `_local_samples/`, `e2e_evidence/`,
   `.playwright/`, `site/`, `tests/`, `backend/tests/`. Verificable
   inspeccionando el archivo y confirmando (`docker build` + inspección
   de capas o `docker run ... find /app/storage_bridge`) que la imagen
   no contiene archivos reales de comprobantes.
5. `docker-compose.yml` en la raíz declara volúmenes de host para los
   **tres** directorios de estado identificados en "Contexto":
   `storage_bridge/`, `output/` e `inbound/` (de raíz). El contenido
   escrito en esas rutas sobrevive a `docker compose down` seguido de
   `docker compose up`. Verificable: escribir un archivo de prueba en la
   ruta de host mapeada a `output/` (o `storage_bridge/ready/`) antes de
   recrear el contenedor, confirmar que sigue presente después.
6. `docker-compose.yml` monta `backend/config/services.ini` del host
   como bind mount de archivo hacia la misma ruta que usa
   `services_config.py` en tiempo de ejecución dentro de la imagen
   (`SERVICES_INI`, resuelta como ruta relativa al paquete instalado, no
   por variable de entorno — ver "Casos borde" sobre el riesgo de montar
   un archivo inexistente). Verificable: editar el `services.ini`
   montado en el host, reiniciar el contenedor (sin reconstruir la
   imagen) y confirmar que `backend/app/services_config.py` refleja el
   cambio (por ejemplo, un campo nuevo aparece en la config expuesta o
   usada por extracción).
7. `docker compose up -d` (o `docker compose up`) levanta el sistema
   completo con un solo comando, sin pasos manuales adicionales más allá
   de tener Docker instalado y que existan (o se creen) las carpetas de
   volumen del host. Verificable: correr ese comando y confirmar
   `GET /api/v1/health` responde `200`.
8. Existe `.github/workflows/release.yml`, disparado únicamente por
   `push` de tags que matchean `v*` (`on: push: tags: ['v*']`), distinto
   del trigger de `ci.yml` (push/PR a `develop`/`main`). Construye la
   imagen con el mismo `Dockerfile` de esta feature y la publica en
   `ghcr.io/<owner>/<repo>` usando `GITHUB_TOKEN` con permiso
   `packages: write` (sin secret adicional a configurar por el humano).
   Verificable: revisar la sintaxis/trigger del workflow (`actionlint` o
   inspección manual) y, si se dispone de un tag de prueba en un
   entorno controlado (no en `main` real), confirmar que el workflow
   corre y publica sin error — taggear un release real sigue siendo
   decisión exclusiva del humano (`ROADMAP.md`), esta feature no lo
   hace.
9. Debe existir `docs/tecnica/empaquetado-despliegue.md`, no vacío, con:
   arquitectura de la imagen (capas, base elegida, exclusión de
   EasyOCR/torch con motivo), los tres volúmenes persistentes y por qué,
   la decisión de config montada vs horneada, el pipeline de
   `release.yml`, y troubleshooting de al menos los problemas reales
   identificados en "Casos borde" (bind mount de archivo inexistente,
   wheels de onnxruntime pinneados sin arm64 garantizado).
10. Debe existir `docs/usuario/empaquetado-despliegue.md`, no vacío, con
    el propósito del empaquetado, prerequisitos (Docker Desktop en
    Windows/Mac, Docker Engine en Linux), comandos exactos para levantar
    el contenedor (`docker compose up -d` y/o `docker run` equivalente
    con sus `-v`/`-p`), cómo apuntar los volúmenes de `storage_bridge/` y
    `services.ini`, y al menos un ejemplo de uso HTTP real
    (`GET /api/v1/health`, request + response) contra el contenedor
    recién levantado.
11. `docs/tecnica/arquitectura.md`, sección "Nota sobre release/despliegue",
    se actualiza para dejar de decir "No hay todavía Dockerfile ni
    pipeline de release" y en su lugar describir el estado real,
    formalizado como **ADR-009** (destino de despliegue, Docker sin
    PaaS/orquestador, referencia a
    `docs/tecnica/empaquetado-despliegue.md`).
12. `runs/03-empaquetado-despliegue/decision.md` existe (creado por
    `builder-agent` al cerrar la feature), y hay enlaces exactos en
    `docs/tecnica/index.md` y `docs/usuario/index.md` hacia
    `empaquetado-despliegue.md` con el mismo Título en ambos índices
    (recomendado: **"Empaquetado y Despliegue"**, vía
    `scripts/update-doc-indexes.ps1 03-empaquetado-despliegue "Empaquetado y Despliegue"`).
13. `Assert-FeatureContract` (`scripts/feature-contract.ps1`) pasa para
    `03-empaquetado-despliegue` con el Título elegido, antes de marcar
    `ROADMAP.md` como `[-] READY_FOR_PR`.
14. La suite existente `pytest -v` (`backend/tests/` + `tests/`) sigue en
    verde sin regresiones. Esta feature no debe requerir Docker instalado
    para correr los tests de Python existentes: Docker es infraestructura
    de despliegue adicional, no reemplaza el flujo de desarrollo/test
    local con `.venv` (`README.md`).
15. Si se agregan tests nuevos específicos de esta feature (por ejemplo,
    validar la sintaxis/estructura de `docker-compose.yml` o de
    `release.yml`, o el contrato de rutas de volumen, sin requerir Docker
    Engine), deben poder correr en CI sin Docker disponible, o saltarse
    con motivo explícito y verificable si Docker no está instalado en el
    entorno de ejecución (mismo patrón de skip ya usado en
    `01-captura-ocr-local-agil`/`02-mejora-precision-ocr`, nunca un
    `PASS` inventado).

## Casos borde a contemplar

- **Bind mount de archivo inexistente**: si `backend/config/services.ini`
  no existe todavía en el host al primer `docker compose up`, Docker crea
  un **directorio vacío** en esa ruta dentro del contenedor en vez de
  fallar, y `services_config.py._load_parser()` rompe al intentar
  `cfg.read()` sobre un directorio. La documentación de usuario debe
  instruir explícitamente copiar/crear el `services.ini` del host antes
  del primer arranque (o `docker-compose.yml` debe versionar un
  `backend/config/services.ini` por defecto en el repo para que el bind
  mount siempre tenga un archivo real de origen).
- **Restart del contenedor con jobs en `processing`**: el estado de
  `JobQueue` vive en memoria; si el contenedor se recrea mientras hay
  jobs en curso, ese job puede quedar con estado desactualizado en
  `output/jobs/` sin reanudarse solo. Se documenta como limitación
  conocida (no se resuelve en esta feature, ver "Alcance").
- **Arquitectura de CPU distinta de `amd64`** (Apple Silicon vía Docker
  Desktop, servidores ARM): `rapidocr-onnxruntime==1.2.3` y
  `onnxruntime==1.28.0` están fijados por versión exacta
  (`backend/requirements.txt`, comentario explícito sobre
  incompatibilidad de API interna en versiones más nuevas); no está
  garantizado que existan wheels manylinux para `linux/arm64` en esas
  versiones exactas. El build se garantiza solo para `linux/amd64` en
  esta ronda; soporte ARM queda como riesgo documentado, no como
  criterio de cierre.
- **Windows (Docker Desktop) vs. Linux (Docker Engine) como host**: las
  rutas absolutas de host difieren entre plataformas;
  `docker-compose.yml` debe usar rutas relativas al propio archivo
  (`./storage_bridge`, `./output`, `./inbound`,
  `./backend/config/services.ini`) para funcionar igual en ambos sin
  edición manual.
- **`storage_bridge/{inbound,ready,failed}/` montado vacío en un
  checkout nuevo** (sin las subcarpetas creadas todavía en el host): el
  contenedor debe seguir creándolas si faltan (mismo comportamiento hoy
  con `mkdir(parents=True, exist_ok=True)` en `storage_bridge_writer.py`
  / `inbound_watcher.py` / `job_store.py`), no fallar por carpeta
  ausente.
- **Visibilidad del paquete en GHCR**: por defecto el paquete puede
  heredar la visibilidad (privada) del repositorio. Si una máquina
  cliente necesita `docker pull` sin autenticarse contra GitHub, alguien
  debe hacer el paquete público manualmente — configuración humana única,
  fuera del circuito agéntico (documentar como paso manual, no
  automatizarlo).
- **Tag de git que no matchea `vX.Y.Z`**: `release.yml` no debe publicar
  una imagen con un tag ambiguo si el patrón del tag pusheado no
  corresponde a semver; debe fallar de forma clara en ese caso, no
  publicar silenciosamente.
- **Reconstrucción de imagen sin cambiar `services.ini` horneado por
  defecto**: si el `services.ini` versionado en el repo cambia entre
  releases pero un cliente tiene su propio `services.ini` montado con
  configuración custom, el bind mount del host siempre gana sobre lo
  horneado en la imagen — documentarlo explícitamente para que no se
  asuma que actualizar la imagen actualiza la config de un cliente ya
  desplegado.

## Riesgos / supuestos

- **Decisión de infraestructura fija, no abierta a objeción del
  reviewer** (dato de entrada del dueño del producto, ver "Alcance"):
  destino de despliegue = servidor/equipo propio del usuario con Docker,
  sin PaaS ni orquestador. Se documenta igual como ADR-009 formal en
  `docs/tecnica/arquitectura.md` para dejar trazabilidad, no porque sea
  negociable en esta ronda.
- **Supuesto (decisión de empaquetado, no reapertura de ADR-006):**
  excluir `easyocr`/`torch` de la imagen Docker no cambia el motor OCR
  principal ni reabre ADR-006 — RapidOCR/ONNX sigue siendo el único
  motor instalado y activo dentro y fuera del contenedor. Si en el
  futuro se decide que EasyOCR debe estar disponible como fallback real
  en producción, hará falta una imagen alternativa o un flag de build;
  eso queda fuera de esta feature.
- **Supuesto:** base `python:3.12-slim` (Debian), no Alpine. Se descarta
  Alpine en esta ronda porque `onnxruntime`/`opencv-python-headless`
  suelen depender de wheels manylinux (glibc); usar musl probablemente
  forzaría compilar desde fuente, lo que no vale la pena para el alcance
  de esta feature. Si el `builder-agent` mide lo contrario con evidencia,
  puede objetarlo.
- **Riesgo no medido en este spec (queda para `builder-agent`/QA con
  evidencia real, no un umbral inventado):** tamaño final de la imagen
  Docker. Excluir `torch`/`easyocr` debería reducirlo sensiblemente
  frente a instalar todo `requirements.txt`, pero no hay medición previa
  — el criterio de aceptación 3 exige la exclusión en sí, no un tamaño
  máximo específico.
- **Riesgo aceptado, documentado, no resuelto en esta feature:**
  resiliencia de `JobQueue`/`JobStore` ante restart del contenedor (ver
  "Casos borde"). El estado en memoria de jobs en curso puede perderse;
  no se implementa persistencia/reanudación de cola en esta ronda.
- **Supuesto:** no se agrega autenticación, TLS ni reverse proxy en esta
  feature (el MVP tampoco lo tiene hoy fuera de Docker). Se documenta
  como recomendación operativa en `docs/usuario/empaquetado-despliegue.md`
  (por ejemplo, nginx/Caddy delante si el servidor del cliente está en
  red no confiable), sin implementarlo.
- **Supuesto:** la versión de imagen publicada en GHCR se corresponde
  1:1 con el tag de git `vX.Y.Z` que el humano pushea manualmente
  (`ROADMAP.md`, sección Versionado). `release.yml` no valida en esta
  ronda que el archivo `VERSION` del repo coincida con el tag pusheado;
  una posible desincronización entre ambos queda documentada como riesgo
  menor, no como bloqueante — corregible en una iteración futura si se
  vuelve un problema real.
- **Supuesto:** la visibilidad pública/privada del paquete en GHCR es
  configuración manual humana fuera de este circuito (ver "Casos
  borde"), análoga al setup manual de GitHub Pages ya documentado en
  `AGENTS.md`, sección "Setup manual".
