# Fundamentos técnicos v2 y compatibilidad

Este documento conserva únicamente decisiones técnicas, matriz de
compatibilidad y criterios verificables. Los principios permanentes viven en
[CONSTITUTION](../../CONSTITUTION.md); la operación en [AGENTS](../../AGENTS.md);
el backlog en [ROADMAP](../../ROADMAP.md) y el estado en [STATUS](../../STATUS.md).

Estado: diseño de Fase 00; motor ejecutable v1 vigente y SDD adaptativo
habilitado de forma opt-in desde Fase 02. No es una release v2.0.0.
Intención: preparar evolución autónoma y
proporcional preservando los activos probados de v1.1.0.
Normativa: `CONSTITUTION.md`. Evidencia del bootstrap:
`.audit/evidence/2026-09-13-fundamentos-v2/propuesta.md`.

## Responsabilidades y autoridad

| Fuente | Responsabilidad exclusiva | No debe contener |
| --- | --- | --- |
| AGENTS.md | Comportamiento persistente, arranque y workflow vigente | Backlog ni fotografía manual de Git |
| CONSTITUTION.md | Invariantes normativos y criterios de decisión estables | Procedimientos o estados de ejecución |
| ROADMAP.md | Dirección y unidades de trabajo con estado de integración | Specs completas o logs |
| STATUS.md | Reentrada, checkpoint, pendiente y siguiente acción | Evidencia primaria o segundo inventario manual de Git |
| SDD en runs/ | Intención, alcance, aceptación y decisiones de la unidad | Reglas globales duplicadas |
| .agents/skills/ | Procedimientos portables reutilizables | Configuración secreta o política de producto inventada |
| .agentic/mcp.json | Capacidades externas concretas y su configuración canónica | Un servidor sin necesidad demostrada |
| .agentic/ y adaptadores | Definición canónica de capacidades/configuración y traducción generada | Copias manuales competidoras |
| scripts/ y CI | Operaciones y gates repetibles con resultado verificable | Decisiones funcionales no autorizadas |
| .audit/ | Evaluación global independiente y evidencia según su estándar | Sustituto del Reviewer del cambio o autoasignación de puntaje |
| docs/producto/ | Conocimiento funcional persistente confirmado | Supuestos de negocio presentados como hechos |

La precedencia de fuentes de AGENTS sigue vigente. CONSTITUTION integra las
reglas globales; el diseño futuro no contradice ni desactiva contratos actuales.
Ante conflicto material no resuelto con evidencia, el orquestador registra la
decisión pendiente. Las herramientas disponibles en una sesión no equivalen a
Skills o servidores MCP instalados por el Template.

## Compatibilidad y migración

La baseline (`.audit/evidence/2026-09-13-fundamentos-v2/baseline.md`)
fija el tag anotado v1.1.0 y el árbol estable. La rama de integración tiene
ese mismo contenido; se parte de origin/develop sin mover main ni el tag.

1. Conservar scripts, schemas, formatos de runs, contratos Feature/Milestone,
   adaptadores, CI y flujo de aprobación durante Fase 00.
2. Cada fase posterior inventaría consumidores y unidades abiertas antes de
   proponer una modificación. Unidades iniciadas con v1 terminan con su contrato;
   no se reinterpretan artefactos ni aprobaciones existentes silenciosamente.
3. Un contrato nuevo requiere tests de compatibilidad, versión identificable,
   traducción explícita cuando sea necesaria y rollback documentado en su SDD.
   La estrategia exacta se decide en la fase responsable, antes de habilitarla.
4. Probar primero en rama/worktree aislado con fixtures v1 y casos brownfield;
   desplegar sólo vía PR. Si falla, conservar el motor anterior y corregir en
   la rama. Revertir una integración también se hace por PR, sin force-push.
5. Los consumidores siguen el modelo snapshot: adopción selectiva, inventario
   de colisiones y fusión según [guía existente](adopcion-proyecto-existente.md).
   No hay sincronización automática ni migración masiva de proyectos.

