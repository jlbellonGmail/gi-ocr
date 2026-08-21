# Administración de servicios/documentos (`services.ini`) — documentación técnica

Profesionaliza el alta de servicios/documentos configurables en
`backend/config/services.ini` (ADR-007, ver
[arquitectura.md](arquitectura.md)): valida su esquema formalmente,
corrige una desconexión real entre esa configuración y el motor de
extracción, y expone un endpoint de solo lectura para introspección. Vive
dentro del subsistema **DATA evaluator**
(`backend/app/services_config.py`, `backend/app/extraction_engine.py`,
`backend/app/document_services.py`, `scripts/evaluate_ocr_service.py`).

## Alcance: qué toca esta feature y qué no

`services.ini` **no** es la única forma de definir un servicio/proveedor
en este repo. Hoy existen **tres mecanismos independientes**:

1. **`services.ini` + `services_config.py` + `extraction_engine.py`** —
   usado solo por el DATA evaluator (`scripts/evaluate_ocr_service.py`).
   **Es el único que toca esta feature.**
2. **`backend/app/templates/providers.py`** — dataclasses Python
   hardcodeadas por proveedor (`ProviderTemplate`/`FieldTemplate`) con
   ROI + anclas + regex + validadores tipados, usadas por el **pipeline
   HTTP en vivo** (`backend/app/capture_pipeline.py`, `classifier.py`,
   endpoint `/api/v1/jobs`). **No afectado por esta feature.** Editar
   `services.ini` **no** cambia el comportamiento de captura en vivo —
   son sistemas de configuración completamente distintos, con motores de
   Python separados. Un futuro mantenedor no debe asumir lo contrario.
3. **`backend/app/gas_extractor.py`** — extractor Python específico de
   GAS, usado solo por `t3_2_orchestrator.py` (fixtures T3.2 antiguas).
   Tampoco afectado.

