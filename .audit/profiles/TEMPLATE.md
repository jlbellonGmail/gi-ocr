# TEMPLATE.md

# Audit Profile — TEMPLATE

**Versión:** 1.1
**Estado:** Activo
**Tipo de proyecto:** Template reutilizable
**Depende de:**

* `../QUALITY_SCORE.md`
* `../AUDIT_RULES.md`

---

# 1. Propósito

Este perfil define cómo interpretar el estándar `QUALITY_SCORE.md` cuando el repositorio evaluado tiene como objetivo servir como:

* template;
* starter;
* boilerplate;
* skeleton;
* blueprint;
* base reutilizable;
* repositorio de referencia para iniciar nuevos proyectos.

La evaluación debe determinar si una persona o equipo puede utilizar el repositorio como punto de partida profesional sin arrastrar:

* errores;
* residuos;
* conocimiento implícito;
* dependencias accidentales;
* configuraciones privadas;
* contradicciones;
* deuda técnica innecesaria.

El objetivo no es premiar al template que tenga más componentes.

El objetivo es comprobar que contiene exactamente los componentes necesarios para cumplir su propósito de forma:

* segura;
* mantenible;
* reproducible;
* comprensible;
* extensible.

---

# 2. Definición de TEMPLATE DE REFERENCIA

Dentro de este perfil se considera un `TEMPLATE DE REFERENCIA` aquel repositorio que:

1. puede reutilizarse de manera predecible;
2. puede inicializarse desde un estado limpio;
3. no arrastra información específica del proyecto que lo originó;
4. tiene un contrato claro;
5. posee controles de calidad verificables;
6. puede evolucionar sin generar divergencias innecesarias;
7. dispone de documentación suficiente para un consumidor nuevo;
8. protege las operaciones críticas;
9. mantiene una arquitectura proporcional a su objetivo;
10. puede demostrar mediante evidencia que su flujo principal funciona.

Para recibir la clasificación:

`TEMPLATE DE REFERENCIA 100/100`

deben cumplirse además todas las condiciones definidas en `QUALITY_SCORE.md`.

---

# 3. Pregunta principal de auditoría

La auditoría debe responder:

> ¿Puede este repositorio copiarse, clonarse, generarse o reutilizarse hoy como base para un proyecto nuevo sin requerir conocimiento oculto del autor y sin trasladar defectos conocidos al proyecto resultante?

---

# 4. Consumidor objetivo

Antes de puntuar, el auditor debe identificar quién se supone que utilizará el template.

Ejemplos:

* desarrollador individual;
* equipo interno;
* múltiples equipos;
* organización;
* terceros;
* proyectos generados automáticamente;
* agentes de IA;
* combinación humano + agentes.

Las exigencias deben interpretarse en función del consumidor declarado.

Un template interno pequeño puede requerir menos infraestructura que uno distribuido públicamente.

No obstante, ambos deben ser coherentes con su propósito.

---

# 5. Modos de reutilización

El auditor debe determinar cómo se espera utilizar el template.

Posibles mecanismos:

```text
Use this template
git clone
copy
generator
CLI
script de bootstrap
scaffolding
cookiecutter
copier
framework propio
automatización agéntica
```

El mecanismo elegido debe funcionar según su contrato.

No se exige uno específico.

---

# 6. Contrato mínimo de un template

Todo template debe poder responder claramente:

```text
¿Qué genera o inicia?
¿Para qué tipo de proyecto?
¿Qué incluye?
¿Qué no incluye?
¿Qué debe cambiar el consumidor?
¿Qué requisitos previos tiene?
¿Cómo se inicializa?
¿Cómo se valida?
¿Cómo se empieza a trabajar?
¿Cómo se actualiza o evoluciona?
```

Si alguna respuesta no aplica, debe quedar implícita o explícitamente justificada por la simplicidad del proyecto.

---

# 7. Aplicación de Q1 — Conformidad con el contrato

**Máximo definido en QUALITY_SCORE: 12 puntos**

---

## Q1.1 — Propósito y alcance claramente definidos

**Máximo: 3 puntos**

Para puntuación completa debe poder determinarse:

* para qué sirve el template;
* qué tipo de proyecto genera o soporta;
* tecnologías o ecosistemas relevantes;
* precondiciones;
* principales capacidades incluidas;
* limitaciones relevantes.

No es obligatorio concentrar toda la información en un único archivo.

Debe existir una fuente claramente localizable.

### Evidencia posible

* `README.md`
* documentación de arquitectura;
* documentación inicial;
* manifiestos;
* configuración;
* descripción del repositorio.

### Pérdida típica de puntos

* propósito ambiguo;
* alcance demasiado genérico;
* capacidades prometidas no delimitadas;
* ausencia de restricciones importantes.

---

## Q1.2 — Capacidades prometidas realmente presentes

**Máximo: 3 puntos**

Toda capacidad anunciada como incorporada debe existir realmente.

Ejemplos:

Si el template promete:

```text
CI
tests
versionado
agentes
documentación
seguridad
bootstrap
```

debe existir evidencia correspondiente.

No se exige ninguna de estas capacidades si el template no las necesita y el estándar no las requiere para su contexto.

### Fallos típicos

* README promete CI pero workflow inexistente;
* documentación anuncia tests que no se ejecutan;
* se documenta automatización que ya fue eliminada;
* se promete soporte de una herramienta sin configuración real.

---

## Q1.3 — Coherencia entre fuentes

**Máximo: 3 puntos**

Debe existir coherencia entre:

```text
README
AGENTS
ROADMAP
documentación
scripts
workflows
configuración
comportamiento
```

cuando existan.

Especial atención a:

* comandos distintos para la misma operación;
* políticas contradictorias;
* nombres de ramas inconsistentes;
* versiones distintas;
* agentes con reglas divergentes;
* documentación heredada.

---

## Q1.4 — Ausencia de requisitos obligatorios incompletos

**Máximo: 3 puntos**

Un template considerado estable no debe contener capacidades fundamentales declaradas como terminadas pero realmente incompletas.

Debe distinguirse claramente entre:

```text
estable
experimental
opcional
planificado
deprecated
```

Un elemento futuro correctamente identificado en ROADMAP no constituye por sí mismo un defecto.

---

# 8. Aplicación de Q2 — Reutilización y limpieza

**Máximo: 12 puntos**

Esta área es especialmente crítica para TEMPLATE.

---

## Q2.1 — Inicialización reproducible

**Máximo: 3 puntos**

El auditor debe intentar reproducir el camino normal de adopción.

Idealmente:

```text
estado limpio
→ inicialización
→ configuración mínima
→ instalación
→ validación
→ proyecto listo
```

Para puntuación completa:

