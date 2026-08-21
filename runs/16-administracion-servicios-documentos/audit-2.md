```yaml
status: approved
attempt: 2
feedback: []
```

# Auditoría — 16-administracion-servicios-documentos (intento 2)

## Resultado

**Aprobado.** Los dos motivos de rechazo del intento 1 fueron corregidos
correctamente y verificados contra el código real, no dados por ciertos.
No se detectan problemas nuevos introducidos por la reescritura.

## Verificación punto 1 — corrección del criterio 11 (afirmación falsa)

Tracé manualmente `_extract_generic("cliente", "Medidor 12345678 Cliente
045-987654")` contra `backend/app/extraction_engine.py` líneas 141-154:

- `field_lower = "cliente"` → contiene `"cliente"` → entra a la rama
  `if "cliente" in field_lower:`.
- `re.search(r"(\d{8,10})", text_clean)` sobre el texto completo. El
  primer (y único) tramo de 8-10 dígitos consecutivos en el string es
  `"12345678"` (8 dígitos exactos, delimitado por espacios). `"045"` y
  `"987654"` están separados por un guion, no forman una corrida
  continua de 8-10 dígitos.
- `match.group(1)` = `"12345678"`. Se retorna tal cual, sin llegar nunca
  al fallback `text_clean[:10]`.

**Confirmado: el resultado real es exactamente `"12345678"`**, tal como
ahora afirma el criterio 11 corregido (`runs/16-administracion-servicios-documentos/spec.md`
líneas 204-223). Releí el criterio 11 completo y **ya no contiene ninguna
cláusula sobre `"Medidor 1"`** — la afirmación falsa fue eliminada por
completo, no reformulada de forma ambigua. La sección "Reglas de dominio
OCR aplicables (criterio 11)" (líneas 293-315) es coherente con este
mismo resultado (`fields["cliente"] == "045-987654"` como salida
esperada tras la corrección, `"12345678"` como el falso positivo que se
evita).

## Verificación punto 2 — `Regex` obligatoria vs. `Patterns` opcional

- **Esquema (Alcance punto 1, líneas 11-25):** `Regex` es ahora
  explícitamente obligatoria por campo (`"Regex obligatoria (ya no 'al
  menos uno de Patterns/Regex')"`); `Patterns` pasa a opcional y
  puramente documental, sin validación de formato más allá de "texto no
  vacío si está presente".
- **Criterio 9 (líneas 195-200):** ante un campo sin `Field.<nombre>.Regex`
  (ausente, vacía, o sin bloque), la validación falla explícitamente
  indicando que `Regex` es obligatoria — "declarar únicamente
  `Field.<nombre>.Patterns` ya no es suficiente". Esto cierra
  exactamente el gap señalado en la auditoría 1: ya no existe ningún
  camino donde un campo sólo-`Patterns` pase la validación de esquema.
- **Coherencia con criterio 11 (líneas 204-223):** el arreglo de
  comportamiento conecta `Field.<nombre>.Regex` (ahora obligatoria para
  todo campo válido) a extracción real. Como el esquema ya no permite
  que un campo llegue a producción sin `Regex`, no puede reproducirse el
  escenario "pasa la validación pero sigue usando `_extract_generic`
  para siempre" que motivó el rechazo del intento 1.
- **Barrido de residuos:** grep de `Patterns`/`Regex` en todo el spec
  (líneas 19, 37, 115, 239, 250, 328, 337, 400) — todas las menciones
  son consistentes con el diseño corregido. La única referencia a "al
  menos uno de Patterns/Regex" (línea 19) es explícitamente histórica,
  entre comillas, citando lo que cambió respecto al intento 1, no una
  regla vigente. No encontré ninguna sección (Casos borde, Reglas de
  dominio OCR, Riesgos/supuestos) que trate `Patterns` como alternativa
  válida a `Regex`.

## Verificación punto 3 — justificación técnica de por qué no se conecta `Patterns`

Verificado leyendo el código, no asumido:

- `extraction_engine._extract_with_patterns` (líneas 126-138) existe y
  funciona: hace `re.search(pattern, text, flags=re.IGNORECASE)` y
  devuelve `match.group(1) if match.lastindex else match.group(0)`.
