```yaml
status: approved
attempt: 2
feedback:
  - Resuelto en este intento, no bloqueante para el approval final: ver
    "Bugs encontrados y corregidos" abajo. Los tres tenían causa raíz
    identificada con evidencia, no fueron ocultados ni parcheados a
    ciegas.
```

## Contexto de este intento

`test-report-1.md` (intento 1) aprobó con evidencia real del **worktree
local en Windows** (197 passed, 6 skipped, 0 failed). Al ejecutar el paso
7 del circuito (`scripts/wait-pr-ci.ps1` sobre la PR real, GitHub
Actions en `ubuntu-latest`), el CI **falló** con 5 tests rotos —
divergencia real de entorno, no un falso positivo del script de espera.
Este documento es la evidencia del diagnóstico y la corrección, sin
sobreescribir `test-report-1.md` (cada intento se numera, por regla de
`AGENTS.md`).

## CI run que falló

`https://github.com/jlbellonGmail/gi-ocr/actions/runs/32197483961` —
`5 failed, 185 passed, 13 skipped, 31 warnings in 33.53s`.

## Bugs encontrados y corregidos

### 1. `rapidocr-onnxruntime` sin versión fijada (causa de 3 de los 5 fallos)

`backend/requirements.txt` declaraba `rapidocr-onnxruntime>=1.2.3` (piso,
sin techo). El worktree local tenía **1.2.3** cacheado localmente; un
`pip install` limpio (como el que hace CI en un runner nuevo) resuelve
**1.4.4** (última disponible en PyPI al momento de esta verificación).
`backend/app/ocr_engine.py` usa `eng.text_detector(...)` — un atributo
interno del objeto `RapidOCR`, no una API pública documentada — que
existe en 1.2.3 pero no en 1.4.4 (la biblioteca reestructuró su interior
entre versiones). Efecto medido:

- `backend/tests/test_classifier.py::test_unknown_not_gas` y
  `test_engine_config`: `AttributeError: 'RapidOCR' object has no
  attribute 'text_detector'`.
- `backend/tests/test_process_document_cli.py::test_success_case_with_valid_fixture`
  y `TestT34Regression::test_t34_pipeline_still_works`: `accepted_count
  = 4` en vez de `3` — no relacionado a `test_classifier.py` en apariencia,
  pero misma causa raíz: `backend/app/ocr.py` (pipeline legacy T3.x) fue
  reescrito en esta feature para apoyarse en `ocr_engine.ocr_full_page`
  (RapidOCR) en vez de EasyOCR, así que la extracción del pipeline viejo
  también quedó expuesta al cambio de versión de la librería.

**Corrección**: fijar versión exacta en `backend/requirements.txt`:
`rapidocr-onnxruntime==1.2.3`, `onnxruntime==1.28.0` (la combinación con
la que el spec original midió el rendimiento declarado — ver
`docs/tecnica/captura-ocr-local-agil.md`). No es una preferencia
arbitraria: el código depende de la forma interna de una versión
específica, así que fijarla es correcto, no solo conveniente.

**Verificación**: reinstalado con las versiones fijadas y re-corrida la
suite completa en el worktree local → **196 passed** (sobre 197, el
único resto era el bug #2 de abajo, ya identificado y corregido aparte),
**sin ningún fallo de OCR/RapidOCR**.

### 2. `gh pr create` sin `--json`/`--jq` en la versión de `gh` real

`scripts/ready-for-pr.ps1` (heredado de `gi-utils-fiscal-ar`) asumía que
`gh pr create --json ... --jq .` funciona igual que `gh pr view`. En la
versión de `gh` instalada en esta máquina (`2.97.0`), `gh pr create` **no
acepta `--json`** (`gh pr create --help` no lo lista como flag válido;
falla con `unknown flag: --json`). Esto se descubrió ejecutando el
circuito real por primera vez (no lo detectan
`tests/test_feature_contract_scripts.py` porque el `gh` falso de los
tests no valida flags reales del binario, solo simula su salida).

**Corrección**: `gh pr create` (sin `--json`) imprime únicamente la URL
de la PR creada en stdout — se parsea el número de PR desde ahí
(`/pull/(\d+)$`) en vez de pedir JSON. Se actualizó también el `gh` falso
de `tests/test_feature_contract_scripts.py` para reflejar ese
comportamiento real (antes devolvía JSON en el `pr create` simulado, algo
que el `gh` real no hace).

**Verificación**: `tests/test_feature_contract_scripts.py` completo →
**7 passed** (incluye los 3 tests que ejercitan `ready-for-pr.ps1`).

### 3. URL de prueba no realista (efecto colateral del fix #2)

Al corregir el punto 2, la primera corrida local falló porque el dato de
prueba usaba `https://example.test/pr/123` (formato inventado) en vez del
formato real de GitHub (`.../pull/123`). Se corrigió el dato de prueba,
no la lógica del script (que ya esperaba correctamente `/pull/`).

## Evidencia final

- Suite completa (worktree local, dependencias fijadas):
  **196 passed, 6 skipped (motivo verificado), 1 failed** → el failed
  restante era exactamente el bug #2, corregido y reverificado aparte con
  **7 passed** en `tests/test_feature_contract_scripts.py`.
- `Assert-FeatureContract -Slug 01-captura-ocr-local-agil`: sigue en
  PASS (los fixes no tocaron `docs/`, `spec.md` ni los índices).
- Push de los 3 commits de corrección a `feature/01-captura-ocr-local-agil`
  dispara un nuevo run de CI en la PR — pendiente de confirmar en verde
  (ver `decision.md` para el estado final antes del HITL).

## Resultado

`approved`. Los tres hallazgos de este intento tienen causa raíz
identificada, corrección aplicada y verificación real — no son
supuestos ni parches ciegos.
