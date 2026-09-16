# Proyecto: gi-ocr (Smart Invoice Capture)

Sistema de captura de comprobantes (impuestos, servicios, documentos
empresariales) vía OCR: captura o carga de imagen desde un frontend web
mobile-first, extracción de campos configurables, validación semántica,
revisión/confirmación humana y salida estructurada para integración con
sistemas externos/legacy por filesystem (`storage_bridge/`).

## Stack

- Lenguaje: Python 3.12+
- Framework API: FastAPI (sirve además el frontend estático en el mismo
  origen, un solo comando)
- Gestor de paquetes: `pip` + entorno virtual (`.venv`), dependencias en
  `backend/requirements.txt`
- OCR: RapidOCR (PP-OCRv3) + ONNX Runtime (motor principal, two-pass
  ROI-focalizada — ver `docs/tecnica/arquitectura.md`, ADR-006). EasyOCR
  se conserva como fallback interno opcional deshabilitado por defecto.
- Testing: `pytest`
- Documentación: MkDocs Material, publicada en GitHub Pages
- Frontend: HTML + JavaScript simple, sin framework, mobile-first

## Estructura del repo

- `backend/app/`: lógica de negocio y capa FastAPI (OCR, extracción,
  validación semántica, orquestación de pipeline, servicio de confirmación
  de revisión humana, exportación de resultados). `backend/app/main.py` es
  la única capa que expone HTTP; el resto de `backend/app/` es importable
  directo por scripts (`scripts/process_document.py`,
  `scripts/evaluate_ocr_service.py`, etc.) sin pasar por HTTP.
- `backend/config/`: configuración de servicios/documentos en texto plano
  (`services.ini`). No usar JSON como configuración persistente de OCR ni
  como salida legacy (ver `docs/tecnica/arquitectura.md`).
- `backend/tests/`: pytest de OCR, extracción, validación, API y pipeline.
- `frontend/`: HTML + JS servido por FastAPI (`StaticFiles`) en el mismo
  origen que la API.
- `storage_bridge/`: integración por filesystem con el sistema externo/legacy
  (`inbound/`, `ready/`, `failed/`). No versionar archivos generados ahí
  (ver `.gitignore`).
- `scripts/`: utilidades operativas (demo E2E, CLI de procesamiento,
  evaluador DATA, detección de zonas) y el motor ejecutable del circuito
  agéntico (`scripts/*.ps1`, ver más abajo).
- `runs/`: artefactos por feature (`spec.md`, `audit-N.md`,
  `test-report-N.md`, `decision.md`, y cuando aplique `post-hitl-gate-N.md`,
  `run.yaml` + `model-routing.jsonl`). No es código de producción, es
  historial del circuito.
- `.agentic/`: fuente canónica multiherramienta para roles, modelos,
  fallback, MCP y skills portables. Los adaptadores específicos
  (`.claude/agents/*.md`, `.codex/*.toml`, `.mcp.json`, `opencode.json`)
  se regeneran desde ahí — no se editan a mano.
- `.agents/skills/`: ubicación canónica de skills Agent Skills portables.
  Las copias requeridas por herramientas específicas se generan, no se
  editan manualmente.
- `docs/tecnica/`: un `.md` por servicio/documento OCR, nombrado solo con
  el slug sin número (ej. `gas.md`, no `01-gas.md`), con el algoritmo
  usado, casos borde y decisiones de diseño. Para quien mantiene el código.
- `docs/usuario/`: un `.md` por servicio/documento, mismo slug, con el
  propósito del endpoint/flujo y ejemplos de uso HTTP. Para quien consume
  la API o usa el frontend.
- `specs/`: specs de features anteriores a la adopción de este circuito
  (T3.x, T4). Se conservan como historial; las features nuevas usan
  `runs/<NN>-<slug>/spec.md` (ver Circuito).
- `tests/`: pytest de los scripts del circuito (`scripts/*.ps1`), no del
  producto OCR (eso vive en `backend/tests/`).

## Workflow del proyecto — circuito agéntico sin HITL intermedio

