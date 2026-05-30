"""Tests for the canonical instrument_key parser (Phase 3.1).

Verifies parse / format / derive_* helpers in
``unified_api_contracts.canonical.instrument_key``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical import (
    derive_instrument_type_set,
    derive_symbol_set,
    derive_venue_set,
    format_instrument_key,
    parse_instrument_key,
)


class TestParseInstrumentKey:
    def test_canonical_3seg(self) -> None:
        assert parse_instrument_key("BINANCE-FUTURES:PERPETUAL:BTCUSDT") == (
            "BINANCE-FUTURES",
            "PERPETUAL",
            "BTCUSDT",
        )

    def test_symbol_with_colons(self) -> None:
        """Option symbols like BTC-28JUN24-70000-C contain no extra colons, but
        symbols CAN contain colons — split-on-first-2 rule must hold."""
        result = parse_instrument_key("DERIBIT:OPTION:BTC:EXTRA")
        assert result == ("DERIBIT", "OPTION", "BTC:EXTRA")

    def test_bare_symbol_returns_none(self) -> None:
        assert parse_instrument_key("BTCUSDT") is None

    def test_two_segments_returns_none(self) -> None:
        assert parse_instrument_key("BINANCE-FUTURES:PERPETUAL") is None

    def test_empty_venue_returns_none(self) -> None:
        assert parse_instrument_key(":PERPETUAL:BTCUSDT") is None

    def test_empty_instrument_type_returns_none(self) -> None:
        assert parse_instrument_key("BINANCE-FUTURES::BTCUSDT") is None

    def test_empty_symbol_returns_none(self) -> None:
        assert parse_instrument_key("BINANCE-FUTURES:PERPETUAL:") is None

    def test_bybit_perp(self) -> None:
        assert parse_instrument_key("BYBIT:PERPETUAL:ETHUSDT") == (
            "BYBIT",
            "PERPETUAL",
            "ETHUSDT",
        )


class TestFormatInstrumentKey:
    def test_round_trip(self) -> None:
        key = format_instrument_key("BINANCE-FUTURES", "PERPETUAL", "BTCUSDT")
        assert key == "BINANCE-FUTURES:PERPETUAL:BTCUSDT"
        assert parse_instrument_key(key) == ("BINANCE-FUTURES", "PERPETUAL", "BTCUSDT")

    def test_empty_venue_raises(self) -> None:
        with pytest.raises(ValueError):
            format_instrument_key("", "PERPETUAL", "BTCUSDT")

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError):
            format_instrument_key("BINANCE-FUTURES", "PERPETUAL", "")


class TestDeriveAxisSets:
    _KEYS = [
        "BINANCE-FUTURES:PERPETUAL:BTCUSDT",
        "BYBIT:PERPETUAL:ETHUSDT",
        "BINANCE-FUTURES:SPOT_PAIR:BTCUSDT",
        "BTCUSDT",  # bare symbol — must be skipped
    ]

    def test_venue_set(self) -> None:
        assert derive_venue_set(self._KEYS) == {"BINANCE-FUTURES", "BYBIT"}

    def test_instrument_type_set(self) -> None:
        assert derive_instrument_type_set(self._KEYS) == {"PERPETUAL", "SPOT_PAIR"}

    def test_symbol_set(self) -> None:
        assert derive_symbol_set(self._KEYS) == {"BTCUSDT", "ETHUSDT"}

    def test_bare_symbols_silently_skipped(self) -> None:
        assert derive_venue_set(["BTCUSDT", "ETHUSDT"]) == set()

    def test_empty_list(self) -> None:
        assert derive_venue_set([]) == set()
        assert derive_instrument_type_set([]) == set()
        assert derive_symbol_set([]) == set()
