# storage_bridge

Directorio operativo para intercambio de archivos.

## Carpetas

```text
inbound/
ready/
failed/
```

## Uso

- `inbound/`: archivos temporales o pendientes.
- `ready/`: archivos finales listos para consumir.
- `failed/`: archivos fallidos o rechazados.

## Reglas

No se versionan archivos reales generados por OCR.

Solo deben quedar versionados:

- este `README.md`;
- `.gitkeep` dentro de cada carpeta operativa.

## Nota

La escritura atómica del bridge se implementará en una tarea específica del roadmap.

