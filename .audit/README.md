# README.md

# Audit Framework

**Versión del framework:** 1.1
**Estado:** Activo

---

# 1. Propósito

La carpeta `.audit/` contiene el framework estándar utilizado para evaluar la calidad de este repositorio.

Su objetivo es permitir auditorías:

* reproducibles;
* matemáticas;
* basadas en evidencia;
* independientes del modelo o agente utilizado;
* comparables entre distintas ejecuciones;
* orientadas a detectar qué falta, qué sobra, qué está mal y qué debe corregirse para alcanzar el estándar objetivo.

Este framework no presupone que el repositorio sea correcto.

Su función es demostrarlo o identificar sus desviaciones.

---

# 2. Principio fundamental

La puntuación no se asigna por impresión general.

Toda evaluación debe seguir esta relación:

```text
CRITERIO
→ HALLAZGO / CONDICIÓN
→ EVIDENCIA
→ PUNTOS PERDIDOS
→ CORRECCIÓN
→ VERIFICACIÓN
```

Toda pérdida de puntos debe tener una causa identificable y materialmente relacionada.

Una `SUGGESTION` nunca resta puntos, nunca activa Quality Gates y nunca bloquea 100/100.

Un proyecto sólo puede alcanzar `100/100` cuando cumple las condiciones definidas por el estándar y existe evidencia suficiente para justificarlo.

---

# 3. Estructura

La estructura base del framework es:

```text
.audit/
│
├── README.md
├── QUALITY_SCORE.md
├── AUDIT_RULES.md
├── AUDIT_PROMPT.md
│
├── profiles/
│   ├── TEMPLATE.md
│   ├── APPLICATION.md
│   └── LIBRARY.md
│
├── evidence/
│   └── README.md
│
├── reports/
│   └── README.md
│
└── history/
    └── README.md
```

No todos los perfiles deben existir desde la primera versión.

Sólo debe utilizarse un perfil que esté definido y activo.

---

# 4. Responsabilidad de cada archivo

## `QUALITY_SCORE.md`

Define:

* los 100 puntos;
* las áreas de evaluación;
* pesos;
* reglas matemáticas;
* severidades;
* Quality Gates;
* condiciones para obtener 100/100;
* tratamiento de N/A;
* nivel de confianza.

Responde:

> ¿Cómo se calcula la nota?

---

## `AUDIT_RULES.md`

Define:

* cómo debe trabajar el auditor;
* orden de inspección;
* uso de evidencia;
* ejecución de comandos;
* tratamiento de contradicciones;
* causas raíz;
* doble penalización;
* seguridad durante la auditoría;
* reglas anti-alucinación;
* reauditorías;
* auditorías cruzadas.

Responde:

> ¿Cómo debe realizarse la auditoría?

---

## `profiles/`

Contiene la interpretación del estándar según el tipo de proyecto.

Ejemplos:

```text
profiles/TEMPLATE.md
profiles/APPLICATION.md
profiles/LIBRARY.md
```

El perfil define qué significa cada criterio dentro de ese contexto.

Responde:

> ¿Qué significa calidad para este tipo de proyecto?

---

## `AUDIT_PROMPT.md`

Contiene la instrucción operativa que debe recibir el agente auditor.

Debe obligarlo a leer y aplicar:

```text
QUALITY_SCORE.md
AUDIT_RULES.md
perfil correspondiente
contrato real del proyecto
```

No debe duplicar innecesariamente el contenido de dichos archivos.

Responde:

> ¿Cómo inicio una auditoría con un agente?

---

## `evidence/`

Contiene evidencia generada o recopilada durante auditorías.

Puede incluir, según corresponda:

```text
repository-tree.txt
git-status.txt
tests.txt
lint.txt
build.txt
security.txt
github-controls.md
verification.md
```

La evidencia debe permitir reconstruir las conclusiones importantes del informe.

---

## `reports/`

Contiene informes completos de auditoría.

Ejemplo:

```text
AUDIT-2026-08-29-a12b34c-framework-auditoria.md
```

Cada informe debe identificar como mínimo:

* repositorio;
* branch;
* commit;
* fecha;
* versión de `QUALITY_SCORE.md`;
* versión del perfil;
* puntuación;
* hallazgos;
* evidencia;
* plan de corrección.

---

## `history/`

Mantiene la evolución histórica de la calidad.

Puede registrar:

```text
fecha
commit
versión
score
BLOCKER
CRITICAL
MAJOR
MINOR
```

