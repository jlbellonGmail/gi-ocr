# Especificación: 14-hitl-single-maintainer

## Objetivo

Agregar al circuito de GI-OCR una vía HITL explícita, segura y auditable
para repositorios single-maintainer cuando el autor de la PR y el mantenedor
humano son la misma cuenta, sin eliminar ni debilitar el camino actual basado
en `reviewDecision == APPROVED`.

## Problema

GitHub no permite que el autor de una pull request se apruebe a sí mismo.
Por eso, en la PR #25 el humano revisó el cambio, pero
`gh pr review 25 --approve` devolvió `Review Can not approve your own pull
request` y `reviewDecision` permaneció vacío. El gate actual rechaza la
ejecución antes de comprobar los checks y antes de mergear.

## Alcance

- Incorporar una autorización manual single-maintainer mediante
  `workflow_dispatch`.
- Mantener sin cambios semánticos el camino multi-maintainer basado en
  GitHub Review y `reviewDecision == APPROVED`.
- Validar identidad, PR, rama, base, SHA, checks e intención de merge.
- Rechazar cualquier ejecución cuyo HEAD cambie después de la revisión.
- Registrar de forma auditable quién autorizó, cuándo, qué PR, qué SHA y qué
  checks fueron validados.
- Cubrir la nueva vía con tests automatizados y documentación del circuito.

## Fuera de alcance

- Cambios en OCR, extracción, validación documental o APIs del producto.
- Adopción de Template v2.0.0.
- Creación de una segunda cuenta o aprobación delegada externa.
- Reemplazo del mecanismo `reviewDecision == APPROVED`.
- Autorización mediante CI, labels, comentarios, `decision.md`, push o
  `synchronize`.
- Cambios en el contrato de datos de `storage_bridge`.

## Estado actual

- `.github/workflows/post-hitl-merge-gate.yml` se dispara por
  `pull_request_review` y por `pull_request.synchronize`.
- El workflow ejecuta `scripts/complete-approved-pr.ps1` desde un checkout
  confiable de `develop`.
- `complete-approved-pr.ps1` valida PR abierta, base, head y luego exige
  exactamente `$pr.reviewDecision -eq "APPROVED"`.
- Si la validación pasa, espera checks distintos del propio workflow y
  ejecuta `gh pr merge`.
- `scripts/feature-contract.ps1` valida artefactos de feature, no la
  autorización humana.
- `post-merge-close-feature.yml` sólo actúa cuando GitHub informa que la PR
  ya fue mergeada.
- No existe `workflow_dispatch`, archivo de autorización humana, label o
  comentario reconocido por el gate.

## Bootstrap y activación inicial

`workflow_dispatch` sólo puede dispararse cuando la definición del workflow
ya existe en la default branch del repositorio. Antes de implementar o usar
el nuevo mecanismo debe obtenerse evidencia real con:

```powershell
gh repo view --json defaultBranchRef
```

No se debe asumir que `develop` es la default branch. La respuesta debe
registrarse en la evidencia de la unidad y determinar la topología efectiva.

La unidad 14 se incorpora inicialmente mediante el circuito disponible antes
de contar con el nuevo dispatch. El bootstrap debe ser único y auditable:

1. Confirmar la default branch real con el comando anterior.
2. Preparar la PR de implementación de esta unidad contra la base que la
   política real del repositorio determine; si la workflow sólo queda
   disponible al llegar a la default branch, la PR debe llegar a esa rama.
3. Verificar CI verde para el HEAD exacto de la unidad 14.
4. Obtener revisión humana explícita sobre ese HEAD.
5. Confirmar el SHA completo revisado.
6. Realizar una única aprobación/merge manual de bootstrap protegido por
   `--match-head-commit <SHA>` si la política real del repositorio permite
   ese mecanismo.
7. Registrar en `runs/14-hitl-single-maintainer/` la default branch, PR,
   actor, timestamp, SHA, checks y resultado del bootstrap.
8. Sólo después de que la definición esté publicada en la default branch,
   habilitar el uso normal del nuevo `workflow_dispatch`.

Si la default branch real no permite activar directamente el workflow después
del merge a `develop`, la implementación debe detenerse y resolver primero
esa topología. No se debe inventar una ejecución de `workflow_dispatch` desde
una rama donde GitHub no pueda cargar la definición del workflow.