Unificar los tres mecanismos es un cambio de arquitectura mayor, no
pedido por el ítem `16` de `ROADMAP.md` (que dice explícitamente "en
`services.ini`"), y queda fuera de alcance.

## Esquema formal de `services.ini`

Validado por `backend/app/services_config.py::validate_services_schema()`
(y las funciones internas `_validate_section_schema`/
`_validate_field_block` que usa). No usa caché: relee el archivo en cada
llamada (`_load_parser()`), por lo que cambios en caliente se reflejan sin
reiniciar el proceso — confirmado por
`test_hot_reload_reflects_changes_without_restart` en
`backend/tests/test_services_config_schema.py`.

### Por sección (servicio)

| Clave | Obligatoria | Regla |
|---|---|---|
| `Title` | sí | No vacía. |
| `Fields` | sí | Lista no vacía, separada por comas, sin nombres duplicados (comparación case-insensitive) ni vacíos. |

### Por campo declarado en `Fields`

Cada nombre listado en `Fields` debe tener un bloque
`Field.<nombre>.*` con:

| Clave | Obligatoria | Regla |
|---|---|---|
| `Label` | sí | No vacía. |
| `Type` | sí | Uno de `text`, `amount`, `date` (`services_config.ALLOWED_FIELD_TYPES`). |
| `Required` | sí | Exactamente `true` o `false` (comparación case-sensitive; no se aceptan variantes localizadas como `si`/`no`/`True`, ni se asume `false` por defecto ante clave ausente o vacía). |
| `Example` | sí | No vacía. |
| `Regex` | **sí** | Debe compilar con `re.compile` y tener **al menos un grupo de captura**. |
| `Patterns` | no | Opcional, puramente **documental** (ver más abajo). Si está presente, solo se exige que no esté vacía; no se valida su formato. |

No se permiten **bloques huérfanos**: si existe cualquier clave
`Field.<nombre>.*` para un `<nombre>` que no está en `Fields` de esa
sección, la validación falla.

### Por qué `Regex` es obligatoria y `Patterns` es solo documental

Decisión tomada explícitamente en el intento 2 del spec (ver
`runs/16-administracion-servicios-documentos/decision.md`), corrigiendo
una ambigüedad señalada por el `reviewer-agent` en el intento 1: si
`Patterns` fuera una alternativa válida a `Regex`, un campo declarado
solo con `Patterns` pasaría la validación "profesional" y sin embargo
seguiría cayendo para siempre en el fallback genérico (ver más abajo) —
reproduciendo exactamente el defecto de "documentación muerta" que esta
feature corrige. Por eso `Regex` es obligatoria para todo campo válido y
`Patterns` pasa a ser exclusivamente informativo (palabras clave de
anclaje separadas por `|`, sin grupo de captura) para quien lee
`services.ini` a ojo — nunca aplicado por el motor de extracción real.

### Mensajes de error

Todos los errores de esquema levantan
`services_config.ServicesConfigError` (subclase de `ValueError`) con un
mensaje que **siempre** nombra sección, campo y clave exacta
involucrados — nunca una traza cruda de `configparser`/`KeyError`/
`re.error`. Ejemplos reales (ver
`backend/tests/test_services_config_schema.py`):

- `Sección [TEST]: falta la clave 'Fields' o está vacía (debe listar al
  menos un nombre de campo separado por comas).`
- `Sección [TEST], campo 'cliente': falta 'Field.cliente.Label' (no puede
  estar vacío).`
- `Sección [TEST]: existe un bloque 'Field.huerfano.*' pero 'huerfano' no
  está declarado en 'Fields' de esa sección (bloque huérfano).`
- `Sección [TEST], campo 'email': 'Field.email.Type' inválido ('email').
  Debe ser uno de: text, amount, date.`
- `Sección [TEST], campo 'importe': 'Field.importe.Required' debe ser
  exactamente 'true' o 'false' (valor actual: 'si').`
- `Sección [TEST], campo 'importe': 'Field.importe.Regex' no compila como
  expresión regular válida: missing ), unterminated subpattern at
  position 0.`
- `Sección [TEST], campo 'importe': 'Field.importe.Regex' debe tener al
  menos un grupo de captura, para no capturar el match completo
  (incluyendo texto de anclaje) como valor.`
- `Sección [TEST], campo 'cliente': falta 'Field.cliente.Regex'
  (obligatoria para todo campo — declarar únicamente
  'Field.cliente.Patterns' no es suficiente, porque el motor de
  extracción real nunca la aplica).`
- `Sección [TEST]: campo duplicado 'importe' en 'Fields'.`

También se envuelven con el mismo tipo de mensaje accionable (no traza
cruda):

- Encoding no UTF-8/corrupto (`UnicodeDecodeError` durante
  `configparser.read()`).
- Secciones duplicadas (`configparser.DuplicateSectionError`), con
  sección y línea si `configparser` la expone.
- Claves duplicadas dentro de una misma sección
  (`configparser.DuplicateOptionError`).

## El bug de desconexión corregido

**Verificado leyendo el código real, no asumido.** Antes de esta feature,
`services_config.py::get_service_config()` solo exponía tres claves por
servicio: `fields` (lista de `Fields`), `zones` (clave de sección en
minúscula `zones=`, formato `campo:x1,y1,x2,y2`) y `patterns` (clave de
sección en minúscula `patterns=`, formato `campo:regex`). **Ninguna**
sección real de `services.ini` (`GAS`, `CEVT`) declara esas dos últimas
claves en minúscula — solo existen los bloques `Field.<nombre>.Patterns`/
`Field.<nombre>.Regex` por campo, con el prefijo `Field.` y mayúscula
inicial. El resultado: `zones` y `patterns` en el dict devuelto por
`get_service_config()` estaban **siempre vacíos**, y
`extraction_engine.py::extract_service_fields()` nunca llegaba a aplicar
ninguna regex declarativa — caía siempre en `_extract_generic()`, una
heurística genérica por palabra clave en el **nombre del campo**, no en
el contenido de `services.ini`.

### Ejemplo concreto: `cliente` de `GAS`

`services.ini` declara `Field.cliente.Example=045-987654` (con guion) y
`Field.cliente.Regex=(?:cliente|nro cliente|n° cliente|numero
cliente)\D{0,40}([0-9\-]{6,20})`.

Para el texto OCR normalizado `"Medidor 12345678 Cliente 045-987654"`:

- `_extract_generic("cliente", texto)` busca `\d{8,10}` (dígitos puros,
  sin guion ni anclaje de contexto) en **todo** el texto. `"12345678"`
  (el número de **medidor**, no de cliente) es una corrida exacta de 8
  dígitos y matchea primero — se devuelve tal cual. **Resultado
  incorrecto: `"12345678"`.**
- `Field.cliente.Regex`, si se aplica, ancla primero a la palabra
  `"cliente"` y solo entonces captura el grupo `([0-9\-]{6,20})` que
  sigue — devuelve correctamente `"045-987654"`.

Este no es un caso hipotético: es el resultado real que produce el
código, verificado por trazado directo y cubierto por
`backend/tests/test_services_config_schema.py::
test_extract_generic_reproduces_the_documented_bug` (reproduce el bug
tal como existía) y
`test_extract_service_fields_gas_cliente_uses_declared_regex`
(verifica la corrección).

### La corrección

1. `services_config.get_service_field_regex(service)` — función nueva
   que expone, por campo, la regex declarada en `Field.<nombre>.Regex`
   (el namespace **real**, con el prefijo `Field.` y mayúscula inicial —
   distinto del namespace `zones=`/`patterns=` en minúscula, que sigue
   sin uso real).
2. `services_config.get_service_config(service)["field_regex"]` — se
   agregó esta clave nueva al dict que ya devolvía la función, sin
   remover `zones`/`patterns` (se conservan por compatibilidad hacia
   atrás, documentadas como muertas más abajo).
3. `extraction_engine.py::extract_service_fields()` — se agregó
   `_extract_with_field_regex(field, text, field_regex)`, que aplica la
   regex declarada con `re.search(..., flags=re.IGNORECASE)` y devuelve
   `match.group(1)` (siempre el primer grupo de captura, nunca
   `match.group(0)` — a diferencia de `_extract_with_patterns`, que sí
   cae a `group(0)` si no hay grupos, un comportamiento que aquí se evita
   porque el esquema ya garantiza al menos un grupo). Se intercala en el
   orden de resolución de cada campo, **antes** del fallback genérico:

   1. Si hay zona configurada para el campo (mecanismo `zones=`, hoy sin
      uso real) y hay imagen, se intenta con el texto de esa zona.
   2. **Si el campo declara `Field.<nombre>.Regex`, se aplica sobre el
      texto completo normalizado** (el camino real, antes inexistente).
   3. Si no hay `Regex` declarada o no matcheó, se intenta con
      `Patterns` de sección en minúscula (mecanismo legado, hoy siempre
      vacío en `services.ini` real).
   4. Fallback final: `_extract_generic()`, la heurística por palabra
      clave — sin cambios, se mantiene como red de seguridad.

`_extract_generic()` **no se modificó**. Sigue siendo alcanzado solo si:

- un campo llega a `extract_service_fields` sin `Field.<nombre>.Regex`
  declarada (una configuración que no pasó por
  `validate_services_schema()`, por ejemplo un `services.ini` editado a
  mano sin revalidar — cubierto por
  `test_extract_generic_still_used_as_fallback_without_declared_regex`),
  o
- la regex declarada es válida pero no matchea nada en el texto real
  (regex demasiado estricta o texto sin el dato — comportamiento
  preexistente, sin cambios; el campo termina en `missing_fields`, no
  con un valor incorrecto).

## `Field.<nombre>.Patterns`: metadata documental, nunca aplicada

`extraction_engine._extract_with_patterns` existe y funciona (hace
`re.search` y devuelve `group(1)` si hay grupos, si no `group(0)`), pero
hoy solo se alimenta de `services_config.get_service_patterns()`, que lee
la clave de sección en minúscula `patterns=` — **no** el namespace
`Field.<nombre>.Patterns`. Ninguna sección real de `services.ini`
declara esa clave de sección en minúscula, así que
`get_service_patterns()` siempre devuelve `{}` para `GAS`/`CEVT`.

Los valores reales de `Field.<nombre>.Patterns` (ej.
`Field.cliente.Patterns=cliente|nro cliente|n° cliente|numero cliente`)
son alternancias de palabras clave **sin ningún grupo de captura**. Si se
conectaran tal cual a `_extract_with_patterns`, devolverían el texto del
ancla matcheado (`match.group(0)`, ej. la palabra `"cliente"` misma), no
el valor real — conectarlo sin rediseñar el formato produciría salidas
incorrectas, no una alternativa funcional a `Regex`. Por eso esta
feature deja `Patterns` como metadata opcional y puramente documental
(ayuda de lectura humana de qué palabras ancla la regex), y exige
`Regex` obligatoria como el único mecanismo real de extracción
declarativa. Rediseñar `Patterns` para que sea funcional (agregar
grupos, redefinir su sintaxis) es trabajo nuevo, no pedido por el ítem
`16` de `ROADMAP.md`.

## Tercer mecanismo muerto: `zones=`/`patterns=` en minúscula

`services_config.py::get_service_zones()`/`get_service_patterns()` leen
claves de **sección** (no de campo) llamadas `zones=` y `patterns=`, en
minúscula, con formato multilínea `campo:valor`. **Ningún** `services.ini`
real usa hoy esas claves — es un **tercer** mecanismo de configuración,
completamente muerto, distinto tanto del namespace `Field.<nombre>.*`
(el vigente) como del bug corregido arriba. Se conservan en el código
(y en `get_service_config()`) por compatibilidad hacia atrás y porque
`extraction_engine.py` ya tiene la lógica de zonas/imagen lista para
usarlas si algún día se declaran, pero **no se debe invertir tiempo
investigándolas como si fueran el mecanismo vigente**: hoy no tienen
ningún efecto observable porque ninguna sección las declara.

## Relación entre `services.ini` y `document_services.json`

`backend/config/document_services.json` es un **inventario separado**
(`data_evaluator_enabled`, `expected_fields` por servicio) que gatea si
el DATA evaluator corre para un servicio dado — no reemplaza ni fusiona
con `services.ini`. Ya existe un test de consistencia parcial entre
ambos: `backend/tests/test_document_services_inventory.py::
test_inventory_data_evaluator_contract_t23`, que valida que
`expected_fields` (JSON) coincide exactamente con `Fields` (INI). Esta
feature **no** reemplaza ese mecanismo ni lo rompe; agrega, además,
validación de esquema **dentro** de `services.ini` (algo que ese test no
cubre: no valida que cada `Field.<nombre>.*` esté completo o bien
formado, solo que la lista de nombres coincida entre los dos archivos).

No se fusionan ambos archivos en esta feature: es un cambio de
arquitectura mayor no pedido por el ítem `16` de `ROADMAP.md`.

## Endpoint de introspección `GET /api/v1/services[/{service_id}]`

`backend/app/main.py` expone, de solo lectura, el esquema validado sobre
`services_config.list_services_schema()`/`get_service_schema()`:

- `GET /api/v1/services` → `{"services": [{"id", "title", "fields": [...]}, ...]}`.
  `services.ini` sin secciones responde `200` con `{"services": []}`, no
  un error (estado válido: "no hay servicios configurados todavía").
- `GET /api/v1/services/{service_id}` → detalle de un servicio. Normaliza
  `service_id` igual que `document_services.normalize_service_id`
  (`strip().upper()`), así que `gas`, `GAS`, ` gas ` y `%20gas%20`
  resuelven al mismo servicio `GAS`.
  - Servicio no configurado → `404` con mensaje claro (nunca `500`).
  - Sección con esquema inválido → `500` con el **mismo mensaje** que
    produce `ServicesConfigError` al validar la carga (sección, campo y
    clave exactos) — nunca un `500` sin explicación ni una traza cruda.

Sin autenticación (es de solo lectura, sin datos sensibles: expone
nombres de campos y metadata de configuración, no comprobantes ni datos
de clientes) — igual que el resto de `/api/v1/*` hoy. `14-seguridad-privacidad-documentos`
queda pendiente en el backlog para eso.

Este endpoint es un sistema **separado** del pipeline HTTP en vivo de
`/api/v1/jobs` — no expone ni afecta las plantillas de
`templates/providers.py`.

## Algoritmo de validación (resumen)

`validate_services_schema(cfg=None)`:

1. Si no se pasa un `ConfigParser` ya cargado, llama a `_load_parser()`
   (que ya envuelve errores de lectura/parseo en `ServicesConfigError`).
2. Para cada sección: valida `Title` y `Fields` (no vacíos, sin
   duplicados case-insensitive dentro de `Fields`).
3. Calcula los nombres de campo con al menos una clave `Field.<nombre>.*`
   declarada (`_iter_field_block_names`) y los compara contra `Fields`:
   cualquier nombre en el primer conjunto que no esté en el segundo es un
   bloque huérfano → error.
4. Para cada nombre en `Fields`, valida su bloque completo
   (`_validate_field_block`): `Label`, `Type`, `Required`, `Example`,
   `Regex` (compila + tiene grupo de captura) y, si está presente,
   `Patterns` no vacía.

`list_services_schema()`/`get_service_schema(service)` reusan
`_validate_section_schema` internamente antes de construir la respuesta
expuesta por la API — así una sección inválida nunca llega a construir
una respuesta parcial o inconsistente.

## Casos borde

- `Type=amount` sin ninguna referencia de moneda en `Regex`/`Patterns`:
  **no** es un error de esquema (no hay forma automática de saber si es
  intencional). Queda como responsabilidad del autor del alta.
- `Field.<nombre>.Regex` que compila y tiene grupo de captura pero nunca
  matchea nada en el texto real (regex demasiado estricta): **no** es un
  error de esquema — el campo cae en `missing_fields`, comportamiento
  preexistente sin cambios.
- Un campo declara `Field.<nombre>.Patterns` pero no `Field.<nombre>.Regex`:
  **sí** es un error de esquema explícito — ver criterio de mensajes
  arriba.
- `services.ini` no existe todavía: `_load_parser()` lo autocrea vacío;
  cero secciones sigue siendo válido.
- Codificación no UTF-8/corrupta: mensaje claro, no traza cruda.
- Secciones duplicadas: `configparser.DuplicateSectionError` envuelto en
  el mismo tipo de mensaje accionable.
- `GET /api/v1/services/{service_id}` con minúsculas/espacios: se
  normaliza igual que `document_services.normalize_service_id`.
- Cambios en caliente sin reiniciar el proceso: confirmado por test
  (`test_hot_reload_reflects_changes_without_restart`), no asumido.

## Tests

- `backend/tests/test_services_config_schema.py`: criterios 1–11 del
  spec (esquema completo + regresión del bug de desconexión, `GAS` y
  `CEVT`).
- `backend/tests/test_services_admin_api.py`: criterio 12 (endpoint de
  introspección, casos borde de archivo vacío/sección inválida,
  normalización de `service_id`).
- Sin regresión sobre `test_document_services_inventory.py`,
  `test_gas_extractor.py`, `test_empty_text.py`,
  `test_evaluate_ocr_service_data_output.py` (verificado corriendo la
  suite completa).