Permite observar si el repositorio mejora o degrada con el tiempo.

---

# 5. Documentos normativos

Los documentos normativos principales son:

```text
QUALITY_SCORE.md
AUDIT_RULES.md
profiles/<PROFILE>.md
```

Estos archivos constituyen el contrato de evaluación.

El auditor no debe modificar sus reglas durante una auditoría activa para favorecer o perjudicar al proyecto.

Además, toda auditoría debe respetar estas reglas de consistencia:

```text
SUGGESTION = 0 puntos perdidos
SUGGESTION = 0 Quality Gates
SUGGESTION = no bloquea 100/100
```

Si una ausencia o problema reduce puntuación, debe clasificarse mediante una severidad puntuable adecuada.

---

# 6. Orden de lectura obligatorio

Antes de comenzar una auditoría debe leerse, en este orden:

```text
1. .audit/README.md
2. .audit/QUALITY_SCORE.md
3. .audit/AUDIT_RULES.md
4. .audit/profiles/<PROFILE>.md
5. documentación y contrato del proyecto
```

Sólo después debe iniciarse la inspección y puntuación.

---

# 7. Selección del perfil

Debe seleccionarse el perfil que corresponda al propósito principal del repositorio.

Ejemplos:

```text
Repositorio utilizado como plantilla
→ TEMPLATE

Aplicación ejecutable
→ APPLICATION

Librería o SDK
→ LIBRARY
```

Si ningún perfil existente representa correctamente el proyecto:

no debe forzarse uno incorrecto.

Debe definirse previamente un perfil apropiado.

Durante una auditoría se carga exactamente UN perfil.

Los demás archivos de .audit/profiles/ deben ignorarse completamente
y no pueden introducir requisitos, penalizaciones ni recomendaciones
en la auditoría actual.

Un perfil con `Estado: NO IMPLEMENTADO` nunca puede seleccionarse.

Tampoco puede introducir requisitos, penalizaciones o recomendaciones en la auditoría actual.

---

# 8. Perfil TEMPLATE

Para repositorios cuyo propósito principal sea servir como base reutilizable debe utilizarse:

```text
.audit/profiles/TEMPLATE.md
```

Este perfil evalúa especialmente:

* reutilización;
* limpieza;
* ausencia de residuos;
* bootstrap;
* portabilidad dentro del alcance declarado;
* documentación;
* tests;
* regresión;
* Git;
* CI/CD;
* releases cuando apliquen al contrato actual;
* seguridad;
* automatización;
* agentes;
* fuentes únicas de verdad;
* comportamiento del proyecto generado cuando corresponda.

No exige automáticamente:

```text
multiplataforma
LICENSE
Dependabot
lockfile
linter específico
branch protection nativa de pago
```

La evaluación debe basarse en contexto, contrato y riesgo objetivo.

---

# 9. Antes de auditar

Debe identificarse el estado exacto del repositorio.

Registrar cuando sea posible:

```text
Repositorio:
Ruta:
Branch:
Commit:
Tag:
Fecha:
Perfil:
Quality Score Standard:
Audit Rules:
```

También debe comprobarse el estado del worktree.

Si existen cambios locales:

```text
WORKTREE NO LIMPIO
```

debe quedar registrado.

---

# 10. Regla de inmutabilidad del objetivo

Una auditoría debe evaluar un estado concreto del repositorio.

Preferentemente:

```text
commit específico
```

No deben realizarse correcciones mientras se está calculando la nota inicial.

El ciclo correcto es:

```text
AUDITAR
→ INFORMAR
→ CORREGIR
→ NUEVO COMMIT
→ REAUDITAR
```

---

# 11. Inicio de una auditoría

La forma normal de iniciar una auditoría será utilizar:

```text
.audit/AUDIT_PROMPT.md
```

El agente debe disponer de acceso al repositorio que se desea evaluar.

El prompt debe indicar el perfil correspondiente.

Ejemplo conceptual:

```text
Ejecuta una auditoría completa de este repositorio.

Framework:
.audit/

Perfil:
.audit/profiles/TEMPLATE.md

No modifiques el proyecto.
Genera evidencia e informe según las reglas del framework.
```

El contenido operativo definitivo se encuentra en `AUDIT_PROMPT.md`.

---

# 12. Flujo de auditoría

El flujo general es:

```text
IDENTIFICAR
     ↓
INVENTARIAR
     ↓
DETERMINAR CONTRATO
     ↓
INSPECCIONAR IMPLEMENTACIÓN
     ↓
EJECUTAR VERIFICACIONES
     ↓
REVISAR GOBERNANZA Y SEGURIDAD
     ↓
CONSOLIDAR HALLAZGOS
     ↓
IDENTIFICAR CAUSAS RAÍZ
     ↓
PUNTUAR
     ↓
VALIDAR CONSISTENCIA MATEMÁTICA
     ↓
APLICAR QUALITY GATES
     ↓
GENERAR INFORME
```

La puntuación definitiva debe realizarse al final.

---

# 13. Evidencia

Toda conclusión importante debe estar respaldada por evidencia suficiente.

Tipos habituales:

```text
documentación
archivo
configuración
código
workflow
test
comando
resultado
configuración remota
historial Git
release
tag
```

No se acepta como evidencia suficiente:

```text
“parece correcto”
“el agente lo sabe”
“esto siempre funciona”
“se explicó en otro chat”
```

---

# 14. Niveles de evidencia

El framework distingue conceptualmente:

```text
E1 — Declarativa
E2 — Estructural
E3 — Implementación inspeccionada
E4 — Ejecución satisfactoria
E5 — Enforcement verificado
```

El nivel requerido depende del criterio evaluado.

Una afirmación crítica normalmente requiere más que evidencia documental.

---

# 15. Estados de verificación

Durante la auditoría deben utilizarse estados claros.

Valores recomendados:

```text
PASS
FAIL
NO VERIFICADO
N/A
```

Cuando sea necesario también pueden emplearse:

```text
DOCUMENTADO
IMPLEMENTADO
INFERIDO
EVIDENCIA INSUFICIENTE
NO DETERMINADO
```

No debe presentarse una inferencia como hecho verificado.

---

# 16. Ejecución de comandos

Siempre deben preferirse los mecanismos oficiales del propio repositorio.

Ejemplos:

```text
validate
test
lint
build
bootstrap
doctor
regression
```

El auditor debe localizar primero cuál es el comando correcto.

No debe inventarlo basándose únicamente en convenciones del ecosistema.

---

# 17. Seguridad durante la auditoría

La auditoría no debe provocar cambios destructivos.

Salvo autorización explícita y entorno seguro, no debe:

* desplegar;
* publicar;
* hacer push;
* crear releases;
* borrar datos;
* ejecutar migraciones destructivas;
* modificar producción;
* rotar secretos;
* alterar configuraciones remotas.

Cuando una verificación implique riesgo debe preferirse:

* inspección;
* simulación;
* entorno aislado;
* evidencia existente.

---

# 18. Auditoría no significa corrección

Durante la evaluación inicial:

```text
NO CORREGIR
```

Los problemas deben registrarse.

Después de finalizar la auditoría podrá iniciarse una etapa independiente de remediación.

Esto evita evaluar un estado que nunca existió realmente en el repositorio.

---

# 19. Puntuación

La puntuación se calcula exclusivamente según:

```text
QUALITY_SCORE.md
```

El auditor no puede:

* agregar puntos;
* modificar pesos;
* compensar según impresión general;
* redondear artificialmente;
* alterar Quality Gates.

La nota máxima es:

```text
100/100
```

---

# 20. Score bruto y Score final

Toda auditoría debe diferenciar:

```text
SCORE BRUTO
```

de:

```text
SCORE FINAL
```

El score final puede quedar limitado por Quality Gates.

Ejemplo:

```text
Score bruto: 94/100
Gate: CRITICAL
Score final: 79/100
```

---

# 21. Condición especial de 100/100

Una puntuación `100/100` requiere:

* todos los criterios aplicables completos;
* ausencia de hallazgos puntuables;
* ausencia de gates;
* verificaciones críticas ejecutadas;
* evidencia suficiente;
* confianza ALTA.

Además:

si el resultado provisional es 100/100 debe realizarse la segunda pasada definida en `AUDIT_RULES.md`.

El objetivo de esa segunda pasada es intentar refutar el 100 mediante evidencia real.

No inventar defectos.

---

# 22. Hallazgos

Los hallazgos deben clasificarse por severidad:

```text
BLOCKER
CRITICAL
MAJOR
MINOR
SUGGESTION
```

Y por tipo cuando corresponda:

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

Cada hallazgo puntuable debe estar relacionado con un criterio.

Regla obligatoria:

```text
SUGGESTION = mejora opcional
SUGGESTION = 0 puntos recuperables obligatorios
SUGGESTION = fuera del camino obligatorio a 100
```

