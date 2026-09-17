# STATUS, observabilidad y reentrada

F13 define `STATUS.md` como vista humana derivada del presente. La precedencia es: Git, PR/CI, ROADMAP y `runs/` verificables; `STATUS.md` es una vista; el bloque AUTO y `update-status.ps1 -Json` son snapshots derivados y nunca sustituyen evidencia.

`update-status.ps1` conserva el texto manual, reconstruye el bloque AUTO de forma idempotente y deriva worktrees/unidades sólo desde worktrees Git reales y ramas Feature reconocibles. GitHub no disponible se representa como `UNKNOWN` y `check-status.ps1` lo clasifica como `TEMPORAL`; un snapshot con HEAD distinto es `STALE`; marcadores o rama contradictorios son `INCONSISTENTE`; fallos de ejecución son `ERROR_REAL`.

La salida machine-readable se obtiene sin persistencia con `pwsh -File scripts/update-status.ps1 -Json`; `-MachinePath` es explícito para consumidores que necesitan un archivo. Así, consultar no ensucia el checkout. Las carpetas Windows residuales no se cuentan como unidades: T04 conserva su clasificación en `check-integrity.ps1`.

Reentrada: leer STATUS, ejecutar `check-status.ps1`, verificar ROADMAP, localizar worktree/branch, abrir SUMMARY y evidencia de la unidad, y ejecutar la siguiente acción indicada. F14 puede consumir `activeUnits`, branch, worktree, HEAD, estado de ROADMAP y snapshot sin asumir que una carpeta física es actividad.