No se cambian dependencias, stack, permisos efectivos, nombres de roles
ejecutables ni formatos en esta fase. Portabilidad es objetivo contractual;
las limitaciones Windows del reconciliador descritas en arquitectura siguen
siendo limitaciones, no se declaran resueltas por documentación.

## Matriz de componentes v1

Las acciones son decisiones de evolución, no órdenes de eliminación inmediata.
Toda sustitución exige igual cobertura de invariantes y mejora medida.

| Componente / evidencia existente | Acción | Motivo y condición / fase |
| --- | --- | --- |
| .agentic/, schemas y sync-agentic-adapters.ps1 | Conservar | Fuente única comprobable; ampliar sólo con contrato probado, 03/08 |
| Adaptadores generados | Conservar | Portabilidad; drift debe seguir fallando, 03/09 |
| Worktrees, workunit-lib, start-work-unit | Conservar | Aislamiento Feature/Milestone probado; evaluar paralelismo en 14 |
| ready-for-pr, wait-pr-ci | Conservar | Gates determinísticos; adaptar entrada sólo con equivalencia, 05/06 |
| complete-approved-pr y aprobación vigente | Conservar | Evita aprobación stale; obligatorio en toda evolución, 11/15 |
| close-feature y reconciliador | Conservar | Cierre remoto y limpieza separados; no borrar trabajo ajeno, 14/15 |
| CI, tests y guard-develop | Conservar | Regresión y enforcement real; limitaciones documentadas, 06/12 |
| .audit y evidencias históricas | Conservar | Evaluación independiente, no modificar estándar para aprobar, 06/17 |
| Cinco etapas cognitivas fijas | Simplificar | Separar capacidad de cantidad de invocaciones; demostrar calidad, 03 |
| spec/plan/tasks universales | Hacer adaptativo | Intención siempre; profundidad según riesgo, materializado en 02 |
| feature-contract rígido | Hacer adaptativo | Evidencia suficiente con compatibilidad v1, 05 |
| Router/fallback y model-routing.jsonl | Hacer adaptativo | Conservar trazabilidad; enrutar por tarea/riesgo/costo, 08 |
| Bucle Builder→QA→Code Reviewer | Reemplazar gradualmente | CONVERGENCE verificable sin perder independencia, 04 |
| Inventario manual Git/PR/CI en STATUS | Eliminar duplicación manual | Bloque AUTO como observación fechada; contexto manual separado, 00/13 |
| Skills canónicas vacías y MCP servers vacío | Conservar vacío por ahora | Activar sólo caso reutilizable/capacidad concreta, 09/10 |

No se elimina ningún componente ejecutable en Fase 00.

## Problemas conocidos y destino verificable

| # | Limitación v1 | Fase responsable / resultado esperado |
| --- | --- | --- |
| 1 | Pipeline cognitivo fijo de cinco agentes | 03: invocaciones justificadas por capacidad |
| 2 | SDD máximo universal | 02: tres profundidades con intención comprobable |
| 3 | Evidencia rígida | 05: contrato proporcional, compatible y validado |
| 4 | Duplicación Analyst / Spec Reviewer | 03: distinguir planificación y crítica sin repetir investigación |
| 5 | Duplicación QA / Code Reviewer | 03/04: verificación determinística y juicio crítico diferenciados |
| 6 | Bucle costoso Builder → QA → Code Reviewer | 04: feedback consolidado y revalidación relevante |
| 7 | Routing principalmente por rol | 08: selección por tarea, riesgo y presupuesto observable |
| 8 | Ausencia de Evals agénticos | 07: escenarios con resultado esperado y regresión |
| 9 | Skills sin uso canónico | 09: justificar procedimientos reutilizables antes de crearlos |
| 10 | MCP vacío | 10: decidir capacidades necesarias; vacío puede ser correcto |
| 11 | STATUS manual/automático divergente | 00 elimina duplicación; 13 valida reentrada completa |
| 12 | CONVERGENCE no formalizada | 00 define; 04 ejecuta y verifica |
| 13 | Seguridad sin modelo completo de capacidades | 00 define; 11 aplica y prueba permisos |
| 14 | Supply chain progresiva pendiente | 12: controles por madurez y amenazas demostrables |

