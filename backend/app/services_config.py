"""
Configuración de servicios OCR basada en backend/config/services.ini.

Este módulo proporciona una capa de abstracción sobre ConfigParser para leer
la configuración de servicios desde el archivo INI plano, y valida el
esquema formal documentado en
docs/tecnica/administracion-servicios-documentos.md.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
SERVICES_INI = CONFIG_DIR / "services.ini"
REGRESSION_INI = CONFIG_DIR / "regression.ini"

# Tipos de campo permitidos por el esquema de Field.<nombre>.Type.
ALLOWED_FIELD_TYPES: Tuple[str, ...] = ("text", "amount", "date")

# Valores exactos permitidos para Field.<nombre>.Required (sin variantes
# localizadas: no "si"/"no"/"True"/"False").
ALLOWED_REQUIRED_VALUES: Tuple[str, ...] = ("true", "false")


class ServicesConfigError(ValueError):
    """Error de esquema o de lectura de services.ini con mensaje accionable.

    Nunca es una traza cruda de configparser/KeyError/re.error: siempre
    identifica sección, campo y clave exactos involucrados.
    """


class ServiceNotFoundError(ServicesConfigError):
    """El servicio solicitado no existe (como sección) en services.ini."""


def _load_parser() -> configparser.ConfigParser:
    """Carga el parser de configuración desde services.ini.

    No cachea: relee el archivo en cada llamada, por lo que cambios en
    caliente en services.ini se reflejan sin reiniciar el proceso (ver
    docs/tecnica/administracion-servicios-documentos.md, "Hot-reload").
    """
    if not SERVICES_INI.exists():
        SERVICES_INI.parent.mkdir(parents=True, exist_ok=True)
        SERVICES_INI.touch()
    cfg = configparser.ConfigParser()
    try:
        cfg.read(SERVICES_INI, encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ServicesConfigError(
            f"No se pudo leer '{SERVICES_INI}' como UTF-8: {exc}. "
            "Verificar que el archivo esté guardado en codificación UTF-8, "
            "sin BOM ni bytes inválidos."
        ) from exc
    except configparser.DuplicateSectionError as exc:
        raise ServicesConfigError(
            f"Sección duplicada '[{exc.section}]' en '{SERVICES_INI}'"
            + (f" (línea {exc.lineno})." if exc.lineno else ".")
        ) from exc
    except configparser.DuplicateOptionError as exc:
        raise ServicesConfigError(
            f"Clave duplicada '{exc.option}' en la sección '[{exc.section}]' de "
            f"'{SERVICES_INI}'" + (f" (línea {exc.lineno})." if exc.lineno else ".")
        ) from exc
    except configparser.Error as exc:
        raise ServicesConfigError(f"Error al parsear '{SERVICES_INI}': {exc}") from exc
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
    fields_str = cfg.get(service, "Fields", fallback="")
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


def get_service_field_regex(service: str) -> Dict[str, str]:
    """Devuelve, por campo, la regex declarada en Field.<nombre>.Regex.

    Este es el namespace REAL que usa extraction_engine.py para extraer
    valores (ver docs/tecnica/administracion-servicios-documentos.md).
    Es distinto de get_service_patterns()/get_service_zones(), que leen
    claves de sección en minúscula ('patterns=', 'zones=') que ningún
    services.ini real declara hoy — un tercer mecanismo muerto, no
    conectado a extracción.
    """
    cfg = _load_parser()
    if not cfg.has_section(service):
        return {}
    result: Dict[str, str] = {}
    for name in get_service_fields(service):
        value = cfg.get(service, f"Field.{name}.Regex", fallback="").strip()
        if value:
            result[name] = value
    return result


def get_service_config(service: str) -> Optional[Dict]:
    """Obtiene la configuración completa de un servicio como dict.

    Incluye "field_regex" (namespace Field.<nombre>.Regex, el mecanismo
    real usado por extraction_engine.py) además de las claves históricas
    "zones"/"patterns" (mecanismo de sección en minúscula, sin uso real
    hoy — ver get_service_field_regex()).
    """
    cfg = _load_parser()
    if not cfg.has_section(service):
        return None
    return {
        "fields": get_service_fields(service),
        "zones": get_service_zones(service),
        "patterns": get_service_patterns(service),
        "field_regex": get_service_field_regex(service),
        "raw": dict(cfg[service]),
    }


# ---------------------------------------------------------------------------
# Validación de esquema (ver docs/tecnica/administracion-servicios-documentos.md)
# ---------------------------------------------------------------------------


def _iter_field_block_names(cfg: configparser.ConfigParser, section: str) -> set:
    """Nombres de campo (en minúscula) que tienen al menos una clave
    'Field.<nombre>.*' declarada en la sección.

    ConfigParser normaliza (minúscula) los nombres de opción al leerlos,
    por lo que la comparación con 'Fields' también se hace en minúscula.
    """
    prefix = "field."
    names: set = set()
    for option in cfg.options(section):
        if not option.startswith(prefix):
            continue
        remainder = option[len(prefix) :]
        if "." not in remainder:
            continue
        name, _key = remainder.split(".", 1)
        if name:
            names.add(name)
    return names


def _validate_field_block(cfg: configparser.ConfigParser, section: str, name: str) -> None:
    """Valida el bloque Field.<name>.* dentro de una sección."""
    label = cfg.get(section, f"Field.{name}.Label", fallback="").strip()
    if not label:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': falta 'Field.{name}.Label' (no puede estar vacío)."
        )

    field_type = cfg.get(section, f"Field.{name}.Type", fallback="").strip()
    if field_type not in ALLOWED_FIELD_TYPES:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': 'Field.{name}.Type' inválido "
            f"({field_type!r}). Debe ser uno de: {', '.join(ALLOWED_FIELD_TYPES)}."
        )

    required_raw = cfg.get(section, f"Field.{name}.Required", fallback=None)
    if required_raw is None or required_raw.strip() not in ALLOWED_REQUIRED_VALUES:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': 'Field.{name}.Required' debe ser "
            f"exactamente 'true' o 'false' (valor actual: {required_raw!r})."
        )

    example = cfg.get(section, f"Field.{name}.Example", fallback="").strip()
    if not example:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': falta 'Field.{name}.Example' (no puede estar vacío)."
        )

    regex_raw = cfg.get(section, f"Field.{name}.Regex", fallback="").strip()
    if not regex_raw:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': falta 'Field.{name}.Regex' "
            "(obligatoria para todo campo — declarar únicamente "
            f"'Field.{name}.Patterns' no es suficiente, porque el motor de "
            "extracción real nunca la aplica)."
        )

    try:
        compiled = re.compile(regex_raw)
    except re.error as exc:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': 'Field.{name}.Regex' no compila "
            f"como expresión regular válida: {exc}."
        ) from exc

    if compiled.groups < 1:
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': 'Field.{name}.Regex' debe tener "
            "al menos un grupo de captura, para no capturar el match completo "
            "(incluyendo texto de anclaje) como valor."
        )

    patterns_raw = cfg.get(section, f"Field.{name}.Patterns", fallback=None)
    if patterns_raw is not None and not patterns_raw.strip():
        raise ServicesConfigError(
            f"Sección [{section}], campo '{name}': 'Field.{name}.Patterns' está "
            "declarada pero vacía (es opcional: si no se usa, quitar la clave)."
        )


def _validate_section_schema(cfg: configparser.ConfigParser, section: str) -> None:
    """Valida el esquema completo de una sección de services.ini."""
    title = cfg.get(section, "Title", fallback="").strip()
    if not title:
        raise ServicesConfigError(f"Sección [{section}]: falta la clave 'Title' (no puede estar vacía).")

    fields_raw = cfg.get(section, "Fields", fallback="").strip().strip('"')
    if not fields_raw:
        raise ServicesConfigError(
            f"Sección [{section}]: falta la clave 'Fields' o está vacía "
            "(debe listar al menos un nombre de campo separado por comas)."
        )

    field_names = [f.strip() for f in fields_raw.split(",")]
    if any(not name for name in field_names):
        raise ServicesConfigError(
            f"Sección [{section}]: 'Fields' contiene un nombre de campo vacío (revisar comas duplicadas o finales)."
        )

    seen: set = set()
    for name in field_names:
        key = name.lower()
        if key in seen:
            raise ServicesConfigError(f"Sección [{section}]: campo duplicado '{name}' en 'Fields'.")
        seen.add(key)

    declared_blocks = _iter_field_block_names(cfg, section)
    fields_lower = {name.lower() for name in field_names}
    orphans = declared_blocks - fields_lower
    if orphans:
        orphan = sorted(orphans)[0]
        raise ServicesConfigError(
            f"Sección [{section}]: existe un bloque 'Field.{orphan}.*' pero "
            f"'{orphan}' no está declarado en 'Fields' de esa sección "
            "(bloque huérfano)."
        )

    for name in field_names:
        _validate_field_block(cfg, section, name)


def validate_services_schema(cfg: Optional[configparser.ConfigParser] = None) -> None:
    """Valida el esquema formal completo de services.ini.

    No lanza ningún error si el archivo no tiene secciones (estado válido:
    "no hay servicios configurados todavía"). Levanta ServicesConfigError
    con sección/campo/clave exactos ante cualquier violación del esquema
    documentado en docs/tecnica/administracion-servicios-documentos.md.
    """
    if cfg is None:
        cfg = _load_parser()
    for section in cfg.sections():
        _validate_section_schema(cfg, section)


def _find_section_case_insensitive(cfg: configparser.ConfigParser, service: str) -> Optional[str]:
    target = service.strip().upper()
    for section in cfg.sections():
        if section.strip().upper() == target:
            return section
    return None


def _build_service_schema(cfg: configparser.ConfigParser, section: str) -> Dict[str, Any]:
    """Construye el esquema expuesto por la API a partir de una sección ya
    validada por _validate_section_schema."""
    _validate_section_schema(cfg, section)
    title = cfg.get(section, "Title").strip()
    fields_raw = cfg.get(section, "Fields").strip().strip('"')
    field_names = [f.strip() for f in fields_raw.split(",") if f.strip()]
    fields = []
    for name in field_names:
        fields.append(
            {
                "name": name,
                "label": cfg.get(section, f"Field.{name}.Label").strip(),
                "type": cfg.get(section, f"Field.{name}.Type").strip(),
                "required": cfg.get(section, f"Field.{name}.Required").strip() == "true",
                "example": cfg.get(section, f"Field.{name}.Example").strip(),
            }
        )
    return {"id": section, "title": title, "fields": fields}


def list_services_schema() -> List[Dict[str, Any]]:
    """Lista el esquema validado de todos los servicios configurados.

    services.ini sin secciones devuelve una lista vacía (estado válido),
    no un error.
    """
    cfg = _load_parser()
    return [_build_service_schema(cfg, section) for section in cfg.sections()]


def get_service_schema(service: str) -> Dict[str, Any]:
    """Devuelve el esquema validado de un único servicio.

    La búsqueda de sección es case-insensitive (mismo criterio que
    document_services.normalize_service_id: strip().upper()). Levanta
    ServiceNotFoundError si el servicio no existe como sección.
    """
    cfg = _load_parser()
    section = _find_section_case_insensitive(cfg, service)
    if section is None:
        raise ServiceNotFoundError(f"Servicio '{service}' no está configurado en services.ini.")
    return _build_service_schema(cfg, section)


def load_regression_config() -> Dict[str, Any]:
    """Carga la configuración de regresión desde regression.ini.
    
    Devuelve un dict con secciones: regression, providers, thresholds.
    """
    if not REGRESSION_INI.exists():
        return {
            "enabled": True,
            "fixtures_version": "1.0.0",
            "min_global_accuracy": 0.95,
            "min_field_accuracy": 0.90,
            "providers": {},
            "thresholds": {}
        }
    
    cfg = configparser.ConfigParser()
    cfg.read(REGRESSION_INI, encoding="utf-8")
    
    result = {}
    for section in cfg.sections():
        result[section] = dict(cfg[section])
    
    # Convertir valores
    if "regression" in result:
        reg = result["regression"]
        reg["enabled"] = reg.get("enabled", "true").lower() == "true"
        reg["min_global_accuracy"] = float(reg.get("min_global_accuracy", 0.95))
        reg["min_field_accuracy"] = float(reg.get("min_field_accuracy", 0.90))
        # Mover a nivel superior para compatibilidad con tests
        result.update(reg)
    
    if "providers" in result:
        providers = {}
        for k, v in result["providers"].items():
            providers[k] = v.lower() == "true"
        result["providers"] = providers
    
    if "thresholds" in result:
        thresholds = {}
        for k, v in result["thresholds"].items():
            thresholds[k] = float(v)
        result["thresholds"] = thresholds
    
    return result
