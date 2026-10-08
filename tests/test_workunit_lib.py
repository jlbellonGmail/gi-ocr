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


def test_assert_roadmap_items_transition_all_pass(tmp_path):
    content = "- [ ] 02-item-a - Uno\n- [ ] 03-item-b - Dos\n"
    result = dot_source(
        tmp_path,
        f"Assert-RoadmapItemsTransition -Content '{content}' -Items @('02-item-a','03-item-b') "
        "-FromStates @('Pending') -ToState 'Ready'; Write-Host DONE",
    )
    assert result.returncode == 0, result.stderr
    assert "DONE" in result.stdout


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
