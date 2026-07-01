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

---

## Estado operativo actual

Última tarea cerrada:
**T2.9 — Integración con pipeline de producción y monitoreo de métricas de campos rechazados.**

Estado: Cerrada, mergeada y pusheada a main.

Feature commit:
`2c4dabf feat(ocr): add rejected data field metrics`

Merge commit:
`613daba merge: integrate rejected field metrics with production pipeline`

Validaciones finales:
- python scripts/validate_project.py: PASS
- pytest -q backend/tests/test_evaluate_ocr_service_data_output.py: 20 passed
- pytest -q: 77 passed, 7 warnings
- git diff --check: sin errores

---

## Tareas T2.x cerradas confirmadas por Git

- **T2.4** — Inventario de documentos/servicios DATA.
- **T2.5** — Integración inventario DATA evaluator.
- **T2.6** — Validación específica por servicio DATA.
- **T2.8** — Validación DATA en salida .DATA.
- **T2.9** — Integración con pipeline de producción y monitoreo de métricas de campos rechazados.

---

## Nota de consistencia

Este roadmap fue reconciliado contra Git después de detectar que la documentación operativa anterior no reflejaba completamente el avance real del repositorio.

---

## Cantidad de tareas restantes

No determinable con precisión hasta definir el siguiente bloque operativo del roadmap posterior a T2.9.