La excepción de bootstrap no puede reutilizarse para features posteriores ni
convertirse en una vía implícita de autorización. Una vez activo el nuevo
mecanismo, todo caso single-maintainer debe pasar por `workflow_dispatch` y
todo caso multi-maintainer por GitHub Review.

## Diseño propuesto

El mismo gate debe aceptar dos modos explícitos:

1. **Review mode**: el camino actual, habilitado únicamente por una review
   GitHub válida y `reviewDecision == APPROVED`.
2. **Single-maintainer mode**: ejecución manual mediante `workflow_dispatch`,
   con inputs obligatorios y validaciones independientes.

El modo debe ser seleccionado por el evento y no por una opción libre que
pueda convertir un `synchronize` en autorización. El workflow debe usar el
checkout confiable de `develop` para ejecutar la lógica de merge y no código
no confiable de la rama de la PR.

El gate no puede esperar por sí mismo ni considerar su propia ejecución como
un check requerido. Los checks previos válidos deben provenir de una
allowlist explícita. Para GI-OCR, la allowlist mínima es:

- workflow `CI`, job `test` (`CI/test`);
- workflow `CI`, job `quality` (`CI/quality`).

`Post-HITL merge gate` queda excluido expresamente de esa allowlist. Cada
check permitido debe estar asociado exactamente al `expected_head_sha`; un
check SUCCESS de otro SHA no es válido. Checks pendientes, ausentes,
`cancelled`, `skipped` o `failure` impiden el merge cuando pertenecen a la
allowlist obligatoria.

Por defecto no se introduce `human-authorization.md`. Escribirlo sobre la
rama de la PR cambiaría el SHA que el humano revisó. La evidencia primaria
debe ser el evento `workflow_dispatch`, sus inputs, actor, timestamp, logs,
job summary y un artefacto de ejecución generado fuera de la rama, si se
necesita conservar un resumen estructurado.

## Flujo multi-maintainer

1. Un revisor distinto del autor aprueba la PR mediante GitHub Review.
2. `pull_request_review` dispara el gate.
3. El gate obtiene PR, base, rama y `reviewDecision` en vivo.
4. Verifica únicamente los checks de la allowlist obligatoria, excluyendo el
   propio `Post-HITL merge gate`, y confirma que corresponden al HEAD
   evaluado.
5. Ejecuta el merge sólo si todas las comprobaciones pasan.
6. `post-merge-close-feature.yml` realiza el cierre de `ROADMAP.md` después
   del merge.

El comportamiento existente debe conservarse, incluido el rechazo cuando no
existe una aprobación GitHub válida.

## Flujo single-maintainer

1. El mantenedor revisa manualmente la PR y sus evidencias fuera del
   workflow.
2. El mantenedor inicia explícitamente `workflow_dispatch` y proporciona
   todos los inputs requeridos.
3. GitHub registra el actor y la hora de la ejecución.
4. El workflow valida que el actor esté autorizado para single-maintainer.
5. El workflow consulta la PR indicada y valida estado, base, rama y HEAD.
6. Valida que el HEAD real coincida exactamente con el SHA ingresado.
7. Consulta los checks obligatorios de la allowlist (`CI/test` y
   `CI/quality`) para el mismo HEAD y exige estado `SUCCESS`; el propio
   `Post-HITL merge gate` nunca se espera a sí mismo.
8. Exige una intención explícita y no ambigua de merge.
9. Revalida PR, base, rama, HEAD y checks inmediatamente antes de mergear.
10. Ejecuta el merge usando una condición de HEAD equivalente a
    `--match-head-commit <expected_head_sha>` o una API con el mismo efecto.
11. Registra en logs y summary el actor, timestamp, PR, base, rama, SHA,
    checks, intención y resultado.
12. El cierre de roadmap permanece exclusivamente a cargo del flujo
    post-merge existente.

El camino no debe ser invocable por `push` ni por `synchronize`.

## Inputs manuales

El `workflow_dispatch` debe exigir, como mínimo:

- `pr_number`: número exacto de la PR, entero positivo.
- `expected_branch`: rama esperada completa, por ejemplo
  `feature/13-observabilidad-operacion`.
- `expected_base`: base esperada, normalmente `develop`.
- `expected_head_sha`: SHA completo de 40 caracteres ingresado explícitamente.
- `hitl_intent`: valor cerrado `MERGE`, no texto libre.
- `confirmation`: valor cerrado suficientemente explícito, por ejemplo
  `I_CONFIRM_HITL_MERGE`, para evitar un dispatch accidental.

