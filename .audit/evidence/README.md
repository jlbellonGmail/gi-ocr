# README.md

# Audit Evidence

**Versión:** 1.1
**Estado:** Activo
**Ubicación:** `.audit/evidence/`

---

# 1. Propósito

Esta carpeta contiene la evidencia persistente generada o recopilada durante las auditorías ejecutadas con el framework:

```text
.audit/
```

Su objetivo es permitir que las conclusiones importantes de un informe puedan:

* verificarse;
* reproducirse;
* revisarse;
* compararse;
* auditarse posteriormente.

La evidencia no sustituye al informe.

El informe explica la conclusión.

La evidencia demuestra en qué se basa.

---

# 2. Principio fundamental

Toda evidencia debe responder, cuando corresponda:

```text
¿Qué se verificó?
¿Cómo se verificó?
¿Sobre qué commit?
¿Qué resultado produjo?
¿Puede otra persona repetirlo?
```

No debe conservarse evidencia únicamente para aumentar el volumen de la auditoría.

Debe almacenarse únicamente aquella información que aporte trazabilidad real.

---

# 3. Una carpeta por auditoría

Cada auditoría debe utilizar su propia carpeta.

Para una auditoría asociada a un commit:

```text
.audit/evidence/YYYY-MM-DD-<short-commit>-<slug>/
```

Ejemplo:

```text
.audit/evidence/2026-08-29-a12b34c-framework-auditoria/
```

El `<slug>` debe ser:

* breve;
* descriptivo;
* estable;
* relacionado con el objetivo de la auditoría.

Debe utilizar el mismo identificador base que el informe correspondiente:

```text
evidence/
└── 2026-08-29-a12b34c-framework-auditoria/

reports/
└── AUDIT-2026-08-29-a12b34c-framework-auditoria.md
```

---

# 4. Auditoría sin commit identificable

Si la auditoría corresponde a un worktree sin commit identificable puede utilizarse:

```text
.audit/evidence/YYYY-MM-DD-WORKTREE/
```

El informe correspondiente será:

```text
.audit/reports/AUDIT-YYYY-MM-DD-WORKTREE.md
```

Siempre debe quedar claramente registrado que el estado auditado no corresponde a un commit inmutable.

---

# 5. Contenido posible

Una carpeta de evidencia puede contener, según corresponda:

```text
verification.md
repository-inventory.md
github-controls.md

git-status.txt
git-log.txt
repository-tree.txt
tests.txt
lint.txt
build.txt
bootstrap.txt
security.txt
dependencies.txt
ci-log.txt
```

Esta lista es orientativa.

No existe obligación de crear todos estos archivos.

Sólo deben crearse aquellos que aporten evidencia real a la auditoría.

---

# 6. Cuándo utilizar `.txt`

Utilizar preferentemente `.txt` para conservar salida cruda o casi cruda de comandos.

Ejemplos:

```text
tests.txt
lint.txt
git-status.txt
git-log.txt
ci-log.txt
```

Un archivo `.txt` es apropiado cuando el valor principal es preservar exactamente o casi exactamente el resultado producido por una herramienta.

Ejemplo:

```text
Comando:
python -m pytest tests/

Resultado:
161 passed, 10 skipped
```

No es necesario transformar una salida técnica en Markdown únicamente por presentación.

---

# 7. Cuándo utilizar `.md`

Utilizar `.md` cuando la evidencia requiera estructura, explicación o relación entre varias fuentes.

Ejemplos:

```text
verification.md
repository-inventory.md
github-controls.md
```

Un archivo `.md` puede registrar:

```text
ID de verificación
objetivo
comando o método
resultado
exit code
estado
fuente
observaciones
limitaciones
archivo de evidencia relacionado
```

Ejemplo:

```markdown
## V-003 — Suite principal

**Objetivo:** comprobar la suite oficial.

**Comando:**
`python -m pytest tests/`

**Resultado:** PASS

**Exit code:** 0

**Evidencia:** `tests.txt`
```

---

# 8. Ledger de verificaciones

Cuando existan múltiples verificaciones significativas se recomienda crear:

```text
verification.md
```

Cada verificación debe tener un identificador estable:

```text
V-001
V-002
V-003
...
```

Formato recomendado:

```text
ID:
Objetivo:
Comando/Método:
Fuente del comando:
Resultado:
Exit code:
Estado:
Evidencia:
Observaciones:
```

Estados principales:

```text
PASS
FAIL
NO VERIFICADO
N/A
```

Cuando corresponda también puede indicarse:

```text
INFERIDO
EVIDENCIA INSUFICIENTE
LIMITACIÓN DEL ENTORNO
```

---

# 9. Evidencia cruda y evidencia interpretada

Debe distinguirse entre:

```text
EVIDENCIA CRUDA
```

y:

```text
INTERPRETACIÓN DEL AUDITOR
```

Ejemplo:

```text
tests.txt
```

puede contener el resultado original de `pytest`.

Mientras:

```text
verification.md
```

