```yaml
status: approved
attempt: 2
feedback:
  - El único hallazgo del intento 1 (afirmación fáctica incorrecta en
    docs/tecnica/seguridad-privacidad-documentos.md, sección 5/TIFF, sobre
    un test de comparación de pixel arrays vía numpy que no existía) fue
    corregido en el commit 1c08bdd. La nueva redacción es técnicamente
    precisa y verificada contra el código real y el test real (ver
    evidencia abajo). No se detectaron inconsistencias nuevas en el resto
    de ambos documentos, ni cambios no autorizados en el commit de
    corrección.
```

# Reporte QA — intento 2 — `14-seguridad-privacidad-documentos`

## Resumen del veredicto

**Approved.** El intento 1 rechazó por un único hallazgo puntual de
documentación (ver `test-report-1.md`): la sección 5 (TIFF) de
`docs/tecnica/seguridad-privacidad-documentos.md` afirmaba la existencia
de un test que comparaba pixel arrays vía `numpy` antes/después de la
anonimización, cuando el test real solo compara `.size`/`.mode`. Ese era
el único defecto encontrado — código, los 14 criterios de aceptación,
tests reales, el resto de ambos documentos, `decision.md` e índices ya
habían sido verificados como correctos en el intento 1.

`builder-agent` corrigió exclusivamente esa sección en el commit
`1c08bdd` ("docs(seguridad): corregir afirmacion de verificacion TIFF en
doc tecnica"), sin tocar código, tests, spec, `decision.md` ni índices.
Verifiqué el diff completo, el código real de `_strip_tiff_ifd0`, el test
real correspondiente, y re-corrí la suite completa de tests y el
contrato del circuito. Todo en verde.

## 1. Verificación del diff de corrección (commit `1c08bdd`)

```
git show 1c08bdd --stat
 docs/tecnica/seguridad-privacidad-documentos.md | 14 ++++++++++----
 1 file changed, 10 insertions(+), 4 deletions(-)
```

Único archivo tocado: `docs/tecnica/seguridad-privacidad-documentos.md`.
Confirmé además con `git diff --stat bea50da 1c08bdd -- docs/tecnica/... docs/usuario/... backend/` que entre el commit de implementación
(`bea50da`) y este commit de corrección **no cambió ningún archivo de
`backend/`** ni el doc de usuario — solo la sección técnica señalada.

**Texto anterior (rechazado):**
> "Esto garantiza preservación **byte a byte** de los datos de imagen
> (verificado en test comparando pixel arrays antes/después vía
> `numpy`)..."

**Texto corregido (aceptado):**
> "Esto garantiza preservación **byte a byte** de los datos de imagen, ya
> que la implementación nunca decodifica ni reescribe los píxeles (no hay
> ninguna llamada a `Image.load()`/`Image.save()` en el camino principal
> `_strip_tiff_ifd0`). El test correspondiente
> (`test_exif_anonymization_tiff_preserves_size_and_mode`) verifica la
> ausencia de degradación comparando `.size` y `.mode` del archivo fuente
> contra el resultante — la verificación suficiente para este formato,
> tal como lo define el spec — y preservación exacta del tag
> `Orientation`..."

**Verificación contra el código real** (`backend/app/exif_privacy.py`,
función `_strip_tiff_ifd0`, líneas 167-231): confirmé línea por línea que
no hay ninguna llamada a `Image.load()` ni `Image.save()` en esa función
— solo `struct.unpack`/`struct.pack` sobre bytes crudos del header/IFD0.
La única llamada a Pillow en todo el módulo TIFF vive en el *fallback* de
`_anonymize_tiff` (líneas 157-164, camino distinto, solo para estructura
no parseable), tal como el propio texto corregido aclara ("camino
principal `_strip_tiff_ifd0`"). La afirmación es precisa.

**Verificación contra el test real** (`backend/tests/test_exif_privacy.py:128-137`,
`test_exif_anonymization_tiff_preserves_size_and_mode`): el test abre la
imagen fuente y la resultante con `PIL.Image.open` y compara únicamente
`.size` y `.mode` — exactamente lo que la nueva redacción describe, ni
más ni menos. No hay ningún test en el archivo (8 tests totales, todos
leídos) que compare arrays de píxeles vía `numpy`; el texto corregido ya
no reclama esa comparación. La corrección es fácticamente exacta.

## 2. Relectura completa de ambos documentos (no solo la sección corregida)

Releí `docs/tecnica/seguridad-privacidad-documentos.md` (386 líneas) y
`docs/usuario/seguridad-privacidad-documentos.md` (159 líneas) de punta a
punta. No se introdujo ninguna inconsistencia nueva:

- La sección 5 sigue siendo consistente consigo misma: la subsección
  "TIFF: por qué se edita el IFD a nivel de bytes..." (justo antes del
  párrafo corregido) ya afirmaba que `_strip_tiff_ifd0` "nunca decodifica
  los píxeles" — el párrafo corregido ahora repite esa misma afirmación
  con el detalle adicional de qué test la respalda, sin contradecir nada
  anterior.
- El resto de las secciones (1-4: validación de uploads, permisos,
  retención/purga, redacción) no mencionan TIFF/numpy y no fueron
  tocadas por el commit — confirmado también por el diff.
- `docs/usuario/seguridad-privacidad-documentos.md` no menciona el detalle
  interno de verificación TIFF (correctamente, es doc de usuario, no
  técnica) — sin cambios, sigue correcto.
- Ambos documentos siguen enlazados exactamente en sus índices (ver
  sección 4).

## 3. Suite de tests completa (`pytest`, re-corrida tras el fix de doc)

Comando ejecutado (worktree
`D:\proyectos\worktrees\14-seguridad-privacidad-documentos`, intérprete
`D:\proyectos\gi-ocr\.venv\Scripts\python.exe`, `--basetemp` propio y
distinto del intento 1 para evitar colisión con otros circuitos
corriendo en paralelo en esta máquina):

```
python -m pytest -v backend/tests tests --basetemp="C:\Users\jlbel\AppData\Local\Temp\pytest-qa-feature14-r2"
```

Resultado: **290 passed, 8 skipped, 0 errors, 38 warnings (524.21s)** —
mismo resultado numérico que el intento 1 (esperable: el cambio fue
exclusivamente de documentación, no de código ni de tests). Los 8 skips
son los mismos ya justificados en el intento 1:
- 1 `playwright` no instalado (E2E, no relacionado).
- 4 "muestras privadas locales no disponibles" (gitignored, no
  relacionado).
- 2 tests de permisos POSIX (`test_uploaded_file_has_owner_only_permissions`,
  `test_uploads_dir_has_owner_only_permissions`), gateados con
  `@pytest.mark.skipif(os.name != "posix", ...)`, correcto en este
  entorno Windows.

Confirmé además, verificando manualmente el código y los tests fuente
(`backend/app/exif_privacy.py`, `backend/tests/test_exif_privacy.py`,
`backend/tests/test_upload_security.py`, `backend/tests/test_retention.py`,
`backend/app/main.py`, `backend/app/redaction.py`) que la integración
descrita en la documentación (puntos de escritura, orden de validación,
anonimización antes de persistir, redacción en `job_queue._process`)
coincide con la implementación real.

## 4. Contrato común (`Assert-FeatureContract`)

```powershell
. .\scripts\feature-contract.ps1
Assert-FeatureContract -Slug '14-seguridad-privacidad-documentos' -Title 'Seguridad y Privacidad de Documentos'
```

Resultado: `CONTRACT_OK` (no lanza excepción). Verificado explícitamente:

- `runs/14-seguridad-privacidad-documentos/decision.md`: existe, no vacío,
  con decisiones demostrables trazadas a código/tests concretos — sin
  cambios respecto al intento 1.
- `runs/14-seguridad-privacidad-documentos/spec.md`: existe, no vacío —
  sin cambios.
- `docs/tecnica/seguridad-privacidad-documentos.md`: existe, no vacío
  (386 líneas tras la corrección).
- `docs/usuario/seguridad-privacidad-documentos.md`: existe, no vacío
  (159 líneas) — sin cambios.
- `runs/14-seguridad-privacidad-documentos/audit-*.md`: existen (audit-1,
  audit-2, audit-3), no vacíos.
- `runs/14-seguridad-privacidad-documentos/test-report-*.md`: existe
  `test-report-1.md` (no vacío); este mismo archivo agrega
  `test-report-2.md`.
- `docs/tecnica/index.md:14` → `- [Seguridad y Privacidad de Documentos](seguridad-privacidad-documentos.md)`
  (enlace único y exacto, verificado con grep).
- `docs/usuario/index.md:12` → `- [Seguridad y Privacidad de Documentos](seguridad-privacidad-documentos.md)`
  (mismo título exacto, enlace único).
- `ROADMAP.md:166` sigue en `[ ]` (correcto: no se toca en esta etapa, es
  paso posterior del orquestador tras QA aprobado).

## 5. Verificación de "no se coló ningún cambio no autorizado"

```
git status --short   → limpio, sin cambios sin commitear en el worktree.
git log --oneline -3  → 1c08bdd (corrección de doc), bf6b2d4 (test-report-1),
                        bea50da (implementación original).
```

El commit `1c08bdd` toca únicamente `docs/tecnica/seguridad-privacidad-documentos.md`
(confirmado por `git show --stat` y por `git diff --stat` contra el commit
de implementación original). No se modificó código, tests, spec,
`decision.md`, índices ni `ROADMAP.md`.

## 6. Conclusión

No quedan re-verificaciones pendientes de los 14 criterios de aceptación
(ya se hizo completo en el intento 1; el único cambio entre intentos fue
la corrección puntual de documentación, ya validada arriba). La feature
queda `approved` para pasar a la etapa de `READY_FOR_PR`.
