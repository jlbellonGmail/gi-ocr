```yaml
status: rejected
attempt: 1
feedback:
  - "Criterio 11 contiene una afirmación técnica falsa, verificada por trazado directo del código (no asumida): para el texto de prueba propuesto \"Medidor 12345678 Cliente 045-987654\", `_extract_generic(\"cliente\", text)` (backend/app/extraction_engine.py, líneas 141-154) SÍ matchea `\\d{8,10}` contra \"12345678\" (8 dígitos corridos) y devuelve \"12345678\" — el fallback `text_clean[:10]` (que produciría algo como \"Medidor 12\", NO \"Medidor 1\") nunca se alcanza porque hay match. El resultado erróneo \"Medidor 1\" que el criterio pide explícitamente evitar no puede ocurrir con ese input; parece una confusión con el otro ejemplo de la sección Contexto (\"Cliente: 045-987654\" → \"Cliente: 0\", ese sí verificado correcto). Corregir o eliminar la cláusula \"ni 'Medidor 1'\" del criterio 11 antes de que el builder-agent escriba un test contra un escenario que no existe."
  - "Gap real entre el esquema (Alcance punto 1 / criterio 9, que acepta 'al menos uno de Patterns/Regex' como válido) y el arreglo de comportamiento (criterio 11, que sólo conecta Field.<nombre>.Regex a extraction_engine.py, dejando _extract_generic sin cambios 'para servicios/campos que no declaren Regex'). Un campo declarado únicamente con Patterns (sin Regex) pasaría la nueva validación 'profesional' y sin embargo seguiría cayendo para siempre en _extract_generic() — reproduciendo exactamente el defecto de 'documentación muerta' que esta feature dice eliminar (Alcance punto 2, última línea). El spec no define qué es Field.<nombre>.Patterns en este nuevo esquema (¿metadata documental de anclaje, nunca consumida por extracción, tal como ya lo describe docs/tecnica/gas.md línea 19-21? ¿o debería conectarse también, ya que extraction_engine._extract_with_patterns ya existe y hoy está muerto porque get_service_patterns() lee una clave de sección equivocada?). Resolver explícitamente antes de implementar: o (a) el esquema exige Regex obligatorio (no 'Patterns o Regex', dado que sólo Regex queda conectado a extracción real), o (b) se mantienen ambos como válidos pero se agrega un criterio de aceptación exigiendo que docs/tecnica/administracion-servicios-documentos.md documente explícitamente que Patterns es sólo metadata de palabras clave de anclaje, nunca aplicada por el motor de extracción, y que un campo sólo-Patterns seguirá usando el fallback genérico."
  - "Nota menor, no bloqueante por sí sola: services_config.py::get_service_zones/get_service_patterns leen claves de sección en minúscula ('zones', 'patterns', formato campo:valor multilínea) que hoy no usa ninguna sección real de services.ini — son un tercer mecanismo de configuración, completamente muerto, distinto tanto del bug de Field.<nombre>.Regex corregido en el criterio 11 como del namespace Field.<nombre>.Patterns documental. El spec no menciona este tercer camino muerto en absoluto. Sugerido (no exigido): al menos una mención en docs/tecnica/administracion-servicios-documentos.md de que ese formato lowercase 'zones'/'patterns' existe en el código pero no está en uso, para que un futuro mantenedor no pierda tiempo investigándolo como si fuera el mecanismo vigente."
```

# Auditoría — 16-administracion-servicios-documentos (intento 1)

## Verificación de cumplimiento del contrato mínimo (AGENTS.md)

- `docs/tecnica/<slug>.md` exigido como criterio de aceptación: **sí**
  (criterio 14, `runs/16-administracion-servicios-documentos/spec.md`
  líneas 222-233).
- `docs/usuario/<slug>.md` exigido: **sí** (criterio 13, líneas 211-221).
- `runs/16-administracion-servicios-documentos/decision.md` y enlaces
  exactos en ambos índices de documentación, verificables con
  `Assert-FeatureContract`: **sí, explícito** (criterio 15, líneas
  234-238).
- No hay disparadores de rechazo automático de AGENTS.md: los dos `.md`
  de documentación, `decision.md` y los enlaces de índice están
  correctamente exigidos. **No se rechaza por esta vía.**

## Verificación de la regla de dominio OCR (declaración obligatoria por mejora)

El spec incluye una sección dedicada "Reglas de dominio OCR aplicables
(criterio 11)" (líneas 248-269) con los seis elementos exigidos por
AGENTS.md: campo extraído (`cliente`, y por extensión el resto de campos
de `GAS`/`CEVT`), tipo de documento (`GAS`, con `CEVT` de regresión),
fixture (texto OCR sintético normalizado, sin necesidad de imagen
binaria), salida esperada (`fields["cliente"] == "045-987654"`),
validación semántica aplicada (anclaje textual a la palabra clave antes
de capturar) y falso positivo evitado (capturar el número de medidor en
vez del número de cliente). **Cumple el formato exigido.**

## Verificación de las afirmaciones técnicas centrales (no dadas por ciertas)

Leí directamente el código citado, no asumí las afirmaciones del spec:

- `backend/app/services_config.py::get_service_config()` (líneas
  101-111) construye el dict de configuración únicamente a partir de
  `get_service_fields` (lee `Fields`), `get_service_zones` (lee una
  clave de sección `"zones"` en minúscula, líneas 44-53) y
  `get_service_patterns` (lee una clave de sección `"patterns"` en
  minúscula, líneas 56-65). Ninguna de las tres toca el namespace
  `Field.<nombre>.*`. Confirmado leyendo `backend/config/services.ini`:
  ninguna sección `[GAS]`/`[CEVT]` declara las claves de sección
  `zones=`/`patterns=` (en minúscula) — sólo existen los bloques
  `Field.<nombre>.Patterns=`/`Field.<nombre>.Regex=` por campo. Por lo
  tanto `zones` y `patterns` en el dict devuelto por
  `get_service_config()` están siempre vacíos para cualquier servicio
  real. **La afirmación del "bug de desconexión" es correcta y está
  bien localizada** (función y archivo exactos).
- `backend/app/extraction_engine.py::extract_service_fields()` (líneas
  26-102): con `zones` y `patterns` siempre vacíos, el paso 1 (zonas,
  línea 65: `if zones and image_np is not None`) y el paso 2 (patrones,
  línea 82: `if value is None and field in patterns`) nunca se activan
  para ningún campo real, y el motor cae siempre en el paso 3,
  `_extract_generic()` (línea 86-87). **Confirmado: el motor de
  extracción configurable nunca aplica la regex declarativa de
  `services.ini`, exactamente como afirma el spec.**
- Ejemplo de dominio (`cliente`, GAS): `Field.cliente.Example=045-987654`
  y `Field.cliente.Regex=(?:cliente|nro cliente|n° cliente|numero
  cliente)\D{0,40}([0-9\-]{6,20})` existen literalmente en
  `backend/config/services.ini` líneas 12-17, coherentes con lo citado
  en el spec.
- Trazado manualmente `_extract_generic("cliente", "Cliente:
  045-987654")` (ejemplo de la sección Contexto, no el de criterio 11):
  no hay corrida continua de 8-10 dígitos (`"045"` y `"987654"`
  separados por guion), cae al fallback `text_clean[:10]` = `"Cliente:
  0"`. **Correcto, verificado.**
- Trazado manualmente `_extract_generic("cliente", "Medidor 12345678
  Cliente 045-987654")` (el texto real que pide el criterio 11 para el
  test de regresión): `"12345678"` sí es una corrida de exactamente 8
  dígitos, matchea `\d{8,10}` y se devuelve tal cual — el fallback
  `text_clean[:10]` nunca se alcanza. Esto confirma la parte correcta
  del criterio 11 (el resultado incorrecto a evitar es `"12345678"`,
  el número de medidor mal capturado) pero **refuta la cláusula
  adicional "ni 'Medidor 1'"**, que no corresponde a ningún resultado
  real posible de `_extract_generic` para ese input (ver feedback
  arriba).

## Evaluación de alcance

- La decisión de no tocar `capture_pipeline.py`/`templates/providers.py`
  (pipeline HTTP en vivo) ni `gas_extractor.py` está bien justificada:
  el ítem 16 de `ROADMAP.md` dice literalmente "en `services.ini`"
  (verificado, línea 174-177 de `ROADMAP.md`), y el spec documenta con
  precisión que son tres mecanismos de configuración de servicio
  independientes y hoy no relacionados (confirmado: `gas_extractor.py`
  no referencia `services_config`/`services.ini`/`Field.`/`Regex` en
  absoluto — es Python hardcodeado, verificado con grep). Es una
  interpretación de alcance defendible, no una reapertura encubierta de
  ADR-006, y queda explícitamente señalada como asunción objetable, tal
  como pide el proceso.
- La adición del endpoint `GET /api/v1/services[/{id}]` es una decisión
  de alcance razonable dado que el texto literal del roadmap pide
  "documentación automática", el endpoint es de solo lectura, no expone
  datos sensibles, no colisiona con rutas existentes (`/api/v1/health`,
  `/api/v1/jobs`, `/api/v1/export`, etc., verificado en
  `backend/app/main.py`), y da un ejemplo HTTP real en vez de forzado.
  No se rechaza por esto.
- No contradice ADR-006 (motor OCR) ni ADR-007 (config en texto plano),
  verificado leyendo `docs/tecnica/arquitectura.md`.

## Evaluación de criterios de aceptación y casos borde

- Los 16 criterios son mayormente verificables por test explícito
  (mensajes de error específicos, valores concretos, nombres de
  archivos de test esperados). El criterio 1 (el `services.ini` real no
  debe romperse) fue verificado manualmente: todas las regex de
  `Field.<nombre>.Regex` en `GAS`/`CEVT` ya tienen al menos un grupo de
  captura, por lo que la nueva regla del criterio 8 no debería romper
  el criterio 1, tal como afirma el spec.
- Casos borde cubren lo esencial del dominio de configuración (archivo
  ausente, encoding corrupto, secciones duplicadas, normalización de
  `service_id`, hot-reload sin caché, y la distinción entre "regex
  inválida" vs. "regex válida que no matcheó"). Razonable para el tipo
  de feature (config/schema, no OCR de imagen), sin vacíos obvios más
  allá de los dos puntos de feedback señalados arriba.

## Conclusión

El spec es sólido en estructura, gobernanza documental y verificación
de sus propias afirmaciones técnicas centrales (el bug de desconexión
está correctamente diagnosticado y localizado). Sin embargo, contiene
un error factual concreto en el ejemplo de dominio OCR del criterio 11
(la cláusula "ni 'Medidor 1'" no se sostiene al trazar el código real) y
deja sin resolver una ambigüedad de diseño real entre el esquema
(`Patterns` como alternativa válida a `Regex`) y el arreglo de
comportamiento (que sólo conecta `Regex`), que puede reproducir
silenciosamente el mismo defecto de "documentación muerta" que la
feature dice corregir. Ambos puntos son accionables y acotados —no
requieren rehacer el spec, sólo corregir el criterio 11 y cerrar la
ambigüedad de `Patterns` con una decisión explícita y su documentación
correspondiente. Rechazado por estos dos puntos concretos; vuelve a
`analyst-agent`.
