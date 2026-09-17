# Seguridad profesional

F11 aplica seguridad por capacidad y riesgo, no por proveedor ni por modelo.
La fuente ejecutable es `.agentic/security-policy.json` y su validador es
`scripts/security-policy.ps1`.

## Política

`READ`, `MODIFY_LOCAL`, `EXECUTE`, `NETWORK_READ` y `GIT_WRITE` en la rama
propia pueden ejecutarse autónomamente según LIGHT/STANDARD/FULL. `REMOTE_WRITE`,
`MERGE`, `EXTERNAL_WRITE`, `DESTRUCTIVE` y `SECRET_ACCESS` requieren gate o
autorización explícita. El valor por defecto es deny.

La autorización es scoped a unidad, acción, rama y base cuando esos campos se
declaran; no contiene secretos. El merge conserva el gate de aprobación humana
vigente y el chequeo del HEAD actual de `complete-approved-pr.ps1`.

## Reversibilidad y aislamiento

La unidad trabaja en su worktree y publica mediante PR. No se autoriza
force-push normal, reset destructivo ni borrado recursivo fuera del cleanup
acotado de una unidad ya mergeada. Los workflows de lectura usan
`persist-credentials: false` y CI sólo tiene `contents: read`.

## Externos y MCP

Un MCP read-only se clasifica como `NETWORK_READ`. Un MCP que escribe o ejecuta
una acción externa se clasifica como `EXTERNAL_WRITE` y necesita alcance,
autorización y evidencia de operación. Las credenciales se consumen sólo por
el mecanismo seguro autorizado; nunca se imprimen en prompts, logs, SUMMARY o
reportes. F10 puede consumir esta clasificación sin implementar MCP aquí.

## Fail-safe

Una política inválida, un scope distinto, una acción no declarada, un secreto
en la autorización o una aprobación stale bloquean el avance. Se registra el
diagnóstico sin intentar compensaciones destructivas.
