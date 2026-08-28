"""Tests contractuales del esquema de backend/config/services.ini.

Cubren los criterios de aceptación 1-11 de
runs/16-administracion-servicios-documentos/spec.md: validación de esquema
formal y la corrección del bug de desconexión entre Field.<nombre>.Regex y
extraction_engine.py.
"""

from __future__ import annotations

import pytest
from backend.app import services_config
from backend.app.extraction_engine import _extract_generic, extract_service_fields
from backend.app.services_config import ServicesConfigError, validate_services_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_ini(tmp_path, content: str, monkeypatch):
    ini_path = tmp_path / "services.ini"
    ini_path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(services_config, "SERVICES_INI", ini_path)
    return ini_path


def _valid_section(section="TEST", field="importe"):
    return (
        f"[{section}]\n"
        f"Title=Servicio de prueba\n"
        f"Fields={field}\n\n"
        f"Field.{field}.Label=Importe\n"
        f"Field.{field}.Type=amount\n"
        f"Field.{field}.Required=true\n"
        f"Field.{field}.Example=100\n"
        f"Field.{field}.Regex=importe\\D{{0,10}}(\\d+)\n"
    )


# ---------------------------------------------------------------------------
# Criterio 1: services.ini real es válido sin cambios
# ---------------------------------------------------------------------------


def test_real_services_ini_passes_schema_validation():
    """El services.ini real (GAS, CEVT) debe seguir siendo válido: los 10
    campos reales ya declaran Regex con grupo de captura."""
    validate_services_schema()


def test_services_ini_without_sections_is_valid(tmp_path, monkeypatch):
    """Cero secciones es un estado válido ('no hay servicios todavía')."""
    _write_ini(tmp_path, "", monkeypatch)
    validate_services_schema()
    assert services_config.list_services() == []


# ---------------------------------------------------------------------------
# Criterio 2: Fields vacío o ausente
# ---------------------------------------------------------------------------


