# Mejora Precision OCR

## Para Que Sirve

Este benchmark permite revisar la precision de la captura OCR local antes de
integrarla con sistemas externos. Genera dos evidencias:

- un JSON estructurado para auditoria tecnica;
- un resumen Markdown para QA o PR.

No requiere subir comprobantes reales ni versionar datos sensibles.

## Ejecutar Con Dataset Sintetico

```powershell
python .\scripts\benchmark_captura.py `
  --dataset synthetic `
  --docs 20 `
  --out _bench\precision.json `
  --report-md _bench\precision.md
```

Este modo crea documentos controlados en `_bench/`, que no se versiona. Sirve
para CI, desarrollo local y revisiones sin muestras privadas. Por defecto usa
`--synthetic-mode controlled`, que no requiere OCR real instalado.

Para procesar las imagenes sinteticas con el motor RapidOCR/ONNX:

```powershell
python .\scripts\benchmark_captura.py `
  --dataset synthetic `
  --synthetic-mode ocr `
  --docs 20 `
  --out _bench\precision-ocr.json `
  --report-md _bench\precision-ocr.md
```

## Ejecutar Con Muestras Privadas Locales

Opcionalmente, crear:

```text
backend/tests/fixtures/_local_samples/real/
```

Dentro de esa carpeta puede existir `expected.local.json` con documentos
anonimizados o controlados. La carpeta esta gitignored y el benchmark la trata
como evidencia local opcional.

```powershell
python .\scripts\benchmark_captura.py `
  --dataset local `
  --docs 400 `
  --out _bench\precision-local.json `
  --report-md _bench\precision-local.md
```

Si se usa `--dataset auto`, el comando usa muestras privadas si estan
disponibles; si faltan, cae al dataset sintetico/controlado.

## Interpretar El JSON

La seccion `summary` muestra:

- cantidad de documentos;
- tiempos p50, p95, media y maximo;
- throughput;
- memoria aproximada;
- conteos por proveedor/servicio;
- conteos por campo;
- falsos positivos evitados.

La seccion `documents` muestra cada comprobante evaluado con:

- `raw_ocr_text`;
- `candidate_fields`;
- `validated_fields`;
- `rejected_fields`;
- `missing_fields`;
- `field_results`;
- `false_positives_avoided`.

## Interpretar El Markdown

El Markdown resume el lote en tablas por proveedor/servicio. Un campo puede
quedar como:

- `validated_match`: coincide con lo esperado;
- `validated_mismatch`: fue validado, pero no coincide con el contrato;
- `rejected` o `rejected_expected`: hubo candidato, pero la validacion lo
  rechazo;
- `missing_allowed`: falta aceptada por limitacion conocida;
- `missing_unexpected`: falta no esperada.

El p95 caliente mayor a 5 segundos queda marcado como `risk`.

## Privacidad

No se deben guardar comprobantes reales ni salidas con datos personales en Git.
Los artefactos de benchmark generados quedan bajo `_bench/`, tambien gitignored.