Este documento define cómo se ejecuta cualquier feature en este repo. Es
leído por todos los agentes al arrancar sesión, sea Claude Code, opencode o
Codex. No es negociable por ningún agente individual: si un agente cree que
debe saltarse un paso, debe decirlo explícitamente en su output, no
saltarlo en silencio.

El circuito tiene un solo punto de intervención humana: la decisión final
sobre la PR ya creada y con CI verde. Esa decisión es binaria: `MERGE` o
`NO MERGE`. No hay checkpoints humanos antes de crear la PR.

Cada uno de los 4 agentes corre como **subagente**, invocado puntualmente
para su etapa. Esto mantiene el contexto principal limpio: el subagente
hace su tarea, entrega su artefacto en `runs/`, y termina.

## Circuito

El contrato mínimo de artefactos vive en una sola fuente ejecutable:
`scripts/feature-contract.ps1`. Los prompts de Codex, Claude Code y
opencode pueden recordar el contrato, pero no deben duplicar validaciones:
deben invocar los scripts comunes. El contrato exige, según etapa:
`spec.md`, `decision.md`, `audit-N.md`, `test-report-N.md`,
`docs/tecnica/<slug>.md`, `docs/usuario/<slug>.md`, un enlace exacto en
`docs/tecnica/index.md`, un enlace exacto en `docs/usuario/index.md`,
estado correcto de `ROADMAP.md`, rama `feature/<NN>-<slug>`, PR contra
`develop` y CI verde.

1. `analyst-agent` (read-only, subagente, sesión nueva) → produce `spec.md`.
   El spec SIEMPRE debe incluir como criterios de aceptación la creación
   de `docs/tecnica/<slug>.md`, `docs/usuario/<slug>.md`,
   `runs/<NN>-<slug>/decision.md`, y enlaces exactos en
   `docs/tecnica/index.md` y `docs/usuario/index.md`.
2. `reviewer-agent` (read-only, subagente, sesión nueva) → produce
   `audit-N.md` con veredicto `approved` o `rejected`. Rechaza
   automáticamente si el spec no exige los dos `.md` de documentación.
   - Si `rejected` → vuelve a 1 con el feedback. La corrección sigue en
     el circuito agéntico; no hay checkpoint humano intermedio.
3. Si `approved` → `builder-agent` (write, subagente, en worktree propio)
   → implementa el código Y escribe `docs/tecnica/<slug>.md` y
   `docs/usuario/<slug>.md` como parte de terminar la feature, no aparte.
   También crea `runs/<NN>-<slug>/decision.md` con decisiones demostrables
   desde spec/auditoría/implementación, y ejecuta
   `scripts/update-doc-indexes.ps1 <NN>-<slug> "<Titulo>"`.
4. `qa-agent` (write, subagente, mismo worktree) → corre tests (pytest),
   verifica que el contrato común pase con `Assert-FeatureContract` (docs,
   decision, auditoría, reporte e índices), produce `test-report-N.md`.
   - Si falla (código o documentación faltante) → vuelve a 3 con el
     reporte. La corrección sigue en el circuito agéntico; no hay
     checkpoint humano intermedio.