---

# 23. Causas raíz

Antes de generar el informe final deben identificarse problemas derivados de una misma causa.

Ejemplo:

```text
ROOT-001
script validate roto
     ↓
tests no ejecutan
lint no ejecuta
CI falla
```

No deben tratarse automáticamente todos los síntomas como defectos independientes.

---

# 24. Qué falta y qué sobra

Toda auditoría debe evaluar ambos sentidos.

## Qué falta

Capacidades necesarias que no existen o están incompletas.

## Qué sobra

Elementos que generan complejidad accidental, duplicación, riesgo o mantenimiento sin aportar valor proporcional.

Un template profesional no mejora simplemente agregando más elementos.

---

# 25. Camino a 100

Cuando el resultado sea inferior a 100/100, el informe debe indicar un camino matemáticamente consistente para recuperar los puntos.

Ejemplo:

```text
Score actual: 93

F-001 → +3
F-002 → +2
F-003 → +2

Score esperado: 100
```

No debe atribuirse más recuperación de puntos que la pérdida real.

Antes de normalizar por N/A debe cumplirse exactamente:

```text
puntos obtenidos
+
puntos recuperables obligatorios
=
puntos aplicables
```

Si el plan proyectado no llega matemáticamente a 100/100, el camino a 100 está incompleto
y el informe debe corregirse antes de utilizarse como baseline oficial.

---

# 26. Evidencia persistente

Cuando sea útil conservar resultados de comandos o verificaciones, deben almacenarse en:

```text
.audit/evidence/
```

La convención concreta se define en:

```text
.audit/evidence/README.md
```

Para auditorías asociadas a un commit, la forma general es:

```text
.audit/evidence/YYYY-MM-DD-<short-commit>-<slug>/
```

La evidencia no debe alterar el comportamiento del proyecto.

---

# 27. Informes

Los informes deben almacenarse en:

```text
.audit/reports/
```

La convención concreta se define en:

```text
.audit/reports/README.md
```

Para auditorías asociadas a un commit, la forma general es:

```text
AUDIT-YYYY-MM-DD-<short-commit>-<slug>.md
```

El informe y su carpeta de evidencia deben compartir el mismo identificador base.

Cada auditoría debe producir un informe independiente.

No debe sobrescribirse silenciosamente una auditoría histórica.

---

# 28. Historial

La evolución de scores debe registrarse en:

```text
.audit/history/
```

La finalidad es poder observar:

```text
versión A → 74
versión B → 86
versión C → 96
versión D → 100
```

y reconstruir qué mejoras explicaron dicha evolución.

---

# 29. Reauditoría

Una vez aplicadas correcciones:

1. crear un nuevo estado verificable;
2. preferentemente realizar commit;
3. volver a ejecutar la auditoría;
4. generar un nuevo informe;
5. actualizar el historial.

No debe asumirse que corregir un archivo recupera automáticamente los puntos.

La corrección debe verificarse.

Una auditoría marcada:

```text
INCONSISTENTE — REQUIERE CORRECCIÓN
```

no debe registrarse como baseline oficial hasta corregir la inconsistencia metodológica.

---

# 30. Auditoría cruzada

Para auditorías de alta confianza puede utilizarse más de un auditor.

Proceso recomendado:

```text
AUDITOR A
   ↓
informe independiente

AUDITOR B
   ↓
informe independiente

comparación
   ↓
discrepancias
   ↓
resolución basada en evidencia
```

No se recomienda promediar puntuaciones.

Las divergencias deben resolverse criterio por criterio.

---

# 31. Uso con distintos agentes

Este framework debe poder utilizarse con herramientas distintas.

Ejemplos:

```text
Claude Code
Codex
OpenCode
otros agentes con acceso al repositorio
```

La herramienta puede cambiar.

El estándar no.

Todos deben utilizar:

```text
mismo QUALITY_SCORE
mismo AUDIT_RULES
mismo perfil
mismo commit
```

para que los resultados sean comparables.

---

# 32. Independencia de memoria externa

La auditoría no debe depender de:

* memoria del modelo;
* conversaciones anteriores;
* instrucciones no persistidas;
* conocimiento exclusivo del autor.

Todo requisito esencial que afecte al resultado debe encontrarse en:

* el repositorio;
* el framework;
* fuentes externas verificables cuando sean necesarias.

---

# 33. Versionado del framework

Los componentes principales deben estar versionados.

