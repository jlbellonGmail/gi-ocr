# CI wiring product tests

Esta feature (`04-ci-wiring-product-tests`) separa el job único `test` de
`.github/workflows/ci.yml` en dos jobs top-level (`circuit-tests` y
`product-tests`), sin agregar stack, dependencia ni herramienta nueva.
Ver `runs/v1.1.0/04-ci-wiring-product-tests/spec.md`, `plan.md` y `tasks.md`
para el detalle completo de criterios de aceptación (`AC-N`) y tareas.

## Por qué dos jobs en vez de uno

Antes de esta feature, `.github/workflows/ci.yml` tenía un único job
`test` con un comentario indicando dónde agregar en el futuro los pasos
de build/test del stack de producto. Ese comentario vivía **dentro** del
mismo job que corre `pytest` sobre `tests/` (los tests del propio
circuito agéntico), lo cual mezclaba dos responsabilidades distintas bajo
un solo status check:

- Verificar que el circuito agéntico (scripts, contrato, workflows) siga
  funcionando — esto es `circuit-tests`, hoy y siempre relevante mientras
  este template exista.
- Verificar el build/test del stack de producto real que un proyecto
  nacido de este template defina — esto es `product-tests`, hoy vacío
  porque este template no tiene stack propio (ver sección "Stack" de
  `AGENTS.md`).

Separarlos en dos jobs top-level, sin relación `needs:` entre ellos (así
que corren en paralelo), permite que cada uno tenga su propio status
check en GitHub, visible por separado en la pestaña "Checks" de una PR, y
que el día que un proyecto real agregue su stack, solo tenga que tocar el
job `product-tests` sin arriesgar romper accidentalmente los tests del
circuito ni su reporte de resultado.

## Por qué `product-tests` es requerido/bloqueante desde ya, pese a estar vacío

Esta fue una ambigüedad material identificada explícitamente durante la
Fase CLARIFY (ver `runs/v1.1.0/04-ci-wiring-product-tests/spec.md`, secciones
"Contexto y fuentes" y "Clarificaciones realizadas"): no había evidencia
previa en el repo sobre si `product-tests` debía ser status check
requerido en branch protection mientras solo corre un placeholder, y es
una decisión de gobernanza del circuito (afecta qué bloquea un merge
hacia `develop`/`main`), no una convención técnica inequívocamente
inferible de código o arquitectura existente. El primer intento de la
spec de esta feature la resolvió (incorrectamente) como supuesto propio
del `analyst-agent`, y `reviewer-agent` la rechazó en `audit-1.md` por
deber pasar por Fase CLARIFY.

**Pregunta elevada al humano:** ¿`product-tests` debe ser status check
requerido/bloqueante en branch protection desde ya, o solo cuando tenga
contenido real de stack?

**Respuesta del humano:** Requerido desde ya. Razón dada: el placeholder
siempre pasa en verde, así que no bloquea a nadie hoy, y evita tener que
acordarse de agregarlo a branch protection el día que el stack real
llegue.

Consecuencia directa de esta decisión: `circuit-tests` y `product-tests`
se tratan como **igualmente obligatorios/bloqueantes, con el mismo nivel
de exigencia**, tanto en la sección "CI/CD" de `AGENTS.md` como acá. Es
la referencia consistente que debe usar el checklist de branch protection
de `05-operational-readiness-docs` (feature separada, no implementada
acá): cuando esa feature configure branch protection real en GitHub,
debe marcar ambos jobs como status checks requeridos, no solo
`circuit-tests`.

## Forma exacta del marcador en `product-tests`

El job `product-tests` en `.github/workflows/ci.yml` tiene:

1. Un único step `actions/checkout@v4` (igual que `circuit-tests`, por si
   el stack real que se agregue después necesita el código del repo
   presente, aunque el placeholder actual no lo use).
