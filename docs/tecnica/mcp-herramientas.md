# MCP y herramientas externas

F10 mantiene `.agentic/mcp.json` como único catálogo declarativo. Un servidor
no se agrega por disponibilidad técnica: debe existir una capacidad concreta,
un caso de uso, permisos mínimos, riesgo y fallback. El catálogo actual está
vacío porque el template no tiene una necesidad externa demostrada.

Cada entrada declara `capability`, `mode` (`read-only`, `write` o `action`),
`risk`, `permissions`, `optional` y `load: on-demand`. La configuración de
transporte es específica del adaptador existente y no cambia la semántica de
seguridad. `.agentic/schemas/mcp.schema.json` valida la forma; el script
`scripts/mcp-tools.ps1` aplica decisiones fail-safe.

Read-only se traduce a `NETWORK_READ`; write/action a `EXTERNAL_WRITE`, según
`.agentic/security-policy.json`. Las acciones gated requieren autorización
scoped a unidad y operación. Los secretos sólo se declaran mediante el nombre
de una variable de entorno y jamás se copian a evidencia. Las capacidades no
configuradas u opcionales hacen `FALLBACK`; una dependencia requerida sin
secreto hace `BLOCKED`. El script no ejecuta la acción externa ni bypassa PR,
lifecycle o gates.

No se precargan todos los MCP y no existe dependencia con un proveedor de
modelos. El routing puede consumir este catálogo en una fase posterior.
