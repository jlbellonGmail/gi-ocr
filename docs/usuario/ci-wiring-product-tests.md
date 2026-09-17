# CI wiring product tests

## Para qué sirve

Antes de esta feature, la pestaña "Checks" de cualquier PR o push a
`develop`/`main` mostraba un único check llamado `test`, que corría los
tests del propio circuito agéntico y traía un comentario indicando que
ahí, algún día, se iban a agregar también los pasos de build/test del
stack de producto real. Ahora ves dos checks separados desde el primer
momento, y queda un lugar único y obvio para agregar el stack real
cuando exista, sin arriesgar mezclarlo con los tests del circuito.

## Qué vas a ver en "Checks" de una PR o en la pestaña Actions

Al abrir una PR (o al mirar un run de un push a `develop`/`main`) vas a
ver dos checks independientes, corriendo en paralelo:

- **`circuit-tests`**: instala Python 3.12 y corre `pytest -v` sobre
  `tests/` (los tests del propio circuito agéntico: scripts, contrato,
  workflows). Es el check que antes se llamaba `test`.
- **`product-tests`**: hace checkout del repo y corre un único paso
  placeholder que siempre termina en verde
  (`echo "product-tests: sin stack de producto definido todavia. ..."`).
  Hoy no verifica nada real porque este template todavía no tiene stack
  de producto propio.

**Los dos son obligatorios.** Ambos deben estar en verde antes de que una
PR pueda mergearse — mismo nivel de exigencia para los dos, aunque
`product-tests` hoy solo corra un placeholder (ver
`docs/tecnica/ci-wiring-product-tests.md` para el razonamiento completo
de por qué se decidió así). Si configurás branch protection real en
GitHub (ver la feature `05-operational-readiness-docs` para ese
checklist), tenés que marcar **ambos** jobs como status checks
requeridos, no solo `circuit-tests`.

## Cómo reemplazar el placeholder cuando el proyecto real defina su stack

1. Documentá primero la decisión de stack (frontend, backend, lo que
   corresponda) en `docs/tecnica/arquitectura.md` — es un paso obligado
   antes de tocar CI, no opcional.
2. Abrí `.github/workflows/ci.yml` y ubicá el job `product-tests`. Vas a
   ver un bloque de comentario grande, delimitado por líneas de `#`, que
   dice textualmente dónde va cada cosa.
3. Reemplazá por completo el step `Placeholder (sin stack definido)`
   (borralo, no lo dejes al lado) por los pasos reales de instalación y
   test de tu stack — por ejemplo `actions/setup-node@v4` + `npm ci` +
   `npm test`, o el equivalente que corresponda según lo que
   documentaste en el paso 1.
4. Dejá `actions/checkout@v4` como primer step si tu stack lo necesita
   (ya está ahí desde el placeholder).
5. No toques el job `circuit-tests`: sigue corriendo los tests del
   circuito agéntico, independientemente de qué stack de producto agregue
   el proyecto.

## Si ya tenías branch protection configurada con el nombre viejo (`test`)

Si tu proyecto (nacido de este template) ya tenía un status check
requerido llamado `test` en GitHub y adoptás esta feature, andá a
Settings → Branches en GitHub y actualizá la regla de protección de rama:
sacá `test` y agregá `circuit-tests` y `product-tests` como checks
requeridos. Si no lo hacés, GitHub va a seguir esperando un check `test`
que nunca va a llegar, y ninguna PR nueva va a poder mergearse hasta que
lo corrijas.
