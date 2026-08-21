# Extension de Roadmap Profesional - documentacion tecnica

Esta extension agrega al `ROADMAP.md` el backlog profesional `05` a `26`
para convertir gi-ocr en una herramienta documental robusta, auditable y
operable.

## Contexto

El proyecto ya resolvio el punto critico inicial: reemplazar EasyOCR por
RapidOCR/ONNX como motor OCR principal local. Tambien cerro la mejora de
precision y el endurecimiento operativo del circuito agentico. Quedaba
registrar las etapas siguientes sin mezclarlas con implementaciones
parciales ni con la feature concurrente `03-empaquetado-despliegue`.

Esta tarea no implementa los items nuevos. Solo los incorpora como backlog
accionable para que cada uno pueda iniciar luego su propio circuito
`analyst-agent -> reviewer-agent -> builder-agent -> qa-agent`.

## Decision de estructura

Los items nuevos arrancan en `05` porque:

- `01-captura-ocr-local-agil` ya esta cerrado.
- `02-mejora-precision-ocr` ya esta cerrado.
- `03-empaquetado-despliegue` existe y se deja intacto.
- `04-cierre-operativo-circuito-agentico` ya esta cerrado.

La rama y el worktree se llaman `ExtensionnRoadmap` por pedido explicito
del usuario. Esto es una excepcion documentada al formato normal
`NN-slug`.

## Lineas tecnicas agregadas

- Correccion EXIF real antes de OCR para fotos de celular.
- Control de calidad de captura mobile.
- Preprocesamiento no destructivo y trazable.
- Regresion permanente de OCR/extraccion.
- Scores, umbrales y enrutamiento a revision humana.
- Consola profesional de revision.
- Auditoria y permisos de operador.
- Contrato legacy `.DATA`/JSON versionado.
- Observabilidad operativa.
- Seguridad y privacidad de documentos.
- Accesibilidad mobile.
- Administracion de servicios/documentos por `services.ini`.
- E2E mobile real.
- Calidad CI y supply chain.
- Operacion de cola, reintentos y dead-letter.
- Expediente documental auditable.
- Politica de almacenamiento y retencion.
- Sesiones operativas de captura/revision.
- Backup, restore y archivado.
- Mejora continua desde correcciones humanas.
- Release productivo.
- Vision v2 cloud multitenant.

## Excepcion del contrato comun

`scripts/feature-contract.ps1` exige slugs `NN-slug-en-minusculas`. Por lo
tanto, `ExtensionnRoadmap` no puede pasar `Assert-FeatureContract` sin
adaptar el contrato o aceptar una verificacion manual equivalente.

La verificacion de esta feature debe comprobar manualmente:

- `runs/ExtensionnRoadmap/spec.md`;
- `runs/ExtensionnRoadmap/audit-1.md`;
- `runs/ExtensionnRoadmap/decision.md`;
- `runs/ExtensionnRoadmap/test-report-1.md`;
- `docs/tecnica/extensionn-roadmap.md`;
- `docs/usuario/extensionn-roadmap.md`;
- enlaces exactos en ambos indices;
- una entrada exacta para cada item `05` a `26`;
- ningun cambio al estado de `03-empaquetado-despliegue`.

## Riesgos

El riesgo principal es que futuras automatizaciones asuman que toda feature
tiene formato `NN-slug`. Por eso esta extension debe tratarse como una
tarea de preparacion del backlog, no como precedente para features de
producto. Las siguientes features deben volver al formato normal numerado.