- Se alimenta de `patterns = config["patterns"]` (línea 58), que viene
  de `get_service_config()` → `get_service_patterns(service)`
  (`services_config.py` líneas 56-65), que lee `cfg.get(service,
  "patterns", fallback="")` — una clave de **sección en minúscula**
  (`patterns=`), formato `campo:regex` multilínea, **distinta** del
  namespace `Field.<nombre>.Patterns`. Ninguna sección real de
  `services.ini` declara esa clave lowercase; confirmado leyendo el
  archivo completo (`backend/config/services.ini`) — no hay ninguna
  línea `patterns=` a nivel de sección, sólo bloques
  `Field.<nombre>.Patterns=`. Por lo tanto `get_service_patterns()`
  siempre devuelve `{}` para `GAS`/`CEVT` reales, exactamente como
  afirma el spec.
- Verificado que los valores reales de `Field.<nombre>.Patterns` en
  `services.ini` (ej. `Field.cliente.Patterns=cliente|nro cliente|n°
  cliente|numero cliente`, `Field.importe.Patterns=importe|total|saldo|a
  pagar`) son alternancias de palabras clave **sin ningún paréntesis de
  captura** — confirmado en las 10 líneas `Field.*.Patterns=` de
  `GAS`/`CEVT`. Si se conectaran tal cual a `_extract_with_patterns`, al
  no tener grupos (`match.lastindex` sería `None`), la función
  devolvería `match.group(0)` — el texto del ancla matcheado (ej. la
  palabra `"cliente"` misma), no el valor real. La justificación técnica
  del spec para descartar conectar `Patterns` sin rediseño es correcta y
  verificable directamente en el código, no una afirmación de fe.

## Verificación punto 4 — criterio 1 no se rompe

Releí las 10 declaraciones `Field.<nombre>.Regex=` de `services.ini`
(`importe`, `cliente`, `nro_medidor`, `a_pagar_hasta`, `periodo` en
`[GAS]`; `medidor_numero`, `periodo`, `vencimiento`,
`codigo_pago_electronico`, `total_a_pagar` en `[CEVT]`) — **las 10 ya
declaran `Regex`** con al menos un grupo de captura visible (paréntesis
en cada expresión). Exigir `Regex` obligatoria en el esquema no rompe la
validación del `services.ini` real, tal como afirma el criterio 1
corregido (líneas 164-171).

## Resto del spec (ya aprobado en auditoría 1)

Revisé que no se haya introducido ningún problema nuevo al reescribir:

- Contrato AGENTS.md: `docs/tecnica/administracion-servicios-documentos.md`
  (criterio 14), `docs/usuario/administracion-servicios-documentos.md`
  (criterio 13), `decision.md` y enlaces exactos en ambos índices
  (criterio 15) siguen exigidos sin cambios de fondo. **No se rechaza
  por esta vía.**
- Declaración completa de la mejora OCR (campo, tipo de documento,
  fixture, salida esperada, validación semántica, falso positivo
  evitado) sigue presente íntegra en "Reglas de dominio OCR aplicables
  (criterio 11)" (líneas 293-315), ahora con el ejemplo corregido.
- Alcance, exclusiones explícitas (pipeline HTTP en vivo,
  `gas_extractor.py`, fusión con `document_services.json`, auth, UI),
  endpoint `GET /api/v1/services[/{id}]`, casos borde (archivo ausente,
  encoding corrupto, secciones duplicadas, hot-reload, normalización de
  `service_id`) y criterios 1-10, 12, 16 permanecen intactos y
  verificables por test, sin degradación respecto al intento 1 ya
  evaluado como sólido.
- La nueva subsección de "Riesgos/supuestos" (líneas 384-426) documenta
  la decisión (a) vs. (b) con justificación técnica trazable y deja
  explícito que el `reviewer-agent` podía objetarla — no lo hago, porque
  la opción elegida es la de menor riesgo de alcance y está verificada
  contra el código real.

## Conclusión

Ambos motivos de rechazo del intento 1 fueron corregidos de forma
verificable, sin introducir contradicciones nuevas ni relajar ningún
criterio previamente aprobado. El spec queda aprobado; pasa a
`builder-agent`.
