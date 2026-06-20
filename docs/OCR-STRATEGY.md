# OCR Strategy

## Objetivo

Definir una estrategia simple para avanzar con OCR sin cambiar de motor impulsivamente.

## Estado actual

El código actual usa EasyOCR.

Esta decisión es experimental y debe validarse con evidencia.

## Estrategia por etapas

### Etapa 1 — Validar flujo local

Usar el motor actual para validar:

- carga de imagen;
- lectura OCR;
- extracción por zonas;
- extracción por patrones;
- respuesta del backend;
- generación de salida.

### Etapa 2 — Medir

Registrar para cada imagen:

- tiempo total;
- cantidad de líneas leídas;
- campos encontrados;
- campos no encontrados;
- errores.

### Etapa 3 — Mejorar imagen

Antes de cambiar motor OCR, probar:

- escala;
- contraste;
- conversión a grises;
- recorte por zona;
- guía de encuadre;
- fallback por regex global.

### Etapa 4 — Comparar motores

Comparar:

- EasyOCR;
- Tesseract;
- PaddleOCR;
- Google Document AI;
- Azure Document Intelligence.

## Regla

No se cambia el motor OCR sin una tarea específica y evidencia mínima.

## Criterios de comparación

- precisión;
- velocidad;
- instalación;
- costo;
- privacidad;
- facilidad de mantenimiento;
- compatibilidad con producción.