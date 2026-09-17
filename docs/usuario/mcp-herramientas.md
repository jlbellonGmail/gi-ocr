# MCP y herramientas externas

El template funciona normalmente aunque no haya MCP configurados. Sólo se
habilita una herramienta externa cuando una tarea declara una capacidad real y
su entrada pasa la validación del catálogo.

Las herramientas de lectura y las acciones de escritura se distinguen. Las
acciones externas requieren autorización con alcance explícito; los secretos
se proporcionan por el mecanismo seguro del entorno y no aparecen en logs,
prompts ni reportes. Si una herramienta opcional no está disponible, el
circuito usa el fallback y deja la degradación identificable. Si es requerida,
el resultado es `BLOCKED` con diagnóstico.