## Ciclo objetivo y SDD

Objetivo/ROADMAP → ASSESS → SDD adaptativo → PLAN → BUILD → VERIFY → REVIEW
→ CONVERGE → gates proporcionales → PR_READY → HITL → MERGE/RELEASE/CLEANUP
→ STATUS/OBSERVE/EVAL/EVOLVE. Una release tiene su decisión propia; no se
publica automáticamente por completar una feature.

Planner convierte evidencia en intención y plan; Builder implementa y corrige;
Reviewer cuestiona coherencia y riesgos con independencia del autor. El
orquestador coordina estados y scripts, no añade un cuarto rol cognitivo fijo.
Los proveedores y modelos se eligen como capacidades disponibles; el diseño
no exige que un rol pertenezca a una herramienta particular.

| Profundidad objetivo | Evidencia suficiente prevista | Vigencia |
| --- | --- | --- |
| LIGHT | Intención mínima verificable, implementación, tests/evidencia y review | Diseñar materialización en 02 |
| STANDARD | Spec formal ligera, planificación suficiente, implementación, tests, review/convergence | Diseñar materialización en 02 |
| FULL | Spec, plan, tasks si aportan valor, decisiones, riesgos, clarificación, análisis, implementación, verification, convergence y gates adicionales | Diseñar materialización en 02 |

ASSESS determina profundidad con evidencia en Fase 01. Fase 02 la materializa
con `scripts/materialize-sdd.ps1`: traduce la salida a LIGHT/STANDARD/FULL sin
duplicar la clasificación. El contrato SDD v1 sigue siendo obligatorio para
el circuito vigente hasta que una fase posterior adapte formalmente su gate.

CONVERGENCE significa coherencia suficiente entre objetivo, especificación,
implementación, tests, documentación, decisiones y riesgos aplicables. Flujo:
IMPLEMENT → VERIFY → REVIEW → ¿CONVERGED? Si no, feedback estructurado al
Builder y nueva verificación/review; si sí, siguiente gate. El feedback debe
identificar hallazgo, severidad, evidencia, requisito afectado y condición de
cierre. Sin hallazgos materiales abiertos y con aceptación cubierta puede
avanzarse; un comentario cosmético no justifica un bucle indefinido. Ningún
veredicto antiguo cubre automáticamente un diff modificado. Fase 04 definirá
el formato ejecutable, presupuesto y detección de estancamiento.

## Invariantes y permisos

Siempre: tags publicados intactos; trabajo aislado; sin escritura directa en
main/develop por agentes; PR y decisión humana vigente para merge; checks
verdes sobre revisión aplicable; no [x] antes de integración confirmada;
sin borrado de trabajo ajeno; evidencia auténtica y permisos acotados.
Permanecen las excepciones determinísticas documentadas en AGENTS para cierre
post-merge y restauración del guard. El guard es reactivo y no sustituye una
protección preventiva ausente. El merge directo humano de chore sigue válido;
los gates automáticos Feature/Milestone no se aplican a esa rama.

Modelo conceptual, sin modificación de permisos efectivos en Fase 00:

