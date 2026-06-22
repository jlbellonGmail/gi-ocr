# Architecture Decisions

Este archivo registra decisiones técnicas del proyecto.

No contiene reglas operativas. Las reglas operativas están en `GOVERNANCE.md`.

## ADR-001 — Integración con sistema externo por filesystem

Estado: aceptada.

El sistema se integrará con el sistema externo o legacy mediante archivos en `storage_bridge/`.

Motivo:

- Reduce acoplamiento.
- Evita dependencias directas con procesos legacy.
- Permite depurar entradas y salidas.
- Facilita una primera integración simple para MVP.

## ADR-002 — Backend principal con FastAPI

Estado: aceptada.

El backend principal será Python con FastAPI.

Motivo:

- Permite API simple para carga de imágenes.
- Tiene buen soporte para procesamiento asíncrono.
- Es adecuado para integrar OCR y scripts Python.

## ADR-003 — Frontend web mobile-first

Estado: aceptada.

El frontend inicial será HTML y JavaScript simple.

Motivo:

- Permite capturar imágenes desde celular sin aplicación nativa.
- Reduce complejidad inicial.
- Evita frameworks innecesarios durante el MVP.

## ADR-004 — MVP con un comprobante inicial

Estado: aceptada.

El primer MVP se enfocará en un comprobante `GAS`.

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

Estado: pendiente de implementación.

La salida final deberá escribirse primero como archivo temporal y luego moverse de forma atómica a `storage_bridge/ready/`.

Motivo:

- Evita que otro proceso lea archivos incompletos.
- Hace más segura la integración con sistemas externos.

Nota:

La existencia de esta decisión no significa que ya esté implementada. Su implementación corresponde a una tarea futura del roadmap.

## ADR-006 — Motor OCR actual

Estado: experimental.

El código actual usa EasyOCR.

Motivo:

- Ya existe implementación inicial.
- Permite validar flujo local.

Pendiente:

- Medir precisión.
- Medir velocidad.
- Comparar contra Tesseract, PaddleOCR, Google Document AI y Azure Document Intelligence.

---

## ADR-007 — Modelo configurable de extracción de texto plano

Estado: aceptada.

Las reglas de extracción OCR se definen en un archivo INI plano (`backend/config/services.ini`), no JSON. La salida legacy se genera en archivos `.DATA` con nombre `SERVICIO_YYYYMMDD_HHMMSS.DATA`.

Motivo:

- Evita proliferación de extractores Python por servicio.
- Hace que la adición de servicios sea solo un cambio de configuración.
- Sigue el principio de separación estructural: lógica genérica, definición por configuración.

Reglas:

- La configuración vive en `backend/config/services.ini`.
- La salida legacy es un archivo plano `.DATA` con nombre `SERVICIO_YYYYMMDD_HHMMSS.DATA`.
- El contenido: primera línea con nombres de campos separados por `;`, segunda línea en adelante con valores extraídos, separado por `;`.
- No usar `json` como contrato persistente ni como salida legacy.
- No crear extractores Python por servicio; todos los servicios deben trabajar con el mismo motor genérico.
- Futuro CRUD sobre servicios, campos y reglas será posible solo por modelo conceptual.