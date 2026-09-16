status: rejected
attempt: 1
feedback:
  - La evidencia CI remota para el HEAD 44a9a7c terminó correctamente en los jobs test y quality.
  - No fue posible repetir pytest, ruff ni mypy localmente porque este checkout no tiene .venv ni esas herramientas instaladas.
  - El contrato vigente no pasa en esta rama porque faltan runs/13-observabilidad-operacion/spec.md y runs/13-observabilidad-operacion/audit-1.md, además de este reporte antes de su creación.
---

# Test report 1: 13-observabilidad-operacion

## Alcance

Reporte QA de la implementación de `13-observabilidad-operacion` en el HEAD
`44a9a7c9046741e3b996d798b401c68aa94ac7b6` de
`feature/13-observabilidad-operacion`.

## Evidencia remota disponible

- CI `test`: **PASS** — run `33211209261`.
- CI `quality`: **PASS** — run `33211209261`.
- Checks observados en PR #25: `test: pass`, `quality: pass`.
- La evidencia corresponde al mismo HEAD `44a9a7c` actualmente checkoutado.

## Validaciones locales

No ejecutables en este entorno:

- `python -m pytest -q`: no ejecutado; el intérprete disponible no tiene
  instalado el módulo `pytest`.
- `ruff check ...`: no ejecutado; `ruff` no está disponible en `PATH`.
- `ruff format --check ...`: no ejecutado; `ruff` no está disponible en
  `PATH`.
- `mypy backend/app`: no ejecutado; `mypy` no está disponible en `PATH`.

No se atribuyen resultados locales a estas herramientas.

## Contrato de feature

Se ejecutó `scripts/feature-contract.ps1` sobre la rama de la PR. Resultado:

```text
Falta el archivo requerido: runs/13-observabilidad-operacion/spec.md
Falta al menos un audit-N.md en runs/13-observabilidad-operacion.
Falta al menos un test-report-N.md en runs/13-observabilidad-operacion.
```

El tercer faltante queda cubierto por este archivo; los dos primeros siguen
pendientes en el HEAD de la rama de la PR.

## Veredicto

`rejected`: la evidencia remota de tests y calidad es positiva, pero no puede
emitirse aprobación QA del contrato completo mientras la rama no contenga el
spec y la auditoría requeridos y no se repita el contrato con todos los
artefactos presentes.
