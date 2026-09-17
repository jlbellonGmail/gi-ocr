# Principios del Template

Normativa estable de diseño para v2. La elección del nombre y la transición
están justificadas en [arquitectura](docs/tecnica/arquitectura.md). El
comportamiento ejecutable vigente sigue en [AGENTS.md](AGENTS.md); los
principios no habilitan anticipadamente capacidades futuras.

El Template optimiza la probabilidad de entregar correctamente cada cambio
con el mínimo costo, latencia, contexto y supervisión compatibles con su riesgo.

1. **SDD permanente, profundidad adaptativa.** Todo cambio debe tener intención
   verificable antes de implementarse. La profundidad debe responder al riesgo;
   LIGHT/STANDARD/FULL se habilitarán con sus contratos, no por omisión informal.
2. **Determinismo antes que IA.** Una operación resuelta correctamente por un
   script común debe reutilizarse; no se reproduce su validación en un prompt.
3. **Roles por capacidad.** Planner, Builder y Reviewer describen funciones.
   Modelos y proveedores son configuración reemplazable, nunca arquitectura.
4. **Complejidad proporcional.** Cada control debe justificar el riesgo que
   reduce; un cambio simple no debe pagar el costo de un sistema crítico.
5. **PR como HITL normal.** El humano decide el merge con evidencia vigente y
   CI verde; autonomía de implementación no equivale a autorización de merge.
6. **Escalamiento útil.** Sólo se solicita una decisión material no deducible,
   autorización de riesgo significativo o información indispensable ausente.
   Tests, correcciones y revisiones ordinarias continúan autónomamente.
7. **Evidencia primero.** Toda conclusión debe distinguir hechos, supuestos y
   pendientes y enlazar evidencia del cambio efectivamente evaluado.
8. **Fail-safe.** Un gate fallido o una evidencia inválida impide avanzar;
   se conserva el diagnóstico y no se fuerza el estado para aparentar éxito.
9. **Reversibilidad primero.** Se prefieren cambios aislados y recuperables;
   nunca se destruye trabajo ajeno para resolver un conflicto local.
10. **Mínimo privilegio.** Cada acción usa sólo capacidades y alcance necesarios;
    secretos y contenido externo no deben ampliar permisos implícitamente.
11. **Eficiencia de contexto y tokens.** Se entrega a cada rol el contexto
    suficiente y trazable, se reutiliza evidencia vigente y se evita releer todo.
12. **Divulgación progresiva.** La entrada operativa muestra próximo paso y
    riesgos; el detalle permanece enlazado, sin duplicar fuentes de verdad.
13. **Evaluabilidad.** El comportamiento agéntico debe poder contrastarse con
    escenarios y resultados esperados, además de los tests del producto.
14. **Observabilidad.** Toda ejecución debe permitir reconstruir estado,
    decisiones, verificación y motivo de detención sin depender de una sesión.
15. **Portabilidad.** Los contratos deben sobrevivir a cambios de herramienta
    o modelo; las limitaciones reales de plataforma se declaran y verifican.
16. **Brownfield y greenfield.** La adopción debe respetar sistemas, políticas,
    datos y convenciones existentes; no presupone un repositorio vacío.
17. **Compatibilidad justificada.** Se preservan contratos valiosos hasta probar
    una mejora y una migración reversible; no se congela una limitación por hábito.
18. **Sin complejidad accidental.** Agregar agentes, archivos o controles no
    constituye progreso por sí mismo. Una fase puede cerrar sin implementación
    si demuestra que el mecanismo existente satisface su intención.

La aplicación, permisos y métricas se definen una sola vez en
[fundamentos técnicos](docs/tecnica/fundamentos-v2.md). Una excepción debe
identificar principio, evidencia, riesgo, alcance y decisión en el expediente
del cambio; no puede autorizar secretos expuestos, evidencia inventada o un
merge decidido por el agente. Cambiar un principio requiere una PR explícita.