puede explicar qué demuestra ese resultado y qué no demuestra.

La interpretación nunca debe modificar silenciosamente el contenido original de la evidencia.

---

# 10. Evidencia de Git

Cuando Git sea relevante pueden conservarse, por ejemplo:

```text
git-status.txt
git-log.txt
git-branches.txt
git-tags.txt
git-remotes.txt
```

Debe registrarse especialmente el estado inicial auditado:

```text
branch
commit
tag
worktree limpio/no limpio
```

La evidencia debe corresponder al mismo estado identificado en el informe.

---

# 11. Evidencia de CI/CD

Cuando se verifique CI/CD puede conservarse:

```text
ci-log.txt
github-controls.md
```

Según corresponda debe distinguirse entre:

```text
WORKFLOW PRESENTE
WORKFLOW EJECUTADO
RESULTADO VERIFICADO
ENFORCEMENT VERIFICADO
```

Un workflow verde no demuestra por sí solo que todos sus controles sean obligatorios o que los fallos no puedan ignorarse.

---

# 12. Configuración remota

Cuando exista acceso autorizado pueden registrarse verificaciones de:

* branch protection;
* rulesets;
* required checks;
* reviews;
* releases;
* permisos;
* settings relevantes.

Ejemplo:

```text
github-controls.md
```

Debe diferenciarse claramente:

```text
CONFIGURACIÓN VERIFICADA
```

de:

```text
CONFIGURACIÓN DOCUMENTADA
```

Si no pudo comprobarse:

```text
NO VERIFICADO
```

No debe inferirse una configuración remota inexistente o inaccesible.

---

# 13. Evidencia de tests

La evidencia debe mostrar, cuando sea relevante:

```text
comando
resultado
cantidad
fallos
skips
exit code
entorno
```

No debe utilizarse únicamente el número de tests como indicador de calidad.

La evidencia sirve para demostrar que las verificaciones relevantes existen y producen resultados reales.

---

# 14. Salidas extensas

No debe llenarse `.audit/evidence/` con datos sin utilidad.

Si una salida es muy extensa:

* conservar únicamente lo necesario cuando sea suficiente;
* o conservar la salida completa en un archivo separado si aporta valor real;
* resumir el resultado en `verification.md`;
* referenciar el archivo desde el informe.

Ejemplo:

```text
verification.md
→ V-006: CI PASS

ci-log.txt
→ salida técnica completa necesaria para reproducir la conclusión
```

No copiar miles de líneas dentro del informe cuando pueden conservarse como evidencia separada.

---

# 15. Evidencia mínima suficiente

El objetivo no es registrar cada comando ejecutado.

No es necesario conservar:

* navegación trivial;
* `cd`;
* listados repetidos;
* búsquedas sin relevancia;
* intentos descartados que no aportan a una conclusión;
* información redundante.

Sí debe conservarse la evidencia necesaria para sostener:

* pérdidas de puntos;
* puntuación completa de criterios importantes;
* Quality Gates;
* hallazgos relevantes;
* NO VERIFICADO significativos;
* conclusiones de seguridad;
* conclusiones sobre CI/enforcement;
* condiciones necesarias para 100/100.

---

# 16. Relación con hallazgos

Todo hallazgo puntuable debe poder rastrearse hasta evidencia suficiente.

Relación esperada:

```text
CRITERIO
→ HALLAZGO / CONDICIÓN
→ EVIDENCIA
→ PUNTOS PERDIDOS
```

La existencia de un archivo de evidencia no justifica por sí sola una pérdida de puntos.

Debe existir relación material entre la evidencia, el hallazgo y el criterio.

---

# 17. SUGGESTION

Una `SUGGESTION` puede tener evidencia que explique por qué sería útil.

Pero:

```text
SUGGESTION = 0 puntos perdidos
SUGGESTION = 0 puntos recuperables obligatorios
SUGGESTION = 0 Quality Gates
SUGGESTION = no bloquea 100/100
```

La evidencia de una mejora opcional no puede utilizarse para convertirla indirectamente en requisito obligatorio.

---

# 18. NO VERIFICADO

Cuando una capacidad relevante no pueda comprobarse debe registrarse:

```text
NO VERIFICADO
```

y, cuando sea útil, conservar evidencia de la limitación.

Ejemplos:

```text
herramienta no disponible
acceso remoto insuficiente
restricción de permisos
limitación del entorno
operación insegura para ejecutar
```

No deben fabricarse resultados para completar la evidencia.

---

# 19. Seguridad y secretos

Nunca deben almacenarse secretos completos dentro de `.audit/evidence/`.

Debe redactarse cualquier:

* token;
* API key;
* password;
* private key;
* cookie;
* credential;
* connection string sensible.

Ejemplo:

```text
ghp_****abcd
```

Si una herramienta produce secretos en su salida, la evidencia debe sanitizarse antes de persistirse.

La sanitización debe preservar suficiente contexto para demostrar el hallazgo sin exponer la credencial.

