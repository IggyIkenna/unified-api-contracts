"""Unit tests for CanonicalFuturesContract + FuturesContractLifecyclePhase.

Implements tradfi_canonical_futures_contract_hard_required_fields_2026_05_13
Phase 1A: greenfield class + enum with hard-required expiry/lifecycle fields.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.canonical.domain import (
    CanonicalFuturesContract,
    FuturesContractLifecyclePhase,
)


def _valid_kwargs() -> dict[str, object]:
    """Minimal valid kwargs for CanonicalFuturesContract."""
    return {
        "venue": "CME",
        "root": "ES",
        "contract_symbol": "ESH26",
        "contract_month": 3,
        "contract_year": 2026,
        "expiry_date": date(2026, 3, 20),
        "last_trading_date": date(2026, 3, 20),
        "first_notice_date": date(2026, 3, 16),
        "delivery_date": date(2026, 3, 20),
        "settlement_date": date(2026, 3, 23),
        "lifecycle_phase": FuturesContractLifecyclePhase.ACTIVE,
    }


def test_lifecycle_phase_enum_closed_set():
    """Exactly 6 lifecycle phases — closed set."""
    expected = {"listed", "active", "in_first_notice", "in_delivery", "expired", "settled"}
    assert {p.value for p in FuturesContractLifecyclePhase} == expected


def test_canonical_futures_contract_minimal_construction():
    """Constructs cleanly with all required fields."""
    c = CanonicalFuturesContract(**_valid_kwargs())
    assert c.venue == "CME"
    assert c.contract_symbol == "ESH26"
    assert c.contract_month == 3
    assert c.contract_year == 2026
    assert c.lifecycle_phase == FuturesContractLifecyclePhase.ACTIVE
    assert c.tick_size is None  # optional
    assert c.contract_size is None  # optional


def test_canonical_futures_contract_with_optional_fields():
    """All optional fields populate."""
    c = CanonicalFuturesContract(
        **_valid_kwargs(),
        tick_size=Decimal("0.25"),
        contract_size=Decimal("50"),
        listed_at=datetime(2024, 6, 1, 0, 0, tzinfo=UTC),
    )
    assert c.tick_size == Decimal("0.25")
    assert c.contract_size == Decimal("50")
    assert c.listed_at == datetime(2024, 6, 1, 0, 0, tzinfo=UTC)


def test_canonical_futures_contract_rejects_missing_expiry_date():
    """expiry_date is hard-required — missing raises ValidationError."""
    kw = _valid_kwargs()
    del kw["expiry_date"]
    with pytest.raises(ValidationError, match="expiry_date"):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_rejects_missing_last_trading_date():
    """last_trading_date is hard-required."""
    kw = _valid_kwargs()
    del kw["last_trading_date"]
    with pytest.raises(ValidationError, match="last_trading_date"):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_rejects_missing_first_notice_date():
    """first_notice_date is hard-required."""
    kw = _valid_kwargs()
    del kw["first_notice_date"]
    with pytest.raises(ValidationError, match="first_notice_date"):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_rejects_missing_delivery_date():
    """delivery_date is hard-required."""
    kw = _valid_kwargs()
    del kw["delivery_date"]
    with pytest.raises(ValidationError, match="delivery_date"):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_rejects_missing_settlement_date():
    """settlement_date is hard-required."""
    kw = _valid_kwargs()
    del kw["settlement_date"]
    with pytest.raises(ValidationError, match="settlement_date"):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_rejects_missing_lifecycle_phase():
    """lifecycle_phase is hard-required."""
    kw = _valid_kwargs()
    del kw["lifecycle_phase"]
    with pytest.raises(ValidationError, match="lifecycle_phase"):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_rejects_extra_fields():
    """CanonicalBase has extra='forbid' — unknown fields rejected."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        CanonicalFuturesContract(**_valid_kwargs(), unknown_field="should_fail")


def test_canonical_futures_contract_month_bounds():
    """contract_month must be in 1..12."""
    kw = _valid_kwargs()
    kw["contract_month"] = 13
    with pytest.raises(ValidationError):
        CanonicalFuturesContract(**kw)
    kw["contract_month"] = 0
    with pytest.raises(ValidationError):
        CanonicalFuturesContract(**kw)


def test_canonical_futures_contract_year_bounds():
    """contract_year must be in 2000..2100 (sanity gate)."""
    kw = _valid_kwargs()
    kw["contract_year"] = 1999
    with pytest.raises(ValidationError):
        CanonicalFuturesContract(**kw)
    kw["contract_year"] = 2101
    with pytest.raises(ValidationError):
        CanonicalFuturesContract(**kw)


def test_lifecycle_phase_string_value_roundtrip():
    """StrEnum values match documented string forms (for parquet serialisation)."""
    c = CanonicalFuturesContract(**_valid_kwargs(), tick_size=Decimal("0.25"))
    # JSON serialization should use the string value
    j = c.model_dump_json()
    assert '"lifecycle_phase":"active"' in j

    # Deserialization from string value works
    c2 = CanonicalFuturesContract.model_validate({**_valid_kwargs(), "lifecycle_phase": "in_first_notice"})
    assert c2.lifecycle_phase == FuturesContractLifecyclePhase.IN_FIRST_NOTICE