Los inputs no sustituyen las consultas en vivo: todos deben compararse con la
PR actual y con el estado remoto inmediatamente antes del merge.

## Validaciones de seguridad

- Actor: leer la variable de repositorio de GitHub Actions
  `vars.SINGLE_MAINTAINER_HITL_ACTORS`, con logins exactos separados por
  comas, y comparar `github.actor` exactamente contra esa allowlist.
  Si la variable no existe, está vacía o no contiene al actor, fallar
  cerrado.
- PR: el número consultado debe ser exactamente `pr_number` y estar `OPEN`.
- Base: `baseRefName` debe coincidir con `expected_base` y la política debe
  permitir sólo `develop`.
- Rama: `headRefName` debe coincidir con `expected_branch` y con el patrón de
  feature permitido.
- SHA: `headRefOid` debe ser exactamente `expected_head_sha`, sin prefijos,
  truncamientos ni comparación sólo por commit de la rama local.
- Checks: todos los checks obligatorios de la allowlist deben terminar en
  `SUCCESS`; para GI-OCR son `CI/test` y `CI/quality`. El propio
  `Post-HITL merge gate` queda excluido y el gate no puede esperar por sí
  mismo. Checks faltantes, pendientes, `cancelled`, `skipped` o `failure`
  impiden el merge. Cada check debe corresponder exactamente a
  `expected_head_sha`; un SUCCESS de otro SHA no es válido.
- Intención: `hitl_intent` y `confirmation` deben coincidir exactamente con
  los valores permitidos.
- Tiempo: repetir todas las validaciones justo antes del merge.
- Merge: usar una precondición de SHA en la operación de merge para evitar
  carreras entre la última lectura y el merge.
- Permisos: conservar `contents: write`, `pull-requests: write` y limitar
  el resto de permisos al mínimo necesario.

## Reglas de autorización

- Sólo `workflow_dispatch` puede activar single-maintainer mode.
- El actor de GitHub del dispatch debe compararse exactamente contra
  `vars.SINGLE_MAINTAINER_HITL_ACTORS`, configuración explícita del
  repositorio.
- Si esa variable no existe, está vacía o no contiene exactamente a
  `github.actor`, el workflow debe fallar cerrado.
- La regla verificable de autorización es la conjunción exacta de evento
  `workflow_dispatch`, actor autorizado, inputs HITL válidos y
  `confirmation == I_CONFIRM_HITL_MERGE`; no se infiere humanidad del actor.
- `MERGE` debe ser una elección explícita; ausencia, otro valor o texto
  ambiguo implica rechazo.
- No se acepta como autorización suficiente CI verde, existencia de PR,
  `decision.md`, label, comentario genérico, `synchronize`, push o autoría
  del commit.
- No se debe inferir autorización a partir del nombre de la rama, del autor
  de la PR o de una ejecución anterior.
- El modo review no debe degradarse a single-maintainer automáticamente si
  `reviewDecision` está vacío.
- Deben registrarse el actor y la fuente
  `vars.SINGLE_MAINTAINER_HITL_ACTORS`, sin exponer secretos.

## Protección contra stale HEAD

El SHA ingresado es la identidad exacta de lo revisado. El workflow debe:

1. Comparar `expected_head_sha` con `headRefOid` al inicio.
2. Esperar/consultar checks asociados a ese SHA, no sólo a la PR.
3. Volver a obtener PR y SHA antes del merge.
4. Rechazar si `headRefOid != expected_head_sha` en cualquier punto.
5. Rechazar si aparece un commit nuevo, aunque los checks de la PR estén
   verdes.
6. Pasar el SHA como condición de la operación de merge cuando GitHub CLI o
   la API lo permitan.
7. No reintentar automáticamente con un SHA distinto. Un cambio requiere
   nueva revisión humana y nuevo `workflow_dispatch`.

## Evidencia/auditoría

La ejecución debe dejar evidencia fuera de la rama de la PR con:

- run ID y attempt de GitHub Actions;
- actor autorizado y timestamp UTC;
- modo `single-maintainer`;
- número de PR, base y rama;
- `expected_head_sha` y `headRefOid` observado;
- lista y estado de checks obligatorios;
- valores de intención y confirmación, sin secretos;
- resultado de cada validación;
- resultado final de merge o rechazo;
- enlace a la PR y al workflow run.

