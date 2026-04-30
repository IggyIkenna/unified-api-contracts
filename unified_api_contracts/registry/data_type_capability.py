"""DataTypeCapability registry — per (asset_group, data_type, venue) live/batch.

The catalogue generator joins this registry with the manifest to compute
``live_ready`` / ``batch_ready`` per tuple and to surface retention /
TTM / liquidity cutoffs in the catalogue artefact.

This is a seed registry — populated against high-volume capture targets as
of 2026-04-29. Every entry carries a ``# source:`` reference (file or
ADR) so future maintainers can verify the row. Missing tuples in the
catalogue generator default to ``live_capable=False`` /
``batch_capable=True`` — the venue clearly writes data (it appears in the
manifest) but we don't have a streaming declaration for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from unified_api_contracts.canonical.gcs_paths import AssetGroup


@dataclass(frozen=True)
class DataTypeCapability:
    """Per-tuple capability declaration.

    Identifying axes (``asset_group`` / ``data_type`` / ``venue`` /
    ``instrument_type``) match the manifest shard key columns. Coverage
    cutoffs (``ttm_cutoff_days`` / ``liquidity_cutoff_usd`` /
    ``retention_days``) carry through to the catalogue MD output so
    downstream readers can reason about expected denominator clipping.
    """

    asset_group: AssetGroup
    data_type: str
    venue: str
    instrument_type: str | None = None
    live_capable: bool = False  # WS / streaming feed exists
    batch_capable: bool = True  # REST / parquet snapshot exists
    streaming_protocol: str | None = None  # "ws" | "fix" | "sse" | None
    requires_credentials: bool = False
    ttm_cutoff_days: int | None = None  # options: ignore expiries beyond this
    liquidity_cutoff_usd: float | None = None  # ignore < this 24h volume
    retention_days: int | None = None  # rolling-window cutoff; None = unbounded
    notes: str | None = None
    sources: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Seed registry
# ---------------------------------------------------------------------------
# Ordering: by asset_group → data_type → venue. Each entry is a frozen
# dataclass — never mutate at import time.

DATA_TYPE_CAPABILITY_REGISTRY: Final[tuple[DataTypeCapability, ...]] = (
    # =====================================================================
    # CeFi
    # =====================================================================
    # Wire-format SSOT verified 2026-04-30 against
    # gs://market-data-tick-cefi-central-element-323112/_index/availability_index.parquet:
    #   - Venue tokens are exchange-product-specific: BINANCE-SPOT vs
    #     BINANCE-FUTURES vs OKX-FUTURES / OKX-SPOT / OKX-SWAP. BYBIT /
    #     DERIBIT / HYPERLIQUID / UPBIT keep a single token per venue.
    #   - data_type vocabulary (top-volume): trades, book_snapshot_5
    #     (NOT book_snapshot), derivative_ticker, futures_chain,
    #     liquidations.
    #   - instrument_type is empty for spot venues + most derivative_ticker
    #     rows; perpetual for liquidations + funding-bearing rows on
    #     BINANCE-FUTURES / BYBIT / OKX-SWAP.
    # No `funding_rate` / `open_interest` data_types in the wire format —
    # those signals are folded into `derivative_ticker`.
    #
    # Trades — derivative venues
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BINANCE-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/binance/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BINANCE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/binance/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX-SWAP",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="COINBASE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="UPBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BYBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/bybit/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/deribit.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="HYPERLIQUID",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/hyperliquid/",),
    ),
    # Book snapshots (depth-5)
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="BINANCE-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="BINANCE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="OKX-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="OKX-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="OKX-SWAP",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="COINBASE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="UPBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="BYBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        liquidity_cutoff_usd=5_000.0,
    ),
    # Derivative ticker — folds funding_rate, mark_price, index_price, OI
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="BINANCE-FUTURES",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Includes funding_rate + mark_price + index_price + OI",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="OKX-SWAP",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="BYBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # Liquidations
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="BINANCE-FUTURES",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="BYBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="OKX-SWAP",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # Futures chain bundle
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="futures_chain",
        venue="BINANCE-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="futures_chain",
        venue="BYBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # =====================================================================
    # DeFi
    # =====================================================================
    # Wire-format SSOT verified 2026-04-30. DeFi adapters today write to
    # the manifest with EMPTY data_type — the data-type axis in market
    # data is currently unused on the DeFi side. Capabilities are
    # therefore keyed by venue alone (one row per protocol). Aspirational
    # data_types (lending_indices / dex_pool_swaps / dex_pool_state /
    # lst_rates / yield_snapshots) are deferred until the DeFi adapters
    # start writing them — captured as a follow-up.
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="AAVE_V3",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        sources=("market_tick_data_service/market_interface/adapters/defi/aave/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="UNISWAP_V3",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        liquidity_cutoff_usd=1_000_000.0,
        sources=("market_tick_data_service/market_interface/adapters/defi/uniswap_v3_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="UNISWAP_V2",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="CURVE",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="BALANCER",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="COMPOUND_V3",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="LIDO",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="ETHENA",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="MORPHO",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="EIGENLAYER",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="rewards",
        venue="EIGENLAYER",
        instrument_type="staking",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="Eigenlayer restaking rewards stream — only DeFi tuple with a non-empty data_type today",
    ),
    # =====================================================================
    # TradFi
    # =====================================================================
    # Wire-format SSOT verified 2026-04-30 against
    # gs://market-data-tick-tradfi-central-element-323112/_index/availability_index.parquet:
    # venues = CME, ICE, CBOE, NYSE, NASDAQ, FX. data_types = ohlcv_1m,
    # ohlcv_24h, ohlcv_15m, trades, tbbo, options_chain. instrument_types =
    # future / equity / spot_pair / options_chain / combo (or empty).
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="CME",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="ICE",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="NYSE",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="NASDAQ",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_24h",
        venue="FX",
        instrument_type="spot_pair",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_15m",
        venue="CBOE",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="CME",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="ICE",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="NYSE",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="NASDAQ",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="tbbo",
        venue="CME",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="tbbo",
        venue="NYSE",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="tbbo",
        venue="NASDAQ",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="options_chain",
        venue="CME",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        ttm_cutoff_days=365,
        sources=("market_tick_data_service/market_interface/adapters/tradfi/databento_opra_converter.py",),
    ),
    # Yahoo Finance ETF daily OHLCV — backfilled by launch-tradfi-etf-backfill-vm.sh
    # (deployment-service commit 890ce29, 2026-04-30). 30-symbol institutional
    # universe: SPY/IVV/VOO, QQQ, IWM, DIA, GLD/SLV, USO, TLT/IEF/SHY, HYG/LQD,
    # EEM/EFA, 10 sector SPDRs, IBIT/FBTC/ARKB, ETHA/FETH.
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1d",
        venue="YAHOO_FINANCE",
        instrument_type="etf",
        live_capable=False,
        batch_capable=True,
        notes="Daily OHLCV via free-tier yfinance — sweet spot for institutional ETF coverage",
        sources=("market_tick_data_service/market_interface/adapters/tradfi/yahoo_finance_adapter.py",),
    ),
    # =====================================================================
    # Prediction
    # =====================================================================
    # Wire-format SSOT verified 2026-04-30 against
    # gs://market-data-tick-prediction-central-element-323112/_index/availability_index.parquet:
    # POLYMARKET writes data_type=trades (with instrument_type=prediction_market)
    # AND data_type=prediction_trades (with per-underlying instrument_type
    # tokens BTC/ETH/XRP/SOL/SPX/DJIA/NDX/SILVER/GOLD/CRUDE_OIL/...).
    # KALSHI excluded — no US account on the test environment yet.
    # POLYMARKET book_snapshot / market_metadata excluded — adapters do
    # not yet write those data_types to the manifest.
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="trades",
        venue="POLYMARKET",
        instrument_type="prediction_market",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/prediction/polymarket_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="BTC",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Per-underlying prediction trades — one capability per underlying token",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="ETH",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="SOL",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="XRP",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="SPX",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="DJIA",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="NDX",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="GOLD",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="SILVER",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="CRUDE_OIL",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="OTHER",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Long-tail / uncategorised prediction-trades bucket",
    ),
    # =====================================================================
    # Sports
    # =====================================================================
    # Wire-format SSOT verified 2026-04-30. The sports manifest has 2M+
    # rows in instruments-store-sports — most rows have empty venue
    # (sports captures source-by-day, not by-venue). Only ODDS_API odds
    # rows (17282) and API_FOOTBALL FIXTURE_STATS rows (5858) carry an
    # explicit venue token. Most-prolific empty-venue data_types:
    # STANDINGS / FIXTURES / INJURIES / FIXTURE_STATS / FIXTURE_EVENTS /
    # FIXTURE_LINEUPS / PLAYER_STATS / WEATHER / PREDICTIONS / ODDS /
    # MATCHES / XG / TRANSFERMARKT_LEAGUES.
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURES",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="Empty venue — sports captures by source-name, not venue",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="ODDS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes=(
            "Bulk ODDS captures (105K+ rows in prod) write to the manifest "
            "with empty venue — the source axis (footystats_odds, "
            "mdps_odds_horizon_bucket) is recorded inside the parquet path, "
            "not as the manifest venue token. SSOT: "
            "unified_api_contracts.sports.SOURCE_COVERAGE_START."
        ),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="ODDS",
        venue="ODDS_API",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        retention_days=730,
        notes=(
            "Explicit ODDS_API venue tag (~17K rows in prod). The bulk of "
            "ODDS data is at empty venue — see the empty-venue capability "
            "above."
        ),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_EVENTS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_STATS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_LINEUPS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="STANDINGS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="INJURIES",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="PLAYER_STATS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="WEATHER",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="PREDICTIONS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="MATCHES",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="XG",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def find_capability(
    asset_group: AssetGroup | str,
    data_type: str,
    venue: str,
    instrument_type: str | None = None,
) -> DataTypeCapability | None:
    """Return the matching capability or ``None``.

    ``instrument_type=None`` matches the first row with the same
    (asset_group, data_type, venue) regardless of instrument_type — useful
    when the caller doesn't have an instrument_type axis (e.g. the venue
    has only one).
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    for cap in DATA_TYPE_CAPABILITY_REGISTRY:
        if cap.asset_group != ag:
            continue
        if cap.data_type != data_type:
            continue
        if cap.venue != venue:
            continue
        if instrument_type is not None and cap.instrument_type != instrument_type:
            continue
        return cap
    return None


def capabilities_for_asset_group(
    asset_group: AssetGroup | str,
) -> tuple[DataTypeCapability, ...]:
    """Return all capability rows for an asset group."""
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    return tuple(c for c in DATA_TYPE_CAPABILITY_REGISTRY if c.asset_group == ag)


__all__ = [
    "DATA_TYPE_CAPABILITY_REGISTRY",
    "DataTypeCapability",
    "capabilities_for_asset_group",
    "find_capability",
]
