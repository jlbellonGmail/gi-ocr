```yaml
status: approved
attempt: 2
feedback:
  - Re-verificación independiente post-sincronización con develop (merge 84cc366 + fix mecánico 1693d8c) — sin regresiones detectadas en features 03/05/14/16 ya mergeadas. Suite completa, ruff, mypy, contrato de features y CI de la PR #10 confirmados en verde de forma independiente.
  - pip-audit contra backend/requirements.txt sigue sin poder ejecutarse contra el índice real de PyPI en este entorno (falla al intentar actualizar pip en un venv temporal aislado — mismo bloqueo de red/TLS documentado desde el intento 1 y en decision.md). Reproducido de nuevo, no es un fallo de la implementación ni bloqueante para esta feature.
```

# Test Report 2: 18-calidad-ci-supply-chain

QA independiente de la sincronización post-aprobación (commits `84cc366`
merge de `origin/develop` y `1693d8c` fix mecánico de lint/formato/tipos),
worktree `D:\proyectos\worktrees\18-calidad-ci-supply-chain`, rama
`feature/18-calidad-ci-supply-chain`.

## Contexto

El `test-report-1.md` (adjunto en el mismo directorio) había aprobado el
commit `ec7262d`. Después de esa aprobación se descubrió que la rama
estaba ~20 commits atrás de `develop` (le faltaban las features
`03-empaquetado-despliegue`, `05-correccion-orientacion-exif`,
`14-seguridad-privacidad-documentos` y
`16-administracion-servicios-documentos`, ya mergeadas), lo que dejó la
PR #10 en `mergeable_state: dirty`. Un builder-agent sincronizó la rama
con un merge (`84cc366`) resolviendo conflictos en `ROADMAP.md`,
`backend/app/main.py`, `backend/app/image_prep.py`,
`backend/app/services_config.py`, `docs/tecnica/index.md` y
`docs/usuario/index.md`, y aplicó fixes mecánicos de lint/formato/tipos
(`1693d8c`) sobre el código traído por ese merge. Este reporte es la
segunda verificación de QA, específicamente enfocada en confirmar que el
merge no perdió funcionalidad y que el estado sigue siendo consistente.

## 1. Suite completa de pytest (re-corrida independiente)

Comando corrido (`.venv` propio del worktree, Python 3.14.7, con
`--basetemp` propio para evitar el `PermissionError` conocido del `TEMP`
por defecto de Windows):

```
.venv/Scripts/python.exe -m pytest -v \
  --basetemp=<scratch>/pytest-basetemp backend/tests tests
```

Resultado real (no asumido del reporte del builder, corrido de nuevo por
QA):

```
341 passed, 10 skipped, 0 failed, 40 warnings in 547.21s (0:09:07)
```

Coincide con lo reportado por el builder (`341 passed, 10 skipped, 0
failed, 40 warnings en 522.31s`; la diferencia de ~25s es variabilidad de
entorno, no relevante). Los 10 `skip` son los esperados: muestras
privadas locales gitignored (`test_api_jobs.py`,
`test_local_samples_real.py` x4), permisos POSIX que no aplican en
Windows (`test_upload_security.py` x2, feature 14), y Playwright sin
navegador instalado como paquete real (`tests/e2e/test_e2e_playwright.py`
x3, feature 17). Ningún test falló. El número de tests subió de 262→341
respecto al intento 1 porque el merge trajo las suites de las features
03/05/14/16 (`test_exif_orientation.py`, `test_exif_privacy.py`,
`test_retention.py`, `test_services_admin_api.py`,
`test_services_config_schema.py`, `test_upload_security.py`), todas
pasando.

## 2. Ruff / mypy (re-corrida independiente)

Comandos del `ci.yml` actual, corridos de nuevo:

```
.venv/Scripts/ruff.exe check backend/app backend/tests scripts tests
→ All checks passed!

.venv/Scripts/ruff.exe check .
→ All checks passed!

.venv/Scripts/ruff.exe format --check backend/app backend/tests scripts tests
→ 76 files already formatted

.venv/Scripts/ruff.exe format --check .
→ 101 files already formatted

.venv/Scripts/mypy.exe backend/app
→ Success: no issues found in 29 source files
```

Todo verde, en las dos variantes de alcance que exige el spec (rutas
específicas y `.` desde la raíz).

## 3. Revisión manual de la resolución de conflictos (features 14/16)

`git show 84cc366 --stat` confirma que el merge trajo intacto el código
de las features 14 y 16: `backend/app/exif_privacy.py` (nuevo, 238
líneas), `backend/app/fs_permissions.py` (nuevo, 52 líneas),
`backend/app/redaction.py` (nuevo), `backend/app/retention.py` (nuevo,
227 líneas), `backend/app/upload_validation.py` (nuevo, 159 líneas),
`backend/app/services_config.py` (+290 líneas de esquema/validación), y
sus tests correspondientes (`test_exif_privacy.py`, `test_retention.py`,
`test_services_admin_api.py`, `test_services_config_schema.py`,
`test_upload_security.py`), todos incluidos en la corrida de pytest de
arriba con resultado verde.

