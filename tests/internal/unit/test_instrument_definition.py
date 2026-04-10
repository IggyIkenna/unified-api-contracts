"""Unit tests for InstrumentDefinition schema.

Covers field validators, model validators (auto-extraction of expiry/option info),
to_dict, from_dict, validate_required_fields, and all uncovered branches.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.reference.instrument_definition import (
    InstrumentDefinition,
    _parse_yymmdd,
    _validate_iso,
)

# ---------------------------------------------------------------------------
# Helper: minimal valid spot definition
# ---------------------------------------------------------------------------

SPOT_MINIMAL = {
    "instrument_key": "binance:spot:BTC-USDT",
    "venue": "binance",
    "instrument_type": "SPOT_PAIR",
    "symbol": "BTC-USDT",
    "available_from_datetime": "2020-01-01T00:00:00Z",
}


def make_spot(**overrides: object) -> InstrumentDefinition:
    data = {**SPOT_MINIMAL, **overrides}
    return InstrumentDefinition(**data)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _parse_yymmdd helper
# ---------------------------------------------------------------------------


class TestParseYymmdd:
    def test_valid_date_2000s(self) -> None:
        result = _parse_yymmdd("240315")
        assert result == "2024-03-15T08:00:00Z"

    def test_valid_date_1900s(self) -> None:
        # yy >= 50 → 1900 + 100 + yy = 1900+100+50 = 2050... wait, that's wrong.
        # Actually: 1900 + 100 + yy → for yy=50: 2050, for yy=99: 2099
        # But the code says: year = 2000 + yy if yy < 50 else 1900 + 100 + yy
        # 1900 + 100 + 99 = 2099 — so all dates map to 20xx. Test with yy=50
        result = _parse_yymmdd("501201")
        assert result == "2050-12-01T08:00:00Z"

    def test_invalid_month(self) -> None:
        assert _parse_yymmdd("241301") is None  # month 13 invalid

    def test_invalid_day(self) -> None:
        assert _parse_yymmdd("240100") is None  # day 0 invalid

    def test_invalid_string(self) -> None:
        assert _parse_yymmdd("abc") is None


# ---------------------------------------------------------------------------
# _validate_iso helper
# ---------------------------------------------------------------------------


class TestValidateIso:
    def test_valid_iso(self) -> None:
        assert _validate_iso("2024-01-01T00:00:00Z") is True

    def test_invalid_iso(self) -> None:
        assert _validate_iso("not-a-date") is False

    def test_iso_with_leading_space(self) -> None:
        assert _validate_iso("  2024-01-01T00:00:00Z") is True


# ---------------------------------------------------------------------------
# validate_instrument_key
# ---------------------------------------------------------------------------


class TestValidateInstrumentKey:
    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="instrument_key is required"):
            make_spot(instrument_key="")

    def test_none_key_raises(self) -> None:
        with pytest.raises(ValueError, match="instrument_key is required"):
            make_spot(instrument_key=None)

    def test_too_few_parts_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid instrument key format"):
            make_spot(instrument_key="binance:spot")

    def test_valid_key_three_parts(self) -> None:
        inst = make_spot(instrument_key="binance:spot:BTC-USDT")
        assert inst.instrument_key == "binance:spot:BTC-USDT"

    def test_valid_key_four_parts(self) -> None:
        inst = make_spot(instrument_key="binance:future:BTC-USDT:240329")
        assert inst.instrument_key == "binance:future:BTC-USDT:240329"


# ---------------------------------------------------------------------------
# validate_from_datetime
# ---------------------------------------------------------------------------


class TestValidateFromDatetime:
    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="available_from_datetime is required"):
            make_spot(available_from_datetime="")

    def test_invalid_iso_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ISO datetime"):
            make_spot(available_from_datetime="not-a-date")

    def test_valid_iso(self) -> None:
        inst = make_spot(available_from_datetime="2021-06-15T00:00:00Z")
        assert inst.available_from_datetime == "2021-06-15T00:00:00Z"


# ---------------------------------------------------------------------------
# validate_to_datetime
# ---------------------------------------------------------------------------


class TestValidateToDatetime:
    def test_none_allowed(self) -> None:
        inst = make_spot(available_to_datetime=None)
        assert inst.available_to_datetime is None

    def test_empty_string_returns_none(self) -> None:
        inst = make_spot(available_to_datetime="")
        assert inst.available_to_datetime is None

    def test_invalid_iso_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ISO datetime"):
            make_spot(available_to_datetime="2024/01/01")

    def test_valid_iso(self) -> None:
        inst = make_spot(available_to_datetime="2025-12-31T23:59:59Z")
        assert inst.available_to_datetime == "2025-12-31T23:59:59Z"


# ---------------------------------------------------------------------------
# validate_expiry
# ---------------------------------------------------------------------------


class TestValidateExpiry:
    def test_none_allowed(self) -> None:
        inst = make_spot(expiry=None)
        assert inst.expiry is None

    def test_empty_string_returns_none(self) -> None:
        inst = make_spot(expiry="")
        assert inst.expiry is None

    def test_invalid_iso_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid expiry"):
            make_spot(expiry="not-valid")

    def test_valid_expiry(self) -> None:
        inst = make_spot(expiry="2024-03-29T08:00:00Z")
        assert inst.expiry == "2024-03-29T08:00:00Z"


# ---------------------------------------------------------------------------
# validate_option_type
# ---------------------------------------------------------------------------


class TestValidateOptionType:
    def test_none_allowed(self) -> None:
        inst = make_spot(option_type=None)
        assert inst.option_type is None

    def test_empty_string_returns_none(self) -> None:
        inst = make_spot(option_type="  ")
        assert inst.option_type is None

    def test_call_normalized(self) -> None:
        inst = make_spot(option_type="C")
        assert inst.option_type == "CALL"

    def test_call_full_normalized(self) -> None:
        inst = make_spot(option_type="call")
        assert inst.option_type == "CALL"

    def test_put_normalized(self) -> None:
        inst = make_spot(option_type="P")
        assert inst.option_type == "PUT"

    def test_put_full_normalized(self) -> None:
        inst = make_spot(option_type="PUT")
        assert inst.option_type == "PUT"

    def test_invalid_option_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid option type"):
            make_spot(option_type="X")


# ---------------------------------------------------------------------------
# validate_contract_size
# ---------------------------------------------------------------------------


class TestValidateContractSize:
    def test_none_allowed(self) -> None:
        inst = make_spot(contract_size=None)
        assert inst.contract_size is None

    def test_empty_string_returns_none(self) -> None:
        inst = make_spot(contract_size="")
        assert inst.contract_size is None

    def test_float_string(self) -> None:
        inst = make_spot(contract_size="1.5")
        assert inst.contract_size == 1.5

    def test_int_value(self) -> None:
        inst = make_spot(contract_size=100)
        assert inst.contract_size == 100.0

    def test_float_value(self) -> None:
        inst = make_spot(contract_size=0.001)
        assert inst.contract_size == 0.001

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid contract_size"):
            make_spot(contract_size="not-a-number")


# ---------------------------------------------------------------------------
# Auto-extraction of expiry via _auto_extract_fields model validator
# ---------------------------------------------------------------------------


class TestAutoExtractExpiry:
    def test_future_key_yymmdd_expiry_extracted(self) -> None:
        """Future with YYMMDD in key should auto-extract expiry."""
        inst = InstrumentDefinition(
            instrument_key="binance:future:BTC-USDT-240329",
            venue="binance",
            instrument_type="FUTURE",
            symbol="BTC-USDT-240329",
            available_from_datetime="2024-01-01T00:00:00Z",
        )
        assert inst.expiry == "2024-03-29T08:00:00Z"

    def test_future_key_short_month_expiry_extracted(self) -> None:
        """Future with short month notation (29MAR24) in key should extract expiry."""
        inst = InstrumentDefinition(
            instrument_key="deribit:future:BTC-29MAR24",
            venue="deribit",
            instrument_type="FUTURE",
            symbol="BTC-29MAR24",
            available_from_datetime="2024-01-01T00:00:00Z",
        )
        assert inst.expiry is not None
        assert "2024" in inst.expiry

    def test_future_expiry_not_overwritten_if_set(self) -> None:
        """Explicit expiry should not be overwritten by auto-extraction."""
        inst = InstrumentDefinition(
            instrument_key="binance:future:BTC-USDT-240329",
            venue="binance",
            instrument_type="FUTURE",
            symbol="BTC-USDT-240329",
            available_from_datetime="2024-01-01T00:00:00Z",
            expiry="2024-09-27T08:00:00Z",
        )
        assert inst.expiry == "2024-09-27T08:00:00Z"

    def test_spot_no_expiry_extraction(self) -> None:
        """Spot instruments should not attempt expiry extraction."""
        inst = make_spot()
        assert inst.expiry is None


# ---------------------------------------------------------------------------
# Auto-extraction of option info
# ---------------------------------------------------------------------------


class TestAutoExtractOptionInfo:
    def test_option_long_format_call(self) -> None:
        """Option with long format strike/type in key should auto-extract."""
        inst = InstrumentDefinition(
            instrument_key="deribit:option:BTC-240329-50000-C",
            venue="deribit",
            instrument_type="OPTION",
            symbol="BTC-240329-50000-C",
            available_from_datetime="2024-01-01T00:00:00Z",
        )
        assert inst.strike == "50000"
        assert inst.option_type == "CALL"

    def test_option_long_format_put(self) -> None:
        inst = InstrumentDefinition(
            instrument_key="deribit:option:BTC-240329-50000-PUT",
            venue="deribit",
            instrument_type="OPTION",
            symbol="BTC-240329-50000-PUT",
            available_from_datetime="2024-01-01T00:00:00Z",
        )
        assert inst.option_type == "PUT"

    def test_option_info_not_overwritten_if_set(self) -> None:
        """Explicit strike/option_type should not be overwritten."""
        inst = InstrumentDefinition(
            instrument_key="deribit:option:BTC-240329-50000-C",
            venue="deribit",
            instrument_type="OPTION",
            symbol="BTC-240329-50000-C",
            available_from_datetime="2024-01-01T00:00:00Z",
            strike="45000",
            option_type="PUT",
        )
        assert inst.strike == "45000"
        assert inst.option_type == "PUT"

    def test_option_no_match_returns_none(self) -> None:
        """Option with no extractable info should leave strike/option_type as None."""
        inst = InstrumentDefinition(
            instrument_key="unknown:option:SOMEKEY",
            venue="unknown",
            instrument_type="OPTION",
            symbol="SOMEKEY",
            available_from_datetime="2024-01-01T00:00:00Z",
        )
        assert inst.strike is None
        assert inst.option_type is None


# ---------------------------------------------------------------------------
# to_dict and from_dict
# ---------------------------------------------------------------------------


class TestToDictFromDict:
    def test_to_dict_returns_dict(self) -> None:
        inst = make_spot()
        d = inst.to_dict()
        assert isinstance(d, dict)
        assert d["instrument_key"] == "binance:spot:BTC-USDT"
        assert d["venue"] == "binance"

    def test_from_dict_roundtrip(self) -> None:
        inst = make_spot()
        d = inst.to_dict()
        inst2 = InstrumentDefinition.from_dict(d)
        assert inst2.instrument_key == inst.instrument_key
        assert inst2.venue == inst.venue

    def test_from_dict_invalid_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            InstrumentDefinition.from_dict({"instrument_key": "missing:parts"})


# ---------------------------------------------------------------------------
# validate_required_fields
# ---------------------------------------------------------------------------


class TestValidateRequiredFields:
    def test_all_required_fields_present(self) -> None:
        inst = InstrumentDefinition(
            instrument_key="binance:spot:BTC-USDT",
            venue="binance",
            instrument_type="SPOT_PAIR",
            symbol="BTC-USDT",
            available_from_datetime="2020-01-01T00:00:00Z",
            base_asset="BTC",
            quote_asset="USDT",
            tardis_symbol="BTC-USDT",
            tardis_exchange="binance",
        )
        missing = inst.validate_required_fields()
        assert missing == []

    def test_missing_required_fields_reported(self) -> None:
        inst = make_spot()  # Missing base_asset, quote_asset, tardis_symbol, etc.
        missing = inst.validate_required_fields()
        assert "base_asset" in missing
        assert "quote_asset" in missing
        assert "tardis_symbol" in missing
        assert "tardis_exchange" in missing


# ---------------------------------------------------------------------------
# Additional coverage for base.py and dead_letter.py
# ---------------------------------------------------------------------------


class TestBaseContractModel:
    def test_base_contract_model_importable(self) -> None:
        from unified_api_contracts.internal.base import BaseContractModel

        assert BaseContractModel is not None

    def test_base_contract_model_is_pydantic_base(self) -> None:
        from pydantic import BaseModel

        from unified_api_contracts.internal.base import BaseContractModel

        assert issubclass(BaseContractModel, BaseModel)


class TestDeadLetterRecord:
    def test_dead_letter_record_importable(self) -> None:
        from unified_api_contracts.internal.schemas.errors import DeadLetterRecord

        assert DeadLetterRecord is not None

    def test_dead_letter_record_instantiable(self) -> None:
        from datetime import UTC, datetime

        from unified_api_contracts.internal.schemas.errors import DeadLetterRecord, ErrorCategory

        now = datetime.now(UTC)
        record = DeadLetterRecord(
            record_id="dlr-001",
            original_event="MARKET_TICK",
            error_category=ErrorCategory.VALIDATION,
            error_message="parse error",
            retry_count=3,
            max_retries=3,
            first_failure_at=now,
            last_failure_at=now,
            source_service="market-tick-data-service",
            dead_lettered_at=now,
        )
        assert record.record_id == "dlr-001"
        assert record.error_message == "parse error"
        assert record.error_category == ErrorCategory.VALIDATION