* pasos claros;
* sin conocimiento oculto;
* sin modificaciones improvisadas;
* sin depender de archivos locales no incluidos;
* sin errores relevantes.

### Evidencia fuerte

* bootstrap ejecutado;
* instalación completada;
* suite de validación pasando;
* nuevo proyecto generado correctamente.

---

## Q2.2 — Ausencia de residuos específicos del origen

**Máximo: 3 puntos**

Debe buscarse activamente información accidental perteneciente al proyecto desde el cual se creó el template.

Buscar razonablemente:

```text
nombres de clientes
nombres personales
IDs
URLs privadas
rutas locales
nombres de máquinas
usuarios
emails internos
tokens
credenciales
bases de datos reales
dominios internos
nombres de proyectos anteriores
comentarios históricos irrelevantes
workarounds específicos
artefactos temporales
logs
backups
outputs
```

### Excepciones válidas

Ejemplos genéricos claramente intencionales no son residuos.

Ejemplo válido:

```text
example@example.com
example-project
your-company
```

si están definidos como placeholders.

Tampoco debe considerarse residuo automáticamente una referencia histórica o
ambiental conservada deliberadamente como evidencia, troubleshooting o trazabilidad,
si:

* está claramente contextualizada;
* no contiene secretos;
* no se propaga al proyecto generado;
* no induce al consumidor a configuraciones incorrectas;
* su conservación aporta valor verificable.

La evaluación debe centrarse en el riesgo real de contaminación del template,
no en la mera existencia de nombres o rutas históricas dentro de evidencia legítima.

---

## Q2.3 — Configuración y personalización claras

**Máximo: 3 puntos**

Debe poder determinarse qué elementos tiene que cambiar el consumidor.

Preferentemente debe diferenciarse:

```text
OBLIGATORIO CAMBIAR
OPCIONAL
NO MODIFICAR
GENERADO AUTOMÁTICAMENTE
```

No se exige necesariamente un archivo específico de variables.

El mecanismo debe ser adecuado al ecosistema.

### Problemas frecuentes

* valores reales mezclados con placeholders;
* configuración distribuida sin orientación;
* mismos valores repetidos en múltiples archivos;
* parámetros esenciales escondidos.

---

## Q2.4 — Portabilidad y extensibilidad

**Máximo: 3 puntos**

Debe evitarse dependencia accidental de:

```text
D:\...
C:\Users\...
/home/nombre...
máquina concreta
editor concreto
shell concreto
estado local oculto
cuentas personales
```

salvo que el template esté explícitamente diseñado para ese entorno.

Si existe una dependencia obligatoria de plataforma debe estar documentada.

La portabilidad significa adecuación al alcance declarado, no necesariamente compatibilidad universal.

Un template no pierde puntos por utilizar de forma intencional una plataforma,
sistema operativo, shell o proveedor específico cuando:

* forma parte del alcance declarado;
* la decisión es técnicamente coherente;
* los prerrequisitos están documentados;
* el flujo prometido es reproducible dentro del entorno soportado;
* no existe una promesa contradictoria de compatibilidad más amplia.

Ejemplo:

```text
Template Windows + PowerShell
```

puede obtener puntuación completa si funciona correctamente en ese alcance.

Sí debe penalizarse la dependencia accidental de una máquina, usuario, ruta local,
configuración oculta o entorno no declarado.

---

# 9. Prueba de contaminación del template

Durante Q2 debe realizarse una revisión específica buscando contaminación del proyecto origen.

La auditoría debe responder:

```text
¿Existe información que no debería propagarse a cada proyecto nuevo?
```

Clasificar resultados:

* funcional y necesario;
* placeholder;
* ejemplo;
* residual;
* privado;
* obsoleto;
* no determinado.

Un template con secretos reales expuestos activa además los criterios y gates de seguridad correspondientes.

---

# 10. Prueba de creación limpia

Siempre que sea seguro y razonablemente posible debe probarse el template desde un estado equivalente a un consumidor nuevo.

La prueba ideal no debe beneficiarse de:

* dependencias ya instaladas accidentalmente;
* configuración personal no documentada;
* archivos ignorados presentes;
* variables de entorno desconocidas;
* cachés esenciales;
* herramientas globales no declaradas.

Cuando no pueda aislarse completamente el entorno, debe indicarse la limitación.

---

# 11. Aplicación de Q3 — Arquitectura y mantenibilidad

**Máximo: 12 puntos**

---

## Q3.1 — Estructura coherente

**Máximo: 3 puntos**

La estructura debe permitir reconocer razonablemente:

```text
código
configuración
documentación
tests
scripts
automatización
infraestructura
agentes
```

cuando dichos elementos existan.

No se exige una organización universal.

Debe evaluarse:

* consistencia;
* navegabilidad;
* claridad;
* ausencia de ubicaciones arbitrarias.

---

## Q3.2 — Separación de responsabilidades

**Máximo: 3 puntos**

La lógica común no debe encontrarse innecesariamente mezclada con configuración específica de herramientas.

Ejemplo:

Si varios agentes necesitan la misma regla:

preferir una fuente compartida y adaptadores pequeños cuando técnicamente sea viable.

Evitar que cada ecosistema mantenga manualmente copias completas divergentes.

---

## Q3.3 — Simplicidad y duplicación

**Máximo: 3 puntos**

Un template debe minimizar el costo que transfiere a todos sus descendientes.

Por ello esta área debe analizar especialmente:

* archivos redundantes;
* configuraciones repetidas;
* dependencias no utilizadas;
* agentes innecesarios;
* scripts superpuestos;
* documentación duplicada;
* herramientas con funciones equivalentes;
* capas arquitectónicas preventivas sin uso real.

### Principio

> Todo elemento innecesario del template se multiplica por cada proyecto creado desde él.

Por eso la complejidad accidental tiene especial impacto.

---

## Q3.4 — Evolución

**Máximo: 3 puntos**

Debe ser posible modificar el template sin tener que actualizar manualmente muchas copias internas de la misma regla.

Evaluar:

* centralización;
* modularidad;
* convenciones;
* versionado;
* extensión;
* dependencias;
* fuentes únicas de verdad.

---

# 12. Fuente única de verdad

El auditor debe identificar reglas conceptualmente compartidas.

Ejemplos:

```text
política Git
flujo de agentes
convenciones
quality gates
workflow de desarrollo
reglas de documentación
criterios de cierre
```

Debe determinarse si existe:

```text
SOURCE OF TRUTH
```

o múltiples fuentes manuales.

La existencia de archivos específicos para distintas herramientas no constituye automáticamente duplicación.

Debe analizarse si son:

* adaptadores;
* imports;
* referencias;
* copias independientes.

---

# 13. Adaptadores por herramienta

