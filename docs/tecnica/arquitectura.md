# Arquitectura

Decisiones de arquitectura de gi-ocr, migradas desde el antiguo
`governance/decisions.md` (ADR-001 a ADR-008) al adoptar el circuito
agéntico de `AGENTS.md`. El contenido es el mismo; solo cambió dónde vive.

## ADR-001 — Integración con sistema externo por filesystem

Estado: aceptada.

El sistema se integra con el sistema externo/legacy mediante archivos en
`storage_bridge/` (`inbound/`, `ready/`, `failed/`).

Motivo:

- Reduce acoplamiento.
- Evita dependencias directas con procesos legacy.
- Permite depurar entradas y salidas.
- Facilita una primera integración simple para MVP.

## ADR-002 — Backend principal con FastAPI

Estado: aceptada.

El backend principal es Python con FastAPI (`backend/app/main.py`).

Motivo:

- Permite API simple para carga de imágenes.
- Tiene buen soporte para procesamiento asíncrono.
- Es adecuado para integrar OCR y scripts Python.

## ADR-003 — Frontend web mobile-first

Estado: aceptada.

El frontend (`frontend/`) es HTML y JavaScript simple, servido por FastAPI
(`StaticFiles`) en el mismo origen que la API.

Motivo:

- Permite capturar imágenes desde celular sin aplicación nativa.
- Reduce complejidad inicial.
- Evita frameworks innecesarios durante el MVP.

## ADR-004 — MVP con un comprobante inicial

Estado: aceptada.

El primer MVP se enfoca en un comprobante `GAS` (ver
[docs/usuario/gas.md](../usuario/gas.md)).

Campos iniciales:

- n° cliente
- nro medidor
- periodo
- a pagar hasta
- importe

Motivo:

- Reduce alcance.
- Permite medir OCR con un caso concreto.
- Evita intentar resolver todos los comprobantes desde el inicio.

## ADR-005 — Escritura atómica del bridge

Estado: implementada (`backend/app/storage_bridge_writer.py`).

La salida final se escribe primero como archivo temporal y luego se mueve
de forma atómica a `storage_bridge/ready/`.

Motivo:

- Evita que otro proceso lea archivos incompletos.
- Hace más segura la integración con sistemas externos.

## ADR-006 — Motor OCR

Estado: **resuelta** (feature `01-captura-ocr-local-agil`, ver
[docs/tecnica/captura-ocr-local-agil.md](captura-ocr-local-agil.md)).

Motor principal: **RapidOCR (PP-OCRv3) + ONNX Runtime**, con arquitectura
two-pass ROI-focalizada. Reemplaza a EasyOCR, que queda declarado en
`backend/requirements.txt` como fallback interno opcional deshabilitado
por defecto (no se elimina).

Evidencia medida:

- EasyOCR: ~30 s/documento (motor previo, `backend/app/ocr.py`).
- RapidOCR/ONNX two-pass ROI: **2.35–2.57 s en caliente** por documento.
- PaddleOCR PP-OCR Mobile: evaluado y descartado — sin wheel disponible
  para Python 3.14 en el entorno de desarrollo (`pip install paddlepaddle`
  → `No matching distribution found`).
- Tesseract, Google Document AI, Azure Document Intelligence: no
  evaluados en esta ronda (RapidOCR/ONNX ya cumplió el objetivo de
  rendimiento local sin costo por página; no había necesidad de seguir
  comparando motores cloud pagos para un requisito 100% local).

Licencias verificadas: RapidOCR Apache-2.0, onnxruntime MIT — ambas
compatibles con uso local sin costo por página ni egress de documentos.

## ADR-007 — Modelo configurable de extracción de texto plano

Estado: aceptada.

Las reglas de extracción OCR se definen en un archivo INI plano
(`backend/config/services.ini`), no JSON. La salida legacy se genera en
archivos `.DATA` con nombre `SERVICIO_YYYYMMDD_HHMMSS.DATA`.

Motivo:

- Evita proliferación de extractores Python por servicio.
- Hace que la adición de servicios sea solo un cambio de configuración.
- Sigue el principio de separación estructural: lógica genérica,
  definición por configuración.