5. Si QA aprueba → actualizar `ROADMAP.md` al estado `[-] READY_FOR_PR`
   para esa feature, sin marcar `[x]`, y commitear ese cambio en la rama
   de la feature. Script recomendado:
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ready-for-pr.ps1 <NN>-<slug>`.
6. Push de la rama de feature y creación automatizada de PR hacia
   `develop` (`gh pr create`). La PR debe incluir evidencias completas:
   resumen de cambios, resultados de tests, auditoría, checklist de
   aceptación, riesgos y enlaces a spec/docs.
7. Verificar que el CI de la PR corre en verde antes de pedir decisión
   humana. Script recomendado:
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\wait-pr-ci.ps1`.
8. **Único HITL:** el humano revisa la PR y sus evidencias completas y
   decide `MERGE` o `NO MERGE`.
   - Si decide `NO MERGE` → vuelve a 3 con observaciones concretas para
     que `builder-agent` corrija la implementación o, si corresponde, la
     spec.
   - Si decide `MERGE` aprobando la PR en GitHub → se dispara el gate
     post-HITL común. Ese gate vuelve a esperar los checks de Actions
     posteriores a la aprobación y solo ejecuta el merge si están verdes.
     Script común:
     `scripts/complete-approved-pr.ps1 -Slug <NN>-<slug> -PrNumber <n>`.
     En GitHub Actions lo invoca
     `.github/workflows/post-hitl-merge-gate.yml` con código confiable de
     `develop`.
   - Si esos checks post-HITL fallan → NO se mergea. El gate produce
     `runs/<NN>-<slug>/post-hitl-gate-N.md` con veredicto `rejected`,
     comenta la PR cuando corre en GitHub Actions y vuelve a 3:
     `builder-agent` corrige con ese error, luego QA/ready-for-pr siguen
     el circuito sin pedir otro checkpoint humano.
   - Si esos checks post-HITL quedan verdes → el gate mergea la PR a
     `develop`. No se marca `[x]` antes del merge.
9. **Cierre automático post-merge remoto:** GitHub Actions dispara
   `.github/workflows/post-merge-close-feature.yml` cuando una PR hacia
   `develop` se cierra como mergeada. El workflow corre código confiable
   de la rama base (`develop`) e invoca la lógica común:
   `scripts/close-feature.ps1 -Slug <NN>-<slug> -PrNumber <n> -SkipLocalCleanup`.
   Este script:
   - confirma con GitHub que la PR está `MERGED` y que su base es
     `develop`;
   - cambia al checkout principal de `develop` y sincroniza con
     `origin/develop`;
   - valida que `ROADMAP.md` tenga exactamente una entrada
     `[-] <NN>-<slug>` o exactamente una entrada `[x] <NN>-<slug>` si es
     una reejecución;
   - cambia exclusivamente `[-] <NN>-<slug>` a `[x] <NN>-<slug>`;
   - commitea y pushea ese cambio directo a `develop` solo si había cierre
     pendiente;
   - valida después del push que `origin/develop:ROADMAP.md` contiene
     exactamente una entrada `[x] <NN>-<slug>` y ninguna `[-] <NN>-<slug>`;
   - en modo local, recién entonces borra el worktree y la rama local de
     la feature ya mergeada;
   - en modo GitHub Actions, omite limpieza local porque un runner remoto
     no puede borrar worktrees del equipo del usuario.

Este último paso es la única automatización que toca `develop`
directamente, y es intencional que viva fuera de cualquier worktree.
GitHub y la PR mergeada son la fuente de verdad del cierre: si la feature
no está mergeada a `develop`, `close-feature.ps1` no debe marcar `[x]`.
El cierre post-merge tiene una sola implementación común:
`scripts/close-feature.ps1`. Codex, Claude Code y opencode no duplican esa
lógica en sus directorios propios; solo deben invocar ese script.

La limpieza local es una reconciliación separada: `ready-for-pr.ps1`
inicia `scripts/start-local-reconciler.ps1`, que observa
`origin/develop:ROADMAP.md` y solo elimina worktree/rama cuando ya existe
exactamente una entrada `[x] <NN>-<slug>` y ninguna `[-]`. Si el equipo o
el agente se cierran, la próxima ejecución del circuito puede relanzar el
reconciliador; la actualización remota de `ROADMAP.md` no depende de esa
limpieza.

## Retornos permitidos

- `reviewer-agent` → `analyst-agent` cuando el spec es `rejected`.
- `qa-agent` → `builder-agent` cuando QA falla.
- `HITL final` → `builder-agent` cuando la decisión es `NO MERGE`.

Cualquier otro retorno o pedido de intervención humana rompe el circuito y
debe declararse como excepción, no ejecutarse en silencio.

## Estados de ROADMAP.md

- `[ ]` pendiente: la feature no está cerrada.
- `[-]` `READY_FOR_PR`: implementación, documentación y QA aprobados; la
  PR existe o está lista para crearse; CI pendiente o verde; falta decisión
  final de merge.
