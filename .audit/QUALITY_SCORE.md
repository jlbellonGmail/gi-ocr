# QUALITY_SCORE.md

# Quality Score Standard

**Versión:** 1.1
**Estado:** Activo
**Puntuación máxima:** 100 puntos

---

# 1. Propósito

Este documento define el sistema oficial de puntuación utilizado para evaluar la calidad de un repositorio.

Su objetivo es proporcionar una evaluación:

* objetiva;
* matemática;
* reproducible;
* trazable;
* basada en evidencia;
* comparable entre auditorías;
* independiente del modelo o agente que realiza la evaluación.

La puntuación no representa una opinión general sobre el proyecto.

Representa el grado de cumplimiento verificable de los criterios definidos por este estándar y por el perfil de auditoría aplicable.

---

# 2. Principio fundamental

La calidad no se presume.

Debe demostrarse mediante evidencia.

La existencia de documentación que afirme que una capacidad está implementada no constituye, por sí sola, evidencia suficiente de funcionamiento.

Cuando corresponda, debe distinguirse entre:

1. DOCUMENTADO
2. PRESENTE
3. IMPLEMENTADO
4. AUTOMATIZADO
5. EJECUTADO
6. VERIFICADO

El nivel máximo de puntuación de un criterio requiere evidencia proporcional a aquello que se está evaluando.

---

# 3. Escala general

La puntuación máxima total es:

**100 puntos**

No existen:

* puntos adicionales;
* bonus;
* compensaciones superiores al máximo;
* puntuaciones mayores a 100.

La puntuación final debe redondearse a un máximo de dos decimales.

---

# 4. Áreas de evaluación

La evaluación se divide en ocho áreas.

| ID | Área                                 |  Puntos |
| -- | ------------------------------------ | ------: |
| Q1 | Conformidad con el contrato          |      12 |
| Q2 | Reutilización y limpieza             |      12 |
| Q3 | Arquitectura y mantenibilidad        |      12 |
| Q4 | Documentación y Developer Experience |      12 |
| Q5 | Calidad, pruebas y regresión         |      16 |
| Q6 | Git, CI/CD, versionado y releases    |      16 |
| Q7 | Seguridad y software supply chain    |      12 |
| Q8 | Automatización y gobernanza          |       8 |
|    | **TOTAL**                            | **100** |

---

# 5. Q1 — Conformidad con el contrato

**Máximo: 12 puntos**

Evalúa si el repositorio cumple realmente aquello que declara ser y proporcionar.

| ID   | Criterio                                                       | Máximo |
| ---- | -------------------------------------------------------------- | -----: |
| Q1.1 | Propósito y alcance claramente definidos                       |      3 |
| Q1.2 | Capacidades prometidas realmente presentes                     |      3 |
| Q1.3 | Coherencia entre documentación, configuración e implementación |      3 |
| Q1.4 | Ausencia de requisitos obligatorios incompletos                |      3 |
|      | **TOTAL Q1**                                                   | **12** |

## Q1.1 — Propósito y alcance

Debe poder determinarse claramente:

* qué resuelve el repositorio;
* qué no pretende resolver;
* para qué contexto fue diseñado;
* cuáles son sus restricciones principales.

## Q1.2 — Capacidades prometidas

Las capacidades declaradas como existentes deben encontrarse realmente implementadas o disponibles según corresponda.

## Q1.3 — Coherencia

No deben existir contradicciones importantes entre:

* documentación;
* configuración;
* código;
* automatizaciones;
* comportamiento observable.

## Q1.4 — Requisitos obligatorios

No deben existir requisitos declarados como obligatorios que estén incompletos, rotos o pendientes.

---

# 6. Q2 — Reutilización y limpieza

**Máximo: 12 puntos**

Evalúa si el repositorio puede reutilizarse de forma segura, predecible y sin dependencia innecesaria del contexto original.

| ID   | Criterio                               | Máximo |
| ---- | -------------------------------------- | -----: |
| Q2.1 | Inicialización reproducible            |      3 |
| Q2.2 | Ausencia de residuos específicos       |      3 |
| Q2.3 | Configuración y personalización claras |      3 |
| Q2.4 | Portabilidad y extensibilidad          |      3 |
|      | **TOTAL Q2**                           | **12** |

## Q2.1 — Inicialización reproducible

