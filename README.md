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

Ejecutar backend:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Validar estructura:

```powershell
python scripts/validate_project.py
```

## Reglas principales

- No trabajar directo en `main`.
- Toda tarea va en rama `feature/*`.
- No versionar `.venv/`.
- No versionar archivos generados en `storage_bridge/ready/`.
- No avanzar sin validar.
- No cambiar arquitectura sin registrar decisión en `governance/decisions.md`.

## Estado actual

Versión base: `0.1.0`.

Esta versión ordena la estructura y deja preparado el proyecto para avanzar con OCR real, bridge atómico, frontend móvil y versionado profesional.