Verificación puntual de que la resolución de conflictos en
`backend/app/main.py` no dejó imports/lógica huérfana:

```
grep -n "exif_privacy|fs_permissions|document_services|upload_validation" backend/app/main.py
```

confirma `from .document_services import normalize_service_id`,
`from .exif_privacy import anonymize_upload_bytes`,
`from .fs_permissions import secure_dir, secure_file`, y uso real de
`anonymize_upload_bytes`, `secure_dir`, `secure_file` en el cuerpo de
`main.py` (no solo importados, efectivamente invocados en el flujo de
subida). En `backend/app/services_config.py` se confirmaron presentes y
exportadas las funciones de esquema de la feature 16:
`_validate_field_block`, `_validate_section_schema`,
`validate_services_schema`, `_build_service_schema`,
`list_services_schema`, `get_service_schema`. Ninguna lógica de las
features 14/16 quedó eliminada, comentada o sin uso por el merge.

## 4. Fix de mypy en `backend/app/capture_pipeline.py`

Diff real del commit `1693d8c` sobre ese archivo:

```diff
-    img = Image.open(path)
+    img: Image.Image = Image.open(path)
     img, exif_applied = image_prep.apply_exif_orientation(img)
```

Es únicamente una anotación de tipo explícita (`Image.Image`) sobre la
variable `img` antes de reasignarla con el resultado de
`apply_exif_orientation()`. No cambia el valor asignado, no cambia el
orden de ejecución, no agrega ni quita ninguna llamada — es información
estática consumida solo por `mypy`, sin efecto en runtime. Confirmado
además porque la suite completa de pytest (incluyendo
`test_exif_orientation.py`, 245 líneas, específico de este flujo) sigue
pasando sin cambios.

## 5. Contrato común de features

```
Get-FeatureContractStatus -Slug '18-calidad-ci-supply-chain' \
  -Title 'Calidad de CI y Supply Chain'

Slug       : 18-calidad-ci-supply-chain
Problems   : {}
IsComplete : True
```

`docs/tecnica/calidad-ci-supply-chain.md` (333 líneas) y
`docs/usuario/calidad-ci-supply-chain.md` (134 líneas) existen y no están
vacíos. `runs/18-calidad-ci-supply-chain/decision.md` (351 líneas) fue
actualizado por el builder con una sección nueva documentando el proceso
de sincronización, comandos corridos y resultados — no quedó ornamental.

## 6. pip-audit (no bloqueante, mismo hallazgo documentado)

```
.venv/Scripts/python.exe -m pip_audit -r backend/requirements.txt
→ ERROR:pip_audit._cli:Failed to upgrade `pip`: [...python.exe, -m, pip,
  install, --upgrade, pip, wheel, setuptools]
```

Mismo bloqueo de red/TLS ya documentado desde el intento 1
(`test-report-1.md`) y en `decision.md`. `pip-audit` intenta crear un
venv temporal aislado y actualizar `pip` contra el índice real de PyPI
antes de auditar; en este entorno esa descarga falla. No es un fallo de
la implementación — el gate de CI real corre en GitHub Actions con
acceso a red, y su resultado (`quality` job) se verificó por separado en
la sección 7.

## 7. Estado real de la PR #10

```
gh pr view 10 --repo jlbellonGmail/gi-ocr \
  --json state,mergeable,mergeStateStatus,statusCheckRollup

state:            OPEN
mergeable:        MERGEABLE
mergeStateStatus: CLEAN
statusCheckRollup:
  - test    (workflow CI) → SUCCESS
  - quality (workflow CI) → SUCCESS
```

La PR pasó de `mergeable_state: dirty` (con conflictos reales) a
`MERGEABLE`/`CLEAN`. Ambos jobs de CI (`test` y `quality`, este último
incluye `ruff`, `mypy` y el gate de `pip-audit` contra
`backend/requirements.txt` con acceso real a PyPI) terminaron con
`SUCCESS`. No es responsabilidad de QA esperar más allá de este estado
observado ni disparar un nuevo run.

## Veredicto

`approved`. La sincronización con `develop` (merge `84cc366` + fix
mecánico `1693d8c`) no introdujo regresiones: la suite completa
(341/341 tests no-skip pasan, 0 fallos), `ruff check`/`ruff format
--check` (ambos alcances) y `mypy backend/app` están verdes de forma
independiente, el contrato común de la feature está completo
(`IsComplete: True`), la documentación técnica/usuario existe y no está
vacía, y la PR #10 quedó `MERGEABLE`/`CLEAN` con CI en `SUCCESS`. La
revisión manual del merge confirma que ninguna funcionalidad de las
features 14 (seguridad/privacidad de documentos) o 16 (administración de
servicios/documentos) se perdió: los imports y usos de
`exif_privacy.anonymize_upload_bytes`, `fs_permissions.secure_dir`/
`secure_file` en `main.py`, y las funciones de validación de esquema en
`services_config.py`, siguen presentes y activos. El fix de `mypy` en
`capture_pipeline.py` es una anotación de tipo pura, sin efecto en
runtime, y está cubierto por la suite de tests de orientación EXIF que
sigue pasando.