Debe ser posible iniciar el proyecto siguiendo únicamente las instrucciones y mecanismos oficiales del repositorio.

## Q2.2 — Residuos específicos

No deben permanecer elementos accidentales pertenecientes al proyecto original.

Ejemplos:

* nombres privados;
* rutas locales;
* usuarios;
* IDs;
* datos reales;
* credenciales;
* comentarios temporales;
* artefactos generados accidentalmente;
* configuraciones locales no justificadas.

## Q2.3 — Personalización

Los elementos que deban modificarse al reutilizar el repositorio deben estar claramente identificados.

## Q2.4 — Portabilidad

El proyecto debe evitar dependencias injustificadas de:

* máquinas concretas;
* rutas absolutas;
* configuraciones ocultas;
* conocimiento tribal;
* operaciones manuales no documentadas.

---

# 7. Q3 — Arquitectura y mantenibilidad

**Máximo: 12 puntos**

| ID   | Criterio                                            | Máximo |
| ---- | --------------------------------------------------- | -----: |
| Q3.1 | Estructura coherente                                |      3 |
| Q3.2 | Separación de responsabilidades                     |      3 |
| Q3.3 | Simplicidad y ausencia de duplicación injustificada |      3 |
| Q3.4 | Capacidad de mantenimiento y evolución              |      3 |
|      | **TOTAL Q3**                                        | **12** |

## Q3.1 — Estructura

La organización del repositorio debe ser comprensible y consistente.

## Q3.2 — Responsabilidades

Los componentes deben tener responsabilidades suficientemente claras y evitar acoplamientos innecesarios.

## Q3.3 — Simplicidad

Debe evitarse complejidad accidental.

Se consideran negativamente cuando no estén justificadas:

* duplicaciones;
* abstracciones innecesarias;
* código muerto;
* configuración repetida;
* documentación redundante;
* automatizaciones equivalentes mantenidas manualmente en varios lugares.

## Q3.4 — Evolución

El repositorio debe poder modificarse y extenderse sin introducir una carga desproporcionada de mantenimiento.

---

# 8. Q4 — Documentación y Developer Experience

**Máximo: 12 puntos**

| ID   | Criterio                              | Máximo |
| ---- | ------------------------------------- | -----: |
| Q4.1 | README funcional                      |      3 |
| Q4.2 | Instalación y bootstrap reproducibles |      3 |
| Q4.3 | Operaciones habituales documentadas   |      2 |
| Q4.4 | Convenciones de contribución          |      2 |
| Q4.5 | Ejemplos y troubleshooting            |      2 |
|      | **TOTAL Q4**                          | **12** |

## Q4.1 — README

Debe permitir comprender rápidamente el proyecto.

## Q4.2 — Instalación

Una persona nueva debe poder preparar el entorno sin depender de conocimiento no documentado.

## Q4.3 — Operaciones

Deben encontrarse documentadas las operaciones relevantes, por ejemplo:

* instalar;
* ejecutar;
* validar;
* probar;
* construir;
* liberar.

## Q4.4 — Contribución

Deben existir convenciones suficientes para modificar el repositorio de forma consistente.

## Q4.5 — Ejemplos y troubleshooting

Los problemas previsibles y operaciones no obvias deben disponer de orientación suficiente.

---

# 9. Q5 — Calidad, pruebas y regresión

**Máximo: 16 puntos**

| ID   | Criterio                                 | Máximo |
| ---- | ---------------------------------------- | -----: |
| Q5.1 | Controles automáticos de calidad         |      3 |
| Q5.2 | Estrategia de pruebas adecuada           |      3 |
| Q5.3 | Pruebas ejecutables y pasando            |      4 |
| Q5.4 | Protección frente a regresiones críticas |      3 |
| Q5.5 | Quality gates automatizados              |      3 |
|      | **TOTAL Q5**                             | **16** |

## Q5.1 — Controles automáticos

Según la tecnología pueden incluir:

* lint;
* format;
* type checking;
* análisis estático;
* validaciones estructurales;
* validaciones equivalentes.

No se exige una herramienta concreta.

## Q5.2 — Estrategia de pruebas

Debe existir una estrategia proporcional al riesgo del proyecto.

No es obligatorio utilizar todos los tipos de pruebas posibles.

Deben existir únicamente aquellos que aporten valor real.

