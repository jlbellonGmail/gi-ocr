# Consola de Revisión Humana — Guía de Usuario

## Qué es

La consola de revisión es la pantalla donde usted, como operador, verifica y corrige los datos que el OCR extrajo automáticamente de un comprobante (factura de gas, luz, etc.) antes de generar el archivo final que se envía al sistema legado.

## Flujo de trabajo

1. **Suba el documento** (foto, PDF, carpeta) en la sección "Cargar documentos".
2. **Espere** a que el estado en la cola pase a **"Listo"** (píldora verde).
3. **Haga clic** en el documento para abrir la consola de revisión.
4. **Revise cada campo** en la tabla (ver detalle abajo).
5. **Corrija** si el valor no coincide con la imagen.
6. **Indique el motivo** de cada corrección o rechazo.
7. **Pulse "Confirmar revisión"** al terminar.
8. **Descargue** el JSON final con el botón "Descargar JSON final".

## La consola de revisión — explicación por zonas

### 1. Visor de imagen (arriba)
- Muestra la foto/PDF del comprobante.
- **Zoom**: rueda del ratón (Ctrl + rueda) / pellizco en pantalla táctil / botones + − ⟲.
- **Mover**: arrastrar con ratón o dedo.
- Úselo para comparar el valor OCR con lo que se ve en el documento.

### 2. Texto OCR bruto (colapsable)
- Texto completo que el motor OCR leyó, sin procesar.
- Útil si un campo no aparece en la tabla: busque aquí el texto original.

### 3. Resumen de contadores
- **Aceptados**: campos que el sistema validó y confía (auto-aceptados).
- **Rechazados**: campos que el sistema detectó como inválidos (ej. fecha malformada).
- **Faltantes**: campos obligatorios que el OCR no encontró.
- **Proveedor**: servicio detectado (GAS, CEVT, etc.) y confianza.

### 4. Tabla de campos (zona principal)

| Columna | Qué muestra | Qué hace usted |
|---------|-------------|----------------|
| **Campo** | Nombre legible (ej. "Importe", "Cliente") | Solo lectura |
| **Candidato (OCR)** | Lo que el OCR leyó en la zona del campo | Solo lectura; "—" si no leyó nada |
| **Valor validado (editable)** | Valor tras validación automática (o candidato si no hay validación) | **Edite aquí** si el valor es incorrecto |
| **Decisión automática** | Badge de color: <span class="decision-badge auto">Auto-aceptado</span> <span class="decision-badge review">Requiere revisión</span> <span class="decision-badge blocked">Bloqueado</span> <span class="decision-badge missing">No encontrado</span> | Solo lectura; indica confianza del sistema |
| **Acción operador** | Selector: **Confirmado** / **Corregido** / **Sin resolver** | Elija según corresponda (ver abajo) |
| **Motivo (req. si ≠ Confirmado)** | Texto libre; prellenado con razón automática si el sistema rechazó el campo | **Obligatorio** si eligió "Corregido" o "Sin resolver" |
| **Scores** | Puntuación final (0.00–1.00) = 60% OCR + 40% extracción | Solo lectura; mayor = más confianza |

#### Qué elegir en "Acción operador"

- **Confirmado**: el valor es correcto, no toca nada. (Por defecto en campos *Auto-aceptado*).
- **Corregido**: cambió el valor en "Valor validado". Debe escribir **por qué** (ej. "OCR leyó 23.345,66; real es 23.345,56").
- **Sin resolver**: no puede confirmar ni corregir (ej. campo ilegible, tachado, no aplica). Debe escribir **motivo** (ej. "Mancha de tinta sobre el importe").

> **Regla**: el botón **"Confirmar revisión" está deshabilitado** hasta que **todos** los campos con acción *Corregido* o *Sin resolver* tengan un motivo escrito.

### 5. Acciones finales
- **Confirmar revisión**: envía sus decisiones al servidor, genera JSON confirmado.
- **Ver JSON original**: abre el resultado crudo del OCR (antes de su revisión).
- **Descargar JSON final**: (solo tras confirmar) descarga el archivo listo para `storage_bridge/`.

## Ejemplos típicos

### Caso 1: Importe con error de OCR
- **Candidato**: `$ 23.345,66`
- **Valor validado**: `$ 23.345,66` (igual, validación de formato pasó)
- **Decisión**: *Requiere revisión* (score 0.72 < umbral 0.88)
- **Usted ve en la imagen**: `$ 23.345,56`
- **Acción**: **Corregido** → edite valor a `$ 23.345,56` → motivo: "Último dígito mal leído (6 vs 5)"

### Caso 2: Fecha inválida detectada por validador
- **Candidato**: `31/02/2026`
- **Rechazado automáticamente**: razón "fecha inválida (31 feb)"
- **Valor validado**: (vacío)
- **Decisión**: *Bloqueado*
- **Usted ve en la imagen**: `28/02/2026`
- **Acción**: **Corregido** → edite a `28/02/2026` → motivo: "Validador detectó 31 feb; real es 28 feb"

### Caso 3: Campo no encontrado
- **Candidato**: —
- **Decisión**: *No encontrado*
- **Acción**: **Sin resolver** → motivo: "Medidor no visible en foto (recorte)"

## Atajos y consejos mobile

- **Desplazamiento horizontal** en la tabla: arrastre con el dedo.
- **Zoom imagen**: pellizco (pinch) o doble toque.
- **Foco en input**: toque el campo "Valor validado" → teclado numérico si es importe/fecha.
- **Navegación por teclado**: Tab avanza campo a campo; Enter en select abre opciones.

## Preguntas frecuentes

**¿Qué pasa si confirmo sin revisar todo?**
El botón no se habilita hasta que todos los campos con acción ≠ Confirmado tengan motivo. No puede saltárselo.

**¿Puedo volver a editar después de confirmar?**
No. Una vez confirmado, el JSON es inmutable. Si hay error, debe **reintentar** el job (botón "Reintentar" en la cola) y repetir la revisión.

**¿Dónde va el JSON final?**
Se guarda en `output/confirmed/` y también se copia a `storage_bridge/ready/` para que el sistema legado lo consuma.

**¿Se guarda mi motivo?**
Sí. Queda en el JSON confirmado bajo `confirmation_metadata.correction_reasons` para auditoría.

## Accesibilidad

- Contraste AA en todos los estados (badges, inputs, botones).
- Targets táctiles ≥ 44×44 px.
- Labels asociados a cada input (`<label for="...">`).
- ARIA en tabla (`role="grid"`, `scope="col"`).
- Orden de tabulación lógico: imagen → tabla fila a fila → botones.

## Referencia API (para desarrolladores)

- `GET /api/v1/jobs/{id}` — detalle del job con `structured_output`
- `GET /api/v1/jobs/{id}/image` — imagen original
- `POST /api/v1/jobs/{id}/confirm` — body: `{ "confirmed_fields": [ { "field", "state", "final_value", "reason?" } ] }`
- `GET /api/v1/jobs/{id}/download` — JSON confirmado (solo tras confirmar)