# AUDIT_RULES.md

# Audit Execution Rules

**Versión:** 1.1
**Estado:** Activo
**Complementa:** `QUALITY_SCORE.md`

---

# 1. Propósito

Este documento define las reglas obligatorias que debe seguir cualquier auditor encargado de evaluar un repositorio mediante el estándar `QUALITY_SCORE.md`.

Su objetivo es conseguir auditorías:

* reproducibles;
* independientes;
* basadas en evidencia;
* técnicamente justificables;
* resistentes a alucinaciones;
* comparables entre modelos, agentes y herramientas;
* capaces de distinguir entre documentación, intención e implementación real.

Este documento define **cómo auditar**.

No redefine la puntuación matemática.

La puntuación se encuentra exclusivamente en:

`QUALITY_SCORE.md`

---

# 2. Principio rector

El auditor debe intentar descubrir la realidad del repositorio.

No debe intentar demostrar que el repositorio:

* es bueno;
* es malo;
* merece 100;
* no merece 100.

La conclusión debe surgir de la evidencia encontrada.

La auditoría debe responder:

> ¿Qué puede demostrarse objetivamente sobre la calidad actual de este repositorio dentro del alcance definido?

---

# 3. Independencia del auditor

El auditor debe actuar de forma independiente respecto de:

* documentación promocional;
* puntuaciones anteriores;
* opiniones de otros agentes;
* objetivos aspiracionales;
* expectativas del autor;
* reputación de las herramientas utilizadas.

Un proyecto no recibe mejor evaluación por utilizar tecnologías populares.

Un proyecto no recibe peor evaluación por utilizar tecnologías menos comunes.

Se evalúan:

* resultados;
* coherencia;
* controles;
* funcionamiento;
* mantenibilidad;
* seguridad;
* trazabilidad;
* adecuación al contexto.

---

# 4. Prohibición de evaluación superficial

Está prohibido asignar una puntuación definitiva después de revisar únicamente:

* README;
* documentación;
* estructura de carpetas;
* nombres de archivos;
* ROADMAP;
* archivos de configuración aislados.

La auditoría debe inspeccionar, cuando sean aplicables:

* estructura real;
* documentación;
* configuración;
* código;
* scripts;
* tests;
* workflows;
* dependencias;
* automatizaciones;
* Git;
* configuración remota verificable;
* comportamiento ejecutable.

---

# 5. Unidad de auditoría

Toda auditoría debe identificar exactamente qué versión del proyecto está evaluando.

Registrar cuando sea posible:

```text
Repositorio:
Ruta:
Branch:
Commit:
Tag:
Fecha:
Quality Score Standard:
Perfil:
Auditor:
Entorno:
```

El commit constituye la referencia preferida.

Si el repositorio contiene cambios sin commit, debe indicarse explícitamente:

`WORKTREE NO LIMPIO`

y registrarse qué estado fue auditado.

---

# 6. Alcance

Antes de comenzar la puntuación debe determinarse el alcance.

El auditor debe identificar:

1. tipo de repositorio;
2. propósito declarado;
3. tecnologías principales;
4. perfil de auditoría aplicable;
5. componentes incluidos;
6. componentes excluidos;
7. restricciones del entorno;
8. verificaciones que pueden ejecutarse.

El alcance no debe modificarse arbitrariamente durante la auditoría.

Si aparece nueva información material, debe registrarse explícitamente la ampliación o corrección del alcance.

---

# 7. Perfil aplicable

`QUALITY_SCORE.md` define criterios generales.

El archivo correspondiente en:

`profiles/`

define cómo deben interpretarse para una determinada clase de proyecto.

Ejemplo:

```text
profiles/TEMPLATE.md
profiles/APPLICATION.md
profiles/LIBRARY.md
```

El auditor debe aplicar:

```text
QUALITY_SCORE
+
AUDIT_RULES
+
PERFIL
+
CONTRATO DEL PROYECTO
```

Ninguno de estos elementos debe interpretarse de forma aislada.

---

# 8. Jerarquía de fuentes

Cuando existan contradicciones, se utilizará el siguiente orden de confianza.

## Nivel 1 — Comportamiento verificado

Resultado reproducible de ejecución.

Ejemplos:

* tests ejecutados;
* build;
* validaciones;
* comportamiento observable.

## Nivel 2 — Implementación real

Código, configuración, workflow o script utilizado realmente.

## Nivel 3 — Configuración externa verificada

Ejemplos:

* reglas reales de branch protection;
* required checks;
* permisos;
* configuración CI externa.

## Nivel 4 — Contrato normativo del repositorio

Ejemplos:

* especificaciones;
* reglas oficiales;
* ADR;
* AGENTS;
* CONTRIBUTING;
* documentación normativa.

## Nivel 5 — Documentación descriptiva

Ejemplos:

* README;
* tutoriales;
* ejemplos.

## Nivel 6 — Comentarios e intención

Comentarios de código, TODO, notas u otros elementos sin garantía de implementación.

Cuando dos fuentes contradigan entre sí:

> prevalece la evidencia de mayor nivel.

La contradicción debe registrarse como hallazgo cuando sea relevante.

---

# 9. Documentación no equivale a implementación

Una frase como:

> “Todos los cambios pasan por tests automáticos”

no demuestra que eso ocurra.

Debe comprobarse, cuando sea posible:

```text
workflow existente
→ workflow ejecuta tests
→ workflow puede fallar
→ check requerido para integración
```

Si sólo existe la afirmación documental:

Estado:

`DOCUMENTADO`

No:

`VERIFICADO`

---

