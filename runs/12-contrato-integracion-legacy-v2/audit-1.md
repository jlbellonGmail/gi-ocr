status: approved
attempt: 1
feedback: []

# Auditoría: 12-contrato-integracion-legacy-v2 (spec.md)

## Veredicto: APPROVED

El spec cumple con todos los requisitos del circuito y las reglas de dominio OCR.

## Análisis por criterio

### 1. Criterios de documentación obligatorios (AGENTS.md) ✅
- **docs/tecnica/contrato-integracion-legacy-v2.md**: Exigido explícitamente en CA #12
- **docs/usuario/contrato-integracion-legacy-v2.md**: Exigido explícitamente en CA #13
- **runs/12-contrato-integracion-legacy-v2/decision.md**: Exigido explícitamente en CA #14
- **Enlaces en índices**: Exigido explícitamente en CA #15

### 2. Criterios de aceptación concretos y verificables ✅
Cada CA es testeable:
- CA #1-6: Formato `.DATA` v2 y JSON v2 (encoding, separador, orden, nombres) → tests de `storage_bridge_writer.py`
- CA #7: Idempotencia por nombre → test `FileExistsError` existente + nuevo test idempotencia por contenido
- CA #8: Detección duplicados por hash → nuevo test `compute_data_hash` + escaneo `ready/`
- CA #9: Reintentos con backoff → test con fallos simulados y verificación de delays
- CA #10: Estados ready/failed → tests existentes + nuevo test registro error en `failed/`
- CA #11: Reconciliación → test de integración comparando `output/confirmed/` vs `storage_bridge/ready/`
- CA #12-15: Documentación → verificación de existencia de archivos y enlaces

### 3. Reglas de dominio OCR (AGENTS.md) ✅
- Diferencia texto bruto OCR / campo candidato / campo validado / rechazado / no encontrado: respetado en pipeline actual, no alterado
- Mejora OCR declara campo/tipo/fixture/salida/validación/falsos positivos: no aplica (feature de contrato, no OCR)
- Configuración en `services.ini` (texto plano): respetado, orden de campos viene de ahí
- No versionar imágenes reales ni archivos generados en `storage_bridge/`: respetado

### 4. Arquitectura y ADRs ✅
- ADR-001 (filesystem bridge): contrato formaliza lo implícito
- ADR-005 (escritura atómica): mantenida y extendida con reintentos
- ADR-007 (config INI, salida .DATA): versionado v2 contractual
- No rompe ADR-006 (motor OCR) ni ADR-009 (Docker/release)

### 5. Casos borde cubiertos ✅
- Timestamp collision (microsegundos/secuencia)
- Servicio no configurado
- Separador/saltos en valores (validación existente documentada)
- Lectura tolerante v1, escritura v2
- Permisos filesystem
- Disco lleno
- Jobs parciales en reconciliación
- Migración v1→v2 documentada como deuda

### 6. Riesgos/supuestos explícitos ✅
- Legacy no modifica `ready/`
- `job_id` clave de correlación
- JSON confirmado no versionado en bridge (solo `.DATA`)
- Hash SHA-256 para duplicados lógicos
- Reconciliación sincrónica inicial (límite 5s documentado)
- Compatibilidad `FileExistsError` mantenida

### 7. Alcance acotado ✅
No incluye: cambio OCR, auth/TLS, backup legacy, resiliencia JobQueue. Todos explícitamente fuera de alcance con referencias a ADRs.

## Observaciones menores (no bloqueantes)

1. **CA #7 vs CA #8**: Idempotencia por nombre (existente) + idempotencia por contenido (nueva) coexisten. El spec dice "si nombre existe pero contenido difiere → error". Correcto: no sobrescribir, forzar nuevo timestamp.
2. **Timestamp en nombre**: `YYYYMMDD_HHMMSS` no incluye microsegundos. CA #7 dice "mismo timestamp (secuencia)" y casos borde mencionan microsegundos/secuencia. Implementación debe resolver: añadir `_001`, `_002` sufijo si colisión en mismo segundo.
3. **Reconciliación por job_id**: El JSON confirmado tiene `job_id` pero el `.DATA` no. La correlación requiere extraer `job_id` del JSON y buscar `.DATA` por timestamp/servicio coincidente, o añadir `job_id` en `.DATA` v2 (línea extra). El spec no lo define explícitamente → builder debe decidir y documentar en `decision.md`.

## Conclusión

Spec aprobado. Listo para builder-agent.