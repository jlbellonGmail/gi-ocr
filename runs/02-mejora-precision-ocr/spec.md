# Spec: Mejora Precision OCR

> Producida por `analyst-agent` desde `ROADMAP.md`, `docs/OCR-STRATEGY.md`,
> `docs/ACCEPTANCE-CRITERIA.md` y la evidencia de
> `01-captura-ocr-local-agil`.

## Alcance

Validar y mejorar la precision operativa del OCR actual sin cambiar el
motor principal. La feature debe convertir el two-pass ROI de
`01-captura-ocr-local-agil` en evidencia medible por lote, proveedor y
campo:

- Benchmark reproducible con `scripts/benchmark_captura.py` o reemplazo
  equivalente, capaz de correr un lote de hasta 400 documentos/variantes.
- Medicion de tiempos `p50`/`p95`, tiempo total, throughput, memoria
  aproximada y tiempos por etapa cuando el pipeline los expone.
- Reporte de precision por proveedor, documento y campo, diferenciando:
  texto bruto OCR, campo candidato, campo validado, campo rechazado y campo
  no encontrado.
- Medicion explicita de falsos positivos evitados: valores candidatos que
  aparecen en OCR/extraccion pero quedan rechazados por validacion
  semantica o por clasificacion de proveedor.
- Uso de muestras reales anonimizadas locales cuando existan
  (`backend/tests/fixtures/_local_samples/real`, gitignored) y dataset
  sintetico/controlado versionable cuando no existan.
- Salida de benchmark en JSON estructurado y resumen Markdown para que QA y
  PR puedan adjuntar evidencia sin inspeccion manual ad hoc.
- Ajustes acotados de ROI, anclas, normalizacion de imagen, regex o
  validadores cuando la evidencia del benchmark muestre una falla
  corregible sin hardcodear datos privados.

**Explícitamente fuera de alcance de esta feature:**

- Cambiar RapidOCR/ONNX como motor OCR principal o reabrir ADR-006.
- Agregar proveedores nuevos fuera de los ya soportados por la feature 01:
  `LITORAL_GAS`/servicio `GAS` y `CEVT`/servicio `ELECTRICITY`.
- Versionar comprobantes reales, imagenes con datos sensibles o outputs que
  expongan datos personales completos.
- Convertir el benchmark puntual en la suite permanente de regresion OCR;
  eso queda para `08-regresion-dataset-ocr`.
- Exigir que CI tenga acceso a muestras privadas locales. En CI debe correr
  el modo sintetico/controlado y saltar lo privado con motivo explicito.

## Contexto

`01-captura-ocr-local-agil` resolvio el problema de rendimiento: EasyOCR
era demasiado lento para una captura operable y RapidOCR/ONNX con two-pass
ROI bajo el procesamiento local a segundos por documento. Esa feature
tambien dejo documentado un caso real relevante: el periodo de Litoral Gas
puede quedar ilegible para PP-OCRv3 y debe derivarse a correccion humana en
vez de inventar una reparacion heuristica.

La deuda actual no es elegir otro motor, sino demostrar con lote y datos
controlados que el motor elegido clasifica documentos, extrae campos y
rechaza falsos positivos de forma estable. El resultado de esta feature
debe servir como evidencia operativa: que campos son confiables, cuales
fallan, que fallos se consideran esperados y que casos quedan para revision
humana.

## Dataset y fixtures

La implementacion debe soportar dos fuentes de evaluacion:

1. **Muestras privadas locales anonimizadas o controladas**, ubicadas bajo
   `backend/tests/fixtures/_local_samples/real/` y no versionadas. Si
   existen, el benchmark puede leer `expected.local.json` para comparar
   resultados esperados de `GAS_LITORAL` y `CEVT`.
2. **Dataset sintetico versionable**, generado a partir de fixtures sin
   datos sensibles o imagenes construidas en test. Debe cubrir al menos
   variantes de rotacion leve, escala, brillo/contraste, compresion y
   documento desconocido/blanco.

El contrato esperado de cada documento evaluado debe declarar:

- id de documento anonimo;
- proveedor esperado (`LITORAL_GAS`, `CEVT` o `UNKNOWN`);
- servicio esperado (`GAS`, `ELECTRICITY` o `UNKNOWN`);
- tipo de documento;
- campos esperados por nombre;
- campos permitidos como `missing` por limitacion conocida;
- campos que deben rechazarse si aparecen como candidato invalido.

## Criterios de aceptación

1. Existe un benchmark reproducible para la captura OCR local que acepta al
   menos `--docs`, `--out`, `--report-md`, `--dataset` o parametros
   equivalentes documentados, y puede ejecutarse con lote objetivo de 400
   documentos/variantes.
2. El benchmark produce JSON estructurado con resumen global, resultados por
   documento y metricas por campo. El JSON debe incluir `docs`,
   `cold_start_s` si aplica, `hot_p50_s`, `hot_p95_s`, `hot_mean_s`,
   `hot_max_s`, `docs_per_minute`, `process_rss_mb` aproximado y tiempos
   por etapa disponibles.
3. El reporte por campo distingue explicitamente: `raw_ocr_text`,
   `candidate_fields`, `validated_fields`, `rejected_fields` y
   `missing_fields`. No se acepta un unico contador ambiguo de "precision".