# 10. Existencia no equivale a funcionamiento

La presencia de:

```text
tests/
.github/workflows/
scripts/
docs/
```

no demuestra calidad por sí misma.

Ejemplos:

Un directorio `tests/` puede:

* estar vacío;
* contener tests obsoletos;
* no ejecutarse;
* pasar siempre;
* probar comportamiento irrelevante.

Un workflow puede:

* estar desactivado;
* ignorar errores;
* ejecutar comandos incorrectos;
* no ser requerido;
* no corresponder a la rama principal.

El auditor debe evaluar efectividad, no presencia nominal.

---

# 11. Orden obligatorio de auditoría

La auditoría debe realizarse, salvo causa justificada, en el siguiente orden.

---

## FASE 1 — Identificación

Determinar:

* repositorio;
* commit;
* branch;
* propósito;
* tecnologías;
* perfil.

---

## FASE 2 — Inventario

Inspeccionar la estructura general.

Identificar:

* código;
* documentación;
* configuración;
* tests;
* scripts;
* workflows;
* agentes;
* dependencias;
* artefactos;
* archivos sospechosos.

---

## FASE 3 — Contrato

Determinar qué promete el proyecto.

Extraer requisitos de:

* README;
* ROADMAP;
* especificaciones;
* documentación normativa;
* archivos de agentes;
* configuración;
* otras fuentes relevantes.

---

## FASE 4 — Implementación

Comprobar dónde y cómo están implementadas las capacidades declaradas.

---

## FASE 5 — Verificación ejecutable

Ejecutar los mecanismos oficiales del proyecto cuando sea seguro y razonablemente posible.

---

## FASE 6 — Infraestructura y gobernanza

Revisar:

* Git;
* CI;
* branches;
* releases;
* seguridad;
* supply chain;
* automatización.

---

## FASE 7 — Hallazgos

Consolidar problemas.

Eliminar:

* duplicados;
* síntomas derivados;
* falsos positivos.

Identificar causas raíz.

---

## FASE 8 — Puntuación

Sólo después de haber consolidado la evidencia se asignan puntos.

---

## FASE 9 — Validación matemática

Verificar:

* subtotales;
* total;
* N/A;
* gates;
* puntos recuperables.

---

## FASE 10 — Informe

Generar el resultado final siguiendo el formato requerido.

---

# 12. Prohibición de puntuar prematuramente

El auditor no debe ir fijando definitivamente la puntuación mientras descubre el proyecto.

Puede mantener una puntuación provisional interna.

La nota oficial sólo debe calcularse una vez consolidada:

* evidencia;
* hallazgos;
* causas raíz;
* aplicabilidad.

Esto reduce sesgos de anclaje.

---

# 13. Evidencia mínima

Todo descuento o puntuación completa debe poder justificarse.

La evidencia debe indicar cuando corresponda:

```text
Archivo:
Ruta:
Línea/sección:
Comando:
Resultado:
Configuración:
Referencia:
```

Ejemplo:

```text
Evidencia:
.github/workflows/ci.yml

El workflow ejecuta:
pytest

Resultado local:
327 passed

Estado:
VERIFICADO
```

---

# 14. Calidad de la evidencia

Se consideran niveles de evidencia:

## E1 — Declarativa

Existe una afirmación documental.

## E2 — Estructural

Existe el elemento correspondiente.

## E3 — Implementación inspeccionada

La implementación parece coherente después de ser revisada.

## E4 — Ejecución satisfactoria

La capacidad fue ejecutada correctamente.

## E5 — Enforcement verificado

Además de funcionar, existe evidencia de que el control no puede omitirse fácilmente cuando debería ser obligatorio.

No todos los criterios requieren E5.

El nivel requerido debe ser proporcional al riesgo evaluado.

---

# 15. Verificación ejecutable

Siempre que exista una forma oficial y segura de verificar un comportamiento relevante, el auditor debe preferir ejecutarla.

Ejemplos:

```text
test
lint
format check
typecheck
build
validate
doctor
bootstrap
security scan
regression suite
```

Debe priorizar los comandos definidos oficialmente por el repositorio.

Ejemplos de fuentes:

```text
README
Makefile
package.json
pyproject.toml
Taskfile
scripts/
CI workflows
documentación oficial
```

---

# 16. No inventar comandos

El auditor no debe asumir arbitrariamente que:

```text
npm test
pytest
make test
```

son los comandos correctos.

Primero debe identificar el mecanismo oficial.

Si decide utilizar una verificación adicional debe diferenciarla explícitamente:

`VERIFICACIÓN COMPLEMENTARIA DEL AUDITOR`

de:

`VERIFICACIÓN OFICIAL DEL PROYECTO`

---

# 17. Seguridad durante la ejecución

El auditor no debe ejecutar comandos potencialmente destructivos sin necesidad.

Debe evitar, salvo necesidad explícita y entorno seguro:

* borrado de datos;
* despliegues reales;
* migraciones destructivas;
* publicación de paquetes;
* releases;
* pushes;
* modificaciones remotas;
* acciones sobre producción.

Cuando una verificación requiera una operación destructiva o irreversible:

debe evaluarse por inspección o mediante un entorno aislado apropiado.

---

# 18. No modificar para poder auditar

La auditoría debe evaluar el estado existente.

Está prohibido:

* corregir código;
* agregar dependencias;
* reparar configuración;
* modificar workflows;
* actualizar documentación;

para conseguir que una verificación pase antes de puntuar.

Si es imprescindible realizar una modificación puramente temporal para poder observar algo, debe:

1. quedar claramente identificada;
2. no formar parte del resultado auditado;
3. revertirse;
4. no utilizarse como evidencia de cumplimiento original.

---

# 19. Dependencias faltantes

Si una verificación falla porque falta una dependencia:

debe determinarse primero si:

### Caso A

La dependencia debería instalarse automáticamente siguiendo las instrucciones oficiales.

Entonces puede existir un defecto de bootstrap.

### Caso B

El entorno del auditor no cumple un prerrequisito claramente documentado.

Entonces no debe penalizarse automáticamente al proyecto.

Debe registrarse:

`NO VERIFICADO — LIMITACIÓN DEL ENTORNO`

---

# 20. Acceso insuficiente

Si el auditor no puede comprobar configuración externa como:

* GitHub branch protection;
* required reviewers;
* secretos;
* permisos;
* environments;

debe marcar:

`NO VERIFICADO`

No debe asumir:

* que existe;
* que no existe.

La puntuación debe seguir las reglas de evidencia definidas en `QUALITY_SCORE.md`.

---

# 21. Evidencia remota

Cuando exista acceso autorizado, pueden utilizarse fuentes externas directamente relacionadas con el repositorio.

Ejemplos:

* configuración GitHub;
* resultados CI;
* releases;
* tags;
* checks;
* políticas;
* registry de paquetes.

Debe distinguirse entre:

```text
CONFIGURACIÓN VERIFICADA
```

y

```text
CONFIGURACIÓN DOCUMENTADA
```

---

# 22. Contrato del proyecto

El auditor debe construir una lista de requisitos verificables a partir del propio repositorio.

Clasificar cada requisito como:

```text
OBLIGATORIO
RECOMENDADO
OPCIONAL
DEPRECADO
AMBIGUO
```

Un requisito obligatorio no implementado puede producir un hallazgo.

Un elemento opcional ausente no debe penalizarse automáticamente.

---

# 23. ROADMAP

Un ROADMAP representa intención futura, no necesariamente incumplimiento actual.

Debe distinguirse entre:

### Trabajo futuro planificado

No afecta necesariamente la calidad actual.

### Requisito declarado para la versión actual

Sí puede afectar la puntuación.

El auditor debe evitar penalizar automáticamente todos los elementos pendientes de un ROADMAP.

---

# 24. TODO y FIXME

La existencia de:

```text
TODO
FIXME
HACK
XXX
```

debe investigarse.

No constituye automáticamente un defecto puntuable.

Debe determinarse:

* si afecta funcionalidad;
* si representa deuda real;
* si sigue vigente;
* si está en código muerto;
* si es meramente informativo.

---

# 25. Código muerto y residuos

El auditor debe buscar razonablemente:

* archivos abandonados;
* configuraciones obsoletas;
* scripts sin uso;
* documentación vieja;
* ramas de compatibilidad innecesarias;
* duplicados;
* ejemplos accidentales;
* artefactos generados;
* backups;
* temporales.

No debe recomendar eliminar algo sólo porque no comprende su finalidad.

Antes debe comprobar:

* referencias;
* documentación;
* uso;
* historial cuando sea necesario.

---

# 26. Duplicación

Debe distinguirse entre:

### Duplicación accidental

Misma fuente de verdad mantenida manualmente en varios lugares.

Puede generar divergencia.

### Duplicación necesaria

Ejemplo:

archivos adaptadores requeridos por herramientas distintas.

No debe penalizarse cuando existe una razón técnica válida y mecanismos adecuados para mantener consistencia.

---

# 27. Complejidad

No debe penalizarse un proyecto por ser complejo si su dominio exige esa complejidad.

Debe identificarse:

### Complejidad esencial

Proviene del problema que se resuelve.

### Complejidad accidental

Proviene de decisiones evitables.

Sólo la complejidad accidental injustificada debe considerarse defecto.

---

# 28. Evaluación contextual

No deben exigirse mecanismos irrelevantes.

Ejemplo:

Una librería pequeña puede no necesitar:

* rollback de despliegue;
* infraestructura productiva;
* múltiples entornos.

Un servicio productivo crítico puede necesitarlos.

La aplicabilidad debe determinarse por:

* tipo de proyecto;
* perfil;
* riesgo;
* contrato.

## Plataforma específica

Un proyecto no debe perder puntos por estar diseñado para una plataforma específica
cuando esa restricción:

* está declarada explícitamente;
* es coherente con el propósito del proyecto;
* no contradice una promesa de portabilidad mayor;
* no introduce dependencias accidentales adicionales.

Ejemplo:

Un template declarado como `Windows + PowerShell` no debe penalizarse simplemente
por no ser multiplataforma.

Sí puede existir penalización cuando la dependencia de plataforma:

* no está documentada;
* contradice el alcance declarado;
* depende de rutas, usuarios o máquinas concretas;
* impide reproducir el flujo prometido dentro de la plataforma soportada.

---

# 29. Uso de N/A

Antes de declarar un criterio N/A debe responderse:

> ¿El criterio es realmente irrelevante para esta clase de proyecto o simplemente no está implementado?

Si la respuesta es:

> “No está implementado”

entonces no es N/A.

Cada N/A debe contener una justificación concreta.

Ejemplo válido:

```text
Q6.6 — N/A

El repositorio es una colección documental sin datos persistentes,
artefactos desplegables ni contratos de compatibilidad versionados.
No existen migraciones o rollback aplicables.
```

---

# 30. Hallazgos independientes

Cada hallazgo debe describir un problema concreto.

Formato conceptual:

```text
ID
Tipo
Severidad
Descripción
Evidencia
Impacto
Criterio afectado
Corrección
Verificación
```

