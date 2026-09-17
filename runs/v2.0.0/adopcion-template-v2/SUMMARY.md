# v2.0.0 — Adopción Template v2

Estado: adoptado y validado
Tipo: Maintenance
Template: v2.0.0
Fuente: f5d4b6cc029c34c0d0c05831bfd28134276fa167
PR: #29 (adopción), #32 y #34 (reconciliación de cierre)
Merge: #29 158aeeafa55b36cdc59e29af27ce47b29fe80179; #32 213f266aa74318ac359a8cdb4a276dd7bba57bfa; #34 8dc33fc19e14ceff8c78c9473392f81e2c1a54ce

## Alcance

Se incorporan gobernanza, SDD adaptativo, work units, evidencias, estado,
integridad, lifecycle, release readiness y roles agnósticos de proveedor.

## Compatibilidad preservada

Se mantienen backend/, frontend/, storage_bridge/, RapidOCR, fallback
EasyOCR, contratos HTTP, services.ini, formatos `.DATA`/JSON confirmado,
hashes, idempotencia, estados OCR y runs históricos.

## Validación

La suite de producto y circuito, lint, tipos, auditoría de dependencias,
adaptadores e integridad se ejecutan antes de cerrar la adopción.
