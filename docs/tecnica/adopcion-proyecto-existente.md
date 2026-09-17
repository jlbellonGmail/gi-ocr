# Adopción del circuito en un proyecto existente

Este documento es el checklist técnico de colisiones probables al mezclar
este template (el circuito agéntico completo: `.agentic/`, `scripts/`,
`runs/`, `docs/`, `AGENTS.md` y los 4 workflows de
`.github/workflows/`) sobre un repositorio que **ya tiene código propio**
— la ruta de adopción real más común, frente al caso de arrancar un
repositorio vacío desde este template.

Cubre exactamente los 7 elementos que enumera el ítem
`03-adopcion-proyecto-existente` de `ROADMAP.md`: `.agentic/`,
`scripts/`, `runs/`, `docs/tecnica/`, `docs/usuario/`, `AGENTS.md`, y los
4 workflows de `.github/workflows/` tratados individualmente
(`ci.yml`, `docs.yml`, `post-hitl-merge-gate.yml`,
`post-merge-close-feature.yml`). Para cada uno describe qué colisión
concreta es probable y una guía de merge accionable (fusionar, renombrar,
mantener ambos, reemplazar, o extender un job/step existente).

Este documento **no automatiza nada**: ninguna colisión se resuelve sola.
La resolución de cada caso la hace el equipo que adopta el template,
apoyándose opcionalmente en `scripts/check-adoption-conflicts.ps1` (ver
la sección "Límites del script" más abajo) para saber, antes de copiar
nada, qué rutas de este template ya existen en el repositorio destino.

Nota adyacente: `docs/producto/contexto-producto.md` no es uno de los 7
elementos de este checklist (el ítem de `ROADMAP.md` no lo incluye), pero
conviene tenerlo presente al adoptar: si el proyecto destino ya tiene
conocimiento funcional documentado en otro lugar, ese contenido debería
migrarse a `docs/producto/contexto-producto.md` una vez adoptado el
circuito, no perderse.

## `.agentic/`

**Colisión probable**: el repositorio destino ya tiene una adopción
previa (y potencialmente desactualizada) de este mismo template, con sus
propios `roles/*.md`, `agents.json`, `models.json`, `mcp.json` o
`schemas/` ya customizados para ese proyecto — por ejemplo, roles con
reglas de dominio propias agregadas, o modelos distintos configurados en
`agents.json`.

**Estrategia de merge**: si el destino no tiene `.agentic/` todavía,
copiar el directorio completo tal cual. Si ya existe una adopción previa,
no sobrescribir a ciegas: comparar archivo por archivo (especialmente
`.agentic/agents.json` y `.agentic/roles/*.md`, que son los más
propensos a tener customización real) y fusionar manualmente,
conservando la customización del destino donde exista y trayendo las
mejoras del template donde no haya conflicto real. Después de fusionar,
correr `scripts/sync-agentic-adapters.ps1` y
`scripts/sync-agentic-adapters.ps1 -Check` para regenerar y validar los
adaptadores (`.claude/agents/*.md`, `.codex/*.config.toml`,
`opencode.json`) — esos adaptadores nunca se editan a mano, así que no
son ellos el punto de fusión: es `.agentic/` como fuente canónica.

## `scripts/`

**Colisión probable**: colisión de **nombre de archivo** puntual, no de
la carpeta en su conjunto — por ejemplo, si el destino ya tiene un script
propio llamado `workunit-lib.ps1` o `ready-for-pr.ps1` para un propósito
totalmente distinto al del circuito. Es poco probable que el destino
tenga por coincidencia un script con el mismo nombre *y* el mismo
propósito, así que la colisión esperable es de nombre, no de contenido
equivalente.

**Estrategia de merge**: copiar los 11 scripts del circuito
(`resolve-agentic-model.ps1`, `sync-agentic-adapters.ps1`,
`update-doc-indexes.ps1`, `wait-pr-ci.ps1`, `start-work-unit.ps1`,
`workunit-lib.ps1`, `local-feature-reconcile.ps1`, `close-feature.ps1`,
`feature-contract.ps1`, `complete-approved-pr.ps1`, `ready-for-pr.ps1`)
junto a los scripts existentes del destino: es una unión, no un
reemplazo de carpeta. Si hay colisión de nombre exacto, renombrar el
script **del destino** primero (el circuito referencia sus propios
scripts por nombre exacto desde `AGENTS.md` y desde otros scripts, así
que renombrar el lado del template rompe ese wiring interno); solo si el
script del destino no puede renombrarse sin romper otra cosa, evaluar
renombrar el del template y actualizar todas sus referencias cruzadas
(`AGENTS.md`, otros `scripts/*.ps1`, workflows).

## `runs/`

**Colisión probable**: `runs/` es un nombre genérico. El destino puede
ya tener una carpeta `runs/` para un propósito no relacionado —salidas de
benchmarks, corridas de entrenamiento de modelos, resultados de
ejecuciones de test suites, etc.— sin ninguna relación con el circuito
agéntico.