Evitar hallazgos vagos como:

> “Mejorar calidad.”

---

# 31. Tipos de hallazgo

Cada hallazgo debe clasificarse además por naturaleza.

Valores:

```text
FALTA
INCORRECTO
INCOMPLETO
ROTO
CONTRADICTORIO
SOBRA
DUPLICADO
OBSOLETO
RIESGO
NO VERIFICADO
```

Puede utilizarse más de un tipo cuando sea necesario, pero debe evitarse clasificación excesiva.

---

# 32. Severidad

La severidad debe basarse en impacto, no en tamaño del archivo o esfuerzo de corrección.

## BLOCKER

Impide el uso seguro o funcional.

## CRITICAL

Riesgo grave incompatible con un estándar profesional de referencia.

## MAJOR

Problema significativo.

## MINOR

Problema real de impacto limitado.

## SUGGESTION

Mejora no necesaria para cumplimiento.

Una `SUGGESTION`:

* nunca resta puntos;
* nunca activa un Quality Gate;
* nunca bloquea 100/100;
* nunca forma parte del camino obligatorio a 100/100.

Si un hallazgo reduce puntuación o impide alcanzar 100/100, debe clasificarse con
una severidad puntuable adecuada y no como `SUGGESTION`.

---

# 33. Severidad no equivale directamente a puntos

Un CRITICAL no significa automáticamente una cantidad fija de puntos menos.

Los puntos se descuentan en el criterio afectado.

La severidad se utiliza para:

* expresar riesgo;
* aplicar Quality Gates;
* priorizar correcciones.

Esto evita penalización doble.

---

# 34. Causa raíz

Antes de finalizar los hallazgos, el auditor debe intentar identificar causas raíz.

Ejemplo:

Síntomas:

```text
tests no ejecutan
lint no ejecuta
build no ejecuta
```

Causa:

```text
script validate roto
```

El auditor debe registrar:

```text
ROOT-001
```

y relacionar los síntomas.

No debe crear tres problemas independientes artificiales si derivan de la misma causa.

---

# 35. Impactos múltiples

Una causa raíz puede afectar legítimamente varios criterios.

Ejemplo:

CI no ejecuta tests.

Puede afectar:

```text
Q5.5 Quality Gates
Q6.3 CI
```

Esto no es necesariamente doble penalización porque son dimensiones distintas.

Sin embargo, el auditor debe ajustar el descuento proporcionalmente y documentar que comparten causa.

---

# 36. Evitar doble penalización

Antes de descontar un criterio debe preguntarse:

> ¿Ya se está descontando exactamente este mismo incumplimiento en otro criterio?

Si sí:

* evitar repetir el descuento completo;
* documentar el impacto cruzado;
* conservar una penalización principal.

---

# 37. Contradicciones

Las contradicciones deben registrarse explícitamente.

Ejemplo:

README:

```text
Todos los cambios entran mediante PR.
```

Configuración real:

```text
push directo permitido.
```

Resultado:

La implementación observada prevalece.

Debe registrarse un hallazgo de coherencia.

---

# 38. Configuración efectiva

Cuando exista configuración heredada o compuesta, el auditor debe intentar determinar el comportamiento efectivo.

Ejemplos:

* configuración base + override;
* workflows reutilizables;
* archivos incluidos;
* reglas heredadas;
* configuración global/local.

No debe evaluar únicamente un archivo aislado si no representa el resultado final.

---

# 39. Generated files

Los archivos generados deben identificarse cuando sea posible.

No deben tratarse como fuente de verdad principal si existe un archivo fuente que los genera.

Ejemplo:

```text
archivo fuente
↓
generador
↓
archivo generado
```

La auditoría debe preferir evaluar:

* fuente;
* mecanismo de generación;
* consistencia del resultado.

---

# 40. Archivos vendor o terceros

El auditor debe diferenciar código propio de:

* vendor;
* dependencias;
* código generado;
* submódulos;
* artefactos externos.

No debe atribuir automáticamente la calidad interna de código tercero al proyecto.

Sí debe evaluar:

* selección;
* integración;
* versionado;
* riesgos;
* mantenimiento.

---

# 41. Tests

Los tests deben evaluarse por efectividad.

El auditor debe analizar razonablemente:

* qué prueban;
* si pueden fallar;
* si cubren comportamiento crítico;
* si se ejecutan;
* si son deterministas;
* si dependen innecesariamente del entorno;
* si existe regresión para defectos conocidos importantes.

No debe evaluar la calidad únicamente por cantidad de tests.

---

# 42. Cobertura

Una métrica de cobertura puede utilizarse como evidencia complementaria.

No debe convertirse automáticamente en objetivo de calidad.

Ejemplo incorrecto:

> 100 % coverage = tests perfectos.

Debe evaluarse la calidad de las verificaciones, no sólo la cantidad de líneas ejecutadas.

---

# 43. CI

Para considerar CI plenamente efectiva debe comprobarse, cuando sea posible:

```text
workflow existe
→ ejecuta verificaciones relevantes
→ los errores hacen fallar el job
→ se ejecuta en eventos correctos
→ protege la integración cuando corresponde
```

Si una parte no puede verificarse:

registrarla.

---

# 44. Fallos silenciados

El auditor debe prestar especial atención a patrones que convierten errores en falsos éxitos.

Ejemplos conceptuales:

```text
continue-on-error
|| true
exit 0
try/catch que ignora fallo
allowed failure
```

No todos son incorrectos.

Debe determinarse si permiten ignorar una verificación que debería bloquear.

---

# 45. Git

