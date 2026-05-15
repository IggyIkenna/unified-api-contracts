"""Tests for expiry guard in validate_instrument_records / _check_record.

Covers:
- status=EXPIRED → rejected unconditionally
- expiry.date() < as_of_date → rejected
- expiry.date() >= as_of_date → passes
- no as_of_date → expiry-date guard inactive (past expiry allowed)
- active instrument with no expiry → passes
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentStatus, InstrumentType
from unified_api_contracts.internal.reference.instrument_validation import validate_instrument_records

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AS_OF = date(2026, 5, 15)
_PAST_EXPIRY = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)  # before _AS_OF
_FUTURE_EXPIRY = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)  # after _AS_OF


_DUMMY_EVM_ADDR = "0xBcca60bB61934080951369a648Fb03DF4F96263C"


def _defi_lending_record(**overrides: object) -> InstrumentRecord:
    """Minimal DeFi LENDING record that passes all validation except what we're testing.

    Uses AAVEV3-ETHEREUM (known DeFi venue). pool_address satisfies the on-chain
    identifier requirement (hard_schema_enforcement_2026_05_08 Phase 1 EVM check).
    """
    kwargs: dict[str, object] = {
        "instrument_key": "AAVEV3-ETHEREUM:LENDING:USDC",
        "venue": "AAVEV3-ETHEREUM",
        "instrument_type": InstrumentType.LENDING,
        "pool_address": _DUMMY_EVM_ADDR,
    }
    kwargs.update(overrides)
    return InstrumentRecord(**kwargs)  # type: ignore[arg-type]


def _assert_rejected(records: list[InstrumentRecord], expected_fragment: str, as_of_date: date | None = None) -> None:
    valid, rejected = validate_instrument_records(records, as_of_date=as_of_date)
    assert len(valid) == 0, f"Expected all rejected, got valid={valid}"
    assert len(rejected) == 1
    _, reason = rejected[0]
    assert expected_fragment in reason, f"Expected {expected_fragment!r} in reason {reason!r}"


def _assert_passes(records: list[InstrumentRecord], as_of_date: date | None = None) -> None:
    valid, rejected = validate_instrument_records(records, as_of_date=as_of_date)
    assert len(rejected) == 0, f"Expected no rejections, got {rejected}"
    assert len(valid) == len(records)


# ---------------------------------------------------------------------------
# status=EXPIRED tests
# ---------------------------------------------------------------------------


class TestExpiredStatus:
    def test_expired_status_rejected_without_as_of(self) -> None:
        rec = _defi_lending_record(status=InstrumentStatus.EXPIRED)
        _assert_rejected([rec], "instrument is EXPIRED", as_of_date=None)

    def test_expired_status_rejected_with_as_of(self) -> None:
        rec = _defi_lending_record(status=InstrumentStatus.EXPIRED)
        _assert_rejected([rec], "instrument is EXPIRED", as_of_date=_AS_OF)

    def test_expired_status_with_future_expiry_still_rejected(self) -> None:
        """status=EXPIRED is authoritative — future expiry datetime doesn't override it."""
        rec = _defi_lending_record(status=InstrumentStatus.EXPIRED, expiry=_FUTURE_EXPIRY)
        _assert_rejected([rec], "instrument is EXPIRED", as_of_date=_AS_OF)

    def test_active_status_not_rejected(self) -> None:
        rec = _defi_lending_record(status=InstrumentStatus.ACTIVE)
        _assert_passes([rec], as_of_date=_AS_OF)

    def test_halted_status_not_rejected(self) -> None:
        """HALTED ≠ EXPIRED — still tradeable in some sessions."""
        rec = _defi_lending_record(status=InstrumentStatus.HALTED)
        _assert_passes([rec], as_of_date=_AS_OF)


# ---------------------------------------------------------------------------
# expiry.date() < as_of_date tests
# ---------------------------------------------------------------------------


class TestPastExpiry:
    def test_past_expiry_with_as_of_rejected(self) -> None:
        rec = _defi_lending_record(expiry=_PAST_EXPIRY)
        _assert_rejected([rec], "instrument expired before as_of_date", as_of_date=_AS_OF)

    def test_past_expiry_reason_contains_dates(self) -> None:
        rec = _defi_lending_record(expiry=_PAST_EXPIRY)
        _, rejected = validate_instrument_records([rec], as_of_date=_AS_OF)
        _, reason = rejected[0]
        assert "2026-05-01" in reason
        assert "2026-05-15" in reason

    def test_past_expiry_no_as_of_passes(self) -> None:
        """Without as_of_date the past-expiry guard is inactive — historical backtests need this."""
        rec = _defi_lending_record(expiry=_PAST_EXPIRY)
        _assert_passes([rec], as_of_date=None)

    def test_expiry_same_day_as_as_of_passes(self) -> None:
        """Expiry on the same day as as_of_date is NOT expired (< is strict)."""
        same_day_expiry = datetime(_AS_OF.year, _AS_OF.month, _AS_OF.day, 16, 0, 0, tzinfo=UTC)
        rec = _defi_lending_record(expiry=same_day_expiry)
        _assert_passes([rec], as_of_date=_AS_OF)

    def test_future_expiry_passes(self) -> None:
        rec = _defi_lending_record(expiry=_FUTURE_EXPIRY)
        _assert_passes([rec], as_of_date=_AS_OF)

    def test_no_expiry_passes(self) -> None:
        rec = _defi_lending_record(expiry=None)
        _assert_passes([rec], as_of_date=_AS_OF)


# ---------------------------------------------------------------------------
# Batch + mixed tests
# ---------------------------------------------------------------------------


class TestBatchValidation:
    def test_mixed_batch_separates_expired_from_active(self) -> None:
        active = _defi_lending_record(instrument_key="AAVEV3-ETHEREUM:LENDING:USDC", expiry=_FUTURE_EXPIRY)
        expired_status = _defi_lending_record(
            instrument_key="AAVEV3-ETHEREUM:LENDING:DAI", status=InstrumentStatus.EXPIRED
        )
        past_expiry = _defi_lending_record(instrument_key="AAVEV3-ETHEREUM:LENDING:WETH", expiry=_PAST_EXPIRY)
        valid, rejected = validate_instrument_records([active, expired_status, past_expiry], as_of_date=_AS_OF)
        assert len(valid) == 1
        assert valid[0].instrument_key == "AAVEV3-ETHEREUM:LENDING:USDC"
        assert len(rejected) == 2

    def test_empty_records_returns_empty(self) -> None:
        valid, rejected = validate_instrument_records([], as_of_date=_AS_OF)
        assert valid == []
        assert rejected == []