2. Un bloque de comentario grande, delimitado por líneas de `#`
   repetidos, con el texto `PLACEHOLDER: build/test del stack de
   producto.`, que:
   - referencia explícitamente `docs/tecnica/arquitectura.md` como el
     lugar donde documentar la decisión de stack **antes** de agregar
     pasos reales aquí (regla de dominio no negociable, ver "Reglas de
     dominio" de `AGENTS.md`: no se agrega backend, base de datos,
     integración externa o dependencia de build sin decisión de
     arquitectura explícita);
   - indica que el step placeholder debe **reemplazarse por completo**,
     no complementarse al lado (ver caso borde "Reemplazo futuro del
     placeholder" en `spec.md`);
   - aclara que este job es gate obligatorio igual que `circuit-tests`,
     pese a correr solo un placeholder hoy.
3. Un único step llamado `Placeholder (sin stack definido)` con
   `run: echo "product-tests: sin stack de producto definido todavia. Ver
   docs/tecnica/arquitectura.md."`, que siempre termina en éxito (código
   de salida 0) y no depende de ningún artefacto, paquete o herramienta
   de un stack todavía no definido (cubre el caso borde "`product-tests`
   no debe fallar por dependencias inexistentes" de `spec.md`).

`tests/test_ci_workflow.py` verifica por substring de texto plano
(mismo patrón que
`tests/test_feature_contract_scripts.py::test_workflow_yaml_is_valid`,
sin parsear YAML ni agregar `pyyaml`) que: existen los nombres exactos de
job `circuit-tests:` y `product-tests:`; `pytest -v` sigue presente
dentro del bloque de `circuit-tests`; el texto `PLACEHOLDER` y la
referencia a `docs/tecnica/arquitectura.md` están presentes dentro del
bloque de `product-tests`; y ninguno de los dos jobs declara un `if:`
propio que lo excluya de algún evento del workflow. Las aserciones usan
substrings estables (nombres de job, texto del marcador), no indentación
exacta, para no romperse con reformateos menores del YAML que no cambian
su comportamiento.

## Advertencia de migración: nombre de status check `test` → `circuit-tests`

El job que corre `pytest` sobre `tests/` se llamaba `test` y ahora se
llama `circuit-tests`. En **este** template no hay branch protection
configurada todavía (setup manual pendiente, ítem
`05-operational-readiness-docs` de `ROADMAP.md`), así que no hay ninguna
configuración real que romper acá.

Sin embargo, cualquier **proyecto real que ya haya nacido de este
template** y configurado un status check requerido llamado `test` en
GitHub (branch protection sobre `develop`/`main`) debe, al adoptar esta
feature (por ejemplo vía merge/rebase desde el template o al aplicar este
mismo cambio manualmente):

1. Actualizar el status check requerido de `test` a `circuit-tests` en la
   configuración de branch protection de GitHub (Settings → Branches →
   reglas de protección de la rama correspondiente).
2. Agregar `product-tests` como status check requerido adicional (ver
   sección anterior sobre por qué es requerido desde ya, no solo cuando
   tenga contenido real).

Si esa migración no se hace, GitHub seguirá esperando un check llamado
`test` que nunca va a reportarse (porque el job ya no existe con ese
nombre), y la rama protegida quedará bloqueada indefinidamente para
cualquier PR nueva.

## Fuera de alcance (deliberado)

- Configurar branch protection real de GitHub (marcar checks como
  requeridos en la UI/API). Es la feature `05-operational-readiness-docs`.
- Agregar build/test real de cualquier stack de producto: este template
  no tiene stack propio; el job `product-tests` queda deliberadamente
  vacío de contenido real.
- Tocar `post-hitl-merge-gate.yml`, `post-merge-close-feature.yml` o
  `docs.yml`.
- Tocar `scripts/*.ps1`, `.agentic/` o el router de modelos.
- Agregar cualquier dependencia nueva de build o runtime, o cualquier
  entrada nueva en `docs/tecnica/arquitectura.md` sobre stack de
  producto.

Ver `runs/v1.1.0/04-ci-wiring-product-tests/spec.md` (sección "Explícitamente NO
incluye") para el detalle completo.
