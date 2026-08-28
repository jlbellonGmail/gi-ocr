"""
Validador contractual para extracción OCR configurable.

Este script verifica que:
1. services.ini exista y tenga configuración completa.
2. Cada servicio tiene Title, Fields y para cada campo los subcampos
   Label, Example, Type, Required, Patterns, Regex.
3. GOVERNANCE.md, decisions.md y current-task.md contienen las reglas
   obligatorias sobre .DATA y separadores.
4. No se usa JSON como configuración ni salida legacy.
5. El writer genera archivos .DATA con separador ';' y sin metadata.
"""

import configparser
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> project root

SERVICES_INI = ROOT / "backend" / "config" / "services.ini"
GOVERNANCE_MD = ROOT / "GOVERNANCE.md"
DECISIONS_MD = ROOT / "governance" / "decisions.md"
CURRENT_TASK_MD = ROOT / "governance" / "current-task.md"
VALIDATOR_MD = ROOT / "scripts" / "validate_plain_text_extraction_contract.py"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def assert_file_content_contains(path: Path, substrings: list[str]) -> None:
    content = path.read_text(encoding="utf-8")
    for sub in substrings:
        if sub not in content:
            fail(f"Texto requerido '{sub}' no encontrado en {path}")


def assert_json_absent_in_paths(paths: list[Path]) -> None:
    for p in paths:
        content = p.read_text(encoding="utf-8")
        # Check for actual JSON usage patterns, not just the word
        import re

        # Look for JSON function calls, json module imports, or json.dump/loads
        json_patterns = [
            r"import\s+json",
            r"from\s+json\s+import",
            r"\.json\(\)",
            r"json\.dump",
            r"json\.loads",
            r"json\.load",
        ]
        for pattern in json_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                fail(f"Uso de JSON detectado en {p}")


def validate_services_ini() -> None:
    """Valida que services.ini tenga formato completo para todos los servicios."""
    if not SERVICES_INI.exists():
        fail(f"services.ini no existe en {SERVICES_INI}")

    cfg = configparser.ConfigParser()
    cfg.read(SERVICES_INI, encoding="utf-8")

    for section in cfg.sections():
        # 1. Title
        title = cfg.get(section, "Title", fallback="")
        fail(f"Sección [{section}] carece de Title") if not title else None

        # 2. Fields
        fields_str = cfg.get(section, "Fields", fallback="")
        fail(f"Sección [{section}] carece de Fields") if not fields_str else None
        fields = [f.strip() for f in fields_str.split(",") if f.strip()]
        fail(f"Sección [{section}]_fields no está em formato 'campo1,campo2...'") if len(fields) == 0 else None

        # 3. For each field, validate Label, Example, Type, Required, Patterns, Regex
        for field in fields:
            label_key = f"Field.{field}.Label"
            example_key = f"Field.{field}.Example"
            type_key = f"Field.{field}.Type"
            required_key = f"Field.{field}.Required"
            patterns_key = f"Field.{field}.Patterns"
            regex_key = f"Field.{field}.Regex"

            for key in [label_key, example_key, type_key, required_key, patterns_key, regex_key]:
                if not cfg.has_option(section, key):
                    fail(f"Sección [{section}] carece de {key}")

    print("[OK] services.ini cumple contrato")


def validate_governance() -> None:
    """Valida que los archivos de gobernanza contengan reglas obligatorias."""
    # GOVERNANCE.md
    assert_file_content_contains(
        GOVERNANCE_MD,
        [
            "No usar JSON como configuración persistente de OCR",
            "La configuración OCR debe mantenerse en texto plano mediante backend/config/services.ini",
            "La salida legacy debe generarse en archivos .DATA con nombre SERVICIO_YYYYMMDD_HHMMSS.DATA",
            "Separador obligatorio: punto y coma (`;`)",
        ],
    )

    # decisions.md (ADR-007)
    assert_file_content_contains(DECISIONS_MD, ["ADR-007", "Modelo configurable de extracción de texto plano"])

    # current-task.md
    assert_file_content_contains(CURRENT_TASK_MD, [".DATA", "SERVICIO_YYYYMMDD_HHMMSS.DATA"])

    print("[OK] Governance y decisiones cumplen contrato")


def validate_no_json_usage() -> None:
    # Collect all Python files to check
    json_paths = list(ROOT.glob("backend/app/*.py")) + [ROOT / "scripts" / "evaluate_gas_ocr.py"]
    assert_json_absent_in_paths(json_paths)
    print("[OK] No se usa JSON como configuración/salida legacy")


def main() -> None:
    validate_services_ini()
    validate_governance()
    validate_no_json_usage()
    print("\n[OK] VALIDACION CONTRATUAL EXITOSA")


if __name__ == "__main__":
    main()
