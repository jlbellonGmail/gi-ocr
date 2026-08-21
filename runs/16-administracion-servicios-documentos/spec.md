# Spec: Administración de servicios/documentos (`services.ini`)

## Alcance

Profesionalizar el alta de proveedores/documentos configurables en
`backend/config/services.ini` (ADR-007), dentro del subsistema **DATA
evaluator** (`backend/app/services_config.py`, `extraction_engine.py`,
`document_services.py`, `service_data_validation.py`,
`scripts/evaluate_ocr_service.py`). Incluye:

1. **Esquema formal y validado de `services.ini`**, documentado y exigible
   al cargar la configuración:
   - Por sección (servicio): `Title` (no vacío) y `Fields` (lista no vacía,
     sin duplicados, separada por `,`).
   - Por campo declarado en `Fields`: debe existir un bloque
     `Field.<nombre>.*` con `Label` (no vacío), `Type` (uno de
     `text`|`amount`|`date`), `Required` (`true`/`false`, sin variantes
     localizadas), `Example` (no vacío) y **`Regex` obligatoria** (ya no
     "al menos uno de Patterns/Regex" — ver "Riesgos/supuestos" para la
     justificación de esta decisión, corregida en el intento 2 tras
     feedback del reviewer-agent). `Field.<nombre>.Patterns` pasa a ser
     **opcional**: si está presente, es metadata puramente documental
     (palabras clave de anclaje separadas por `|`, sin grupo de captura),
     nunca aplicada por el motor de extracción; no se valida su formato
     más allá de ser texto no vacío cuando está presente.
   - `Field.<nombre>.Regex` debe compilar como regex Python válida y tener
     **al menos un grupo de captura** (evita el defecto de capturar el
     match completo, incluyendo texto de anclaje, como valor final).
   - Todo bloque `Field.<nombre>.*` debe corresponder a un nombre listado
     en `Fields` de su sección (no se permiten bloques huérfanos sin
     declarar).
   - Errores de validación deben ser específicos y accionables: sección,
     campo y clave exactos involucrados — no una traza cruda de
     `configparser`/`KeyError`.
2. **Corrección de una desconexión real detectada en el código actual**
   (ver "Contexto"): `backend/app/services_config.py` hoy nunca lee
   `Field.<nombre>.Regex`/`Patterns`/`Type`/`Required` — el motor de
   extracción configurable (`extraction_engine.py`, usado por
   `scripts/evaluate_ocr_service.py`) cae siempre en su fallback genérico
   por palabra clave (`_extract_generic`), ignorando en silencio la regex
   declarativa que ya existe, y que cualquier persona que dé de alta un
   servicio nuevo copiando el patrón de `[GAS]`/`[CEVT]` asumiría que se
   usa. Esta feature debe exponer esa metadata estructurada (vía una
   función nueva o una extensión de `get_service_config`) y **hacer que
   `extraction_engine.py` la use realmente** para los campos que declaren
   `Field.<nombre>.Regex` (ahora obligatoria en el esquema, ver punto 1) —
   sin lo cual "profesionalizar" el esquema sería formalizar configuración
   que no tiene ningún efecto observable.
3. **`Required` deja de ser decorativo**: la metadata de requerido, tipo y
   ejemplo por campo debe quedar disponible para quien consume la
   configuración (endpoint de introspección de este mismo spec, y
   documentación), no solo escrita en el `.ini` sin lector.
4. **Endpoint de solo lectura `GET /api/v1/services` y
   `GET /api/v1/services/{service_id}`** en `backend/app/main.py`, que
   expone el esquema validado (`title`, campos con `label`/`type`/
   `required`/`example`) de los servicios configurados en `services.ini`.
   Es la forma más directa de cumplir "documentación automática" (texto
   literal del ítem `16` de `ROADMAP.md`) y de dar un ejemplo HTTP real
   para `docs/usuario/` (ver "Riesgos/supuestos" sobre por qué se decide
   agregar este endpoint en vez de usar solo ejemplos de CLI).
5. **Guía de alta de un servicio nuevo** en la documentación de usuario,
   con un ejemplo de configuración **correcta** y uno **incorrecto** (con
   el error que produce y por qué), más el flujo CLI real
   (`scripts/evaluate_ocr_service.py --service <NUEVO>`).
