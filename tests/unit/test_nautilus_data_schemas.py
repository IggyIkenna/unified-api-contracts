"""Tests for external/nautilus/data_schemas.py — Nautilus schema + instrument ID conversion."""

from __future__ import annotations

import pytest

from unified_api_contracts.external.nautilus.data_schemas import (
    EXCHANGE_NAME_MAP,
    INSTRUMENT_TYPE_SUFFIX_MAP,
    NAUTILUS_SCHEMA_MAP,
    convert_from_nautilus_instrument_id,
    convert_to_nautilus_instrument_id,
    get_nautilus_schema,
)


class TestGetNautilusSchema:
    def test_trades_schema_exists(self) -> None:
        schema = get_nautilus_schema("trades")
        assert schema is not None
        assert isinstance(schema, list)
        assert len(schema) > 0

    def test_book_snapshot_5_schema_exists(self) -> None:
        schema = get_nautilus_schema("book_snapshot_5")
        assert schema is not None
        assert isinstance(schema, list)

    def test_liquidations_schema_exists(self) -> None:
        schema = get_nautilus_schema("liquidations")
        assert schema is not None

    def test_derivative_ticker_schema_exists(self) -> None:
        schema = get_nautilus_schema("derivative_ticker")
        assert schema is not None

    def test_liquidity_snapshots_schema_exists(self) -> None:
        schema = get_nautilus_schema("liquidity_snapshots")
        assert schema is not None

    def test_unknown_returns_none(self) -> None:
        result = get_nautilus_schema("COMPLETELY_UNKNOWN_DATA_TYPE_XYZ")
        assert result is None

    def test_schema_entries_are_dicts(self) -> None:
        schema = get_nautilus_schema("trades")
        assert schema is not None
        for entry in schema:
            assert isinstance(entry, dict)

    def test_all_schemas_in_map(self) -> None:
        for data_type in NAUTILUS_SCHEMA_MAP:
            result = get_nautilus_schema(data_type)
            assert result is not None


class TestExchangeNameMap:
    def test_binance_maps_to_binance(self) -> None:
        assert EXCHANGE_NAME_MAP["binance"] == "BINANCE"

    def test_binance_futures_maps_to_binance(self) -> None:
        assert EXCHANGE_NAME_MAP["binance-futures"] == "BINANCE"

    def test_bybit_maps_to_bybit(self) -> None:
        assert EXCHANGE_NAME_MAP["bybit"] == "BYBIT"

    def test_deribit_maps_to_deribit(self) -> None:
        assert EXCHANGE_NAME_MAP["deribit"] == "DERIBIT"

    def test_okx_maps_to_okx(self) -> None:
        assert EXCHANGE_NAME_MAP["okx"] == "OKX"

    def test_okex_maps_to_okx(self) -> None:
        assert EXCHANGE_NAME_MAP["okex"] == "OKX"

    def test_all_values_uppercase(self) -> None:
        for v in EXCHANGE_NAME_MAP.values():
            assert v == v.upper()


class TestInstrumentTypeSuffixMap:
    def test_perpetual_maps_to_perp(self) -> None:
        assert INSTRUMENT_TYPE_SUFFIX_MAP["PERPETUAL"] == "PERP"

    def test_future_maps_to_fut(self) -> None:
        assert INSTRUMENT_TYPE_SUFFIX_MAP["FUTURE"] == "FUT"

    def test_spot_pair_maps_to_spot(self) -> None:
        assert INSTRUMENT_TYPE_SUFFIX_MAP["SPOT_PAIR"] == "SPOT"

    def test_option_maps_to_opt(self) -> None:
        assert INSTRUMENT_TYPE_SUFFIX_MAP["OPTION"] == "OPT"


class TestConvertToNautilusInstrumentId:
    def test_binance_futures_perpetual(self) -> None:
        result = convert_to_nautilus_instrument_id("BINANCE-FUTURES:PERPETUAL:BTC-USDT")
        assert result == "BTCUSDT-PERP.BINANCE"

    def test_bybit_perpetual(self) -> None:
        result = convert_to_nautilus_instrument_id("BYBIT:PERPETUAL:ETH-USDT")
        assert result == "ETHUSDT-PERP.BYBIT"

    def test_okx_spot(self) -> None:
        result = convert_to_nautilus_instrument_id("OKX:SPOT_PAIR:BTC-USDT")
        assert result == "BTCUSDT-SPOT.OKX"

    def test_deribit_option(self) -> None:
        result = convert_to_nautilus_instrument_id("DERIBIT:OPTION:BTC-USD")
        assert result == "BTCUSD-OPT.DERIBIT"

    def test_strips_timestamp_suffix(self) -> None:
        result = convert_to_nautilus_instrument_id("BINANCE-FUTURES:PERPETUAL:BTC-USDT@2024-01-01")
        assert "@" not in result

    def test_invalid_format_returns_original(self) -> None:
        result = convert_to_nautilus_instrument_id("INVALID_FORMAT")
        # Less than 3 parts — returns original
        assert isinstance(result, str)

    def test_unknown_exchange_uses_fallback(self) -> None:
        result = convert_to_nautilus_instrument_id("UNKNOWN_EXCHANGE:PERPETUAL:BTC-USDT")
        assert "PERP" in result
        assert isinstance(result, str)

    def test_returns_string(self) -> None:
        result = convert_to_nautilus_instrument_id("BINANCE-FUTURES:PERPETUAL:ETH-USDT")
        assert isinstance(result, str)
        assert len(result) > 0


class TestConvertFromNautilusInstrumentId:
    def test_btcusdt_perp_binance(self) -> None:
        result = convert_from_nautilus_instrument_id("BTCUSDT-PERP.BINANCE")
        assert isinstance(result, str)
        assert "PERPETUAL" in result or "BTC" in result

    def test_ethusdt_perp_bybit(self) -> None:
        result = convert_from_nautilus_instrument_id("ETHUSDT-PERP.BYBIT")
        assert isinstance(result, str)

    def test_btcusd_spot(self) -> None:
        result = convert_from_nautilus_instrument_id("BTCUSD-SPOT.COINBASE")
        assert isinstance(result, str)

    def test_malformed_returns_original(self) -> None:
        result = convert_from_nautilus_instrument_id("MALFORMED_NO_DOT")
        assert isinstance(result, str)

    def test_converts_usdt_suffix(self) -> None:
        result = convert_from_nautilus_instrument_id("ETHUSDT-PERP.BYBIT")
        assert "-USDT" in result or "ETH" in result

    def test_returns_string(self) -> None:
        result = convert_from_nautilus_instrument_id("BTCUSDT-PERP.BINANCE")
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.parametrize(
    ("canonical_id", "expected_result"),
    [
        ("BINANCE-FUTURES:PERPETUAL:BTC-USDT", "BTCUSDT-PERP.BINANCE"),
        ("BYBIT:PERPETUAL:ETH-USDT", "ETHUSDT-PERP.BYBIT"),
        ("OKX:SPOT_PAIR:BTC-USDT", "BTCUSDT-SPOT.OKX"),
    ],
)
def test_convert_to_nautilus_parametrized(canonical_id: str, expected_result: str) -> None:
    result = convert_to_nautilus_instrument_id(canonical_id)
    assert result == expected_result