Un patrón favorable cuando es técnicamente viable:

```text
regla central
   ↓
adaptador Claude
adaptador Codex
adaptador OpenCode
```

Un patrón de riesgo:

```text
Claude → 500 líneas de reglas
Codex  → copia manual
OpenCode → otra copia manual
```

si las tres deberían mantenerse sincronizadas.

No debe forzarse centralización cuando la herramienta no la soporte adecuadamente.

---

# 14. Aplicación de Q4 — Documentación y Developer Experience

**Máximo: 12 puntos**

---

## Q4.1 — README funcional

**Máximo: 3 puntos**

Un consumidor nuevo debería comprender rápidamente:

```text
qué es
para qué sirve
cómo empezar
requisitos
flujo inicial
dónde profundizar
```

El README no debe intentar necesariamente contener toda la documentación.

Debe funcionar como punto de entrada.

---

## Q4.2 — Instalación y bootstrap

**Máximo: 3 puntos**

Debe documentarse el proceso real.

Idealmente debe existir una ruta única o claramente recomendada.

Evitar situaciones como:

```text
README dice A
script hace B
CI utiliza C
autor utiliza D
```

sin explicación.

---

## Q4.3 — Operaciones habituales

**Máximo: 2 puntos**

Según corresponda deben ser localizables comandos o mecanismos para:

```text
inicializar
desarrollar
validar
probar
construir
actualizar
versionar
liberar
```

No todas las operaciones son obligatorias para todos los templates.

---

## Q4.4 — Convenciones de contribución

**Máximo: 2 puntos**

Debe quedar razonablemente claro cómo se modifica el template sin degradarlo.

Puede incluir:

* flujo Git;
* ramas;
* PR;
* tests;
* calidad;
* documentación;
* agentes;
* criterios de cierre.

No se exige `CONTRIBUTING.md` si existe otra fuente adecuada.

---

## Q4.5 — Ejemplos y troubleshooting

**Máximo: 2 puntos**

Debe existir orientación proporcional a la complejidad.

Un template simple puede necesitar muy poco troubleshooting.

Uno complejo debería cubrir errores previsibles.

No debe premiarse documentación especulativa de errores nunca observados.

---

# 15. Documentación autoritativa versus explicativa

El auditor debe identificar qué documentos contienen reglas obligatorias.

Ejemplo:

```text
AGENTS.md → normativa operativa
README.md → introducción
docs/... → explicación ampliada
```

Debe evitarse que varios documentos parezcan simultáneamente fuentes autoritativas y contengan reglas distintas.

---

# 16. Aplicación de Q5 — Calidad, pruebas y regresión

**Máximo: 16 puntos**

---

## Q5.1 — Controles automáticos

**Máximo: 3 puntos**

El template debe incluir controles proporcionales a las tecnologías que genera o incorpora.

Ejemplos:

```text
lint
format check
typecheck
schema validation
markdown lint
shell lint
config validation
static analysis
```

No deben agregarse controles sin valor sólo para puntuar.

La ausencia de una herramienta concreta, por ejemplo:

```text
PSScriptAnalyzer
markdownlint
ShellCheck
Dependabot
```

no constituye por sí sola un defecto.

Para descontar puntos debe demostrarse que existe una necesidad real de control
no cubierta por mecanismos equivalentes o que el propio contrato exige ese control.

El auditor debe evaluar la cobertura efectiva del riesgo, no una checklist de herramientas.

---

## Q5.2 — Estrategia de pruebas

**Máximo: 3 puntos**

La auditoría debe responder:

> ¿Qué podría romperse en el template y cómo se detectaría?

Posibles pruebas:

* unitarias;
* integración;
* generación;
* bootstrap;
* smoke;
* estructura;
* contrato;
* regresión;
* end-to-end.

Para un template, una prueba de generación/bootstrap puede ser más valiosa que cientos de pruebas unitarias.

---

## Q5.3 — Tests ejecutables y pasando

**Máximo: 4 puntos**

Las verificaciones críticas deben:

* poder ejecutarse;
* producir exit code significativo;
* fallar cuando corresponde;
* pasar en el estado auditado.

Debe comprobarse, cuando sea viable:

```text
comando oficial
→ ejecución
→ resultado
```

---

## Q5.4 — Protección frente a regresiones

**Máximo: 3 puntos**

Los defectos importantes ya corregidos deberían transformarse en controles permanentes cuando sea razonable.

Ejemplo:

Si anteriormente el template olvidaba actualizar un elemento crítico durante el cierre:

una validación automatizada que impida repetirlo constituye evidencia positiva de madurez.

No es obligatorio crear regresión para cada bug trivial.

---

## Q5.5 — Quality Gates

**Máximo: 3 puntos**

Los controles críticos deben ejecutarse antes de considerar válido un cambio.

Idealmente:

```text
cambio
→ quality
→ tests
→ revisión
→ integración
```

Debe evaluarse tanto la automatización como el enforcement cuando corresponda.

---

# 17. Tests específicos recomendables para templates

No son obligatorios universalmente.

El auditor debe considerar si serían relevantes:

### Smoke test del template

Comprueba que la estructura mínima funciona.

### Bootstrap test

Comprueba instalación/inicialización limpia.

### Generation test

Si existe generador, comprueba que produce un proyecto válido.

### Contract test

Comprueba archivos o capacidades obligatorias.

### Regression test

Protege errores históricos importantes.

### Example project test

Genera un proyecto ejemplo y ejecuta sus validaciones.

La selección debe ser proporcional al riesgo.

---

# 18. No premiar tests cosméticos

Ejemplo de bajo valor:

```text
test que sólo comprueba que README existe
```

si el README vacío también pasa.

Ejemplo de mayor valor:

```text
generar proyecto
→ instalar
→ ejecutar validation suite
→ resultado PASS
```

El auditor debe valorar efectividad.

---

# 19. Aplicación de Q6 — Git, CI/CD, versionado y releases

**Máximo: 16 puntos**

---

## Q6.1 — Estrategia Git

**Máximo: 3 puntos**

Debe existir una estrategia coherente.

Puede ser:

```text
trunk-based
GitHub Flow
GitFlow adaptado
develop + feature branches
otra estrategia documentada
```

No se penaliza una estrategia por no coincidir con preferencias del auditor.

Debe evaluarse:

* coherencia;
* enforcement;
* simplicidad;
* adecuación.

---

## Q6.2 — Protección e integración

**Máximo: 3 puntos**

Cuando exista plataforma compatible debe comprobarse, si hay acceso:

* branch protection;
* required checks;
* reviews;
* restricciones de push;
* force push;
* borrado;
* reglas relevantes.

Un template que prescribe reglas para futuros proyectos debe distinguir entre:

```text
configuración que vive en el repositorio
```

