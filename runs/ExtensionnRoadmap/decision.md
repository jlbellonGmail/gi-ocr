# Decision: ExtensionnRoadmap - Extension de Roadmap Profesional

## Estado

Implementacion documental preparada para revision y QA.

## Excepcion registrada

Esta feature fue solicitada explicitamente sin numero y con worktree
`ExtensionnRoadmap`. Por eso no sigue el formato normal `NN-slug` de
`AGENTS.md`.

La excepcion se limita a esta tarea de extension del backlog. Las features
nuevas agregadas al `ROADMAP.md` vuelven al formato normal numerado
`05-...`, `06-...`, etc.

## Evidencias revisadas

- `ROADMAP.md`
- `runs/ExtensionnRoadmap/spec.md`
- `docs/tecnica/extensionn-roadmap.md`
- `docs/usuario/extensionn-roadmap.md`
- `docs/tecnica/index.md`
- `docs/usuario/index.md`

## Decisiones demostrables

- Se agregaron los items `05` a `26` al backlog actual sin modificar los
  estados existentes de `01`, `02`, `03` y `04`.
- `03-empaquetado-despliegue` queda pendiente `[ ]` e intacto para su
  circuito concurrente.
- `05-correccion-orientacion-exif` queda primero porque el pipeline actual
  debe resolver orientacion real de fotos de celular antes de seguir
  escalando captura masiva.
- Se incorporaron lineas profesionales de producto: calidad mobile,
  preprocesamiento no destructivo, regresion OCR, confianza/HITL,
  auditoria, contrato legacy, observabilidad, seguridad, accesibilidad,
  administracion de servicios, E2E mobile, supply chain, cola/DLQ,
  expediente documental, retencion, sesiones operativas, backup, mejora
  continua, release y vision cloud multitenant.
- Se creo documentacion tecnica y de usuario para explicar que esta tarea
  solo extiende el roadmap y no implementa los items nuevos.
- Se enlazaron los dos documentos en sus indices con el titulo exacto
  `Extension de Roadmap Profesional`.
- Tras el cierre de `03-empaquetado-despliegue`, la rama se rebaseo sobre
  `develop` y se preservaron el estado `[x]` de `03` y sus enlaces de
  documentacion junto con la extension `05` a `26`.

## Resultado esperado

La rama `feature/ExtensionnRoadmap` queda lista para commit/PR cuando QA
complete la verificacion manual equivalente y documente que
`Assert-FeatureContract` no aplica a este slug excepcional sin adaptar el
contrato comun.