El job summary y los logs de Actions son la evidencia primaria propuesta.
Puede conservarse además un artefacto de workflow generado durante la
ejecución, sin escribir sobre la rama. No se requiere `human-authorization.md`
salvo que una auditoría posterior demuestre que los logs/summary y el
artefacto retenido no son suficientes. Si se necesitara, debería generarse
fuera de la rama aprobada o registrarse después del merge, nunca como un
commit previo que invalide el SHA revisado.

## Archivos esperados

Una futura implementación modificaría como mínimo:

- `.github/workflows/post-hitl-merge-gate.yml`: agregar
  `workflow_dispatch`, inputs, selección segura de modo y registro de
  evidencia.
- `scripts/complete-approved-pr.ps1`: aceptar un modo single-maintainer y
  validar actor/PR/base/rama/SHA/checks/intención antes del merge, sin
  eliminar la validación `reviewDecision` del modo review.
- `tests/test_complete_approved_pr_script.py` o el archivo de tests que se
  establezca para el script: cubrir validaciones y no-merge en fallos.
- `tests/test_post_hitl_workflow.py` o un test estructural equivalente:
  verificar triggers, inputs, permisos y separación de modos.
- `docs/tecnica/circuito-agentico.md`: documentar ambos mecanismos y la
  evidencia.
- `docs/usuario/circuito-agentico.md`: documentar la operación manual
  single-maintainer y sus rechazos.
- `AGENTS.md`: actualizar la regla del único HITL y la descripción del gate.

No se prevé modificar `scripts/feature-contract.ps1`, salvo que una futura
decisión explícita determine que la evidencia de autorización deba formar
parte del contrato de artefactos. No se prevé crear `human-authorization.md`
en esta unidad.

## Tests requeridos

- Test estructural: `workflow_dispatch` existe en la definición que reside en
  la default branch y tiene todos los inputs.
- Test estructural: el camino actual `pull_request_review` conserva la
  exigencia `reviewDecision == APPROVED`.
- Test estructural: `synchronize`, `push` y CI verde no autorizan el nuevo
  camino.
- Test estructural: el propio `Post-HITL merge gate` está excluido de los
  checks previos y el gate no espera por sí mismo.
- Test de allowlist de checks: sólo `CI/test` y `CI/quality` son obligatorios
  inicialmente.
- Test de SUCCESS perteneciente a otro SHA: rechazo.
- Tests de check faltante, pendiente, `cancelled`, `skipped` y `failure`:
  rechazo cuando el check es obligatorio.
- Test de actor autorizado y actor no autorizado usando
  `vars.SINGLE_MAINTAINER_HITL_ACTORS`.
- Tests de variable ausente, vacía, con formato inválido y sin coincidencia
  exacta: todos deben fallar cerrado.
- Test de actor inferido del autor de la PR, owner, branch o commit: rechazo.
- Test de PR inexistente, cerrada o no abierta.
- Test de base incorrecta.
- Test de rama incorrecta.
- Test de SHA truncado, inválido, distinto y cambiado durante la ejecución.
- Test de checks faltantes, pendientes, fallidos y exitosos.
- Test de intención ausente o distinta de `MERGE`.
- Test de confirmación inválida.
- Test de doble validación antes de merge.
- Test de uso de precondición de SHA en el merge.
- Test de que ningún rechazo ejecuta `gh pr merge`.
- Test de que una ejecución válida sí llega al merge sólo después de todas
  las validaciones.
- Test de que el registro contiene actor, timestamp, PR, SHA, checks y
  resultado, sin secretos.
- Test de bootstrap: exige evidencia de default branch, CI verde, revisión
  humana, SHA exacto y merge único protegido por `--match-head-commit` cuando
  la política lo permite.
- Regresión de `tests/test_feature_contract_scripts.py`,
  `tests/test_close_feature_script.py` y
  `tests/test_wait_pr_ci_script.py`.

## Compatibilidad hacia atrás

- Multi-maintainer continúa usando GitHub Review y
  `reviewDecision == APPROVED`.
- Una PR con `reviewDecision` vacío sigue siendo rechazada por el modo review.
- Los workflows post-merge y el cambio `[x]` de `ROADMAP.md` conservan su
  semántica.
- Los artefactos existentes de `runs/` no se renombran ni se reemplazan.
- La solución no cambia contratos HTTP, OCR, storage bridge ni releases.