## Q5.3 — Ejecución

Las pruebas relevantes deben poder ejecutarse de forma reproducible.

La existencia de archivos de tests que nunca se ejecutan no obtiene puntuación completa.

## Q5.4 — Regresión

Las capacidades críticas previamente validadas deben estar protegidas frente a regresiones cuando esto sea técnicamente aplicable.

## Q5.5 — Quality gates

Los cambios incorrectos deben poder ser detectados automáticamente antes de ser considerados válidos.

---

# 10. Q6 — Git, CI/CD, versionado y releases

**Máximo: 16 puntos**

| ID   | Criterio                                       | Máximo |
| ---- | ---------------------------------------------- | -----: |
| Q6.1 | Estrategia Git definida y coherente            |      3 |
| Q6.2 | Protección de ramas y controles de integración |      3 |
| Q6.3 | CI reproducible y confiable                    |      3 |
| Q6.4 | Versionado y releases                          |      3 |
| Q6.5 | Build y artefactos reproducibles               |      2 |
| Q6.6 | Compatibilidad, migraciones o rollback         |      2 |
|      | **TOTAL Q6**                                   | **16** |

## Q6.1 — Git

El flujo de trabajo debe ser coherente con el proyecto.

No se exige una estrategia Git específica.

## Q6.2 — Protección

Cuando el repositorio utilice una plataforma que permita controles de integración, deben evaluarse los mecanismos relevantes.

La documentación de una protección no equivale a verificar su configuración real.

## Q6.3 — CI

La integración continua debe ejecutar controles útiles y producir errores cuando corresponde.

Un workflow que existe pero no protege nada relevante no obtiene puntuación completa.

## Q6.4 — Versionado

Debe existir una estrategia clara y coherente cuando el tipo de proyecto requiera versiones o releases.

## Q6.5 — Reproducibilidad

Cuando existan builds o artefactos, deben ser suficientemente reproducibles.

## Q6.6 — Compatibilidad

Se evalúan únicamente los mecanismos aplicables al tipo de proyecto.

Ejemplos:

* migraciones;
* backward compatibility;
* rollback;
* estrategias de actualización.

---

# 11. Q7 — Seguridad y software supply chain

**Máximo: 12 puntos**

| ID   | Criterio                              | Máximo |
| ---- | ------------------------------------- | -----: |
| Q7.1 | Gestión de secretos                   |      3 |
| Q7.2 | Gestión de dependencias               |      2 |
| Q7.3 | Seguridad de CI/CD y automatizaciones |      2 |
| Q7.4 | Defaults seguros                      |      2 |
| Q7.5 | Supply chain y cumplimiento básico    |      3 |
|      | **TOTAL Q7**                          | **12** |

## Q7.1 — Secretos

No deben existir credenciales reales, tokens, contraseñas o claves privadas almacenadas indebidamente.

## Q7.2 — Dependencias

Debe existir un tratamiento razonable de:

* versiones;
* actualizaciones;
* vulnerabilidades;
* dependencias abandonadas;
* lockfiles cuando correspondan.

## Q7.3 — Automatizaciones

Las automatizaciones deben evitar privilegios innecesarios y dependencias externas inseguras.

## Q7.4 — Defaults seguros

La configuración inicial no debe inducir comportamientos inseguros.

## Q7.5 — Supply chain

Según la naturaleza del proyecto pueden considerarse:

* licencias;
* integridad;
* provenance;
* SBOM;
* firma;
* trazabilidad de artefactos;
* controles equivalentes.

No debe penalizarse la ausencia de mecanismos avanzados que no sean razonablemente necesarios para el proyecto.

---

# 12. Q8 — Automatización y gobernanza

**Máximo: 8 puntos**

| ID   | Criterio                              | Máximo |
| ---- | ------------------------------------- | -----: |
| Q8.1 | Fuente única de verdad                |      2 |
| Q8.2 | Responsabilidades y límites definidos |      2 |
| Q8.3 | Flujos deterministas y fail-safe      |      2 |
| Q8.4 | Trazabilidad                          |      2 |
|      | **TOTAL Q8**                          |  **8** |

## Q8.1 — Fuente única de verdad

Las reglas compartidas deben centralizarse cuando sea viable.

La duplicación manual entre herramientas debe evitarse cuando pueda provocar divergencias.

