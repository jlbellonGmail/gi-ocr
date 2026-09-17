# Code Reviewer y Spec-Driven Development (SDD)

Esta feature (`01-code-reviewer-y-sdd`) agrega un quinto agente al
circuito (`code-reviewer-agent`), formaliza Spec-Driven Development
(`plan.md` + `tasks.md` junto a `spec.md`), y corrige tres bugs reales
detectados por auditoría en `scripts/feature-contract.ps1` y
`scripts/close-feature.ps1`, más `$schema` roto en `.agentic/`. Ver
`runs/v1.1.0/01-code-reviewer-y-sdd/spec.md`, `plan.md` y `tasks.md` para el
detalle completo de criterios de aceptación (`AC-N`) y tareas.

## Eje 1 — `code-reviewer-agent`

### Por qué un quinto agente y no ampliar `qa-agent`

`qa-agent` corre tests y puede tocar/agregar tests como parte de resolver
fallas; eso significa que el diff final que sale de QA puede no haber
sido revisado técnicamente por nadie (ni `reviewer-agent`, que solo vio
el spec antes de implementar). `code-reviewer-agent` cierra ese hueco:
revisa el DIFF FINAL (código, tests, scripts, config, docs técnicas)
DESPUÉS de que QA aprueba, nunca antes. Es read-only (mismo perfil que
`reviewer-agent`: `claude.tools = [Read, Grep, Glob]`, sin
`Write`/`Edit`/`Bash`; en OpenCode `permission.edit/bash/webfetch =
deny`) porque su trabajo es auditar, no corregir.

Un rechazo de `code-reviewer-agent` vuelve a `builder-agent` (paso 3 del
circuito), nunca a `analyst-agent`: el problema es de implementación, no
de spec. Si Builder toca código o tests para resolver el feedback, el
circuito exige repetir QA antes de que `code-reviewer-agent` reevalúe —
esto es una regla de proceso documentada en
`.agentic/roles/code-reviewer-agent.md` y en `AGENTS.md`; no hay una
forma 100% automática de encodearlo en el contrato ejecutable sin
comparar timestamps/hashes de commit entre `test-report-N.md` y
`code-review-N.md` (ver "Limitación conocida" más abajo).

### Modelo y permisos

`.agentic/agents.json`/`.agentic/models.json` reutilizan exactamente la
misma clase de modelo, variante y cadena de fallback que
`reviewer-agent` (mismo `claude.model`/`effort`, mismo `codex.model`,
mismo `opencode.model`/`reasoningEffort`), sin introducir ningún
proveedor nuevo. `scripts/sync-agentic-adapters.ps1` no necesitó cambios
de lógica: ya deriva la lista de agentes de
`agents.roles.PSObject.Properties`, así que agregar la entrada
`code-reviewer-agent` a `agents.json` fue suficiente para que se generen
`.claude/agents/code-reviewer-agent.md`,
`.codex/code-reviewer-agent.config.toml` y la entrada
`agent.code-reviewer-agent` en `opencode.json`.

## Eje 2 — Spec-Driven Development (SDD)

`analyst-agent` ahora produce tres archivos por invocación:
`spec.md` (QUÉ + POR QUÉ, sin detalle de implementación), `plan.md`
(CÓMO: arquitectura afectada, componentes/contratos, compatibilidad,
dependencias, estrategia de tests, impacto operacional) y `tasks.md`
(tareas pequeñas y verificables, cada una trazable a un `AC-N` de
`spec.md`). `reviewer-agent` audita los tres juntos: coherencia
spec↔plan (ningún alcance nuevo solo en `plan.md`) y trazabilidad
requisito→plan→tarea en ambas direcciones (todo `AC-N` cubierto por al
menos una sección de plan y una tarea; ninguna tarea sin `AC-N` real).

El contrato común (`Assert-WorkUnitContract`, modo `Feature` y
`Milestone`) exige `plan.md` y `tasks.md` no vacíos con la misma función
`Assert-NonEmptyFile` ya usada para `spec.md`.

