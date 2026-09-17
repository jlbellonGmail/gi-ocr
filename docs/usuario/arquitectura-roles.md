# Arquitectura de roles

El circuito usa tres funciones intercambiables: Planner prepara la estrategia,
Builder realiza el cambio y Reviewer lo valida. La función Reviewer reúne las
comprobaciones de QA y code review sin convertir cada capacidad en un agente.

ASSESS determina riesgo y LIGHT/STANDARD/FULL determina la profundidad SDD.
Los modelos y proveedores se configuran aparte; no forman parte del nombre ni
de la responsabilidad del rol. Los controles de formato, tests, estados,
índices, CI y lifecycle siguen siendo determinísticos.
