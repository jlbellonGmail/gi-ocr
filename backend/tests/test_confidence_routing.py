"""
Tests unitarios para feature 09-confianza-y-enrutamiento-hitl:
- Lógica de decisión de confianza
- Cálculo de scores
- Validación de esquemas services.ini
"""

from __future__ import annotations

import pytest
from backend.app.capture_pipeline import (
    _calc_extraction_score,
    _make_confidence_decision,
)
from backend.app.services_config import (
    DEFAULT_BLOCK_ON_VALIDATION_FAIL,
    DEFAULT_CONFIDENCE_AUTO_ACCEPT,
    DEFAULT_CONFIDENCE_NEEDS_REVIEW,
    DEFAULT_SENSITIVE,
    get_field_confidence_config,
    validate_services_schema,
)


class TestExtractionScore:
    """Tests para _calc_extraction_score."""

    def test_zone_regex(self):
        assert _calc_extraction_score("zone_regex", True) == 1.0
        assert _calc_extraction_score("zone_regex", False) == 1.0

    def test_fulltext_regex(self):
        assert _calc_extraction_score("fulltext_regex", True) == 0.9
        assert _calc_extraction_score("fulltext_regex", False) == 0.9

    def test_anchor_only(self):
        assert _calc_extraction_score("anchor_only", True) == 0.7
        assert _calc_extraction_score("anchor_only", False) == 0.7

    def test_generic(self):
        assert _calc_extraction_score("generic", True) == 0.3
        assert _calc_extraction_score("generic", False) == 0.3

    def test_none(self):
        assert _calc_extraction_score("none", True) == 0.0
        assert _calc_extraction_score("none", False) == 0.0

    def test_unknown_path(self):
        assert _calc_extraction_score("unknown", True) == 0.0


class TestConfidenceDecision:
    """Tests para _make_confidence_decision."""

    def _base_config(self):
        return {
            "auto_accept": 0.85,
            "needs_review": 0.50,
            "sensitive": False,
            "block_on_validation_fail": True,
        }

    def test_auto_accepted_high_confidence(self):
        config = self._base_config()
        decision, detail = _make_confidence_decision("importe", 0.95, 1.0, True, None, config)
        assert decision == "auto_accepted"
        assert detail["final_score"] == round(0.95 * 0.6 + 1.0 * 0.4, 3)
        assert detail["validation_passed"] is True

    def test_needs_review_medium_confidence(self):
        config = self._base_config()
        decision, detail = _make_confidence_decision("importe", 0.70, 0.9, True, None, config)
        assert decision == "needs_review"
        assert detail["final_score"] == round(0.70 * 0.6 + 0.9 * 0.4, 3)

    def test_needs_review_low_confidence(self):
        config = self._base_config()
        decision, detail = _make_confidence_decision("importe", 0.40, 0.7, True, None, config)
        assert decision == "needs_review"

    def test_blocked_sensitive_field_validation_fail(self):
        config = self._base_config()
        config["sensitive"] = True
        decision, detail = _make_confidence_decision("importe", 0.90, 1.0, False, "amount_parse", config)
        assert decision == "blocked"
        assert detail["sensitive"] is True
        assert detail["validation_passed"] is False

    def test_blocked_block_on_fail_true(self):
        config = self._base_config()
        config["block_on_validation_fail"] = True
        config["sensitive"] = False
        decision, detail = _make_confidence_decision("periodo", 0.80, 0.9, False, "no_period_pattern", config)
        assert decision == "blocked"

    def test_rejected_not_sensitive_block_on_fail_false(self):
        config = self._base_config()
        config["sensitive"] = False
        config["block_on_validation_fail"] = False
        decision, detail = _make_confidence_decision("nro_medidor", 0.80, 0.9, False, "too_short", config)
        assert decision == "rejected"

    def test_final_score_calculation(self):
        config = self._base_config()
        _, detail = _make_confidence_decision("test", 0.80, 0.90, True, None, config)
        expected = round(0.80 * 0.6 + 0.90 * 0.4, 3)
        assert detail["final_score"] == expected

    def test_thresholds_in_detail(self):
        config = self._base_config()
        _, detail = _make_confidence_decision("test", 0.80, 0.90, True, None, config)
        assert detail["thresholds"]["auto"] == 0.85
        assert detail["thresholds"]["review"] == 0.50

    def test_sensitive_flag_in_detail(self):
        config = self._base_config()
        config["sensitive"] = True
        _, detail = _make_confidence_decision("test", 0.80, 0.90, True, None, config)
        assert detail["sensitive"] is True

    def test_block_on_validation_fail_flag_in_detail(self):
        config = self._base_config()
        config["block_on_validation_fail"] = False
        _, detail = _make_confidence_decision("test", 0.80, 0.90, True, None, config)
        assert detail["block_on_validation_fail"] is False