## Casos borde

- El mantenedor dispara el workflow para otra PR por error: el número, rama,
  base y SHA deben impedir el merge.
- El dispatch usa un SHA de 7 caracteres: rechazo.
- Se agrega un commit mientras corren los checks: rechazo por stale HEAD.
- Un check aparece verde en la PR pero corresponde a otro SHA: rechazo.
- El workflow se reintenta: debe volver a validar todo y no reutilizar una
  autorización anterior.
- Dos dispatches concurrentes para la misma PR: concurrency group y
  revalidación deben impedir doble merge.
- Actor autorizado pero confirmation inválida: rechazo.
- PR abierta con base distinta de `develop`: rechazo.
- `gh` devuelve datos incompletos o error transitorio: no mergear.
- El job logra validar pero falla antes del merge: dejar evidencia de fallo,
  sin marcar roadmap ni ejecutar cierre.
- Logs o summary contienen datos sensibles: no incluir tokens ni contenido
  OCR; sólo metadatos de autorización y CI.

## Riesgos

- Una allowlist mal configurada podría autorizar a una cuenta incorrecta.
- Un workflow que use inputs sin consultar GitHub en vivo podría mergear un
  SHA stale.
- Un permiso excesivo de `GITHUB_TOKEN` aumentaría el impacto de un error.
- Un artefacto de evidencia mal retenido podría dificultar auditoría.
- Una condición amplia para `workflow_dispatch` podría convertirlo en un
  auto-merge silencioso.
- La operación manual puede ejecutarse por error si la confirmación no es
  suficientemente explícita.

## Rollback

- Deshabilitar el nuevo camino single-maintainer manteniendo el camino
  `pull_request_review`.
- Revertir únicamente los cambios del workflow/script/documentación/tests
  de esta unidad.
- No revertir código OCR ni modificar el estado de `ROADMAP.md` como parte
  del rollback.
- Si una ejecución se comporta de forma inesperada, impedir nuevos dispatches
  y revisar logs antes de cualquier merge.

## Criterios de aceptación

1. El camino multi-maintainer continúa exigiendo
   `reviewDecision == APPROVED`.
2. Existe un camino single-maintainer activable únicamente mediante
   `workflow_dispatch`.
3. Antes de usarlo, se verifica con `gh repo view --json defaultBranchRef`
   cuál es la default branch real.
4. El bootstrap de la unidad 14 ocurre una sola vez, con CI verde, revisión
   humana, SHA exacto, merge manual protegido por `--match-head-commit`
   cuando la política lo permite y evidencia en `runs/14-hitl-single-maintainer/`.
5. El actor del dispatch se valida exactamente contra
   `vars.SINGLE_MAINTAINER_HITL_ACTORS`.
6. La variable ausente, vacía o sin coincidencia produce fallo cerrado.
7. Se valida el número exacto de PR y que la PR esté abierta.
8. Se valida la base exacta esperada.
9. Se valida la rama exacta esperada.
10. Se exige un `expected_head_sha` completo ingresado explícitamente.
11. Se verifica `headRefOid == expected_head_sha` antes y justo antes del
   merge.
12. Sólo `CI/test` y `CI/quality` son checks obligatorios inicialmente; el
    propio `Post-HITL merge gate` queda excluido y el gate no espera por sí
    mismo.
13. Cada check obligatorio corresponde exactamente al SHA esperado y todos
    terminan en `SUCCESS`; faltantes, pendientes, `cancelled`, `skipped` o
    `failure` impiden el merge.
14. Se exige confirmación explícita de intención `MERGE`.
15. Cualquier cambio de HEAD produce rechazo y no reintenta con otro SHA.
16. La operación de merge usa una precondición equivalente a
    `--match-head-commit`.
17. CI verde por sí solo, PR existente, `decision.md`, labels, comentarios,
    `synchronize`, push y autoría no pueden autorizar por sí solos.
18. La evidencia registra actor, timestamp, fuente de allowlist, PR, base,
    rama, SHA, checks,
    intención y resultado sin cambiar el SHA revisado.
19. Los tests cubren los caminos aprobados, rechazados, stale HEAD,
    concurrencia y ausencia de merge en fallos.
20. `human-authorization.md` no se crea salvo una justificación posterior de
    insuficiencia de logs/summary/artefactos; la especificación inicial no lo
    requiere.
21. No se modifica la arquitectura OCR ni los contratos del producto.
