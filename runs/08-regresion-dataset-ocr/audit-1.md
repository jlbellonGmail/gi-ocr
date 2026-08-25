```yaml
status: rejected
attempt: 1
feedback:
  - "Bloqueante: el fixture 'documento no reconocido/en blanco' del criterio 7 (imagen totalmente en blanco, sin texto, tal como devuelve la rama por defecto de `_base_case_image` en `scripts/benchmark_captura.py` para cualquier `case_id` no reconocido) va a chocar con `quality_gate.evaluate`, que corre ANTES de la clasificación de proveedor dentro de `capture_pipeline.process_document` (backend/app/capture_pipeline.py:242-250). Verificado en `backend/app/quality_gate.py`: sobre un canvas RGB blanco puro (255,255,255) sin ningún trazo, la señal `blur` (`_blur_signal`, Laplaciano) da varianza 0 < `GI_OCR_QUALITY_BLUR_REJECT_BELOW` (40.0) => reject, y la señal `poor_lighting` (`_illumination_signal`) da media de gris 255.0 > `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE` (254.5) => reject. Verdict agregado: 'reject'. Con verdict 'reject', `process_document` corta en `_quality_rejected_result` (capture_pipeline.py:274-296), cuyo `processing_metadata` NO tiene ninguna clave `provider_detected` (solo trae `quality_gate` y `engine`). El criterio 7 exige `processing_metadata['provider_detected'] == 'UNKNOWN'`: con este fixture tal como está descrito, el acceso lanza `KeyError`, no un simple mismatch — el test fallaría por una razón ajena a lo que se quiere probar (clasificación de proveedor), sino por interacción no contemplada con la feature `06-calidad-captura-mobile`. El spec no menciona esta interacción ni en 'Criterios de aceptación' ni en 'Casos borde'. Corregir de una de estas formas explícitas (a decisión del analyst, pero debe quedar decidida en el spec, no como sorpresa del builder): (a) cambiar el fixture del caso 'no reconocido' para que sea un documento sintético con contenido tipográfico legible/nítido (similar en calidad de imagen a `gas_valid`/`cevt_valid`) pero SIN ninguna de las `classify_keywords` de `LITORAL_GAS`/`CEVT` — esto también es conceptualmente más correcto: 'proveedor no reconocido' es un caso distinto de 'calidad de imagen rechazada', y mezclarlos en un canvas en blanco confunde el objetivo del test; o (b) si el analyst insiste en un canvas realmente en blanco, el criterio 7 debe reescribirse para esperar y verificar explícitamente el camino de `quality_gate` rechazado (`processing_metadata['quality_gate']['verdict'] == 'reject'` y ausencia de `provider_detected`), no `provider_detected == 'UNKNOWN'`."
  - "Relacionado, no bloqueante en sí pero debe quedar explícito una vez resuelto el punto anterior: agregar a 'Casos borde' la advertencia sobre la interacción entre `quality_gate` (06) y esta suite (08), para que quien mantenga las plantillas de providers.py sepa que un fixture demasiado 'limpio' (poco texto, fondo mayormente blanco) puede acercarse al umbral `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_WARN_ABOVE`/`_REJECT_ABOVE` y producir un warn/reject espurio de calidad, no solo un problema de legibilidad OCR (que sí está contemplado en el caso borde de fuente tipográfica)."
```

## Verificación contra código (todo correcto salvo el punto anterior)

- `backend/app/capture_pipeline.py`: confirmado que `process_document` invoca `quality_gate.evaluate` antes de clasificar proveedor (líneas 242-250) y que `process_image` es la función que hace two-pass ROI + clasificación + extracción + validación, devolviendo `candidate_fields`/`validated_fields`/`rejected_fields`/`missing_fields`/`raw_ocr_text` como describe el spec.
- `backend/app/templates/providers.py`: `required_fields` de `litoral_gas_template()` y `cevt_template()` citados en el spec coinciden exactamente con el código (incluyendo orden y nombres de campo).
- `backend/app/validators.py`: `validate_comprobante`, `validate_date`, `validate_account`, `validate_period`, `validate_amount` existen con la firma y comportamiento (tupla `(valor, reason)`) que el spec asume; `validate_period` rechaza `13/2026` con `"month_out_of_range"` (no vacío), tal como exige el criterio 7.
- `scripts/benchmark_captura.py`: `_base_case_image`, `variant`, `build_synthetic_dataset`, `values_match` (tolerancia `abs_tol=0.01`, comparación `strip().lower()`) existen exactamente como se describen. `synthetic_controlled_result` efectivamente evita el motor OCR real, confirmando la afirmación del spec de que ese atajo no debe usarse para esta suite.
- `backend/tests/test_benchmark_captura.py`: confirmado que todos los tests usan `_pipeline_result()` mockeado a mano, nunca ejecutan el motor OCR real — coincide con lo que dice el spec.
- `backend/tests/test_local_samples_real.py`: confirmado `pytestmark = pytest.mark.skipif(...)` que salta todo el módulo (incluido `test_unknown_not_gas`, que usa exactamente el mismo patrón de imagen en blanco 400x600 que preocupa arriba) cuando faltan las fixtures privadas gitignored — coincide con la afirmación del spec de que hoy esa suite nunca corre en CI, y confirma además que el escenario "imagen en blanco" nunca fue puesto a prueba en CI hasta ahora bajo el pipeline con `quality_gate` activo.
- `backend/config/services.ini`: confirmado que usa nombres de campo (`nro_medidor`, `a_pagar_hasta`, `importe`) distintos de `providers.py` (`medidor`, `vencimiento`, `total`), sustentando la exclusión explícita de `extraction_engine`/`services.ini` del alcance.
- `docs/tecnica/index.md` y `docs/usuario/index.md`: existen y siguen el patrón de enlace que el spec exige agregar.
- `docs/tecnica/arquitectura.md`: ADR-006 y ADR-007 existen tal como se citan.
- Contrato obligatorio de `AGENTS.md` (docs técnica/usuario, `decision.md`, enlaces de índice) está correctamente exigido en los criterios 1-5.
- Regla de dominio OCR (campo, tipo de documento, fixture, salida esperada, validación, falsos positivos evitados) está cubierta explícitamente por cada caso del criterio 7.
- No se versionan imágenes reales: los fixtures son sintéticos generados por código, coherente con la regla no negociable.

## Archivos relevantes

- `D:\proyectos\gi-ocr\runs\08-regresion-dataset-ocr\spec.md`
- `D:\proyectos\gi-ocr\backend\app\capture_pipeline.py`
- `D:\proyectos\gi-ocr\backend\app\quality_gate.py`
- `D:\proyectos\gi-ocr\backend\app\templates\providers.py`
- `D:\proyectos\gi-ocr\backend\app\validators.py`
- `D:\proyectos\gi-ocr\scripts\benchmark_captura.py`
- `D:\proyectos\gi-ocr\backend\tests\test_benchmark_captura.py`
- `D:\proyectos\gi-ocr\backend\tests\test_local_samples_real.py`
- `D:\proyectos\gi-ocr\backend\config\services.ini`