## Q8.2 — Responsabilidades

Las automatizaciones o agentes deben tener límites y responsabilidades suficientemente claros.

## Q8.3 — Fail-safe

Los flujos no deben aparentar éxito cuando una operación crítica ha fallado.

## Q8.4 — Trazabilidad

Debe existir trazabilidad proporcional al proyecto entre los elementos relevantes.

Ejemplo:

`REQUISITO → CAMBIO → VALIDACIÓN → REVIEW → INTEGRACIÓN → RELEASE`

---

# 13. Escala de puntuación por subcriterio

Cada subcriterio debe evaluarse utilizando únicamente uno de los siguientes niveles base:

| Nivel    | Porcentaje | Interpretación                                       |
| -------- | ---------: | ---------------------------------------------------- |
| COMPLETO |      100 % | Cumplimiento completo y suficientemente verificado   |
| MENOR    |       75 % | Correcto con defectos menores                        |
| PARCIAL  |       50 % | Implementación parcial o inconsistente               |
| DÉBIL    |       25 % | Presencia nominal, insuficiente o poco confiable     |
| AUSENTE  |        0 % | Ausente, roto, contradictorio o sin evidencia mínima |

La puntuación del subcriterio se calcula:

`Puntos obtenidos = Puntos máximos × porcentaje`

Ejemplo:

Criterio máximo:

`3 puntos`

Resultado:

`PARCIAL = 50 %`

Puntuación:

`3 × 0,50 = 1,50`

---

# 14. Uso excepcional de puntuaciones intermedias

Para reducir subjetividad, deben utilizarse preferentemente los cinco niveles definidos anteriormente.

Sólo se permite una puntuación diferente cuando exista una medición objetiva que la justifique.

Ejemplo válido:

10 controles obligatorios.

9 pasan.

1 falla.

Puede justificarse:

`90 %`

Ejemplo inválido:

“Parece bastante bueno, asigno 87 %”.

Toda puntuación intermedia debe explicar matemáticamente su origen.

---

# 15. Evidencia y puntuación máxima

Un criterio no puede obtener puntuación completa si requiere verificación ejecutable y dicha verificación no fue realizada pudiendo razonablemente realizarse.

Debe distinguirse:

### Evidencia documental

Demuestra que algo está definido.

### Evidencia estructural

Demuestra que algo existe.

### Evidencia ejecutable

Demuestra que algo puede ejecutarse.

### Evidencia de resultado

Demuestra que su ejecución produjo el resultado esperado.

La calidad de la evidencia debe ser proporcional al criterio.

---

# 16. NO VERIFICADO

`NO VERIFICADO` no significa automáticamente `FAIL`.

Significa que el auditor no dispone de evidencia suficiente para confirmar el resultado.

Cuando la falta de verificación impida demostrar cumplimiento completo:

el criterio no podrá recibir el 100 %.

La puntuación exacta dependerá de la evidencia restante.

No debe asignarse automáticamente 0 si existe evidencia parcial razonable.

Si un elemento `NO VERIFICADO` provoca una pérdida de puntuación porque la
verificación es necesaria para demostrar cumplimiento, debe reflejarse en el
criterio correspondiente.

No debe clasificarse simultáneamente como `SUGGESTION` si está reduciendo puntos
o impidiendo alcanzar 100/100.

---

# 17. Criterios N/A

Un criterio puede declararse:

`N/A`

únicamente cuando sea objetivamente inaplicable a la naturaleza del proyecto.

No puede utilizarse N/A porque:

* la capacidad no existe;
* implementar el requisito sea difícil;
* se desee evitar una penalización;
* todavía no se haya hecho;
* el auditor no pueda verificarlo.

Cada N/A debe tener una justificación explícita.

---

# 18. Normalización por N/A

Cuando existan criterios legítimamente N/A:

se calcula primero la puntuación bruta sobre los puntos aplicables.

Después:

`Puntuación normalizada = puntos obtenidos / puntos aplicables × 100`

Ejemplo:

Puntos aplicables:

`98`

Puntos obtenidos:

`96`

Resultado:

`96 / 98 × 100 = 97,96`

Debe mostrarse:

* puntuación bruta;
* puntos aplicables;
* puntuación normalizada.

---

# 19. Regla contra doble penalización

