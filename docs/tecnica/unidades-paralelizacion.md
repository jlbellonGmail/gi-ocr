# Unidades y paralelización

F14 registra cada unidad con version, mode, unitId, canonicalSlug, branch,
worktree, runPath, baseCommit y currentHead. El registro vive en
runs/<version>/<slug>/work-unit.json; ramas Maintenance auxiliares siguen
resolviendo su identidad por TNN mediante Resolve-CanonicalWorkUnitSlug.

unit-lifecycle.ps1 -Action inspect compara la base original con
origin/develop. -Action reconcile hace fetch y merge únicamente de
origin/develop; si Git detecta conflicto, aborta y devuelve BLOCKED / SEMANTIC,
sin aplicar ours/theirs. Una reconciliación marca CI, reviews y autorización
scoped como stale y exige revalidación sobre el nuevo HEAD.

Los merges son serializados por el punto de integración develop: cada unidad
debe reconciliar contra origin/develop vigente justo antes de mergear.
cleanup-work-unit.ps1 elimina sólo metadata Git y ramas ya desconectadas,
clasifica A_NOT_EXISTS, B_RESIDUAL_WINDOWS_EMPTY y
C_RESIDUAL_WINDOWS_CONTENT, y nunca borra contenido residual.

El gate post-HITL declara SingleMaintainer o MultiMaintainer. El primer modo
requiere autorización humana scoped, Reviewer de agente aprobado sobre
unit/base/HEAD, CI verde e integridad PASS; el segundo conserva la review
humana de GitHub. Ambos modos invalidan evidencia cuyo HEAD ya no coincide.