6. **Tests contractuales** en `backend/tests/` (pytest) que verifiquen:
   alta válida carga sin error y produce el esquema esperado; cada clase
   de alta inválida falla con mensaje específico; la extracción usa
   realmente `Field.<nombre>.Regex` cuando está declarado (regresión del
   punto 2); el endpoint de introspección responde consistentemente con
   `services.ini`.

**Explícitamente NO incluye:**

- No cambia el motor OCR (RapidOCR/ONNX, ADR-006), ni el formato
  `.DATA`/`services.ini` como texto plano (ADR-007), ni la separación
  OCR/extracción/validación/storage. Es una decisión de arquitectura
  vigente, no se reabre.
- No toca el pipeline HTTP en vivo de captura
  (`backend/app/capture_pipeline.py`, `classifier.py`,
  `templates/providers.py`, usados por `/api/v1/jobs`). Ese pipeline usa
  un sistema **distinto** y hoy no relacionado: plantillas Python
  hardcodeadas (`ProviderTemplate`/`FieldTemplate`) con ROI + regex +
  validadores tipados, no `services.ini`. Ver "Riesgos/supuestos" para el
  detalle de esta fragmentación real del repo y por qué no se resuelve
  acá.
- No toca `backend/app/gas_extractor.py` (un tercer extractor Python
  específico de GAS, usado solo por `t3_2_orchestrator.py`/fixtures T3.2).
  Es otro camino paralelo, fuera de alcance de esta feature.
- No fusiona `services.ini` (config de extracción) con
  `document_services.json` (inventario de habilitación del DATA
  evaluator) en un único archivo. Se documenta la relación entre ambos y
  se valida que no diverjan (ya existe un test parcial,
  `test_inventory_data_evaluator_contract_t23`), pero fusionarlos es un
  cambio de arquitectura mayor no pedido por `ROADMAP.md` ítem 16.
- No conecta `Field.<nombre>.Patterns` al motor de extracción real. Se
  mantiene como metadata opcional, puramente documental (ver Alcance
  punto 1 y "Riesgos/supuestos" para la justificación de esta decisión).
  Rediseñar el formato de `Patterns` para que sea un patrón de captura
  funcional es trabajo nuevo, no pedido por este ítem del roadmap.
- No agrega autenticación/autorización al endpoint nuevo de introspección
  (es de solo lectura, sin datos sensibles — expone únicamente nombres de
  campos y regex de configuración, no comprobantes ni datos de clientes).
  Igual que el resto de `/api/v1/*` hoy, sin auth (`14-seguridad-privacidad-documentos`
  queda pendiente en el backlog para eso).
- No agrega una UI de administración en el frontend para editar
  `services.ini` desde el navegador. El alta sigue siendo edición manual
  del archivo de texto plano (ADR-007); esta feature profesionaliza la
  validación y documentación de esa edición manual, no la reemplaza por
  una UI.

## Contexto

`backend/config/services.ini` (ADR-007) declara hoy dos servicios (`GAS`,
`CEVT`), cada uno con 5 campos, y cada campo con un bloque rico
`Field.<nombre>.Label/Example/Type/Required/Patterns/Regex`. Ese formato
es exactamente el que documenta `docs/tecnica/gas.md` como "la"
configuración del servicio.

Sin embargo, **verificado en el código real, no asumido**:
`backend/app/services_config.py::get_service_config()` solo lee tres
claves por sección: `Fields` (lista de nombres), `zones` (formato
multilínea `campo:x1,y1,x2,y2`) y `patterns` (formato multilínea
`campo:regex`, en minúscula, plano, sin el prefijo `Field.`). Ninguna
sección real de `services.ini` usa esas dos últimas claves en minúscula
— ambas están siempre vacías para `GAS`/`CEVT`. El resultado es que
`extraction_engine.py::extract_service_fields()`, usado por
`scripts/evaluate_ocr_service.py` (el "DATA evaluator" mencionado en
`ROADMAP.md`), **nunca aplica los `Field.<nombre>.Regex` declarados** y
cae siempre en `_extract_generic()`, una heurística genérica por palabra
clave en el nombre del campo, no en el contenido de `services.ini`.

Esto no es solo una inconsistencia de documentación: produce salidas
incorrectas verificables hoy mismo. Por ejemplo, para el campo `cliente`
de GAS, cuyo propio `Field.cliente.Example=045-987654` (con guion) ya
declarado en `services.ini`:

