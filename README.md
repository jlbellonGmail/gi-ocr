# Smart Invoice Capture

Sistema MVP para capturar una imagen de un comprobante desde el celular, enviarla a un backend OCR, extraer campos relevantes y generar una salida validada para integración posterior con un sistema externo o legacy.

## Objetivo del MVP

El MVP inicial se limita a:

1. Capturar o cargar una imagen desde el frontend web móvil.
2. Enviar la imagen al backend FastAPI.
3. Procesar OCR sobre un comprobante conocido.
4. Extraer campos configurados por servicio.
5. Mostrar el resultado al usuario.
6. Generar una salida controlada en `storage_bridge/`.

## Alcance inicial

El primer comprobante objetivo es `GAS`.

Campos iniciales:

- n° cliente
- nro medidor
- periodo
- a pagar hasta
- importe

## Arquitectura simple

```text
frontend/
  index.html
  src/app.js

backend/
  app/main.py
  app/ocr.py
  config/services.ini

storage_bridge/
  inbound/
  ready/
  failed/
```

## Ejecución local

Crear entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Ejecutar backend + frontend (un solo comando, mismo origen):

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Correr tests:

```powershell
pytest
```

## Circuito de desarrollo (AI-Native)

Este proyecto se desarrolla con el circuito agéntico definido en
[AGENTS.md](AGENTS.md): Analyst → Reviewer → Builder → QA →
`ROADMAP.md [-]` → PR → CI verde → HITL (único punto de aprobación
humana: `MERGE`/`NO MERGE`) → Merge → `ROADMAP.md [x]`. Ver también
[ROADMAP.md](ROADMAP.md) y [docs/index.md](docs/index.md).

## Reglas principales

- No trabajar directo en `main` ni en `develop`.
- Toda tarea va en rama `feature/<NN>-<slug>` (ver `AGENTS.md`).
- No versionar `.venv/`.
- No versionar archivos generados en `storage_bridge/{inbound,ready,failed}/`.
- No avanzar sin validar (tests reales, no evidencia inventada).
- No cambiar arquitectura sin registrar la decisión en
  `docs/tecnica/arquitectura.md`.

## Estado actual

Ver [ROADMAP.md](ROADMAP.md) para el estado real verificado (qué está
cerrado, qué está en curso, próxima etapa hacia el MVP operable).