## Eje 3 — Bugs corregidos

### 3.1 — Selección del último veredicto por número real, no orden lexicográfico

`Get-FirstExistingArtifact` (eliminada del archivo: no quedó ningún otro
llamador tras el reemplazo, confirmado por grep) ordenaba
`Get-ChildItem` por `Name` (`Sort-Object Name`), lo que hacía que
`audit-10.md` quedara ANTES que `audit-2.md` en orden alfabético. Además
nunca miraba el contenido: un `audit-1.md` con `status: rejected` seguido
de un `audit-2.md` vacío o inexistente igual pasaba el contrato, porque
solo se comprobaba "existe al menos un archivo que matchea el patrón".

Se reemplaza por `Get-LatestVerdictArtifact` +
`Assert-LatestVerdictApproved` (`scripts/feature-contract.ps1`):

- Enumera archivos `<prefix>-N.md` con regex anclada al nombre completo
  (`^<prefix>-(\d+)\.md$`), no a la ruta.
- Selecciona el de mayor `[int] N` (`Sort-Object Number -Descending`),
  no por nombre.
- Extrae el primer bloque ```` ```yaml ... ``` ```` con una regex simple
  (sin parser YAML completo — el formato del bloque de veredicto es
  deliberadamente 2 líneas clave-valor conocidas, no requiere
  `ConvertFrom-Yaml` ni módulos externos).
- Exige exactamente una línea `status:` (valor `approved` o `rejected`,
  comparación **case-sensitive** con `-cne`: un valor como `Approved`
  con mayúscula se trata como malformado, no como aprobado por default)
  y exactamente una línea `attempt:` numérica que coincida con el número
  del nombre de archivo.
- Lanza excepciones con la ruta exacta y la causa concreta: "sin bloque
  YAML", "status ausente/invalido", "attempt ausente/no numerico",
  "attempt no coincide con el nombre de archivo", o (en
  `Assert-LatestVerdictApproved`) "ultimo intento rejected".

Esta misma función se usa para los tres artefactos de veredicto
(`audit-N.md`, `test-report-N.md`, `code-review-N.md`), en modo
`Feature` y `Milestone`.

### 3.2 — `New-DecisionFile` ya no afirma aprobación de merge

La versión anterior escribía literalmente "MERGE aprobado por evidencias
del circuito agéntico." — una afirmación falsa, porque el único HITL es
la aprobación de la PR en GitHub, no algo que el circuito agéntico
otorgue. Ahora la sección "Estado" dice "Estado tecnico: ready_for_pr."
y aclara explícitamente que la aprobación de merge es exclusiva del HITL
en GitHub y que `decision.md` no la otorga ni la implica. La sección
"Evidencias revisadas" ahora también referencia `plan.md`, `tasks.md` y
`code-review-1.md`, además de `spec.md`, `audit-1.md` y
`test-report-1.md` (lista fija de nombres de primer intento, mismo
criterio que el código anterior — si una feature necesita referenciar un
intento posterior, es una extensión menor a futuro, no algo que esta
corrección deba dinamizar).

### 3.3 — `close-feature.ps1`: retry de push cuando el commit local ya existe

Bug reproducible: si el primer `git push origin develop` fallaba después
de que el commit local de cierre ya se había creado (remoto rechazó el
push, red caída, etc.), una segunda ejecución del script detectaba
`closeState = "already-closed"` (porque el ROADMAP.md local YA decía
`[x]`) y saltaba directo a la verificación final contra
`origin/$baseBranch` — que fallaba, porque el remoto seguía en `[-]`, y
el script nunca reintentaba el push.

El fix agrega, en la rama `already-closed` (tanto modo `Feature` como
`Milestone`): `git fetch origin $baseBranch`, lee
`origin/$baseBranch:ROADMAP.md`, y compara con
`Test-RoadmapClosedOnce`/`Test-RoadmapItemsClosedOnce` (variantes
booleanas de las `Assert-Roadmap*ClosedOnce` existentes, sin duplicar la
regex de estado — reutilizan `Get-RoadmapState`/`Get-RoadmapItemState`).
Si el remoto YA tiene el cierre, no hace nada más. Si no, pushea el
commit local pendiente antes de continuar a la verificación final (que
queda intacta como autoridad final). El caso normal
(`closeState != "already-closed"`) no cambia.

