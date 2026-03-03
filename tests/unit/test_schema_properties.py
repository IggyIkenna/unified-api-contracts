"""Hypothesis property-based tests for schema robustness."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from unified_api_contracts.unified_normalised_contracts import CanonicalTrade

pytestmark = pytest.mark.unit

_TS = datetime(2024, 1, 1, tzinfo=UTC)
_VENUE = "test_venue"
_SYMBOL = "TEST:BTC-USDT"
_TRADE_ID = "trade-001"


@given(
    st.decimals(
        allow_nan=False,
        allow_infinity=False,
        min_value=Decimal("0.000001"),
        max_value=Decimal("1e18"),
    )
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_canonical_trade_price_no_silent_truncation(price: Decimal) -> None:
    """Extreme Decimal prices must round-trip without silent truncation."""
    trade = CanonicalTrade(
        venue=_VENUE,
        symbol=_SYMBOL,
        trade_id=_TRADE_ID,
        timestamp=_TS,
        price=price,
        quantity=Decimal("1"),
        side="buy",
    )
    assert trade.price == price


def test_zero_quantity_trade_rejected() -> None:
    """Zero-quantity trades must be rejected."""
    with pytest.raises(ValidationError):
        CanonicalTrade(
            venue=_VENUE,
            symbol=_SYMBOL,
            trade_id=_TRADE_ID,
            timestamp=_TS,
            price=Decimal("50000"),
            quantity=Decimal("0"),
            side="buy",
        )


def test_negative_price_rejected() -> None:
    """Negative prices must be rejected (prices must be > 0)."""
    with pytest.raises(ValidationError):
        CanonicalTrade(
            venue=_VENUE,
            symbol=_SYMBOL,
            trade_id=_TRADE_ID,
            timestamp=_TS,
            price=Decimal("-1"),
            quantity=Decimal("1"),
            side="buy",
        )


def test_empty_symbol_rejected() -> None:
    """Empty symbol must be rejected."""
    with pytest.raises(ValidationError):
        CanonicalTrade(
            venue=_VENUE,
            symbol="",
            trade_id=_TRADE_ID,
            timestamp=_TS,
            price=Decimal("50000"),
            quantity=Decimal("1"),
            side="buy",
        )


def test_timezone_naive_timestamp_rejected() -> None:
    """Timezone-naive timestamps must be rejected (UTC required per utc-datetime.mdc)."""
    with pytest.raises(ValidationError):
        CanonicalTrade(
            venue=_VENUE,
            symbol=_SYMBOL,
            trade_id=_TRADE_ID,
            timestamp=datetime(2024, 1, 1),  # no tzinfo
            price=Decimal("50000"),
            quantity=Decimal("1"),
            side="buy",
        )


@given(st.just(""))
def test_empty_venue_rejected(venue: str) -> None:
    """Empty venue string must be rejected."""
    with pytest.raises(ValidationError):
        CanonicalTrade(
            venue=venue,
            symbol=_SYMBOL,
            trade_id=_TRADE_ID,
            timestamp=_TS,
            price=Decimal("50000"),
            quantity=Decimal("1"),
            side="buy",
        )


def test_nan_float_in_raw_json_boundary() -> None:
    """NaN floats from venue JSON must not silently become Decimal NaN."""
    with pytest.raises((ValidationError, ValueError, InvalidOperation)):
        CanonicalTrade(
            venue=_VENUE,
            symbol=_SYMBOL,
            trade_id=_TRADE_ID,
            timestamp=_TS,
            price=float("nan"),  # type: ignore[arg-type]
            quantity=Decimal("1"),
            side="buy",
        )
