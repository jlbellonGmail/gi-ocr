# Spec: ExtensionnRoadmap - Extension de Roadmap Profesional

## Excepcion del circuito

Feature excepcional solicitada por el usuario para integrar backlog
extendido al `ROADMAP.md`. No usa formato `NN-slug`.

- Worktree requerido: `../worktrees/ExtensionnRoadmap/`
- Run dir requerido: `runs/ExtensionnRoadmap/`
- Rama requerida: `feature/ExtensionnRoadmap`
- Doc slug: `extensionn-roadmap`

Esta excepcion rompe el contrato actual: `Assert-FeatureContract` usa
`Get-FeatureInfo`, que exige `NN-slug`. Por lo tanto, QA debe documentar
que el contrato no aplica tal cual, salvo que se adapte explicitamente o
se acepte esta excepcion con verificacion manual equivalente.

## Objetivo

Agregar al `ROADMAP.md` actual un bloque profesional de backlog desde `05`
hasta `26`, sin perder puntos, sin modificar `01`, `02`, `03` ni `04`, y
dejando el proyecto listo para iniciar las nuevas features por circuito
agentico normal.

## Alcance

- Agregar items `05` a `26` al backlog.
- Mantener `01`, `02` y `04` cerrados como estan.
- No tocar el contenido ni estado de `03-empaquetado-despliegue`.
- Crear documentacion tecnica y de usuario de esta extension.
- Crear `decision.md`, `audit-N.md` y `test-report-N.md`.
- No implementar ninguna feature del backlog nuevo en esta tarea.

## Bloque a agregar al ROADMAP.md

- [ ] 05-correccion-orientacion-exif — Aplicar correctamente EXIF
  Orientation antes de OCR para fotos reales de celular. Debe cubrir
  orientaciones 90/180/270 y espejadas, tests sinteticos con EXIF,
  reemplazo o subordinacion de la heuristica actual por lectura confiable
  del tag, y evidencia de que RapidOCR recibe la imagen en orientacion
  correcta.
- [ ] 06-calidad-captura-mobile — Agregar control de calidad previo al OCR
  para fotos tomadas rapido: blur, baja resolucion, reflejos, sombras,
  documento cortado, mala perspectiva, mala iluminacion o encuadre
  insuficiente. Debe definir cuando procesar, cuando advertir y cuando
  pedir nueva foto.
- [ ] 07-preprocesamiento-documental-no-destructivo — Formalizar el
  pipeline de imagen preservando siempre el original y generando versiones
  preparadas trazables. Debe registrar transformaciones aplicadas: EXIF,
  deskew, perspectiva, escala, contraste y normalizacion, evitando que una
  mejora visual destruya ROI o datos utiles.
- [ ] 08-regresion-dataset-ocr — Crear suite permanente de regresion
  OCR/extraccion con fixtures anonimos o sinteticos controlados y expected
  outputs por proveedor, documento y campo. Debe funcionar como gate
  futuro para no romper precision ya validada.
- [ ] 09-confianza-y-enrutamiento-hitl — Definir scores y umbrales por
  campo: autoaceptar alta confianza, enviar baja confianza a revision
  humana y bloquear falsos positivos sensibles. Debe registrar confianza
  OCR, confianza de extraccion, validacion semantica y decision final.
- [ ] 10-consola-revision-humana-profesional — Completar la UI mobile de
  revision: imagen, texto OCR, candidatos, campos validados, rechazados y
  no encontrados, edicion manual, motivo de correccion/rechazo y
  confirmacion final antes de exportar.
- [ ] 11-auditoria-permisos-operador — Registrar quien corrigio que, valor
  original, valor final, fecha, motivo y accion. Preparar permisos minimos
  por rol operador/revisor/admin si el producto deja de ser monousuario
  local.
- [ ] 12-contrato-integracion-legacy-v2 — Versionar formalmente `.DATA` +
  JSON confirmado: encoding, separador, orden de campos, nombres de
  archivo, idempotencia, duplicados, reintentos, estados `ready/failed` y
  reconciliacion con el sistema externo.
- [ ] 13-observabilidad-operacion — Agregar logs estructurados, metricas y
  trazabilidad por job/documento: tiempos OCR, estado de cola, errores por
  etapa, campos aceptados/rechazados/no encontrados, health/readiness y
  runbook operativo.
- [ ] 14-seguridad-privacidad-documentos — Endurecer uploads y
  almacenamiento: extension, MIME, firma de archivo, tamaño maximo, nombres
  aleatorios, permisos, retencion, anonimizacion y redaccion de datos
  sensibles en logs.
- [ ] 15-accesibilidad-ux-mobile — Alinear frontend mobile con buenas
  practicas de accesibilidad: errores claros, estados accesibles,
  contraste, reflow, targets tactiles, confirmaciones, foco visible y
  reduccion de entrada repetida.
- [ ] 16-administracion-servicios-documentos — Profesionalizar altas de
  proveedores/documentos en `services.ini`: validacion, documentacion
  automatica, campos requeridos/opcionales, reglas semanticas, ejemplos y
  tests contractuales.
