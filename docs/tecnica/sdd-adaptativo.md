# SDD adaptativo

Fase 02 agrega `scripts/materialize-sdd.ps1`. El script consume la salida
determinista de ASSESS y materializa el perfil SDD correspondiente, sin volver
a clasificar las rutas ni invocar agentes, modelos o proveedores.

## Contrato

`-AssessmentPath` acepta el JSON de ASSESS o un JSONL y usa su última línea.
La entrada debe declarar `assessment: ASSESS`, `deterministic: true`, un
`depth` válido y archivos evaluados. `-Objective` es obligatorio. La salida
JSON contiene la profundidad recibida, pasos, artefactos, gates, objetivo y la
ruta de evidencia fuente; opcionalmente se persiste con `-OutputPath` y se
registra con `-EvidencePath`.

| Profundidad | Secuencia | Evidencia mínima |
| --- | --- | --- |
| LIGHT | objetivo → mini-spec → build → tests → review | intención, mini-spec, tests y review |
| STANDARD | objetivo → planificación ligera → spec → plan/tasks proporcionales → build → tests → review | intención, spec, plan/tasks proporcionales, tests y review |
| FULL | objetivo → planificación completa → spec/plan/tasks → validaciones → build → tests → review → gates | paquete formal, decisión, validaciones, tests, review y gates aplicables |

El perfil es una instrucción ejecutable y auditable para el circuito; no
reemplaza todavía `feature-contract.ps1`. Por compatibilidad, una Feature v1
que usa el circuito vigente continúa generando y validando sus artefactos
completos hasta la fase que adapte formalmente ese contrato.

## Límites

La clasificación pertenece exclusivamente a ASSESS. Una evidencia inválida,
vacía o no determinista falla cerradamente. No se agregan roles, estados,
permisos, dependencias ni gates nuevos; FULL solo declara las validaciones
proporcionales que el consumidor ya deba ejecutar.
