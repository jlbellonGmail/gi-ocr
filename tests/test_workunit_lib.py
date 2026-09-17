import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "workunit-lib.ps1"

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
WHITESPACE_RE = re.compile(r"\s+")


def plain_output(output: str) -> str:
    # pwsh en Linux envuelve mensajes de error largos al ancho de terminal
    # e inserta un marcador "|" al inicio de cada linea continuada (el
    # "gutter" del formateador de errores). Se quita antes de colapsar
    # espacios para que el mensaje quede como una sola frase comparable.
    without_ansi = ANSI_ESCAPE_RE.sub("", output)
    without_pipes = without_ansi.replace("|", " ")
    return WHITESPACE_RE.sub(" ", without_pipes).strip()


def powershell() -> str:
    candidates = ["powershell.exe", "pwsh"] if os.name == "nt" else ["pwsh", "powershell"]
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    pytest.skip("PowerShell no esta disponible")


def run_ps(command: str, cwd: Path):
    return subprocess.run(
        [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def dot_source(cwd: Path, tail: str) -> subprocess.CompletedProcess[str]:
    return run_ps(f". '{LIB}'; {tail}", cwd)


# --------------------------------------------------------------------------
# Get-RoadmapItemState / Get-RoadmapItemStateName
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("roadmap_line", "expected_state"),
    [
        ("- [ ] 02-item-a - Uno\n", "Pending"),
        ("- [-] 02-item-a - Uno\n", "Ready"),
        ("- [x] 02-item-a - Uno\n", "Done"),
    ],
)
def test_get_roadmap_item_state_detects_single_state(tmp_path, roadmap_line, expected_state):
    (tmp_path / "r.md").write_text(roadmap_line, encoding="utf-8")
    result = dot_source(
        tmp_path,
        "$c = Get-Content r.md -Raw; Get-RoadmapItemStateName -Content $c -ItemSlug '02-item-a'",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected_state


def test_get_roadmap_item_state_missing_and_ambiguous(tmp_path):
    result = dot_source(
        tmp_path,
        "Get-RoadmapItemStateName -Content '- [ ] 99-otro - X' -ItemSlug '02-item-a'",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Missing"

    ambiguous = "- [ ] 02-item-a - Uno\n- [-] 02-item-a - Dos\n"
    result = dot_source(
        tmp_path,
        f"Get-RoadmapItemStateName -Content '{ambiguous}' -ItemSlug '02-item-a'",
    )
    assert result.stdout.strip() == "Ambiguous"


# --------------------------------------------------------------------------
# Get-WorkUnitInfo
# --------------------------------------------------------------------------


def test_get_workunit_info_feature_matches_legacy_shape(tmp_path):
    result = dot_source(
        tmp_path,
        "$i = Get-WorkUnitInfo -Slug '07-mi-feature' -Mode Feature; "
        "$i.Mode, $i.Slug, $i.Branch, $i.RunDir, $i.TechnicalDoc, $i.UserDoc, "
        "$i.TechnicalIndex, $i.UserIndex, $i.Decision, $i.Title -join '|'",
    )
    assert result.returncode == 0, result.stderr
    parts = result.stdout.strip().split("|")
    assert parts == [
        "Feature",
        "07-mi-feature",
        "feature/07-mi-feature",
        "runs/07-mi-feature",
        "docs/tecnica/mi-feature.md",
        "docs/usuario/mi-feature.md",
        "docs/tecnica/index.md",
        "docs/usuario/index.md",
        "runs/07-mi-feature/decision.md",
        "Mi Feature",
    ]


def test_get_workunit_info_feature_rejects_invalid_slug(tmp_path):
    result = dot_source(tmp_path, "Get-WorkUnitInfo -Slug 'not-numbered' -Mode Feature")
    assert result.returncode != 0
    assert "Slug invalido" in plain_output(result.stderr)


def test_get_workunit_info_milestone_shape_and_items(tmp_path):
    result = dot_source(
        tmp_path,
        "$i = Get-WorkUnitInfo -Slug 'mi-milestone' -Mode Milestone -Items @('02-item-a','03-item-b'); "
        "$i.Mode, $i.Slug, $i.Branch, $i.RunDir, $i.Manifest, $i.Decision -join '|'; "
        "'---'; "
        "($i.Items | ForEach-Object { $_.Slug }) -join ','",
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[0] == (
        "Milestone|mi-milestone|milestone/mi-milestone|runs/milestone-mi-milestone|"
        "runs/milestone-mi-milestone/work-unit.json|runs/milestone-mi-milestone/decision.md"
    )
    assert lines[-1] == "02-item-a,03-item-b"


def test_get_workunit_info_milestone_rejects_numbered_slug(tmp_path):
    result = dot_source(tmp_path, "Get-WorkUnitInfo -Slug '02-mi-milestone' -Mode Milestone -Items @('02-item-a')")
    assert result.returncode != 0
    assert "Slug de milestone invalido" in plain_output(result.stderr)


def test_get_workunit_info_milestone_reads_items_from_manifest_when_present(tmp_path):
    manifest_dir = tmp_path / "runs" / "milestone-mi-milestone"
    manifest_dir.mkdir(parents=True)
    manifest = {
        "schemaVersion": 1,
        "mode": "milestone",
        "slug": "mi-milestone",
        "items": ["02-item-a", "03-item-b"],
    }
    (manifest_dir / "work-unit.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = dot_source(
        tmp_path,
        "$i = Get-WorkUnitInfo -Slug 'mi-milestone' -Mode Milestone; ($i.Items | ForEach-Object { $_.Slug }) -join ','",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "02-item-a,03-item-b"


# --------------------------------------------------------------------------
# Read/Write-WorkUnitManifest
# --------------------------------------------------------------------------


def test_write_then_read_workunit_manifest_roundtrip(tmp_path):
    result = dot_source(
        tmp_path,
        "Write-WorkUnitManifest -Path 'runs/milestone-demo/work-unit.json' -Slug 'demo' "
        "-Items @('02-item-a','03-item-b'); "
        "$m = Read-WorkUnitManifest -Path 'runs/milestone-demo/work-unit.json'; "
        "$m.SchemaVersion, $m.Mode, $m.Slug, ($m.Items -join ',') -join '|'",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1|milestone|demo|02-item-a,03-item-b"

    manifest_path = tmp_path / "runs" / "milestone-demo" / "work-unit.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data == {
        "schemaVersion": 1,
        "mode": "milestone",
        "slug": "demo",
        "items": ["02-item-a", "03-item-b"],
    }


def test_read_workunit_manifest_missing_file_throws(tmp_path):
    result = dot_source(tmp_path, "Read-WorkUnitManifest -Path 'runs/milestone-demo/work-unit.json'")
    assert result.returncode != 0
    assert "No existe el manifest" in plain_output(result.stderr)


def test_read_workunit_manifest_rejects_wrong_mode(tmp_path):
    manifest_dir = tmp_path / "runs" / "milestone-demo"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "work-unit.json").write_text(
        json.dumps({"schemaVersion": 1, "mode": "feature", "slug": "demo", "items": ["02-item-a"]}),
        encoding="utf-8",
    )
    result = dot_source(tmp_path, "Read-WorkUnitManifest -Path 'runs/milestone-demo/work-unit.json'")
    assert result.returncode != 0
    assert "mode=milestone" in plain_output(result.stderr)


# --------------------------------------------------------------------------
# Assert-RoadmapItemsTransition
# --------------------------------------------------------------------------


def test_assert_roadmap_items_transition_all_pass(tmp_path):
    content = "- [ ] 02-item-a - Uno\n- [ ] 03-item-b - Dos\n"
    result = dot_source(
        tmp_path,
        f"Assert-RoadmapItemsTransition -Content '{content}' -Items @('02-item-a','03-item-b') "
        "-FromStates @('Pending') -ToState 'Ready'; Write-Host DONE",
    )
    assert result.returncode == 0, result.stderr
    assert "DONE" in result.stdout


def test_assert_roadmap_items_transition_one_item_wrong_state_blocks_all(tmp_path):
    content = "- [ ] 02-item-a - Uno\n- [-] 03-item-b - Dos\n"
    result = dot_source(
        tmp_path,
        f"Assert-RoadmapItemsTransition -Content '{content}' -Items @('02-item-a','03-item-b') "
        "-FromStates @('Pending') -ToState 'Ready'",
    )
    assert result.returncode != 0
    stderr = plain_output(result.stderr)
    assert "02-item-a" not in stderr.split("03-item-b")[0] or "03-item-b" in stderr
    assert "invalida" in stderr
    assert "Ningun item fue modificado" in stderr


def test_assert_roadmap_items_transition_empty_list_throws(tmp_path):
    # PowerShell rechaza una matriz vacia contra un parametro mandatory
    # antes de que el cuerpo de la funcion se ejecute (por eso el mensaje
    # de error viene del binding, no del "al menos un item" interno); en
    # ambos casos el resultado observable es el mismo: falla, sin ejecutar
    # la transicion.
    result = dot_source(
        tmp_path,
        "Assert-RoadmapItemsTransition -Content 'x' -Items @() -FromStates @('Pending') -ToState 'Ready'",
    )
    assert result.returncode != 0