**Estrategia de merge**: mover el contenido preexistente del destino a
otro nombre (por ejemplo `runs-legacy/` o el nombre que tenga sentido
para ese contenido), no renombrar la carpeta del circuito. `runs/` está
hardcodeado por nombre fijo en `scripts/*.ps1` (por ejemplo
`start-work-unit.ps1`, `ready-for-pr.ps1`, `close-feature.ps1`) y en
`AGENTS.md`; renombrarlo requeriría cambios de código fuera del alcance
de esta guía. La opción realista siempre es liberar el nombre `runs/`
para el circuito, no adaptar el circuito al nombre que ya use el
destino.

## `docs/tecnica/`

**Colisión probable**: el destino ya tiene su propia carpeta
`docs/tecnica/` (o equivalente) con archivos reales de documentación de
diseño del producto existente, no relacionados con el circuito.

**Estrategia de merge**: fusionar, no reemplazar. Conservar todos los
archivos existentes del destino, y agregar los archivos propios del
template que falten: `index.md` (con los marcadores
`<!-- FEATURE_LINKS_START -->` / `<!-- FEATURE_LINKS_END -->` que
`scripts/update-doc-indexes.ps1` edita automáticamente),
`arquitectura.md` y `circuito-agentico.md`. Si el destino ya tiene un
`index.md` propio con otro formato, fusionar su contenido dentro de la
plantilla del template para no perder los marcadores que el circuito
necesita para agregar enlaces por feature automáticamente.

## `docs/usuario/`

**Colisión probable**: igual que `docs/tecnica/` — el destino ya tiene su
propia documentación de usuario/operación del producto existente.

**Estrategia de merge**: la misma que `docs/tecnica/`: fusionar
conservando el contenido existente del destino y agregando `index.md`
(con los mismos marcadores `FEATURE_LINKS_START`/`FEATURE_LINKS_END`) y
`circuito-agentico.md` del template, sin pisar ningún archivo real del
destino.

## `AGENTS.md`

**Colisión probable**: el destino ya tiene su propio `AGENTS.md` (o un
sistema equivalente de instrucciones para agentes IA, como
`CLAUDE.md`/`.cursorrules`/similares) con contenido específico del
proyecto: su stack real, sus convenciones de código, su propia
estructura de repo. Un reemplazo directo por el `AGENTS.md` de este
template destruye ese contexto real.

**Estrategia de merge**: fusión por sección, no reemplazo de archivo
completo. Copiar tal cual las secciones "del circuito" —no negociables,
son el motor agéntico en sí: "Workflow del proyecto", "Circuito",
"Contexto de producto y bootstrap", "Retornos permitidos", "Estados de
ROADMAP.md", "Modo MILESTONE", "Git", "Versionado (tags)", "CI/CD",
"Herramientas locales requeridas", "Artefactos", "Formato de veredicto",
"Configuración de modelos", "Reglas adicionales", "Reglas de dominio",
"Setup manual"— y reemplazar únicamente las secciones que este mismo
template documenta como propias de cada proyecto real: "Stack",
"Estructura del repo" y "Propósito del producto" (si existiera), con el
contenido real del destino. Si el destino tenía un `AGENTS.md` (o
equivalente) con secciones que no mapean a ninguna de estas categorías,
conservarlas como secciones adicionales al final, sin perderlas.

## `.github/workflows/`

Los 4 workflows del circuito asumen GitHub Actions + GitHub CLI (`gh`),
ya declarado en `AGENTS.md` ("Herramientas locales requeridas", "CI/CD").
Esta guía no cubre otros hostings (GitLab CI, Bitbucket Pipelines, Azure
DevOps): si el destino usa un hosting distinto, es un límite explícito,
no algo que esta guía generalice.

### `ci.yml`

**Colisión probable**: el destino ya tiene su propio `ci.yml` (o
workflow de CI con otro nombre) con sus propios pasos de build/test para
el stack real del proyecto.

**Estrategia de merge**: extender, no reemplazar. Agregar el paso
`pytest -v` del circuito (que corre los tests de `scripts/*.ps1` bajo
`tests/`) como un paso o job adicional dentro del `ci.yml` existente del
destino, sin quitar ni reemplazar los pasos de build/test propios del
destino. Prestar atención a la versión de Python: este template pinea
Python 3.12+ en su `setup-python`; si el `ci.yml` del destino ya fija
otra versión de Python para su propio stack, verificar que ambos jobs/
steps puedan coexistir (por ejemplo, en jobs separados con su propia
matriz de versión) en vez de forzar una sola versión de Python para todo
el workflow. Nota: el ítem `04-ci-wiring-product-tests` de `ROADMAP.md`
va a separar `ci.yml` de este propio template en dos jobs
(`circuit-tests` y `product-tests`); cuando ese trabajo esté hecho, fusionar
`ci.yml` contra un destino será más simple porque el job `product-tests`
ya va a traer un punto de extensión explícito. Esta guía documenta la
estrategia contra la estructura **actual** de `ci.yml` (un solo job
`test`).

### `docs.yml`

