# Decision: 01-captura-ocr-local-agil - Captura OCR Local Ágil

## Estado

MERGE aprobado por evidencias del circuito agéntico.

## Evidencias revisadas

- `runs/01-captura-ocr-local-agil/spec.md`
- `runs/01-captura-ocr-local-agil/audit-1.md`
- `runs/01-captura-ocr-local-agil/test-report-1.md`

## Decisiones demostrables

- Motor OCR principal reemplazado: EasyOCR -> RapidOCR-onnxruntime + onnxruntime, con evidencia medida (2.35-2.57s en caliente vs ~30s de EasyOCR), resolviendo ADR-006 de docs/tecnica/arquitectura.md.
- Se prioriza esta linea de trabajo sobre feature/t4-mvp-web-operable por decision explicita del usuario (2026-08-18); T4 queda archivada en el tag archive/t4-mvp-web-operable, no descartada.
- Cambio de superficie de API aceptado: /api/v1/capture (legacy) reemplazado por /api/v1/jobs*; documentado en docs/tecnica y docs/usuario, no es una regresion de tests existentes.
- EasyOCR se conserva declarado en requirements.txt como fallback opcional, no se elimina legacy.
- Suite completa verificada en el worktree: 197 passed, 6 skipped (motivo explicito: playwright no instalado, muestras privadas no disponibles), 0 failed.
- Bug de encoding corregido durante este QA: scripts/feature-contract.ps1 no tenia BOM UTF-8 y Windows PowerShell 5.1 corrompia caracteres acentuados (agentico -> agÃ©ntico); se agrego BOM.

## Resultado

La feature queda apta para integrarse/cerrarse cuando GitHub confirme merge contra `develop` y el cierre automatico marque `ROADMAP.md`.
