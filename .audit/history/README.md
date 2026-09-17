# Audit History

**Versión:** 1.1
**Estado:** Activo

---

# 1. Propósito

La carpeta:

```text
.audit/history/
```

mantiene la evolución histórica de la calidad del repositorio.

Su objetivo es permitir observar:

* mejora;
* degradación;
* estabilidad;
* cierre de hallazgos;
* aparición de nuevos riesgos;
* evolución hacia 100/100.

No reemplaza los informes individuales.

---

# 2. Archivo principal recomendado

Utilizar:

```text
.audit/history/SCORE_HISTORY.md
```

para registrar la secuencia de auditorías.

Puede crearse en la primera auditoría real.

---

# 3. Formato recomendado

```markdown
# Quality Score History

| Fecha | Commit | Tag | Perfil | Framework | Estado | Score bruto | Score final | Confianza | B | C | M | m | Informe |
|---|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---|
```

Donde:

```text
B = BLOCKER
C = CRITICAL
M = MAJOR
m = MINOR
```

---

# 4. Ejemplo

```markdown
| Fecha | Commit | Tag | Perfil | Framework | Estado | Score bruto | Score final | Confianza | B | C | M | m | Informe |
|---|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---|
| 2026-08-29 | a12b34c | - | TEMPLATE 1.1 | 1.1 | BASELINE | 78 | 78 | ALTA | 0 | 0 | 5 | 3 | ../reports/AUDIT-2026-08-29-a12b34c-baseline.md |
| 2026-09-02 | c45d67e | - | TEMPLATE 1.1 | 1.1 | REAUDITORÍA | 91 | 91 | ALTA | 0 | 0 | 2 | 2 | ../reports/AUDIT-2026-09-02-c45d67e-reauditoria.md |
| 2026-09-10 | f89e012 | v1.0.0 | TEMPLATE 1.1 | 1.1 | RELEASE | 100 | 100 | ALTA | 0 | 0 | 0 | 0 | ../reports/AUDIT-2026-09-10-f89e012-release-v1.md |
```

---

# 5. Una fila por auditoría válida

Cada auditoría completa, consistente y aceptada como resultado oficial debe generar una fila.

No registrar automáticamente como score oficial:

* auditorías abortadas;
* pruebas parciales;
* resultados preliminares;
* auditorías marcadas `INCONSISTENTE — REQUIERE CORRECCIÓN`;
* baseline provisionales;
* auditorías invalidadas.

Pueden documentarse separadamente cuando tengan valor histórico.

Una auditoría sólo puede convertirse en baseline oficial cuando haya pasado la validación de consistencia metodológica definida por el framework.

---

# 6. Auditorías parciales o provisionales

Si se desea registrarlas:

deben indicarse claramente.

Estados posibles:

```text
PARCIAL
PILOTO
BASELINE PROVISIONAL
INCONSISTENTE — REQUIERE CORRECCIÓN
```

No deben confundirse ni compararse directamente con auditorías completas oficiales.

Una `BASELINE PROVISIONAL` no debe utilizarse como punto oficial de evolución hasta ser reemplazada por una auditoría completa, consistente y confiable.

---

# 7. Auditorías invalidadas

Si una auditoría histórica es invalidada:

no debe borrarse necesariamente.

Debe marcarse:

```text
INVALIDADA
```

con referencia al motivo.

No debe utilizarse para:

* calcular tendencia oficial;
* establecer baseline;
* certificar releases;
* comparar evolución como si siguiera siendo válida.

Esto conserva trazabilidad sin falsear la serie histórica.

---

# 8. No editar retrospectivamente scores

Un score histórico representa lo calculado con:

* un commit;
* un framework;
* un perfil;
* una evidencia concreta.

No debe cambiarse porque posteriormente el proyecto mejoró.

La mejora genera una nueva fila.

---

# 9. Cambios del framework

Si cambia la versión de:

```text
QUALITY_SCORE
AUDIT_RULES
perfil
AUDIT_PROMPT
AUDIT_FRAMEWORK
```