---

# 20. Datos personales y privados

No deben persistirse datos personales o privados innecesarios.

Si una evidencia contiene información sensible que no es necesaria para sostener la conclusión:

debe redactarse o excluirse.

La auditoría debe conservar la mínima información necesaria.

---

# 21. No modificar el proyecto para generar evidencia

Los artefactos de evidencia no deben alterar el comportamiento del proyecto auditado.

Está prohibido modificar código, configuración, tests o workflows únicamente para producir una evidencia favorable.

La evidencia debe representar el estado real auditado.

Si una herramienta genera temporales:

* deben identificarse;
* limpiarse cuando sea seguro;
* no deben confundirse con contenido original del repositorio.

---

# 22. Evidencia temporal

No toda evidencia necesita persistirse.

Una verificación puede documentarse directamente en `verification.md` si:

* su salida es breve;
* puede reproducirse fácilmente;
* no aporta valor conservar un archivo separado.

Debe evitarse crear archivos innecesarios.

---

# 23. Evidencia histórica

La evidencia de una auditoría anterior:

```text
NO sustituye
```

la verificación de una auditoría actual.

Puede utilizarse como contexto histórico.

Las capacidades críticas deben volver a verificarse cuando corresponda.

Cada carpeta de evidencia representa la auditoría específica a la que pertenece.

---

# 24. Inmutabilidad práctica

Una vez finalizada y aceptada una auditoría, su carpeta de evidencia debe tratarse como histórica.

No debe modificarse para hacer coincidir retroactivamente una conclusión posterior.

Si se corrige el proyecto:

```text
nuevo commit
→ nueva auditoría
→ nueva carpeta de evidencia
→ nuevo informe
```

---

# 25. Auditorías provisionales o inconsistentes

Si una auditoría es posteriormente identificada como:

```text
PILOTO
BASELINE PROVISIONAL
INCONSISTENTE — REQUIERE CORRECCIÓN
```

su evidencia puede conservarse como registro histórico.

Pero no debe utilizarse como evidencia de una baseline oficial corregida.

La nueva auditoría debe generar su propia carpeta de evidencia.

---

# 26. Auditorías cruzadas

Si dos auditores evalúan el mismo commit de forma independiente, cada auditoría debe conservar evidencia diferenciada cuando sea necesario.

Puede utilizarse un slug que identifique el propósito o auditor:

```text
2026-08-29-a12b34c-baseline-claude/
2026-08-29-a12b34c-baseline-codex/
```

Los informes deben seguir la misma distinción.

No deben mezclarse evidencias para ocultar divergencias entre auditores.

---

# 27. Reproducibilidad

Siempre que sea razonablemente posible, la evidencia debe permitir repetir:

```text
comando
método
fuente consultada
estado observado
resultado
```

Debe evitarse evidencia cuya interpretación dependa exclusivamente de memoria externa o conversación previa.

---

# 28. Referencias desde el informe

El informe debe referenciar la evidencia relevante.

Ejemplo:

```text
F-002
→ V-008
→ verification.md
→ ci-log.txt
```

No es obligatorio referenciar cada archivo en cada párrafo.

Sí debe ser posible reconstruir de dónde surge una conclusión importante.

---

# 29. Nombres de archivos

Preferir nombres:

* descriptivos;
* estables;
* en minúsculas;
* con guiones cuando sea útil.

Ejemplos:

```text
verification.md
repository-inventory.md
github-controls.md
git-status.txt
tests.txt
ci-log.txt
```

Evitar:

```text
resultado-final-final2.txt
prueba-nueva.txt
cosas.txt
```

---

# 30. Formato recomendado de la carpeta

Ejemplo:

```text
.audit/
└── evidence/
    ├── README.md
    └── 2026-08-29-a12b34c-framework-auditoria/
        ├── verification.md
        ├── repository-inventory.md
        ├── github-controls.md
        ├── git-status.txt
        ├── tests.txt
        └── ci-log.txt
```

No es obligatorio utilizar exactamente estos archivos.

La estructura debe responder a la evidencia realmente necesaria.

---

# 31. Qué no debe ocurrir

Está prohibido utilizar `.audit/evidence/` para:

* guardar secretos;
* modificar comportamiento del proyecto;
* introducir archivos que hagan pasar tests;
* ocultar fallos;
* reemplazar evidencia fallida por una inventada;
* almacenar salidas irrelevantes para aparentar profundidad;
* reescribir evidencia histórica para mejorar una nota;
* mezclar evidencia de commits diferentes sin indicarlo;
* tratar documentación como prueba de ejecución cuando no lo es.

---

# 32. Regla final

La evidencia existe para permitir responder:

> ¿Qué observación concreta permite sostener esta conclusión?

Si un dato almacenado no ayuda razonablemente a responder esa pregunta:

probablemente no necesita conservarse.

La evidencia debe ser:

```text
suficiente
relevante
reproducible
segura
trazable
proporcional
```

No debe ser simplemente abundante.
