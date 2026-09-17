# Tests, CI y `.audit`

La validación del template se divide en tests determinísticos de scripts y
contratos, integración del circuito, lifecycle local, wiring de product-tests
y auditoría global independiente.

CI conserva tres jobs: `circuit-tests` (pytest y adaptadores),
`product-tests` (placeholder hasta declarar stack) y
`local-reconciler-tests` (Windows, bloqueante). No se usa un modelo para
decidir un gate determinístico.

`.audit` mantiene sus normas, perfil TEMPLATE, evidencia e informes fuera de
Reviewer y de `runs/`. F06 sólo comprueba invariantes estructurales; la
puntuación y auditoría siguen siendo procesos independientes.

El reconciliador usa argumentos `-File`. En un host que mata procesos hijos al
terminar el launcher, los escenarios persistentes pueden agotar su espera;
esto se reporta como limitación ambiental y no se convierte en `continue-on-error`.
