"""Verificaciones de estructura de .github/workflows/ci.yml.

Sigue el mismo patrón que
tests/test_feature_contract_scripts.py::test_workflow_yaml_is_valid:
aserciones de substring sobre el contenido de texto plano del workflow,
sin parsear YAML (no hay `pyyaml` en requirements-dev.txt y esta feature
no agrega esa dependencia).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

# Nombre de job top-level bajo `jobs:`: exactamente 2 espacios de sangría
# seguidos de un identificador y `:` (ej. "  circuit-tests:",
# "  product-tests:"). Los steps y sus claves van con más sangría.
JOB_HEADER_RE = re.compile(r"^  [A-Za-z0-9_-]+:", re.MULTILINE)


def _read_ci_workflow() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def _job_block(content: str, job_name: str) -> str:
    """Devuelve el bloque de texto del job dado hasta el próximo job
    top-level (o fin de archivo)."""
    marker = f"\n  {job_name}:"
    start = content.index(marker) + 1
    next_match = None
    for match in JOB_HEADER_RE.finditer(content, start + len(f"  {job_name}:")):
        next_match = match
        break
    end = next_match.start() if next_match else len(content)
    return content[start:end]


def _without_comment_lines(block: str) -> str:
    """Descarta líneas cuyo contenido (sin indentación) empieza con `#`.

    Los checks de "gate real" de este módulo buscan substrings como
    `continue-on-error` o `exit 0` en el texto crudo del job. Sin esto,
    un comentario YAML o un comentario PowerShell/shell dentro de un
    bloque `run: |` que simplemente *mencione* esos textos (por ejemplo,
    para explicar por qué el job NO los usa) produce un falso positivo:
    la aserción "no está" falla aunque la configuración real no tenga
    ese anti-patrón. Ignorar líneas comentadas sigue detectando un
    `continue-on-error`/`|| true`/`exit 0`/`if: always()` real, porque
    esos solo cuentan como configuración o código ejecutable cuando no
    están comentados.
    """
    return "\n".join(line for line in block.splitlines() if not line.strip().startswith("#"))


def test_ci_workflow_declares_circuit_tests_and_product_tests_jobs():
    content = _read_ci_workflow()
    assert "circuit-tests:" in content
    assert "product-tests:" in content


def test_circuit_tests_job_runs_pytest():
    content = _read_ci_workflow()
    circuit_block = _job_block(content, "circuit-tests")
    assert "pytest -v" in circuit_block


def test_product_tests_job_has_placeholder_marker():
    content = _read_ci_workflow()
    product_block = _job_block(content, "product-tests")
    assert "PLACEHOLDER" in product_block
    assert "docs/tecnica/arquitectura.md" in product_block


def test_validar_adaptadores_agenticos_is_a_real_gate():
    content = _read_ci_workflow()
    circuit_block = _job_block(content, "circuit-tests")
    assert "sync-agentic-adapters.ps1 -Check" in circuit_block
    assert "continue-on-error" not in _without_comment_lines(circuit_block)


def test_both_jobs_share_same_workflow_triggers():
    content = _read_ci_workflow()
    # El bloque `on:` es único a nivel de workflow (no hay overrides por
    # job); alcanza con confirmar que ninguno de los dos jobs declara un
    # `if:` propio que los excluya de algún evento.
    assert "on:\n  push:\n    branches: [develop, main]" in content
    assert "pull_request:\n    branches: [develop, main]" in content
    circuit_block = _without_comment_lines(_job_block(content, "circuit-tests"))
    product_block = _without_comment_lines(_job_block(content, "product-tests"))
    assert "if:" not in circuit_block
    assert "if:" not in product_block


def test_ci_workflow_declares_local_reconciler_tests_job():
    content = _read_ci_workflow()
    assert "local-reconciler-tests:" in content


def test_local_reconciler_tests_job_runs_on_windows():
    content = _read_ci_workflow()
    reconciler_block = _job_block(content, "local-reconciler-tests")
    assert "runs-on: windows-latest" in reconciler_block


def test_local_reconciler_tests_job_runs_the_specific_suite():
    content = _read_ci_workflow()
    reconciler_block = _job_block(content, "local-reconciler-tests")
    assert "pytest -v tests/test_local_reconciler_scripts.py" in reconciler_block


def test_local_reconciler_tests_job_is_a_real_blocking_gate():
    """F-003 (reauditoria final v1.1): el job debe quedar rojo si la suite
    falla, sin `continue-on-error` ni ningun mecanismo equivalente que
    convierta un fallo real en exito aparente.

    Ignora líneas comentadas (YAML o PowerShell/shell dentro de un
    `run: |`) antes de buscar estos substrings: un comentario que
    simplemente *mencione* uno de estos anti-patrones (por ejemplo, para
    explicar que el job no lo usa) no es la configuración real del job.
    Ver `_without_comment_lines`.
    """
    content = _read_ci_workflow()
    reconciler_block = _without_comment_lines(_job_block(content, "local-reconciler-tests"))
    assert "continue-on-error" not in reconciler_block
    assert "|| true" not in reconciler_block
    assert "exit 0" not in reconciler_block
    assert "if: always()" not in reconciler_block
