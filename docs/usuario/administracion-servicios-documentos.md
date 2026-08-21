# Administración de servicios/documentos (`services.ini`) — guía de usuario

Cómo dar de alta un servicio/documento nuevo en el DATA evaluator (el
flujo por lotes de `scripts/evaluate_ocr_service.py`), y cómo consultar
los servicios ya configurados por HTTP.

> Esta guía aplica a `backend/config/services.ini` y al DATA evaluator.
> **No** afecta el flujo de captura en vivo del frontend
> (`/api/v1/jobs`), que usa un sistema de configuración distinto
> (`backend/app/templates/providers.py`) — ver
> [docs/tecnica/administracion-servicios-documentos.md](../tecnica/administracion-servicios-documentos.md)
> para el detalle de esa separación.

## 1. Dar de alta un servicio nuevo en `services.ini`

Cada servicio es una sección `[NOMBRE]` con `Title`, `Fields` (lista de
nombres de campo separados por coma) y, por cada nombre listado, un
bloque `Field.<nombre>.*` con `Label`, `Type`, `Required`, `Example` y
**`Regex` obligatoria** (`Patterns` es opcional, solo documental).

### Ejemplo correcto

```ini
[AGUA]
Title=Servicio de Agua
Fields=cuenta,importe

Field.cuenta.Label=Cuenta
Field.cuenta.Type=text
Field.cuenta.Required=true
Field.cuenta.Example=AG-00123
Field.cuenta.Patterns=cuenta|nro cuenta
Field.cuenta.Regex=(?:cuenta|nro cuenta)\D{0,40}([A-Z0-9\-]{4,20})

Field.importe.Label=Importe
Field.importe.Type=amount
Field.importe.Required=true
Field.importe.Example=$ 5.432,10
Field.importe.Patterns=importe|total
Field.importe.Regex=(?:importe|total)\D{0,40}(\d+[.,]\d{2})
```

Puntos clave:

- `Regex` siempre necesita **al menos un grupo de captura** (los
  paréntesis `(...)`) — es lo que se devuelve como valor extraído. Si la
  regex no tiene grupo, la validación rechaza el alta (ver ejemplo
  incorrecto abajo).
- `Patterns` es solo una ayuda de lectura humana (palabras clave de
  anclaje). El motor de extracción real **nunca la aplica** — no alcanza
  con declarar `Patterns` sin `Regex`.
- `Type` debe ser exactamente `text`, `amount` o `date`.
- `Required` debe ser exactamente `true` o `false` (sin `si`/`no`, sin
  mayúsculas).

### Ejemplo incorrecto (y el error exacto que produce)

Mismo servicio, pero sin declarar `Field.cuenta.Regex` (solo
`Patterns`):

```ini
[AGUA]
Title=Servicio de Agua
Fields=cuenta,importe

Field.cuenta.Label=Cuenta
Field.cuenta.Type=text
Field.cuenta.Required=true
Field.cuenta.Example=AG-00123
Field.cuenta.Patterns=cuenta|nro cuenta

Field.importe.Label=Importe
Field.importe.Type=amount
Field.importe.Required=true
Field.importe.Example=$ 5.432,10
Field.importe.Regex=(?:importe|total)\D{0,40}(\d+[.,]\d{2})
```

Al cargar la configuración (por el endpoint de introspección, el DATA
evaluator, o directamente `services_config.validate_services_schema()`),
esto falla con:

```text
Sección [AGUA], campo 'cuenta': falta 'Field.cuenta.Regex' (obligatoria
para todo campo — declarar únicamente 'Field.cuenta.Patterns' no es
suficiente, porque el motor de extracción real nunca la aplica).
```

Otros errores comunes y su causa (ver
[docs/tecnica/administracion-servicios-documentos.md](../tecnica/administracion-servicios-documentos.md)
para la lista completa):

- `Field.<nombre>.Type=email` (fuera de `text`/`amount`/`date`) → error
  listando los tipos permitidos.
- `Field.<nombre>.Required=si` → error exigiendo `true`/`false` exacto.
- `Field.<nombre>.Regex=\d{4,15}` (sin paréntesis, sin grupo de captura)
  → error exigiendo al menos un grupo de captura.
- Un nombre en `Fields` sin ningún bloque `Field.<nombre>.*` → error
  nombrando el campo faltante.
- Un bloque `Field.<nombre>.*` cuyo nombre no está en `Fields` → error de
  "bloque huérfano".

## 2. Validar y probar el alta con el DATA evaluator (CLI)

Una vez editado `services.ini`, correr el evaluador sobre una carpeta de
imágenes de muestra del servicio nuevo:

```powershell
python scripts\evaluate_ocr_service.py --service AGUA --samples _local_samples\agua --output _ocr_reports
```