El auditor debe evaluar el flujo Git real cuando pueda observarlo.

Puede considerar:

* branches;
* convenciones;
* PR;
* merges;
* reviews;
* required checks;
* tags;
* releases;
* protección.

No debe exigir un modelo de branching particular sin fundamento.

## Objetivo de control de integración

La evaluación de protección de ramas debe centrarse en el objetivo de control,
no en exigir una funcionalidad comercial concreta de una plataforma.

Si la plataforma no permite branch protection nativa por limitaciones de plan,
el auditor debe comprobar si existe un control técnico alternativo verificable
que logre de forma suficientemente equivalente el objetivo esperado.

Ejemplos de controles alternativos posibles:

* gate técnico previo al merge;
* workflow que rechaza integraciones no autorizadas;
* automatización que impide o revierte cambios fuera del circuito;
* mecanismo equivalente verificable.

Una regla exclusivamente documental o basada sólo en disciplina humana no
equivale a enforcement técnico completo.

El auditor no debe convertir automáticamente en requisito:

* pagar un plan superior;
* hacer público un repositorio;
* cambiar de proveedor;

si el objetivo de control puede satisfacerse profesionalmente por otro medio.

## Versionado y releases no ejercidos

Cuando el proyecto declare versionado o releases como capacidad **actual y
obligatoria**, pero nunca haya ejecutado el flujo real, la falta de evidencia
de ejecución puede reducir el criterio correspondiente.

En ese caso:

* la pérdida debe quedar asociada al criterio y a un hallazgo puntuable;
* no puede clasificarse simultáneamente como `SUGGESTION`;
* el camino a 100/100 debe indicar la verificación real necesaria para recuperar
  esos puntos.

Si el release está declarado únicamente como capacidad futura, prospectiva o de
ROADMAP, su falta de ejecución no debe penalizar la versión actual.

---

# 46. Historial Git

El historial puede utilizarse para verificar:

* coherencia del flujo;
* versionado;
* tags;
* releases;
* cambios relevantes;
* archivos recientemente eliminados;
* origen de contradicciones.

No debe revisarse exhaustivamente sin necesidad.

---

# 47. Seguridad

Los hallazgos de seguridad deben basarse en riesgo concreto.

Evitar:

* alarmismo;
* severidad inflada;
* recomendaciones genéricas.

Cada riesgo debe explicar:

```text
activo
amenaza
condición
impacto
evidencia
```

cuando sea relevante.

## Licencia y términos de reutilización

La ausencia de un archivo `LICENSE` no debe penalizarse automáticamente.

Debe evaluarse el contexto:

* si el repositorio se distribuye externamente o públicamente, los términos de
  reutilización pueden ser necesarios;
* si el contrato del proyecto exige una licencia, su ausencia es puntuable;
* si el repositorio es privado, interno o personal y no promete distribución,
  la ausencia de `LICENSE` no constituye por sí sola un defecto.

Si existe incertidumbre real sobre derechos de reutilización dentro del alcance
declarado, el auditor debe explicar el riesgo concreto antes de descontar puntos.

---

# 48. Secretos

Si aparecen posibles secretos:

1. no reproducirlos completos en el informe;
2. redactarlos;
3. verificar razonablemente si parecen reales;
4. tratarlos con prioridad.

Ejemplo:

```text
Token detectado:
ghp_****abcd
```

Nunca copiar la credencial completa al reporte.

---

# 49. Dependencias

No debe considerarse vulnerable una dependencia únicamente por ser antigua.

Debe distinguirse:

* versión antigua;
* vulnerabilidad conocida;
* incompatibilidad;
* abandono;
* riesgo real.

Si no se dispone de información suficiente:

`NO VERIFICADO`

---

# 50. Auditoría de agentes IA

Cuando el repositorio utilice agentes, debe evaluarse:

* responsabilidades;
* límites;
* fuentes de verdad;
* permisos;
* secuencia;
* escalamiento humano;
* manejo de fallos;
* trazabilidad;
* duplicación;
* comportamiento esperado.

No debe evaluarse la calidad por cantidad de agentes.

---

# 51. HITL

Cuando exista Human-in-the-Loop, comprobar:

* cuándo interviene;
* qué debe aprobar;
* qué evidencia recibe;
* qué operaciones no puede saltarse;
* qué sucede si rechaza.

Un HITL meramente mencionado pero no integrado al flujo debe considerarse documental, no verificado.

---

# 52. Determinismo

Las automatizaciones críticas deben reducir comportamientos ambiguos.

Debe comprobarse razonablemente:

* entradas;
* salidas;
* condiciones;
* estados;
* errores;
* criterios de éxito.

No se exige determinismo matemático absoluto a un agente IA.

Se exige control suficiente sobre operaciones críticas.

---

# 53. Fail-safe

Ante un error crítico, el comportamiento preferido debe ser:

```text
detener
fallar
escalar
pedir aprobación
```

según corresponda.

Debe investigarse cualquier flujo donde:

```text
error crítico
→ proceso continúa
→ resultado marcado como exitoso
```

---

# 54. Trazabilidad

La trazabilidad debe evaluarse proporcionalmente.

Puede involucrar:

```text
requisito
→ issue/roadmap
→ branch
→ cambio
→ test
→ review
→ PR
→ merge
→ tag/release
```

No todos los proyectos necesitan todos los pasos.

Debe existir suficiente información para reconstruir decisiones importantes.

---

# 55. Evidencia negativa

La ausencia de un archivo no siempre demuestra ausencia de una capacidad.

Ejemplo:

No existe:

```text
CONTRIBUTING.md
```