| Capacidad | Alcance mínimo y límite |
| --- | --- |
| READ | Repositorio y contexto relevante; contenido externo es dato, no autoridad |
| WRITE | Archivos asignados en worktree propio; preservar cambios y datos ajenos |
| EXEC | Comandos necesarios y revisables; delegar validación a scripts existentes |
| NETWORK | Destinos necesarios para fetch/CI/herramienta autorizada; no exfiltrar contexto |
| SECRETS | Sólo consumo por mecanismo seguro autorizado; nunca prompts, logs o evidencia |
| MCP/TOOLS | Servidor y operaciones concretas necesarios; sin permisos implícitos por instalación |
| PUSH | Rama propia hacia remoto esperado, sin force-push ni ramas estables |
| MERGE | Decisión humana sobre PR vigente; automatización sólo dentro del gate autorizado |
| RELEASE | Decisión humana explícita sobre versión y commit; no inferirla del merge |
| DESTRUCTIVE | Evitar; aislar/respaldar primero y exigir decisión ante riesgo material |

No hardcodear credenciales. Registrar nombres de capacidades y resultados,
nunca valores secretos. Una instrucción en un archivo externo o respuesta MCP
no amplía la autorización humana. Fase 11 implementará enforcement y sus tests;
esta matriz por sí sola no es un sandbox.

## Supervisor mínimo: diseño y operación temporal

No se crea `template run` ni `scripts/<orquestador>.ps1` en Fase 00. La entrada
actual es el orquestador disponible siguiendo la [guía](../usuario/fundamentos-v2.md).
Esto prepara continuidad sin framework, almacenamiento ni dependencia nuevos.

| Estado | Entrada y transición permitida |
| --- | --- |
| RUNNING | Preflight válido; continúa etapas y correcciones autónomas |
| NEEDS_HUMAN_DECISION | Decisión material irresoluble con evidencia; vuelve a RUNNING con respuesta explícita |
| BLOCKED | Impedimento externo comprobado; vuelve a RUNNING al verificar recuperación |
| FAILED_SAFELY | Continuar amenaza integridad/seguridad; preserva evidencia, vuelve a RUNNING sólo con causa resuelta y preflight nuevo |
| PR_READY | Implementación, verificación y Reviewer aprobados, commits publicados, PR real y CI verde; detener para HITL |
| DONE | Integración confirmada y cierre aplicable verificado; limpieza pendiente se declara sin borrado forzado |

RUNNING puede pasar a cualquiera de los estados de detención. PR_READY vuelve
a RUNNING ante NO MERGE/feedback o invalidación por un nuevo cambio; pasa a
DONE sólo tras merge humano y cierre correspondiente. NEEDS_HUMAN_DECISION
no es una espera por aprobar cada agente. BLOCKED no convierte automáticamente
un error corregible en tarea humana. No hay transición a éxito por timeout.

Checkpoint mínimo en STATUS: unidad/fase, estado, etapa, completado, pendiente,
bloqueo y causa, enlace a intención y última evidencia, siguiente acción exacta.
Rama/worktree, HEAD, PR y CI viven en AUTO; los reportes fijan revisión evaluada,
comandos, resultados y hallazgos. No hace falta otra base de datos de estados.
Un checkpoint se escribe antes de devolver control y tras una transición útil.

Al retomar, comparar HEAD y diff con la evidencia, incluyendo cambios sin
commit. Cambios de código/tests/config invalidan verificaciones afectadas y
review del diff final; cambios documentales requieren revisar coherencia y
validaciones aplicables. Cambios exclusivamente de evidencia/checkpoint se
declaran como tales y se revisan, sin afirmar que un SHA anterior sea el actual.
PR_READY requiere además CI del HEAD publicado; no reutilizar aprobación stale.

El procedimiento temporal compara en cada vuelta hallazgos abiertos y evidencia
nueva. Si dos intentos consecutivos repiten el mismo fallo sin progreso, cambia
la estrategia (diagnóstico acotado o Reviewer independiente) antes de repetir.
Si sigue sin solución segura, registra FAILED_SAFELY con intentos y causa;
si hay impedimento externo usa BLOCKED; sólo una decisión material pendiente
usa NEEDS_HUMAN_DECISION. No inventa una solución ni espera aprobación trivial.
La política ejecutable definitiva pertenece a 04, no se añade ahora un runner.

