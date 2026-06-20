from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    ".gitignore",
    ".env.example",
    "README.md",
    "ROADMAP.md",
    "GOVERNANCE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "VERSION",
    "CHANGELOG.md",
    "governance/current-task.md",
    "governance/decisions.md",
    "docs/MVP.md",
    "docs/OCR-STRATEGY.md",
    "docs/WORKFLOW-AI.md",
    "docs/ACCEPTANCE-CRITERIA.md",
    "storage_bridge/README.md",
    "backend/requirements.txt",
]


FORBIDDEN_PATHS = [
    ".ai",
    ".cursorrules",
    "app",
    "zones_detected.png",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read_text(path: str) -> str:
    full_path = ROOT / path
    return full_path.read_text(encoding="utf-8")


def assert_required_files() -> None:
    for relative_path in REQUIRED_FILES:
        full_path = ROOT / relative_path

        if not full_path.exists():
            fail(f"Falta archivo requerido: {relative_path}")

        if full_path.is_file() and full_path.stat().st_size == 0:
            fail(f"Archivo vacío no permitido: {relative_path}")


def assert_forbidden_paths_absent() -> None:
    for relative_path in FORBIDDEN_PATHS:
        full_path = ROOT / relative_path

        if full_path.exists():
            fail(f"Debe eliminarse: {relative_path}")


def assert_no_powershell_pasted_into_docs() -> None:
    files_to_check = [
        ".gitignore",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "governance/decisions.md",
    ]

    forbidden_fragments = [
        '@"',
        '"@ | Set-Content',
        "Set-Content",
    ]

    for relative_path in files_to_check:
        content = read_text(relative_path)

        for fragment in forbidden_fragments:
            if fragment in content:
                fail(f"Contenido PowerShell pegado por error en {relative_path}: {fragment}")


def assert_no_legacy_references() -> None:
    agents = read_text("AGENTS.md")

    if ".ai/" in agents or ".ai\\" in agents:
        fail("AGENTS.md no debe referenciar .ai/")

    governance = read_text("GOVERNANCE.md")
    decisions = read_text("governance/decisions.md")

    if "Estructura del Payload de Salida" in governance:
        fail("GOVERNANCE.md no debe duplicar decisiones técnicas de payload")

    if "Flujo obligatorio por tarea" in decisions:
        fail("governance/decisions.md no debe duplicar reglas operativas")


def assert_version() -> None:
    version = read_text("VERSION").strip()

    if version != "0.1.0":
        fail(f"VERSION debe ser 0.1.0 y actualmente es: {version!r}")


def assert_requirements_match_code() -> None:
    requirements = read_text("backend/requirements.txt")

    required_packages = [
        "fastapi",
        "uvicorn",
        "python-multipart",
        "pydantic",
        "Pillow",
        "numpy",
        "opencv-python-headless",
        "easyocr",
        "pytest",
    ]

    for package in required_packages:
        if package not in requirements:
            fail(f"Falta dependencia en backend/requirements.txt: {package}")

    if "pytesseract" in requirements:
        fail("pytesseract no debe estar en requirements mientras el código use EasyOCR")


def assert_storage_bridge_clean() -> None:
    allowed_names = {".gitkeep"}

    folders = [
        ROOT / "storage_bridge" / "inbound",
        ROOT / "storage_bridge" / "ready",
        ROOT / "storage_bridge" / "failed",
    ]

    for folder in folders:
        if not folder.exists():
            fail(f"Falta carpeta: {folder.relative_to(ROOT)}")

        for child in folder.iterdir():
            if child.name not in allowed_names:
                fail(f"Archivo generado no permitido en {child.relative_to(ROOT)}")


def assert_empty_future_files_removed() -> None:
    forbidden_empty_files = [
        "backend/app/bridge_writer.py",
        "backend/app/schemas.py",
        "backend/app/services_config.py",
        "backend/test/test_bridge_writer.py",
        "backend/test/test_ocr_gas.py",
    ]

    for relative_path in forbidden_empty_files:
        full_path = ROOT / relative_path

        if full_path.exists():
            fail(f"Archivo vacío o prematuro debe eliminarse: {relative_path}")


def main() -> None:
    assert_required_files()
    assert_forbidden_paths_absent()
    assert_no_powershell_pasted_into_docs()
    assert_no_legacy_references()
    assert_version()
    assert_requirements_match_code()
    assert_storage_bridge_clean()
    assert_empty_future_files_removed()

    print("PASS: project baseline validation")


if __name__ == "__main__":
    main()
    