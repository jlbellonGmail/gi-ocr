# Auditoría — attempt 2

He releído `audit-1.md`, el `spec.md` corregido completo, y verificado nuevamente contra el código real (`backend/app/capture_pipeline.py`, `backend/app/image_prep.py`, `backend/app/pdf_util.py`) y contra `docs/tecnica/correccion-orientacion-exif.md` y `docs/tecnica/calidad-captura-mobile.md`.

```yaml
status: approved
attempt: 2
feedback:
  - "Verificado contra el código: la corrección del criterio 12, la sección 'Explícitamente NO incluye' y el párrafo de Contexto ahora describen con precisión que apply_exif_orientation y quality_gate.evaluate son los únicos pasos genuinamente ausentes del camino PDF, mientras que correct_orientation (skip=False), deskew (incondicional), correct_perspective (si se pide) y normalize_scale sí corren igual que en el camino imagen porque comparten image_prep.prepare(). Ya no hay contradicción con el criterio 14."
  - "El nuevo caso _process_pdf_native también es fácticamente correcto: en pdf_util.extract_text_and_render, 'image' es None cuando needs_ocr es False (>=6 caracteres alfanuméricos nativos); si ninguna página produce imagen, _process_pdf llama a _process_pdf_native sin invocar prepare(). El spec lo describe con exactitud."
```

## Verificación puntual

1. **Criterio 12 vs. 14 (contradicción original resuelta)**: confirmado línea por línea en `capture_pipeline.py::_process_pdf` (línea 282: `image_prep.prepare(page_to_process["image"])`, sin pasar `exif_orientation_applied` ni `apply_perspective`, ambos con default `False` igual que en `process_document`) y en `image_prep.py::prepare` (línea 285: `correct_orientation(image_np, skip=exif_orientation_applied)` → `skip=False` en el camino PDF, corre la heurística; línea 286: `deskew(out)` incondicional; línea 289: `normalize_scale`). El criterio 12 ahora exige que la traza de PDF sea honesta sobre estos pasos (que sí corren) y solo exige ausencia de `apply_exif_orientation` y `quality_gate` (que efectivamente nunca se invocan en `_process_pdf`, confirmado: no aparecen en esa función). El criterio 14 exige que el contraste se integre dentro de `prepare()` y corra igual en ambos caminos, sin rama `is_pdf`. Ambos criterios son ahora mutuamente consistentes.

2. **"Explícitamente NO incluye" y "Contexto"**: ya no contienen la afirmación errónea de que el camino PDF "nunca ejecuta" deskew/perspectiva/contraste. El texto nuevo (líneas 82-107 y 127-138) es fácticamente exacto y coincide con lo que verifiqué en el código.

3. **Caso nuevo `_process_pdf_native`**: confirmado contra `pdf_util.py::extract_text_and_render` (línea 42-46: `needs_ocr = alnum < 6`; `image = None` si `needs_ocr` es `False`) y `capture_pipeline.py::_process_pdf` (líneas 273-281: si ninguna página tiene `image` no-None, se llama a `_process_pdf_native` sin invocar `prepare()`). El spec describe correctamente que este sub-camino nunca renderiza imagen ni llama a `prepare()`, y por tanto no genera traza de preparación — tratado con el mismo criterio que el caso `reject` de `quality_gate` (criterio 11), lo cual es coherente.

4. **Verificación de la afirmación sobre docs previas** (pedido explícito del feedback anterior, punto 5): confirmé que `docs/tecnica/correccion-orientacion-exif.md` ("Fuera de alcance", líneas 213-224) y `docs/tecnica/calidad-captura-mobile.md` (líneas 486-489) son precisos — dicen explícitamente que deskew/perspectiva/escala/contraste "siguen sin cambios de comportamiento" (es decir, siguen corriendo igual), no que estén ausentes del camino PDF. La afirmación del spec en "Riesgos/supuestos" de que estos documentos ya eran correctos y no requieren corrección es válida; el error solo existía en la versión anterior de `07`.

5. **Resto del spec intacto**: los criterios 1-11, 13, 15-18, la sección de casos borde, las reglas de dominio OCR (criterio 16, con campo/tipo de documento/fixture/salida esperada/validación/falsos positivos declarados), la delimitación de alcance frente a `05`, `06`, `08`, `09`, `20`, `21`, y los criterios generales de documentación/decision/índices (1-5) permanecen sin cambios respecto de lo ya aprobado como correcto en `audit-1.md`. No se detectan regresiones colaterales introducidas por la corrección.

## Conclusión

El único motivo de rechazo de `audit-1.md` (imprecisión fáctica sobre qué pasos corren en el camino PDF, y la contradicción derivada entre criterios 12 y 14) fue corregido de forma verificable contra el código real, sin introducir nuevas inconsistencias. El spec cumple los requisitos no negociables de documentación (`docs/tecnica/`, `docs/usuario/`, `decision.md`, enlaces de índice), tiene criterios de aceptación verificables por test, cubre casos borde relevantes (incluido el nuevo sub-camino `_process_pdf_native`), declara la regla de dominio OCR con el detalle exigido, y no asume stack/dependencias nuevas sin declararlas como decisión explícita. Apruebo para pasar a `builder-agent`.

Archivos relevantes revisados:
- `D:\proyectos\gi-ocr\runs\07-preprocesamiento-documental-no-destructivo\spec.md`
- `D:\proyectos\gi-ocr\runs\07-preprocesamiento-documental-no-destructivo\audit-1.md`
- `D:\proyectos\gi-ocr\backend\app\capture_pipeline.py`
- `D:\proyectos\gi-ocr\backend\app\image_prep.py`
- `D:\proyectos\gi-ocr\backend\app\pdf_util.py`
- `D:\proyectos\gi-ocr\docs\tecnica\correccion-orientacion-exif.md`
- `D:\proyectos\gi-ocr\docs\tecnica\calidad-captura-mobile.md`