def test_missing_fields_key_fails_naming_section_and_key(tmp_path, monkeypatch):
    _write_ini(tmp_path, "[TEST]\nTitle=Servicio de prueba\n", monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "Fields" in message


def test_empty_fields_key_fails(tmp_path, monkeypatch):
    _write_ini(
        tmp_path,
        "[TEST]\nTitle=Servicio de prueba\nFields=\n",
        monkeypatch,
    )
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "Fields" in message


def test_missing_title_fails(tmp_path, monkeypatch):
    _write_ini(tmp_path, "[TEST]\nFields=importe\n", monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "Title" in message


# ---------------------------------------------------------------------------
# Criterio 3: campo listado en Fields sin bloque Field.<nombre>.*
# ---------------------------------------------------------------------------


def test_field_without_block_fails_naming_section_and_field(tmp_path, monkeypatch):
    _write_ini(
        tmp_path,
        "[TEST]\nTitle=Servicio de prueba\nFields=cliente\n",
        monkeypatch,
    )
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "cliente" in message


# ---------------------------------------------------------------------------
# Criterio 4: bloque huérfano
# ---------------------------------------------------------------------------


def test_orphan_field_block_fails(tmp_path, monkeypatch):
    content = (
        _valid_section("TEST", "importe") + "\nField.huerfano.Label=Huerfano\n"
        "Field.huerfano.Type=text\n"
        "Field.huerfano.Required=false\n"
        "Field.huerfano.Example=x\n"
        "Field.huerfano.Regex=(huerfano)\n"
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "huerfano" in message


# ---------------------------------------------------------------------------
# Criterio 5: Type fuera de {text, amount, date}
# ---------------------------------------------------------------------------


def test_invalid_type_fails_listing_allowed_types(tmp_path, monkeypatch):
    content = (
        "[TEST]\nTitle=Servicio de prueba\nFields=email\n\n"
        "Field.email.Label=Email\n"
        "Field.email.Type=email\n"
        "Field.email.Required=false\n"
        "Field.email.Example=a@b.com\n"
        "Field.email.Regex=([^\\s]+@[^\\s]+)\n"
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "email" in message
    assert "text" in message and "amount" in message and "date" in message


# ---------------------------------------------------------------------------
# Criterio 6: Required distinto de true/false
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "required_line",
    [
        "Field.importe.Required=si\n",
        "Field.importe.Required=\n",
        "",  # clave ausente
    ],
)
def test_invalid_required_value_fails(tmp_path, monkeypatch, required_line):
    content = (
        "[TEST]\nTitle=Servicio de prueba\nFields=importe\n\n"
        "Field.importe.Label=Importe\n"
        "Field.importe.Type=amount\n"
        f"{required_line}"
        "Field.importe.Example=100\n"
        "Field.importe.Regex=importe\\D{0,10}(\\d+)\n"
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "Required" in message
    assert "true" in message and "false" in message


# ---------------------------------------------------------------------------
# Criterio 7: Regex inválida (no compila)
# ---------------------------------------------------------------------------


def test_invalid_regex_fails_with_re_error_message(tmp_path, monkeypatch):
    content = (
        "[TEST]\nTitle=Servicio de prueba\nFields=importe\n\n"
        "Field.importe.Label=Importe\n"
        "Field.importe.Type=amount\n"
        "Field.importe.Required=true\n"
        "Field.importe.Example=100\n"
        "Field.importe.Regex=(importe\\D{0,10}(\\d+\n"  # paréntesis sin cerrar
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "importe" in message
    assert "Regex" in message


# ---------------------------------------------------------------------------
# Criterio 8: Regex válida sin grupo de captura
# ---------------------------------------------------------------------------


def test_regex_without_capture_group_fails(tmp_path, monkeypatch):
    content = (
        "[TEST]\nTitle=Servicio de prueba\nFields=importe\n\n"
        "Field.importe.Label=Importe\n"
        "Field.importe.Type=amount\n"
        "Field.importe.Required=true\n"
        "Field.importe.Example=100\n"
        "Field.importe.Regex=\\d{4,15}\n"
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "grupo de captura" in message


# ---------------------------------------------------------------------------
# Criterio 9: Regex ausente (solo Patterns declarada)
# ---------------------------------------------------------------------------


def test_missing_regex_with_only_patterns_fails(tmp_path, monkeypatch):
    content = (
        "[TEST]\nTitle=Servicio de prueba\nFields=cliente\n\n"
        "Field.cliente.Label=Cliente\n"
        "Field.cliente.Type=text\n"
        "Field.cliente.Required=true\n"
        "Field.cliente.Example=045-987654\n"
        "Field.cliente.Patterns=cliente|nro cliente\n"
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "Regex" in message
    assert "Patterns" in message


def test_patterns_present_but_empty_fails(tmp_path, monkeypatch):
    content = (
        "[TEST]\nTitle=Servicio de prueba\nFields=importe\n\n"
        "Field.importe.Label=Importe\n"
        "Field.importe.Type=amount\n"
        "Field.importe.Required=true\n"
        "Field.importe.Example=100\n"
        "Field.importe.Regex=importe\\D{0,10}(\\d+)\n"
        "Field.importe.Patterns=\n"
    )
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    assert "Patterns" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Criterio 10: nombres de campo duplicados en Fields
# ---------------------------------------------------------------------------


def test_duplicate_field_names_in_fields_fails(tmp_path, monkeypatch):
    _write_ini(
        tmp_path,
        "[TEST]\nTitle=Servicio de prueba\nFields=importe,importe,cliente\n",
        monkeypatch,
    )
    with pytest.raises(ServicesConfigError) as exc_info:
        validate_services_schema()
    message = str(exc_info.value)
    assert "TEST" in message
    assert "importe" in message
    assert "duplicad" in message.lower()


# ---------------------------------------------------------------------------
# Criterio 11: corrección del bug de desconexión Field.<nombre>.Regex
# ---------------------------------------------------------------------------


def test_extract_generic_reproduces_the_documented_bug():
    """Reproduce el bug documentado en el spec: _extract_generic por sí
    solo captura el número de MEDIDOR en vez del número de CLIENTE para
    este texto, porque busca cualquier corrida de 8-10 dígitos sin anclaje
    de contexto."""
    text = "Medidor 12345678 Cliente 045-987654"
    assert _extract_generic("cliente", text) == "12345678"


@pytest.mark.anyio
async def test_extract_service_fields_gas_cliente_uses_declared_regex():
    """Regresión del criterio 11: extract_service_fields debe usar
    Field.cliente.Regex (anclado a la palabra 'cliente'), no
    _extract_generic (que devolvería el número de medidor)."""
    text = "Medidor 12345678 Cliente 045-987654"
    result = await extract_service_fields("GAS", text)
    assert result["fields"]["cliente"] == "045-987654"
    assert result["fields"]["cliente"] != "12345678"


@pytest.mark.anyio
async def test_extract_service_fields_cevt_uses_declared_regex():
    """Caso de regresión adicional (CEVT) pedido explícitamente por el
    criterio 11."""
    text = (
        "Medidor N\u00b0 12345 Periodo 05/2026 Vencimiento 15/12/2026 "
        "Codigo de pago electronico ABC123456 Total a pagar $ 1.234,56"
    )
    result = await extract_service_fields("CEVT", text)
    assert result["fields"]["medidor_numero"] == "12345"


@pytest.mark.anyio
async def test_extract_generic_still_used_as_fallback_without_declared_regex(tmp_path, monkeypatch):
    """_extract_generic se mantiene como fallback defensivo cuando un
    campo llega a extract_service_fields sin Field.<nombre>.Regex
    declarada (config no validada, editada a mano)."""
    content = "[TEST]\nTitle=Servicio de prueba\nFields=cliente\n\nField.cliente.Label=Cliente\n"
    _write_ini(tmp_path, content, monkeypatch)
    text = "Cliente 12345678"
    result = await extract_service_fields("TEST", text)
    # Sin Regex declarada, cae en _extract_generic (mismo comportamiento
    # de siempre, sin cambios por esta feature).
    assert result["fields"]["cliente"] == _extract_generic("cliente", text)


# ---------------------------------------------------------------------------
# Casos borde adicionales
# ---------------------------------------------------------------------------


def test_corrupt_encoding_fails_with_clear_message(tmp_path, monkeypatch):
    ini_path = tmp_path / "services.ini"
    ini_path.write_bytes(b"[GAS]\nTitle=Gas\xff\xfe invalido\nFields=importe\n")
    monkeypatch.setattr(services_config, "SERVICES_INI", ini_path)
    with pytest.raises(ServicesConfigError) as exc_info:
        services_config.list_services()
    assert "UTF-8" in str(exc_info.value)


def test_duplicate_section_fails_with_clear_message(tmp_path, monkeypatch):
    content = "[GAS]\nTitle=Gas\nFields=importe\n\n[GAS]\nTitle=Gas otra vez\nFields=importe\n"
    _write_ini(tmp_path, content, monkeypatch)
    with pytest.raises(ServicesConfigError) as exc_info:
        services_config.list_services()
    message = str(exc_info.value)
    assert "GAS" in message
    assert "duplicad" in message.lower()


def test_hot_reload_reflects_changes_without_restart(tmp_path, monkeypatch):
    """services.ini se relee en cada llamada (sin caché): un cambio en el
    archivo se refleja sin reiniciar el proceso."""
    _write_ini(tmp_path, _valid_section("A", "importe"), monkeypatch)
    assert services_config.list_services() == ["A"]

    ini_path = tmp_path / "services.ini"
    ini_path.write_text(
        _valid_section("A", "importe") + "\n" + _valid_section("B", "importe"),
        encoding="utf-8",
    )
    assert services_config.list_services() == ["A", "B"]