debe registrarse cuando corresponda.

Ejemplo:

```text
Perfil:
TEMPLATE 1.1
```

Esto es esencial porque dos scores calculados con metodologías distintas pueden no ser perfectamente comparables.

Si la metodología cambia entre auditorías, el historial debe permitir distinguir claramente:

```text
cambio real del proyecto
```

de:

```text
cambio del método de medición
```

---

# 10. Cambios MAJOR del estándar

Si cambia la distribución matemática del score:

debe considerarse una nueva serie histórica o marcar claramente el corte metodológico.

Ejemplo:

```text
QUALITY_SCORE 1.x
──────────────
QUALITY_SCORE 2.0
```

No interpretar automáticamente una diferencia de score como mejora o degradación si también cambió la rúbrica.

---

# 11. Score bruto y final

Registrar ambos cuando difieran.

Cuando existan criterios N/A debe conservarse también, al menos en el informe asociado:

```text
puntos aplicables
score normalizado
```

Ejemplo:

```text
Score bruto: 94
Score final: 79
```

Esto permite observar que la calidad matemática era alta pero existía un CRITICAL que activó un gate.

---

# 12. Severidades

Registrar como mínimo:

```text
BLOCKER
CRITICAL
MAJOR
MINOR
```

Las `SUGGESTION` no forman parte del score histórico principal porque:

```text
SUGGESTION = 0 puntos perdidos
SUGGESTION = 0 Quality Gates
SUGGESTION = no bloquea 100/100
```

Pueden conservarse únicamente como contexto opcional en el informe.

---

# 13. Confianza

Registrar:

```text
ALTA
MEDIA
BAJA
```

Un aumento de score acompañado de caída importante de confianza debe interpretarse con cautela.

---

# 14. Commit como referencia

El commit debe ser la referencia principal siempre que exista.

Preferir:

```text
a12b34c
```

frente a depender únicamente de:

```text
develop
main
```

porque las ramas cambian con el tiempo.

---

# 15. Tags

Cuando una auditoría corresponda a una release estable:

registrar el tag.

Ejemplo:

```text
v1.0.0
```

Esto permite conocer la calidad de cada versión publicada.

---

# 16. Evolución hacia 100

El historial debe permitir observar algo como:

```text
72
↓
84
↓
93
↓
98
↓
100
```

Pero el objetivo no es maximizar mecánicamente la cifra.

Debe observarse también:

* severidades;
* confianza;
* calidad de la evidencia.

---

# 17. Regresión de calidad

Si una nueva auditoría obtiene menos score:

no corregir el historial para ocultarlo.

Ejemplo:

```text
100
↓
94
```

puede representar una regresión real.

Debe investigarse.

---

# 18. Regresión crítica

Si un proyecto previamente 100/100 recibe posteriormente:

* BLOCKER;
* CRITICAL;
* fallo de verificación esencial;

debe registrarse inmediatamente la nueva realidad.

Un score 100 histórico no constituye garantía permanente.

---

# 19. Score de release

Para templates versionados puede ser útil garantizar:

```text
cada release estable
→ auditoría
→ score registrado
```

Esto permite saber qué versiones fueron realmente auditadas.

No es obligatorio para todos los proyectos.

---

# 20. Relación con reports

Cada fila debe apuntar preferentemente al informe correspondiente.

Ejemplo:

```text
../reports/AUDIT-2026-08-29-a12b34c-baseline.md
```

El historial resume.

El informe explica.

---

# 21. Relación con evidence

No es necesario enlazar cada evidencia desde el historial.

El flujo normal es:

```text
history
→ report
→ evidence
```

---

# 22. Auditoría cruzada

Si existen varios informes independientes para el mismo commit:

el historial oficial debe definir cuál representa el resultado aceptado.

Puede utilizar:

```text
CONSENSUS
```

como resultado oficial después de resolver divergencias.

El informe de consenso debería seguir la convención:

