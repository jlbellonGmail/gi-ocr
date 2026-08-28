# Preprocesamiento documental no destructivo — documentación de usuario

## Propósito

Antes de que un documento (foto o PDF) llegue al motor OCR, el sistema le
aplica una serie de mejoras automáticas en memoria: corrige la orientación,
endereza una leve inclinación (deskew), opcionalmente corrige perspectiva,
ajusta el tamaño y — con esta mejora — **normaliza el contraste/iluminación**
si el documento se ve deslucido u oscuro.

Esta mejora agrega dos garantías que antes no eran visibles:

1. **El archivo original nunca se toca.** Todo lo anterior ocurre sobre una
   copia en memoria; el archivo que subiste (`output/uploads/...`) queda
   intacto en todo momento, incluso si reintentás el procesamiento
   (`POST /retry`).
2. **Ahora podés ver exactamente qué se le hizo a la imagen** antes de que
   el OCR la leyera: una lista ordenada de pasos, cada uno indicando si se
   aplicó o no y por qué, disponible en el mismo resultado del job que ya
   consultás hoy (`GET /api/v1/jobs/{job_id}`).

También se agrega un paso nuevo: si la foto está oscura o con poco
contraste, el sistema la mejora automáticamente antes de leerla — sin
inventar texto ni deformar números, y sin tocar documentos que ya están
bien iluminados.

## Qué NO cambia

- El endpoint de subida (`POST /api/v1/jobs`) es el mismo de siempre, con
  el mismo contrato de request.
- El control de calidad de captura (`06-calidad-captura-mobile`, veredictos
  `ok`/`warn`/`reject`) sigue funcionando exactamente igual: esta mejora no
  cambia cuándo se acepta o rechaza una foto, solo agrega información sobre
  lo que pasó con las fotos que sí se procesan.
- No hay ningún endpoint nuevo: la información de esta mejora aparece
  dentro del mismo resultado de job que ya existía
  (`processing_metadata`), en una clave nueva: `preparation_trace`.
- La revisión, confirmación y descarga del resultado final siguen
  funcionando igual.

## `preparation_trace`: qué se le hizo a la imagen

Dentro de `result.processing_metadata`, aparece una lista ordenada de
pasos bajo la clave `preparation_trace`. Cada elemento indica, como
mínimo, el nombre del paso (`step`) y si se aplicó o no (`applied`), más
algunos datos concretos según el paso:

| Paso | Qué hace | Datos que reporta |
|---|---|---|
| `apply_exif_orientation` | Corrige la rotación según la metadata de la cámara (sólo fotos, no PDF) | motivo |
| `correct_orientation` | Corrige rotación por análisis del contenido, si no se hizo ya por EXIF | motivo, si rotó |
| `deskew` | Endereza una leve inclinación | ángulo estimado |
| `correct_perspective` | Corrige perspectiva (sólo si se pidió explícitamente, no es el comportamiento por defecto) | si se pidió, si se encontró el documento |
| `normalize_scale` | Ajusta el tamaño si la imagen es muy grande | tamaño antes/después |
| `normalize_contrast` | Mejora contraste/iluminación si el documento se ve deslucido | método usado, si mejoró |

Esta lista aparece tanto para fotos como para PDF que necesitaron
renderizarse a imagen para OCR (con la diferencia de que un PDF nunca
tiene la entrada `apply_exif_orientation`, porque no aplica). Si el
documento fue rechazado por el control de calidad (`needs_new_photo`) o es
un PDF con texto nativo que no necesitó OCR en ninguna página, esta clave
simplemente no aparece — no hubo ninguna preparación de imagen que
reportar.

## Ejemplo de uso HTTP

### Subir un documento (sin cambios)

```http
POST /api/v1/jobs
Content-Type: multipart/form-data

files=<foto_comprobante_gas.jpg>
```

Respuesta (`200 OK`):

```json
{
  "created": [
    { "job_id": "a1b2c3d4e5f6", "filename": "foto_comprobante_gas.jpg" }
  ],
  "queued": 1
}
```

### Consultar el resultado, con la traza de preparación

```http
GET /api/v1/jobs/a1b2c3d4e5f6
```