- `_extract_generic("cliente", "Cliente: 045-987654")` busca
  `\d{8,10}` (dígitos puros, sin guion) en todo el texto. Como
  `"045-987654"` no es una corrida continua de 8-10 dígitos (el guion la
  parte en `"045"` y `"987654"`), no matchea nada y cae al último
  fallback (`text_clean[:10]`), devolviendo `"Cliente: 0"` — un valor sin
  sentido.
- `Field.cliente.Regex=(?:cliente|nro cliente|n° cliente|numero
  cliente)\D{0,40}([0-9\-]{6,20})`, si se aplicara (que hoy no se
  aplica), captura correctamente `"045-987654"`.

Esta feature corrige esa desconexión como parte de "profesionalizar el
alta": una configuración que no tiene efecto en el comportamiento no es
una configuración profesional, es documentación muerta.

`document_services.json` (inventario separado, con `data_evaluator_enabled`
y `expected_fields` por servicio) gatea si el DATA evaluator corre para un
servicio dado. Ya existe un test de consistencia parcial entre ambos
archivos (`backend/tests/test_document_services_inventory.py::test_inventory_data_evaluator_contract_t23`),
que valida que `expected_fields` (JSON) coincide exactamente con `Fields`
(INI). Esta feature no reemplaza ese mecanismo, lo mantiene como
prerequisito de consistencia y agrega validación de esquema **dentro**
de `services.ini` (algo que ese test no cubre: no valida que cada
`Field.<nombre>.*` esté completo/bien formado, solo que la lista de
nombres coincida entre los dos archivos).

## Criterios de aceptación

1. Existe una función de validación de esquema para `services.ini`
   (nueva, en `backend/app/services_config.py` o módulo asociado) que,
   dado el contenido actual del archivo, no lanza ningún error — el
   `services.ini` real (`GAS`, `CEVT`) es válido según el esquema
   definido en "Alcance", punto 1 (los 10 campos reales de `GAS`/`CEVT`
   ya declaran `Regex`, verificado leyendo `services.ini`, por lo que
   exigirla obligatoria no rompe este criterio). Test de regresión
   explícito.
2. La misma función, ante una sección con `Fields` vacío o ausente,
   lanza un error específico que nombra la sección y la clave faltante
   (no un `KeyError` genérico ni un `configparser.Error` crudo).
3. Ante un campo listado en `Fields` sin bloque `Field.<nombre>.*`
   correspondiente (ninguna clave `Label`/`Type`/`Required`/`Example`
   para ese nombre), la validación falla nombrando la sección y el campo
   exacto que falta.
4. Ante un bloque `Field.<nombre>.*` cuyo nombre no está en `Fields` de
   su sección (bloque huérfano), la validación falla nombrando la
   sección y el nombre de campo huérfano.
5. Ante `Field.<nombre>.Type` con un valor fuera de
   `{text, amount, date}` (ej. `Type=email`), la validación falla y el
   mensaje lista los tipos permitidos.
6. Ante `Field.<nombre>.Required` con un valor distinto de `true`/`false`
   (ej. `Required=si`, `Required=` vacío, clave ausente), la validación
   falla — no se asume `false` por defecto en silencio.
7. Ante `Field.<nombre>.Regex` con una expresión regular inválida (no
   compila con `re.compile`), la validación falla incluyendo el mensaje
   de error de `re.error` y el campo/sección donde ocurre.
8. Ante `Field.<nombre>.Regex` válida pero **sin ningún grupo de
   captura** (ej. `Regex=\d{4,15}` sin paréntesis), la validación falla
   explicando que se requiere al menos un grupo de captura para no
   capturar el match completo (incluyendo texto de anclaje) como valor.
9. Ante un campo sin `Field.<nombre>.Regex` (clave ausente, vacía, o sin
   ese bloque), la validación falla indicando que `Regex` es obligatoria
   para todo campo — declarar únicamente `Field.<nombre>.Patterns` ya no
   es suficiente, porque `Patterns` es metadata documental que el motor
   de extracción real nunca aplica (ver Alcance punto 1 y
   "Riesgos/supuestos" para la justificación de esta decisión).
10. Ante nombres de campo duplicados dentro de `Fields=` de una misma
    sección (ej. `Fields=importe,importe,cliente`), la validación falla
    nombrando el duplicado.
