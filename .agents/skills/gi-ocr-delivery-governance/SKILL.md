# Skill: gi-ocr-delivery-governance

## Propósito

Aplicar gates de delivery para GI-OCR manteniendo calidad, evidencia y trazabilidad.

## Gates obligatorios

### 1. Feature per task

- una sola tarea abierta
- alcance explícito
- fuera de alcance explícito
- próxima tarea no iniciada

### 2. Git

- rama confirmada
- working tree limpio antes de iniciar
- diff revisado
- commit local solo con validaciones
- no push sin instrucción explícita

### 3. Documentación

- actualizar documentación solo si la tarea lo requiere
- no mezclar documentación con cambios funcionales salvo necesidad directa
- specs livianas cuando la tarea sea nueva o ambigua

### 4. Seguridad

- no exponer secretos
- no agregar credenciales
- no modificar .env real
- no agregar dependencias sin justificación
- no tocar rutas generadas o cachés

### 5. Observabilidad y evidencia

- reportar comandos reales
- reportar salidas relevantes
- distinguir PASS, FAIL, WARN y NOT_RUN
- no declarar éxito sin evidencia

### 6. OCR/DATA/storage

- mantener separación técnica
- no hardcodear reglas de negocio
- fixtures identificables
- validación semántica explícita
- storage_bridge no contaminado con salidas generadas fuera de scope

## Resultado esperado

Cierre profesional con evidencia suficiente para decidir:

- continuar
- commitear
- mergear
- cerrar
- bloquear
