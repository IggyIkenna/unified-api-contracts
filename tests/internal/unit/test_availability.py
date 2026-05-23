"""Unit tests for get_instruments_available_on.

Covers the per-day availability window, boundary inclusivity, open-ended
bounds (None on either side), combined filters, and edge cases across
options chains, futures chains, perpetuals, and equities.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from unified_api_contracts.internal.reference import get_instruments_available_on
from unified_api_contracts.internal.reference.instrument import (
    InstrumentRecord,
    InstrumentType,
    OptionType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int) -> _dt.datetime:
    return _dt.datetime(year, month, day, tzinfo=_dt.UTC)


def _make(
    instrument_key: str,
    venue: str,
    instrument_type: InstrumentType,
    *,
    available_from: _dt.datetime | None,
    available_to: _dt.datetime | None,
    expiry: _dt.datetime | None = None,
    strike: Decimal | None = None,
    option_type: OptionType | None = None,
    underlying: str | None = None,
) -> InstrumentRecord:
    return InstrumentRecord(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=instrument_type,
        available_from_datetime=available_from,
        available_to_datetime=available_to,
        expiry=expiry,
        strike=strike,
        option_type=option_type,
        underlying=underlying,
    )


# ---------------------------------------------------------------------------
# Options chain — listing_date + expiry_date windows
# ---------------------------------------------------------------------------


class TestOptionsChainWindow:
    def test_option_in_window(self) -> None:
        record = _make(
            "DERIBIT:OPTION:BTC-26DEC25-100000-C",
            "DERIBIT",
            InstrumentType.OPTION,
            available_from=_utc(2025, 1, 1),
            available_to=_utc(2025, 12, 26),
            expiry=_utc(2025, 12, 26),
            strike=Decimal("100000"),
            option_type=OptionType.CALL,
            underlying="BTC",
        )
        out = get_instruments_available_on(_dt.date(2025, 6, 15), [record])
        assert out == [record]

    def test_option_before_listing_excluded(self) -> None:
        record = _make(
            "DERIBIT:OPTION:BTC-26DEC25-100000-C",
            "DERIBIT",
            InstrumentType.OPTION,
            available_from=_utc(2025, 1, 1),
            available_to=_utc(2025, 12, 26),
            expiry=_utc(2025, 12, 26),
        )
        out = get_instruments_available_on(_dt.date(2024, 12, 31), [record])
        assert out == []

    def test_option_after_expiry_excluded(self) -> None:
        record = _make(
            "DERIBIT:OPTION:BTC-26DEC25-100000-C",
            "DERIBIT",
            InstrumentType.OPTION,
            available_from=_utc(2025, 1, 1),
            available_to=_utc(2025, 12, 26),
            expiry=_utc(2025, 12, 26),
        )
        out = get_instruments_available_on(_dt.date(2025, 12, 27), [record])
        assert out == []


# ---------------------------------------------------------------------------
# Futures chain — quarterly contracts
# ---------------------------------------------------------------------------


class TestFuturesChain:
    def _quarterlies(self) -> list[InstrumentRecord]:
        return [
            # Expired Q1
            _make(
                "BINANCE_FUTURES:FUTURE:BTCUSDT-250328",
                "BINANCE_FUTURES",
                InstrumentType.FUTURE,
                available_from=_utc(2024, 12, 28),
                available_to=_utc(2025, 3, 28),
                expiry=_utc(2025, 3, 28),
            ),
            # In-window Q2
            _make(
                "BINANCE_FUTURES:FUTURE:BTCUSDT-250627",
                "BINANCE_FUTURES",
                InstrumentType.FUTURE,
                available_from=_utc(2025, 3, 28),
                available_to=_utc(2025, 6, 27),
                expiry=_utc(2025, 6, 27),
            ),
            # Pre-listing Q3
            _make(
                "BINANCE_FUTURES:FUTURE:BTCUSDT-250926",
                "BINANCE_FUTURES",
                InstrumentType.FUTURE,
                available_from=_utc(2025, 6, 27),
                available_to=_utc(2025, 9, 26),
                expiry=_utc(2025, 9, 26),
            ),
        ]

    def test_only_in_window_quarterly_returned(self) -> None:
        catalogue = self._quarterlies()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue)
        assert len(out) == 1
        assert out[0].instrument_key == "BINANCE_FUTURES:FUTURE:BTCUSDT-250627"

    def test_expired_and_pre_listing_excluded(self) -> None:
        catalogue = self._quarterlies()
        # Pre-Q1 listing
        assert get_instruments_available_on(_dt.date(2024, 12, 1), catalogue) == []
        # After Q3 expiry
        assert get_instruments_available_on(_dt.date(2025, 10, 1), catalogue) == []


# ---------------------------------------------------------------------------
# Perpetual — open-ended (no expiry)
# ---------------------------------------------------------------------------


class TestPerpetual:
    def test_perp_included_for_any_date_after_listing(self) -> None:
        record = _make(
            "BINANCE_FUTURES:PERPETUAL:BTCUSDT",
            "BINANCE_FUTURES",
            InstrumentType.PERPETUAL,
            available_from=_utc(2020, 1, 1),
            available_to=None,
        )
        # Well after listing
        out = get_instruments_available_on(_dt.date(2030, 12, 31), [record])
        assert out == [record]
        # Before listing
        out2 = get_instruments_available_on(_dt.date(2019, 12, 31), [record])
        assert out2 == []

    def test_perp_with_no_from_matches_any_past_date(self) -> None:
        """available_from None = since inception (-inf)."""
        record = _make(
            "BINANCE_FUTURES:PERPETUAL:ETHUSDT",
            "BINANCE_FUTURES",
            InstrumentType.PERPETUAL,
            available_from=None,
            available_to=None,
        )
        out = get_instruments_available_on(_dt.date(1999, 1, 1), [record])
        assert out == [record]


# ---------------------------------------------------------------------------
# Equity — IPO → delisting
# ---------------------------------------------------------------------------


class TestEquityIpoDelisting:
    def test_equity_in_window(self) -> None:
        record = _make(
            "IBKR:EQUITY:AAPL",
            "IBKR",
            InstrumentType.EQUITY,
            available_from=_utc(1980, 12, 12),  # IPO
            available_to=None,
        )
        out = get_instruments_available_on(_dt.date(2024, 1, 2), [record])
        assert out == [record]

    def test_equity_delisted(self) -> None:
        record = _make(
            "IBKR:EQUITY:LEH",
            "IBKR",
            InstrumentType.EQUITY,
            available_from=_utc(1994, 5, 10),
            available_to=_utc(2008, 9, 15),  # Lehman delisting
        )
        assert get_instruments_available_on(_dt.date(2008, 9, 15), [record]) == [record]
        assert get_instruments_available_on(_dt.date(2008, 9, 16), [record]) == []
        assert get_instruments_available_on(_dt.date(1994, 5, 9), [record]) == []


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------


class TestCombinedFilters:
    def _mixed_catalogue(self) -> list[InstrumentRecord]:
        return [
            _make(
                "BINANCE_FUTURES:PERPETUAL:BTCUSDT",
                "BINANCE_FUTURES",
                InstrumentType.PERPETUAL,
                available_from=_utc(2020, 1, 1),
                available_to=None,
            ),
            _make(
                "BINANCE_FUTURES:FUTURE:BTCUSDT-250627",
                "BINANCE_FUTURES",
                InstrumentType.FUTURE,
                available_from=_utc(2025, 3, 28),
                available_to=_utc(2025, 6, 27),
            ),
            _make(
                "BYBIT:PERPETUAL:BTCUSDT",
                "BYBIT",
                InstrumentType.PERPETUAL,
                available_from=_utc(2020, 1, 1),
                available_to=None,
            ),
            _make(
                "IBKR:EQUITY:AAPL",
                "IBKR",
                InstrumentType.EQUITY,
                available_from=_utc(1980, 12, 12),
                available_to=None,
            ),
        ]

    def test_venue_filter_case_insensitive(self) -> None:
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue, venue="binance_futures")
        keys = {r.instrument_key for r in out}
        assert keys == {
            "BINANCE_FUTURES:PERPETUAL:BTCUSDT",
            "BINANCE_FUTURES:FUTURE:BTCUSDT-250627",
        }

    def test_instrument_type_filter_case_insensitive(self) -> None:
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue, instrument_type="perpetual")
        keys = {r.instrument_key for r in out}
        assert keys == {
            "BINANCE_FUTURES:PERPETUAL:BTCUSDT",
            "BYBIT:PERPETUAL:BTCUSDT",
        }

    def test_venue_and_instrument_type_and_filter(self) -> None:
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(
            _dt.date(2025, 5, 15),
            catalogue,
            venue="BINANCE_FUTURES",
            instrument_type="FUTURE",
        )
        assert [r.instrument_key for r in out] == ["BINANCE_FUTURES:FUTURE:BTCUSDT-250627"]

    def test_no_matches_returns_empty(self) -> None:
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue, venue="OKX")
        assert out == []

    def test_asset_group_filter_matches_none_until_field_populated(self) -> None:
        """InstrumentRecord has no `asset_group` field yet (populated in Phase 1.5).

        Until then, passing an asset_group filter should return nothing because
        no record can report a matching asset group.
        """
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue, asset_group="cefi")
        assert out == []

    def test_chain_filter_matches_none_until_field_populated(self) -> None:
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue, chain="ethereum")
        assert out == []

    def test_all_wildcards_returns_all_in_window(self) -> None:
        catalogue = self._mixed_catalogue()
        out = get_instruments_available_on(_dt.date(2025, 5, 15), catalogue)
        # All except the quarterly future if we were before 2025-03-28
        assert len(out) == 4


# ---------------------------------------------------------------------------
# Boundary dates — inclusive on both ends
# ---------------------------------------------------------------------------


class TestBoundaries:
    def test_exactly_on_available_from_included(self) -> None:
        record = _make(
            "BINANCE:SPOT_PAIR:BTCUSDT",
            "BINANCE",
            InstrumentType.SPOT_PAIR,
            available_from=_utc(2020, 6, 15),
            available_to=None,
        )
        out = get_instruments_available_on(_dt.date(2020, 6, 15), [record])
        assert out == [record]

    def test_exactly_on_available_to_included(self) -> None:
        record = _make(
            "BINANCE:SPOT_PAIR:XYZUSDT",
            "BINANCE",
            InstrumentType.SPOT_PAIR,
            available_from=_utc(2020, 1, 1),
            available_to=_utc(2024, 7, 4),
        )
        out = get_instruments_available_on(_dt.date(2024, 7, 4), [record])
        assert out == [record]

    def test_one_day_before_from_excluded(self) -> None:
        record = _make(
            "BINANCE:SPOT_PAIR:BTCUSDT",
            "BINANCE",
            InstrumentType.SPOT_PAIR,
            available_from=_utc(2020, 6, 15),
            available_to=None,
        )
        out = get_instruments_available_on(_dt.date(2020, 6, 14), [record])
        assert out == []

    def test_one_day_after_to_excluded(self) -> None:
        record = _make(
            "BINANCE:SPOT_PAIR:XYZUSDT",
            "BINANCE",
            InstrumentType.SPOT_PAIR,
            available_from=_utc(2020, 1, 1),
            available_to=_utc(2024, 7, 4),
        )
        out = get_instruments_available_on(_dt.date(2024, 7, 5), [record])
        assert out == []

    def test_intraday_from_uses_date_only(self) -> None:
        """available_from with a time component is compared by date only."""
        record = _make(
            "BINANCE:SPOT_PAIR:BTCUSDT",
            "BINANCE",
            InstrumentType.SPOT_PAIR,
            available_from=_dt.datetime(2020, 6, 15, 23, 59, tzinfo=_dt.UTC),
            available_to=None,
        )
        out = get_instruments_available_on(_dt.date(2020, 6, 15), [record])
        assert out == [record]


# ---------------------------------------------------------------------------
# Empty catalogue
# ---------------------------------------------------------------------------


class TestEmptyCatalogue:
    def test_empty_list(self) -> None:
        out = get_instruments_available_on(_dt.date(2025, 1, 1), [])
        assert out == []

    def test_empty_generator(self) -> None:
        def _empty() -> list[InstrumentRecord]:
            return []

        out = get_instruments_available_on(_dt.date(2025, 1, 1), _empty())
        assert out == []

    def test_empty_with_filters(self) -> None:
        out = get_instruments_available_on(
            _dt.date(2025, 1, 1),
            [],
            asset_group="cefi",
            venue="BINANCE",
            instrument_type="PERPETUAL",
            chain="ethereum",
        )
        assert out == []
