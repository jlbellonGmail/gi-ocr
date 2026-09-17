# Validación del template

Ejecuta `pytest -q` para los tests del circuito. Los tests de producto todavía
son un placeholder porque este repositorio no declara stack de producto.

En CI, `circuit-tests`, `product-tests` y `local-reconciler-tests` aparecen
separados. El último requiere Windows y confirma la limpieza segura de
worktrees sólo después del cierre remoto.

`.audit` es una evaluación global independiente; no reemplaza la revisión de
una feature ni autoriza un merge por sí solo.
