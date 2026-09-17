"""Verificaciones de estructura de
`.github/workflows/guard-develop-branch.yml`.

Sigue el mismo patrón que `tests/test_ci_workflow.py`: aserciones de
substring/regex sobre el contenido de texto plano del workflow, sin
parsear YAML (no hay `pyyaml` en requirements-dev.txt). Ver
`docs/tecnica/arquitectura.md`, decisión "Enforcement técnico de
`develop` sin branch protection nativa" (F-004 de la auditoría baseline),
y su corrección de seguridad de concurrencia (revisión post-HITL: nunca
sobrescribir un avance legítimo de `develop` con una remediación
automática).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD_WORKFLOW = ROOT / ".github" / "workflows" / "guard-develop-branch.yml"

# Header de step dentro del único job de este workflow: exactamente 6
# espacios de sangría seguidos de "- name: ". Los cuerpos de step (env,
# run, etc.) van con más sangría, así que este patrón solo matchea el
# inicio de cada step, igual que JOB_HEADER_RE en test_ci_workflow.py
# matchea solo el inicio de cada job.
STEP_HEADER_RE = re.compile(r"^      - name: ", re.MULTILINE)


def _read_guard_workflow() -> str:
    return GUARD_WORKFLOW.read_text(encoding="utf-8")


def _step_block(content: str, step_name: str) -> str:
    """Devuelve el bloque de texto del step dado (por su 'name:' exacto)
    hasta el próximo step o fin de archivo."""
    marker = f"      - name: {step_name}"
    start = content.index(marker)
    next_match = None
    for match in STEP_HEADER_RE.finditer(content, start + len(marker)):
        next_match = match
        break
    end = next_match.start() if next_match else len(content)
    return content[start:end]


def test_guard_workflow_exists():
    assert GUARD_WORKFLOW.is_file()


def test_guard_workflow_triggers_only_on_push_to_develop():
    content = _read_guard_workflow()
    assert "on:\n  push:\n    branches: [develop]" in content
    # No debe dispararse por pull_request ni por otras ramas: sería un
    # gate distinto (ese ya lo cubre ci.yml).
    assert "pull_request:" not in content


def test_guard_workflow_declares_least_privilege_permissions():
    content = _read_guard_workflow()
    assert "contents: write" in content
    assert "issues: write" in content
    # Requerido por `gh api repos/.../commits/$sha/pulls`: sin este
    # permiso, GitHub Actions devuelve 403 "Resource not accessible by
    # integration" al consultar las PR asociadas a cada commit (fallo
    # real confirmado en ejecucion), y el guard no puede clasificar
    # ningun push como legitimo o directo.
    assert "pull-requests: read" in content


def test_guard_workflow_has_concurrency_group():
    content = _read_guard_workflow()
    assert "concurrency:" in content
    assert "group: guard-develop-branch" in content


def test_guard_workflow_skips_github_actions_bot_actor():
    content = _read_guard_workflow()
    assert "github.actor != 'github-actions[bot]'" in content


def test_guard_workflow_checks_commit_pr_association_against_develop():
    content = _read_guard_workflow()
    assert "commits/$sha/pulls" in content
    assert 'select(.base.ref == "develop" and .merged_at != null)' in content


def test_guard_workflow_handles_forced_push():
    content = _read_guard_workflow()
    assert "github.event.forced" in content
    assert "force-push" in content


def test_guard_workflow_reverts_offending_commits_without_editor():
    content = _read_guard_workflow()
    assert "git revert" in content
    assert "--no-edit" in content


def test_guard_workflow_aborts_revert_on_conflict_instead_of_forcing_state():
    content = _read_guard_workflow()
    assert "git revert --abort" in content
    assert "conflict" in content


def test_guard_workflow_creates_auditable_issue_on_violation():
    content = _read_guard_workflow()
    assert "gh issue create" in content


def test_guard_workflow_fails_the_run_when_violation_detected():
    content = _read_guard_workflow()
    assert "steps.guard.outputs.violation != 'none'" in content
    assert "exit 1" in content


def test_guard_workflow_never_force_pushes_without_lease():
    content = _read_guard_workflow()
    # Ninguna línea de código (no comentario) puede contener "--force"
    # como flag suelto sin "-with-lease" pegado: esto detectaría una
    # regresión a `git push ... --force` sin protección de carrera. Los
    # comentarios explicativos que mencionan "--force" en prosa quedan
    # afuera del chequeo (no son código ejecutable).
    bare_force_lines = [
        line
        for line in content.splitlines()
        if "--force" in line and "--force-with-lease" not in line and not line.strip().startswith("#")
    ]
    assert bare_force_lines == []


def test_restore_step_uses_force_with_lease_bound_to_after():
    content = _read_guard_workflow()
    restore_block = _step_block(content, "Restaurar develop tras push forzado")
    assert "AFTER: ${{ github.event.after }}" in restore_block
    assert '--force-with-lease="develop:$AFTER"' in restore_block


def test_restore_step_checks_remote_head_before_restoring():
    content = _read_guard_workflow()
    restore_block = _step_block(content, "Restaurar develop tras push forzado")
    assert "git ls-remote origin refs/heads/develop" in restore_block
    assert '"$remote_head" != "$AFTER"' in restore_block
    assert "concurrent-update" in restore_block


def test_revert_step_fetches_latest_develop_before_reverting():
    content = _read_guard_workflow()
    revert_block = _step_block(content, "Revertir commits sin PR mergeada asociada")
    assert "git fetch origin develop" in revert_block


def test_revert_step_push_is_never_forced_and_detects_concurrent_update():
    content = _read_guard_workflow()
    revert_block = _step_block(content, "Revertir commits sin PR mergeada asociada")
    assert "git push origin HEAD:develop" in revert_block
    code_lines = [line for line in revert_block.splitlines() if not line.strip().startswith("#")]
    assert not any("--force" in line for line in code_lines)
    assert "concurrent-update" in revert_block


def test_remediation_and_incident_steps_run_even_after_a_failed_prior_step():
    content = _read_guard_workflow()
    for step_name in (
        "Revertir commits sin PR mergeada asociada",
        "Restaurar develop tras push forzado",
        "Registrar incidente auditable",
        "Marcar el run como fallido (violacion detectada)",
    ):
        block = _step_block(content, step_name)
        first_line = block.splitlines()[0]
        assert "if: always() &&" in block, (
            f"El step '{step_name}' debe usar always() en su condicion "
            f"para no saltarse si un paso previo fallo (linea: {first_line})"
        )


def test_incident_step_reports_concurrent_update_and_unresolved_states():
    content = _read_guard_workflow()
    incident_block = _step_block(content, "Registrar incidente auditable")
    assert "concurrent-update" in incident_block
    assert "REVERT_STATUS" in incident_block
    assert "RESTORE_STATUS" in incident_block
    # Si el step de remediacion no llego a reportar ningun estado (fallo
    # antes de tiempo), el incidente igual debe dejar eso explicito, no
    # crear un issue vacio o silencioso.
    assert "sin-reportar" in incident_block
