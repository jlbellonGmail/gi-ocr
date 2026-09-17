# Audit Reports

**Versión:** 1.1
**Estado:** Activo

---

# 1. Propósito

La carpeta:

```text
.audit/reports/
```

almacena los informes finales de auditoría.

Cada informe representa la evaluación de un estado concreto del repositorio utilizando versiones concretas del framework.

Los informes son históricos.

No deben sobrescribirse para reflejar correcciones posteriores.

---

# 2. Unidad de informe

Cada auditoría completa debe generar un informe independiente.

Formato recomendado:

```text
AUDIT-YYYY-MM-DD-<short-commit>-<slug>.md
```

Ejemplo:

```text
AUDIT-2026-08-29-a12b34c-framework-auditoria.md
```

Si no existe commit:

```text
AUDIT-YYYY-MM-DD-WORKTREE.md
```

---

# 3. Colisiones de nombre

El `<slug>` debe utilizarse para distinguir auditorías con propósito diferente.

Ejemplos:

```text
AUDIT-2026-08-29-a12b34c-baseline.md
AUDIT-2026-08-29-a12b34c-seguridad.md
```

Si se realizan varias auditorías equivalentes sobre el mismo commit, fecha y propósito,
puede añadirse un sufijo estable:

```text
AUDIT-2026-08-29-a12b34c-baseline-01.md
AUDIT-2026-08-29-a12b34c-baseline-02.md
```

Para auditorías cruzadas puede identificarse al auditor dentro del slug:

```text
AUDIT-2026-08-29-a12b34c-baseline-claude.md
AUDIT-2026-08-29-a12b34c-baseline-codex.md
```

El nombre debe ser suficientemente descriptivo para identificar el informe sin abrirlo.

---

# 4. No usar `latest.md` como fuente histórica

Puede existir opcionalmente un puntero o índice al informe actual.

Pero el informe histórico real debe conservar nombre único.

No debe reemplazarse silenciosamente:

```text
latest.md
```

perdiendo trazabilidad.

---

# 5. Identificación obligatoria

Todo informe debe indicar:

```text
Repositorio:
Ruta:
Branch:
Commit:
Tag:
Fecha:
Worktree:
Perfil:
QUALITY_SCORE:
AUDIT_RULES:
Versión de perfil:
Auditor:
Entorno:
Confianza:
Consistencia metodológica:
```

Cuando un dato no pueda determinarse:

```text
NO DETERMINADO
```

---

# 6. Estructura mínima

Los informes generados mediante `AUDIT_PROMPT.md` deben contener:

```text
A. IDENTIFICACIÓN
B. VEREDICTO EJECUTIVO
C. ALCANCE Y LIMITACIONES
D. CONTRATO DETECTADO
E. MATRIZ DE PUNTUACIÓN
F. DETALLE POR SUBCRITERIO
G. LEDGER DE VERIFICACIÓN
H. HALLAZGOS
I. CAUSAS RAÍZ
J. QUÉ SOBRA
K. QUÉ FALTA
L. NO VERIFICADO
M. QUALITY GATES
N. CAMINO MATEMÁTICO A 100
O. PLAN DE REMEDIACIÓN
P. SEGUNDA PASADA DE 100
Q. CERTIFICACIÓN FINAL
```

No deben omitirse silenciosamente secciones obligatorias.

Si una sección no aplica, debe indicarse explícitamente:

```text
N/A
```

y justificarse cuando corresponda.

---

# 7. Score

Todo informe debe mostrar separadamente:

```text
Score bruto
Score final
```

Cuando existan N/A:

también:

```text
Puntos aplicables
Score normalizado
```

Cuando exista Quality Gate:

indicar cuál.

Toda pérdida de puntos debe ser trazable:

```text
CRITERIO
→ HALLAZGO / CONDICIÓN
→ EVIDENCIA
→ PUNTOS PERDIDOS
```

Un informe no debe contener descuentos sin causa identificable.