pero las reglas de contribución están correctamente definidas en:

```text
AGENTS.md
README.md
```

Debe evaluarse la capacidad, no exigir nombres arbitrarios de archivos salvo que el perfil lo establezca explícitamente.

---

# 56. Evidencia positiva falsa

La existencia de un archivo con nombre esperado tampoco demuestra cumplimiento.

Ejemplo:

```text
SECURITY.md
```

vacío o genérico.

Debe inspeccionarse su contenido y efectividad.

---

# 57. Calidad documental

La documentación debe juzgarse por:

* exactitud;
* suficiencia;
* coherencia;
* actualidad;
* accionabilidad.

No por:

* longitud;
* cantidad de archivos;
* estilo ornamental.

Más documentación puede empeorar la calidad si aumenta contradicciones.

---

# 58. Ortografía y estilo

Los errores menores de redacción no deben recibir severidad desproporcionada.

Sólo deben afectar puntuación cuando:

* dificultan comprensión;
* generan ambigüedad;
* afectan profesionalidad significativamente;
* alteran instrucciones técnicas.

---

# 59. Recomendaciones

Las recomendaciones deben ser:

* concretas;
* mínimas;
* proporcionales;
* verificables.

Evitar:

> “Mejorar DevOps.”

Preferir:

> “Agregar `pytest` al job `quality` de `.github/workflows/ci.yml` y convertir su fallo en requerido para merge.”

---

# 60. Corrección mínima suficiente

El auditor debe recomendar el cambio mínimo necesario que resuelva correctamente el problema.

No debe aprovechar la auditoría para rediseñar innecesariamente el proyecto.

---

# 61. Qué sobra

La auditoría debe analizar explícitamente elementos innecesarios.

Antes de recomendar eliminación debe poder explicar:

```text
qué es
por qué no aporta valor
qué riesgo genera
qué depende de él
cómo verificar que puede eliminarse
```

---

# 62. Qué falta

Una ausencia sólo debe considerarse defecto si existe fundamento.

El fundamento debe derivar de:

```text
QUALITY_SCORE
PERFIL
CONTRATO
RIESGO OBJETIVO
```

No de preferencias personales.

---

# 63. Mejora opcional

Toda propuesta que no sea necesaria para recuperar puntos debe marcarse:

`SUGGESTION`

Debe quedar separada del camino a 100.

Esto evita que el objetivo 100/100 se convierta en una lista infinita.

Regla de consistencia:

```text
SUGGESTION = 0 puntos perdidos = 0 puntos recuperables obligatorios
```

Si una mejora es necesaria para recuperar aunque sea una fracción de punto,
entonces no es una `SUGGESTION`.

---

# 64. Camino a 100

Para cada pérdida de puntos debe poder identificarse:

```text
hallazgo
→ corrección
→ validación
→ puntos recuperables
```

La corrección debe corresponder exactamente al descuento.

No inventar trabajos adicionales para “merecer” recuperar los puntos.

El camino obligatorio a 100/100 debe cubrir **todos** los puntos perdidos.

Antes de emitir el informe debe comprobarse:

```text
puntos obtenidos
+
puntos recuperables obligatorios
=
puntos aplicables
```

antes de aplicar normalización por N/A.

Si el resultado proyectado queda por debajo de 100/100:

* el camino a 100 está incompleto;
* debe identificarse qué criterio sigue perdiendo puntos;
* no puede presentarse como un plan completo a 100.

Ninguna pérdida puede quedar escondida bajo una mejora opcional.

---

# 65. Verificación de correcciones

Cada hallazgo puntuable debe incluir una forma de comprobar su resolución.

Ejemplos:

```text
ejecutar test
inspeccionar archivo
consultar configuración
repetir bootstrap
verificar required check
comparar salida
```

Una corrección sin criterio de aceptación es incompleta.

## Validación de asociaciones

Antes de cerrar la matriz de puntuación, el auditor debe revisar que cada
asociación:

```text
HALLAZGO ↔ CRITERIO
```

sea materialmente correcta.

Está prohibido asociar un hallazgo a un criterio únicamente para justificar una
pérdida de puntos.

Si un criterio está por debajo de 100 %, debe poder demostrarse exactamente qué
hallazgo o condición explica la pérdida.

Si un hallazgo no afecta materialmente a un criterio, debe eliminarse esa
asociación.

---

# 66. Reauditoría

Después de realizar correcciones, debe preferirse una nueva auditoría sobre el nuevo commit.

No debe simplemente editarse manualmente la nota anterior.

Proceso recomendado:

```text
auditoría
→ correcciones
→ nuevo commit
→ nueva auditoría
```

---

# 67. Evidencia histórica

Los informes anteriores son contexto histórico.

No constituyen evidencia suficiente para la auditoría actual.

Una capacidad que pasó anteriormente puede haberse roto.

Las verificaciones críticas deben repetirse cuando corresponda.

---

# 68. Auditorías cruzadas

Cuando varios auditores evalúan el mismo commit:

deben trabajar, preferentemente, de forma independiente.

No deben conocer la puntuación del otro antes de completar su evaluación inicial.

Después se comparan:

* puntuaciones;
* hallazgos;
* N/A;
* severidades;
* evidencia.

---

# 69. Divergencia entre auditores

Una diferencia significativa no debe resolverse promediando notas.

Debe localizarse:

```text
criterio divergente
→ evidencia de auditor A
→ evidencia de auditor B
→ regla aplicable
→ resolución
```

El objetivo es encontrar el resultado defendible.

---

# 70. Umbral de divergencia

