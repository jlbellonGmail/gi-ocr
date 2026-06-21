# Current Task

## ID

T1.2

## Nombre

Evaluación OCR GAS con imágenes reales locales

## Objetivo

Crear un flujo local de evaluación OCR para comprobantes GAS usando imágenes reales o sanitizadas fuera del repositorio Git.

El objetivo no es lograr OCR perfecto, sino medir con evidencia si el motor actual puede extraer campos útiles desde comprobantes reales con mucha información.

## Alcance

Crear o modificar únicamente:

- `.gitignore`
- `scripts/evaluate_gas_ocr.py`
- `docs/OCR-STRATEGY.md`
- `docs/ACCEPTANCE-CRITERIA.md`
- `governance/current-task.md`
- `backend/app/ocr.py` solo si se requiere una función reutilizable mínima de OCR global o extracción regex

## Carpetas locales no versionadas

Las imágenes reales deben ubicarse en:

```text
_local_samples/gas/
```

Los reportes locales deben generarse en:

```text
_ocr_reports/
```

Estas carpetas deben estar ignoradas por Git.

## Fuera de alcance

- No modificar frontend.
- No implementar bridge atómico.
- No cambiar motor OCR.
- No subir imágenes reales al repositorio.
- No crear base de datos.
- No trabajar otros servicios distintos de GAS.
- No modificar GitHub remoto.
- No crear tag.
- No hacer refactors grandes.

## Criterios de aceptación

- `.gitignore` ignora `_local_samples/`, `_ocr_reports/` y `_debug/`.
- Existe un script local de evaluación OCR para GAS.
- El script procesa imágenes desde `_local_samples/gas/`.
- El script no falla si no hay imágenes, debe mostrar instrucción clara.
- El script genera reporte local en `_ocr_reports/`.
- El reporte incluye:
  - archivo procesado;
  - tiempo OCR;
  - cantidad de líneas OCR;
  - campos detectados;
  - campos faltantes;
  - texto OCR normalizado o resumen útil.
- `python scripts\validate_project.py` pasa.
- `pytest backend\tests -v` pasa.
- `python -m pytest backend\tests -v` pasa.
- No quedan imágenes reales ni reportes versionables.

## Campos objetivo

Prioridad:

1. importe
2. a pagar hasta
3. n° cliente
4. periodo
5. nro medidor

## Validación esperada

```powershell
python scripts\validate_project.py
pytest backend\tests -v
python -m pytest backend\tests -v
python scripts\evaluate_gas_ocr.py
git status --short
git diff --stat
```
