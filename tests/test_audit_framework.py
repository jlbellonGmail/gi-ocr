from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / ".audit"


def read_audit(name: str) -> str:
    path = AUDIT / name
    assert path.is_file(), f"Falta artefacto normativo de .audit: {path}"
    content = path.read_text(encoding="utf-8")
    assert content.strip(), f"Artefacto de .audit vacio: {path}"
    return content


def test_audit_has_one_active_template_profile():
    template = read_audit("profiles/TEMPLATE.md")
    assert "**Estado:** Activo" in template
    assert "QUALITY_SCORE.md" in template
    assert "AUDIT_RULES.md" in template

    other_profiles = [path for path in (AUDIT / "profiles").glob("*.md") if path.name != "TEMPLATE.md"]
    assert other_profiles, "El framework debe conservar perfiles alternativos separados"
    assert all(
        "Estado: NO IMPLEMENTADO" in path.read_text(encoding="utf-8") or path.name in {"APPLICATION.md", "LIBRARY.md"}
        for path in other_profiles
    ), "El perfil TEMPLATE no debe incorporar requisitos de perfiles alternativos"


def test_audit_prompt_preserves_independent_normative_order():
    prompt = read_audit("AUDIT_PROMPT.md")
    required = [
        ".audit/README.md",
        ".audit/QUALITY_SCORE.md",
        ".audit/AUDIT_RULES.md",
        ".audit/profiles/TEMPLATE.md",
    ]
    positions = [prompt.index(item) for item in required]
    assert positions == sorted(positions), "AUDIT_PROMPT debe imponer el orden normativo"
    assert "PERFIL = TEMPLATE" in prompt
    assert "exactamente un perfil" in prompt.lower()


def test_audit_is_not_a_reviewer_or_merge_gate():
    rules = read_audit("AUDIT_RULES.md")
    prompt = read_audit("AUDIT_PROMPT.md")
    combined = f"{rules}\n{prompt}".lower()
    assert "no debe modificar" in combined or "no modificar" in combined
    assert "auditor" in combined and "correc" in combined
    assert "reviewer-agent" not in combined


def test_audit_evidence_and_reports_are_separate_from_runs():
    evidence_readme = read_audit("evidence/README.md")
    reports_readme = read_audit("reports/README.md")
    assert ".audit/evidence/" in evidence_readme
    assert ".audit/reports/" in reports_readme
    assert not (AUDIT / "runs").exists(), ".audit no debe crear un segundo runs/"