- Si `services.ini` tiene un error de esquema, la carga falla con el
  mismo mensaje accionable descrito arriba (sección, campo, clave) — no
  hace falta esperar a procesar una imagen para descubrirlo.
- Si el esquema es válido, el evaluador procesa cada imagen de
  `--samples`, aplica `Field.<nombre>.Regex` sobre el texto OCR, y
  escribe un archivo `.DATA` por imagen en `--output` (o en
  `storage_bridge/ready/` con `--target bridge`), con una cabecera de
  campos y una línea de valores, separados por `;`.

## 3. Consultar servicios configurados por HTTP

Dos endpoints de solo lectura, sin autenticación, construidos sobre la
misma validación de esquema que usa el DATA evaluator. Requieren el
servidor levantado:

```powershell
uvicorn backend.app.main:app
```

### `GET /api/v1/services` — lista de servicios configurados

```http
GET /api/v1/services HTTP/1.1
Host: localhost:8000
```

Respuesta (`200 OK`, contra el `services.ini` real del repo — `GAS` y
`CEVT` recortado por espacio, ver ejemplo completo de `GAS` en el punto
siguiente):

```json
{
  "services": [
    {
      "id": "GAS",
      "title": "Servicio de Gas",
      "fields": [
        { "name": "importe", "label": "Importe", "type": "amount", "required": true, "example": "$ 23.345,56" },
        { "name": "cliente", "label": "Cliente", "type": "text", "required": true, "example": "045-987654" },
        { "name": "nro_medidor", "label": "Nro Medidor", "type": "text", "required": false, "example": "34572" },
        { "name": "a_pagar_hasta", "label": "A pagar hasta", "type": "date", "required": false, "example": "20/06/2026" },
        { "name": "periodo", "label": "Periodo", "type": "text", "required": false, "example": "01/2026" }
      ]
    },
    {
      "id": "CEVT",
      "title": "Servicio CEVT",
      "fields": [
        { "name": "medidor_numero", "label": "Medidor N°", "type": "text", "required": false, "example": "12345" },
        { "name": "periodo", "label": "Periodo", "type": "text", "required": false, "example": "01/2026" },
        { "name": "vencimiento", "label": "Vencimiento", "type": "date", "required": false, "example": "15/12/2024" },
        { "name": "codigo_pago_electronico", "label": "Código de Pago Electrónico", "type": "text", "required": false, "example": "ABC123456" },
        { "name": "total_a_pagar", "label": "Total a Pagar", "type": "amount", "required": false, "example": "$ 1.234,56" }
      ]
    }
  ]
}
```

Si `services.ini` no tiene ninguna sección todavía, responde `200` con
`{"services": []}` — no es un error.

### `GET /api/v1/services/{service_id}` — detalle de un servicio

`service_id` se normaliza igual que en el resto de la API
(`strip().upper()`), así que `gas`, `GAS`, ` gas ` o `%20gas%20`
resuelven al mismo servicio.

```http
GET /api/v1/services/gas HTTP/1.1
Host: localhost:8000
```

Respuesta (`200 OK`):

```json
{
  "id": "GAS",
  "title": "Servicio de Gas",
  "fields": [
    { "name": "importe", "label": "Importe", "type": "amount", "required": true, "example": "$ 23.345,56" },
    { "name": "cliente", "label": "Cliente", "type": "text", "required": true, "example": "045-987654" },
    { "name": "nro_medidor", "label": "Nro Medidor", "type": "text", "required": false, "example": "34572" },
    { "name": "a_pagar_hasta", "label": "A pagar hasta", "type": "date", "required": false, "example": "20/06/2026" },
    { "name": "periodo", "label": "Periodo", "type": "text", "required": false, "example": "01/2026" }
  ]
}
```

Servicio no configurado:

```http
GET /api/v1/services/UNKNOWN HTTP/1.1
Host: localhost:8000
```

Respuesta (`404 Not Found`):

```json
{
  "detail": "Servicio 'UNKNOWN' no está configurado en services.ini."
}
```

Si `services.ini` tuviera una sección con un error de esquema, ambos
endpoints responden `500` con el mismo mensaje accionable de sección,
campo y clave descrito en la sección 1 — nunca una traza cruda sin
explicación.

## Qué NO hace esta guía

- No cubre el flujo de captura en vivo del frontend (`/api/v1/jobs`,
  carga de imagen desde el navegador) — ver
  [docs/usuario/gas.md](gas.md) para ese flujo, que usa un sistema de
  configuración Python distinto (`templates/providers.py`), no
  `services.ini`.
- No incluye una UI para editar `services.ini` desde el navegador. El
  alta sigue siendo edición manual del archivo de texto plano.