class TestServicesConfigConfidence:
    """Tests para configuración de confianza en services_config."""

    def test_get_field_confidence_config_defaults(self):
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
""")
        conf = get_field_confidence_config(cfg, "TEST", "campo1")
        assert conf["auto_accept"] == DEFAULT_CONFIDENCE_AUTO_ACCEPT
        assert conf["needs_review"] == DEFAULT_CONFIDENCE_NEEDS_REVIEW
        assert conf["sensitive"] == DEFAULT_SENSITIVE
        assert conf["block_on_validation_fail"] == DEFAULT_BLOCK_ON_VALIDATION_FAIL

    def test_get_field_confidence_config_custom(self):
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.ConfidenceAutoAccept=0.90
Field.campo1.ConfidenceNeedsReview=0.60
Field.campo1.Sensitive=true
Field.campo1.BlockOnValidationFail=false
""")
        conf = get_field_confidence_config(cfg, "TEST", "campo1")
        assert conf["auto_accept"] == 0.90
        assert conf["needs_review"] == 0.60
        assert conf["sensitive"] is True
        assert conf["block_on_validation_fail"] is False

    def test_validate_auto_accept_greater_than_needs_review(self):
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.ConfidenceAutoAccept=0.50
Field.campo1.ConfidenceNeedsReview=0.85
""")
        with pytest.raises(Exception) as exc_info:
            validate_services_schema(cfg)
        assert "ConfidenceAutoAccept" in str(exc_info.value)
        assert "mayor que" in str(exc_info.value)

    def test_validate_confidence_range(self):
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.ConfidenceAutoAccept=1.5
""")
        with pytest.raises(Exception) as exc_info:
            validate_services_schema(cfg)
        assert "fuera de rango" in str(exc_info.value)

    def test_validate_sensitive_values(self):
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.Sensitive=yes
""")
        with pytest.raises(Exception) as exc_info:
            validate_services_schema(cfg)
        assert "Sensitive" in str(exc_info.value)
        assert "true" in str(exc_info.value) and "false" in str(exc_info.value)

    def test_validate_block_on_validation_fail_values(self):
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.BlockOnValidationFail=si
""")
        with pytest.raises(Exception) as exc_info:
            validate_services_schema(cfg)
        assert "BlockOnValidationFail" in str(exc_info.value)
        assert "true" in str(exc_info.value) and "false" in str(exc_info.value)

    def test_validate_only_one_threshold_declared_uses_default_for_other(self):
        """Si solo se declara uno, debe usar default para el otro y validar que auto > review."""
        import configparser

        cfg = configparser.ConfigParser()
        cfg.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.ConfidenceAutoAccept=0.90
""")
        # No debe fallar, usa default 0.50 para needs_review, 0.90 > 0.50 OK
        validate_services_schema(cfg)

        cfg2 = configparser.ConfigParser()
        cfg2.read_string("""
[TEST]
Title=Test
Fields=campo1
Field.campo1.Label=Campo 1
Field.campo1.Type=text
Field.campo1.Required=true
Field.campo1.Example=valor
Field.campo1.Regex=(valor)
Field.campo1.ConfidenceNeedsReview=0.90
""")
        # No debe fallar, usa default 0.85 para auto_accept, pero 0.85 <= 0.90 -> falla
        with pytest.raises(Exception) as exc_info:
            validate_services_schema(cfg2)
        assert "mayor que" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
