"""
Tests para validar el formato exacto de archivos .DATA generados.
"""

from datetime import datetime
from pathlib import Path

from backend.app.plain_text_writer import write_data_file


def test_data_file_format():
    """Valida que un archivo .DATA tenga formato correcto, separador y contenido."""
    # Arrange
    output_dir = Path(str(Path(__file__).parents[2] / "backend" / "output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    fields = ["importe", "cliente", "nro_medidor", "a_pagar_hasta", "periodo"]
    values = {
        "importe": "23345,56",
        "cliente": "045-987654",
        "nro_medidor": "34572",
        "a_pagar_hasta": "20/06/2026",
        "periodo": "01/2026",
    }
    timestamp = datetime(2026, 6, 20, 23, 59, 0)

    # Act
    filepath = write_data_file("GAS", fields, values, timestamp=timestamp, output_dir=output_dir)

    # Assert
    content = Path(filepath).read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Validation
    assert len(lines) >= 2, "El archivo debe contener al menos 2 líneas"
    # First line: fields separated by ;
    first_line = lines[0]
    assert first_line == ";".join(fields), f"Header line incorrecta: {first_line}"
    # Second line: values separated by ;
    second_line = lines[1]
    assert second_line == ";".join(values[f] for f in fields), f"Data line incorrecta: {second_line}"
    # Note: Commas may legitimately appear within values (e.g., "23345,56")
    # We only validate that field separators are semicolons
    # No metadata or extra lines
    assert all("[" not in line for line in lines[:5]), "Debe no incluir metadata en el archivo"


def test_data_file_emptiness_empty_value():
    """Valida que valores vacíos no alteren el formato y no generen separadores de comas."""
    output_dir = Path(str(Path(__file__).parents[2] / "output" / "test"))
    output_dir.mkdir(parents=True, exist_ok=True)

    fields = ["importe", "cliente"]
    values = {"importe": None, "cliente": None}
    timestamp = datetime(2026, 6, 20, 23, 59, 0)

    # Act
    filepath = write_data_file("TEST", fields, values, timestamp=timestamp, output_dir=output_dir)

    content = Path(filepath).read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    assert len(lines) == 2, "Solo se deben tener dos líneas en el archivo .DATA"
    assert lines[0] == ";".join(fields), "Encabezado debería ser separado por ';'"
    assert lines[1] == ";".join("" if v is None else str(v) for f, v in values.items()), (
        "Datos vacíos deben generar separadores entre ellos"
    )


def test_data_file_no_json_meta():
    """Asegura que ningún contenido de meta-datos se escriba por accidente."""
    output_dir = Path(str(Path(__file__).parents[2] / "output" / "meta"))
    output_dir.mkdir(parents=True, exist_ok=True)

    fields = ["test_field"]
    values = {"test_field": "test_value"}
    timestamp = datetime(2026, 6, 20, 23, 59, 0)

    # Act
    filepath = write_data_file("TEST_META", fields, values, timestamp=timestamp, output_dir=output_dir)

    content = Path(filepath).read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Lines should not contain metadata like JSON, timestamps in content, etc.
    for line in lines:
        assert not line.startswith("{"), "No debe contener salida JSON"
        assert "json" not in line.lower(), "No debe contener referencia a JSON"
        assert "[GAS]" not in line, "No debe contener seccion de configuración"
        assert "[CEVT]" not in line, "No debe contener seccion de configuración"
