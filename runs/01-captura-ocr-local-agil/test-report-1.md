```yaml
status: approved
attempt: 1
feedback:
  - No bloqueante: benchmark de lote (scripts/benchmark_captura.py) y E2E
    Playwright no se corrieron (requieren datos privados no versionados
    y, en el caso de Playwright, el paquete no está instalado). Ambos
    quedan como NOT_RUN explícito, no como PASS asumido — ver detalle
    abajo. No bloquean approval porque no son criterios de cierre de
    esta feature (ver spec.md, "Explícitamente fuera de alcance").
```

## Comandos ejecutados y resultado real

Entorno: worktree `../worktrees/01-captura-ocr-local-agil`, rama
`feature/01-captura-ocr-local-agil`, Python 3.14.7,
`.venv` compartido de `gi-ocr` con dependencias sincronizadas desde
`backend/requirements.txt` de esta rama (`rapidocr-onnxruntime>=1.2.3`,
`onnxruntime>=1.17.0`, `pypdfium2>=4.0.0` instaladas y confirmadas).

```
pip install -r backend/requirements.txt
  → Successfully installed flatbuffers-25.12.19 onnxruntime-1.29.0
    protobuf-7.35.1 pypdfium2-5.13.0 rapidocr-onnxruntime-1.2.3

pytest -q --basetemp=<dir propio, ver nota>
  → 197 passed, 6 skipped, 31 warnings in 293.23s (0:04:53)
  → exit code 0
```

Nota de entorno (heredada y ya documentada en `AGENTS.md`/`.claude/agents/qa-agent.md`):
se usó `--basetemp` propio porque el directorio temporal por defecto del
usuario (`%TEMP%\pytest-of-<usuario>`) tiene una `PermissionError` de
Windows preexistente en esta máquina, no relacionada con el código.

### Skips, con motivo verificado (no silencioso)

| Test | Motivo | Verificado |
|---|---|---|
| `tests/e2e/test_e2e_playwright.py` | `playwright` no instalado | `pytest.importorskip("playwright")` — paquete real ausente, confirmado con `pip show playwright` |
| `backend/tests/test_api_jobs.py` (1 caso) | muestra privada local no disponible | Ruta esperada `backend/tests/fixtures/_local_samples/real/...`, gitignored, no presente |
| `backend/tests/test_local_samples_real.py` (4 casos) | muestras privadas locales no disponibles | Mismo motivo, `skipif` explícito en el archivo |

Todos los skips tienen `reason=` explícito en el propio test, verificado
leyendo el código fuente (no solo el output de pytest) — no hay ningún
skip sin justificación legible.

## Cobertura de criterios de aceptación (spec.md)

| # | Criterio | Test que lo cubre | Resultado |
|---|---|---|---|
| 1 | RapidOCR/onnxruntime como motor principal | `backend/app/ocr_engine.py` importado y usado en `_startup`; sin test unitario dedicado al singleton, verificado por lectura de código | Cumple |
| 2 | Clasificación nunca asigna GAS por defecto | `backend/tests/test_classifier.py` | PASS |
| 3 | `POST /api/v1/jobs` acepta imagen/PDF, PDF con texto nativo primero | `backend/tests/test_pdf_util.py`, `test_api_jobs.py` | PASS |
| 4 | Ciclo job completo (crear→consultar→confirmar→descargar→export) | `backend/tests/test_api_jobs.py` | PASS |
| 5 | Seguridad: extensión/MIME/tamaño, sanitización, path traversal | `backend/tests/test_validators.py`, `test_security.py` | PASS |
| 6 | Watcher de `inbound/` detecta de forma segura | `backend/tests/test_inbound_watcher.py` | PASS |
| 7 | Suite previa de `develop` sin regresión | Resto de `backend/tests/` (T3.x, OCR, extracción, validación) + `tests/` (24 tests de scripts del circuito) | PASS, sin modificar |
| 8 | Tests nuevos pasan o se saltan con motivo | Ver tabla de skips arriba | PASS / SKIP justificado |
| 9 | `docs/tecnica/captura-ocr-local-agil.md` no vacío | `Assert-NonEmptyFile` (ver verificación de contrato abajo) | Cumple |
| 10 | `docs/usuario/captura-ocr-local-agil.md` no vacío | ídem | Cumple |
| 11 | `decision.md` + enlaces exactos en ambos índices | ídem | Cumple |

## Verificación empírica independiente (no solo confiar en el reporte del builder)

Se releyó directamente `backend/app/main.py` para confirmar que los
endpoints declarados en el spec existen literalmente en el código (no
solo en la documentación), y se confirmó por lectura de
`backend/app/job_queue.py` que el default real de workers es `2`
(`JobQueue(store, workers=2)`), dato que quedó documentado en
`docs/tecnica/captura-ocr-local-agil.md` en respuesta al feedback no
bloqueante de `audit-1.md`.

## Verificación del contrato común (`scripts/feature-contract.ps1`)

```powershell
. .\scripts\feature-contract.ps1
Assert-FeatureContract -Slug '01-captura-ocr-local-agil' -Title 'Captura OCR Local Ágil'
```

Resultado: **PASS** — `decision.md`, `spec.md`, doc técnico, doc usuario,
`audit-1.md` y `test-report-1.md` (este archivo) no vacíos; enlaces
exactos verificados en `docs/tecnica/index.md` y `docs/usuario/index.md`.

## Bug encontrado y corregido durante este QA (declarado, no oculto)

`scripts/feature-contract.ps1` no tenía BOM UTF-8. Bajo Windows
PowerShell 5.1 (`powershell.exe`, no `pwsh`), esto corrompía los
caracteres acentuados del template de `New-DecisionFile` (`agéntico` →
`agÃ©ntico`, mojibake). Se corrigió agregando BOM UTF-8 al archivo
(commit aparte, ver `decision.md`). Verificado regenerando `decision.md`
después de la corrección: el texto sale correcto.

## NOT_RUN, declarado explícitamente

- `scripts/benchmark_captura.py` (benchmark de lote, 400 documentos):
  no corrido. Requiere variantes sintéticas locales no versionadas.
- `tests/e2e/test_e2e_playwright.py`: no corrido (playwright no instalado
  + muestras privadas no disponibles). Ninguno de los dos es criterio de
  cierre de esta feature (ver spec.md).

## Resultado

`approved`. 197 passed, 0 failed, 6 skipped con motivo verificado.
Contrato común del circuito verificado en PASS.
