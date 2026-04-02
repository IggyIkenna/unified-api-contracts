"""Unit tests for phase5 (tradfi, onchain) and phase6 (market_state) normalizers.

Covers:
- tradfi: FRED, ECB, OFR, OpenBB normalizers
- onchain: Glassnode, DeFiLlama normalizers
- market_state: Binance, Bybit, OKX, Deribit, Coinbase, IBKR, Kalshi, Betfair normalizers
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

# ---------------------------------------------------------------------------
# tradfi — FRED
# ---------------------------------------------------------------------------


class TestFredNormalizers:
    def test_normalize_fred_observation_valid(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalYieldCurvePoint,
        )
        from unified_api_contracts.external.fred.schemas import (
            FredObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_observation,
        )

        raw = FredObservation(date="2024-01-15", value="4.25", series_id="DGS10")
        result = normalize_fred_observation(raw, series_id="DGS10", tenor="10Y")
        assert isinstance(result, CanonicalYieldCurvePoint)
        assert result.value == Decimal("4.25")
        assert result.tenor == "10Y"
        assert result.currency == "USD"
        assert result.venue == "fred"
        assert result.series_id == "DGS10"
        assert result.timestamp.tzinfo is not None

    def test_normalize_fred_observation_missing_sentinel(self):
        from unified_api_contracts.external.fred.schemas import (
            FredObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_observation,
        )

        raw = FredObservation(date="2024-01-15", value=".", series_id="DGS10")
        result = normalize_fred_observation(raw)
        assert result is None

    def test_normalize_fred_observation_empty_value(self):
        from unified_api_contracts.external.fred.schemas import (
            FredObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_observation,
        )

        raw = FredObservation(date="2024-01-15", value="", series_id="DGS2")
        result = normalize_fred_observation(raw)
        assert result is None

    def test_normalize_fred_observation_none_value(self):
        from unified_api_contracts.external.fred.schemas import (
            FredObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_observation,
        )

        raw = FredObservation(date="2024-01-15", value=None, series_id="DGS2")
        result = normalize_fred_observation(raw)
        assert result is None

    def test_normalize_fred_series_response(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalYieldCurvePoint,
        )
        from unified_api_contracts.external.fred.schemas import (
            FredObservation,
            FredSeriesObservationsResponse,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_series_response,
        )

        obs = [
            FredObservation(date="2024-01-10", value="4.1", series_id="DGS10"),
            FredObservation(date="2024-01-11", value=".", series_id="DGS10"),  # missing
            FredObservation(date="2024-01-12", value="4.2", series_id="DGS10"),
        ]
        raw = FredSeriesObservationsResponse(observations=obs)
        results = normalize_fred_series_response(raw, series_id="DGS10", tenor="10Y")
        assert len(results) == 2
        assert all(isinstance(r, CanonicalYieldCurvePoint) for r in results)

    def test_normalize_fred_series_response_empty(self):
        from unified_api_contracts.external.fred.schemas import (
            FredSeriesObservationsResponse,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_series_response,
        )

        raw = FredSeriesObservationsResponse(observations=[])
        results = normalize_fred_series_response(raw)
        assert results == []

    def test_normalize_fred_observation_uses_raw_series_id(self):
        """series_id falls back to raw.series_id when not provided."""
        from unified_api_contracts.external.fred.schemas import (
            FredObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_fred_observation,
        )

        raw = FredObservation(date="2024-03-01", value="5.0", series_id="DGS30")
        result = normalize_fred_observation(raw)
        assert result is not None
        assert result.series_id == "DGS30"


# ---------------------------------------------------------------------------
# tradfi — ECB
# ---------------------------------------------------------------------------


class TestEcbNormalizers:
    def test_normalize_ecb_yield_curve_observation_full_date(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalYieldCurvePoint,
        )
        from unified_api_contracts.external.ecb.schemas import (
            EcbYieldCurveObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ecb_yield_curve_observation,
        )

        raw = EcbYieldCurveObservation(period="2024-06-15", value=3.5)
        result = normalize_ecb_yield_curve_observation(raw, series_id="OIS5Y", tenor="5Y")
        assert isinstance(result, CanonicalYieldCurvePoint)
        assert result.value == Decimal("3.5")
        assert result.currency == "EUR"
        assert result.timestamp.year == 2024
        assert result.timestamp.month == 6
        assert result.timestamp.day == 15

    def test_normalize_ecb_yield_curve_observation_year_month(self):
        from unified_api_contracts.external.ecb.schemas import (
            EcbYieldCurveObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ecb_yield_curve_observation,
        )

        raw = EcbYieldCurveObservation(period="2024-06", value=3.5)
        result = normalize_ecb_yield_curve_observation(raw)
        assert result is not None
        assert result.timestamp.month == 6
        assert result.timestamp.day == 1  # defaults to first of month

    def test_normalize_ecb_yield_curve_observation_none_value(self):
        from unified_api_contracts.external.ecb.schemas import (
            EcbYieldCurveObservation,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ecb_yield_curve_observation,
        )

        raw = EcbYieldCurveObservation(period="2024-06-15", value=None)
        result = normalize_ecb_yield_curve_observation(raw)
        assert result is None

    def test_normalize_ecb_dataflow_response(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalYieldCurvePoint,
        )
        from unified_api_contracts.external.ecb.schemas import (
            EcbDataflowObservation,
            EcbDataflowResponse,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ecb_dataflow_response,
        )

        # EcbDataflowObservation observations are dict[str, str]
        obs = EcbDataflowObservation(
            key="B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
            observations=[{"2024-01-15": "2.8", "2024-01-16": "2.9"}],
        )
        raw = EcbDataflowResponse(data=[obs])
        results = normalize_ecb_dataflow_response(raw, series_id="OIS10Y")
        assert len(results) == 2
        assert all(isinstance(r, CanonicalYieldCurvePoint) for r in results)
        assert all(r.currency == "EUR" for r in results)

    def test_normalize_ecb_dataflow_response_empty(self):
        from unified_api_contracts.external.ecb.schemas import (
            EcbDataflowResponse,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ecb_dataflow_response,
        )

        raw = EcbDataflowResponse(data=[])
        results = normalize_ecb_dataflow_response(raw)
        assert results == []


# ---------------------------------------------------------------------------
# tradfi — OFR CDS
# ---------------------------------------------------------------------------


class TestOfrNormalizers:
    def test_normalize_ofr_cds_spread_valid(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalCdsSpread,
        )
        from unified_api_contracts.external.ofr.schemas import (
            OfrCdsSpreadIndex,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ofr_cds_spread,
        )

        raw = OfrCdsSpreadIndex(
            date="2024-03-01",
            series_id="CDX.NA.IG",
            value=75.5,
            index_name="CDX North America IG",
            tenor="5Y",
            sector="IG",
        )
        result = normalize_ofr_cds_spread(raw)
        assert isinstance(result, CanonicalCdsSpread)
        assert result.spread_bps == Decimal("75.5")
        assert result.venue == "ofr"
        assert result.tenor == "5Y"
        assert result.sector == "IG"

    def test_normalize_ofr_cds_spread_none_value(self):
        from unified_api_contracts.external.ofr.schemas import (
            OfrCdsSpreadIndex,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ofr_cds_spread,
        )

        raw = OfrCdsSpreadIndex(date="2024-03-01", series_id="CDX.NA.IG", value=None)
        result = normalize_ofr_cds_spread(raw)
        assert result is None

    def test_normalize_ofr_cds_response(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalCdsSpread,
        )
        from unified_api_contracts.external.ofr.schemas import (
            OfrCdsResponse,
            OfrCdsSpreadIndex,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_ofr_cds_response,
        )

        items = [
            OfrCdsSpreadIndex(date="2024-01-01", series_id="CDX.NA.IG", value=70.0),
            OfrCdsSpreadIndex(date="2024-01-02", series_id="CDX.NA.IG", value=None),  # skip
            OfrCdsSpreadIndex(date="2024-01-03", series_id="CDX.NA.IG", value=72.0),
        ]
        raw = OfrCdsResponse(data=items)
        results = normalize_ofr_cds_response(raw)
        assert len(results) == 2
        assert all(isinstance(r, CanonicalCdsSpread) for r in results)


# ---------------------------------------------------------------------------
# tradfi — OpenBB Treasury
# ---------------------------------------------------------------------------


class TestOpenBBNormalizers:
    def test_normalize_openbb_treasury_price_valid(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalBondData,
        )
        from unified_api_contracts.external.openbb.schemas import (
            OpenBBTreasuryPrice,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_openbb_treasury_price,
        )

        raw = OpenBBTreasuryPrice(
            symbol="US10Y",
            name="10-Year Treasury",
            date="2024-03-01",
            bid=98.5,
            ask=98.6,
            last=98.55,
            yield_to_maturity=4.25,
        )
        result = normalize_openbb_treasury_price(raw)
        assert isinstance(result, CanonicalBondData)
        assert result.symbol == "US10Y"
        assert result.bid == Decimal("98.5")
        assert result.ask == Decimal("98.6")
        assert result.yield_to_maturity == Decimal("4.25")

    def test_normalize_openbb_treasury_price_no_symbol_no_name(self):
        from unified_api_contracts.external.openbb.schemas import (
            OpenBBTreasuryPrice,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_openbb_treasury_price,
        )

        raw = OpenBBTreasuryPrice(symbol=None, name=None, date="2024-03-01")
        result = normalize_openbb_treasury_price(raw)
        assert result is None

    def test_normalize_openbb_treasury_prices_response(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalBondData,
        )
        from unified_api_contracts.external.openbb.schemas import (
            OpenBBTreasuryPrice,
            OpenBBTreasuryPricesResponse,
        )
        from unified_api_contracts.normalize_utils.tradfi import (
            normalize_openbb_treasury_prices_response,
        )

        items = [
            OpenBBTreasuryPrice(symbol="US2Y", name="2Y", date="2024-01-01", last=99.0),
            OpenBBTreasuryPrice(symbol=None, name=None, date="2024-01-01"),  # skip
        ]
        raw = OpenBBTreasuryPricesResponse(results=items)
        results = normalize_openbb_treasury_prices_response(raw)
        assert len(results) == 1
        assert isinstance(results[0], CanonicalBondData)


# ---------------------------------------------------------------------------
# onchain — Glassnode
# ---------------------------------------------------------------------------


class TestGlassnodeNormalizers:
    def test_normalize_glassnode_mvrv(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.glassnode.schemas import (
            MvrvRatio,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_mvrv,
        )

        raw = MvrvRatio(timestamp=1704067200, mvrv=2.5)
        result = normalize_glassnode_mvrv(raw)
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "mvrv"
        assert result.value == Decimal("2.5")
        assert result.asset == "BTC"
        assert result.venue == "glassnode"
        assert result.timestamp.tzinfo is not None

    def test_normalize_glassnode_timeseries_point(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.glassnode.schemas import (
            GlassnodeTimeseriesPoint,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_timeseries_point,
        )

        raw = GlassnodeTimeseriesPoint(t=1704067200, v=1234567890.0)
        result = normalize_glassnode_timeseries_point(raw, metric_type="custom_metric", asset="ETH")
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "custom_metric"
        assert result.asset == "ETH"

    def test_normalize_glassnode_timeseries_point_none_v(self):
        from unified_api_contracts.external.glassnode.schemas import (
            GlassnodeTimeseriesPoint,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_timeseries_point,
        )

        raw = GlassnodeTimeseriesPoint(t=1704067200, v=None)
        result = normalize_glassnode_timeseries_point(raw, metric_type="custom_metric")
        assert result is None

    def test_normalize_glassnode_sopr(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.glassnode.schemas import (
            SoprMetric,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_sopr,
        )

        raw = SoprMetric(timestamp=1704067200, sopr=1.02)
        result = normalize_glassnode_sopr(raw)
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "sopr"

    def test_normalize_glassnode_nvt(self):
        from unified_api_contracts.external.glassnode.schemas import (
            NvtRatio,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_nvt,
        )

        raw = NvtRatio(timestamp=1704067200, nvt=55.0)
        result = normalize_glassnode_nvt(raw)
        assert result is not None
        assert result.metric_type == "nvt"

    def test_normalize_glassnode_nvt_signal(self):
        from unified_api_contracts.external.glassnode.schemas import (
            NvtSignal,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_nvt_signal,
        )

        raw = NvtSignal(timestamp=1704067200, nvt_signal=65.0)
        result = normalize_glassnode_nvt_signal(raw)
        assert result is not None
        assert result.metric_type == "nvt_signal"

    def test_normalize_glassnode_exchange_reserves(self):
        from unified_api_contracts.external.glassnode.schemas import (
            ExchangeReserves,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_exchange_reserves,
        )

        raw = ExchangeReserves(timestamp=1704067200, asset="BTC", balance_sum=500000.0, net_flow_24h=-1000.0)
        result = normalize_glassnode_exchange_reserves(raw)
        assert result is not None
        assert result.metric_type == "exchange_reserves"
        assert result.secondary_value == Decimal("-1000.0")

    def test_normalize_glassnode_realized_cap(self):
        from unified_api_contracts.external.glassnode.schemas import (
            RealizedCap,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_realized_cap,
        )

        raw = RealizedCap(timestamp=1704067200, realized_cap_usd=400000000000.0)
        result = normalize_glassnode_realized_cap(raw)
        assert result is not None
        assert result.metric_type == "realized_cap"

    def test_normalize_glassnode_thermocap(self):
        from unified_api_contracts.external.glassnode.schemas import (
            ThermoCap,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_thermocap,
        )

        raw = ThermoCap(timestamp=1704067200, thermocap_usd=50000000000.0)
        result = normalize_glassnode_thermocap(raw)
        assert result is not None
        assert result.metric_type == "thermocap"

    def test_normalize_glassnode_mvrv_z_score(self):
        from unified_api_contracts.external.glassnode.schemas import (
            MvrvZScore,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_mvrv_z_score,
        )

        raw = MvrvZScore(timestamp=1704067200, mvrv_z_score=1.5)
        result = normalize_glassnode_mvrv_z_score(raw)
        assert result is not None
        assert result.metric_type == "mvrv_z_score"

    def test_normalize_glassnode_hodl_wave(self):
        from unified_api_contracts.external.glassnode.schemas import (
            HodlWave,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_glassnode_hodl_wave,
        )

        raw = HodlWave(
            timestamp=1704067200,
            band_1d=0.02,
            band_1d_1w=0.05,
            band_1w_1m=0.10,
            band_1m_3m=0.12,
            band_3m_6m=0.08,
            band_6m_12m=0.07,
            band_1y_2y=0.06,
            band_2y_3y=0.05,
            band_3y_5y=0.10,
            band_5y_7y=0.12,
            band_7y_10y=0.09,
            band_10y_plus=0.08,
        )
        result = normalize_glassnode_hodl_wave(raw)
        assert result is not None
        assert result.metric_type == "hodl_wave"
        assert result.value == Decimal("0.02")  # band_1d


# ---------------------------------------------------------------------------
# onchain — DeFiLlama
# ---------------------------------------------------------------------------


class TestDefiLlamaNormalizers:
    def test_normalize_defillama_protocol(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.defillama.schemas import (
            DefiLlamaProtocol,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_defillama_protocol,
        )

        raw = DefiLlamaProtocol(
            id="aave",
            name="Aave",
            tvl=5000000000.0,
            chain="Ethereum",
            category="Lending",
        )
        result = normalize_defillama_protocol(raw)
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "protocol_tvl"
        assert result.entity == "Aave"
        assert result.value == Decimal("5000000000.0")
        assert result.venue == "defillama"

    def test_normalize_defillama_chain_tvl(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.defillama.schemas import (
            DefiLlamaChainTvl,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_defillama_chain_tvl,
        )

        # DefiLlamaChainTvl uses `name` for chain name
        raw = DefiLlamaChainTvl(name="Ethereum", tvl=30000000000.0)
        result = normalize_defillama_chain_tvl(raw)
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "chain_tvl"
        assert result.chain == "Ethereum"

    def test_normalize_defillama_tvl_history_point(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.defillama.schemas import (
            DefiLlamaTvlHistoryPoint,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_defillama_tvl_history_point,
        )

        raw = DefiLlamaTvlHistoryPoint(date=1704067200, totalLiquidityUSD=28000000000.0)
        result = normalize_defillama_tvl_history_point(raw, protocol_name="Aave")
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "protocol_tvl_history"
        assert result.entity == "Aave"

    def test_normalize_defillama_yield_pool(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalOnChainMetric,
        )
        from unified_api_contracts.external.defillama.schemas import (
            DefiLlamaYieldPool,
        )
        from unified_api_contracts.normalize_utils.onchain import (
            normalize_defillama_yield_pool,
        )

        raw = DefiLlamaYieldPool(
            pool="0xabc123",
            project="Aave",
            symbol="USDC",
            chain="Ethereum",
            apy=5.2,
            tvlUsd=100000000.0,
        )
        result = normalize_defillama_yield_pool(raw)
        assert isinstance(result, CanonicalOnChainMetric)
        assert result.metric_type == "yield_pool"
        assert result.secondary_value == Decimal("100000000.0")


# ---------------------------------------------------------------------------
# market_state — Generic and per-venue
# ---------------------------------------------------------------------------


class TestMarketStateNormalizers:
    def test_normalize_binance_trading(self):
        from unified_api_contracts.canonical.domain import (
            CanonicalMarketStateEvent,
            MarketState,
        )
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="TRADING", symbol="BTCUSDT")
        assert isinstance(result, CanonicalMarketStateEvent)
        assert result.state == MarketState.NORMAL
        assert result.venue == "binance"
        assert result.instrument_key == "binance:SPOT_PAIR:BTCUSDT"

    def test_normalize_binance_halt(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="HALT", symbol="ETHUSDT")
        assert result.state == MarketState.HALTED

    def test_normalize_binance_auction_match(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="AUCTION_MATCH", symbol="BTCUSDT")
        assert result.state == MarketState.AUCTION

    def test_normalize_binance_pre_trading(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="PRE_TRADING", symbol="NEWUSDT")
        assert result.state == MarketState.PRE_MARKET

    def test_normalize_bybit_trading(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_bybit_market_state,
        )

        result = normalize_bybit_market_state(status="TRADING", symbol="BTCUSDT")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "bybit:PERPETUAL:BTCUSDT"

    def test_normalize_bybit_closed(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_bybit_market_state,
        )

        result = normalize_bybit_market_state(status="CLOSED", symbol="BTCUSDT")
        assert result.state == MarketState.CLOSED

    def test_normalize_okx_live(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_okx_market_state,
        )

        result = normalize_okx_market_state(state="live", inst_id="BTC-USDT-SWAP")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "okx:PERPETUAL:BTC-USDT-SWAP"

    def test_normalize_okx_suspend(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_okx_market_state,
        )

        result = normalize_okx_market_state(state="suspend", inst_id="BTC-USDT-SWAP")
        assert result.state == MarketState.HALTED

    def test_normalize_deribit_open(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_deribit_market_state,
        )

        result = normalize_deribit_market_state(state="open", instrument_name="BTC-PERPETUAL")
        assert result.state == MarketState.NORMAL

    def test_normalize_deribit_closed(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_deribit_market_state,
        )

        result = normalize_deribit_market_state(state="closed", instrument_name="BTC-PERPETUAL")
        assert result.state == MarketState.CLOSED

    def test_normalize_coinbase_online(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_coinbase_market_state,
        )

        result = normalize_coinbase_market_state(trading_mode="ONLINE", product_id="BTC-USD")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "coinbase:SPOT:BTC-USD"

    def test_normalize_coinbase_offline(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_coinbase_market_state,
        )

        result = normalize_coinbase_market_state(trading_mode="OFFLINE", product_id="BTC-USD")
        assert result.state == MarketState.HALTED

    def test_normalize_ibkr_open(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(trading_phase="OPEN", symbol="AAPL")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "ibkr:SPOT_PAIR:AAPL"

    def test_normalize_ibkr_afterhours(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(trading_phase="AFTERHOURS", symbol="AAPL")
        assert result.state == MarketState.POST_MARKET

    def test_normalize_ibkr_futures_type_map(self):
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(trading_phase="OPEN", symbol="ES", sec_type="FUT")
        assert result.instrument_key == "ibkr:FUTURE:ES"

    def test_normalize_kalshi_open(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_kalshi_market_state,
        )

        result = normalize_kalshi_market_state(status="open", ticker="BTCZ-25JAN31-T50000")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "kalshi:PREDICTION:BTCZ-25JAN31-T50000"

    def test_normalize_kalshi_paused(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_kalshi_market_state,
        )

        result = normalize_kalshi_market_state(status="paused", ticker="BTCZ-25JAN31-T50000")
        assert result.state == MarketState.HALTED

    def test_normalize_betfair_open(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_betfair_market_state,
        )

        result = normalize_betfair_market_state(status="OPEN", market_id="1.234567")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "betfair:MARKET:1.234567"

    def test_normalize_betfair_suspended(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_betfair_market_state,
        )

        result = normalize_betfair_market_state(status="SUSPENDED", market_id="1.234567")
        assert result.state == MarketState.HALTED

    def test_normalize_betfair_inactive_pre_market(self):
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_betfair_market_state,
        )

        result = normalize_betfair_market_state(status="INACTIVE", market_id="1.234567")
        assert result.state == MarketState.PRE_MARKET

    def test_normalize_market_state_with_timestamp(self):
        """Custom timestamp propagates correctly."""
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        result = normalize_binance_market_state(status="TRADING", symbol="BTCUSDT", timestamp=ts)
        assert result.timestamp == ts

    def test_normalize_market_state_with_previous_state(self):
        """previous_state field propagates."""
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(
            status="HALT",
            symbol="BTCUSDT",
            previous_state=MarketState.NORMAL,
            reason="Circuit breaker triggered",
        )
        assert result.previous_state == MarketState.NORMAL
        assert result.reason == "Circuit breaker triggered"

    def test_normalize_market_state_case_insensitive(self):
        """State lookup is case-insensitive (raw_state.upper())."""
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="trading", symbol="BTCUSDT")
        assert result.state == MarketState.NORMAL

    def test_normalize_market_state_unknown_falls_back_to_normal(self):
        """Unknown states fall back to NORMAL per generic helper default."""
        from unified_api_contracts.canonical.domain import MarketState
        from unified_api_contracts.normalize_utils.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="TOTALLY_UNKNOWN_STATE", symbol="BTCUSDT")
        assert result.state == MarketState.NORMAL
