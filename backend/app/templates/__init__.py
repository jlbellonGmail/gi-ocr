"""Plantillas de proveedores para captura OCR."""

from .providers import (
    REGISTRY,
    FieldTemplate,
    ProviderTemplate,
    all_templates,
    cevt_template,
    get_template,
    litoral_gas_template,
    unknown_template,
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