11. **Corrección del bug de desconexión (ver "Contexto")**:
    `extraction_engine.py::extract_service_fields()` usa efectivamente
    `Field.<nombre>.Regex` (ahora obligatoria en el esquema para todo
    campo válido, ver Alcance punto 1) cuando está declarado en
    `services.ini`, en vez de caer directo en `_extract_generic()`. Test
    de regresión con texto OCR sintético normalizado `"Medidor 12345678
    Cliente 045-987654"` para el servicio `GAS`: el campo `cliente` debe
    quedar en `"045-987654"` (vía `Field.cliente.Regex`, anclado a la
    palabra "cliente"), **no** `"12345678"` — el resultado incorrecto que
    produce hoy `_extract_generic("cliente", texto)` para ese mismo
    input, verificado por trazado directo del código: la regex de
    fallback `\d{8,10}` matchea la corrida de 8 dígitos `"12345678"` (el
    número de **medidor**, no de cliente) y la devuelve tal cual, sin
    llegar a `text_clean[:10]`. `_extract_generic` se mantiene sin
    cambios como fallback defensivo, alcanzado sólo si un campo llega a
    `extract_service_fields` sin `Field.<nombre>.Regex` declarada (una
    configuración que no pasó por la validación de esquema del punto 1,
    ej. un `services.ini` editado a mano sin revalidar) o si la regex
    declarada es válida pero no matchea nada en el texto real
    (comportamiento ya cubierto, sin cambios, en "Casos borde").
12. Existen `GET /api/v1/services` (lista de servicios configurados con
    su esquema: `id`, `title`, `fields: [{name, label, type, required,
    example}]`) y `GET /api/v1/services/{service_id}` (detalle de un
    servicio) en `backend/app/main.py`, de solo lectura, construidos
    sobre la función de validación del punto 1. `GET
    /api/v1/services/UNKNOWN` (servicio no configurado) responde `404`
    con mensaje claro, no `500`. Si `services.ini` tuviera una sección
    inválida según el esquema, el endpoint no debe devolver `500` sin
    explicación: debe distinguir claramente en la respuesta o en logs
    qué sección falla y por qué (mismo mensaje que produce la validación
    de carga).
13. Existe una guía de alta de servicio en
    `docs/usuario/administracion-servicios-documentos.md` con: un
    ejemplo de sección `services.ini` **correcta** (servicio nuevo
    ficticio, distinto de GAS/CEVT, con `Label`/`Type`/`Required`/
    `Example`/`Regex` obligatorios por campo, `Patterns` opcional), un
    ejemplo **incorrecto** con un error real de los cubiertos en los
    criterios 2–10 (ej. `Regex` ausente, o `Regex` sin grupo de captura)
    y el mensaje de error exacto que produce, el flujo CLI
    (`scripts/evaluate_ocr_service.py --service <NUEVO> --samples
    <dir>`) y al menos un ejemplo de uso HTTP completo (request +
    response) de `GET /api/v1/services` y de
    `GET /api/v1/services/{service_id}` contra `services.ini` real.
14. Debe existir `docs/tecnica/administracion-servicios-documentos.md`,
    no vacío, con: el esquema formal de `services.ini` (claves
    requeridas/opcionales por sección y por campo, incluyendo que
    `Regex` es obligatoria y `Patterns` opcional/documental), el
    algoritmo de validación y sus categorías de error, la explicación
    del bug de desconexión corregido (criterio 11) con el ejemplo
    concreto de `cliente`/`045-987654`, la relación entre `services.ini`
    y `document_services.json` (qué valida cada uno, qué test cruza
    ambos), y la aclaración explícita de que el pipeline HTTP en vivo
    (`/api/v1/jobs`, `capture_pipeline.py`, `templates/providers.py`) es
    un sistema de configuración **distinto**, no afectado por esta
    feature (para que futuros mantenedores no asuman que editar
    `services.ini` cambia el comportamiento de captura en vivo).
    Adicionalmente, debe documentar explícitamente:
    - Que `Field.<nombre>.Patterns` es **únicamente metadata documental**
      de palabras clave de anclaje (lista separada por `|`, sin grupo de
      captura), **nunca aplicada por el motor de extracción real**:
      `extraction_engine._extract_with_patterns` existe en el código y
      funciona, pero hoy sólo se alimenta de
      `services_config.get_service_patterns()`, que lee una clave de
      sección distinta (ver punto siguiente), no el namespace
      `Field.<nombre>.Patterns`. Conectar `Patterns` a extracción real
      queda fuera de alcance de esta feature — es una decisión de diseño
      conocida y documentada, no un bug oculto (ver "Riesgos/supuestos").
    - Que `services_config.py::get_service_zones`/`get_service_patterns`
      leen claves de sección en **minúscula** (`zones=`, `patterns=`,
      formato `campo:valor` multilínea) que **ningún `services.ini` real
      usa hoy** — un **tercer** mecanismo de configuración, completamente
      muerto, distinto tanto del namespace `Field.<nombre>.*` como del
      bug corregido en el criterio 11, para que un futuro mantenedor no
      lo confunda con el mecanismo vigente ni pierda tiempo
      investigándolo como si estuviera en uso.
