# Regresión de dataset OCR — documentación de usuario

## Propósito

Esta mejora no agrega ningún endpoint HTTP nuevo ni cambia el
comportamiento de la API o del frontend. Es una suite de tests permanente
que protege la precisión de extracción de campos que ya funcionaba
(`LITORAL_GAS`/`GAS` y `CEVT`/`ELECTRICITY`) para que un cambio futuro en
el motor OCR, en una plantilla de proveedor, en un validador o en el
preprocesamiento de imagen no la rompa **en silencio**.

Antes de esta mejora, ningún test corría siempre (en cualquier checkout,
incluido CI) contra el motor OCR real con un contrato de "estos campos
tienen que dar exactamente este valor". Ahora sí: si alguien cambia código
del pipeline de captura y un campo que antes se extraía bien deja de
hacerlo, `pytest` falla con un mensaje concreto de qué campo y qué caso se
rompió, en la misma corrida que ya se ejecuta en cada Pull Request.

## Cómo se ejecuta

Igual que el resto de la suite de tests del backend, sin ningún paso
adicional ni variable de entorno especial:

```bash
pytest -q
```

Para correr sólo esta suite en particular:

```bash
pytest backend/tests/test_ocr_regression_dataset.py -v
```

Salida esperada (todo en verde, ~9 segundos incluyendo la carga del motor
OCR):

```
backend/tests/test_ocr_regression_dataset.py::TestLitoralGasValidDocument::test_raw_ocr_text_is_not_empty PASSED
backend/tests/test_ocr_regression_dataset.py::TestLitoralGasValidDocument::test_all_required_fields_validated_with_expected_value PASSED
...
backend/tests/test_ocr_regression_dataset.py::test_synthetic_fixtures_are_deterministic PASSED

======================= 22 passed in 9.03s =======================
```

No requiere ninguna imagen ni archivo externo: cada fixture se genera por
código, en memoria, al correr el test (ver
[docs/tecnica/regresion-dataset-ocr.md](../tecnica/regresion-dataset-ocr.md)
para el detalle de cómo).

## Cómo interpretar un fallo

Si un cambio en el pipeline de captura degrada la extracción de un campo,
el test correspondiente falla con el valor obtenido y el esperado en el
mismo mensaje, por ejemplo (`total` extraído mal por un cambio hipotético
en el validador de montos):

```
FAILED backend/tests/test_ocr_regression_dataset.py::TestLitoralGasValidDocument::test_all_required_fields_validated_with_expected_value

AssertionError: 'total' validado con valor inesperado: obtenido='999.99' esperado=12345.67
assert False
 +  where False = values_match('999.99', 12345.67)
```

O, si un campo dejó de rechazarse cuando debería (por ejemplo, si un cambio
futuro en `validators.validate_period` dejara de detectar un mes fuera de
rango):

```
FAILED backend/tests/test_ocr_regression_dataset.py::TestLitoralGasInvalidPeriod::test_periodo_is_rejected_with_non_empty_reason

AssertionError: 'periodo' debería estar en rejected_fields, obtenido: {}
```

En ambos casos, el mensaje indica el campo, el caso (`LITORAL_GAS` válido,
`CEVT` válido, `LITORAL_GAS` con período inválido, o documento no
reconocido) y el valor concreto obtenido vs. el esperado — no hace falta
inspeccionar el pipeline a mano para saber qué se rompió.

## Qué cubre y qué no

Cubre, contra el motor OCR real (RapidOCR/ONNX):

- Un documento `LITORAL_GAS` completo y válido: los 7 campos esperados
  (`provider`, `cliente`, `periodo`, `comprobante`, `fecha_emision`,
  `vencimiento`, `total`) terminan validados con el valor correcto.
- Un documento `CEVT` completo y válido: los 9 campos esperados terminan
  validados con el valor correcto.
- Un documento `LITORAL_GAS` con un `periodo` inválido (`13/2026`, mes
  fuera de rango): ese campo termina **rechazado** (con motivo), nunca
  validado ni "perdido" sin explicación, mientras el resto de los campos
  sigue extrayéndose con normalidad.
- Un documento con texto legible pero de un proveedor no reconocido: el
  sistema lo clasifica como `UNKNOWN`, sin inventar ningún campo de
  `LITORAL_GAS` ni `CEVT`, y confirma que no fue el control de calidad de
  imagen (`06-calidad-captura-mobile`) el que lo descartó.

No cubre (fuera de alcance de esta mejora):

- Latencia o uso de memoria del pipeline: eso lo mide
  `scripts/benchmark_captura.py` (ver
  [docs/usuario/mejora-precision-ocr.md](mejora-precision-ocr.md)), sin
  cambios.
- Documentos/proveedores que no estén ya configurados en
  `backend/app/templates/providers.py` (hoy sólo `LITORAL_GAS` y `CEVT`).
- El motor de extracción alternativo usado para exportación legacy por
  lotes (`backend/config/services.ini` +
  `backend/app/extraction_engine.py`), que no es el que usa la API/cola de
  jobs real.

## Ver también

- [docs/tecnica/regresion-dataset-ocr.md](../tecnica/regresion-dataset-ocr.md):
  diseño completo de la suite, fixtures y decisiones de calibración.
- [docs/usuario/captura-ocr-local-agil.md](captura-ocr-local-agil.md): flujo
  completo de subida/revisión/confirmación que esta suite protege.
- [docs/usuario/calidad-captura-mobile.md](calidad-captura-mobile.md):
  control de calidad de imagen previo al OCR, verificado explícitamente en
  cada caso de esta suite (`quality_gate.verdict != "reject"`).