y:

```text
configuración que debe aplicar el consumidor
```

Si no puede automatizarse, debe documentarse claramente.

La puntuación debe centrarse en el **objetivo de control de integración**, no en
exigir una funcionalidad comercial concreta del proveedor.

Si la protección nativa de ramas no está disponible por limitaciones del plan,
puede aceptarse un control técnico alternativo suficientemente equivalente,
siempre que sea:

* verificable;
* difícil de omitir accidentalmente;
* coherente con el flujo declarado;
* capaz de detectar o impedir integraciones no autorizadas cuando corresponda.

Una regla exclusivamente documental o basada sólo en disciplina humana no equivale
a enforcement técnico completo.

No debe convertirse automáticamente en requisito para 100/100:

* pagar un plan superior;
* hacer público el repositorio;
* migrar de proveedor;

si el objetivo de control puede satisfacerse profesionalmente por otro mecanismo.

---

# 20. Configuración GitHub no portable automáticamente

El auditor debe reconocer que determinados controles de plataforma no se copian necesariamente al crear un repositorio desde un template.

Ejemplos:

* branch protection;
* rulesets;
* secrets;
* environments;
* permisos;
* settings.

Si son obligatorios para el contrato del template debe existir un mecanismo razonable para:

* automatizarlos;
* validarlos;
* documentarlos;
* o guiar explícitamente su aplicación.

No debe asumirse que se heredan.

Cuando un control remoto no pueda aplicarse por una limitación externa del proveedor,
el auditor debe evaluar primero si existe un mecanismo alternativo que satisfaga el
mismo objetivo antes de descontar puntos por la ausencia del control nativo.

---

## Q6.3 — CI reproducible

**Máximo: 3 puntos**

La CI debe representar las validaciones reales del proyecto.

Evitar divergencia:

```text
local validate ≠ CI validate
```

cuando deberían comprobar lo mismo.

Patrón favorable:

```text
script común
↓
local
CI
agentes
```

cuando sea viable.

---

## Q6.4 — Versionado y releases

**Máximo: 3 puntos**

Un template reutilizado por múltiples proyectos debería disponer de una forma de identificar estados estables cuando su contexto lo requiera.

Puede incluir:

```text
SemVer
tags
GitHub Releases
CHANGELOG
release notes
```

No se exige obligatoriamente SemVer si otro mecanismo es más apropiado.

Debe poder responderse:

> ¿Qué versión del template utilicé?

cuando la trazabilidad sea relevante.

Debe distinguirse entre:

### Capacidad actual y obligatoria

Si el template declara que el flujo de release/versionado ya forma parte de su
operación actual, la puntuación completa requiere evidencia proporcional de que
ese flujo fue ejercido realmente cuando sea seguro y razonablemente verificable.

Si nunca se ejecutó y por ello no puede demostrarse su funcionamiento, la pérdida
de puntos debe asociarse explícitamente a Q6.4 mediante un hallazgo puntuable.

No puede clasificarse simultáneamente como `SUGGESTION`.

### Capacidad futura o prospectiva

Si el release está documentado como mecanismo previsto para una etapa futura,
ROADMAP o primera liberación aún no realizada, su ausencia de ejecución no debe
penalizar automáticamente el estado actual.

El auditor debe evaluar el contrato real, no anticipar obligaciones futuras.

---

## Q6.5 — Build y artefactos

**Máximo: 2 puntos**

Aplica cuando el template produce:

* paquetes;
* imágenes;
* binarios;
* documentación compilada;
* generadores;
* otros artefactos.

Si no produce artefactos puede declararse N/A justificadamente.

---

## Q6.6 — Compatibilidad, actualización y rollback

**Máximo: 2 puntos**

Para templates debe interpretarse principalmente como:

```text
¿Cómo evolucionan proyectos creados anteriormente?
```

No todos los templates prometen actualización automática.

Debe identificarse el modelo:

### Snapshot

El proyecto se crea y luego evoluciona independientemente.

### Updatable template

Los proyectos pueden sincronizar cambios posteriores.

### Generator versionado

Puede regenerar o migrar proyectos.

### Managed framework

La base permanece vinculada.

La estrategia elegida debe estar suficientemente clara para que el consumidor
entienda qué ocurre después de crear el proyecto.

No es obligatorio utilizar literalmente las etiquetas:

```text
snapshot
updatable
generator
managed
```

si el comportamiento y las expectativas de actualización ya quedan inequívocamente
definidos por la documentación y el mecanismo real.

Si es `snapshot`, explícita o inequívocamente por contrato, no debe penalizarse
la ausencia de sincronización futura.

---

# 21. ROADMAP del template

Si existe ROADMAP debe diferenciar:

* mejoras del propio template;
* capacidades obligatorias de la versión actual;
* ideas futuras.

El auditor debe revisar que los elementos marcados como terminados no contradigan la implementación.

Un ROADMAP no es obligatorio para todos los templates.

---

# 22. Cierre de trabajo

Cuando el template define un proceso de features, etapas o milestones, debe comprobarse si existe una definición clara de terminado.

Puede incluir:

```text
código
tests
review
evidencia
documentación
ROADMAP
PR
merge
release
```

según el flujo definido.

Los pasos críticos no deben depender únicamente de memoria humana si el template promete automatización.

---

# 23. Aplicación de Q7 — Seguridad y software supply chain

**Máximo: 12 puntos**

---

## Q7.1 — Gestión de secretos

**Máximo: 3 puntos**

Un template tiene un riesgo particular:

> cualquier secreto incluido puede propagarse a todos los proyectos generados.

Debe buscarse activamente:

```text
API keys
tokens
passwords
private keys
connection strings
credentials
certificados privados
cookies
```

Los ejemplos deben utilizar valores claramente ficticios.

---

# 24. Archivos de entorno

Cuando existan archivos como:

```text
.env
.env.example
.env.template
```

debe comprobarse:

* si secretos reales están ignorados;
* si ejemplos no contienen credenciales válidas;
* si variables obligatorias están documentadas;
* si no existe duplicación contradictoria.

No se exige `.env` como patrón universal.

---

## Q7.2 — Dependencias

**Máximo: 2 puntos**

Debe comprobarse razonablemente:

* dependencias necesarias;
* dependencias no utilizadas;
* pinning cuando corresponda;
* lockfiles cuando aporten reproducibilidad real;
* proceso de actualización;
* vulnerabilidades relevantes.

Un template no debe transmitir dependencias innecesarias a todos sus consumidores.

La ausencia de:

```text
lockfile
Dependabot
Renovate
bot equivalente
```

no constituye por sí sola un defecto.

Para descontar puntos debe existir un riesgo objetivo no cubierto por otro mecanismo
razonable de mantenimiento, reproducibilidad o actualización.