15. Debe existir `runs/16-administracion-servicios-documentos/decision.md`,
    y enlaces exactos (mismo título en ambos) en `docs/tecnica/index.md`
    y `docs/usuario/index.md` hacia
    `administracion-servicios-documentos.md`, verificable con
    `Assert-FeatureContract` (`scripts/feature-contract.ps1`).
16. Tests contractuales nuevos en `backend/tests/` (ej.
    `test_services_config_schema.py`, `test_services_admin_api.py`)
    cubren los criterios 1–12 y corren en verde con `pytest -v`
    (`backend/tests/` + `tests/`), sin requerir red ni Docker, sin
    regresión sobre la suite existente (en particular
    `test_document_services_inventory.py`,
    `test_gas_extractor.py`, `test_empty_text.py`,
    `test_evaluate_ocr_service_data_output.py`).

### Reglas de dominio OCR aplicables (criterio 11)

- **Campo extraído:** `cliente` (también aplica, por el mismo mecanismo
  genérico corregido, a `importe`, `nro_medidor`, `a_pagar_hasta`,
  `periodo` de `GAS`, y a los 5 campos de `CEVT` — todos ya declaran
  `Field.<nombre>.Regex` en `services.ini`).
- **Tipo de documento/servicio:** `GAS` (sección `[GAS]` de
  `services.ini`), con `CEVT` como caso adicional de regresión.
- **Fixture/texto usado:** texto OCR normalizado sintético (no requiere
  imagen ni fixture binaria — `extraction_engine.extract_service_fields`
  acepta texto directamente, igual que `test_empty_text.py`):
  `"Medidor 12345678 Cliente 045-987654"`.
- **Salida esperada:** `fields["cliente"] == "045-987654"`.
- **Validación semántica aplicada:** anclaje textual obligatorio a la
  palabra clave (`cliente`/`nro cliente`/`n° cliente`/`numero cliente`)
  antes de capturar el valor, definido declarativamente en
  `Field.cliente.Regex` — no en Python hardcodeado por servicio (ADR-007).
- **Falso positivo evitado:** capturar el número de **medidor**
  (`12345678`) como si fuera el número de **cliente**, por buscar
  cualquier corrida de dígitos sin anclaje al contexto — el defecto real
  de `_extract_generic` que esta feature dejó de usar como camino
  primario para campos con `Regex` declarada (ahora obligatoria para
  todo campo válido).

## Casos borde a contemplar

- `services.ini` no existe todavía (`services_config.py._load_parser()`
  hoy lo autocrea vacío): cero secciones debe seguir siendo un estado
  válido ("no hay servicios configurados todavía"), no un error de
  esquema. `GET /api/v1/services` debe responder `200` con lista vacía
  en ese caso, no `500`.
- `services.ini` con codificación no UTF-8 o corrupta: debe fallar con un
  mensaje claro (no una traza cruda de `UnicodeDecodeError`), consistente
  con el resto de mensajes de validación.
- Un campo con `Type=amount` pero sin ninguna referencia de moneda en su
  `Regex`/`Patterns` — no es un error de esquema (no hay forma
  automática de saber si el autor lo hizo a propósito), pero debe quedar
  documentado como responsabilidad del autor del alta en
  `docs/tecnica/administracion-servicios-documentos.md`.
