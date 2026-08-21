"""Plantillas de proveedores con ROI normalizadas + anclas + regex + validadores tipados.

Las ROI usan coordenadas normalizadas [0,1] (no píxeles absolutos), tolerantes a
desplazamiento, rotación, escala, iluminación y compresión. Campo define:
  band: (y1, y2, x1, x2) centro esperado
  anchor: regex de ancla textual/posicional opcional
  extract: regex de captura del valor
  validator: función de validators.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .. import validators


@dataclass
class FieldTemplate:
    name: str
    band: Tuple[float, float, float, float]  # (y1,y2,x1,x2)
    extract: Optional[str] = None  # regex con grupo 1 para el valor
    # El validador devuelve (valor_normalizado, motivo_rechazo). El valor
    # normalizado puede ser str (fecha/periodo/cuenta/medidor) o float
    # (monto, ver validators.validate_amount); el llamador siempre lo
    # castea a str antes de guardarlo (ver capture_pipeline.py).
    validator: Optional[Callable[[str], Tuple[Optional[str] | Optional[float], Optional[str]]]] = None
    score_min: float = 0.3
    anchor: Optional[str] = None  # regex que debe aparecer cerca (texto ancla)


@dataclass
class ProviderTemplate:
    provider: str  # LITORAL_GAS, CEVT, UNKNOWN
    service: str  # GAS, ELECTRICITY, UNKNOWN
    document_type: str
    required_fields: List[str]
    fields: List[FieldTemplate]
    classify_bands: List[Tuple[float, float, float, float]] = field(default_factory=list)
    classify_keywords: List[str] = field(default_factory=list)
    files_extensions: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

    def field_by_name(self, name: str) -> Optional[FieldTemplate]:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def all_bands(self) -> List[Tuple[float, float, float, float]]:
        return [f.band for f in self.fields] + list(self.classify_bands)


def _re_imports():
    return validators


def litoral_gas_template() -> ProviderTemplate:
    return ProviderTemplate(
        provider="LITORAL_GAS",
        service="GAS",
        document_type="LITORAL_GAS_BILL",
        required_fields=[
            "provider",
            "cliente",
            "periodo",
            "comprobante",
            "fecha_emision",
            "vencimiento",
            "total",
        ],
        classify_bands=[(0.165, 0.205, 0.40, 0.62)],
        classify_keywords=["litoral gas", "litoralgas", "litoral"],
        fields=[
            FieldTemplate("provider", (0.165, 0.205, 0.40, 0.62), extract=r"(litoral\s*gas)", validator=None),
            FieldTemplate(
                "comprobante",
                (0.185, 0.215, 0.70, 0.88),
                extract=r"(\d{4}-\d{8})",
                validator=validators.validate_comprobante,
            ),
            FieldTemplate(
                "fecha_emision",
                (0.198, 0.228, 0.72, 0.86),
                extract=r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                validator=validators.validate_date,
            ),
            FieldTemplate(
                "vencimiento",
                (0.252, 0.288, 0.77, 0.90),
                extract=r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                validator=validators.validate_date,
            ),
            FieldTemplate(
                "cliente", (0.270, 0.305, 0.66, 0.82), extract=r"(\d{8,10})", validator=validators.validate_account
            ),
            FieldTemplate(
                "periodo",
                (0.265, 0.305, 0.78, 0.90),
                extract=r"(\d{1,2}[/-]\d{4})",
                validator=validators.validate_period,
            ),
            FieldTemplate(
                "total", (0.845, 0.895, 0.72, 0.90), extract=r"(\d[\d.,]{3,}\d)", validator=validators.validate_amount
            ),
        ],
    )


def cevt_template() -> ProviderTemplate:
    return ProviderTemplate(
        provider="CEVT",
        service="ELECTRICITY",
        document_type="CEVT_ELECTRICITY_BILL",
        required_fields=[
            "provider",
            "cliente",
            "medidor",
            "periodo",
            "comprobante",
            "fecha_emision",
            "vencimiento",
            "codigo_pago_electronico",
            "total",
        ],
        classify_bands=[(0.02, 0.075, 0.05, 0.46), (0.795, 0.820, 0.53, 0.66)],
        classify_keywords=["cevt", "cooperativa", "electri"],
        fields=[
            FieldTemplate(
                "comprobante",
                (0.02, 0.075, 0.45, 0.72),
                extract=r"(\d{4}-\d{8})",
                validator=validators.validate_comprobante,
            ),
            FieldTemplate(
                "periodo",
                (0.02, 0.075, 0.45, 0.72),
                extract=r"periodo[:\s]*(\d{1,2}[/-]\d{4})",
                validator=validators.validate_period,
            ),
            FieldTemplate(
                "fecha_emision",
                (0.058, 0.090, 0.55, 0.70),
                extract=r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                validator=validators.validate_date,
            ),
            FieldTemplate(
                "vencimiento",
                (0.078, 0.108, 0.55, 0.70),
                extract=r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                validator=validators.validate_date,
            ),
            FieldTemplate(
                "codigo_pago_electronico",
                (0.158, 0.188, 0.60, 0.76),
                extract=r"(\d{8,10})",
                validator=validators.validate_account,
            ),
            FieldTemplate(
                "medidor",
                (0.198, 0.238, 0.22, 0.42),
                anchor=r"medidor",
                extract=r"(\d{7,18})",
                validator=validators.validate_meter,
            ),
            FieldTemplate(
                "cliente",
                (0.478, 0.512, 0.10, 0.30),
                anchor=r"cliente",
                extract=r"(\d{8,10})",
                validator=validators.validate_account,
            ),
            FieldTemplate(
                "total", (0.320, 0.352, 0.60, 0.78), extract=r"(\d[\d.,]{3,}\d)", validator=validators.validate_amount
            ),
        ],
    )


def unknown_template() -> ProviderTemplate:
    return ProviderTemplate(
        provider="UNKNOWN",
        service="UNKNOWN",
        document_type="MANUAL_REVIEW",
        required_fields=[],
        fields=[],
        classify_bands=[],
        classify_keywords=[],
    )


REGISTRY = {
    "LITORAL_GAS": litoral_gas_template,
    "CEVT": cevt_template,
    "UNKNOWN": unknown_template,
}


def get_template(provider: str) -> ProviderTemplate:
    return REGISTRY.get(provider, unknown_template)()


def all_templates() -> List[ProviderTemplate]:
    return [litoral_gas_template(), cevt_template()]


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
