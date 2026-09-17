# Auditoría final y release v2.0.0

F17 concentra la verificación final del circuito: evidencia .audit, suite
integral, gates de seguridad/supply-chain, revisión independiente y readiness
de release. La publicación sigue la secuencia develop → main → tag → GitHub
Release. No se reescriben tags históricos y el cierre de ROADMAP ocurre sólo
después del merge.

El wait de CI usa gh pr checks --watch dentro de un proceso con
timeout configurable (900 segundos por defecto) y polling de 10 segundos.
Un timeout produce BLOCKED/TEMPORAL; no es un PASS.