- `Field.<nombre>.Regex` que compila y tiene grupo de captura, pero el
  grupo nunca matchea nada en el texto real (regex demasiado estricta):
  no es un error de esquema — cae en `missing_fields`, comportamiento ya
  existente y correcto (diferenciar "regex inválida" de "regex válida
  que no matcheó").
- Un campo declara `Field.<nombre>.Patterns` pero no `Field.<nombre>.Regex`:
  ahora es un error de esquema explícito (criterio 9), no un estado
  ambiguo silencioso — el mensaje debe dejar claro que `Patterns` por sí
  solo no es suficiente porque no está conectado a extracción.
- Servicio presente en `document_services.json` pero ausente en
  `services.ini` (o viceversa): ya cubierto parcialmente por
  `test_inventory_data_evaluator_contract_t23`; esta feature no debe
  romper ese test y debe referenciarlo en
  `docs/tecnica/administracion-servicios-documentos.md` como parte del
  contrato de consistencia.
- `GET /api/v1/services/{service_id}` con `service_id` en minúsculas o
  con espacios: debe normalizar igual que `document_services.normalize_service_id`
  (`strip().upper()`) para no exigir que el cliente HTTP conozca el
  casing exacto de la sección INI.
- Dos secciones en `services.ini` con el mismo nombre: `configparser` ya
  lanza `DuplicateSectionError` al leer — la validación debe envolver ese
  error en un mensaje consistente con el resto (sección duplicada,
  archivo y línea si `configparser` la expone), no dejarlo pasar como
  traza cruda distinta al resto de los errores de esquema.
- Cambiar `services.ini` en caliente sin reiniciar el proceso: hoy
  `_load_parser()` relee el archivo en cada llamada (no cachea), por lo
  que el endpoint nuevo y el DATA evaluator ya reflejan cambios sin
  reinicio — debe quedar confirmado por un test y mencionado en la
  documentación, no asumido.

## Riesgos / supuestos

- **Fragmentación real de "dar de alta un servicio" en este repo, no
  resuelta por esta feature:** hoy existen **tres** mecanismos
  independientes para definir un servicio/proveedor de captura de
  comprobantes: (1) `services.ini` + `services_config.py` +
  `extraction_engine.py`, usado solo por el DATA evaluator
  (`scripts/evaluate_ocr_service.py`); (2)
  `backend/app/templates/providers.py`, dataclasses Python hardcodeadas
  por proveedor con ROI/anclas/regex/validadores tipados, usado por el
  pipeline HTTP en vivo (`capture_pipeline.py`, `/api/v1/jobs`); (3)
  `backend/app/gas_extractor.py`, extractor Python específico de GAS
  usado solo por `t3_2_orchestrator.py` (fixtures T3.2 antiguas). El
  texto de `ROADMAP.md` ítem 16 dice explícitamente "en `services.ini`",
  por lo que se interpreta el alcance como (1) únicamente. Se documenta
  esta fragmentación en `docs/tecnica/administracion-servicios-documentos.md`
  para que quede trazable, pero unificar los tres mecanismos es un
  cambio de arquitectura mayor, no pedido por este ítem del roadmap, y
  potencialmente reñido con ADR-006 (el pipeline en vivo depende de las
  plantillas Python two-pass ROI, no de config de texto plano genérica).
  El `reviewer-agent` puede objetar esta interpretación de alcance si
  considera que el roadmap implica unificar los tres mecanismos.
- **Decisión (corregida en el intento 2, tras feedback del
  reviewer-agent): `Regex` se vuelve obligatoria en el esquema para todo
  campo; `Field.<nombre>.Patterns` deja de ser una alternativa válida a
  `Regex` y pasa a ser opcional y puramente documental.** El intento 1
  dejaba una ambigüedad real entre el esquema (que aceptaba "Patterns o
  Regex") y el arreglo de comportamiento (que sólo conecta `Regex` a
  extracción), lo que hubiera permitido que un campo declarado solo con
  `Patterns` pasara la validación "profesional" y siguiera cayendo para
  siempre en `_extract_generic()` — reproduciendo el mismo defecto de
  "documentación muerta" que esta feature dice eliminar. Alternativas
  evaluadas:
  - **(a) — elegida: exigir `Regex` obligatoria.**
  - (b) mantener ambas como válidas, agregando solo un criterio de
    documentación que aclare que `Patterns` nunca se aplica.
  Se eligió (a) porque, verificado leyendo `backend/config/services.ini`
  y `backend/app/extraction_engine.py` directamente: (1) los 10 campos
  reales de `GAS`/`CEVT` ya declaran `Regex` además de `Patterns` —
  exigirla obligatoria no rompe el criterio 1 (el archivo real sigue
  siendo válido sin cambios); (2) el valor de `Patterns` en
  `services.ini` (ej. `cliente|nro cliente|n° cliente|numero cliente`) es
  una alternancia de palabras clave de anclaje **sin grupo de captura**
  — si se conectara tal cual a `extraction_engine._extract_with_patterns`
  (que existe y funciona, pero hoy sólo se alimenta de
  `services_config.get_service_patterns()`, un mecanismo de sección en
  minúscula distinto y muerto, no del namespace `Field.<nombre>.Patterns`),
  devolvería el texto del ancla matcheado (`match.group(0)`, por no tener
  grupos) en vez del valor real — conectar `Patterns` tal cual produciría
  salidas incorrectas, no una alternativa funcional a `Regex`; hacerlo
  bien exigiría rediseñar su formato (agregar grupos de captura,
  redefinir su sintaxis), trabajo nuevo no pedido por `ROADMAP.md` ítem
  16 y fuera del alcance mínimo para cerrar el bug de desconexión. La
  opción (a) es la de menor riesgo de alcance: reconecta exactamente lo
  que ya existe y ya funciona (`Regex` + su grupo de captura), sin
  inventar semántica nueva para `Patterns`. `Patterns` se conserva en el
  esquema como campo opcional, documental, para quien lee `services.ini`
  a ojo (ayuda de lectura humana de qué palabras clave ancla la regex),
  pero no se valida su formato ni se conecta a extracción —
  documentado explícitamente en
  `docs/tecnica/administracion-servicios-documentos.md` (criterio 14)
  para que no se confunda con una alternativa funcional a `Regex`. El
  `reviewer-agent` puede objetar esta decisión si prefiere invertir en
  conectar `Patterns` a extracción real como parte de esta misma
  feature.
- **Decisión: agregar un endpoint HTTP nuevo, de solo lectura
  (`GET /api/v1/services[/{id}]`), en vez de limitarme a ejemplos de CLI
  para `docs/usuario/`.** Esta feature, tal como está scopeada
  (validación de config + DATA evaluator), no tiene ningún endpoint HTTP
  existente al que enganchar un ejemplo real (el precedente
  `04-cierre-operativo-circuito-agentico` resolvió esta misma tensión
  con ejemplos de CLI/PowerShell en vez de HTTP, para una feature sin
  superficie HTTP). Se optó por agregar el endpoint en vez de replicar
  ese patrón porque (a) es exactamente lo que pide `ROADMAP.md` como
  "documentación automática", (b) es de solo lectura y no toca OCR, el
  pipeline en vivo ni ADR-006, y (c) da un ejemplo HTTP real y
  verificable en vez de uno forzado. El `reviewer-agent` puede objetar
  esto si prefiere no agregar superficie HTTP nueva para una feature de
  "config admin".
- **Supuesto de esquema:** los tres tipos (`text`, `amount`, `date`) y el
  formato `true`/`false` para `Required` se toman literalmente de los
  valores que ya usa `services.ini` real (`GAS`, `CEVT`) — no se inventa
  un tipo nuevo. Si en el futuro se necesita un tipo adicional (ej.
  `email`, `phone`), habrá que extender el esquema explícitamente, no
  read-only.
- **Supuesto:** "al menos un grupo de captura" en `Regex` (criterio 8) es
  una regla nueva, no exigida hoy por ningún código. Los `Field.<nombre>.Regex`
  reales de `GAS`/`CEVT` ya la cumplen (verificado leyendo
  `services.ini`), por lo que el criterio 1 (el archivo real pasa la
  validación sin cambios) no debería romperse al introducir esta regla.
- **Riesgo aceptado, no resuelto en esta feature:** la clave `Required`
  del esquema de `services.ini` no se cruza automáticamente con
  `expected_fields` de `document_services.json` (que hoy mezcla el
  concepto de "campo esperado por el DATA evaluator" con "campo
  requerido para que el documento se considere válido"). Esta feature no
  fusiona ambos conceptos; solo exige que `Required` esté bien formado
  dentro de `services.ini`. Documentado como deuda conocida en
  `docs/tecnica/administracion-servicios-documentos.md`.
