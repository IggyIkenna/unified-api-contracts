"""Centralized venue and data type configuration — SSOT for venue identity.

Previously duplicated across config-interface and market-interface; consolidated
into unified-api-contracts (T0) because venue identity is a contracts-level
concept, not a config concept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from unified_api_contracts.registry.defi_venues import (
    ALL_DEFI_VENUES,
    LEGACY_DEFI_VENUE_ALIASES,
)
from unified_api_contracts.registry.venue_trading_calendar import (
    US_MARKET_HOLIDAYS,
    WEEKDAY_ONLY_PREDICTION_SHARDS,
)


@dataclass
class VenueMapping:
    """CANONICAL venue to exchange API mappings (centralized business logic)"""

    # ALL possible Tardis exchange endpoints (we'll call each to get complete data)
    # Aligned with DATA_SOURCE_TO_VENUES["tardis"] in canonical_mappings.py (19 canonical venues)
    all_tardis_exchanges: list[str] = field(
        default_factory=lambda: [
            # Tier 1: Primary exchanges (highest liquidity)
            "binance",
            "binance-futures",  # BINANCE USDT-margined (perps + dated quarterly)
            "deribit",  # DERIBIT unified (perps + futures + options)
            "bybit",
            "bybit-spot",  # BYBIT unified
            "okex",
            "okex-futures",
            "okex-swap",  # OKX needs all endpoints for complete data
            "coinbase",  # Coinbase - spot only, for coinbase premium
            "coinbase-international",  # Coinbase Derivatives (perps) — pairs with COINBASE-SPOT perp-gate
            # Tier 2: Regional / specialist exchanges
            "upbit",  # Upbit (Korean exchange) - spot only, for kimchi premium
            # Tier 3: Additional CeFi exchanges
            # 2026-05-01 Tier-3: cryptofacilities = Kraken Futures (legacy id).
            "bitfinex",
            "bitfinex-derivatives",
            "bitget",
            "bitget-futures",
            "kraken",
            "cryptofacilities",
            # 2026-05-12: Lighter (zkSync L2) — Tardis coverage from 2026-04-17.
            # Pre-2026-04-17 falls through to REST /candles in MTDS adapter.
            # Tardis exchange slug is "lighter" (confirmed via /v1/exchanges/lighter);
            # "lighter-zksync" is NOT a valid Tardis slug.
            "lighter",
            # 2026-06-24: Binance COIN-M (inverse/delivery) perps + futures.
            # Distinct Tardis endpoint from ``binance-futures`` (USDT-M linear).
            "binance-delivery",
        ]
    )

    # Canonical TradFi venues (user-friendly names, not data source names)
    # Note: Not all are Databento-sourced (FX + KRX use Yahoo Finance; CBOE is
    # Databento XCBF.PITCH for VX/VIX futures).
    all_databento_venues: list[str] = field(
        default_factory=lambda: [
            "CME",  # Chicago Mercantile Exchange (futures, options, treasuries)
            "CBOE",  # CBOE Futures Exchange (CFE) — VX/VIX FUTURES via Databento XCBF.PITCH
            "NASDAQ",  # NASDAQ Stock Market (equities, ETFs)
            "NYSE",  # New York Stock Exchange (equities, ETFs)
            "ICE",  # Intercontinental Exchange (futures, options)
            "FX",  # OTC Foreign Exchange (KRW/USD via Yahoo Finance data provider)
            "KRX",  # Korea Exchange (single stocks via Yahoo Finance .KS tickers)
        ]
    )

    # DeFi venues — canonical PROTOCOL-CHAIN format (matches URDI
    # CANONICAL_VENUE_TO_ADAPTER). Data moved to ``defi_venues.py`` to keep
    # this file under the 900-line QG cap — see ALL_DEFI_VENUES +
    # LEGACY_DEFI_VENUE_ALIASES there. Note: HYPERLIQUID and ASTER live in
    # all_cefi_onchain_clob_venues.
    all_defi_venues: list[str] = field(default_factory=lambda: list(ALL_DEFI_VENUES))

    # Legacy → canonical DeFi venue name mapping. Data moved to
    # ``defi_venues.LEGACY_DEFI_VENUE_ALIASES``. SSOT:
    # codex/02-data/mtds-data-source-coverage-matrix.md §4.
    legacy_defi_venue_aliases: dict[str, str] = field(default_factory=lambda: dict(LEGACY_DEFI_VENUE_ALIASES))

    # On-chain CLOB venues (treated as CEFI for buckets — CLOB-style data
    # like a centralized exchange). Add new DEX perps to BOTH this list AND
    # VENUES_BY_ASSET_GROUP['cefi'] in market_data_categories.py.
    all_cefi_onchain_clob_venues: list[str] = field(
        default_factory=lambda: [
            "HYPERLIQUID",
            "ASTER",
            "PACIFICA-SOLANA",
            "EXTENDED-STARKNET",
            "LIGHTER-ZKSYNC",
            # DRIFT removed 2026-05-14: operator revised 2026-05-13 — GMX/DRIFT are
            # DeFi-only (on-chain settlement). DRIFT-SOLANA lives in MTDS_DEFI_VENUES.
            "COINBASE-CDE",  # 2026-07-10, zero Tardis coverage, native REST source
        ]
    )

    # All exchanges (computed from above - no duplication)
    @property
    def all_exchanges(self) -> list[str]:
        """All exchanges (Tardis + Databento + CEFI CLOB + DeFi)"""
        return (
            self.all_tardis_exchanges
            + self.all_databento_venues
            + self.all_cefi_onchain_clob_venues
            + self.all_defi_venues
        )

    @property
    def all_cefi_venues(self) -> list[str]:
        """All CEFI venues (Tardis + on-chain CLOBs), deduped — HYPERLIQUID
        is in both sets and would otherwise inflate the data-status expected
        denominator (incident 2026-04-20).
        """
        merged = set(self.tardis_to_venue.values()) | set(self.all_cefi_onchain_clob_venues)
        return sorted(merged)

    # Map canonical venues to Databento dataset identifiers.
    # ICE is NOT listed here (2026-06-27): ICE Databento datasets (IFUS.IMPACT /
    # IFEU.IMPACT) are outside our 3-dataset subscription and raise
    # DatabentoDatasetNotAllowedError. The only retained ICE instrument (DXY) is
    # Yahoo-sourced (see venue_to_data_provider["ICE"] and YAHOO_INDICES). Any legacy
    # ICE Databento mapping must NOT be re-added without an explicit ICE subscription.
    venue_to_databento: dict[str, str] = field(
        default_factory=lambda: {
            "CME": "GLBX.MDP3",  # CME Globex Market Data Platform 3.0
            "CBOE": "XCBF.PITCH",  # CBOE Futures Exchange (CFE) — VX/VIX FUTURES via Databento
            "NASDAQ": "DBEQ.BASIC",  # NASDAQ equities via Databento DBEQ.BASIC
            "NYSE": "DBEQ.BASIC",  # NYSE equities via Databento DBEQ.BASIC
        }
    )

    # Canonical venues to CCXT exchange IDs
    venue_to_ccxt: dict[str, str] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": "binance",
            "BINANCE-FUTURES": "binance",  # Same CCXT class, different market types
            "DERIBIT": "deribit",
            "BYBIT": "bybit",  # Unified
            "OKX": "okx",  # Unified
            "HYPERLIQUID": "hyperliquid",
            "UPBIT": "upbit",
            # RE-KEYED from bare "COINBASE" 2026-07-10 (coinbase_bare_name_migration
            # S3) — no "COINBASE-SPOT" entry pre-existed in this dict (unlike
            # tardis_to_venue, a different direction), so this is a rename.
            "COINBASE-SPOT": "coinbase",
            # Note: ASTER not in CCXT yet
        }
    )

    # Reverse mapping: Tardis exchange endpoint → canonical venue name
    # Each Tardis exchange MUST map to a DISTINCT canonical venue so instruments
    # are distinguishable after date filtering (no venue-collapse).
    tardis_to_venue: dict[str, str] = field(
        default_factory=lambda: {
            # Tier 1
            "binance": "BINANCE-SPOT",
            "binance-futures": "BINANCE-FUTURES",
            "deribit": "DERIBIT",
            "bybit": "BYBIT",
            # Bybit spot is a DISTINCT canonical venue (BYBIT-SPOT) so it
            # enumerates separately from the BYBIT perp/future endpoint and the
            # perp-gate pairs the two on the shared ``BYBIT`` entity prefix.
            "bybit-spot": "BYBIT-SPOT",
            "okex": "OKX-SPOT",
            "okex-swap": "OKX-SWAP",
            "okex-futures": "OKX-FUTURES",
            "coinbase": "COINBASE-SPOT",
            # Coinbase Derivatives (perps) — distinct canonical venue; entity
            # prefix COINBASE pairs it with COINBASE-SPOT for the perp-gate.
            "coinbase-international": "COINBASE-FUTURES",
            # Tier 2
            "upbit": "UPBIT",
            "hyperliquid": "HYPERLIQUID",
            # Tier 3 — 2026-05-01 extension
            "bitfinex": "BITFINEX-SPOT",
            "bitfinex-derivatives": "BITFINEX-FUTURES",
            "bitget": "BITGET-SPOT",
            "bitget-futures": "BITGET-FUTURES",
            "kraken": "KRAKEN-SPOT",
            "cryptofacilities": "KRAKEN-FUTURES",
            # 2026-05-12 — Lighter (Tardis coverage from 2026-04-17).
            # MTDS routes pre-2026-04-17 dates to REST /candles; post to Tardis.
            # Tardis exchange slug is "lighter" (NOT "lighter-zksync").
            "lighter": "LIGHTER-ZKSYNC",
            # 2026-06-24: Binance COIN-M (inverse/delivery) perps + futures.
            # Distinct canonical venue from BINANCE-FUTURES (USDT-M linear).
            "binance-delivery": "BINANCE-DELIVERY",
        }
    )

    # Map venues to their data providers (for non-Tardis venues)
    venue_to_data_provider: dict[str, str] = field(
        default_factory=lambda: {
            # TradFi venues with external data providers (not Databento).
            # CBOE is NOT here: its VX/VIX FUTURES are Databento (XCBF.PITCH) — see
            # venue_to_databento. (Barchart was retired 2026-06-24; VIX 15m is now
            # aggregated from VX futures via databento, not a Barchart CSV preload.)
            "FX": "yahoo_finance",  # KRW/USD via Yahoo Finance
            "ICE": "yahoo_finance",  # ICE/NYBOT DXY index only — Yahoo Finance (DX-Y.NYB);
            # the ICE Databento datasets (IFUS/IFEU) are OUT of our subscription
            # (removed from venue_to_databento 2026-06-27). This entry ensures the parity
            # gate (test_tradfi_venue_resolves_to_a_data_source) sees a valid source for
            # ICE (DXY via Yahoo), not a "routes nowhere" gap.
            "KRX": "yahoo_finance",  # Korea Exchange: KOSPI/KOSPI200 indices + single stocks via Yahoo
            # DeFi venues with direct API integration
            "HYPERLIQUID": "hyperliquid_api",
            "ASTER": "aster_api",
            "PACIFICA-SOLANA": "pacifica_api",
            "EXTENDED-STARKNET": "extended_api",
            "LIGHTER-ZKSYNC": "lighter_api",  # pre-2026-04-17; post routes to Tardis
            "DRIFT": "drift_api",  # S3 archive (2022-2025) + Data API (2025-present)
            "COINBASE-CDE": "coinbase_advanced_trade_api",
            # DeFi venues — canonical PROTOCOL-CHAIN format
            "UNISWAP_V2-ETHEREUM": "the_graph",
            "UNISWAP_V3-ETHEREUM": "the_graph",
            "UNISWAP_V4-ETHEREUM": "the_graph",
            "CURVE-ETHEREUM": "rpc",
            "BALANCER-ETHEREUM": "balancer_api_v3",
            "AAVE_V3-ETHEREUM": "the_graph",
            "MORPHO-ETHEREUM": "the_graph",
            "FLUID-ETHEREUM": "the_graph",
            "LIDO-ETHEREUM": "protocol_sdk",
            "ETHERFI-ETHEREUM": "protocol_sdk",
            "ETHENA-ETHEREUM": "protocol_sdk",
        }
    )

    # Venue launch/start dates (centralized - single source of truth)
    # These are the earliest dates when data is available for each venue
    # Adapters should use these instead of hardcoding dates
    venue_start_dates: dict[str, str] = field(
        default_factory=lambda: {
            # CEFI - Tardis exchanges (Tier 1)
            # Start dates = earliest manifest data, NOT exchange founding dates
            "BINANCE-SPOT": "2020-01-01",
            "BINANCE-FUTURES": "2019-11-17",
            # Binance COIN-M (inverse/delivery) — Tardis ``binance-delivery``
            # availableSince 2020-01-01 (Binance COIN-M launched 2019-09-13;
            # Tardis archive starts 2020-01-01 for this endpoint).
            "BINANCE-DELIVERY": "2020-01-01",
            "DERIBIT": "2019-03-30",
            "BYBIT": "2020-01-01",
            # Bybit spot — Tardis ``bybit-spot`` availableSince 2021-12-04.
            "BYBIT-SPOT": "2021-12-04",
            # Coinbase Derivatives (perps) — Tardis ``coinbase-international``
            # availableSince 2024-10-31.
            "COINBASE-FUTURES": "2024-10-31",
            "COINBASE-CDE": "2026-07-10",  # brand-new venue, no historical archive
            "OKX-SPOT": "2020-01-01",
            "OKX-FUTURES": "2020-01-01",
            "OKX-SWAP": "2020-01-01",
            "UPBIT": "2021-03-03",
            "COINBASE-SPOT": "2020-01-01",
            # CEFI Tardis Tier-3 (2026-05-01) — verified vs Tardis availableSince.
            "BITFINEX-SPOT": "2020-01-01",
            # Tardis bitfinex-derivatives available from 2019-12-01; symbols
            # reliable from 2020-05-27 (pre-filter emits EXPECTED_PRE_SOURCE_COVERAGE_START).
            "BITFINEX-FUTURES": "2019-12-01",
            "BITGET-SPOT": "2024-11-08",
            "BITGET-FUTURES": "2024-11-08",
            "KRAKEN-SPOT": "2020-01-01",
            # Kraken Futures: earliest CAPTURED manifest data = 2020-01-01
            # (operator-confirmed 2026-06-17 "per the manifest"; the
            # cryptofacilities Tardis archive reaches 2019-03-30 but our
            # captured market-data-tick rows begin 2020-01-01, so the
            # IS-catalogue enumeration floor is 2020-01-01).
            "KRAKEN-FUTURES": "2020-01-01",
            # CEFI on-chain CLOBs. HYPERLIQUID earliest = book_snapshot_5 S3
            # archive 2023-04-15; see VENUE_DATA_TYPE_CAPABILITIES for per-
            # data-type starts (trades only from 2025-03-22, no liquidations).
            "HYPERLIQUID": "2023-04-15",
            # Astherus pre-rebrand genesis (operator-confirmed 2026-06-17);
            # pre-2024 funding is Binance-proxied (imported, not Aster-native).
            "ASTER": "2023-07-22",
            "PACIFICA-SOLANA": "2025-06-01",
            "EXTENDED-STARKNET": "2024-10-01",
            "LIGHTER-ZKSYNC": "2024-08-01",
            # Prediction-platform PERPETUAL FUTURES — crypto perps treated as cefi.
            # Start dates = venue launch dates (no pre-launch data exists).
            # SSOT: plans/active/prediction_venue_perps_and_live_clob_depth_2026_06_20.md
            "KALSHI-PERP": "2026-05-29",  # Kalshi CFTC crypto perp launch
            "POLYMARKET-PERP": "2026-04-21",  # Polymarket perp beta launch
            # TradFi - Databento
            # Start dates = earliest manifest data
            "CME": "2020-01-01",
            "CBOE": "2020-06-01",  # VX futures (XCBF.PITCH) captured history floor
            "NASDAQ": "2023-04-15",
            "NYSE": "2023-04-15",
            "ICE": "2020-01-01",
            "FX": "2020-01-01",
            # KRX (Korea Exchange) single stocks — Yahoo-sourced (.KS). Daily
            # history confirmed back to 2019 (probed 2026-06-24). Floor = our
            # Yahoo daily backfill floor.
            "KRX": "2019-01-02",
            # DeFi - DEX protocols (canonical PROTOCOL-CHAIN format)
            # Start dates = earliest manifest data
            "UNISWAP_V2-ETHEREUM": "2020-05-06",  # Uniswap V2 factory deployed May 2020
            "UNISWAP_V3-ETHEREUM": "2021-05-05",  # Uniswap V3 mainnet launch
            "UNISWAP_V3-ARBITRUM": "2021-06-18",
            "UNISWAP_V3-POLYGON": "2021-12-22",  # Uniswap V3 Polygon deployment
            "UNISWAP_V3-OPTIMISM": "2021-11-12",
            "UNISWAP_V3-BASE": "2023-09-03",  # Earliest subgraph data (Base launched 2023-08-09)
            "UNISWAP_V4-ETHEREUM": "2025-01-30",  # Uniswap V4 mainnet deployment
            "CURVE-ETHEREUM": "2020-01-20",  # Curve genesis pool
            "CURVE-AVALANCHE": "2021-11-10",  # Curve Avalanche deployment
            "CURVE-OPTIMISM": "2022-01-13",  # Curve Optimism deployment
            "BALANCER-ETHEREUM": "2021-04-22",  # Earliest subgraph data (V1 launched 2020-02-28)
            "BALANCER-POLYGON": "2021-06-24",
            "BALANCER-ARBITRUM": "2021-08-27",
            "BALANCER-OPTIMISM": "2022-05-20",
            "BALANCER-AVALANCHE": "2023-08-17",
            "BALANCER-BASE": "2023-07-29",
            "PANCAKESWAP_V3-BSC": "2023-04-03",  # PancakeSwap V3 BSC launch
            "PANCAKESWAP_V3-ETHEREUM": "2023-04-03",  # PancakeSwap V3 ETH launch
            "PANCAKESWAP_V3-BASE": "2023-09-01",
            "CAMELOT_V3-ARBITRUM": "2023-06-14",  # Earliest pool createdAtTimestamp
            "SUSHISWAP_V3-ETHEREUM": "2023-04-01",  # SushiSwap V3 ETH launch
            "SUSHISWAP_V3-AVALANCHE": "2023-04-01",
            "GMX-ARBITRUM": "2021-09-06",  # GMX Arbitrum launch
            "GMX-AVALANCHE": "2022-01-05",  # GMX Avalanche launch
            "AERODROME_V3-BASE": "2024-05-01",  # Earliest pool createdAtTimestamp from subgraph
            "VELODROME_V2-OPTIMISM": "2023-06-15",  # Velodrome V2 Optimism launch
            "TRADERJOE-AVALANCHE": "2021-07-04",  # TraderJoe Avalanche launch
            # DeFi - Lending protocols
            "AAVE_V3-ETHEREUM": "2023-01-27",
            "AAVE_V3-POLYGON": "2022-03-12",
            "AAVE_V3-AVALANCHE": "2022-03-12",
            "AAVE_V3-ARBITRUM": "2022-03-12",
            "AAVE_V3-OPTIMISM": "2022-03-12",
            "AAVE_V3-BASE": "2023-08-23",
            "AAVE_V3-BSC": "2024-01-24",
            "AAVE_V3-LINEA": "2025-02-12",
            "COMPOUND_V3-ETHEREUM": "2022-08-14",
            "COMPOUND_V3-ARBITRUM": "2023-05-05",
            "COMPOUND_V3-BASE": "2023-08-20",
            "COMPOUND_V3-OPTIMISM": "2024-04-07",
            "MORPHO-ETHEREUM": "2024-01-08",
            "MORPHO-BASE": "2024-06-01",
            "FLUID-ETHEREUM": "2024-02-27",
            # DeFi - LST/Yield protocols
            "LIDO-ETHEREUM": "2020-12-18",
            "ETHERFI-ETHEREUM": "2023-11-01",
            "ETHENA-ETHEREUM": "2024-02-19",
            "EIGENLAYER-ETHEREUM": "2024-09-17",  # EIGEN token listing date (earliest instrument)
            "SUSHISWAP-ARBITRUM": "2023-03-30",  # Earliest pool createdAtTimestamp from subgraph
            # DeFi - Solana protocols
            # DRIFT canonical venue string (market_data_categories.py uses "DRIFT" not "DRIFT-SOLANA").
            # S3 archive data: 2022-01-01. DRIFT-SOLANA kept as an alias start date.
            "DRIFT": "2022-01-01",
            "DRIFT-SOLANA": "2022-11-04",
            "ORCA-SOLANA": "2023-12-29",
            "RAYDIUM-SOLANA": "2021-02-21",  # Raydium AMM V4 mainnet launch
            "KAMINO-SOLANA": "2023-01-21",
            "JITO-SOLANA": "2021-11-01",
            "MARINADE-SOLANA": "2021-08-01",
            # Prediction — Polymarket
            # POLYMARKET base venue start = first date with actual instruments
            "POLYMARKET": "2025-03-14",
            # Per-market start dates — verified from GCS instrument parquets.
            # Each market's denominator starts from its actual first appearance.
            "POLYMARKET:BTC": "2025-03-13",
            "POLYMARKET:ETH": "2025-03-14",
            "POLYMARKET:SOL": "2025-03-14",
            "POLYMARKET:XRP": "2025-03-31",
            "POLYMARKET:DOGE": "2026-03-01",  # Intermittent before Mar 2026
            "POLYMARKET:HYPE": "2026-03-01",  # Intermittent before Mar 2026
            "POLYMARKET:BNB": "2026-03-01",  # Intermittent before Mar 2026
            "POLYMARKET:FOOTBALL": "2025-10-18",
            "POLYMARKET:OTHER": "2025-03-13",
            "POLYMARKET:SPX": "2025-10-15",
            "POLYMARKET:DJIA": "2025-10-15",
            "POLYMARKET:NDX": "2025-10-15",
            "POLYMARKET:CRUDE_OIL": "2025-12-08",  # Gap Oct 27-Dec 7 (Polymarket didn't list daily)
            "POLYMARKET:GOLD": "2025-12-09",
            "POLYMARKET:SILVER": "2025-12-09",
        }
    )

    # Source/provider data start dates (distinct from venue launch dates)
    # These are data aggregators or providers, not trading venues.
    # The date is the earliest date with actual data available from the source.
    source_data_start_dates: dict[str, str] = field(
        default_factory=lambda: {
            # Sports — Odds API historical data starts 2020-06-06
            # API returns 401 Unauthorized for dates before this
            "ODDS_API": "2020-06-06",
        }
    )

    # MVP token list for DeFi pool discovery (configurable)
    defi_mvp_base_currencies: list[str] = field(
        default_factory=lambda: [
            "ETH",  # Native Ethereum
            "WETH",  # Wrapped ETH
            "BTC",  # Bitcoin (WBTC on Ethereum)
            "WBTC",  # Wrapped Bitcoin (explicitly include WBTC)
            "USDT",  # Tether
            "USDC",  # USD Coin
            "DAI",  # Dai stablecoin
            "weETH",  # EtherFi LST (Wrapped eETH) - non-rebasing
            "WSTETH",  # Lido LST (non-rebasing, wrapped version)
            # STETH removed - rebasing token, not supported by AAVE
        ]
    )

    # MVP base assets for Hyperliquid and Aster perpetuals
    # These are the 21 trading assets used for CeFi/TradFi MVP
    hyperliquid_aster_mvp_base_assets: list[str] = field(
        default_factory=lambda: [
            "SOL",  # Solana
            "BTC",  # Bitcoin
            "ETH",  # Ethereum
            "AVAX",  # Avalanche
            "ADA",  # Cardano
            "SUSHI",  # SushiSwap
            "CAKE",  # PancakeSwap
            "XRP",  # Ripple
            "DOGE",  # Dogecoin
            "XLM",  # Stellar
            "LTC",  # Litecoin
            "ALGO",  # Algorand
            "FIL",  # Filecoin
            "TRX",  # Tron
            "BNB",  # Binance Coin
            "LINK",  # Chainlink
            "MATIC",  # Polygon
            "APT",  # Aptos
            "VET",  # VeChain
            "ATOM",  # Cosmos
            "NEAR",  # Near Protocol
        ]
    )

    @property
    def all_tradfi_venues(self) -> list[str]:
        """Complete TradFi venue universe — ALL tradfi venues regardless of data source.

        Derived from the authoritative ``all_databento_venues`` field (which, despite its
        name, already contains the full tradfi universe including non-Databento venues):
          - CME, NASDAQ, NYSE → Databento
          - CBOE → Databento XCBF.PITCH (VX/VIX FUTURES; VIX 15m aggregates from VX)
          - FX   → Yahoo Finance (KRW/USD; see ``venue_to_data_provider``)
          - KRX  → Yahoo Finance (Korea single stocks, .KS tickers)
          - ICE  → Yahoo Finance — DXY index only (DX-Y.NYB). The ICE Databento
            datasets (IFUS/IFEU = Brent/Gasoil commodity futures) are OUT of our
            subscription (removed from ``venue_to_databento`` 2026-06-27); those
            commodity futures remain a genuine Databento subscription ask — only the
            DXY/index series is sourced today, and it is Yahoo, not Databento.

        Use this accessor (not ``all_databento_venues``) for any denominator that must
        count ALL expected tradfi coverage cells — e.g. the deployment-api
        MTDS_CATEGORY_META["TRADFI"]["venue_accessor"]. Using ``all_databento_venues``
        directly on that path caused FLAG-4: CBOE/FX cells excluded from the expected
        denominator → inflated coverage % + CBOE/FX never showed as expected in drilldown.
        """
        return list(self.all_databento_venues)

    def is_databento_venue(self, venue: str) -> bool:
        """Check if venue uses Databento (canonical venue name)."""
        return venue in self.all_databento_venues

    def is_tardis_exchange(self, exchange: str) -> bool:
        """Check if exchange uses Tardis (API endpoint name)."""
        return exchange in self.all_tardis_exchanges

    def is_defi_venue(self, venue: str) -> bool:
        """Check if venue is a DeFi protocol (swaps, lending, staking).

        Accepts both canonical (``AAVE_V3-ETHEREUM``) and legacy
        (``AAVE_V3``) forms.
        """
        if venue in self.all_defi_venues:
            return True
        return self.legacy_defi_venue_aliases.get(venue) in self.all_defi_venues

    def normalize_defi_venue(self, raw_venue: str, chain: str | None = None) -> str:
        """Normalise a DeFi venue identifier to the canonical PROTOCOL-CHAIN form.

        Manifests pre-dating the canonical-naming migration carry legacy forms
        such as ``AAVE_V3`` / ``UNISWAP_V2`` / ``CURVE`` / ``ETHENA``. This
        helper resolves either form to the canonical ``AAVE_V3-ETHEREUM`` /
        ``UNISWAP_V2-ETHEREUM`` / etc. so data-status aggregators, feature
        services, and ML pipelines can look up by a single key.

        Args:
            raw_venue: Venue identifier as stored in the manifest (canonical
                or legacy).
            chain: Optional chain name (``ETHEREUM`` etc.). Only consulted
                when the legacy form is ambiguous across chains. Currently
                all registered DeFi protocols are Ethereum-only so chain is
                advisory — reserved for Arbitrum/Base/Optimism/etc. expansion.

        Returns:
            Canonical ``PROTOCOL-CHAIN`` form. Falls back to ``raw_venue``
            unchanged if the legacy form is unrecognised (so unknown venues
            are surfaced honestly as missing from the UAC registry instead
            of silently remapped).

        SSOT: codex/02-data/mtds-data-source-coverage-matrix.md §4.
        """
        # Canonicalise the protocol-version spelling FIRST (underscore is the
        # documented canonical form — ``AAVEV3`` → ``AAVE_V3``, ``YEARNV3`` →
        # ``YEARN_V3``). The no-underscore "ghost" spellings carry historical
        # GCS paths but must collapse to the underscore identity before the
        # membership/alias resolution below; otherwise a ghost that happens to
        # be in ``all_defi_venues`` (e.g. ``AAVEV3-ARBITRUM``) short-circuits
        # as-is and never reaches the underscore-only
        # ``VENUE_DATA_TYPE_CAPABILITIES`` → its shards are silently uncredited.
        raw_venue = self._canonicalise_defi_protocol_spelling(raw_venue)
        if raw_venue in self.all_defi_venues:
            return raw_venue
        alias = self.legacy_defi_venue_aliases.get(raw_venue)
        if alias is None:
            return raw_venue
        # Chain override for multi-chain expansion — swap -ETHEREUM suffix.
        if chain and chain != "ETHEREUM" and alias.endswith("-ETHEREUM"):
            alias = alias[: -len("ETHEREUM")] + chain
        return alias

    @staticmethod
    def _canonicalise_defi_protocol_spelling(venue: str) -> str:
        """Insert the canonical underscore before a protocol version token
        (``AAVEV3`` → ``AAVE_V3``, ``UNISWAPV3`` → ``UNISWAP_V3``,
        ``YEARNV3`` → ``YEARN_V3``), preserving a ``-CHAIN`` suffix.

        Underscore-before-version is the documented DeFi naming convention
        (``defi_venues.py`` header); the no-underscore forms are legacy ghosts.
        Idempotent on already-canonical names (``AAVE_V3`` has no ``letter+V+digit``
        run to rewrite) and a no-op on non-DeFi / version-less venues."""
        version_re = r"([A-Za-z])V(\d)"
        if "-" in venue:
            protocol, chain = venue.rsplit("-", 1)
            return f"{re.sub(version_re, r'\1_V\2', protocol)}-{chain}"
        return re.sub(version_re, r"\1_V\2", venue)

    def is_cefi_onchain_clob_venue(self, venue: str) -> bool:
        """Check if venue is an on-chain CLOB (treated as CEFI for data classification)."""
        return venue in self.all_cefi_onchain_clob_venues

    def is_cefi_venue(self, venue: str) -> bool:
        """Check if venue should be treated as CEFI (includes Tardis + on-chain CLOBs)."""
        # Check if it's a Tardis exchange (via canonical venue mapping)
        canonical_venues = set(self.tardis_to_venue.values())
        if venue in canonical_venues:
            return True
        # Check if it's an on-chain CLOB venue
        return venue in self.all_cefi_onchain_clob_venues

    def get_venue_start_date(self, venue: str) -> str | None:
        """
        Get the start date for a venue or data source.

        Checks venue_start_dates first, then source_data_start_dates as fallback.

        Args:
            venue: Canonical venue name or source name (e.g., "BINANCE-SPOT", "ODDS_API")

        Returns:
            ISO date string (YYYY-MM-DD) or None if not found
        """
        return self.venue_start_dates.get(venue) or self.source_data_start_dates.get(venue)

    # Sparse override: venues whose instrument-discovery API has NARROWER
    # historical coverage than the market-data archive earliest date in
    # ``venue_start_dates``. Most venues do NOT need an entry — their
    # discovery API can return instrument-list snapshots from
    # ``venue_start_dates[venue]`` onwards. Add a venue here only when
    # instruments-service can prove (by live probe) that the discovery
    # endpoint returns empty / errors for dates before some later cutoff.
    #
    # Reference incident 2026-05-05: HYPERLIQUID. Market-data S3 archive
    # starts 2023-04-15; instrument-discovery API returns nothing for dates
    # before 2023-11-01 (no historical instrument-listing snapshots exposed
    # for the April-October 2023 window). Without this override, the
    # instruments-service orchestrator marked 200 (venue, date) shards as
    # ``attempted_failed`` because the venue was "expected to be available"
    # per market-data start but the discovery call legitimately had no data.
    venue_instrument_discovery_overrides: dict[str, str] = field(
        default_factory=lambda: {
            "HYPERLIQUID": "2023-11-01",
        }
    )

    def get_instrument_discovery_start(self, venue: str) -> str | None:
        """Return earliest date instruments-service can produce honest discovery snapshots.

        SSOT for the instruments-service expected-window lower bound. For most
        venues this equals ``get_venue_start_date(venue)`` — the market-data
        archive earliest date. Override here (via
        ``venue_instrument_discovery_overrides``) when the discovery API has
        narrower historical coverage than the market-data archive — e.g.
        HYPERLIQUID where the API returns nothing for instrument-listing
        snapshots before 2023-11-01 even though market-data S3 archive starts
        2023-04-15.

        instruments-service orchestrator MUST consult this (not
        ``venue_start_dates`` directly) when deciding whether a (venue, date)
        shard is expected to produce instrument records — otherwise the gap
        between market-data start and discovery start renders as
        ``attempted_failed`` phantoms (200 dates for HYPERLIQUID pre-fix).

        Args:
            venue: Canonical venue name (e.g., "HYPERLIQUID", "BINANCE-SPOT").

        Returns:
            ISO date string (YYYY-MM-DD) or None if the venue is unknown.
        """
        override = self.venue_instrument_discovery_overrides.get(venue)
        if override is not None:
            return override
        return self.get_venue_start_date(venue)

    # Prediction-market shards tied to traditional financial instruments —
    # SSOT data lives in ``venue_trading_calendar.WEEKDAY_ONLY_PREDICTION_SHARDS``.
    _WEEKDAY_ONLY_PREDICTION_SHARDS: frozenset[str] = field(default_factory=lambda: WEEKDAY_ONLY_PREDICTION_SHARDS)

    # US market holidays — TradFi venues (NYSE/NASDAQ/CBOE-Index) and
    # Polymarket UP_DOWN markets on traditional instruments don't list /
    # don't trade on these days. SSOT data lives in
    # ``venue_trading_calendar.py`` (also re-exposed via
    # :func:`is_non_trading_day` and :func:`clip_dates_to_trading_days`
    # for the orchestrator pre-skip + data-status denominator).
    _US_MARKET_HOLIDAYS: frozenset[str] = field(default_factory=lambda: US_MARKET_HOLIDAYS)

    def get_expected_trading_dates(self, venue: str, start_date: str, end_date: str) -> list[str]:
        """Return expected trading dates for a venue between start and end dates.

        TradFi venues and prediction shards tied to traditional markets
        (SPX, CRUDE_OIL, GOLD, etc.) trade weekdays only.
        Crypto venues/shards (BTC, ETH, SOL) trade 24/7 including weekends.
        """
        from unified_api_contracts.registry.market_data_categories import VENUE_TO_ASSET_GROUP

        all_dates = pd.date_range(start_date, end_date, freq="D")
        asset_group = VENUE_TO_ASSET_GROUP.get(venue, "")
        weekday_only = asset_group == "tradfi" or venue in self._WEEKDAY_ONLY_PREDICTION_SHARDS
        if weekday_only:
            all_dates = all_dates[all_dates.weekday < 5]
            # Exclude US market holidays
            date_strs: list[str] = all_dates.strftime("%Y-%m-%d").tolist()
            return [d for d in date_strs if d not in self._US_MARKET_HOLIDAYS]
        return [d.strftime("%Y-%m-%d") for d in all_dates]

    def is_venue_available_on_date(self, venue: str, target_date: datetime | date | str) -> bool:
        """
        Check if a venue was available (launched) on a given date.

        Args:
            venue: Canonical venue name
            target_date: datetime or date object to check

        Returns:
            True if venue was available on the target date, False otherwise
        """
        start_date_str = self.venue_start_dates.get(venue) or self.source_data_start_dates.get(venue)
        if not start_date_str:
            # If no start date configured, assume always available
            return True

        # Parse the start date
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        # Normalize target_date to date object
        if isinstance(target_date, datetime):
            target = target_date.date()
        elif isinstance(target_date, date):
            target = target_date
        else:
            # Try to parse string
            date_str = str(target_date)[:10]
            target = datetime.strptime(date_str, "%Y-%m-%d").date()

        return target >= start_date

    def get_venue_to_tardis_exchanges(self) -> dict[str, list[str]]:
        """
        Get reverse mapping: canonical venue -> list of Tardis exchange names.

        Note: One canonical venue can map to multiple Tardis exchanges.
        E.g., OKX -> ["okex", "okex-futures", "okex-swap"]

        Returns:
            Dict mapping canonical venue names to list of Tardis exchange names
        """
        venue_to_exchanges: dict[str, list[str]] = {}
        for tardis_exchange, canonical_venue in self.tardis_to_venue.items():
            if canonical_venue not in venue_to_exchanges:
                venue_to_exchanges[canonical_venue] = []
            venue_to_exchanges[canonical_venue].append(tardis_exchange)
        return venue_to_exchanges

    def _get_direct_tardis_match(self, canonical_venue: str) -> str | None:
        for tardis_exchange, venue in self.tardis_to_venue.items():
            if venue == canonical_venue:
                return tardis_exchange
        return None

    def _get_suffixed_tardis_match(self, canonical_venue: str) -> str | None:
        if "-" not in canonical_venue:
            return None
        base_venue, suffix = canonical_venue.rsplit("-", 1)
        suffix_to_type = {
            "SPOT": "SPOT_PAIR",
            "SWAP": "PERPETUAL",
            "FUTURES": "FUTURE",
            "OPTIONS": "OPTION",
        }
        inst_type = suffix_to_type.get(suffix, suffix)
        for venue_key in (canonical_venue, base_venue):
            tardis_name = self.venue_instrument_type_to_tardis.get((venue_key, inst_type))
            if tardis_name:
                return tardis_name
        if suffix == "FUTURES":
            futures_fallback = self.venue_instrument_type_to_tardis.get((base_venue, "PERPETUAL"))
            if futures_fallback:
                return futures_fallback
        return self._get_direct_tardis_match(base_venue)

    def get_tardis_exchange_for_venue(self, canonical_venue: str) -> str | None:
        """Get Tardis exchange name for a canonical venue.

        Handles suffixed venues (OKX-SPOT → okex, OKX-FUTURES → okex-futures,
        COINBASE-SPOT → coinbase, BINANCE-SPOT → binance).

        Uses the instrument_type_to_tardis mapping for suffixed venues,
        falls back to direct tardis_to_venue lookup for simple names.
        """
        upper = canonical_venue.upper()
        direct_match = self._get_direct_tardis_match(upper)
        if direct_match:
            return direct_match
        return self._get_suffixed_tardis_match(upper)

    def convert_to_tardis_exchange(self, exchange_or_venue: str) -> str:
        """
        Convert exchange name to Tardis API format (lowercase).

        Handles both:
        - Canonical venue names: UPBIT -> upbit, COINBASE -> coinbase
        - Already lowercase Tardis names: upbit -> upbit

        Args:
            exchange_or_venue: Exchange name (could be canonical venue or Tardis name)

        Returns:
            Lowercase Tardis exchange name
        """
        # If it's uppercase, it's likely a canonical venue name
        upper_name = exchange_or_venue.upper()
        lower_name = exchange_or_venue.lower()

        # Check if it's a canonical venue name
        tardis_name = self.get_tardis_exchange_for_venue(upper_name)
        if tardis_name:
            return tardis_name

        # Check if it's already a valid Tardis exchange name
        if lower_name in self.all_tardis_exchanges:
            return lower_name

        # Return lowercase as fallback
        return lower_name

    def get_defi_mvp_tokens(self) -> list[str]:
        """Get MVP token list from the configured defi_mvp_base_currencies field.

        To override the token list, pass a custom list at construction time:
            VenueMapping(defi_mvp_base_currencies=["ETH", "WETH", "USDC"])
        """
        return self.defi_mvp_base_currencies

    def get_databento_exchange_id(self, venue: str) -> str | None:
        """Get Databento exchange identifier for canonical venue."""
        return self.venue_to_databento.get(venue)

    # CRITICAL: Map venue+instrument_type -> Tardis exchange endpoint
    # Note: HYPERLIQUID and ASTER use direct APIs, not Tardis
    venue_instrument_type_to_tardis: dict[tuple[str, str], str] = field(
        default_factory=lambda: {
            # Binance mappings
            ("BINANCE-SPOT", "SPOT_PAIR"): "binance",
            ("BINANCE-FUTURES", "PERPETUAL"): "binance-futures",
            ("BINANCE-FUTURES", "FUTURE"): "binance-futures",
            # Binance COIN-M (inverse/delivery) — distinct endpoint from USDT-M.
            # Perps (e.g. BTCUSD_PERP) and dated futures (e.g. BTCUSD_241227)
            # both live on this endpoint (2026-06-24).
            ("BINANCE-DELIVERY", "PERPETUAL"): "binance-delivery",
            ("BINANCE-DELIVERY", "FUTURE"): "binance-delivery",
            # OKX mappings (CRITICAL: instrument_type determines endpoint)
            ("OKX", "SPOT_PAIR"): "okex",
            ("OKX", "PERPETUAL"): "okex-swap",
            ("OKX", "FUTURE"): "okex-futures",
            # Bybit mappings
            ("BYBIT", "SPOT_PAIR"): "bybit-spot",
            ("BYBIT", "PERPETUAL"): "bybit",
            ("BYBIT", "FUTURE"): "bybit",
            # Bybit spot as its own canonical venue
            ("BYBIT-SPOT", "SPOT_PAIR"): "bybit-spot",
            # Deribit (unified endpoint)
            ("DERIBIT", "SPOT_PAIR"): "deribit",
            ("DERIBIT", "PERPETUAL"): "deribit",
            ("DERIBIT", "FUTURE"): "deribit",
            ("DERIBIT", "OPTION"): "deribit",
            # Upbit (spot only - Korean exchange for kimchi premium)
            ("UPBIT", "SPOT_PAIR"): "upbit",
            # Coinbase (spot only - for coinbase premium)
            ("COINBASE-SPOT", "SPOT_PAIR"): "coinbase",
            # Coinbase Derivatives (perps) via Tardis coinbase-international
            ("COINBASE-FUTURES", "PERPETUAL"): "coinbase-international",
            ("COINBASE-FUTURES", "SPOT_PAIR"): "coinbase-international",
            # DEX perps with Tardis routing (2026-05-12)
            # Tardis exchange slug is "lighter" (NOT "lighter-zksync").
            ("LIGHTER-ZKSYNC", "PERPETUAL"): "lighter",
            ("KRAKEN-FUTURES", "PERPETUAL"): "cryptofacilities",
            ("KRAKEN-FUTURES", "FUTURE"): "cryptofacilities",
            ("BITFINEX-FUTURES", "PERPETUAL"): "bitfinex-derivatives",
            ("BITFINEX-FUTURES", "FUTURE"): "bitfinex-derivatives",
        }
    )

    # Which Tardis exchanges map to which instrument types (for filtering)
    tardis_exchange_instrument_types: dict[str, list[str]] = field(
        default_factory=lambda: {
            # Tier 1
            "binance": ["SPOT_PAIR"],
            "binance-futures": ["PERPETUAL", "FUTURE"],
            "okex": ["SPOT_PAIR"],
            "okex-swap": ["PERPETUAL"],
            "okex-futures": ["FUTURE"],
            "bybit": ["PERPETUAL", "FUTURE"],
            "bybit-spot": ["SPOT_PAIR"],
            "deribit": ["SPOT_PAIR", "PERPETUAL", "FUTURE", "OPTION"],
            "coinbase": ["SPOT_PAIR"],
            "coinbase-international": ["PERPETUAL", "SPOT_PAIR"],
            # Tier 2
            "upbit": ["SPOT_PAIR"],
            # 2026-06-24: Binance COIN-M (inverse/delivery)
            "binance-delivery": ["PERPETUAL", "FUTURE"],
        }
    )

    # Venues that require MVP base asset filtering (spot only venues for premium calculations)
    # These venues will only include instruments for the 21 MVP base assets
    spot_mvp_filtered_venues: list[str] = field(
        default_factory=lambda: [
            "UPBIT",  # Korean exchange - for kimchi premium
            "COINBASE-SPOT",  # Coinbase - for coinbase premium
        ]
    )

    def get_data_provider(self, venue: str) -> str | None:
        """Get data provider for a venue.

        Returns one of: tardis, databento, hyperliquid_api, aster_api,
        the_graph, protocol_sdk.
        """
        # Check if it's a Tardis venue
        if venue in self.tardis_to_venue.values() or any(venue == v for v in self.tardis_to_venue.values()):
            return "tardis"
        # Check if it's a Databento venue
        if venue in self.all_databento_venues:
            return "databento"
        # Check venue_to_data_provider mapping
        return self.venue_to_data_provider.get(venue)


@dataclass
class DataTypeConfig:
    """CRITICAL: Data types per instrument type (fixes 66% false positives)"""

    instrument_data_types: dict[str, list[str]] = field(
        default_factory=lambda: {
            # CeFi instrument types
            "SPOT_PAIR": ["trades", "book_snapshot_5"],
            "PERPETUAL": [
                "trades",
                "book_snapshot_5",
                "derivative_ticker",
                "liquidations",
            ],
            "FUTURE": [
                "trades",
                "book_snapshot_5",
                "derivative_ticker",
                "liquidations",
            ],
            "OPTION": ["options_chain", "trades", "book_snapshot_5", "liquidations"],
            # DeFi instrument types
            "POOL": ["dex_pool_swaps", "dex_pool_state"],  # DEX pools (Uniswap, etc.)
            "A_TOKEN": ["lending_indices", "oracle_prices"],  # Lending supply positions (AAVE, Morpho)
            "DEBT_TOKEN": [
                "lending_indices",
                "oracle_prices",
            ],  # Lending borrow positions (AAVE, Morpho)
            "LST": ["lst_rates", "oracle_prices"],  # Liquid staking tokens (Lido, EtherFi)
            "YIELD_BEARING": ["oracle_prices"],  # Yield-bearing tokens (Ethena sUSDe)
        }
    )

    default_data_types: list[str] = field(
        default_factory=lambda: [
            "trades",
            "book_snapshot_5",
            "derivative_ticker",
            "liquidations",
            "options_chain",
        ]
    )

    # Instrument type filters (exclude complex types we don't want to process)
    excluded_instrument_types: list[str] = field(
        default_factory=lambda: ["combo"]  # Exclude Deribit combo strategies
    )

    # Complex option strategy filters (Deribit specific - exclude complex strategies)
    excluded_deribit_strategies: list[str] = field(
        default_factory=lambda: [
            "PS-",
            "STRG-",
            "CBUT-",
            "CCOND-",
            "PDIAG-",
            "PBUT-",
            "ICOND-",
            "BOX-",
            "FS-",
            "RR-",
            "CSR12-",
            "PSR12-",
            "CSR13-",
            "PSR13-",
            "CCAL-",
            "CDIAG-",
        ]
    )


# ExchangeInstrumentConfig moved to venue_instrument_config.py 2026-05-06 to
# keep venue_mapping.py under the 900-line ceiling. Re-exported via
# registry/__init__.py and the top-level package for consumer-import parity.


# ---------------------------------------------------------------------------
# LST margin collateral — venues that accept liquid staking tokens as margin
# 2026-05-12 (dex_perp_and_venue_data_expansion plan, Phase 1)
# ---------------------------------------------------------------------------
# Confirmed: Bybit UTA (stETH), Deribit (stETH, 7.5% haircut), Drift (JitoSOL + mSOL).
# OKX, Binance: pending live API verification (stETH status unconfirmed).
# Reference: codex/09-strategy/architecture-v2/archetypes/carry-staked-basis.md
LST_MARGIN_VENUES: dict[str, list[str]] = {
    "BYBIT": ["stETH"],
    "DERIBIT": ["stETH"],
    "DRIFT": ["JitoSOL", "mSOL"],
}
