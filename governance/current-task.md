# Current Task

## ID

T1.4

## Nombre

Modelo configurable de extracción de texto plano OCR

## Objetivo

Implementar una arquitectura de extracción OCR configurable por texto plano, donde nuevos servicios se definen únicamente mediante configuración, sin crear nuevos archivos Python.

La salida legacy debe ser archivo plano `.DATA` con nombre `SERVICIO_YYYYMMDD_HHMMSS.DATA` y contenido con separador punto y coma (`;`).

## Rama requerida

```text
feature/configurable-extraction-model
```

## Alcance permitido

Pueden crearse/modificar únicamente:

- `backend/config/services.ini`
- `backend/app/services_config.py`
- `backend/app/extraction_engine.py`
- `backend/app/plain_text_writer.py`
- `backend/tests/test_services_config.py`
- `backend/tests/test_extraction_engine.py`
- `backend/tests/test_plain_text_writer.py`
- `scripts/evaluate_gas_ocr.py`
- `scripts/validate_plain_text_extraction_contract.py`
- `scripts/validate_project.py`
- `GOVERNANCE.md`
- `governance/decisions.md`
- `governance/current-task.md`
- `docs/OCR-STRATEGY.md`
- `docs/ACCEPTANCE-CRITERIA.md`

## Alcance prohibido

No modificar:

- `frontend/`
- `storage_bridge/`
- endpoints FastAPI
- motor OCR
- GitHub remoto
- tags
- imágenes reales
- reportes locales versionables

No crear:

- archivos JSON como configuración persistente
- archivos JSON como salida legacy
- nuevos extractores Python por servicio (cada servicio = solo configuración)

## Contrato de configuración (services.ini)

Cada servicio debe tener:

```ini
[SERVICIO]
Title=Título del servicio
Fields=campo1,campo2,campo3

Field.campo1.Label=Nombre del campo
Field.campo1.Example=ejemplo
Field.campo1.Type=amount|text|date
Field.campo1.Required=true|false
Field.campo1.Patterns=patrón1|patrón2
Field.campo1.Regex=expresión regular
```

## Contrato de salida .DATA

Nombre obligatorio: `SERVICIO_YYYYMMDD_HHMMSS.DATA`

Contenido:

```
campo1;campo2;campo3
valor1;valor2;valor3
```

Reglas:

- Separador obligatorio: punto y coma (`;`)
- No usar coma como separador de columnas
- No incluir `[SERVICIO]` en el contenido
- No incluir fecha/hora en el contenido (va en el nombre del archivo)
- Línea 1: nombres de campos separados por `;`
- Línea 2+: datos extraídos separados por `;`

## Tests requeridos

1. `test_services_config.py`: carga de `services.ini`, sección `[GAS]`, campos, patrones.
2. `test_extraction_engine.py`: extracción de campos usando regex desde configuración.
3. `test_plain_text_writer.py`: generación de archivo `.DATA` con nombre correcto y formato.
4. Test de servicio ficticio `CABLEVISION_TEST` definido solo por configuración.

## Validación contractual

Ejecutar:

```powershell
python scripts\validate_plain_text_extraction_contract.py
```

El validador debe verificar:

1. `backend/config/services.ini` existe.
2. Sección `[GAS]` existe.
3. `Title` existe.
4. `Fields` existe.
5. Cada campo tiene `Label`, `Example`, `Type`, `Required`, `Patterns`, `Regex`.
6. `GOVERNANCE.md` contiene regla sobre `SERVICIO_YYYYMMDD_HHMMSS.DATA`.
7. `governance/decisions.md` contiene ADR-007.
8. No hay uso de `json` como configuración ni salida legacy.
9. El writer usa `;` como separador.
10. El writer genera nombre con formato `SERVICIO_YYYYMMDD_HHMMSS.DATA`.

## Criterios de aceptación

La tarea queda lista si:

- estás en rama `feature/configurable-extraction-model`;
- `services.ini` cumple el contrato nuevo;
- governance registra la regla obligatoria;
- existe validador contractual pasando;
- `pytest backend\tests -v` pasa;
- `python scripts\evaluate_gas_ocr.py` genera `.DATA` correcto;
- no hay `json` como configuración ni salida;
- no hay extractores por servicio;
- no se toca `frontend/` ni `storage_bridge/`.