Respuesta (`200 OK`) una vez procesado — foto con rotación EXIF, leve
inclinación y algo de bajo contraste, ya corregidas:

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "ready",
  "confirmed": false,
  "result": {
    "processing_metadata": {
      "provider_detected": "LITORAL_GAS",
      "provider_confidence": 1.0,
      "engine": "RapidOCR-ONNX-PP-OCRv3",
      "quality_gate": {
        "verdict": "ok",
        "reasons": [],
        "signals": { "...": "..." }
      },
      "preparation_trace": [
        {
          "step": "apply_exif_orientation",
          "applied": true,
          "reason": "corrección aplicada según tag EXIF Orientation"
        },
        {
          "step": "correct_orientation",
          "applied": false,
          "reason": "omitido: orientación ya corregida por EXIF (apply_exif_orientation)"
        },
        {
          "step": "deskew",
          "applied": true,
          "reason": "skew corregido por rotación",
          "angle_deg": 1.8
        },
        {
          "step": "correct_perspective",
          "applied": false,
          "requested": false,
          "reason": "omitido: no solicitado (apply_perspective=False)"
        },
        {
          "step": "normalize_scale",
          "applied": true,
          "reason": "reescalado al lado mayor máximo permitido",
          "original_size": [3024, 4032],
          "final_size": [1200, 1600],
          "scale_factor": 0.3968
        },
        {
          "step": "normalize_contrast",
          "applied": true,
          "method": "clahe_lab_l_channel",
          "reason": "contraste normalizado (CLAHE sobre canal L de LAB)",
          "std_before": 22.4,
          "std_after": 31.7,
          "sharpness_before": 340.1,
          "sharpness_after": 402.6
        }
      ]
    },
    "raw_ocr_text": "COMPROBANTE GAS\nLitoral Gas - Servicio de Gas Natural\nN Cliente: 12345678\n...",
    "structured_output": {
      "document_type": "GAS",
      "candidate_fields": { "cliente": "12345678", "periodo": "05/2026" },
      "validated_fields": { "cliente": "12345678", "periodo": "05/2026" },
      "rejected_fields": {},
      "missing_fields": {}
    }
  }
}
```

En este ejemplo:

- La cámara había guardado la foto rotada (metadata EXIF), así que
  `apply_exif_orientation` la corrigió y `correct_orientation` (la
  heurística por análisis de contenido) se omitió a propósito para no
  corregir dos veces.
- Había una leve inclinación de la foto (mano no del todo firme): `deskew`
  la corrigió en ~1.8°.
- No se pidió corrección de perspectiva (comportamiento por defecto), así
  que ese paso queda `applied: false, requested: false`.
- La foto era grande (`3024x4032`, típica de un celular moderno):
  `normalize_scale` la redujo al límite de 1600px de lado mayor.
- El documento se veía un poco deslucido: `normalize_contrast` lo mejoró
  (nótese que `sharpness_after` es mayor que `sharpness_before`, la señal
  de que la mejora realmente ayudó, no perjudicó, la legibilidad).

### Un documento que ya estaba bien iluminado

Si la foto ya tenía buen contraste, el paso de contraste no la toca (para
no arriesgar "inventar" ruido o textura sobre algo que ya se lee bien):

```json
{
  "step": "normalize_contrast",
  "applied": false,
  "method": "clahe_lab_l_channel",
  "reason": "mejora habría degradado la nitidez, se descarta (salvaguarda anti sobre-procesamiento)",
  "std_before": 12.3,
  "std_after": 12.3,
  "sharpness_before": 1093.7,
  "sharpness_after": 1073.5
}
```

### Un PDF (sin `apply_exif_orientation`, misma preparación)

```http
GET /api/v1/jobs/b2c3d4e5f6a1
```

```json
{
  "job_id": "b2c3d4e5f6a1",
  "status": "ready",
  "confirmed": false,
  "result": {
    "processing_metadata": {
      "is_pdf": true,
      "pdf_pages": 1,
      "pdf_pages_ocr": 1,
      "preparation_trace": [
        { "step": "correct_orientation", "applied": false, "reason": "no fue necesario (orientación ya correcta)" },
        { "step": "deskew", "applied": false, "reason": "contenido insuficiente para estimar ángulo de skew" },
        { "step": "correct_perspective", "applied": false, "requested": false, "reason": "omitido: no solicitado (apply_perspective=False)" },
        { "step": "normalize_scale", "applied": false, "reason": "ya dentro del límite (no se achica)", "original_size": [1200, 1600], "final_size": [1200, 1600], "scale_factor": 1.0 },
        { "step": "normalize_contrast", "applied": false, "method": "clahe_lab_l_channel", "reason": "imagen casi uniforme (sin variación de intensidad detectable), nada que normalizar", "std_before": 0.0, "std_after": 0.0 }
      ]
    }
  }
}
```

Nótese que no hay entrada `apply_exif_orientation` ni `quality_gate` en
este caso: ninguno de los dos corre sobre PDF.

### Un PDF con texto nativo (sin `preparation_trace`)

Cuando el PDF ya trae texto seleccionable en todas sus páginas (no hace
falta renderizar ninguna imagen ni correr OCR), no hay ninguna preparación
de imagen que reportar — la clave `preparation_trace` directamente no
aparece:

```json
{
  "processing_metadata": {
    "engine": "PDF-NATIVE-TEXT",
    "is_pdf": true,
    "pdf_pages": 1,
    "pdf_pages_ocr": 0
  }
}
```

## Ver también

- Flujo completo de subida/revisión/confirmación:
  [docs/usuario/captura-ocr-local-agil.md](captura-ocr-local-agil.md).
- Control de calidad de captura y estado `needs_new_photo`:
  [docs/usuario/calidad-captura-mobile.md](calidad-captura-mobile.md).
- Detalle técnico del algoritmo de contraste, la salvaguarda y las
  decisiones de diseño:
  [docs/tecnica/preprocesamiento-documental-no-destructivo.md](../tecnica/preprocesamiento-documental-no-destructivo.md).