- `[x]` completado: solo después de que la PR fue mergeada a `develop` y
  el cierre post-merge marcó el roadmap automáticamente.

Regla dura: `ROADMAP.md` no se marca `[x]` antes del merge. Antes del
merge solo puede quedar pendiente `[ ]` o `READY_FOR_PR` `[-]`.

## Git

- Rama base de trabajo diario: `develop`
- Rama de producción: `main` — solo recibe merges desde `develop` vía PR,
  cuando se decide hacer un release (no en cada feature)
- Cada feature: `feature/<NN>-<slug>`, en su propio `git worktree` bajo
  `../worktrees/<slug>/` — esto habilita correr varios circuitos en
  paralelo sin pisarse
- Nunca commitear directo a `develop` (salvo el cierre automatizado de
  `ROADMAP.md`, ver paso 9) ni nunca directo a `main`
- La PR hacia `develop` se crea automáticamente después de QA aprobado.
- El humano no abre la PR ni hace checkpoints previos: solo decide
  `MERGE` o `NO MERGE` con la PR y sus evidencias a la vista.

En repositorios single-maintainer, cuando GitHub impide que el autor apruebe
su propia PR, la única alternativa válida es el camino explícito
`workflow_dispatch` definido por la unidad `14-hitl-single-maintainer`. Ese
camino no reemplaza `reviewDecision == APPROVED` para multi-maintainer y no
puede activarse por `push` o `synchronize`. Requiere actor autorizado por la
variable de repositorio `vars.SINGLE_MAINTAINER_HITL_ACTORS`, PR/base/branch
exactos, SHA completo ingresado, checks `CI/test` y `CI/quality` exitosos para
ese SHA, intención `MERGE` y confirmación exacta. El workflow debe revalidar
todo inmediatamente antes del merge y usar una precondición de SHA. La
configuración ausente o inválida falla cerrado. El bootstrap es único y debe
verificar la default branch real con `gh repo view --json defaultBranchRef`.

## Versionado (tags)

- Cada release a `main` se marca con un tag `vX.Y.Z` (SemVer:
  major.minor.patch), pusheado por el humano después de mergear a `main`
  (`git tag vX.Y.Z && git push origin vX.Y.Z`).
- Los agentes nunca crean tags — es una decisión del humano, en el momento
  de release hacia `main`.
- El empaquetado Docker / release automatizado (`release.yml`) todavía no
  existe en este repo: se agrega como tarea futura del `ROADMAP.md` cuando
  haya una decisión de despliegue concreta (ver `docs/tecnica/arquitectura.md`).
  No inventar esa infraestructura sin esa decisión.

## CI/CD

- **CI** (`.github/workflows/ci.yml`): corre tests (`pytest`, suite
  `backend/tests/` + `tests/`) en cada push/PR a `develop` o `main`. Gate
  obligatorio antes de mergear cualquier PR (paso 7 del circuito). El lint
  automatizado (ruff u otro) queda pendiente como tarea futura del
  `ROADMAP.md`; no se agrega sin antes dejar el código base limpio para
  evitar romper el CI el mismo día de la adopción del circuito.
- **Docs** (`.github/workflows/docs.yml`): se dispara al pushear a `main`
  con cambios en `docs/` o `mkdocs.yml`. Publica el sitio MkDocs a GitHub
  Pages. Público, sin gate por ahora.
- **Post-merge close** (`.github/workflows/post-merge-close-feature.yml`):
  ver paso 9 del circuito.
- **Post-HITL merge gate**
  (`.github/workflows/post-hitl-merge-gate.yml`): se dispara cuando el
  humano aprueba la PR hacia `develop`; invoca
  `scripts/complete-approved-pr.ps1`, espera checks post-aprobación,
  mergea solo si están verdes y devuelve feedback a builder si fallan.
- **Release**: pendiente (ver sección Versionado). No hay `Dockerfile` ni
  `release.yml` todavía.

## Herramientas locales requeridas

