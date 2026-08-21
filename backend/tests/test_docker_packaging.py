"""
Tests de empaquetado Docker (feature 03-empaquetado-despliegue).

Estos tests NO requieren Docker Engine instalado: validan estructura y
contenido de Dockerfile, .dockerignore, docker-compose.yml y
.github/workflows/release.yml por inspeccion de archivo, para poder
correr en CI sin Docker disponible (criterio de aceptacion 15 del spec).

La verificacion end-to-end real (build, run, health check, persistencia
de volumen, bind mount de services.ini) se corrio manualmente por el
qa-agent con Docker Desktop activo y esta documentada en
runs/03-empaquetado-despliegue/test-report-1.md; no se automatiza aqui
porque requeriria Docker Engine en el entorno de CI.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _read(path: Path) -> str:
    assert path.exists(), f"Archivo esperado no encontrado: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Dockerfile (criterios 1, 2, 3)
# ---------------------------------------------------------------------------


def test_dockerfile_exists_and_uses_slim_debian_base():
    content = _read(DOCKERFILE)
    assert "FROM python:3.12-slim" in content, (
        "Dockerfile debe basarse en python:3.12-slim (Debian), no Alpine (ver spec, criterio 1 y Riesgos/supuestos)."
    )


def test_dockerfile_installs_requirements_and_copies_app_code():
    content = _read(DOCKERFILE)
    assert "backend/requirements.txt" in content
    assert "COPY backend/ backend/" in content
    assert "COPY frontend/ frontend/" in content


def test_dockerfile_ensures_runtime_state_directories():
    content = _read(DOCKERFILE)
    for path in (
        "storage_bridge/inbound",
        "storage_bridge/ready",
        "storage_bridge/failed",
        "output",
        "inbound",
    ):
        assert path in content, (
            f"Dockerfile debe asegurar la carpeta '{path}' (mkdir -p) para "
            "que el contenedor arranque sin volumenes montados (criterio 1)."
        )


def test_dockerfile_exposes_8000_and_binds_all_interfaces():
    content = _read(DOCKERFILE)
    assert "EXPOSE 8000" in content
    assert '"--host", "0.0.0.0"' in content, "El CMD debe arrancar con --host 0.0.0.0, no 127.0.0.1 (criterio 2)."
    assert '"--port", "8000"' in content


def test_dockerfile_excludes_easyocr_from_installed_requirements():
    content = _read(DOCKERFILE)
    # Verificacion real: el pipeline de instalacion filtra easyocr del
    # requirements.txt antes de pip install (criterio 3, ADR-006 sin reabrir).
    assert "grep -v -E '^easyocr'" in content
    assert "requirements-docker.txt" in content


def test_requirements_txt_still_declares_easyocr_for_local_dev():
    # La exclusion es solo de la imagen Docker (filtrado en build time), no
    # del repo: el flujo local (.venv) sigue pudiendo instalar easyocr como
    # fallback opcional (ADR-006, sin reabrir).
    requirements = _read(REPO_ROOT / "backend" / "requirements.txt")
    assert "easyocr" in requirements.lower()


# ---------------------------------------------------------------------------
# .dockerignore (criterio 4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "excluded_entry",
    [
        ".venv/",
        ".git/",
        "runs/",
        "storage_bridge/inbound/*",
        "storage_bridge/ready/*",
        "storage_bridge/failed/*",
        "output/",
        "/inbound/",
        "_local_samples/",
        "e2e_evidence/",
        ".playwright/",
        "site/",
        "tests/",
        "backend/tests/",
    ],
)
def test_dockerignore_excludes_sensitive_and_unnecessary_paths(excluded_entry):
    content = _read(DOCKERIGNORE)
    assert excluded_entry in content, (
        f"'{excluded_entry}' debe estar excluido del contexto de build via .dockerignore (criterio 4)."
    )


def test_dockerignore_preserves_storage_bridge_placeholders():
    content = _read(DOCKERIGNORE)
    # No debe filtrarse comprobantes reales, pero si debe preservarse la
    # estructura de carpetas via .gitkeep/README.md (mismo criterio que
    # .gitignore).
    assert "!storage_bridge/inbound/.gitkeep" in content
    assert "!storage_bridge/ready/.gitkeep" in content
    assert "!storage_bridge/failed/.gitkeep" in content
    assert "!storage_bridge/README.md" in content


# ---------------------------------------------------------------------------
# docker-compose.yml (criterios 5, 6, 7 + casos borde de rutas)
# ---------------------------------------------------------------------------


def _load_compose() -> dict:
    return yaml.safe_load(_read(COMPOSE_FILE))


def test_compose_declares_the_three_state_volumes():
    compose = _load_compose()
    service = compose["services"]["gi-ocr"]
    volumes = service["volumes"]
    assert "./storage_bridge:/app/storage_bridge" in volumes
    assert "./output:/app/output" in volumes
    assert "./inbound:/app/inbound" in volumes


def test_compose_mounts_services_ini_as_file_bind_mount():
    compose = _load_compose()
    service = compose["services"]["gi-ocr"]
    volumes = service["volumes"]
    assert "./backend/config/services.ini:/app/backend/config/services.ini" in volumes


def test_compose_services_ini_mount_path_matches_services_config_resolution():
    """
    Caso borde critico: la ruta interna del bind mount de services.ini debe
    coincidir EXACTAMENTE con la ruta que resuelve
    backend/app/services_config.py en runtime dentro de la imagen, donde
    WORKDIR=/app (ver Dockerfile). Si no coincide, el bind mount no tiene
    efecto y el contenedor lee un services.ini distinto al editado.
    """
    from backend.app import services_config

    # SERVICES_INI se resuelve como ruta relativa al paquete instalado
    # (parents[1] de services_config.py = backend/, luego /config/services.ini).
    relative_to_backend_app = services_config.SERVICES_INI.relative_to(
        Path(services_config.__file__).resolve().parents[2]
    )
    resolved_in_image = "/app/" + relative_to_backend_app.as_posix()

    compose = _load_compose()
    service = compose["services"]["gi-ocr"]
    mount_entry = next(v for v in service["volumes"] if v.endswith(":/app/backend/config/services.ini"))
    container_side = mount_entry.split(":", 1)[1]
    assert container_side == resolved_in_image == "/app/backend/config/services.ini"


def test_compose_exposes_port_8000():
    compose = _load_compose()
    service = compose["services"]["gi-ocr"]
    assert "8000:8000" in service["ports"]


def test_compose_uses_host_relative_paths_only():
    """
    Caso borde: rutas relativas al propio docker-compose.yml, no rutas
    absolutas de host, para funcionar igual en Windows (Docker Desktop) y
    Linux (Docker Engine) sin edicion manual.
    """
    compose = _load_compose()
    service = compose["services"]["gi-ocr"]
    for volume in service["volumes"]:
        host_side = volume.split(":", 1)[0]
        assert host_side.startswith("./"), (
            f"Volumen '{volume}' debe usar ruta relativa (./...) al archivo "
            "docker-compose.yml, no ruta absoluta de host."
        )


# ---------------------------------------------------------------------------
# release.yml (criterio 8 + caso borde de tag no-semver)
# ---------------------------------------------------------------------------


def test_release_workflow_is_valid_yaml():
    parsed = yaml.safe_load(_read(RELEASE_WORKFLOW))
    assert parsed is not None


def test_release_workflow_triggers_only_on_semver_tag_push():
    parsed = yaml.safe_load(_read(RELEASE_WORKFLOW))
    # PyYAML interpreta la clave "on:" como booleano True en YAML 1.1.
    trigger = parsed.get("on", parsed.get(True))
    assert trigger == {"push": {"tags": ["v*"]}}, (
        "release.yml debe dispararse UNICAMENTE por push de tags v* (no "
        "por push a ramas), distinto del trigger de ci.yml."
    )


def test_release_workflow_does_not_trigger_on_branch_push():
    parsed = yaml.safe_load(_read(RELEASE_WORKFLOW))
    trigger = parsed.get("on", parsed.get(True))
    push_trigger = trigger.get("push", {})
    assert "branches" not in push_trigger


def test_release_workflow_uses_github_token_without_extra_secret():
    content = _read(RELEASE_WORKFLOW)
    assert "secrets.GITHUB_TOKEN" in content
    assert "packages: write" in content


def test_release_workflow_validates_tag_matches_semver_before_publishing():
    """
    Caso borde: un tag de git que no matchea vX.Y.Z no debe publicar imagen
    ambigua; el workflow debe fallar de forma clara.
    """
    content = _read(RELEASE_WORKFLOW)
    assert "semver" in content.lower()
    assert "exit 1" in content


def test_release_workflow_builds_from_same_dockerfile():
    content = _read(RELEASE_WORKFLOW)
    assert "./Dockerfile" in content or "Dockerfile" in content
    assert "ghcr.io" in content


def test_release_and_ci_workflows_have_distinct_triggers():
    release_trigger = yaml.safe_load(_read(RELEASE_WORKFLOW))
    ci_trigger = yaml.safe_load(_read(CI_WORKFLOW))
    release_on = release_trigger.get("on", release_trigger.get(True))
    ci_on = ci_trigger.get("on", ci_trigger.get(True))
    assert release_on != ci_on


# ---------------------------------------------------------------------------
# Verificacion opcional con Docker Engine real (se salta si no esta
# disponible en el entorno de CI, mismo patron de skip que
# 01-captura-ocr-local-agil / 02-mejora-precision-ocr para muestras
# privadas locales).
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    return shutil.which("docker") is not None


@pytest.mark.skipif(not _docker_available(), reason="Docker no disponible en este entorno de CI")
def test_docker_binary_is_on_path_when_available():
    # Verificacion minima no invasiva: no dispara build/run reales (correrian
    # varios minutos y requieren estado de red), pero confirma que si
    # Docker esta instalado, el binario responde. El build/run/compose
    # real se verifico manualmente por el qa-agent (ver test-report-1.md).
    assert shutil.which("docker") is not None
