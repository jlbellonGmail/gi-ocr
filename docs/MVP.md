# MVP

## Objetivo

Construir una primera versión funcional que permita:

1. Capturar o cargar una imagen desde celular.
2. Enviarla al backend.
3. Procesarla con OCR.
4. Extraer campos definidos.
5. Mostrar resultado.
6. Guardar salida controlada.

## Caso inicial

Servicio inicial:

```text
GAS
```

Campos:

```text
n° cliente
nro medidor
periodo
a pagar hasta
importe
```

## Lo que entra en el MVP

- Frontend web simple.
- Backend FastAPI.
- OCR local inicial.
- Configuración por servicio en `services.ini`.
- Salida hacia `storage_bridge/`.

## Lo que no entra todavía

- Login.
- Base de datos.
- App móvil nativa.
- Dashboard.
- Multiusuario.
- OCR perfecto para todos los comprobantes.
- Integración definitiva con VB6.
- Google Document AI o Azure en producción.

## Criterio de MVP aceptado

El MVP se considera aceptado cuando:

1. Se sube una imagen de comprobante GAS.
2. El backend procesa la imagen.
3. Se obtienen al menos 2 campos útiles.
4. El usuario ve el resultado.
5. Se genera un archivo de salida controlado.
6. El flujo se puede repetir sin romper el proyecto.