4. El reporte agrupa resultados por proveedor/servicio y por campo. Debe
   cubrir como minimo `LITORAL_GAS`/`GAS` con `provider`, `cliente`,
   `periodo`, `comprobante`, `fecha_emision`, `vencimiento`, `total`; y
   `CEVT`/`ELECTRICITY` con `provider`, `cliente`, `medidor`, `periodo`,
   `comprobante`, `fecha_emision`, `vencimiento`,
   `codigo_pago_electronico`, `total`.
5. La salida mide falsos positivos evitados: todo campo candidato que no
   termine validado debe registrar campo, valor candidato, motivo de rechazo
   o condicion de no coincidencia, y validacion semantica aplicada.
6. El benchmark no versiona imagenes reales ni datos sensibles. Si usa
   muestras privadas locales, debe tratarlas como opcionales y gitignored;
   si faltan, la ejecucion de CI debe usar dataset sintetico/controlado o
   saltar solo el caso privado con motivo verificable.
7. La feature debe declarar umbrales de aceptacion operativa para esta
   ronda. Como minimo: el benchmark no debe degradar el rendimiento ya
   documentado de `01-captura-ocr-local-agil` sin explicacion; cualquier
   `p95` mayor a 5 s/documento en caliente debe quedar marcado como riesgo
   o fallo segun el modo de ejecucion.
8. Las mejoras de precision, si se implementan, deben vivir en plantillas,
   ROI, anclas, `backend/config/services.ini`, normalizacion o validadores
   genericos. No se permite hardcodear valores de comprobantes reales ni
   crear extractores Python por proveedor fuera del modelo vigente.
9. Deben existir tests para el parser/agregador de resultados del benchmark
   y para al menos un escenario con campo validado, uno rechazado y uno no
   encontrado. Los tests deben poder correr sin muestras privadas.
10. Los tests existentes de backend y scripts deben seguir en verde. Los
    tests que dependan de `playwright` o muestras privadas pueden saltarse
    solo con motivo explicito y verificable.
11. Debe existir `docs/tecnica/mejora-precision-ocr.md`, no vacio, con el
    algoritmo de benchmark, dataset usado, metricas, umbrales, falsos
    positivos evitados, casos borde y decisiones de diseno.
12. Debe existir `docs/usuario/mejora-precision-ocr.md`, no vacio, con el
    proposito de la validacion, como ejecutar el benchmark localmente y como
    interpretar el reporte sin exponer datos sensibles.
13. Debe existir `runs/02-mejora-precision-ocr/decision.md`, con decisiones
    demostrables desde spec, auditoria, implementacion y QA.
14. Deben existir enlaces exactos a ambos documentos en
    `docs/tecnica/index.md` y `docs/usuario/index.md`.
15. `Assert-FeatureContract` debe pasar para
    `02-mejora-precision-ocr` y el titulo `Mejora Precision OCR` antes de
    marcar `ROADMAP.md` como `[-] READY_FOR_PR`.

## Casos borde a contemplar

- Documento desconocido o blanco: debe clasificarse como `UNKNOWN`, no como
  `GAS` por defecto, y sus campos deben quedar no encontrados o rechazados
  segun corresponda.
- Campo visible en texto bruto OCR pero invalido semanticamente: debe
  aparecer como candidato rechazado, no como validado ni como missing.
- Campo esperado ausente o ilegible por OCR: debe quedar en
  `missing_fields` y derivable a revision humana.
- Campo con formato confundible por OCR, por ejemplo fechas con separadores
  `.`/`-`/`/` o montos con `.` y `,`: debe pasar por validadores existentes,
  registrando normalizacion o rechazo.
- Proveedor detectado correctamente pero un campo de otra plantilla aparece
  como candidato: debe contarse como falso positivo evitado si no se valida.
- PDF con texto nativo y PDF escaneado: si el benchmark los incluye, debe
  reportar si se uso texto nativo o OCR, sin mezclar ambas rutas en una
  metrica opaca.
- Lote grande interrumpido o documento individual fallido: el reporte debe
  conservar los documentos ya procesados y registrar error por documento.

## Riesgos / supuestos

- **Supuesto:** RapidOCR/ONNX sigue siendo el motor principal y la
  arquitectura two-pass ROI vigente; esta feature mide y ajusta precision,
  no reevalua motores.
- **Riesgo:** el lote de 400 documentos puede ser costoso en maquinas sin
  CPU suficiente. El benchmark debe permitir lotes chicos para desarrollo y
  documentar el comando usado por QA.
- **Riesgo:** las muestras reales locales pueden existir en una maquina y
  faltar en CI. La aceptacion depende de que el modo sin privados sea
  reproducible; los privados agregan evidencia, no son requisito de
  portabilidad.
- **Riesgo:** mejorar un campo con heuristicas demasiado especificas puede
  aumentar falsos positivos en otro proveedor. Por eso toda mejora debe
  reportar aceptados, rechazados y no encontrados por proveedor/campo, no
  solo un caso exitoso.
- **Supuesto:** la salida legacy `.DATA` y el contrato de
  `storage_bridge/` no cambian en esta feature. El foco esta antes de la
  confirmacion final: OCR, extraccion, validacion y evidencia.