Se recomienda revisar obligatoriamente cualquier diferencia de:

* más de 5 puntos en la nota global;
* más del 25 % dentro de un área;
* cualquier diferencia BLOCKER/CRITICAL;
* cualquier discrepancia sobre 100/100.

La divergencia no implica automáticamente que uno de los auditores sea incorrecto.

Puede revelar una regla ambigua.

---

# 71. Auditoría de la metodología

Si dos auditores competentes interpretan repetidamente un mismo criterio de manera diferente:

el problema puede estar en:

* `QUALITY_SCORE.md`;
* `AUDIT_RULES.md`;
* perfil utilizado.

Debe corregirse el framework en una nueva versión.

No alterar reglas durante una auditoría activa.

---

# 72. Regla anti-alucinación

Está estrictamente prohibido afirmar como hecho algo que no fue observado o inferido con evidencia suficiente.

Expresiones requeridas cuando corresponda:

```text
VERIFICADO
NO VERIFICADO
INFERIDO
NO APLICA
EVIDENCIA INSUFICIENTE
```

---

# 73. Inferencias

Una inferencia puede utilizarse cuando exista evidencia razonable.

Debe identificarse explícitamente.

Ejemplo:

```text
INFERIDO:
Este script parece ser el mecanismo de release porque es invocado
por el workflow de publicación.
```

No debe presentarse como hecho absoluto hasta que exista evidencia suficiente.

---

# 74. Desconocimiento

El auditor puede declarar:

`NO DETERMINADO`

cuando no existe información suficiente.

Es preferible reconocer una limitación que inventar una conclusión.

---

# 75. Prohibición de completar huecos

Está prohibido asumir contenido inexistente basándose en convenciones.

Ejemplo:

No asumir que:

```text
main
```

está protegida porque el README dice que el flujo es profesional.

Debe comprobarse o declararse no verificado.

---

# 76. Fuentes externas

Cuando sea necesario consultar información técnica externa:

priorizar:

1. documentación oficial;
2. estándares oficiales;
3. documentación del proveedor;
4. fuentes primarias;
5. fuentes secundarias de alta calidad.

Las fuentes externas sirven para interpretar requisitos.

No sustituyen la evidencia del repositorio.

---

# 77. Estándares

Los estándares deben utilizarse como marco, no como mecanismo para inflar requisitos.

No debe afirmarse:

> “El proyecto cumple ISO.”

salvo que exista una certificación válida que corresponda.

Puede afirmarse:

> “El criterio está alineado conceptualmente con…”

cuando sea apropiado.

---

# 78. Actualidad

Cuando la evaluación dependa de:

* versiones;
* vulnerabilidades;
* recomendaciones del proveedor;
* herramientas;
* reglas externas;

debe utilizarse información suficientemente actual.

Un estándar o documentación obsoleta no debe utilizarse para penalizar injustificadamente.

---

# 79. Herramientas automáticas

Los resultados de herramientas automáticas no deben aceptarse sin interpretación.

Ejemplos:

* scanners;
* linters;
* SAST;
* dependency scanners;
* coverage.

Debe revisarse:

* relevancia;
* falsos positivos;
* configuración;
* alcance.

---

# 80. Falsos positivos

Un resultado automático que no representa un riesgo real debe documentarse como:

`FALSO POSITIVO`

y no debe reducir la puntuación.

---

# 81. Falsos negativos

Que una herramienta automática no encuentre problemas no demuestra ausencia absoluta de defectos.

Debe utilizarse como una evidencia más.

---

# 82. Resultados parciales

Si una auditoría no puede completarse:

debe generarse un resultado parcial indicando:

* qué se evaluó;
* qué quedó pendiente;
* qué no pudo verificarse;
* nivel de confianza.

No debe emitirse 100/100 con una auditoría incompleta.

---

# 83. Confianza

La confianza debe calcularse cualitativamente según `QUALITY_SCORE.md`.

Factores relevantes:

* acceso completo;
* posibilidad de ejecución;
* evidencia real;
* acceso a configuración remota;
* cantidad de NO VERIFICADO;
* reproducibilidad.

---

# 84. Separación entre score y riesgo

Un score alto no elimina automáticamente riesgos puntuales.

Ejemplo:

Un repositorio podría obtener score bruto alto pero contener un CRITICAL.

Por eso deben mantenerse separados:

```text
Score bruto
Quality Gates
Score final
Hallazgos
Confianza
```

---

# 85. Registro de comandos

Los comandos significativos ejecutados durante la auditoría deben registrarse cuando sea útil.

Formato recomendado:

```text
Comando:
Resultado:
Exit code:
Estado:
```

No es necesario registrar comandos triviales de navegación.

---

# 86. Salidas extensas

Cuando un comando produzca una salida extensa:

no es necesario copiarla íntegra al informe.

Debe preservarse como evidencia y resumirse.

Ejemplo:

```text
pytest:
327 passed
0 failed
duración: ...
```

---

# 87. Evidencias generadas

Cuando la auditoría genere evidencia persistente debe almacenarse preferentemente en:

```text
.audit/evidence/
```

según la convención definida por el framework.

Para auditorías asociadas a un commit debe utilizarse la convención:

```text
YYYY-MM-DD-<short-commit>-<slug>/
```

El `<slug>` debe ser breve, descriptivo y estable.

Ejemplo:

```text
2026-08-29-a12b34c-framework-auditoria/
```

Si no existe commit identificable puede utilizarse:

```text
YYYY-MM-DD-WORKTREE/
```

Los archivos de evidencia no deben modificar el comportamiento del proyecto.

---

# 88. Informes

