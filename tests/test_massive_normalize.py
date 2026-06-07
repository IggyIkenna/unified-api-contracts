"""Unit tests for Massive raw → canonical InstrumentRecord normalisers.

Credential-free; pure normalisation of static raw payloads. Verifies the
canonical schema (instrument_key shape, venue tagging, instrument_type,
asset_class, lifecycle fields) matches the Databento conventions so the
canonical instrument schema is identical regardless of data source.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts import (
    MassiveFuturesContract,
    MassiveFuturesProduct,
    MassiveOptionContract,
    MassiveTicker,
    normalize_massive_equity,
    normalize_massive_futures,
    normalize_massive_fx,
    normalize_massive_index,
    normalize_massive_option,
)
from unified_api_contracts.external.massive import (
    venue_for_equity_mic,
    venue_for_futures_mic,
)
from unified_api_contracts.internal import AssetClass, InstrumentType, OptionType


class TestEquity:
    def test_nasdaq_common_stock(self) -> None:
        rec = normalize_massive_equity(
            MassiveTicker(ticker="AAPL", name="Apple Inc.", primary_exchange="XNAS", type="CS")
        )
        assert rec is not None
        assert rec.instrument_key == "NASDAQ:EQUITY:AAPL"
        assert rec.venue == "NASDAQ"
        assert rec.instrument_type == InstrumentType.EQUITY
        assert rec.asset_class == AssetClass.EQUITY
        assert rec.base_asset == "AAPL"
        assert rec.quote_asset == "USD"

    def test_arca_etf_maps_to_nyse_and_etf_type(self) -> None:
        rec = normalize_massive_equity(MassiveTicker(ticker="SPY", primary_exchange="ARCX", type="ETF"))
        assert rec is not None
        assert rec.instrument_key == "NYSE:ETF:SPY"
        assert rec.venue == "NYSE"
        assert rec.instrument_type == InstrumentType.ETF

    def test_unknown_mic_defaults_to_nyse(self) -> None:
        rec = normalize_massive_equity(MassiveTicker(ticker="XYZ", primary_exchange="ZZZZ", type="CS"))
        assert rec is not None
        assert rec.venue == "NYSE"

    def test_blank_ticker_skipped(self) -> None:
        assert normalize_massive_equity(MassiveTicker(ticker=None)) is None
        assert normalize_massive_equity(MassiveTicker(ticker="  ")) is None


class TestIndex:
    def test_vix_strips_i_prefix(self) -> None:
        rec = normalize_massive_index(MassiveTicker(ticker="I:VIX", name="Cboe Volatility Index", market="indices"))
        assert rec is not None
        assert rec.instrument_key == "CBOE:INDEX:VIX"
        assert rec.venue == "CBOE"
        assert rec.raw_symbol == "I:VIX"
        assert rec.instrument_type == InstrumentType.INDEX


class TestFx:
    def test_krwusd(self) -> None:
        rec = normalize_massive_fx(
            MassiveTicker(ticker="C:KRWUSD", base_currency_symbol="KRW", currency_symbol="USD", market="fx")
        )
        assert rec is not None
        assert rec.instrument_key == "FX:SPOT_PAIR:KRW-USD"
        assert rec.venue == "FX"
        assert rec.base_asset == "KRW"
        assert rec.quote_asset == "USD"
        assert rec.asset_class == AssetClass.FX

    def test_missing_currency_skipped(self) -> None:
        assert normalize_massive_fx(MassiveTicker(ticker="C:KRWUSD", base_currency_symbol="KRW")) is None


class TestOption:
    def test_spy_call(self) -> None:
        rec = normalize_massive_option(
            MassiveOptionContract(
                ticker="O:SPY260608C00500000",
                underlying_ticker="SPY",
                contract_type="call",
                expiration_date="2026-06-08",
                strike_price=500.0,
                shares_per_contract=100,
                primary_exchange="BATO",
            )
        )
        assert rec is not None
        assert rec.instrument_key == "NYSE:OPTION:O:SPY260608C00500000"
        assert rec.instrument_type == InstrumentType.OPTION
        assert rec.option_type == OptionType.CALL
        assert rec.strike == Decimal("500.0")
        assert rec.contract_size == Decimal("100")
        assert rec.underlying == "SPY"
        assert rec.expiry is not None and rec.expiry.year == 2026

    def test_missing_expiry_skipped(self) -> None:
        assert (
            normalize_massive_option(
                MassiveOptionContract(ticker="O:X", underlying_ticker="X", contract_type="put", expiration_date=None)
            )
            is None
        )

    def test_venue_override_for_index_option(self) -> None:
        # SPX index option: OPRA primary_exchange XCBO does not map to an equity
        # venue, so the caller pins venue=CBOE.
        rec = normalize_massive_option(
            MassiveOptionContract(
                ticker="O:SPX260618C05000000",
                underlying_ticker="SPX",
                contract_type="call",
                expiration_date="2026-06-18",
                strike_price=5000,
                primary_exchange="XCBO",
            ),
            venue="CBOE",
        )
        assert rec is not None
        assert rec.instrument_key == "CBOE:OPTION:O:SPX260618C05000000"
        assert rec.venue == "CBOE"
        assert rec.underlying == "SPX"


class TestFutures:
    def test_es_contract_with_product(self) -> None:
        rec = normalize_massive_futures(
            MassiveFuturesContract(
                ticker="ESH0",
                product_code="ES",
                trading_venue="XCME",
                first_trade_date="2018-12-21",
                last_trade_date="2020-03-20",
            ),
            MassiveFuturesProduct(
                product_code="ES", asset_sub_class="equity", trade_currency_code="USD", unit_of_measure_qty=50.0
            ),
        )
        assert rec is not None
        assert rec.instrument_key == "CME:FUTURE:ESH0"
        assert rec.venue == "CME"
        assert rec.asset_class == AssetClass.EQUITY
        assert rec.contract_size == Decimal("50.0")
        assert rec.underlying == "ES"
        assert rec.expiry is not None and rec.expiry.year == 2020
        assert rec.available_from_datetime is not None and rec.available_from_datetime.year == 2018

    def test_energy_subclass_is_commodity(self) -> None:
        rec = normalize_massive_futures(
            MassiveFuturesContract(
                ticker="CLF0", product_code="CL", trading_venue="XNYM", last_trade_date="2019-12-20"
            ),
            MassiveFuturesProduct(product_code="CL", asset_sub_class="energy"),
        )
        assert rec is not None
        assert rec.venue == "CME"
        assert rec.asset_class == AssetClass.COMMODITY

    def test_ice_mic_maps_to_ice(self) -> None:
        rec = normalize_massive_futures(
            MassiveFuturesContract(
                ticker="BRNF0", product_code="BRN", trading_venue="IFEU", last_trade_date="2019-12-31"
            ),
            None,
        )
        assert rec is not None
        assert rec.venue == "ICE"

    def test_blank_ticker_skipped(self) -> None:
        assert normalize_massive_futures(MassiveFuturesContract(ticker=None), None) is None

    def test_missing_expiry_skipped(self) -> None:
        assert normalize_massive_futures(MassiveFuturesContract(ticker="ESH0", product_code="ES"), None) is None


class TestMicMaps:
    def test_equity_mic(self) -> None:
        assert venue_for_equity_mic("XNAS") == "NASDAQ"
        assert venue_for_equity_mic("XNYS") == "NYSE"
        assert venue_for_equity_mic(None) == "NYSE"

    def test_futures_mic(self) -> None:
        assert venue_for_futures_mic("XCME") == "CME"
        assert venue_for_futures_mic("IFUS") == "ICE"
        assert venue_for_futures_mic(None) == "CME"
