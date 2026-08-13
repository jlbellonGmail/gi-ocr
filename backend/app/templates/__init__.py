"""Plantillas de proveedores para captura OCR."""
from .providers import (
    FieldTemplate,
    ProviderTemplate,
    litoral_gas_template,
    cevt_template,
    unknown_template,
    get_template,
    all_templates,
    REGISTRY,
)

__all__ = [
    "FieldTemplate",
    "ProviderTemplate",
    "litoral_gas_template",
    "cevt_template",
    "unknown_template",
    "get_template",
    "all_templates",
    "REGISTRY",
]