Una misma causa raíz no debe descontar puntos múltiples veces de forma artificial.

Ejemplo:

Un script central roto provoca:

* fallo del build;
* fallo de CI;
* imposibilidad de ejecutar tests.

Debe identificarse la causa raíz.

Puede afectar varios criterios porque el impacto es real, pero el auditor debe evitar aplicar penalizaciones independientes completas como si fueran tres defectos no relacionados.

El informe debe indicar:

`CAUSA RAÍZ COMPARTIDA`

cuando corresponda.

---

# 20. Hallazgos

Los hallazgos se clasifican por severidad.

## BLOCKER

Defecto que impide utilizar el proyecto de forma razonablemente segura o funcional.

Ejemplos:

* pérdida potencial de datos;
* secretos reales expuestos;
* bootstrap imposible;
* operación destructiva insegura;
* mecanismo fundamental completamente roto.

## CRITICAL

Defecto grave que impide considerar el proyecto como referencia profesional.

Ejemplos:

* tests críticos fallando;
* CI principal inutilizable;
* controles esenciales fácilmente evitables;
* release fundamental no reproducible;
* comportamiento crítico contradictorio.

## MAJOR

Defecto significativo de:

* calidad;
* arquitectura;
* mantenibilidad;
* documentación;
* seguridad;
* automatización;
* gobernanza.

## MINOR

Defecto real de bajo impacto.

## SUGGESTION

Mejora opcional.

Una `SUGGESTION` no resta puntos.

Una `SUGGESTION`:

- nunca resta puntos;
- nunca activa un Quality Gate;
- nunca puede utilizarse como justificación de una pérdida de puntuación;
- nunca puede formar parte del camino obligatorio a 100/100;
- nunca puede impedir obtener 100/100.

Si una ausencia o problema reduce puntuación, entonces no puede clasificarse como
`SUGGESTION`; debe clasificarse con una severidad puntuable adecuada.

---

# 21. Relación entre hallazgos y puntuación

Todo descuento debe poder relacionarse con al menos un criterio de la rúbrica.

No deben descontarse puntos únicamente porque exista un hallazgo si éste no afecta ningún criterio puntuable.

A su vez, todo criterio que pierda puntos debe indicar qué evidencia o hallazgo explica la pérdida.

Debe existir trazabilidad:

`CRITERIO → EVIDENCIA → HALLAZGO → PUNTOS`

---

# 22. Quality Gates globales

La puntuación matemática puede quedar limitada por condiciones críticas.

Estos límites no sustituyen el score bruto.

Siempre deben mostrarse ambos.

---

## Gate G1 — BLOCKER

Si existe al menos un BLOCKER abierto:

**la puntuación final máxima es 69/100**

---

## Gate G2 — CRITICAL

Si existe al menos un CRITICAL abierto:

**la puntuación final máxima es 79/100**

---

## Gate G3 — Verificación esencial rota

Si alguna capacidad esencial aplicable como:

* bootstrap;
* build;
* suite principal de tests;
* validación principal;
* CI principal;

falla durante la auditoría:

**la puntuación final máxima es 89/100**

---

# 23. Aplicación de múltiples Gates

Si se activan varios Gates simultáneamente, se utiliza el más restrictivo.

Ejemplo:

Score bruto:

`94`

Existe:

* 1 CRITICAL;
* suite principal de tests fallando.

Límites:

* CRITICAL → 79
* Tests → 89

Resultado:

`79/100`

---

# 24. Score bruto y Score final

Siempre deben informarse por separado.

Ejemplo:

`Score bruto: 91/100`

`Quality Gate aplicado: CRITICAL`

`Score final: 79/100`

Esto permite diferenciar:

* calidad matemática;
* riesgo global.

---

# 25. Condiciones obligatorias para 100/100

Un proyecto sólo puede obtener:

**100/100**

si se cumplen simultáneamente todas las siguientes condiciones:

1. Todos los criterios aplicables obtienen puntuación completa.
2. No existen BLOCKER abiertos.
3. No existen CRITICAL abiertos.
4. No existen MAJOR que afecten criterios puntuables.
5. No existen MINOR que resten puntuación.
6. Todos los mecanismos críticos que puedan razonablemente ejecutarse fueron verificados.
7. Todas las verificaciones críticas ejecutadas finalizaron correctamente.
8. No existen contradicciones conocidas entre documentación e implementación.
9. No existen requisitos obligatorios pendientes.
10. Toda afirmación crítica posee evidencia suficiente.
11. No se activa ningún Quality Gate.
12. El nivel de confianza de la auditoría es ALTO.

