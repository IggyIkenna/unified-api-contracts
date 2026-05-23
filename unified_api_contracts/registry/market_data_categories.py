"""Market data category reference data (SSOT).

Canonical data types, venues, and timeframes organized by market category.
Used by market-data-processing-service, features-delta-one-service, and
other data pipeline services.

Previously hardcoded in market-data-processing-service/config.py with
comment 'NOTE: Keep in sync with unified-trading-deployment-v2/configs/venues.yaml'.
Centralized here as the system SSOT per UAC registry pattern.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date as _date
from datetime import timedelta as _timedelta

from unified_api_contracts.registry.defi_venues import MTDS_DEFI_VENUES as _MTDS_DEFI_VENUES

# Default timeframes for candle processing (used by sharding and CLI)
TIMEFRAMES: list[str] = ["15s", "1m", "5m", "15m", "1h", "4h", "24h"]

# Base (native) granularity per data type — the finest meaningful timeframe
# that can be produced from the raw source data for each data type.
# Tick-level data (trades, book snapshots) → 15s base.
# Pre-aggregated OHLCV → native period is the base.
# DeFi on-chain data → depends on block time; 15m is safe default for ETH (~12s blocks).
# Sports odds → horizon-based buckets, not standard timeframes.
BASE_GRANULARITY_BY_DATA_TYPE: dict[str, str] = {
    # CeFi — tick-level from Tardis
    "trades": "15s",
    "book_snapshot_5": "15s",
    "derivative_ticker": "15s",
    "liquidations": "15s",
    "options_chain": "15s",
    "futures_chain": "15s",
    # TradFi — pre-aggregated candles
    "ohlcv_1m": "1m",
    "ohlcv_15m": "15m",
    "ohlcv_24h": "24h",
    "tbbo": "15s",
    # DeFi — on-chain sampled (ETH ~12s blocks → 15m safe default)
    # Note: "liquidations" already declared in CeFi section above (same 15s granularity)
    "dex_pools": "15m",
    "dex_swaps": "15s",
    "lending_indices": "15m",
    "perp_funding": "15m",
    "lst_rates": "15m",
    "oracle_prices": "15m",
    "gas_fees": "15m",
    "rewards": "24h",
    "risk_params": "24h",
    # New DeFi data types (Phase 1 — defi_data_types_completeness_2026_04_24)
    "liquidation_events": "15m",
    "flash_loan_events": "15m",
    "staking_yields": "24h",
    "token_transfers": "15m",
    "bridge_events": "15m",
    "position_data": "24h",
    "mev_events": "15m",
    "governance_events": "24h",
    "eigenlayer_rewards": "24h",
    "vault_share_price": "1h",  # ERC-4626 share-price tick: per-block read; 1h sampling enough for APY drift
    # Sports — horizon-based, not standard timeframes
    "odds_snapshot": "15m",
    "odds_movement": "15m",
    "arbitrage_opportunity": "15m",
    # Prediction — tick-level from CLOB (uses canonical "trades" / "book_snapshot_5",
    # aligned with CeFi; no category-specific data_type names).
}

# Timeframe ordering in seconds (used for validation and aggregation)
TIMEFRAME_SECONDS: dict[str, int] = {
    "15s": 15,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "24h": 86400,
}


def get_valid_timeframes_for_data_type(data_type: str) -> list[str]:
    """Return the list of valid output timeframes for a data type.

    Only timeframes >= the base granularity are valid. Requesting 15s candles
    from ohlcv_15m source data would produce NaN-filled garbage.
    """
    base = BASE_GRANULARITY_BY_DATA_TYPE.get(data_type)
    if base is None:
        return list(TIMEFRAMES)  # Unknown data type — allow all
    base_seconds = TIMEFRAME_SECONDS.get(base, 0)
    return [tf for tf in TIMEFRAMES if TIMEFRAME_SECONDS.get(tf, 0) >= base_seconds]


# Data types per asset group
DATA_TYPES_BY_ASSET_GROUP: dict[str, list[str]] = {
    "cefi": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "options_chain",  # Deribit options - LOCF sampled to candles
        "futures_chain",  # Deribit/CME futures - LOCF sampled to candles
        # 2026-05-07: ohlcv_1m for DEX venues (Lighter /candles + Pacifica /kline).
        # Lighter zkSync per-trade /recentTrades is hard-capped at last ~100 trades
        # with no cursor, so /candles OHLCV bars are the only historical-capable
        # path; same shape applies to Pacifica /kline. Tardis CeFi venues do not
        # expose OHLCV bars — their adapters return empty for ohlcv_1m, which the
        # manifest records as empty_confirmed (honest absence per workspace
        # "honest absence vs fake placeholders" rule).
        "ohlcv_1m",
    ],
    "tradfi": [
        "trades",
        "ohlcv_1m",  # Databento 1m candles (base timeframe)
        "ohlcv_15m",  # VIX 15m: Barchart CSV (2020-01-07→2021-04-21, discontinued) then Yahoo Finance; KRW rates
        "ohlcv_24h",  # Yahoo Finance daily rates (KRW/USD, etc.)
        "tbbo",  # Top-of-book quotes
    ],
    "defi": [
        "dex_pools",  # DEX pool metrics (TVL, liquidity depth)
        "dex_swaps",  # DEX swap events (requires candle sampling)
        "lending_indices",  # Lending rate indices (supply/borrow APY, utilization)
        "liquidations",  # DeFi liquidation events
        "perp_funding",  # Perpetual funding rates (Hyperliquid, Aster, GMX)
        "lst_rates",  # Liquid staking token exchange rates
        "oracle_prices",  # Chainlink oracle price snapshots
        "gas_fees",  # EVM gas fee history
        "rewards",  # Protocol reward emissions (pass-through, OHLCV=NaN)
        "risk_params",  # Protocol risk parameters (pass-through, OHLCV=NaN)
        # ── New data types (Phase 1 — defi_data_types_completeness_2026_04_24) ──
        "liquidation_events",  # Liquidation call events (Aave V3, Morpho)
        "flash_loan_events",  # Flash loan events (Aave V3)
        "staking_yields",  # Staking APY snapshots (Lido, EigenLayer)
        "token_transfers",  # ERC-20 transfer events for top DeFi tokens
        "bridge_events",  # Cross-chain bridge transfer events
        "position_data",  # User positions (Aave V3 top borrowers, Uniswap V3 LP)
        "mev_events",  # MEV-Boost relay builder/relay stats
        "governance_events",  # DAO proposal + vote events
        "eigenlayer_rewards",  # EigenLayer restaking reward distributions
        # DeFi pipeline extension follow-ups (2026-05-03):
        # ERC-4626 vault totalAssets/totalSupply snapshots (top-40 vaults
        # across Yearn V3 / Morpho / Aave Vaults / Sommelier / MetaMorpho).
        "vault_share_price",
        "native_staking_rates",  # Solana validator native staking APY per epoch
    ],
    "sports": [
        "odds",  # Raw bookmaker odds from Odds API (MTDS raw tick data)
        "odds_snapshot",  # Point-in-time bookmaker odds (LOCF sampled)
        "odds_movement",  # Odds line movement OHLC candles
        "arbitrage_opportunity",  # Cross-bookmaker arbitrage detection
    ],
    "prediction": [
        # Canonical names — aligned with CeFi. Legacy prediction_* names retired
        # 2026-04-19. book_snapshot_5 also removed 2026-04-19 — POLYMARKET/KALSHI
        # capability was trimmed and leaving it here phantom-inflated PREDICTION
        # completion_pct (35k vs 5.7k observed). Re-add if/when a prediction
        # adapter starts emitting book snapshots.
        "trades",
        # Non-instrument-day-grain data_types — cluster-grain (question_group) and
        # market_id-grain (MARKET_LIFECYCLE). Downstream completion_pct aggregators
        # MUST NOT mix these with instrument-day-grain types when computing coverage
        # denominators; segregate by grain before summing. See predictions_master plan
        # PR-3/PR-4 and catalogue_audit_prediction_2026_05_12.md findings PR-3/PR-4.
        "prediction_canonical_question_group",  # cluster-grain (CanonicalQuestionGroup)
        "MARKET_LIFECYCLE",  # market_id-grain (lifecycle timestamps per market)
    ],
}

# Venues per asset group
VENUES_BY_ASSET_GROUP: dict[str, list[str]] = {
    "cefi": [
        # Centralized exchanges (Tardis API)
        "BINANCE-SPOT",
        "BINANCE-FUTURES",
        "BYBIT",
        "OKX",
        "DERIBIT",
        "UPBIT",
        "COINBASE",
        # 2026-05-01: Tardis Tier-3 expansion (cefi_venue_universe_expansion plan)
        "BITFINEX-SPOT",
        "BITFINEX-FUTURES",
        "BITGET-SPOT",
        "BITGET-FUTURES",
        "KRAKEN-SPOT",
        "KRAKEN-FUTURES",
        # On-chain CLOBs (reclassified from DEFI - CLOB-style data like CeFi)
        "HYPERLIQUID",
        "ASTER",
        # 2026-05-01 DEX perp expansion (cefi_venue_universe_expansion plan)
        "PACIFICA-SOLANA",
        "EXTENDED-STARKNET",
        "LIGHTER-ZKSYNC",
    ],
    "tradfi": [
        # Databento venues
        "NASDAQ",
        "NYSE",
        "CME",
        "ICE",
        "CBOE",
        # External data providers
        "FX",  # FX rates (KRW/USD via Yahoo Finance data provider)
        "BARCHART",  # VIX 15m historical: 2020-01-02→2025-11-12 (CSV download, discontinued; pre-loaded to GCS)
        "YAHOO_FINANCE",  # VIX 15m ongoing: rolling 60-day window; KRW/USD daily rates
    ],
    "defi": list(_MTDS_DEFI_VENUES),
    "sports": [
        # Sports betting exchanges and bookmakers active in the May-23 universe.
        # DEFERRED-INDEFINITELY 2026-05-12 per operator: scraper bookmakers
        # (BET365, DRAFTKINGS, FANDUEL, WILLIAMHILL, LADBROKES, CORAL, PADDYPOWER,
        # SKYBET, BETWAY, BETVICTOR, BOYLESPORTS, BWIN, BET888SPORT, UNIBET,
        # BETFRED, SBOBET) are out of the active venue universe; their venue
        # constants + capability flags + execution adapter stubs remain in the
        # codebase as future-work scaffolding but they do NOT participate in MTDS
        # market-data ingestion or in `VENUES_BY_ASSET_GROUP["sports"]`. See
        # `unified-trading-pm/plans/epics/sports_master.md` §
        # "Scrapers DEFERRED-INDEFINITELY 2026-05-12 per operator".
        "ODDS_API",  # Multi-bookmaker odds aggregator (raw tick data source)
        "PINNACLE",
        "BETFAIR",
    ],
    "prediction": [
        # Prediction markets (binary / multi-outcome)
        "POLYMARKET",
        "KALSHI",
    ],
}

# All supported data types (union of all asset groups)
ALL_DATA_TYPES: list[str] = sorted({dt for dts in DATA_TYPES_BY_ASSET_GROUP.values() for dt in dts})

# All supported venues (union of all asset groups)
ALL_VENUES: list[str] = sorted({v for vs in VENUES_BY_ASSET_GROUP.values() for v in vs})


# --- Candle processing classification ---
# True = MDPS should process this data type through a candle adapter.
# False = bypass (pre-bucketed data written directly by MTDS, no OHLCV conversion needed).
NEEDS_CANDLE_PROCESSING: dict[str, bool] = {
    # CeFi — all need candle processing from raw ticks
    "trades": True,
    "book_snapshot_5": True,
    "derivative_ticker": True,
    "liquidations": True,
    "options_chain": True,
    "futures_chain": True,
    # TradFi — pre-aggregated but still processed (timeframe re-aggregation)
    "ohlcv_1m": True,
    "ohlcv_15m": True,
    "ohlcv_24h": True,
    "tbbo": True,
    # DeFi — candle-sampled types need processing; pass-through types do not
    "dex_pools": False,
    "dex_swaps": True,
    "lending_indices": False,
    # Note: "liquidations" already declared in CeFi section above (True — same for DeFi)
    "perp_funding": False,
    "lst_rates": False,
    "oracle_prices": False,
    "gas_fees": False,
    "rewards": False,
    "risk_params": False,
    # New DeFi data types — all pass-through (event/snapshot data, not OHLCV)
    "liquidation_events": False,
    "flash_loan_events": False,
    "staking_yields": False,
    "token_transfers": False,
    "bridge_events": False,
    "position_data": False,
    "mev_events": False,
    "governance_events": False,
    "eigenlayer_rewards": False,
    "vault_share_price": False,  # ERC-4626 share-price tick — pass-through, no candle adapter
    "native_staking_rates": False,  # Solana validator native staking APY per epoch — pass-through
    # Sports — candle adapters process these
    "odds": False,  # Raw tick data, not directly processed (bucket adapter handles)
    "odds_snapshot": True,
    "odds_movement": True,
    "arbitrage_opportunity": True,
    # Prediction — uses canonical "trades" / "book_snapshot_5" (same keys as CeFi).
}


def needs_candle_processing(data_type: str) -> bool:
    """Return True if the data type requires MDPS candle adapter processing.

    Data types not in NEEDS_CANDLE_PROCESSING default to True (process by default).
    """
    return NEEDS_CANDLE_PROCESSING.get(data_type, True)


# --- Venue → asset group reverse lookup ---

VENUE_TO_ASSET_GROUP: dict[str, str] = {venue: ag for ag, venues in VENUES_BY_ASSET_GROUP.items() for venue in venues}


# --- Feature-group → data_type mappings (SSOT for all feature services) ---
# Previously hardcoded in features-delta-one-service orchestrator.

FEATURE_GROUP_DATA_TYPES: dict[str, str] = {
    # Default (CEFI) — most feature groups use trades
    "technical_indicators": "trades",
    "moving_averages": "trades",
    "oscillators": "trades",
    "volatility_realized": "trades",
    "momentum": "trades",
    "volume_analysis": "trades",
    "vwap": "trades",
    "candlestick_patterns": "trades",
    "market_structure": "trades",
    "returns": "trades",
    "round_numbers": "trades",
    "streaks": "trades",
    "microstructure": "book_snapshot_5",
    "funding_oi": "derivative_ticker",
    "liquidations": "liquidations",
    "futures_basis": "trades",
    "volume_flow": "trades",
    "temporal": "trades",
    "economic_events": "trades",
    "targets": "trades",
    # S/R level system feature groups
    "supply_demand_zones": "trades",
    "fibonacci": "trades",
    "level_confluence": "trades",
    "market_structure_sequence": "trades",
    # ML feature enhancement
    "risk_reward": "trades",
    "wedge_quality": "trades",
}

# Asset-group-specific overrides (applied on top of FEATURE_GROUP_DATA_TYPES)
FEATURE_GROUP_DATA_TYPE_OVERRIDES: dict[str, dict[str, str]] = {
    "tradfi": {
        "microstructure": "tbbo",  # Top of Book for TradFi equities
    },
    "defi": {
        "technical_indicators": "oracle_prices",
        "moving_averages": "oracle_prices",
        "oscillators": "oracle_prices",
        "volatility_realized": "oracle_prices",
        "momentum": "oracle_prices",
        "volume_analysis": "dex_swaps",
        "vwap": "dex_swaps",
        "candlestick_patterns": "oracle_prices",
        "market_structure": "oracle_prices",
        "returns": "oracle_prices",
        "round_numbers": "oracle_prices",
        "streaks": "oracle_prices",
        "microstructure": "dex_swaps",
        "funding_oi": "perp_funding",
        "liquidations": "liquidations",
        "temporal": "oracle_prices",
        "economic_events": "oracle_prices",
        "targets": "oracle_prices",
    },
    # "prediction": no overrides needed — prediction markets use "trades" (same as CeFi)
    # for all delta-one feature groups, and the default FEATURE_GROUP_DATA_TYPES already
    # maps them to "trades". Aligning with CeFi per single-source-of-truth rule.
}


def resolve_data_type_for_feature_group(feature_group: str, asset_group: str) -> str:
    """Resolve the correct data type for a feature group in a given asset group.

    Uses FEATURE_GROUP_DATA_TYPES as base, with per-asset-group overrides.
    This is the SSOT — services should not hardcode data type mappings.
    """
    ag_lower = asset_group.lower()
    overrides = FEATURE_GROUP_DATA_TYPE_OVERRIDES.get(ag_lower, {})
    if feature_group in overrides:
        return overrides[feature_group]
    return FEATURE_GROUP_DATA_TYPES.get(feature_group, "trades")


def get_valid_data_types_for_venue(venue: str) -> list[str]:
    """Return the valid data types for a venue based on its asset group.

    Looks up the venue's asset group, then returns the data types for that group.
    """
    ag = VENUE_TO_ASSET_GROUP.get(venue, "")
    return DATA_TYPES_BY_ASSET_GROUP.get(ag, [])


def validate_data_type_for_venue(venue: str, data_type: str) -> bool:
    """Check if a data type is valid for a venue.

    Returns True if the data type is in the venue's asset group's allowed data types.
    Returns True for unknown venues (permissive — validation is advisory).
    """
    valid = get_valid_data_types_for_venue(venue)
    if not valid:
        return True  # Unknown venue — don't block
    return data_type in valid


# --- Per-venue data type capabilities with start dates ---
# SSOT for which data types each venue can produce and when that capability started.
# Used by MTDS for shard-level skip logic and deployment UI for multi-dimensional status.
#
# Structure: {venue: {data_type: start_date_YYYY_MM_DD}}
# Default rule: if a venue is NOT in this dict, fall back to asset-group-level
# DATA_TYPES_BY_ASSET_GROUP with VenueMapping.venue_start_dates as the start date.
# Only venues with non-default data type availability need explicit entries.
#
# ── MVP Data Type Overrides ──
# In MVP mode, we limit downloads to reduce cost and API calls.
# Key decision: Deribit options — only download options_chain (IV/greeks, bulk 1-call)
# not trades/book_snapshot_5/derivative_ticker/liquidations per individual option strike
# (~12,000 API calls/day → 1 call/day). Full tick data for individual options is
# only needed for execution quality analysis, not for strategy/ML.
# Perpetuals still get all data types (trades, book, deriv_ticker, liquidations).

MVP_VENUE_DATA_TYPES: dict[str, list[str]] = {
    # Deribit: perpetual data types + only bulk-downloadable chain types (no per-strike tick data)
    "DERIBIT": ["trades", "book_snapshot_5", "derivative_ticker", "liquidations", "options_chain", "futures_chain"],
    # For other CeFi venues, perpetuals get all data types (same as full mode)
    # TradFi: controlled by tick_windows + MVP_CME_EXCHANGE_CODES (ES-only)
}

# Deribit MVP: which instrument types get which data types.
# Options/futures only get chain data types (bulk download).
# Perpetuals get all data types (per-symbol download, but only ~20 perps).
DERIBIT_MVP_INSTRUMENT_TYPE_DATA_TYPES: dict[str, list[str]] = {
    "perpetual": ["trades", "book_snapshot_5", "derivative_ticker", "liquidations"],
    "options_chain": ["options_chain"],  # Bulk only — no per-strike trades/book
    "futures_chain": ["futures_chain"],  # Bulk only — no per-contract trades/book
}


# Override entries needed when:
# - A venue's data type started later than the venue itself (e.g. Deribit options added later)
# - A venue only supports a subset of its category's data types (e.g. CBOE has ohlcv_15m only)
# - A data type has a different start date per venue (e.g. TradFi venues)

VENUE_DATA_TYPE_CAPABILITIES: dict[str, dict[str, str]] = {
    # ── CeFi — Tardis exchanges ──
    # Most CeFi venues support all cefi data types from their launch date.
    # Exceptions: only DERIBIT has options_chain/futures_chain.
    # HYPERLIQUID/ASTER: perpetual-focused, no options/futures chain.
    "BINANCE-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "BINANCE-FUTURES": {
        "trades": "2019-11-17",
        "book_snapshot_5": "2019-11-17",
        "derivative_ticker": "2019-11-17",
        "liquidations": "2019-11-17",
        "futures_chain": "2019-11-17",
    },
    "DERIBIT": {
        "trades": "2019-03-30",
        "book_snapshot_5": "2019-03-30",
        "derivative_ticker": "2019-03-30",
        "liquidations": "2019-03-30",
        "options_chain": "2019-03-30",
        "futures_chain": "2019-03-30",
    },
    "BYBIT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
        "futures_chain": "2020-01-01",
    },
    "OKX": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
    },
    # Canonical suffixed variants (VenueMapping.tardis_to_venue returns
    # these forms — OKX-SPOT/OKX-FUTURES/OKX-SWAP — to disambiguate market
    # types). Bare "OKX" kept above for execution-context / client-config
    # callers that don't split by market. MTDS per-venue lookups hit the
    # suffixed form.
    "OKX-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "OKX-FUTURES": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
    },
    "OKX-SWAP": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
    },
    "UPBIT": {
        "trades": "2021-03-03",
        "book_snapshot_5": "2021-03-03",
    },
    "COINBASE": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "COINBASE-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    # HYPERLIQUID — verified 2026-05-04 against the actual S3 archive layout.
    # Tardis added Hyperliquid 2024-10-29 but our adapter does not wire the
    # Tardis trades fetch path (returns []), so trades start = S3 archive start
    # 2025-03-22. liquidations is out of scope (Hyperliquid does not publish a
    # liquidations feed — no S3 prefix, no Tardis channel).
    # perp_funding: collected by perp_funding_handler via POST /info fundingHistory
    # (declared in _defi.py _ProtocolCapability data_types=["perp_funding"]);
    # start date aligned with derivative_ticker S3 archive start.
    "HYPERLIQUID": {
        "trades": "2025-03-22",  # S3 hl-mainnet-node-data/node_fills
        "book_snapshot_5": "2023-04-15",  # S3 hyperliquid-archive/market_data/
        "derivative_ticker": "2023-05-20",  # S3 hyperliquid-archive/asset_ctxs/
        "perp_funding": "2023-05-20",  # perp_funding_handler REST /info fundingHistory
    },
    # ASTER — only derivative_ticker (fundingRate REST) and trades (aggTrades
    # REST, ~30-day rolling depth) are wired in _fetch_aster_rest. Both available
    # since Aster launch (2024-10-01). book_snapshot_5 + liquidations both out
    # of scope (no wired fetch path).
    # perp_funding: collected by perp_funding_handler (declared in _defi.py
    # _ProtocolCapability data_types=["perp_funding"]); start = Aster launch.
    "ASTER": {
        "trades": "2024-10-01",
        "derivative_ticker": "2024-10-01",
        "perp_funding": "2024-10-01",  # perp_funding_handler REST Aster API
    },
    # Tier-3 CeFi (2026-05-01) — spot=trades+book; perp=+ derivative_ticker
    # +liquidations. None carry chain bundles (perps are individual syms).
    "BITFINEX-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "BITFINEX-FUTURES": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
    },
    "BITGET-SPOT": {
        "trades": "2024-11-08",
        "book_snapshot_5": "2024-11-08",
    },
    "BITGET-FUTURES": {
        "trades": "2024-11-08",
        "book_snapshot_5": "2024-11-08",
        "derivative_ticker": "2024-11-08",
        "liquidations": "2024-11-08",
    },
    "KRAKEN-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "KRAKEN-FUTURES": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
    },
    # ── TradFi — Databento (OHLCV-only MVP per operator direction 2026-05-15) ──
    # Operator: "lets [do] ohlcv 1m for all the tradfi mvp instruments only please …
    # no need for l1-l3 yet … i want the full period for tradfi thats available …
    # since 2019 1st jan at least". SSOT:
    # plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md Phase 2.
    # `trades` + `tbbo` (L1 + L2 tick data) are MOVED to post-cutover scope
    # (`_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS` below preserves the prior
    # date floors for the successor plan). Only `ohlcv_1m` (cheap pre-aggregated
    # bars) stays in MVP. Start dates backdated to 2019-01-01 per operator's
    # full-period ask (NASDAQ/NYSE only have Databento equity data from
    # 2023-04-15 — keep that floor since Databento's coverage starts there).
    "NASDAQ": {
        "ohlcv_1m": "2023-04-15",
    },
    "NYSE": {
        "ohlcv_1m": "2023-04-15",
    },
    "CME": {
        "ohlcv_1m": "2019-01-01",
    },
    "ICE": {
        "ohlcv_1m": "2019-01-01",
    },
    "CBOE": {
        "ohlcv_15m": "2020-01-07",  # VIX — Barchart CSV start
    },
    "FX": {
        "ohlcv_24h": "2020-01-01",  # KRW/USD daily via Yahoo Finance
    },
    "BARCHART": {
        "ohlcv_15m": "2020-01-02",  # VIX 15m historical CSV (discontinued 2025-11-12)
    },
    "YAHOO_FINANCE": {
        "ohlcv_15m": "2021-04-22",  # VIX 15m rolling 60-day window
        "ohlcv_24h": "2020-01-01",  # KRW/USD daily rates
    },
    # ── DeFi — multi-chain entries live in defi_venue_capabilities.py and
    # are merged into this dict at module-load time (see below). Split out
    # to keep this file under the 900-line QG ceiling.
    # ── Sports ──
    "ODDS_API": {
        "odds_snapshot": "2024-01-01",
        "odds_movement": "2024-01-01",
        "arbitrage_opportunity": "2024-01-01",
    },
    "PINNACLE": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    "BETFAIR": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    # DRAFTKINGS / FANDUEL / BET365 + the 14 UK/EU scraper bookmakers are
    # DEFERRED-INDEFINITELY 2026-05-12 per operator (see VENUES_BY_ASSET_GROUP
    # comment above + sports_master plan).
    # ── Prediction (market data only — metadata is reference data, see below) ──
    # Prediction CLOBs emit canonical "trades" (same key as CeFi). Legacy
    # prediction_* names + book_snapshot_5 retired 2026-04-19; book snapshots
    # phantom-inflated PREDICTION completion_pct (35k vs 5.7k observed).
    "POLYMARKET": {
        "trades": "2024-06-01",
    },
    "KALSHI": {
        "trades": "2024-06-01",
    },
}

# Merge the DEFI multi-chain block (extracted to defi_venue_capabilities.py
# to keep this file under the 900-line QG ceiling).
from unified_api_contracts.registry.defi_prediction_instrument_seeds import (  # noqa: E402  # placed after conditional setup to avoid circular import at load time
    seed_for_venue_and_data_type,
)
from unified_api_contracts.registry.defi_venue_capabilities import (  # noqa: E402  # placed after conditional setup to avoid circular import at load time
    DEFI_VENUE_DATA_TYPE_CAPABILITIES,
)

VENUE_DATA_TYPE_CAPABILITIES.update(DEFI_VENUE_DATA_TYPE_CAPABILITIES)


# Reference data capabilities — static/structural data collected by
# instruments-service.  Separate from market data capabilities above.
# Market shards (BTC, ETH, SPX, etc.) are emergent from the data and
# not declared here — only explicitly-typed reference data goes here.
# Reference data capabilities — reserved for instruments-service reference
# data types that are genuinely separate from the instruments themselves.
# Prediction market metadata is NOT separate — the instruments parquet IS
# the metadata (market question, outcomes, expiry are InstrumentRecord fields).
VENUE_REFERENCE_DATA_CAPABILITIES: dict[str, dict[str, str]] = {}


# TradFi tick data windows — OHLCV-only MVP per operator direction 2026-05-15.
# Per `plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md` Phase 1:
# tbbo + trades scope moved to post-cutover; only ohlcv_1m collected in MVP.
# `is_in_tradfi_tick_window` below returns False for ALL dates when the windows
# list is empty (`any([]) == False` is the intentional short-circuit), suppressing
# every tbbo/trades fetch attempt in MTDS orchestrator.py:3014.
# Restoration: post-cutover, populate from `_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS`
# below. Successor plan: `tradfi_l1_l2_l3_tick_data_post_cutover_2026_06_01.md`.
TRADFI_TICK_DATA_WINDOWS: list[dict[str, str]] = []

# Preserved windows for the post-cutover restoration plan (do not delete; the
# successor plan reads this list to restore TRADFI_TICK_DATA_WINDOWS above).
# Kept here (not in the post-cutover plan file) so a single grep -r finds the
# canonical historical scope.
# Renamed 2026-05-17 from `_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS` (the
# original naming conflicted with the dict-shape per-(venue, data_type)
# deferred constant added below — same name, incompatible shapes). The
# list-shape constant here mirrors TRADFI_TICK_DATA_WINDOWS; the dict-shape
# `_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS` below mirrors
# VENUE_DATA_TYPE_COVERAGE_WINDOWS. Plan reference:
# `plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md` Phase 1.
_DEFERRED_TRADFI_TICK_DATA_WINDOWS: list[dict[str, str]] = [
    {"start": "2023-05-01", "end": "2023-05-31"},  # was: Training window
    {"start": "2024-07-01", "end": "2024-07-31"},  # was: Validation window
]


def is_in_tradfi_tick_window(date_str: str) -> bool:
    """Check if a date falls within any TradFi tick data window.

    Tick windows are date ranges where expensive tick data (tbbo, trades) is
    collected from Databento. Outside these windows, only cheaper ohlcv_1m
    is downloaded.
    """
    return any(w["start"] <= date_str <= w["end"] for w in TRADFI_TICK_DATA_WINDOWS)


# ---------------------------------------------------------------------------
# Phase 4.3 — TradFi futures per-contract staleness gate
# ---------------------------------------------------------------------------
# CME/ICE futures symbols follow the pattern: ROOT + MONTH_CODE + YEAR_DIGITS
# e.g. ESH26, CLZ6, GCM26, 6EZ26, BRN.H26, CL.F27
# This regex matches the canonical raw_symbol format from Databento.
_FUTURES_SYMBOL_RE = re.compile(
    r"^(?P<root>[A-Z0-9]{1,5})"  # root: 1-5 alphanumeric chars
    r"\.?"  # optional dot separator (BRN.H26, CL.F27)
    r"(?P<month>[FGHJKMNQUVXZ])"  # CME month code
    r"(?P<year>\d{1,2})$",  # 1-2 digit year suffix
)

# CME month-code → month number (mirrors instruments-service futures_factory.py)
_FUTURES_MONTH_CODE: dict[str, int] = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}


def is_tradfi_futures_instrument_active(instrument_id: str, as_of_date_str: str) -> bool:
    """Return True if a TradFi futures instrument is expected to be active on a given date.

    Parses the CME/ICE futures symbol format (e.g. ESH26, CLZ6, BRN.H26) to derive
    the contract month and year, then checks whether the contract's expiry month is
    on or after the as_of_date.

    Conservative contract-expiry estimate: a contract is considered expired once
    ``as_of_date`` is strictly past the LAST DAY of the contract month.  In practice
    most CME contracts expire mid-month, so this is a conservative (inclusive) gate —
    it may include a few extra trading days inside the delivery month but never
    drops a contract that is still tradeable.  The full-precision expiry gate requires
    CanonicalFuturesContract.expiry_date from the IS GCS parquet (Phase 4.3
    precision upgrade — out of scope for the UAC pure-function tier).

    Parameters
    ----------
    instrument_id:
        Raw CME/ICE futures symbol (e.g. ``ESH26``, ``CLZ6``, ``BRN.H26``).
    as_of_date_str:
        ISO date string (``YYYY-MM-DD``).

    Returns
    -------
    bool
        ``True``  — contract is active (expiry month >= as_of_date month).
        ``True``  — symbol cannot be parsed (fail-open: don't suppress unknowns).
        ``False`` — contract is past its expiry month (expiry month < as_of_date month).

    Plan: tradfi_canonical_futures_contract_hard_required_fields_2026_05_13.md
    Phase 4.3 — mtds-tradfi-staleness per-contract gate.
    """
    m = _FUTURES_SYMBOL_RE.match(instrument_id.upper())
    if m is None:
        # Symbol doesn't match CME format — fail-open (don't suppress).
        return True
    year_suffix = int(m.group("year"))
    # Expand 2-digit year: 00-49 → 2000-2049, 50-99 → 1950-1999 (2030-safe).
    contract_year = (2000 + year_suffix) if year_suffix < 50 else (1900 + year_suffix)
    month_code = m.group("month")
    contract_month = _FUTURES_MONTH_CODE.get(month_code)
    if contract_month is None:
        return True  # Unknown month code — fail-open.
    try:
        as_of = _date.fromisoformat(as_of_date_str)
    except ValueError:
        return True  # Unparseable date — fail-open.
    # Contract is active if the as_of_date is not past the last day of contract month.
    # last day of contract month = first day of next month - 1 day
    if contract_month == 12:
        last_day = _date(contract_year + 1, 1, 1) - _timedelta(days=1)
    else:
        last_day = _date(contract_year, contract_month + 1, 1) - _timedelta(days=1)
    return as_of <= last_day


# Per-(venue, data_type) coverage-window registry — the more granular
# successor to the global ``TRADFI_TICK_DATA_WINDOWS``. When a key is
# present, the data-status reconciler restricts the expected-dates
# denominator to dates inside the windows. Use for cost-tier'd data
# types where we deliberately collect only specific reference months
# (e.g. CME futures L2 microstructure for execution-tuning).
#
# **Why per-(venue, data_type), not global:**
# Different venues have different cost / use-case profiles. CME tbbo
# is the heavy "execution-microstructure" capture for the date-futures
# arb archetype (May 2023 + Jun 2024 reference months only). Future
# entries can scope mbp_10 to the same window, or scope CBOE / NYSE
# tick captures to different bands without polluting the global config.
#
# Keys are ``(venue, data_type)``; values are inclusive [start, end]
# date-string tuples. ALL data not listed here is expected on every
# trading day from the venue's start_date (the default behaviour).
# Currently empty per OHLCV-only MVP scope (`tradfi_ohlcv_only_mvp_backfill_2026_05_15.md`
# Phase 1, 2026-05-15 operator direction). CME tbbo + CME mbp_10 windows moved to
# `_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS` below for post-cutover restoration.
VENUE_DATA_TYPE_COVERAGE_WINDOWS: dict[tuple[str, str], list[tuple[str, str]]] = {}


# Frozen reference of pre-2026-05-15 per-(venue, data_type) coverage windows.
# Restored by post-cutover successor plan
# `tradfi_l1_l2_l3_tick_data_post_cutover_2026_06_01.md` (filed Phase 9 of the
# OHLCV-only MVP plan). Mirrors the dict shape of VENUE_DATA_TYPE_COVERAGE_WINDOWS.
_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS: dict[tuple[str, str], list[tuple[str, str]]] = {
    # CME futures L2 microstructure (BTC date-futures-arb reference months)
    ("CME", "tbbo"): [
        ("2023-05-01", "2023-05-31"),
        ("2024-06-01", "2024-06-30"),
    ],
    # CME futures 10-deep book — adapter deferred to post-cutover scope.
    ("CME", "mbp_10"): [
        ("2023-05-01", "2023-05-31"),
        ("2024-06-01", "2024-06-30"),
    ],
}


def get_coverage_windows(venue: str, data_type: str) -> list[tuple[str, str]]:
    """Return the per-(venue, data_type) coverage-window list, or [] if unset.

    Used by deployment-api ``_mtds_expected_dates_for_venue_dt`` to clip
    the expected-dates denominator. Empty list = no clipping (default —
    expect every trading day from venue start_date).
    """
    return VENUE_DATA_TYPE_COVERAGE_WINDOWS.get((venue, data_type), [])


def is_in_coverage_window(venue: str, data_type: str, date_str: str) -> bool:
    """True if ``date_str`` (YYYY-MM-DD) is inside any registered coverage
    window for (venue, data_type). Returns False if no windows registered
    (caller should treat as "no clip" — i.e. date is in scope by default).
    """
    windows = VENUE_DATA_TYPE_COVERAGE_WINDOWS.get((venue, data_type), [])
    return any(start <= date_str <= end for start, end in windows)


def get_venue_data_type_start_date(venue: str, data_type: str) -> str | None:
    """Return the start date for a specific (venue, data_type) pair.

    Priority:
    1. VENUE_DATA_TYPE_CAPABILITIES[venue][data_type] — market data
    2. VENUE_REFERENCE_DATA_CAPABILITIES[venue][data_type] — reference data
    3. VenueMapping.venue_start_dates[venue] — venue-level default (lazy import)
    4. None — unknown venue/data_type (permissive)
    """
    caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
    if data_type in caps:
        return caps[data_type]
    ref_caps = VENUE_REFERENCE_DATA_CAPABILITIES.get(venue, {})
    if data_type in ref_caps:
        return ref_caps[data_type]
    # Fall back to venue start date from VenueMapping
    from .venue_mapping import (
        VenueMapping,  # noqa: qg-inside-import  # lazy import to avoid circular dependency at module load
    )

    vm = VenueMapping()
    # Check compound key first (e.g. POLYMARKET:CRUDE_OIL) for per-shard start dates
    compound = f"{venue}:{data_type}" if data_type else venue
    compound_start = vm.get_venue_start_date(compound)
    if compound_start:
        return compound_start
    return vm.get_venue_start_date(venue)


def get_expected_data_types_for_venue(
    venue: str,
    service: str = "",
) -> list[str]:
    """Return the list of data types a venue is expected to produce.

    The capabilities registry is split by service layer:
    - instruments-service → VENUE_REFERENCE_DATA_CAPABILITIES (static metadata)
    - MTDS/MDPS/features → VENUE_DATA_TYPE_CAPABILITIES (market data)

    Market shards (BTC, ETH, SPX for prediction) are emergent from the index
    and not declared in either registry — they appear automatically.
    """
    if service == "instruments-service":
        ref_caps = VENUE_REFERENCE_DATA_CAPABILITIES.get(venue, {})
        return sorted(ref_caps.keys()) if ref_caps else []
    caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
    if caps:
        return sorted(caps.keys())
    return get_valid_data_types_for_venue(venue)


# ---------------------------------------------------------------------------
# Phase 8 — per-instrument Tier-3 sentinel denominator helpers
# ---------------------------------------------------------------------------
# SSOT: unified-trading-pm/codex/02-data/mtds-data-source-coverage-matrix.md
# §§ 2, 4 and 8 (Phase 8 stretch goal — instrument-level expected).
#
# Per-instrument shard data_types: the adapter writes one GCS parquet per
# instrument per day. Honest-coverage denominator must therefore be
# (venue x data_type x instrument x date), not (venue x data_type x date).
#
# Venue-level shard data_types (`liquidations`, `ohlcv_*`, `tbbo`, `gas_fees`,
# `perp_funding`, `odds`) remain per-venue x per-date and are served by
# `get_expected_data_types_for_venue` + the Tier-2 sentinel path. Callers
# branch on `bool(get_expected_instruments_for_venue(...))` -- truthy == Tier-3
# fan-out, falsy == Tier-2 fan-out.

_PER_INSTRUMENT_SHARD_DATA_TYPES: frozenset[str] = frozenset(
    {
        # CEFI per-instrument shards
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "options_chain",
        "futures_chain",
        # DEFI per-pool / per-market / per-asset shards
        "dex_swaps",
        "dex_pools",
        "lending_indices",
        "oracle_prices",
        "lst_rates",
        "rewards",
        "risk_params",
        # PREDICTION per-conditionId shards
        "prediction_trades",
        "prediction_book_snapshot",
        "prediction_market_metadata",
    }
)

# MVP seed instrument tables — used when no runtime `instruments_provider` is
# injected. These caps keep the Phase 8 denominator from blowing up against
# the full ~200-perp BINANCE-FUTURES tape during initial rollout. Operators
# dial into Expanded / Full tiers via the `--per-instrument-sentinel-cap`
# CLI flag once the MVP-tier rollout stabilises.
#
# Scope: the 21 MVP base assets (crypto majors) on SPOT_PAIR venues, and the
# top-10 perp contracts on PERPETUAL venues. Derivative venues (OPTION /
# FUTURE) seed with the two dominant underlyings BTC / ETH — expiry
# expansion happens at adapter write-time, not in the sentinel denominator.
_SPOT_MVP_SEED_INSTRUMENTS: tuple[str, ...] = (
    "BTC-USDT",
    "ETH-USDT",
    "SOL-USDT",
    "BNB-USDT",
    "XRP-USDT",
    "ADA-USDT",
    "AVAX-USDT",
    "DOT-USDT",
    "MATIC-USDT",
    "LINK-USDT",
    "LTC-USDT",
    "TRX-USDT",
    "NEAR-USDT",
    "ATOM-USDT",
    "FIL-USDT",
    "APT-USDT",
    "ARB-USDT",
    "OP-USDT",
    "SUI-USDT",
    "INJ-USDT",
    "TIA-USDT",
)

_PERP_MVP_SEED_INSTRUMENTS: tuple[str, ...] = (
    "BTC-PERP",
    "ETH-PERP",
    "SOL-PERP",
    "BNB-PERP",
    "XRP-PERP",
    "ADA-PERP",
    "AVAX-PERP",
    "DOGE-PERP",
    "MATIC-PERP",
    "ARB-PERP",
)

# Derivatives (options / futures) underlyings for MVP seed — expiry series
# expansion happens inside the adapter, not in the denominator.
_OPTION_FUTURE_MVP_SEED_UNDERLYINGS: tuple[str, ...] = (
    "BTC",
    "ETH",
)


def is_per_instrument_shard_data_type(data_type: str) -> bool:
    """Return True iff ``data_type`` writes one GCS shard per instrument per day.

    Per-instrument dt require per-(venue, dt, instrument, date) denominators
    in the honest-coverage aggregator (Phase 8). Venue-level dt keep the
    Phase 6d per-(venue, dt, date) denominator.
    """
    return data_type in _PER_INSTRUMENT_SHARD_DATA_TYPES


def get_expected_instruments_for_venue(
    venue: str,
    data_type: str,
    *,
    as_of_date: str | None = None,
    instruments_provider: Callable[[str, str], list[str] | None] | None = None,
    cap: int | None = None,
) -> list[str]:
    """Return the per-instrument shard denominator for ``(venue, data_type)``.

    Phase 8 of the MTDS honest-coverage rollout. Callers (MTDS orchestrator,
    deployment-api aggregator) use this to fan out Tier-3 sentinels and to
    size the honest-coverage denominator at ``len(instruments) * len(dates)``
    per per-instrument data_type.

    Parameters
    ----------
    venue:
        Canonical MTDS venue key (``BINANCE-SPOT``, ``DERIBIT``,
        ``AAVEV3-ETHEREUM`` …) as used by ``VenueMapping``.
    data_type:
        Canonical MTDS data_type (``trades``, ``book_snapshot_5``,
        ``dex_swaps`` …).
    as_of_date:
        ISO date (YYYY-MM-DD). Reserved for future use — today both MVP
        seed tables and injected providers are date-agnostic, but this
        signature keeps the door open for instrument universes that churn
        (delisting tracking, expiry rolls).
    instruments_provider:
        Optional callable ``(venue, data_type) -> list[str]`` returning the
        live instrument list from a runtime source (typically the
        instruments-service parquet snapshot already in memory in the
        MTDS orchestrator). When ``None``, UAC falls back to the MVP seed
        tables below — this keeps UAC free of runtime GCS reads and makes
        the function pure for unit tests.
    cap:
        Optional hard ceiling on the returned list size. The MTDS
        orchestrator passes ``cap=_DEFAULT_PER_INSTRUMENT_SENTINEL_CAP``
        (MVP tier = 50) to keep manifest row counts bounded.

    Returns
    -------
    list[str]
        Canonical instrument_ids (possibly capped). **Empty list** when
        ``data_type`` is a venue-level (not per-instrument) shard, when the
        venue is unknown, or when the seed tables have no entry. Callers
        branch on truthiness: truthy → Tier-3 per-instrument fan-out;
        falsy → Tier-2 per-(venue, data_type) fan-out.
    """
    del as_of_date  # reserved for future churn-tracking; not yet used
    if data_type not in _PER_INSTRUMENT_SHARD_DATA_TYPES:
        return []

    resolved: list[str]
    if instruments_provider is not None:
        raw = instruments_provider(venue, data_type)
        resolved = [] if raw is None else [str(i) for i in raw]
    else:
        resolved = list(_default_seed_instruments_for(venue, data_type))

    if cap is not None and cap >= 0:
        resolved = resolved[:cap]
    return resolved


def _default_seed_instruments_for(venue: str, data_type: str) -> tuple[str, ...]:
    """MVP seed table — used when ``instruments_provider`` is None.

    Scope intentionally narrow: the 21 MVP base assets on SPOT dts, the
    top-10 perps on PERPETUAL / derivative_ticker dts, BTC / ETH on
    options_chain / futures_chain, top-20 Uniswap V3 pools / top-10 Aave
    reserves / LST tokens on DEFI dts, and top-10 Polymarket conditionIds
    on PREDICTION dts (Wave 8G — see
    ``registry.defi_prediction_instrument_seeds``).
    """
    # CEFI spot_pair path for `trades` + `book_snapshot_5`. PREDICTION
    # venues also write canonical `trades` (since 2026-04-19
    # `prediction_trades` rename) so they branch off first.
    if data_type in ("trades", "book_snapshot_5"):
        if venue in ("POLYMARKET", "KALSHI"):
            return seed_for_venue_and_data_type(venue, data_type)
        venue_caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
        # If the venue's capability table doesn't declare this data_type at
        # all, the venue isn't wired to publish it — empty seed so the
        # Tier-3 sentinel doesn't fan out an expectation that can never be
        # satisfied. ASTER is the canonical case (no book_snapshot_5 per
        # VENUE_DATA_TYPE_CAPABILITIES, only trades + derivative_ticker).
        if venue_caps and data_type not in venue_caps:
            return ()
        # Spot-only venues. Names ending in -SPOT plus the historical bare
        # COINBASE-SPOT / UPBIT / BINANCE-SPOT entries that predate the
        # suffix convention. These trade SPOT pairs only.
        if venue.endswith("-SPOT") or venue in ("COINBASE-SPOT", "UPBIT", "BINANCE-SPOT"):
            return _SPOT_MVP_SEED_INSTRUMENTS
        # Perp-only / perp-dominant venues. Anything ending -FUTURES on
        # Tardis is actually a perp/derivative venue (Bitfinex / Bitget /
        # Kraken) — the suffix is the Tardis exchange-name historical
        # accident. OKX-FUTURES is dated futures but the MVP universe seeds
        # with perps (the linear ones live under OKX-SWAP, the dated ones
        # under OKX-FUTURES; both write trades for the MVP perp basket).
        if venue.endswith("-FUTURES") or venue in (
            "BINANCE-FUTURES",
            "BYBIT",
            "OKX-SWAP",
            "HYPERLIQUID",
            "ASTER",
        ):
            return _PERP_MVP_SEED_INSTRUMENTS
        if venue == "DERIBIT":
            # DERIBIT writes SPOT + PERP + OPTION; on the `trades` /
            # `book_snapshot_5` axis we seed with perps.
            return _PERP_MVP_SEED_INSTRUMENTS
        # Unknown venue — fall back to empty (caller degrades to Tier-2).
        if not venue_caps:
            return ()
        # Default: treat as spot.
        return _SPOT_MVP_SEED_INSTRUMENTS

    if data_type == "derivative_ticker":
        # derivative_ticker only makes sense on derivative venues. Spot-only
        # venues (BINANCE-SPOT / OKX-SPOT / COINBASE-SPOT / UPBIT /
        # KRAKEN-SPOT / BITFINEX-SPOT / BITGET-SPOT) have no derivatives, so
        # no expected instruments — return empty so the Tier-3 sentinel
        # doesn't fan out a per-perp expectation onto a venue that can't
        # publish derivative_ticker.
        if venue.endswith("-SPOT") or venue in ("COINBASE-SPOT", "UPBIT", "BINANCE-SPOT"):
            return ()
        # Unknown venue with no declared capability — empty (degrade to
        # Tier-2 or skip). VENUE_DATA_TYPE_CAPABILITIES is the SSOT for
        # whether the venue is wired for this data_type at all.
        venue_caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
        if data_type not in venue_caps:
            return ()
        return _PERP_MVP_SEED_INSTRUMENTS

    if data_type in ("options_chain", "futures_chain"):
        return _OPTION_FUTURE_MVP_SEED_UNDERLYINGS

    # DEFI per-instrument dts (dex_pools / dex_swaps / lending_indices /
    # oracle_prices / lst_rates / rewards / risk_params) + PREDICTION
    # legacy `prediction_trades` / `prediction_book_snapshot` /
    # `prediction_market_metadata` — delegated to the Wave 8G seed module.
    return seed_for_venue_and_data_type(venue, data_type)