Ejemplo:

```text
QUALITY_SCORE: 1.1
AUDIT_RULES: 1.1
TEMPLATE PROFILE: 1.1
AUDIT_PROMPT: 1.1
AUDIT_FRAMEWORK: 1.1
```

Un informe debe registrar qué versiones utilizó.

Esto evita comparar auditorías realizadas con reglas distintas como si fueran equivalentes.

---

# 34. Modificación del framework

No debe modificarse el estándar en mitad de una auditoría para cambiar el resultado.

El proceso correcto es:

```text
detectar ambigüedad
→ finalizar, marcar provisional o invalidar auditoría
→ corregir framework
→ versionar
→ ejecutar nueva auditoría
```

Una auditoría piloto puede utilizarse específicamente para descubrir ambigüedades del framework.

En ese caso, su score puede conservarse como evidencia histórica, pero no debe tratarse como baseline oficial
si la metodología utilizada resultó inconsistente.

---

# 35. Qué no es este framework

Este framework no es:

* una certificación oficial;
* una garantía de ausencia de bugs;
* una auditoría legal;
* una auditoría financiera;
* una prueba absoluta de seguridad;
* un reemplazo del juicio técnico.

Es un mecanismo estructurado para evaluar de forma consistente la calidad técnica dentro de un alcance definido.

---

# 36. Filosofía de diseño

El framework sigue estos principios:

### Evidencia antes que opinión

No asumir.

Verificar.

### Resultados antes que nombres de archivos

La capacidad importa más que la convención utilizada.

### Simplicidad antes que sofisticación innecesaria

Más herramientas no significa mayor calidad.

### Automatización donde aporta valor

No automatizar por automatizar.

### Quality Gates reales

Un control que puede ignorarse accidentalmente no protege realmente.

### Objetivo de control antes que proveedor

La evaluación debe valorar si el riesgo está controlado de forma verificable.

No debe exigir automáticamente una funcionalidad comercial concreta cuando exista un mecanismo técnico alternativo equivalente.

### Transparencia

Cada punto debe poder explicarse.

### Reproducibilidad

Otro auditor debería poder llegar a una conclusión sustancialmente equivalente.

---

# 37. Flujo recomendado completo

```text
┌──────────────────────────┐
│ Seleccionar repositorio  │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Seleccionar perfil       │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Fijar branch / commit    │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Ejecutar AUDIT_PROMPT    │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Recolectar evidencia     │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Calcular score           │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Validar consistencia     │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Generar reporte          │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Corregir hallazgos       │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Commit nuevo             │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Reauditar                │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Actualizar historial     │
└──────────────────────────┘
```

---

# 38. Resultado esperado

Una auditoría completa debe permitir responder con evidencia:

```text
¿Cuánto puntúa el proyecto?
¿Por qué?
¿Qué está bien?
¿Qué falta?
¿Qué está mal?
¿Qué sobra?
¿Qué riesgos existen?
¿Qué no pudo verificarse?
¿Qué debe corregirse?
¿Cuántos puntos recupera cada corrección?
¿Qué falta exactamente para llegar a 100/100?
```

Si el informe no permite responder estas preguntas, la auditoría está incompleta.

---

# 39. Estado actual del framework

Componentes fundamentales:

```text
[x] README.md
[x] QUALITY_SCORE.md
[x] AUDIT_RULES.md
[x] profiles/TEMPLATE.md
[x] AUDIT_PROMPT.md
[x] evidence/README.md
[x] reports/README.md
[x] history/README.md
```

Versiones activas principales:

```text
QUALITY_SCORE: 1.1
AUDIT_RULES: 1.1
TEMPLATE PROFILE: 1.1
AUDIT_PROMPT: 1.1
AUDIT_FRAMEWORK: 1.1
```

Los perfiles adicionales deben incorporarse sólo cuando exista una necesidad real.

Si existen placeholders como:

```text
profiles/APPLICATION.md
profiles/LIBRARY.md
```

con `Estado: NO IMPLEMENTADO`, deben ignorarse completamente hasta su implementación y activación.

---

# 40. Regla final

El propósito de `.audit/` no es conseguir una nota alta.

Su propósito es hacer visible la diferencia entre:

```text
“creemos que el proyecto está bien”
```

y:

```text
“podemos demostrar por qué está bien”
```

El resultado ideal no es simplemente:

`100/100`

El resultado ideal es:

`100/100 defendible, reproducible y respaldado por evidencia`.
