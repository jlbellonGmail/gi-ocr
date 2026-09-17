# Adopción Template v2.0.0 en GI-OCR

GI-OCR adopta Template v2.0.0 como capa transversal de gobernanza. La fuente
es `f5d4b6cc029c34c0d0c05831bfd28134276fa167`.

La adopción preserva el pipeline RapidOCR/ONNX, el fallback EasyOCR, FastAPI,
`services.ini`, `storage_bridge`, formatos `.DATA` y JSON confirmado,
idempotencia, hashes, estados y contratos HTTP. Los artefactos históricos de
`runs/` no se migran destructivamente.

La profundidad SDD se decide con ASSESS y puede ser LIGHT, STANDARD o FULL.
Planner, Builder y Reviewer son roles por capacidad; la configuración de
modelos es reemplazable. `STATUS.md`, `.audit/`, work units, convergence,
integridad y release readiness aportan reentrada y evidencia sin alterar el
runtime de producto.
