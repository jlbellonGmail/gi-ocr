# Current Task

## ID

T1.3

## Nombre

Extracción robusta de campos GAS

## Objetivo

Mejorar la extracción de campos de comprobantes GAS usando el texto OCR ya disponible.

La tarea debe enfocarse en normalización de texto, reglas regex iniciales y salida estructurada de campos. No busca cambiar el motor OCR ni mejorar imagen todavía.

## Rama requerida

```text
feature/ocr-gas-field-extractor
```

## Contexto

La tarea anterior `T1.2 — Evaluación OCR GAS con imágenes reales locales` agregó el script:

```text
scripts/evaluate_gas_ocr.py
```

Ese script ya procesa imágenes locales ignoradas por Git desde:

```text
_local_samples/gas/
```

y genera reportes locales ignorados por Git en:

```text
_ocr_reports/
```

En la prueba con fixture local, se detectaron varios campos, pero quedó pendiente mejorar especialmente:

```text
a pagar hasta
```

## Alcance permitido

Se puede crear o modificar únicamente:

* `backend/app/gas_extractor.py`
* `backend/tests/test_gas_extractor.py`
* `scripts/evaluate_gas_ocr.py`
* `docs/OCR-STRATEGY.md`
* `docs/ACCEPTANCE-CRITERIA.md`
* `governance/current-task.md`

## Alcance prohibido

No modificar:

* frontend;
* bridge;
* `storage_bridge/`;
* motor OCR;
* endpoints FastAPI;
* GitHub remoto;
* tags;
* imágenes reales;
* reportes locales;
* fixtures reales con datos sensibles.

No crear nuevas ramas desde el agente.

No hacer commits automáticos.

## Campos objetivo

La extracción GAS debe intentar obtener:

1. `importe`
2. `a_pagar_hasta`
3. `cliente`
4. `periodo`
5. `nro_medidor`

## Requisitos técnicos

Crear un módulo específico:

```text
backend/app/gas_extractor.py
```

El módulo debe exponer una función principal simple, por ejemplo:

```python
extract_gas_fields(ocr_text: str) -> dict
```

La salida debe incluir:

```json
{
  "fields": {
    "importe": "...",
    "a_pagar_hasta": "...",
    "cliente": "...",
    "periodo": "...",
    "nro_medidor": "..."
  },
  "detected_fields": [],
  "missing_fields": [],
  "normalized_text": "..."
}
```

Los campos no encontrados deben quedar como `null`.

## Reglas de extracción

La extracción debe usar:

* normalización de saltos de línea;
* normalización de espacios múltiples;
* tolerancia a mayúsculas/minúsculas;
* regex específicas por campo;
* tolerancia a variantes como:

  * `cliente`
  * `nro cliente`
  * `n° cliente`
  * `número cliente`
  * `medidor`
  * `nro medidor`
  * `vencimiento`
  * `vence`
  * `pagar hasta`
  * `a pagar hasta`
  * `total`
  * `importe`
  * `saldo`

## Integración con evaluación local

Actualizar:

```text
scripts/evaluate_gas_ocr.py
```

para que use `backend/app/gas_extractor.py` en lugar de tener la lógica de regex embebida en el script.

El script debe conservar su comportamiento actual:

* corre sin imágenes;
* procesa imágenes desde `_local_samples/gas/`;
* genera reportes en `_ocr_reports/`;
* no escribe en `storage_bridge/`.

## Tests requeridos

Crear:

```text
backend/tests/test_gas_extractor.py
```

Los tests deben validar, como mínimo:

* extracción de importe;
* extracción de cliente;
* extracción de fecha `a_pagar_hasta`;
* extracción de periodo;
* extracción de nro medidor;
* campos faltantes cuando el texto no contiene datos;
* salida estable con `fields`, `detected_fields`, `missing_fields` y `normalized_text`.

Los tests deben usar textos sintéticos, no imágenes reales.

## Criterios de aceptación

La tarea queda lista solo si:

* existe `backend/app/gas_extractor.py`;
* existe `backend/tests/test_gas_extractor.py`;
* `scripts/evaluate_gas_ocr.py` usa el extractor GAS;
* `python scripts\validate_project.py` pasa;
* `pytest backend\tests -v` pasa;
* `python -m pytest backend\tests -v` pasa;
* `python scripts\evaluate_gas_ocr.py` corre sin romper;
* no aparecen `_local_samples/`, `_ocr_reports/` ni `_debug/` en Git;
* `git diff --name-only` muestra solo archivos dentro del alcance.

## Validación esperada

```powershell
git branch --show-current
git status --short
python scripts\validate_project.py
pytest backend\tests -v
python -m pytest backend\tests -v
python scripts\evaluate_gas_ocr.py
git diff --stat
git diff --name-only
```

## Commit sugerido

```text
feat(ocr): add gas field extractor
```