---

# 26. Qué significa realmente 100/100

`100/100` NO significa:

* software perfecto;
* ausencia absoluta de bugs;
* ausencia de riesgos desconocidos;
* certificación oficial;
* garantía de seguridad;
* garantía de funcionamiento futuro.

Significa:

> Dentro del alcance definido y utilizando la evidencia disponible, todos los criterios aplicables de este estándar fueron satisfechos y verificados sin hallazgos puntuables abiertos conocidos.

---

# 27. No premiar complejidad

Agregar más componentes no aumenta automáticamente la calidad.

No deben otorgarse puntos adicionales por tener:

* más documentación;
* más tests;
* más workflows;
* más agentes;
* más herramientas;
* más scripts;
* más capas arquitectónicas;
* más controles;

si dichos elementos no aportan valor proporcional.

La simplicidad correcta debe considerarse una característica positiva.

---

# 28. No penalizar decisiones válidas distintas

Este estándar evalúa resultados y controles, no preferencias personales.

No deben penalizarse decisiones simplemente porque el auditor prefiera otra tecnología o metodología.

Ejemplos:

* GitFlow frente a trunk-based development;
* GitHub Actions frente a otro CI;
* una librería frente a otra;
* monorepo frente a multirepo.

Debe evaluarse si la solución elegida es:

* coherente;
* segura;
* mantenible;
* adecuada al contexto.

---

# 29. No inventar requisitos

El auditor no debe exigir capacidades simplemente porque sean populares o modernas.

Todo requisito debe derivarse de:

1. este estándar;
2. el perfil aplicable;
3. el contrato declarado por el proyecto;
4. requisitos explícitos del proyecto;
5. riesgos objetivos técnicamente justificables.

---

# 30. Puntuación y confianza

Toda auditoría debe declarar además un nivel de confianza.

## ALTA

Se pudo inspeccionar directamente el repositorio y ejecutar las verificaciones críticas aplicables.

## MEDIA

Se pudo inspeccionar el repositorio pero alguna verificación relevante no pudo ejecutarse.

## BAJA

La evaluación depende sustancialmente de:

* documentación;
* evidencias parciales;
* información indirecta;
* acceso limitado.

Un resultado:

`100/100`

requiere obligatoriamente:

`Confianza: ALTA`

---

# 31. Interpretación de la nota

La puntuación numérica puede interpretarse de la siguiente manera:

| Score | Interpretación                             |
| ----: | ------------------------------------------ |
|  0–49 | Calidad insuficiente                       |
| 50–69 | Requiere correcciones importantes          |
| 70–79 | Base funcional con deficiencias relevantes |
| 80–89 | Buen nivel, aún no de referencia           |
| 90–94 | Muy buen nivel                             |
| 95–99 | Excelente, con desviaciones menores        |
|   100 | Cumplimiento completo verificable          |

Estas bandas son descriptivas.

No sustituyen el análisis de hallazgos ni los Quality Gates.

---

# 32. Estados globales

Además de la puntuación se asignará uno de los siguientes estados.

## NO APTO

Existe riesgo que impide recomendar el proyecto para su propósito actual.

Normalmente asociado a:

* BLOCKER;
* múltiples CRITICAL;
* capacidades fundamentales rotas.

## APTO CON CORRECCIONES

El proyecto puede utilizarse, pero presenta deficiencias que deben resolverse.

## APTO

El proyecto cumple adecuadamente su propósito sin defectos relevantes que bloqueen su utilización.

## TEMPLATE DE REFERENCIA 100/100

Sólo puede asignarse cuando:

`Score final = 100/100`

y se cumplen todas las condiciones definidas en este documento.

Para perfiles que no sean TEMPLATE podrá utilizarse un nombre equivalente definido por el perfil correspondiente.

---

# 33. Mejora opcional frente a defecto

Debe distinguirse claramente entre:

### Defecto

Existe incumplimiento respecto del estándar, perfil, contrato o comportamiento esperado.

Puede restar puntos.

### Mejora opcional

