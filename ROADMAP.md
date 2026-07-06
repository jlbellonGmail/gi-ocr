# Roadmap del Proyecto GI-OCR / TGI-OCR — Smart Invoice Capture

Este roadmap es el contrato operativo de alcance, avance y cierre de la primera versión del producto.

No debe usarse solo como lista técnica. Debe indicar con claridad:

- qué producto se está construyendo;
- qué ya está cerrado;
- qué está parcialmente aplicado;
- qué todavía no fue demostrado;
- qué falta para cerrar la V1;
- cuál es la próxima tarea elegible.

---

## Propósito del producto

GI-OCR / TGI-OCR tiene como objetivo capturar comprobantes, impuestos, servicios y documentos empresariales mediante OCR, extraer campos configurables, validarlos semánticamente y generar salidas estructuradas para integración operativa.

El objetivo primario de la primera versión es permitir el siguiente flujo demostrable:

```text
Imagen de impuesto/servicio/comprobante
→ OCR
→ extracción de texto bruto
→ candidatos de campos configurables
→ validación semántica
→ campos aceptados / rechazados / no encontrados
→ salida TXT/.DATA/storage_bridge
→ evidencia auditable del procesamiento
```

La V1 no se considera cerrada solo porque existen tests internos. La V1 se considera cerrada cuando el flujo anterior pueda ejecutarse y demostrarse de forma reproducible.

---

## Alcance de la V1

La V1 debe permitir una demostración controlada de punta a punta con al menos un tipo de documento, impuesto, servicio o fixture representativo.

Incluye:

* carga o captura de imagen de comprobante/impuesto/servicio;
* selección manual o configuración del servicio/documento;
* procesamiento OCR;
* extracción de texto bruto OCR;
* extracción de campos configurables;
* validación semántica de campos;
* diferenciación entre campos aceptados, rechazados y no encontrados;
* generación de salida estructurada;
* escritura segura en `storage_bridge`;
* salida TXT, `.DATA` o equivalente estructurado;
* evidencia mínima para auditoría técnica;
* prueba demostrable reproducible.

---

## Fuera de alcance de la V1

Quedan fuera de la primera versión:

* multiusuario;
* autenticación avanzada;
* facturación SaaS;
* integraciones ERP productivas;
* procesamiento masivo;
* OCR cloud pago obligatorio;
* motor OCR definitivo;
* UI enterprise completa;
* automatización contable final;
* reglas de negocio hardcodeadas por proveedor sin configuración o tests;
* eliminación de legacy sin autorización explícita.

---

## Principios de avance

* No avanzar a una fase posterior si la fase actual no está validada.
* No declarar tareas cerradas sin evidencia real.
* No confundir infraestructura interna con producto demostrable.
* Toda mejora OCR debe indicar campo, documento, fixture, salida y validación.
* Todo cambio funcional debe tener tests o justificación explícita.
* La V1 se cierra por demostración end-to-end, no solo por tests unitarios.
* El roadmap debe reflejar el estado real de Git y no expectativas.
* Una sola tarea técnica puede estar abierta por vez.

---

## Leyenda de estado

```text
CERRADO: implementado, validado y respaldado por evidencia.
PARCIAL: existe avance, pero falta validación, integración o demostración completa.
PENDIENTE: no implementado o no demostrado.
BLOQUEADO: no puede avanzar sin resolver dependencia.
```

---

## Estado operativo actual

Últimas tareas cerradas:

```text
T3.1 — MVP End-to-End Demo
Tarea SDD local (Normalización local SDD)
```

Estado reportado:

```text
Cerrada, commiteada y pusheada a main.
```

Merge commit reportado:

```text
9a37026 merge: add mvp end-to-end demo
66dfe03 merge: normalize local sdd structure
```

Feature commits reportados:

```text
acd2c4b feat(demo): add mvp end-to-end demo
3d22e34 docs(governance): normalize local sdd structure
```

Tarea técnica anterior cerrada:

```text
T2.9 — Integración con pipeline de producción y monitoreo de métricas de campos rechazados.
```

Commits relevantes reportados:

```text
python scripts/validate_project.py: PASS
pytest -q backend/tests/test_evaluate_ocr_service_data_output.py: 20 passed
pytest -q: 77 passed, 7 warnings
git diff --check: sin errores
```

---

## Fase 0 — Baseline controlado

Objetivo: dejar el proyecto limpio, versionable y gobernado.

Estado: CERRADO según historial operativo del proyecto.

Capacidades esperadas:

* estructura base simple;
* `GOVERNANCE.md`;
* `CONTRIBUTING.md`;
* `VERSION`;
* `CHANGELOG.md`;
* documentación base en `docs/`;
* validador de proyecto;
* baseline aprobado en Git.

Criterio de cierre:

```bash
python scripts/validate_project.py
git status --short
```

Nota:

Esta fase representa la base de gobernanza y versionado. No implica por sí sola que el producto OCR sea demostrable.

---

## Fase 1 — OCR baseline con imagen fixture

Objetivo: procesar una imagen conocida y extraer campos mínimos.

Estado: PARCIAL/CERRADO según evidencia de tests y fixtures existentes en el repositorio.

Capacidades esperadas:

* fixture representativo, por ejemplo `gas_sample.jpg`;
* prueba OCR mínima;
* extracción de al menos dos campos;
* medición de tiempo de procesamiento;
* documentación de limitaciones.

Criterio de cierre:

```bash
pytest backend/tests
```

Nota:

Esta fase valida que existe una base OCR medible. No equivale a una demo completa de producto si no está conectada con extracción, validación y salida estructurada.

---

## Fase 2 — Bridge de salida controlado / DATA pipeline

Objetivo: generar archivos de salida estructurados sin riesgo de lectura parcial.

Estado: CERRADO para las tareas T2.x confirmadas; PARCIAL como experiencia de producto visible.

Capacidades asociadas:

* escritura atómica en `storage_bridge`;
* validación de payload;
* movimiento seguro a `storage_bridge/ready`;
* generación de salida `.DATA`;
* evaluador DATA;
* inventario de documentos/servicios;
* validación específica por servicio;
* validación DATA en salida `.DATA`;
* métricas de campos rechazados;
* integración con pipeline productivo.

Tareas T2.x cerradas confirmadas:

* T2.4 — Inventario de documentos/servicios DATA.
* T2.5 — Integración inventario DATA evaluator.
* T2.6 — Validación específica por servicio DATA.
* T2.8 — Validación DATA en salida `.DATA`.
* T2.9 — Integración con pipeline de producción y monitoreo de métricas de campos rechazados.
* T2.10 — Reconciliación de roadmap operativo con Git real.

Nota importante:

Las tareas T2.x prepararon infraestructura interna del pipeline. Son valiosas, pero no cierran por sí solas la V1 porque todavía falta una demostración visible end-to-end para el usuario/dueño de producto.

---

## Fase 3 — Demo end-to-end visible de la V1

Objetivo: demostrar el flujo completo del producto sin asumir funcionamiento por piezas internas.

Estado: PENDIENTE.

Esta es la siguiente fase crítica.

Flujo mínimo requerido:

```text
Imagen fixture o imagen real controlada
→ OCR
→ texto bruto OCR
→ extracción de campos candidatos
→ validación semántica
→ campos aceptados, rechazados y no encontrados
→ salida TXT/.DATA/storage_bridge
→ evidencia del archivo generado
```

Tareas propuestas:

* T3.0 — Auditoría demostrable del MVP end-to-end actual.
* T3.1 — Definición del comando o procedimiento único de demo local.
* T3.2 - Ejecucion documento/servicio controlado -> salida estructurada.
* T3.3 — Reporte de campos aceptados, rechazados y no encontrados.
* T3.4 — Documentación de cómo reproducir la demo.
* T3.5 — Criterio de aceptación visual/técnico para dueño de producto.