- Windows PowerShell (`powershell.exe`) para los scripts de automatización
  en `scripts/*.ps1`.
- Git (`git`) para ramas, worktrees, commits, push y verificación de merge.
- GitHub CLI (`gh`) instalado, en `PATH` y autenticado para crear PRs,
  consultar estado de PR mergeada y esperar checks de CI.
- Python 3.12+ con entorno virtual (`.venv`) y
  `pip install -r backend/requirements.txt` para instalar dependencias,
  correr tests y ejecutar tooling Python.

## Artefactos

Cada ciclo de feature genera su carpeta en `runs/<NN>-<slug>/` con:
- `spec.md`
- `audit-N.md` (uno por intento del reviewer-agent)
- `test-report-N.md` (uno por intento del qa-agent)
- `decision.md` (archivo canónico obligatorio con decisiones demostrables
  y evidencia de cierre/merge; no debe quedar vacío ni ornamental)
- `post-hitl-gate-N.md` (cuando el gate posterior a la aprobación humana
  necesita dejar evidencia de merge aprobado o feedback automático para
  builder si Actions falla después del HITL)

Ningún agente sobreescribe el artefacto de otro. Cada intento se numera.
El número y slug de cada feature sale de `ROADMAP.md`.

## Formato de veredicto

`reviewer-agent` y `qa-agent` deben abrir su output con un bloque YAML así,
antes de cualquier prosa:

```yaml
status: approved | rejected
attempt: <n>
feedback:
  - punto concreto 1
  - punto concreto 2
```

## Configuración de modelos (Claude Code, opencode, Codex)

`AGENTS.md` sigue siendo la fuente canónica de reglas compartidas del
repo. Las definiciones funcionales por rol viven una sola vez en
`.agentic/roles/*.md` (incluyen las reglas de dominio OCR propias de este
proyecto); los metadatos, permisos y modelos por herramienta viven en
`.agentic/agents.json`; el router OpenCode vive en `.agentic/models.json`;
y la fuente MCP vive en `.agentic/mcp.json`.