**Colisión probable**: el destino ya publica documentación con otro
generador de sitio estático a GitHub Pages (Jekyll, Docusaurus,
VuePress, Sphinx, etc.), potencialmente con su propio workflow ya
apuntando al mismo repositorio de GitHub Pages.

**Estrategia de merge**: esta guía no resuelve este caso de forma
automática — es un punto de decisión explícito para el equipo que
adopta el template. Las dos opciones razonables son (a) mantener ambos
workflows activos, cada uno publicando a una ruta/carpeta distinta
dentro del mismo sitio de GitHub Pages, o (b) migrar la documentación
existente del destino a MkDocs (el generador que usa `docs.yml` de este
template) y quedarse con un solo pipeline de publicación. Ninguna de las
dos se aplica por defecto: el equipo debe decidir según cuánto contenido
ya tenga publicado con el generador anterior.

### `post-hitl-merge-gate.yml`

**Colisión probable**: colisión de **nombre de archivo** sin relación
semántica — el destino ya tiene un workflow con ese nombre exacto para
una automatización propia no relacionada con el circuito agéntico (poco
probable pero posible dado que es un nombre bastante específico; más
probable si el destino ya tenía su propio concepto de "gate post
aprobación").

**Estrategia de merge**: renombrar el archivo del template (por ejemplo
`post-hitl-merge-gate.circuit.yml`) es una estrategia segura sin tocar
más wiring, porque los nombres de archivo de workflows de GitHub Actions
son arbitrarios: este workflow se dispara por eventos (`pull_request_review:
submitted`, `pull_request: synchronize`) y por invocar
`scripts/complete-approved-pr.ps1`, no por su nombre de archivo, así que
renombrarlo no rompe ninguna referencia interna del circuito.

### `post-merge-close-feature.yml`

**Colisión probable**: igual que `post-hitl-merge-gate.yml` — posible
colisión de nombre de archivo sin relación semántica.

**Estrategia de merge**: igual que el anterior. Renombrar el archivo del
template es seguro: este workflow se dispara cuando una PR hacia
`develop` se cierra como mergeada e invoca
`scripts/close-feature.ps1 -SkipLocalCleanup`, wiring que depende del
contenido y del evento disparador, no del nombre del archivo `.yml`.

## Límites de `scripts/check-adoption-conflicts.ps1`

`scripts/check-adoption-conflicts.ps1` es una herramienta de apoyo
**opcional**, de solo lectura, que reporta qué rutas conocidas de este
template ya existen en un directorio destino, agrupadas por elemento de
este mismo checklist. Ver
[la guía de usuario](../usuario/adopcion-proyecto-existente.md) para cómo
correrlo. Sus límites, explícitos y deliberados:

- **No compara contenido ni hace diff.** Solo verifica existencia de la
  ruta con `Test-Path`. No lee el contenido de ningún archivo del
  destino, así que no puede decirte si un archivo detectado es
  compatible, obsoleto o inofensivo de sobrescribir.
- **No distingue "archivo idéntico al del template" de "archivo que solo
  comparte el nombre".** Si el destino tiene un `scripts/ready-for-pr.ps1`
  que no tiene absolutamente nada que ver con el circuito, el script lo
  reporta igual que si fuera una adopción previa real del mismo template.
  La decisión de cuál es cuál queda siempre en manos de quien lee el
  reporte.
- **No usa historial de git.** No intenta inferir qué existía "antes" de
  mezclar el template en el destino, ni asume que el destino es (o no es)
  un repositorio git. Esto es una decisión deliberada, no una limitación
  técnica accidental: usar historial de git requeriría asumir que el
  destino tiene el template como remoto o subtree accesible, algo que no
  se puede garantizar en un repositorio destino genérico.
- **No resuelve ninguna colisión automáticamente.** El script solo
  detecta y reporta; no copia, fusiona, sobrescribe ni borra nada. La
  resolución de cada colisión reportada sigue siempre la guía de merge
  de la sección correspondiente de este mismo documento.
- **Límite conocido no resuelto: acceso denegado.** Si `$TargetPath`
  existe pero alguna de sus subrutas no es accesible (permisos
  denegados, unidad de red desconectada, etc.), `Test-Path` de
  PowerShell típicamente devuelve `$false` en vez de lanzar una
  excepción — lo que el script reportaría como "no existe" en vez de
  "no se pudo inspeccionar". El script no agrega lógica adicional para
  distinguir ambos casos: quien lo corre contra un destino con permisos
  restringidos debe tenerlo presente y no confiar ciegamente en un
  reporte de "sin colisiones" si sospecha que hay rutas inaccesibles.
- **La lista de rutas conocidas se mantiene manualmente alineada con
  este checklist.** El script no parsea este archivo Markdown en tiempo
  de ejecución; su tabla interna de rutas conocidas es una lista fija
  que replica a mano las rutas descriptas en las secciones de arriba. Si
  este checklist cambia (por ejemplo, se agrega un archivo nuevo al
  circuito), la tabla del script debe actualizarse por separado.