Criterio de cierre:

```text
Existe una ejecución reproducible que muestra:
- entrada usada;
- servicio/documento procesado;
- texto bruto OCR;
- campos candidatos;
- campos validados;
- campos rechazados;
- campos no encontrados;
- archivo de salida generado;
- comando o procedimiento de reproducción.
```

---

## Fase 4 — Frontend móvil mínimo

Objetivo: capturar o cargar una imagen desde celular y mostrar resultados básicos.

Estado: PENDIENTE.

Tareas:

* corregir carga de servicios si aplica;
* permitir selección manual de servicio;
* permitir carga/captura de imagen desde celular;
* mostrar vista previa de imagen;
* mostrar campos extraídos;
* mostrar campos rechazados/no encontrados;
* mostrar errores claros;
* conectar con pipeline real o endpoint local.

Criterio de cierre:

```text
Desde una interfaz mínima usable se puede cargar/capturar una imagen,
procesarla y ver el resultado estructurado.
```

Nota:

Esta fase no debe iniciarse hasta saber con evidencia qué parte del flujo backend end-to-end ya funciona.

---

## Fase 5 — Mejora de precisión OCR

Objetivo: mejorar captura y extracción con evidencia medible.

Estado: PENDIENTE.

Tareas:

* preprocesamiento de imagen;
* recorte o guía visual;
* fallback por regex global;
* métrica simple de confianza;
* fixtures por tipo de servicio/documento;
* evaluación de falsos positivos;
* comparación de resultados antes/después.

Criterio de cierre:

```text
La mejora OCR debe demostrar:
- campo extraído;
- tipo de documento;
- fixture o imagen usada;
- salida producida;
- validación aplicada;
- falsos positivos evitados.
```

---

## Fase 6 — Evaluación de motor OCR

Objetivo: decidir motor OCR con evidencia y no por preferencia.

Estado: PENDIENTE.

Motores candidatos:

* EasyOCR;
* Tesseract;
* PaddleOCR;
* Google Document AI;
* Azure Document Intelligence.

Criterios:

* precisión;
* velocidad;
* costo;
* facilidad de instalación;
* privacidad;
* mantenimiento;
* compatibilidad con despliegue esperado.

Criterio de cierre:

```text
Existe una matriz comparativa con fixtures reales y decisión documentada.
```

---

## Cierre de V1

La V1 solo puede considerarse cerrada cuando exista evidencia de:

* al menos un flujo end-to-end reproducible;
* al menos un documento/servicio procesado con fixture o imagen real controlada;
* OCR ejecutado;
* texto bruto OCR disponible;
* campos configurables extraídos;
* validación semántica aplicada;
* campos aceptados, rechazados y no encontrados reportados;
* salida TXT/.DATA/storage_bridge generada;
* comando o procedimiento documentado;
* tests relevantes pasando;
* `python scripts/validate_project.py` pasando;
* `pytest -q` pasando o justificación explícita si se usa subset;
* `git diff --check` sin errores;
* working tree limpio;
* commit y push realizados.

---

## Próxima tarea elegible

La próxima tarea elegible recomendada es:

T3.3 — Reporte de campos aceptados, rechazados y no encontrados.

Tipo:

feature / execution / demo-output

Objetivo:

Generar un reporte estructurado de campos aceptados, rechazados y no encontrados.
Procesar documentos de impuestos/servicios/comprobantes.
Salida con métricas de calidad OCR.

Resultado esperado:

Un reporte reproducible que demuestre: documento procesado → extracción de campos → validación de campos → clasificación de campos aceptados/rechazados/no encontrados.

## Notas de consistencia

Este roadmap reemplaza la visión incompleta anterior por una estructura orientada a V1 demostrable.

Las tareas T2.x cerradas siguen siendo válidas como infraestructura interna, pero no cierran por sí solas la primera versión del producto.

La siguiente prioridad no es sumar más infraestructura, sino demostrar el flujo completo visible.
