# Roadmap del Proyecto

Este roadmap define el avance por fases pequeñas. No se debe avanzar a una fase posterior si la fase actual no está validada.

## Fase 0 — Baseline controlado

Objetivo: dejar el proyecto limpio, versionable y gobernado.

Tareas:

- [x] Crear estructura base simple.
- [x] Crear `GOVERNANCE.md`.
- [x] Crear `CONTRIBUTING.md`.
- [x] Crear `VERSION`.
- [x] Crear `CHANGELOG.md`.
- [x] Crear `docs/`.
- [ ] Ejecutar `scripts/validate_project.py`.
- [ ] Crear commit baseline aprobado.

Criterio de cierre:

```powershell
python scripts/validate_project.py
git status --short
```

## Fase 1 — OCR baseline con imagen fixture

Objetivo: procesar una imagen conocida y extraer campos mínimos.

Tareas:

- [ ] Confirmar fixture de prueba `gas_sample.jpg`.
- [ ] Corregir dependencias OCR.
- [ ] Crear prueba mínima para GAS.
- [ ] Medir tiempo de procesamiento.
- [ ] Documentar limitaciones.

Criterio de cierre:

```powershell
pytest backend/tests
```

## Fase 2 — Bridge de salida controlado

Objetivo: generar archivos de salida sin riesgo de lectura parcial.

Tareas:

- [ ] Implementar escritura en `storage_bridge/inbound/*.tmp`.
- [ ] Validar payload.
- [ ] Mover con `os.replace` a `storage_bridge/ready/`.
- [ ] Crear test de escritura atómica.

## Fase 3 — Frontend móvil mínimo

Objetivo: capturar imagen desde celular y mostrar resultados.

Tareas:

- [ ] Corregir carga de servicios.
- [ ] Permitir selección manual de servicio.
- [ ] Mostrar vista previa de imagen.
- [ ] Mostrar campos extraídos.
- [ ] Mostrar errores claros.

## Fase 4 — Mejora de precisión OCR

Objetivo: mejorar captura y extracción.

Tareas:

- [ ] Preprocesamiento de imagen.
- [ ] Recorte o guía visual.
- [ ] Fallback por regex global.
- [ ] Métrica simple de confianza.

## Fase 5 — Evaluación de motor OCR

Objetivo: decidir motor OCR con evidencia.

Opciones a comparar:

- EasyOCR
- Tesseract
- PaddleOCR
- Google Document AI
- Azure Document Intelligence

Criterios:

- Precisión.
- Velocidad.
- Costo.
- Facilidad de instalación.
- Privacidad.
- Mantenimiento.