Después de editar `.agentic/`, regenerar y validar adaptadores:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-agentic-adapters.ps1 -Check
```

No editar manualmente archivos generados en `.claude/agents/*.md`,
`.codex/*.config.toml`, `.codex/config.toml`, `.mcp.json` ni
`opencode.json`. El modo `-Check` falla si detecta divergencia o
adaptadores legacy en `.codex/prompts/` o `.opencode/agent/`.

Para OpenCode, `opencode.json` consume `AGENTS.md` mediante
`instructions` y referencia los prompts canónicos con
`prompt: "{file:./.agentic/roles/<role>.md}"`. `model`,
`reasoningEffort`, `permission` y MCP son adaptador de OpenCode generado,
no fuente de verdad manual. El modelo por defecto configurado hoy es
`anthropic/claude-sonnet-4-5` (ya en uso real en este repo); Go, Zen y
OpenRouter quedan declarados en `.agentic/models.json` como fallback
autorizado para cuando se conecten con `/connect`.

Para Claude Code, `model` y `effort` sí quedan en el frontmatter de cada
`.claude/agents/*.md`, porque Claude Code no tiene un mecanismo
equivalente de override centralizado por agente de proyecto. El cuerpo de
esos archivos se genera desde `.agentic/roles/*.md`. `CLAUDE.md`
mantiene `@AGENTS.md` porque Claude Code lee `CLAUDE.md` como memoria de
proyecto y soporta imports `@`.

Para ejecutar el circuito completo hasta `git push`, creación de PR,
consulta/espera de CI y cierre post-merge, Claude debe correr como
Claude Code en un entorno con permisos reales sobre el repo Git y GitHub.

Para Codex, la configuración nativa del repo vive en `.codex/`. Ese
directorio se usa como `CODEX_HOME` reproducible del proyecto:

- `.codex/config.toml`: defaults comunes de Codex y MCP generado.
- `.codex/<role>.config.toml`: perfil por agente, invocado con
  `codex exec -p <role>`.
- `.agentic/roles/<role>.md`: prompt canónico canalizado al ejecutar el
  perfil Codex.

Ejemplo desde PowerShell, ejecutado por el Main Agent al delegar:

```powershell
$env:CODEX_HOME = (Resolve-Path .\.codex).Path
Get-Content .\.agentic\roles\analyst-agent.md -Raw | codex exec -p analyst-agent -C . -
```

Los perfiles Codex fijan modelo y esfuerzo; las reglas comunes del
circuito siguen viviendo en este `AGENTS.md`, para evitar duplicación.

Para resolver modelos OpenCode antes de iniciar una etapa, usar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\resolve-agentic-model.ps1 `
  -Role analyst-agent `
  -Feature <NN>-<slug>
```

La declaración mínima previa a `spec.md` es
`runs/<NN>-<slug>/run.yaml`, basada en `.agentic/run.example.yaml`.
`model: default` usa el default del rol; un modelo explícito debe estar en
allowlist. La variante (`variant`) se valida aparte del modelo. El
fallback se declara como lista controlada (`go`, `zen`,
`openrouter-free`) y OpenRouter solo se usa si aparece explícitamente en
la declaración o en `-Fallback`.

El router registra evidencia en
`runs/<NN>-<slug>/model-routing.jsonl`: feature, agente, etapa,
proveedor, modelo, variante, origen de selección, fallback aplicado,
motivo, fecha UTC, duración, resultado y costo si la herramienta lo
entrega de forma confiable. No inventa costos.

Credenciales: no se guardan secretos en el repo. El modelo directo
Anthropic usa `ANTHROPIC_API_KEY` o la marca `AGENTIC_ANTHROPIC_READY=1`
para entornos ya conectados. OpenCode Go/Zen se conectan fuera del repo
con `/connect`; para automatización local se usan marcas no secretas
`AGENTIC_OPENCODE_GO_READY=1` y `AGENTIC_OPENCODE_ZEN_READY=1`.
OpenRouter usa `OPENROUTER_API_KEY` o la marca
`AGENTIC_OPENROUTER_READY=1` cuando el entorno ya está conectado sin
exponer tokens.

## Reglas adicionales

Ver `.claude/rules/` para instrucciones modulares por dominio (OCR,
seguridad de `storage_bridge`, estilo). Vacío por ahora — se completa a
medida que el proyecto lo necesite, no de entrada. opencode las lee vía el
campo `instructions` de `opencode.json`. Si `.claude/rules/` deja de estar
vacío, Codex debe referenciar esas reglas desde `.agentic/roles/*.md`
(canalizado a los perfiles `.codex/<role>.config.toml`).

## Reglas de dominio OCR (no negociables por ningún agente)

- Diferenciar siempre: texto bruto OCR, campo candidato, campo validado,
  campo rechazado, campo no encontrado.
- Toda mejora OCR debe declarar: campo extraído, tipo de documento,
  fixture o imagen usada, salida esperada, validación aplicada y falsos
  positivos evitados. Es un criterio de aceptación más para
  `analyst-agent`/`reviewer-agent`, no un aparte.
- La configuración de extracción por servicio vive en texto plano
  (`backend/config/services.ini`), no en JSON ni hardcodeada en Python por
  servicio (ver ADR en `docs/tecnica/arquitectura.md`).
- No versionar imágenes reales de comprobantes ni archivos generados en
  `storage_bridge/{inbound,ready,failed}/`.

## Setup manual (una sola vez, no automatizable)

- **GitHub Pages** (Settings → Pages → Source): elegir "GitHub Actions".
  Necesario para que `docs.yml` pueda publicar el sitio MkDocs.
- **Rama `develop`**: ya existe y hoy está sincronizada con `main`. Las
  features en curso previas a este circuito (por ejemplo
  `feature/t4-mvp-web-operable`) siguen ahí hasta que se cierren; no se
  renombran ni se fuerzan al esquema `feature/<NN>-<slug>` retroactivamente
  (ver `ROADMAP.md`, sección Historial).