---

# 8. Hallazgos

Cada hallazgo debe tener ID estable dentro del informe.

Formato:

```text
F-001
F-002
F-003
```

Un hallazgo debe conservar su ID dentro del mismo informe.

No reutilizar IDs para problemas diferentes.

---

# 9. Hallazgos históricos

Los IDs no necesitan ser globalmente únicos entre auditorías.

Por ejemplo:

```text
AUDIT A → F-001
AUDIT B → F-001
```

son válidos porque cada informe tiene su propio contexto.

Si se necesita trazabilidad longitudinal puede añadirse posteriormente un identificador persistente.

---

# 10. Evidencia

Los informes deben referenciar la carpeta correspondiente:

```text
.audit/evidence/YYYY-MM-DD-<short-commit>-<slug>/
```

Ejemplo:

```text
Evidencia:
../evidence/2026-08-29-a12b34c-framework-auditoria/tests.txt
```

No copiar dentro del informe salidas extensas sin necesidad.

---

# 11. Informe inmutable

Después de completado y aceptado como resultado histórico:

el informe no debe modificarse para aparentar que el proyecto auditado era diferente.

Si se detecta un error material en el informe:

preferir:

* emitir una corrección explícita;
* marcarlo como provisional o invalidado cuando corresponda;
* o ejecutar una nueva auditoría.

Nunca debe reescribirse silenciosamente el resultado histórico.

---

# 12. Correcciones posteriores

Un hallazgo corregido posteriormente no debe borrarse del informe original.

El informe representa:

```text
estado en commit X
```

La corrección debe aparecer en:

```text
nuevo commit
→ nueva auditoría
→ nuevo informe
```

---

# 13. Auditoría parcial

Si una auditoría no pudo completarse:

el nombre puede utilizar:

```text
AUDIT-PARTIAL-YYYY-MM-DD-<short-commit>-<slug>.md
```

y debe indicar claramente:

```text
ESTADO: PARCIAL
```

No debe confundirse con una auditoría completa.

---

# 14. Auditoría provisional, inconsistente o invalidada

Si una auditoría piloto revela ambigüedades o inconsistencias metodológicas puede marcarse:

```text
PILOTO
BASELINE PROVISIONAL
INCONSISTENTE — REQUIERE CORRECCIÓN
```

Su informe puede conservarse como evidencia histórica, pero no debe utilizarse como baseline oficial.

Si se descubre que la metodología utilizada era incorrecta de forma material o que se auditó el commit equivocado:

el informe debe marcarse:

```text
INVALIDADO
```

No debe eliminarse silenciosamente si ya forma parte del historial relevante.

Debe explicarse el motivo y, cuando corresponda:

```text
corregir framework
→ versionar
→ ejecutar nueva auditoría
→ generar nuevo informe
```

---

# 15. Auditoría cruzada

Cuando exista más de un auditor sobre el mismo estado:

conservar todos los informes independientes.

Posteriormente puede generarse:

```text
CONSENSUS-YYYY-MM-DD-<short-commit>-<slug>.md
```

para resolver divergencias.

El informe de consenso no reemplaza los originales.

---

# 16. Informe de consenso

Un informe de consenso debe indicar:

```text
Auditorías comparadas:
Discrepancias:
Evidencia revisada:
Resoluciones:
Score resultante:
```

No debe simplemente promediar las notas.

---

# 17. Reauditoría

Después de correcciones:

crear siempre un nuevo informe.

Ejemplo:

```text
AUDIT-2026-08-29-a12b34c-baseline.md → 83/100

correcciones

AUDIT-2026-09-02-c45d67e-reauditoria.md → 96/100
```

Ambos deben conservarse.

---

# 18. Plan a 100

Si el score es inferior a 100, el informe debe indicar:

```text
Score actual
Hallazgos puntuables
Puntos recuperables
Score esperado
```

La suma debe ser matemáticamente exacta.