```text
CONSENSUS-YYYY-MM-DD-<short-commit>-<slug>.md
```

No se deben promediar notas: las divergencias se resuelven criterio por criterio mediante evidencia.

---

# 23. Historial de hallazgos

Si en el futuro se necesita trazabilidad más profunda puede incorporarse:

```text
FINDINGS_HISTORY.md
```

para seguir problemas concretos entre auditorías.

No debe crearse hasta que exista necesidad real.

---

# 24. Historial de metodología

También puede incorporarse en el futuro:

```text
FRAMEWORK_HISTORY.md
```

para registrar cambios relevantes de la metodología.

No es obligatorio en la versión inicial.

---

# 25. Mantener simplicidad

Inicialmente basta con:

```text
SCORE_HISTORY.md
```

No crear sistemas adicionales de métricas hasta que exista una necesidad demostrada.

---

# 26. Primera auditoría

En la primera auditoría completa, consistente y confiable:

crear:

```text
.audit/history/SCORE_HISTORY.md
```

y registrar la primera línea base oficial.

Estado:

```text
BASELINE
```

Si la primera auditoría es un piloto y revela defectos de la metodología:

```text
BASELINE PROVISIONAL
```

puede conservarse como registro histórico, pero no debe convertirse en línea base oficial.

La baseline oficial será la primera auditoría posterior que utilice el framework corregido y pase todas las validaciones de consistencia.

---

# 27. Baseline

La primera auditoría completa, metodológicamente consistente y confiable debe considerarse:

```text
BASELINE
```

No importa si obtiene:

```text
43
68
87
99
```

Su función es medir la realidad inicial.

No debe manipularse para obtener una línea base favorable.

Requisitos mínimos para una baseline oficial:

```text
[ ] commit/estado identificado
[ ] framework y perfil identificados
[ ] auditoría completa
[ ] consistencia metodológica PASS
[ ] camino a 100 matemáticamente consistente cuando score < 100
[ ] informe y evidencia relacionados
[ ] confianza suficiente para el alcance declarado
```

Una auditoría que falle estas condiciones debe permanecer como provisional, parcial o invalidada según corresponda.

---

# 28. Tendencia

La tendencia debe interpretarse utilizando múltiples dimensiones.

Ejemplo:

```text
Score:      84 → 92
Critical:    2 → 0
Major:       6 → 2
Confianza: ALTA → ALTA
```

representa una mejora mucho más defendible que observar únicamente:

```text
+8 puntos
```

Las auditorías `PARCIAL`, `BASELINE PROVISIONAL`, `INCONSISTENTE` o `INVALIDADA`
no deben utilizarse para calcular tendencia oficial como si fueran equivalentes a auditorías válidas.

---

# 29. Comparación entre proyectos

Los scores de distintos repositorios sólo son directamente comparables cuando utilizan:

* misma versión de `QUALITY_SCORE`;
* reglas de auditoría equivalentes;
* perfiles equivalentes o conscientemente comparables;
* niveles de evidencia razonablemente similares;
* estados metodológicos válidos.

Evitar rankings simplistas entre tipos de proyecto diferentes.

---

# 30. Estados recomendados del historial

La columna `Estado` debe utilizar valores claros.

Ejemplos:

```text
BASELINE
REAUDITORÍA
RELEASE
CONSENSUS
PILOTO
BASELINE PROVISIONAL
PARCIAL
INCONSISTENTE
INVALIDADA
```

Los estados oficiales comparables normalmente son:

```text
BASELINE
REAUDITORÍA
RELEASE
CONSENSUS
```

Los demás conservan trazabilidad pero no deben mezclarse automáticamente en la tendencia oficial.

---

# 31. Regla final

El historial debe permitir responder:

> ¿El proyecto está objetivamente mejor que antes, qué cambió y mediante qué auditoría válida podemos demostrarlo?

El historial debe preservar tanto la evolución del proyecto como la evolución del método de medición,
sin confundir una mejora real del repositorio con un cambio de rúbrica.