- [ ] 17-pruebas-e2e-mobile-real — Agregar E2E con Playwright/perfiles
  mobile para upload, captura, polling de jobs, revision humana y
  confirmacion. Debe contemplar fixtures publicos y saltos explicitos para
  muestras privadas.
- [ ] 18-calidad-ci-supply-chain — Incorporar lint, formato, type checks,
  dependencias fijadas, auditoria basica de vulnerabilidades y CI
  reproducible, sin romper el baseline actual.
- [ ] 19-operacion-cola-reintentos-dlq — Robustecer cola/jobs:
  persistencia, reintentos configurables, dead-letter queue, backpressure,
  reanudacion tras reinicio y diagnostico de jobs trabados.
- [ ] 20-expediente-auditoria-documental — Crear un expediente unico por
  documento que agrupe foto original, imagen normalizada, texto OCR bruto,
  candidatos, campos validados/rechazados/no encontrados, JSON confirmado,
  `.DATA`, timestamps, operador y decisiones humanas. Debe incluir
  `document_id`, checksums/hash, manifest auditable y trazabilidad
  completa.
- [ ] 21-politica-almacenamiento-retencion — Definir donde vive cada dato y
  por cuanto tiempo: originales, imagenes preparadas, JSON, `.DATA`, logs,
  auditoria y temporales. Debe soportar modo local seguro, limpieza
  automatica, retencion configurable, exportacion para auditoria y borrado
  controlado.
- [ ] 22-sesion-captura-operador — Modelar apertura/cierre de sesion
  operativa: sesion de carga/revision, documentos asociados, operador,
  inicio, cierre, estado final, errores y resumen. Debe permitir saber que
  lote proceso cada operador, que quedo confirmado, pendiente o exportado.
- [ ] 23-backup-retencion-archivado — Implementar politica de backup,
  restore probado, archivado y limpieza. Debe cubrir expedientes, salidas
  legacy, JSON, configuracion critica y evidencia de auditoria, sin
  respaldar basura temporal ni datos fuera de politica.
- [ ] 24-mejora-continua-datos — Convertir correcciones humanas en mejora
  operativa: casos nuevos para dataset, reporte de drift, ranking de campos
  problematicos, proveedores con mas fallos y propuestas de ajuste de
  plantillas/reglas.
- [ ] 25-release-versionado-productivo — Formalizar releases: SemVer,
  changelog, PR `develop` -> `main`, tags humanos, artefactos esperados,
  checklist, rollback y separacion clara entre merge de feature y release
  productivo.
- [ ] 26-version-cloud-multitenant — Diseñar una version v2
  SaaS/multitenant para clientes pagos en la nube. Debe definir
  aislamiento por tenant, autenticacion, roles, billing, limites de uso,
  almacenamiento seguro por cliente, cifrado, auditoria, backups,
  monitoreo, escalabilidad de OCR/jobs, costos por documento, cumplimiento
  legal y migracion desde modo local/on-premise. No bloquea el MVP local.

## Criterios de aceptacion

- `ROADMAP.md` conserva intactos `01`, `02`, `03` y `04`.
- `ROADMAP.md` contiene exactamente una entrada para cada item `05` a
  `26`.
- Todos los nuevos items quedan en estado `[ ]`.
- No se duplica ningun numero ni slug.
- Se crean `docs/tecnica/extensionn-roadmap.md` y
  `docs/usuario/extensionn-roadmap.md`.
- Los indices incluyen exactamente:
  - `docs/tecnica/index.md`: `- [Extension de Roadmap Profesional](extensionn-roadmap.md)`
  - `docs/usuario/index.md`: `- [Extension de Roadmap Profesional](extensionn-roadmap.md)`
- Se crea `runs/ExtensionnRoadmap/decision.md` explicando la excepcion de
  slug no estandar.
- Reviewer produce `runs/ExtensionnRoadmap/audit-1.md`.
- QA produce `runs/ExtensionnRoadmap/test-report-1.md`.
- QA ejecuta `git diff --check`.
- QA documenta que `Assert-FeatureContract -Slug ExtensionnRoadmap` no
  aplica sin adaptacion, o demuestra la adaptacion usada.
- No se usa `skip-worktree` para ocultar cambios de esta feature.

## Casos borde

- Si `03-empaquetado-despliegue` cambia por otra PR concurrente, esta
  feature debe rebasear y preservar su estado final sin tocarlo.
- Si ya existe algun item `05` a `26`, builder debe detenerse y reconciliar
  para evitar duplicados.
- Si los indices ya contienen `extensionn-roadmap.md`, no deben agregarse
  enlaces duplicados.
- Si scripts de ready/close fallan por slug no estandar, no se debe
  falsear PASS; debe quedar explicado en `decision.md` y
  `test-report-1.md`.

## Riesgos

- La excepcion puede romper automatizaciones que asumen `NN-slug`.
- Un roadmap largo puede volverse ambiguo si las descripciones son pobres.
- `26-version-cloud-multitenant` puede distraer del MVP local; debe quedar
  marcado como vision v2, no bloqueante.

## Fuera de alcance

- Implementar OCR, EXIF, UI, seguridad, cloud o despliegue.
- Cambiar el contrato agentico general salvo adaptacion minima y
  documentada para esta excepcion.
- Marcar nuevos items como `[-]` o `[x]`.
