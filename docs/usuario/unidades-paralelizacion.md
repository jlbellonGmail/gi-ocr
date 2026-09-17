# Unidades y paralelización

Arranca cada Feature desde el checkout principal de develop con
start-work-unit.ps1. Para inspeccionar una unidad aislada:

    pwsh -File scripts/unit-lifecycle.ps1 -Action inspect -Slug 19-unidades-paralelizacion -Mode Feature -Version v2.0.0 -Json

Antes de crear o mergear una PR, ejecuta -Action reconcile. Si devuelve
BLOCKED, hay un conflicto semántico que requiere una decisión humana. Tras
una reconciliación hay que volver a ejecutar QA, Reviewer, CI e integridad.

Después del cierre remoto, -Action retry-cleanup reintenta la limpieza
pendiente. Un residual Windows vacío se registra sin confundirlo con una
unidad activa; un residual con contenido se preserva y se informa.
