"""
Configuración de servicios OCR basada en backend/config/services.ini.

Este módulo proporciona una capa de abstracción sobre ConfigParser para leer
la configuración de servicios desde el archivo INI plano.
"""
from __future__ import annotations

import configparser
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
SERVICES_INI = CONFIG_DIR / "services.ini"


def _load_parser() -> configparser.ConfigParser:
    """Carga el parser de configuración desde services.ini."""
    if not SERVICES_INI.exists():
        SERVICES_INI.parent.mkdir(parents=True, exist_ok=True)
        SERVICES_INI.touch()
    cfg = configparser.ConfigParser()
    cfg.read(SERVICES_INI, encoding="utf-8")
    return cfg


def list_services() -> List[str]:
    """Devuelve la lista de nombres de servicios configurados."""
    cfg = _load_parser()
    return list(cfg.sections())


def get_service_fields(service: str) -> List[str]:
    """Obtiene la lista ordenada de campos para un servicio."""
    cfg = _load_parser()
    if not cfg.has_section(service):
        return []
    fields_str = cfg.get(service, "fields", fallback="")
    fields_str = fields_str.strip().strip('"')
    return [f.strip() for f in fields_str.split(",") if f.strip()]


def get_service_zones(service: str) -> Dict[str, Tuple[float, float, float, float]]:
    """
    Obtiene las zonas configuradas para un servicio.
    Formato: campo -> (x1%, y1%, x2%, y2%)
    """
    cfg = _load_parser()
    if not cfg.has_section(service):
        return {}
    zones_str = cfg.get(service, "zones", fallback="")
    return _parse_zones(zones_str)


def get_service_patterns(service: str) -> Dict[str, str]:
    """
    Obtiene los patrones regex configurados para un servicio.
    Formato: campo -> regex_pattern
    """
    cfg = _load_parser()
    if not cfg.has_section(service):
        return {}
    patterns_str = cfg.get(service, "patterns", fallback="")
    return _parse_patterns(patterns_str)


def _parse_zones(zones_str: str) -> Dict[str, Tuple[float, float, float, float]]:
    """Parsea string de zonas en formato campo:x1,y1,x2,y2 (porcentajes)."""
    zones: Dict[str, Tuple[float, float, float, float]] = {}
    if not zones_str or not zones_str.strip():
        return zones
    for line in zones_str.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        field, coords_str = line.split(":", 1)
        try:
            coords = tuple(float(x.strip()) for x in coords_str.split(","))
            if len(coords) == 4:
                zones[field.strip()] = coords
        except ValueError:
            continue
    return zones


def _parse_patterns(patterns_str: str) -> Dict[str, str]:
    """Parsea string de patrones en formato campo:regex_pattern."""
    patterns: Dict[str, str] = {}
    if not patterns_str or not patterns_str.strip():
        return patterns
    for line in patterns_str.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        field, pattern = line.split(":", 1)
        patterns[field.strip()] = pattern.strip()
    return patterns


def get_service_config(service: str) -> Optional[Dict]:
    """Obtiene la configuración completa de un servicio como dict."""
    cfg = _load_parser()
    if not cfg.has_section(service):
        return None
    return {
        "fields": get_service_fields(service),
        "zones": get_service_zones(service),
        "patterns": get_service_patterns(service),
        "raw": dict(cfg[service]),
    }