Reglas:

- La configuración vive en `backend/config/services.ini`.
- La salida legacy es un archivo plano `.DATA` con nombre
  `SERVICIO_YYYYMMDD_HHMMSS.DATA`.
- El contenido: primera línea con nombres de campos separados por `;`,
  segunda línea en adelante con valores extraídos, separado por `;`.
- No usar JSON como contrato persistente ni como salida legacy.
- No crear extractores Python por servicio; todos los servicios trabajan
  con el mismo motor genérico.

## ADR-008 — Estrategia de ramas para etapas funcionales

Estado: aceptada; reemplazada operativamente por el modelo de
`feature/<NN>-<slug>` + worktrees de `AGENTS.md` para features nuevas.

Reglas vigentes:

- `main` → estable. Solo recibe merges validados.
- `develop` → integración. Base para crear ramas `feature/*`.
- `feature/*` → una etapa funcional por rama, en worktree propio para
  features iniciadas bajo el circuito de `AGENTS.md`.
- Las features previas a la adopción del circuito (p. ej.
  `feature/t4-mvp-web-operable`) no se renombran retroactivamente al
  esquema `<NN>-<slug>`; se cierran con su nombre actual (ver
  `ROADMAP.md`, sección Historial).

## ADR-009 — Empaquetado Docker y pipeline de release

Estado: **resuelta** (feature `03-empaquetado-despliegue`, ver
[docs/tecnica/empaquetado-despliegue.md](empaquetado-despliegue.md)).

Destino de despliegue: **servidor o equipo propio del usuario, con
Docker**. Sin PaaS gestionado (Railway/Render/Fly.io), sin Kubernetes ni
otro orquestador — dato de entrada fijo del dueño del producto para el
caso de uso real (llevar el sistema a probar a distintos clientes en
equipos que ellos mismos administran).

Implementación:

- `Dockerfile` en la raíz: imagen `python:3.12-slim` (Debian, no Alpine,
  por los wheels manylinux de `onnxruntime`/`opencv-python-headless`),
  instala `backend/requirements.txt` excluyendo `easyocr` (y, por
  arrastre transitivo, `torch`) — RapidOCR/ONNX Runtime sigue siendo el
  único motor OCR instalado y activo, dentro y fuera del contenedor; no
  reabre ADR-006. Copia `backend/` y `frontend/`, asegura los
  directorios de estado runtime, expone el puerto `8000` y arranca con
  `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml`: un servicio, con volúmenes de host (rutas
  relativas) para los **tres** directorios de estado identificados en el
  código real (`storage_bridge/`, `output/`, `inbound/` de raíz — no solo
  el primero), y bind mount de archivo individual para
  `backend/config/services.ini` (ADR-007: configuración externa, no
  horneada, para ajustar campos por cliente sin reconstruir la imagen).
- `.github/workflows/release.yml`: build + publish a
  `ghcr.io/<owner>/<repo>`, disparado únicamente por `push` de tags
  `v*` — nunca en cada commit. El humano tagea manualmente después de
  mergear a `main` (ver `ROADMAP.md`, sección Versionado); los agentes
  nunca crean tags.

Motivo:

- Permite distribuir el sistema sin exigir Python/venv/dependencias
  instaladas a mano en el equipo del cliente.
- Mantiene la imagen liviana para distribución, excluyendo un motor OCR
  fallback (`easyocr`/`torch`) que no se usa en el camino activo.
- Preserva la configurabilidad por cliente de `services.ini` (ADR-007)
  sin acoplarla al ciclo de build de la imagen.
- No introduce infraestructura de orquestación (PaaS/K8s) no solicitada
  para el caso de uso real de esta etapa del producto.

Explícitamente fuera de esta ADR (ver
[docs/tecnica/empaquetado-despliegue.md](empaquetado-despliegue.md) para
el detalle): autenticación/TLS/reverse proxy delante del contenedor,
resiliencia de `JobQueue` ante restart, soporte garantizado
`linux/arm64`, backup/rotación de `storage_bridge/ready/` (sigue siendo
responsabilidad del sistema legacy, ADR-001 sin cambios).
