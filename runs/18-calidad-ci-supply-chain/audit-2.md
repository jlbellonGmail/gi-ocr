```yaml
status: approved
attempt: 2
feedback: []
```

## Resumen

El intento 2 resuelve los tres puntos del `audit-1.md` de forma concreta y verificable, sin introducir contradicciones nuevas ni romper la numeración interna del spec.

## Verificación punto por punto del feedback previo

**1. Descripción de `backend/requirements-dev.txt`.** Se leyó el archivo real (`backend/requirements-dev.txt`): contiene exactamente `-r requirements.txt`, `pytest>=8.0.0`, `httpx>=0.27.0`, `playwright>=1.40.0`. El spec cita ese contenido literal (Alcance, bullet "Herramientas de desarrollo separadas del runtime", y también en "Riesgos / supuestos") y ya no lo llama "archivo nuevo": dice explícitamente "ya existe en el repo" y "extiende ese archivo existente, no lo crea ni lo reemplaza". El criterio 8 deja el resultado exacto y verificable: conserva `-r requirements.txt` sin tocar, elimina `pytest>=8.0.0` y `httpx>=0.27.0` (con motivo: quedan redundantes una vez que el criterio 7 los fija en `requirements.txt`, que ya se incluye vía `-r`), agrega `ruff`, `mypy`, `pip-audit` fijados a `==`, y deja intacta sin fijar `playwright>=1.40.0` (con motivo: pertenece al scaffolding de la feature 17, aún `[ ]` en `ROADMAP.md`, confirmado por grep sobre `ROADMAP.md`). Resuelto.

**2. Justificación de excluir `requirements-dev.txt` del gate de `pip-audit`.** El spec ya no lo excluye del todo: agrega un criterio 6 nuevo con un paso de `pip-audit` informativo (no gate) contra `requirements-dev.txt`, y el bloque "Riesgos / supuestos" ("Alcance de pip-audit gate limitado a runtime, con paso informativo agregado sobre dev") justifica ambos lados de la decisión: por qué no es gate (dependencias dev no llegan a producción vía Dockerfile, y `playwright` no está fijado a versión exacta, por lo que un gate ahí sería inestable y ajeno a esta feature) y por qué sí necesita visibilidad (incluye `playwright` y, tras esta feature, el propio `pip-audit`, superficie no trivial que contradiría el propósito de "auditoría básica de vulnerabilidades" si quedara sin ningún chequeo). No deja el hueco de seguridad original: pasa de "cero visibilidad" a "visibilidad informativa declarada y verificable en CI". Resuelto de forma razonable.

**3. Revisión periódica de excepciones de `pip-audit`.** El criterio 5 ahora dice explícitamente: "Esta lista de excepciones **no es una declaración de una sola vez**: el propio archivo de excepciones ... y `docs/tecnica/calidad-ci-supply-chain.md` deben incluir, como texto explícito y verificable (por ejemplo, mediante un grep/test que confirme la presencia de la frase), la política de que la lista se revisa cada vez que se modifica `backend/requirements.txt`". Es un requisito verificable, no solo una declaración de intención. El criterio 12 (docs técnica) referencia lo mismo ("la revisión obligatoria cada vez que cambia `backend/requirements.txt`"), y el último caso borde del spec cierra el círculo explicando por qué esto evita el uso de excepciones como forma de ocultar deuda. Resuelto.

## Verificación de consistencia interna (no solo los tres puntos)

- Numeración de criterios 1–15 sin huecos ni saltos; todas las referencias cruzadas internas apuntan al criterio correcto: "ver criterio 5" (Alcance, sobre revisión de excepciones) apunta al criterio de excepciones de `pip-audit`; "ver criterio 6" (Alcance y criterio 1) apunta al paso informativo sobre `requirements-dev.txt`; "ver criterio 8" (Alcance) apunta al contenido exacto exigido de `requirements-dev.txt`. Ninguna referencia quedó desalineada tras la reescritura.
- Criterio 1 describe correctamente 5 pasos de CI (`ruff check`, `ruff format --check`, `mypy`, `pip-audit` runtime gate, `pip-audit` dev informativo), consistente con los criterios 2–6 que los detallan uno por uno.
- Se verificó `backend/requirements.txt` línea por línea: la lista de dependencias directas del criterio 7 (`fastapi`, `uvicorn`, `python-multipart`, `pydantic`, `pydantic-settings`, `Pillow`, `numpy`, `opencv-python-headless`, `pypdfium2`, `easyocr`, `pytest`, `httpx`) coincide exactamente con el archivo real, y el pin/comentario de `rapidocr-onnxruntime`/`onnxruntime` que el criterio exige preservar sigue intacto en el archivo actual.
- Se verificó `ROADMAP.md`: feature 17 (`17-pruebas-e2e-mobile-real`) sigue `[ ]` pendiente y feature 18 sigue `[ ]` pendiente, consistente con las afirmaciones del spec sobre el estado de ambas features.
- Los casos borde nuevos ("Editar `backend/requirements-dev.txt` sin notar que ya existe", "Excepción de `pip-audit` usada para ocultar deuda real") son coherentes con los criterios 5 y 8 respectivos y no contradicen ninguna otra sección.
- El resto del spec no tocado por esta ronda (exclusiones de alcance, elección de herramientas, alcance de `mypy`, `pyproject.toml` sin `[build-system]`, slug de documentación, interpretación del "ejemplo HTTP") sigue siendo coherente con los cambios introducidos; no quedó ninguna sección huérfana o contradictoria.

## Reglas duras del circuito

- Criterio 12 exige `docs/tecnica/calidad-ci-supply-chain.md` no vacío, con el detalle pedido (pasos de CI, config de `ruff`/`mypy`, estrategia de fijado, política de excepciones de `pip-audit` con revisión obligatoria, tratamiento de `requirements-dev.txt`). Cumple.
- Criterio 13 exige `docs/usuario/calidad-ci-supply-chain.md` no vacío, con propósito y ejemplo concreto de uso (comandos + salida esperada), como equivalente funcional razonable al ejemplo HTTP para una feature sin endpoint. Cumple.
- Criterio 14 exige `runs/18-calidad-ci-supply-chain/decision.md` con decisiones demostrables y evidencia de que pasa `scripts/feature-contract.ps1`. Cumple.
- Criterio 15 exige enlace exacto a `calidad-ci-supply-chain.md` en `docs/tecnica/index.md` y en `docs/usuario/index.md`, con el formato de lista ya usado (`- [Título](calidad-ci-supply-chain.md)`), consistente con lo que exige `Assert-IndexLink` en `scripts/feature-contract.ps1` (ya verificado en `audit-1.md`, sin cambios en esta ronda). Cumple.
- No aplica el rechazo automático por falta de documentación ni por falta de `decision.md`/enlaces de índice.

## Puntos ya aprobados en `audit-1.md` y no reabiertos

Alcance con límites claros y exclusiones justificadas, elección de herramientas (`ruff`/`mypy`/`pip-audit`), mitigación CRLF/LF vía `.gitattributes`, interpretación del "ejemplo HTTP" para features sin endpoint, compatibilidad del `Dockerfile` actual con el criterio 7 — ninguno de estos fue tocado por el intento 2 y siguen siendo válidos.

## Siguiente paso

Ninguno del lado del reviewer. El spec queda `approved`; corresponde avanzar a `builder-agent`.