Podría mejorar el proyecto, pero su ausencia no constituye incumplimiento.

No resta puntos.

Un proyecto puede obtener 100/100 y seguir teniendo mejoras opcionales posibles.

---

# 34. Recuperación de puntos

Toda corrección propuesta debe indicar qué puntuación puede recuperar.

La suma de puntos recuperables no puede superar la pérdida real existente.

Ejemplo correcto:

Score actual:

`94`

Hallazgo A:

`-3`

Hallazgo B:

`-2`

Hallazgo C:

`-1`

Camino a 100:

`+3 +2 +1 = 100`

Ejemplo incorrecto:

Score actual:

`94`

Proponer seis mejoras de `+3` cada una.

El camino obligatorio a 100/100 debe explicar la recuperación de TODOS los
puntos perdidos.

Debe cumplirse exactamente:

`puntos actuales + puntos recuperables obligatorios = puntos aplicables`

antes de normalización.

Si el plan de remediación proyectado no alcanza matemáticamente 100/100, el
"Camino a 100" es incompleto y la auditoría debe marcarse como inconsistente
hasta corregirlo.

---

# 35. Integridad matemática

Antes de emitir cualquier evaluación deben comprobarse:

1. suma de subcriterios;
2. suma de áreas;
3. puntuación bruta;
4. normalización por N/A;
5. Quality Gates;
6. puntuación final;
7. puntos recuperables.

La suma total máxima debe permanecer exactamente en:

**100 puntos**

---

# 36. Regla de reproducibilidad

Dos auditores independientes que utilicen:

* la misma versión de este estándar;
* el mismo perfil;
* el mismo commit;
* la misma evidencia;
* las mismas condiciones de ejecución;

deberían producir resultados sustancialmente equivalentes.

Las divergencias importantes deben considerarse una señal para revisar:

* criterios ambiguos;
* evidencia insuficiente;
* interpretación incorrecta;
* metodología defectuosa.

---

# 37. Identificación de la versión evaluada

Toda evaluación debe registrar, cuando sea posible:

* repositorio;
* branch;
* commit;
* tag;
* fecha;
* versión de `QUALITY_SCORE.md`;
* perfil utilizado.

Ejemplo:

```text
Repositorio: example-template
Branch: develop
Commit: a12b34c
Tag: N/A
Quality Score Standard: 1.1
Perfil: TEMPLATE 1.1
```

Esto permite repetir posteriormente la evaluación exacta.

---

# 38. Cambios al estándar

Este documento constituye el contrato matemático de evaluación.

No debe modificarse durante una auditoría para favorecer o perjudicar al proyecto evaluado.

Los cambios deben:

1. realizarse fuera de una auditoría activa;
2. documentarse;
3. actualizar la versión;
4. aplicarse posteriormente a todas las nuevas auditorías.

---

# 39. Versionado del estándar

Se utilizará:

`MAJOR.MINOR`

Ejemplos:

`1.0`
`1.1`
`2.0`

## Cambio MINOR

Puede incluir:

* aclaraciones;
* mejoras de redacción;
* reglas adicionales que no cambien sustancialmente la distribución matemática.

## Cambio MAJOR

Requerido cuando cambien:

* áreas;
* pesos;
* criterios puntuables;
* Quality Gates;
* significado de 100/100;
* metodología matemática esencial.

---

# 40. Regla de consistencia entre hallazgos y puntuación

Todo criterio con puntuación inferior al 100 % debe tener una causa identificable.

Cada pérdida de puntos debe poder relacionarse con:

`CRITERIO → HALLAZGO/CONDICIÓN → EVIDENCIA → PUNTOS PERDIDOS`

Está prohibido:

- descontar puntos sin identificar la causa;
- recuperar puntos mediante un hallazgo que no explica toda la pérdida;
- asociar un hallazgo a un criterio que no tenga relación material con él;
- declarar un camino a 100 que deje subcriterios parcialmente puntuados sin
  explicar cómo recuperan sus puntos.

---

# 41. Regla final

El objetivo de este estándar no es conseguir que todos los proyectos obtengan 100/100.

El objetivo es que un proyecto sólo obtenga 100/100 cuando exista evidencia suficiente para justificarlo.

La puntuación debe ser consecuencia de la calidad.

Nunca la calidad una consecuencia de la puntuación.