Los informes deben almacenarse preferentemente en:

```text
.audit/reports/
```

Para auditorías asociadas a un commit debe utilizarse:

```text
AUDIT-YYYY-MM-DD-<short-commit>-<slug>.md
```

Ejemplo:

```text
AUDIT-2026-08-29-a12b34c-framework-auditoria.md
```

Si no existe commit identificable:

```text
AUDIT-YYYY-MM-DD-WORKTREE.md
```

Un informe debe referenciar:

* commit;
* estándar;
* perfil;
* evidencia.

El informe y su carpeta de evidencia deben utilizar el mismo identificador base
si pertenecen a la misma auditoría.

---

# 89. Repetibilidad

Cuando sea razonablemente posible, otro auditor debe poder repetir:

* comandos;
* inspecciones;
* cálculos.

Evitar afirmaciones que dependan exclusivamente de intuición.

---

# 90. Cálculo final

El auditor debe aplicar exactamente:

1. puntuación de subcriterios;
2. suma por área;
3. puntos aplicables;
4. normalización N/A;
5. score bruto;
6. gates;
7. score final.

No modificar manualmente la nota final por “sensación general”.

Antes de emitir el resultado debe ejecutar una validación de consistencia:

```text
[ ] Toda pérdida de puntos tiene causa identificada
[ ] Todo hallazgo puntuable está asociado a un criterio materialmente relacionado
[ ] Ninguna SUGGESTION resta puntos
[ ] Ninguna SUGGESTION bloquea 100/100
[ ] Todos los puntos perdidos aparecen en el camino obligatorio a 100
[ ] El camino proyectado alcanza exactamente los puntos aplicables
[ ] Los N/A están justificados
[ ] Los Quality Gates se derivan de hallazgos reales
```

Si cualquiera de estas comprobaciones falla, el informe debe marcarse:

`INCONSISTENTE — REQUIERE CORRECCIÓN`

y no debe utilizarse como baseline oficial hasta corregir la inconsistencia.

---

# 91. Prohibición de redondeo estratégico

No se debe redondear para alcanzar una banda deseada.

Ejemplo:

`99,94`

no debe convertirse artificialmente en:

`100`

La puntuación máxima sólo se obtiene mediante cumplimiento completo.

---

# 92. Estado global

El estado debe derivarse de:

* score final;
* severidades;
* gates;
* confianza;
* perfil.

No debe seleccionarse únicamente por puntuación.

---

# 93. Regla para 100/100

Antes de emitir 100/100, el auditor debe realizar una última revisión explícita:

```text
[ ] Todos los criterios aplicables = completos
[ ] Sin BLOCKER
[ ] Sin CRITICAL
[ ] Sin MAJOR puntuables
[ ] Sin MINOR puntuables
[ ] Sin verificaciones críticas pendientes
[ ] Tests críticos pasan
[ ] Quality Gates pasan
[ ] Sin contradicciones conocidas
[ ] Sin requisitos obligatorios pendientes
[ ] Evidencia suficiente
[ ] Confianza ALTA
```

Si cualquiera de estas condiciones falla:

`100/100 PROHIBIDO`

---

# 94. Segunda pasada obligatoria para 100

Si la puntuación provisional resulta 100/100:

el auditor debe realizar una segunda pasada dirigida específicamente a intentar refutar ese resultado.

Debe buscar:

* residuos;
* contradicciones;
* verificaciones omitidas;
* TODO críticos;
* archivos obsoletos;
* falsos positivos de CI;
* tests cosméticos;
* configuraciones no verificadas;
* problemas de seguridad;
* supuestos no comprobados.

Sólo si el resultado continúa siendo 100 puede emitirse la calificación final.

---

# 95. No degradar artificialmente un 100

La segunda pasada no debe inventar problemas para evitar otorgar 100.

Si no existe defecto puntuable demostrado:

debe mantenerse el resultado.

Ser exigente no significa crear incumplimientos ficticios.

---

# 96. Preservación del estado

Cuando la auditoría sea exclusivamente de lectura, debe dejar el repositorio en el mismo estado en que lo encontró.

Si alguna herramienta produce archivos temporales:

deben identificarse y limpiarse cuando sea seguro.

---

# 97. Auditoría versus corrección

La auditoría responde:

> ¿Cuál es el estado actual?

La remediación responde:

> ¿Cómo lo llevamos al estado deseado?

Deben mantenerse conceptualmente separadas.

El auditor puede proponer correcciones.

No debe aplicarlas durante la evaluación salvo instrucción explícita posterior.

---

# 98. Prioridad de correcciones

El plan de remediación debe ordenar:

1. BLOCKER
2. CRITICAL
3. MAJOR
4. MINOR
5. SUGGESTION

Dentro de una misma severidad:

priorizar causas raíz y cambios que desbloqueen múltiples hallazgos.

---

# 99. Definición de terminado

Un hallazgo sólo puede considerarse resuelto cuando:

1. se aplicó la corrección;
2. desapareció la causa;
3. se ejecutó su criterio de verificación;
4. la verificación pasó.

Cambiar el archivo sin comprobar el resultado no constituye cierre completo.

---

# 100. Regla final

Toda afirmación importante de una auditoría debe poder responder a esta pregunta:

> ¿Qué evidencia permite sostener esta conclusión?

Si no existe una respuesta suficientemente clara:

la conclusión debe:

* revisarse;
* rebajarse;
* declararse inferida;
* o marcarse como no verificada.

El objetivo del auditor no es producir una nota.

El objetivo es producir una evaluación cuya nota pueda defenderse técnicamente.
