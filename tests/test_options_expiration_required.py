"""Unit tests for tradfi_master Q2 Phase 1B — CanonicalOptionsChainEntry.expiration flip.

Covers:
- Schema enforcement (expiration now required at pydantic level)
- Deribit symbol parser (_parse_deribit_option_expiry) covering happy path,
  single-digit day, unknown month, malformed segments
- Round-trip: parse from instrument_name, construct entry, verify expiration
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.canonical.domain import CanonicalOptionsChainEntry
from unified_api_contracts.normalize_utils.options import _parse_deribit_option_expiry

# ---------------------------------------------------------------------------
# Schema enforcement
# ---------------------------------------------------------------------------


def test_expiration_required():
    """Pydantic raises ValidationError when expiration is omitted."""
    with pytest.raises(ValidationError) as exc_info:
        CanonicalOptionsChainEntry(  # type: ignore[call-arg]
            timestamp=datetime(2026, 5, 13, 14, 0, tzinfo=UTC),
            venue="deribit",
            symbol="BTC-28JUN24-70000-C",
            underlying="BTC",
            strike=Decimal("70000"),
            option_type="call",
            # expiration intentionally omitted
        )
    err = exc_info.value.errors()[0]
    assert err["loc"] == ("expiration",)
    assert err["type"] == "missing"


def test_expiration_rejects_none_explicitly():
    """Pydantic raises when expiration is explicitly None."""
    with pytest.raises(ValidationError):
        CanonicalOptionsChainEntry(
            timestamp=datetime(2026, 5, 13, 14, 0, tzinfo=UTC),
            venue="deribit",
            symbol="BTC-28JUN24-70000-C",
            underlying="BTC",
            strike=Decimal("70000"),
            option_type="call",
            expiration=None,  # type: ignore[arg-type]
        )


def test_canonical_options_chain_entry_with_expiration():
    """Constructs cleanly when expiration provided."""
    entry = CanonicalOptionsChainEntry(
        timestamp=datetime(2026, 5, 13, 14, 0, tzinfo=UTC),
        venue="deribit",
        symbol="BTC-28JUN24-70000-C",
        underlying="BTC",
        strike=Decimal("70000"),
        option_type="call",
        expiration=datetime(2024, 6, 28, 8, 0, tzinfo=UTC),
    )
    assert entry.expiration == datetime(2024, 6, 28, 8, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Deribit symbol parser
# ---------------------------------------------------------------------------


def test_deribit_parser_happy_path_two_digit_day():
    """BTC-28JUN24-70000-C → 2024-06-28 08:00 UTC."""
    result = _parse_deribit_option_expiry("BTC-28JUN24-70000-C")
    assert result == datetime(2024, 6, 28, 8, 0, tzinfo=UTC)


def test_deribit_parser_happy_path_single_digit_day():
    """ETH-7JAN25-3000-P → 2025-01-07 08:00 UTC."""
    result = _parse_deribit_option_expiry("ETH-7JAN25-3000-P")
    assert result == datetime(2025, 1, 7, 8, 0, tzinfo=UTC)


def test_deribit_parser_all_12_months():
    """All 12 month codes parse correctly."""
    expected_months = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    for code, month in expected_months.items():
        sym = f"BTC-15{code}26-50000-C"
        result = _parse_deribit_option_expiry(sym)
        assert result.month == month, f"Month {code} failed: got {result.month}, expected {month}"


def test_deribit_parser_rejects_short_symbol():
    """Symbol with <4 segments raises ValueError."""
    with pytest.raises(ValueError, match=r"expected 4"):
        _parse_deribit_option_expiry("BTC-28JUN24")


def test_deribit_parser_rejects_short_expiry_segment():
    """Expiry segment too short raises ValueError."""
    with pytest.raises(ValueError, match="DDMMMYY"):
        _parse_deribit_option_expiry("BTC-J24-70000-C")


def test_deribit_parser_rejects_unknown_month():
    """Unknown month code raises ValueError."""
    with pytest.raises(ValueError, match="Unknown Deribit month"):
        _parse_deribit_option_expiry("BTC-28XXX24-70000-C")


def test_deribit_parser_rejects_non_numeric_day():
    """Non-numeric day raises ValueError."""
    with pytest.raises(ValueError, match="day/year"):
        _parse_deribit_option_expiry("BTC-XXJUN24-70000-C")


def test_deribit_parser_expiry_time_is_08_utc():
    """Deribit settlement convention: all parsed expiries land at 08:00 UTC."""
    result = _parse_deribit_option_expiry("BTC-28JUN24-70000-C")
    assert result.hour == 8
    assert result.minute == 0
    assert result.second == 0
    assert result.tzinfo == UTC


def test_deribit_parser_year_2000_offset():
    """Two-digit year is interpreted as 2000+YY."""
    result = _parse_deribit_option_expiry("BTC-28JUN99-70000-C")
    assert result.year == 2099
    result_low = _parse_deribit_option_expiry("BTC-28JUN20-70000-C")
    assert result_low.year == 2020