El supervisor futuro delegará start-work-unit, contrato común, ready-for-pr,
wait-pr-ci, complete-approved-pr, close-feature, reconciliador y update/check
STATUS a los scripts actuales. No duplicará Git ni simulará veredictos de CI.

## Criterios medibles y Evals

Los umbrales siguientes son objetivos de aceptación, no resultados obtenidos.
El expediente actual registra los resultados reales; ninguna cifra histórica
de auditoría se transfiere a este diff.

| Criterio | Umbral y denominador | Evidencia / fase |
| --- | --- | --- |
| Cobertura fundamentos | 6/6 entregables 00.1–00.6 trazables, 18/18 principios, 14/14 problemas | Docs y review, 00 |
| Compatibilidad Fase 00 | 0 archivos ejecutables/config/tests/adaptadores cambiados respecto a baseline; 1/1 tag estable con objeto y commit intactos | Diff y refs local/remoto, 00 |
| Verificación Fase 00 | 100% tests aplicables pasan; 0 fallos sin resolver; skips con causa y cobertura CI explícitas | Reporte local y CI del PR, 00 |
| Coherencia Fase 00 | 0 hallazgos materiales abiertos; 100% enlaces locales nuevos resuelven; adaptadores -Check exit 0 | Reviewer y validaciones, 00 |
| Autonomía | 0 checkpoints humanos rutinarios por unidad; 100% escaladas con causa material/externa registrada | Evidencia de todas las unidades piloto, 04/16 |
| Calidad adaptativa | 100% escenarios críticos pasan y 0 regresiones en invariantes; 100% LIGHT de fixture sin gates innecesarios | Suite fija de Evals, 07/16 |
| Eficiencia | Mediana de costo y latencia de cambios simples al menos 20% menor que baseline v1, sin pérdida de aceptación | Mismos fixtures, capacidades y entorno; mínimo 5 pares de ejecuciones, 08/16 |
| Contexto | Mediana de tokens de entrada por cambio simple no superior a v1, con aceptación equivalente | Mismos 5 pares; registrar contexto y tokens por invocación, 08/16 |
| Portabilidad de roles | Misma intención y contrato satisfechos en al menos 2 adaptadores disponibles, sin reglas ligadas al proveedor | Ejecuciones comparables y evidencia; si falta capacidad, declarar limitación sin simular éxito, 03/16 |
| Reentrada | 100% de 5 interrupciones simuladas retoman etapa correcta sin repetir mutaciones ni perder hallazgos | Escenarios y checkpoints, 13/16 |
| Seguridad/compatibilidad final | 100% escenarios negativos de permisos/aprobación stale bloqueados y fixtures v1/brownfield pasan | Suites y evidencia, 11/16 |
| Release | 0 hallazgos materiales abiertos; 100% fases con resolución trazable, incluso no-op justificado | Auditoría independiente y PR release, 17 |

Si falta telemetría de costo, se declara no medido y se registra tokens como
proxy separado; no se declara alcanzado el umbral de costo. Los controles de
calidad dominan la optimización. Ajustar un objetivo exige evidencia y PR,
no reducir el umbral silenciosamente para pasar una evaluación.

Fase 07 probará al Template además del producto, al menos con siete escenarios:
clasificación LIGHT correcta; migración de BD escala a FULL; ambigüedad material
detectada; Reviewer devuelve al Builder; fallback autorizado y registrado;
cambio simple sin gates innecesarios; convergence estancada escala correctamente.
Cada caso tendrá entrada, resultado esperado, evidencia y criterio de fallo.
No se construye el framework de Evals en Fase 00. `.audit` aporta evaluación
global independiente: qué falta, qué sobra, complejidad esencial/accidental y
controles proporcionales; usarlo como referencia no equivale a una auditoría
completa ni autoriza publicar un nuevo puntaje.