---

## Q7.3 — Seguridad de CI/CD

**Máximo: 2 puntos**

Revisar cuando corresponda:

* permisos;
* tokens;
* actions externas;
* referencias mutables;
* ejecución de código no confiable;
* secretos en forks/PR;
* privilegios.

No todos los riesgos aplican a todos los workflows.

---

## Q7.4 — Defaults seguros

**Máximo: 2 puntos**

Los valores por defecto no deben inducir:

```text
debug inseguro
credenciales triviales reales
autenticación deshabilitada
permisos excesivos
servicios públicos accidentalmente
configuraciones destructivas
```

cuando sean relevantes.

Ejemplos locales claramente documentados pueden aceptarse si no generan un riesgo razonable.

---

## Q7.5 — Supply chain y cumplimiento

**Máximo: 3 puntos**

Evaluar según el contexto:

```text
LICENSE
dependency integrity
action pinning
SBOM
provenance
artifact signing
package signing
renovation/dependabot
security policy
```

No todos son obligatorios.

La selección debe basarse en exposición, distribución y riesgo.

---

# 25. Licencia

Para templates destinados a distribución externa debe estar claro bajo qué condiciones pueden reutilizarse.

La ausencia de licencia puede ser relevante si genera incertidumbre real sobre reutilización.

Para un repositorio estrictamente interno, privado o personal que no promete
redistribución externa, la ausencia de `LICENSE` no constituye por sí sola un defecto
ni debe restar puntos automáticamente.

Sólo debe penalizarse cuando:

* el contrato exige una licencia;
* existe distribución externa o pública;
* los consumidores necesitan derechos claros de reutilización;
* existe una incertidumbre jurídica material dentro del alcance auditado.

El auditor debe evaluar el riesgo concreto, no la mera ausencia del archivo.

---

# 26. Aplicación de Q8 — Automatización y gobernanza

**Máximo: 8 puntos**

Esta área debe activarse completamente cuando el template incluya agentes, automatizaciones de desarrollo o reglas de gobernanza.

Cuando no existan, debe evaluarse la aplicabilidad conforme a `QUALITY_SCORE.md`.

---

## Q8.1 — Fuente única de verdad

**Máximo: 2 puntos**

Las instrucciones comunes deberían residir en una fuente principal cuando sea técnicamente viable.

Ejemplos:

```text
AGENTS.md
rules/
policies/
shared configuration
```

Herramientas específicas pueden tener archivos adaptadores.

Debe evitarse sincronización manual innecesaria.

---

## Q8.2 — Responsabilidades y límites

**Máximo: 2 puntos**

Cuando existan agentes debe poder determinarse:

```text
rol
entrada
salida
responsabilidad
límites
herramientas permitidas
condiciones de escalamiento
HITL
```

Evitar superposición ambigua entre agentes.

---

## Q8.3 — Fail-safe

**Máximo: 2 puntos**

Las automatizaciones críticas deben distinguir:

```text
PASS
FAIL
NO VERIFICADO
REQUIERE HITL
```

No deben convertir fallos en éxito silencioso.

Si una etapa crítica falla, el flujo debe detenerse o escalar según el diseño.

---

## Q8.4 — Trazabilidad

**Máximo: 2 puntos**

Cuando el template define un circuito de trabajo debe poder reconstruirse razonablemente:

```text
requisito
→ planificación
→ implementación
→ validación
→ review
→ integración
→ cierre
→ release
```

No todos los pasos necesitan una herramienta diferente.

---

# 27. Evaluación específica de agentes múltiples

Cuando el mismo template soporte, por ejemplo:

```text
Claude Code
Codex
OpenCode
otros
```

debe analizarse:

1. qué reglas son comunes;
2. qué reglas son específicas;
3. cuáles están duplicadas;
4. cómo se evita divergencia;
5. si todos producen resultados equivalentes;
6. si existe una fuente autoritativa.

No se exige que las estructuras sean idénticas si cada herramienta tiene requisitos distintos.

---

# 28. Skills

Si el template utiliza skills, plugins, MCP o mecanismos equivalentes, el auditor debe verificar:

* finalidad;
* necesidad;
* ubicación;
* alcance local/global;
* documentación;
* instalación;
* versiones cuando sea relevante;
* duplicación;
* permisos;
* comportamiento si falta la skill.

No deben instalarse skills simplemente para aparentar sofisticación.

---

# 29. MCP y herramientas externas

Cuando existan integraciones externas:

* deben tener propósito claro;
* evitar credenciales embebidas;
* disponer de configuración reproducible;
* manejar ausencia o error;
* documentar requisitos.

No se exige que todos los consumidores utilicen todas las integraciones si son opcionales.

---

# 30. Configuración multi-agente

Debe revisarse especialmente el riesgo:

```text
regla común cambia
→ un ecosistema se actualiza
→ otro queda desactualizado
```

Si existe este riesgo y no hay mecanismo de control, puede afectar:

* Q3.3;
* Q3.4;
* Q8.1;
* Q8.4.

Debe aplicarse la regla contra doble penalización.

---

# 31. HITL en templates agénticos

Si el flujo declara decisiones humanas obligatorias, debe estar claro:

```text
cuándo se detiene
qué evidencia se presenta
quién decide
qué resultado permite continuar
```

Especial atención a:

* merge;
* release;
* cambios destructivos;
* seguridad;
* decisiones arquitectónicas;
* cierre de etapa.

El diseño debe ser proporcional al riesgo.

---

# 32. Auditoría de archivos fundamentales

El auditor debe identificar archivos fundamentales del template.

No existe una lista universal obligatoria.

Posibles ejemplos:

```text
README.md
AGENTS.md
ROADMAP.md
CONTRIBUTING.md
LICENSE
CHANGELOG.md
CLAUDE.md
opencode.json
.codex/
.claude/
.github/
docs/
scripts/
tests/
```

La evaluación debe basarse en función, no en nombre.

---

# 33. Archivos obligatorios declarados

Si el propio template establece que determinados archivos son obligatorios, entonces pasan a formar parte de su contrato.

Ejemplo:

Si afirma:

```text
Todo proyecto generado debe contener AGENTS.md
```

el auditor debe comprobarlo.

No debe imponer ese requisito a templates que no lo declaren.

---

# 34. Placeholders

Los placeholders deben ser:

* identificables;
* consistentes;
* no ambiguos;
* fáciles de localizar cuando deban cambiarse.

Ejemplos:

```text
{{PROJECT_NAME}}
<PROJECT_NAME>
YOUR_COMPANY
example-project
```

Evitar placeholders que parezcan valores reales.

---

# 35. Búsqueda de valores hardcoded

Debe realizarse una búsqueda razonable de:

* nombres;
* rutas;
* dominios;
* IDs;
* cuentas;
* puertos específicos;
* credenciales;
* proyectos históricos.

Un hardcode no es automáticamente incorrecto.

Debe determinarse si representa:

```text
convención del template
default válido
ejemplo
residuo
configuración que debería parametrizarse
```

---

# 36. Archivos ignorados

Revisar `.gitignore` o equivalente cuando aplique.

Debe evitarse versionar accidentalmente:

* secretos;
* caches;
* builds;
* archivos locales;
* IDE state;
* logs;
* temporales.

No se debe ignorar indiscriminadamente archivos que deberían quedar bajo control de versiones.

---

# 37. Estado limpio del repositorio

Para releases o estados declarados estables se espera normalmente:

```text
working tree limpio
```

cuando se evalúa el commit publicado.

Cambios locales del auditor no deben atribuirse al template.

Si el repositorio base se distribuye con artefactos accidentales versionados, sí deben evaluarse.

---

# 38. Dependencia del autor original

Una prueba conceptual fundamental:

> ¿Un desarrollador competente que nunca habló con el creador puede utilizar correctamente el template?

Si la respuesta depende de:

```text
“debe saber que...”
“normalmente yo hago...”
“ese archivo no se toca aunque no diga nada...”
```

existe conocimiento tribal.

Debe evaluarse su impacto.

---

# 39. Dependencia de conversación previa

Un template profesional no debe requerir acceso a conversaciones históricas con una IA o con su autor para comprender reglas esenciales.

El repositorio debe contener las fuentes necesarias para operar.

Conversaciones externas pueden aportar contexto, no ser una dependencia operacional obligatoria.

---

# 40. Neutralidad frente a IA

Si el template soporta desarrollo asistido por IA, debe seguir siendo auditable mediante artefactos concretos.

No deben aceptarse como evidencia:

```text
“el agente ya sabe esto”
“está en la memoria del modelo”
“se explicó en otro chat”
```

Las reglas críticas deben vivir en fuentes persistentes cuando sean necesarias para operar.

---

# 41. Herramientas opcionales

Debe diferenciarse claramente:

```text
REQUERIDA
RECOMENDADA
OPCIONAL
```

Una herramienta opcional ausente no debe impedir utilizar el template salvo que se haya convertido en dependencia real.

---

# 42. Vendor lock-in

No debe penalizarse automáticamente el uso de una plataforma específica.

Debe evaluarse si:

* es decisión consciente;
* está documentada;
* afecta portabilidad;
* contradice el propósito declarado;
* existen dependencias innecesarias.

Un template diseñado explícitamente para GitHub puede depender de GitHub.

---

# 43. Compatibilidad de plataformas

No se exige soporte:

```text
Windows
Linux
macOS
```

simultáneamente.

Debe verificarse compatibilidad con las plataformas declaradas.

Si el template se presenta como multiplataforma, debe existir evidencia proporcional.

---

# 44. Shell y scripts

Si se proporcionan scripts:

* deben usar intérprete claramente soportado;
* evitar rutas accidentales;
* fallar correctamente;
* documentar prerrequisitos;
* evitar efectos destructivos innecesarios.

Si existen variantes PowerShell/Bash debe revisarse consistencia.

---

# 45. Bootstrap

Un bootstrap ideal debe ser:

* idempotente cuando sea razonable;
* claro;
* seguro;
* verificable;
* poco dependiente del estado previo.

No se exige un único script.

Puede ser una secuencia documentada.

---

# 46. Idempotencia

No todos los comandos deben ser idempotentes.

Debe exigirse principalmente cuando el usuario razonablemente pueda repetirlos.

Ejemplo:

```text
setup
bootstrap
install
configure
```

Si una segunda ejecución rompe el proyecto sin advertencia, puede existir un defecto.

---

# 47. Defaults

Los defaults deben optimizar:

* seguridad;
* facilidad de inicio;
* baja sorpresa;
* mantenibilidad.

No deben ocultar decisiones importantes que el consumidor debería tomar conscientemente.

---

# 48. Ejemplos incluidos

Los ejemplos deben:

* funcionar cuando corresponda;
* estar claramente identificados;
* no confundirse con configuración productiva;
* no contener datos sensibles;
* no quedar obsoletos respecto al template.

---

# 49. Proyecto ejemplo

En templates complejos puede ser favorable disponer de un proyecto ejemplo o fixture de referencia.

No es obligatorio universalmente.

Debe justificarse por costo/beneficio.

---

# 50. Actualización de dependencias

Debe existir algún mecanismo razonable para evitar que el template quede congelado indefinidamente con dependencias obsoletas **cuando el riesgo lo justifique**.

Puede ser:

```text
manual documentado
bot automatizado
revisión periódica
release process
```

No se exige una herramienta concreta.

La ausencia de un bot de actualización no debe penalizarse si:

* la superficie de dependencias es pequeña;
* existe mantenimiento manual razonable;
* no hay evidencia de obsolescencia o vulnerabilidad relevante;
* el contrato no exige automatización.

La evaluación debe basarse en riesgo y mantenibilidad reales.

---

# 51. Versionado del propio template

Cuando el template tenga consumidores múltiples o evolución continua, se recomienda fuertemente poder identificar su versión.

El auditor debe distinguir:

```text
versión del template
```

de:

```text
versión de los proyectos generados
```

No deben confundirse.

---

# 52. Release estable

Si existe rama o versión declarada estable:

debe representar un estado listo para consumo.

No debería contener:

* features incompletas no marcadas;
* pruebas críticas fallando;
* documentación contradictoria;
* residuos temporales.

---

# 53. Estrategia develop/main

Si el template utiliza:

```text
develop → línea de trabajo
main → releases estables
```

debe evaluarse:

* coherencia;
* protección;
* PR/merge;
* versionado;
* tags;
* release;
* sincronización posterior cuando corresponda.

No se exige esta estrategia a otros templates.

---

# 54. Tags

Si se utiliza SemVer:

```text
vMAJOR.MINOR.PATCH
```

debe aplicarse de manera coherente.

El auditor debe comprobar cuando sea posible:

* existencia;
* orden;
* correspondencia con releases;
* documentación.

No debe exigirse SemVer cuando no corresponda.

---

# 55. Changelog

Un changelog puede ser valioso para templates versionados.

No siempre es obligatorio.

Debe evaluarse si los consumidores necesitan comprender diferencias entre versiones.

Puede resolverse mediante:

* `CHANGELOG.md`;
* release notes;
* mecanismo equivalente.

---

# 56. Auditoría de upgrade

Si el template promete actualizar proyectos existentes, esta capacidad debe probarse explícitamente.

Debe comprobarse:

```text
proyecto versión anterior
→ upgrade
→ validaciones
→ resultado
```

Una promesa de actualización sin mecanismo probado es una deficiencia importante.

---

# 57. Snapshot templates

Si el modelo es snapshot:

```text
crear proyecto
→ independizarse del template
```

debe estar suficientemente claro para el consumidor.

No es obligatorio que el repositorio utilice la palabra `snapshot` si la mecánica
de adopción y la ausencia de sincronización posterior están inequívocamente descritas.

No debe exigirse capacidad de upgrade posterior.

---

# 58. Documentación específica de IA

Si el template soporta agentes IA, las reglas deben ser suficientemente concretas para evitar:

* modificaciones fuera de alcance;
* bypass de quality gates;
* autoaprobación de operaciones humanas;
* cambios destructivos no autorizados;
* inconsistencias entre agentes.

---

# 59. Separación Builder / Reviewer

Si existe separación entre construcción y revisión, debe comprobarse que tenga efecto real.

Ejemplo favorable:

```text
Builder implementa
Reviewer inspecciona independientemente
HITL decide
```

Ejemplo débil:

```text
mismo agente implementa y declara que todo está perfecto
```

No se exige separación de agentes si el template no la necesita.

---

# 60. Code review

Si el template declara code review obligatorio debe evaluarse:

* responsable;
* alcance;
* criterios;
* evidencia;
* enforcement cuando corresponda.

Un archivo llamado `code-reviewer` no demuestra que haya revisión efectiva.

---

# 61. Auditoría de documentación agéntica duplicada

Buscar especialmente:

```text
AGENTS.md
CLAUDE.md
.codex/*
.claude/*
.opencode/*
rules/*
skills/*
```

Determinar si la duplicación es:

* requerida por herramientas;
* generada;
* referenciada;
* mantenida manualmente.

La duplicación manual divergente debe considerarse riesgo.

---

# 62. Archivos generados para agentes

Si existen archivos generados desde una fuente central:

debe comprobarse:

```text
fuente
→ generador
→ output
→ validación de sincronización
```

Un generador sin check de drift puede seguir permitiendo divergencias.

---

# 63. Drift

Cuando múltiples representaciones deban mantenerse sincronizadas, debe considerarse si existe una forma de detectar drift.

Ejemplo:

```text
validate-agent-config
```

No es obligatorio si la arquitectura evita el problema.

---

# 64. Reglas de workflow

El template debe identificar claramente qué operaciones son:

```text
automáticas
humanas
mixtas
```

especialmente en:

* merge;
* release;
* seguridad;
* decisiones arquitectónicas;
* cierre.

---

# 65. Auto-merge

No debe considerarse bueno o malo por sí mismo.

Debe evaluarse si:

* respeta quality gates;
* respeta reviews necesarias;
* está alineado con el riesgo;
* puede saltarse HITL obligatorio.

---

# 66. Evidencia de cierre

Si el template define un circuito agéntico, el cierre de una tarea importante debería producir evidencia proporcional.

Ejemplos:

```text
tests
review
diff
PR
estado CI
criterios de aceptación
```

No se exige un formato específico.

---

# 67. ROADMAP como estado

Si ROADMAP se utiliza como fuente de estado operativo:

debe existir coherencia entre:

```text
pendiente
en progreso
completado
```

y la realidad.

Si su actualización forma parte del contrato de cierre, debe verificarse.

---

# 68. Automatización del ROADMAP

No es obligatorio automatizar ROADMAP.

Pero si el template declara que su circuito lo actualiza automáticamente:

debe comprobarse que realmente ocurra.

Un cierre que deja el estado incorrecto constituye contradicción del contrato.

---

# 69. PR templates

Pueden aportar valor cuando el proceso necesita estandarización.

No son obligatorios por defecto.

Debe evaluarse si ayudan a garantizar:

* evidencia;
* tests;
* checklist;
* trazabilidad.

Un template vacío o ceremonial no aporta puntuación por sí solo.

---

# 70. Issue templates

Misma regla:

valorar función, no existencia.

---

# 71. CI como gate

Una CI útil debe detectar defectos relevantes.

Para puntuación máxima no basta con:

```text
workflow verde
```

si ninguna prueba significativa se ejecuta.

Debe poder responderse:

> ¿Qué clase de error impediría integrar este workflow?

---

# 72. CI local equivalente

Cuando sea viable, es favorable poder ejecutar localmente los mismos controles esenciales de CI.

Ejemplo:

```text
./validate
```

usado por:

```text
desarrollador
agente
CI
```

No debe forzarse si el costo supera el beneficio.

---

# 73. Versiones de tooling

Las herramientas críticas deben tener una estrategia razonable de versiones.

Evitar dependencia implícita de:

```text
“la última versión”
```

cuando cambios futuros puedan romper reproducibilidad.

La intensidad del pinning depende del ecosistema.

---

# 74. Configuración del editor

Configuraciones para IDE/editor:

* pueden incluirse;
* deben ser opcionales salvo necesidad real;
* no deben introducir dependencia innecesaria.

El template no debe dejar de funcionar porque el consumidor use otro editor salvo que sea parte explícita del producto.

---

# 75. Configuración local

Archivos específicos de cada desarrollador deben separarse de configuración compartida.

No deben versionarse valores personales innecesarios.

---

# 76. Datos de ejemplo

Deben ser:

* sintéticos;
* anonimizados;
* ficticios;
* legales para redistribución.

Especialmente importante si el template incluye fixtures.

---

# 77. Fixtures

Los fixtures deben ser deterministas cuando se utilicen para regresión.

Deben evitar depender de datos externos cambiantes salvo que el test esté diseñado explícitamente para ello.

---

# 78. Datasets

Si el template contiene datasets de regresión:

debe comprobarse:

* origen;
* privacidad;
* licencia;
* estabilidad;
* expected outputs;
* versionado.

---

# 79. Documentación de decisiones

ADRs u otros mecanismos pueden ser útiles para decisiones no obvias.

No son obligatorios por defecto.

Debe evitarse obligar a documentar decisiones triviales.

---

# 80. Arquitectura extensible

Un template debe facilitar cambios comunes sin requerir reestructuración completa.

No debe intentar anticipar todos los usos posibles.

Extensibilidad no equivale a abstracción máxima.

---

# 81. Feature flags

No son obligatorias en templates.

Sólo deben incluirse si el tipo de proyecto generado las necesita realmente.

---

# 82. Observabilidad

No es requisito universal del template.

Debe evaluarse si el template genera servicios desplegables que necesitan:

* logging;
* metrics;
* tracing;
* health checks.

Aplicar N/A cuando sea legítimo.

---

# 83. Bases de datos

Si el template incluye persistencia:

deben evaluarse:

* configuración;
* migraciones;
* datos de ejemplo;
* secretos;
* inicialización;
* rollback cuando aplique.

No aplica a templates sin persistencia.

---

# 84. Infraestructura

Si incluye IaC:

debe:

* validarse;
* evitar valores privados;
* separar entornos;
* manejar secretos;
* ser reproducible.

No se exige IaC a todo template.

---

# 85. Deploy

Si el template promete deploy:

debe comprobarse la capacidad.

No basta con incluir una carpeta `deploy/`.

---

# 86. Template especializado

Un template especializado no debe ser penalizado por no ser genérico.

Ejemplo:

```text
template exclusivo GeneXus
template exclusivo Python API
template exclusivo GitHub
```

puede obtener 100/100 si cumple completamente su alcance.

---

# 87. Template genérico

Un template que se presenta como genérico asume una exigencia mayor de neutralidad.

Debe evitar dependencias no declaradas de:

* lenguaje;
* plataforma;
* proveedor;
* workflow;
* sistema operativo.

---

# 88. Personalización post-copia

Debe minimizarse la cantidad de cambios manuales repetitivos.

Si el consumidor debe editar los mismos datos en diez archivos:

puede existir un problema de diseño.

Considerar centralización o automatización cuando sea proporcional.

---

# 89. Validación de placeholders restantes

Cuando el proceso de inicialización debe sustituir placeholders:

debe existir, si el riesgo lo justifica, una forma de detectar placeholders obligatorios no sustituidos.

Ejemplo:

```text
validate-template
```

que encuentre:

```text
{{PROJECT_NAME}}
TODO_PROJECT_NAME
```

restantes.

---

# 90. Archivos que deben conservarse

No todos los elementos del template deben personalizarse.

Debe quedar claro cuáles representan políticas comunes que deberían heredarse sin cambios.

---

# 91. Eliminación post-bootstrap

Algunos archivos pueden existir sólo para inicialización.

Si deben eliminarse después:

esto debe ser claro o automatizado.

No deberían quedar residuos de scaffolding innecesarios en el proyecto generado.

---

# 92. Comparación template → proyecto generado

Cuando sea posible, una auditoría profunda debe distinguir:

```text
calidad del repositorio template
```

de:

```text
calidad del proyecto generado
```

Ambas están relacionadas pero no son idénticas.

Un template puede estar ordenado y generar un proyecto roto.

Por eso la generación debe probarse cuando corresponda.

---

# 93. Prueba mínima del producto generado

Cuando el template genera un proyecto ejecutable, para puntuación máxima en los criterios correspondientes debe intentarse:

```text
generar
→ instalar
→ validar
→ ejecutar smoke test
```

si es seguro y técnicamente razonable.

---

# 94. Contaminación del framework de auditoría

La presencia de `.audit/` no debe otorgar puntos por sí misma.

El framework de auditoría:

```text
.audit/
```

sirve para medir el repositorio.

No constituye automáticamente evidencia de:

* buena arquitectura;
* buena documentación;
* buen testing;
* seguridad;
* gobernanza.

Sólo puede aportar evidencia si sus controles están realmente integrados al comportamiento del proyecto.

---

# 95. Prohibición de autoevaluación circular

No es evidencia válida:

```text
El template obtiene 100 porque QUALITY_SCORE dice que cumple.
```

La rúbrica define requisitos.

La evidencia debe provenir del proyecto auditado y de sus verificaciones.

---

# 96. Auditoría del propio framework

Si `.audit/` se distribuye como parte del template, también debe revisarse como contenido del repositorio:

* consistencia;
* mantenimiento;
* duplicación;
* impacto;
* seguridad;
* utilidad.

No obstante, no debe convertirse en una fuente artificial de puntos.

---

# 97. Hallazgos especialmente relevantes para TEMPLATE

Durante la auditoría debe realizarse una búsqueda explícita de:

```text
RESIDUO
HARDCODE
DUPLICACIÓN
DRIFT
CONTRADICCIÓN
KNOWLEDGE GAP
BOOTSTRAP FAILURE
QUALITY GATE BYPASS
SECRET
OBSOLETO
DEAD CONFIG
DEAD SCRIPT
NON-PORTABLE
FALSE SUCCESS
```

No todos deben existir.

Son categorías de riesgo características de templates.

---

# 98. Condiciones adicionales para TEMPLATE DE REFERENCIA

Además de `QUALITY_SCORE.md`, antes de otorgar `100/100` debe verificarse explícitamente:

```text
[ ] Adopción limpia reproducida
[ ] Sin residuos específicos conocidos
[ ] Sin secretos reales
[ ] Personalización obligatoria identificada
[ ] Contrato coherente
[ ] Validaciones críticas pasan
[ ] CI/gates aplicables verificados
[ ] Sin duplicación manual peligrosa conocida
[ ] Sin knowledge tribal crítico
[ ] Documentación suficiente para consumidor nuevo
[ ] Flujo Git/release coherente cuando aplica
[ ] Automatización agéntica coherente cuando aplica
[ ] Proyecto generado validado cuando aplica
```

Si una condición aplicable no puede verificarse:

`100/100 PROHIBIDO`

hasta disponer de evidencia suficiente.

Estas condiciones deben interpretarse conforme a `QUALITY_SCORE.md` y
`AUDIT_RULES.md`.

Una `SUGGESTION` nunca puede utilizarse para bloquear 100/100.

Si una condición de esta lista impide alcanzar 100/100, entonces debe corresponder
a un criterio aplicable que realmente pierde puntos o a una condición obligatoria
de evidencia/confianza definida por el estándar.

---

# 99. Preguntas finales obligatorias

Al finalizar la auditoría TEMPLATE el auditor debe poder responder:

### Reutilización

> ¿Puedo iniciar un nuevo proyecto desde aquí sin arrastrar residuos?

### Reproducibilidad

> ¿Otra persona puede repetir el proceso sin hablar con el autor?

### Calidad

> ¿Los errores importantes son detectados automáticamente?

### Gobernanza

> ¿Está claro cómo se trabaja y cómo se integra un cambio?

### Evolución

> ¿Puede mantenerse el template sin multiplicar inconsistencias?

### Seguridad

> ¿Es razonablemente seguro copiar esta base a nuevos proyectos?

### Evidencia

> ¿Puedo demostrar las respuestas anteriores?

---

# 100. Regla final del perfil TEMPLATE

Un template excelente no es el que más cosas contiene.

Es el que transfiere a cada proyecto nuevo:

* las decisiones correctas;
* los controles necesarios;
* la documentación suficiente;
* la menor complejidad accidental posible.

Toda deficiencia del template se multiplica por sus consumidores.

Toda buena decisión del template también.
