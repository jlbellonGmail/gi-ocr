"""Tests unitarios de validadores tipados y normalizadores."""
from backend.app import validators as v


class TestDate:
    def test_valid_full(self):
        assert v.validate_date("12/03/2026") == ("12/03/2026", None)
    def test_valid_2digit_year(self):
        assert v.validate_date("1/4/26") == ("01/04/2026", None)
    def test_invalid_month(self):
        val, reason = v.validate_date("99/03/2026")
        assert val is None and reason == "out_of_range"
    def test_no_pattern(self):
        assert v.validate_date("no date here") == (None, "no_date_pattern")


class TestPeriod:
    def test_valid(self):
        assert v.validate_period("Periodo:06/2026") == ("06/2026", None)
    def test_valid_slash(self):
        assert v.validate_period("01/2026") == ("01/2026", None)
    def test_invalid_month(self):
        val, reason = v.validate_period("13/2026")
        assert val is None and reason == "month_out_of_range"


class TestComprobante:
    def test_clean(self):
        assert v.validate_comprobante("0081-57501806") == ("0081-57501806", None)
    def test_with_noise(self):
        assert v.validate_comprobante("LIQ.SERV.PUB.0009-03883672") == ("0009-03883672", None)
    def test_too_short(self):
        val, reason = v.validate_comprobante("123")
        assert val is None and reason == "too_short"


class TestAccount:
    def test_valid_digits(self):
        assert v.validate_account("Nro CLIENTE 0045630002") == ("0045630002", None)
    def test_wrong_length(self):
        val, reason = v.validate_account("12345")
        assert val is None


class TestMeter:
    def test_valid(self):
        assert v.validate_meter("Medidor No:0006071353") == ("0006071353", None)
    def test_too_short(self):
        assert v.validate_meter("12") == (None, "too_short")


class TestAmount:
    def test_ar_canonical(self):
        assert v.validate_amount("13.429,89") == (13429.89, None)
    def test_ocr_dots_only(self):
        assert v.validate_amount("13.429.89") == (13429.89, None)
    def test_simple_decimal(self):
        assert v.validate_amount("13429,89") == (13429.89, None)
    def test_cevt(self):
        assert v.validate_amount("47.061,59") == (47061.59, None)
    def test_with_dollar(self):
        assert v.validate_amount("$47.061,59") == (47061.59, None)
    def test_invalid(self):
        assert v.validate_amount("abc") == (None, "amount_parse")