Antes de normalización debe cumplirse:

```text
puntos obtenidos
+
puntos recuperables obligatorios
=
puntos aplicables
```

Si el resultado proyectado no alcanza exactamente 100/100 normalizado:

```text
CAMINO A 100 INCOMPLETO
```

y el informe debe corregirse antes de utilizarse como baseline oficial.

No puede quedar ningún subcriterio parcialmente puntuado sin explicar cómo recupera sus puntos.

---

# 19. Mejoras opcionales

Las `SUGGESTION` deben quedar claramente separadas de los defectos puntuables.

Regla obligatoria:

```text
SUGGESTION = 0 puntos perdidos
SUGGESTION = 0 puntos recuperables obligatorios
SUGGESTION = 0 Quality Gates
SUGGESTION = no bloquea 100/100
```

Si una propuesta es necesaria para recuperar puntos o alcanzar 100/100, no puede clasificarse como `SUGGESTION`.

---

# 20. Consistencia metodológica

Antes de aceptar un informe como resultado oficial debe verificarse:

```text
[ ] Toda pérdida de puntos tiene causa identificada
[ ] Todo hallazgo puntuable está materialmente relacionado con su criterio
[ ] Ninguna SUGGESTION resta puntos
[ ] Ninguna SUGGESTION activa Quality Gates
[ ] Ninguna SUGGESTION bloquea 100/100
[ ] Todos los puntos perdidos aparecen en el camino obligatorio a 100
[ ] El camino proyectado alcanza exactamente los puntos aplicables
[ ] Todos los N/A están justificados
[ ] Los Quality Gates derivan de hallazgos reales
[ ] Informe y evidencia usan el mismo identificador base
```

Si alguna condición falla:

```text
INCONSISTENTE — REQUIERE CORRECCIÓN
```

El informe no debe utilizarse como baseline oficial hasta corregir la inconsistencia.

---

# 21. Certificación interna del framework

La frase:

```text
TEMPLATE DE REFERENCIA 100/100
```

sólo puede utilizarse cuando se cumplen todas las condiciones definidas por:

```text
QUALITY_SCORE.md
AUDIT_RULES.md
profiles/TEMPLATE.md
```

No representa una certificación oficial externa.

---

# 22. Resumen ejecutivo

El resumen ejecutivo debe ser breve y útil.

Debe responder:

```text
¿Cuál es el score?
¿Cuál es el principal riesgo?
¿Qué impide 100?
¿Puede utilizarse el proyecto?
```

El detalle técnico pertenece a las secciones posteriores.

---

# 23. Objetividad

Los informes deben evitar expresiones vagas como:

```text
“muy bueno”
“bastante profesional”
“parece excelente”
```

sin explicación.

Preferir:

```text
Q5.3 = 4/4
Tests oficiales ejecutados:
327 passed
```

---

# 24. No ocultar incertidumbre

Debe mostrarse explícitamente:

```text
NO VERIFICADO
EVIDENCIA INSUFICIENTE
NO DETERMINADO
```

cuando corresponda.

Un informe profesional no necesita aparentar certeza absoluta.

La incertidumbre relevante debe reflejarse también en el nivel de confianza y, cuando corresponda, en la puntuación.

---

# 25. Referencias a archivos

Cuando sea posible utilizar rutas concretas.

Ejemplo:

```text
.github/workflows/ci.yml
scripts/validate.ps1
AGENTS.md
```

Esto facilita reproducibilidad.

---

# 26. Regla final

Un informe debe permitir a una persona que no participó en la auditoría comprender:

> por qué el proyecto obtuvo exactamente esa puntuación y qué evidencia sostiene cada desviación relevante.

Además, debe poder determinarse sin ambigüedad:

```text
qué estado del repositorio fue auditado
qué versión del framework se utilizó
qué perfil estuvo activo
qué evidencia corresponde al informe
si el resultado es oficial, provisional, parcial o invalidado
```