Caso borde cubierto explícitamente: si el remoto avanzó con otros
commits no relacionados entre el intento fallido y el reintento, el
`git push` sigue siendo válido mientras el commit local sea
fast-forward; si no lo es, el push falla con el mismo mensaje de error
de siempre (`Command failed: git push origin develop`), sin forzar el
push. El estado "parcialmente cerrado" en Milestone (algunos items
`[x]`, otros no) sigue siendo irrecuperable automáticamente — el fix del
retry no toca ese comportamiento.

### 3.4 — Schemas JSON reales para `.agentic/`

`.agentic/agents.json` y `.agentic/models.json` declaraban `$schema:
"./schemas/agents.schema.json"` / `"./schemas/models.schema.json"`, pero
`.agentic/schemas/` no existía: la referencia estaba rota. Se agregaron:

- `.agentic/schemas/agents.schema.json`
- `.agentic/schemas/models.schema.json`
- `.agentic/schemas/work-unit.schema.json`

JSON Schema Draft 2020-12 real (validado con la librería `jsonschema` de
Python en `tests/test_agentic_schemas.py`, con un caso positivo y al
menos un caso negativo por schema). Decisión de `additionalProperties`:
`true` a nivel raíz de cada rol en `agents.json`/`models.json` (no
romper con campos futuros menores), `false` dentro de los bloques
`claude`/`codex`/`opencode` (detectar typos reales de configuración por
herramienta). `work-unit.schema.json` es estricto en su raíz
(`additionalProperties: false`) porque el manifest de Milestone tiene
una forma fija y pequeña. Ver la decisión de arquitectura completa en
`docs/tecnica/arquitectura.md` ("Decisión: validación real de JSON
Schema para `.agentic/`"), incluida la justificación de la dependencia
de test `jsonschema`.

El manifest de Milestone (`work-unit.json`) NO autoreferencia su propio
schema con un campo `$schema` — se valida solo desde los tests, para no
tocar el formato de archivo ya cubierto por `test_workunit_lib.py` /
`test_start_work_unit.py` ni arriesgar compatibilidad con un manifest ya
committeado en algún Milestone en curso.

## Limitación conocida (documentada, no resuelta por esta feature)

El contrato ejecutable no puede detectar automáticamente si
`code-reviewer-agent` está reevaluando un `test-report-N.md` que quedó
desactualizado porque Builder tocó código/tests después de esa corrida
de QA sin que QA volviera a correr. Es una regla de proceso (documentada
en `.agentic/roles/code-reviewer-agent.md` y en `AGENTS.md`), no un gate
técnico: implementarla requeriría comparar timestamps o hashes de commit
entre artefactos, lo cual el spec de esta feature dejó explícitamente
fuera de alcance (ver `runs/v1.1.0/01-code-reviewer-y-sdd/spec.md`, sección
"Alcance" y "Riesgos / supuestos").

## Actualización de documentación del propio circuito

`AGENTS.md` (sección "Circuito", "Retornos permitidos", "Artefactos",
"Formato de veredicto", "Modo MILESTONE"), `ROADMAP.md` (encabezado),
`docs/tecnica/circuito-agentico.md`, `docs/usuario/circuito-agentico.md`
y `.agentic/README.md` se actualizaron para reflejar los 5 roles, el
nuevo orden (`Builder → QA → Code Reviewer → READY_FOR_PR`) y los nuevos
artefactos (`plan.md`, `tasks.md`, `code-review-N.md`).
`scripts/ready-for-pr.ps1` incluye `plan.md`, `tasks.md` y
`code-review-N.md` en la sección de evidencias del cuerpo de la PR, en
ambos modos `Feature` y `Milestone`.
