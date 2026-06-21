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

from unified_api_contracts.registry.defi_venues import ALL_DEFI_VENUES as _ALL_DEFI_VENUES

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
    "ohlcv_1s": "1s",  # Databento ohlcv-1s — fetched alongside ohlcv_1m (both L0/free); 15m/1h/24h aggregated
    "ohlcv_1m": "1m",
    "ohlcv_15m": "15m",
    "ohlcv_24h": "24h",
    "tbbo": "15s",
    # DeFi — on-chain sampled (ETH ~12s blocks → 15m safe default)
    # Note: "liquidations" already declared in CeFi section above (same 15s granularity)
    "dex_pool_state": "15m",
    "dex_pool_swaps": "15s",
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
    "odds_horizon_bucket": "15m",
    "markets": "24h",
    "outcomes": "24h",
    "settlements": "24h",
    # Prediction — tick-level from CLOB (uses canonical "trades" / "book_snapshot_5",
    # aligned with CeFi; no category-specific data_type names).
    # DeFi adapter-produced types (canonicalized 2026-05-23).
    "utilization": "15m",
    "flash_loan_availability": "15m",
    "vault_apy": "24h",
    "vault_tvl": "24h",
    # TradFi reference/event types — daily grain.
    "corporate_action_confirmed": "24h",
    "earnings_result": "24h",
    "macro_result": "24h",
    "mbp_10": "15s",  # Market by price 10 levels — tick-level from CME/Databento
    # Prediction lifecycle
    "market_lifecycle": "24h",  # Market creation/resolution/settlement events
}

# Timeframe ordering in seconds (used for validation and aggregation)
TIMEFRAME_SECONDS: dict[str, int] = {
    "1s": 1,
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
        # 2026-06-21: periodic funding settlements for CFTC-regulated crypto perp venues.
        # kalshi_perp (launched 2026-05-29) + polymarket_perp (launched 2026-04-21) expose
        # a dedicated /markets/{ticker}/funding_rates REST endpoint (cursor-paginated,
        # public-read). Source priority: ("cefi", "perp_funding"). SSOT: prediction-perps-sourcing.md.
        "perp_funding",
    ],
    "tradfi": [
        "trades",
        "ohlcv_1s",  # Databento ohlcv-1s (L0/free 16y) — fetched alongside ohlcv_1m; 15m/1h/24h aggregated
        "ohlcv_1m",  # Databento 1m candles — fetched (L0/free 16y), completes the existing 1m corpus
        "ohlcv_15m",  # VIX 15m: Barchart CSV (2020-01-07→2021-04-21, discontinued) then Yahoo Finance; KRW rates
        "ohlcv_24h",  # Yahoo Finance daily rates (KRW/USD, etc.)
        "tbbo",  # Top-of-book quotes
        "mbp_10",  # Market by price — 10 levels (CME Databento)
        # ── Reference/event types from Polygon.io and FRED (canonicalized 2026-05-23) ──
        "corporate_action_confirmed",  # Confirmed dividends + splits (Polygon.io Equities Basic)
        "earnings_result",  # Earnings results (Polygon.io)
        "macro_result",  # Macro economic results: NFP/CPI/GDP/FOMC/Claims/PCE (FRED)
    ],
    "defi": [
        "dex_pool_state",  # DEX pool metrics (TVL, liquidity depth)
        "dex_pool_swaps",  # DEX swap events (requires candle sampling)
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
        # ── Adapter-produced types (canonicalized 2026-05-23) ──
        # Written as separate GCS parquets by lending/vault adapters;
        # distinct from their parent data types.
        "utilization",  # Utilization rate extracted alongside lending_indices (Aave, Morpho, Fluid)
        "flash_loan_availability",  # Available flash-loan liquidity (Morpho historicalState)
        "vault_apy",  # ERC-4626 vault APY (Yearn/Beefy/Pendle/Convex/Idle)
        "vault_tvl",  # ERC-4626 vault TVL (same adapters as vault_apy)
    ],
    "sports": [
        "odds",  # Raw bookmaker odds from Odds API (MTDS raw tick data)
        "ODDS",  # Canonical uppercase form per mega-audit R2 (ODDS_API emits this)
        "odds_snapshot",  # Point-in-time bookmaker odds (LOCF sampled)
        "odds_movement",  # Odds line movement OHLC candles
        "arbitrage_opportunity",  # Cross-bookmaker arbitrage detection
        "odds_horizon_bucket",  # Time-to-event horizon bucket assignment for odds
        # ── Exchange/market lifecycle types (in venue_data_types.yaml, canonicalized 2026-05-23) ──
        "markets",  # Market metadata (event/market listings per bookmaker)
        "outcomes",  # Outcome results (settled markets)
        "settlements",  # Settlement records (payout confirmation)
        # ── Bet/trade events (PINNACLE, BETFAIR_SB_UK/EX_UK/EX_EU, DRAFTKINGS, FANDUEL) ──
        "trades",  # Matched bets / trade-level acceptance events (aligned with CeFi/prediction)
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
        "market_lifecycle",  # market_id-grain — MTDS/YAML canonical name (lowercase)
        "MARKET_LIFECYCLE",  # market_id-grain — instruments-service GCS data_type (uppercase legacy)
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
        # DERIBIT-COMBO: multi-leg combo/spread instruments fetched from Deribit's
        # public get_instruments (future_combo + option_combo kinds). Registered as a
        # DISTINCT venue (instruments-service VENUE_TO_ADAPTER["DERIBIT-COMBO"]="deribit_combo",
        # its own manifest shard) — the validation registry MUST know it or every fetched
        # combo is rejected "unknown venue" (the venue had 0 captured days 2026-05-23→06-18
        # until the kind-split + venue-tag fixes 2026-06-18). instrument_key stays DERIBIT:COMBO:*.
        "DERIBIT-COMBO",
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
        # 2026-06-20 prediction-platform perp CLOBs — CFTC-regulated crypto perps
        # with funding (NOT prediction YES/NO markets; those stay in "prediction").
        # Kalshi: 13 crypto perp contracts, CFTC-approved, launched 2026-05-29.
        # Polymarket: crypto+stock perps, beta 2026-04-21. Share canonical perp
        # instrument universe (BTC-PERP etc.) alongside CeFi venues for funding-
        # rate arb / basis / cross-venue dispersion. SSOT: prediction_venue_perps_
        # and_live_clob_depth_2026_06_20.md
        "KALSHI-PERP",
        "POLYMARKET-PERP",
    ],
    "tradfi": [
        # Databento venues — 3-dataset subscription lockdown (operator 2026-06-18):
        # GLBX.MDP3 (CME futures+options+event contracts) + DBEQ.BASIC (NASDAQ/NYSE
        # equities, consolidated) + CFE (CBOE — VX/VIX futures). The ICE Databento
        # datasets (IFEU.IMPACT/IFUS.IMPACT) are OUT of the paid subscription so the
        # ICE Databento *instruments* (Brent/Gasoil/softs/DX) were dropped from
        # tradfi_instrument_universe.py — but ICE STAYS a venue here because the
        # ICE/NYBOT US Dollar Index (DXY) is still sourced via Yahoo (non-Databento)
        # under venue ICE, and the market-session / data-status / source-resolution
        # registries key off it. SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.
        "NASDAQ",
        "NYSE",
        "CME",
        "ICE",  # Yahoo-sourced ICE/NYBOT DXY index only (no ICE Databento datasets)
        "CBOE",  # Cboe Futures Exchange (CFE) — VX / VIX futures
        # External data providers
        "FX",  # FX rates (KRW/USD via Yahoo Finance data provider)
        "BARCHART",  # VIX 15m historical: 2020-01-02→2025-11-12 (CSV download, discontinued; pre-loaded to GCS)
        "YAHOO_FINANCE",  # VIX 15m ongoing: rolling 60-day window; KRW/USD daily rates
    ],
    "defi": list(_ALL_DEFI_VENUES),
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
        "PINNACLE",  # Bookmaker API (ODDS_API fan-out + direct)
        "BETFAIR",  # Canonical exchange venue constant (execution/reference)
        "BETFAIR_SB_UK",  # MTDS manifest sub-venue: Betfair Sportsbook UK
        "BETFAIR_EX_UK",  # MTDS manifest sub-venue: Betfair Exchange UK
        "BETFAIR_EX_EU",  # MTDS manifest sub-venue: Betfair Exchange EU
        "DRAFTKINGS",  # US bookmaker via ODDS_API fan-out (manifest-confirmed)
        "FANDUEL",  # US bookmaker via ODDS_API fan-out (manifest-confirmed)
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
    "ohlcv_1s": True,
    "ohlcv_1m": True,
    "ohlcv_15m": True,
    "ohlcv_24h": True,
    "tbbo": True,
    # DeFi — candle-sampled types need processing; pass-through types do not
    "dex_pool_state": False,
    "dex_pool_swaps": True,
    # Bypass — periodic supply/borrow-index snapshot read raw by features-onchain
    # (aave_lending_rates / aave_utilization); no lending_ohlcv consumer exists.
    # Same class as oracle_prices / lst_rates. Do NOT re-enable without a real
    # lending_ohlcv consumer (see issue defi_code_codex_drift D3; reverts 4c98a635).
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
    "odds_horizon_bucket": True,
    "markets": False,  # Reference/lifecycle data — pass-through
    "outcomes": False,  # Settlement results — pass-through
    "settlements": False,  # Settlement records — pass-through
    # Prediction — uses canonical "trades" / "book_snapshot_5" (same keys as CeFi).
    # DeFi adapter-produced types — all pass-through (snapshot/event data).
    "utilization": False,
    "flash_loan_availability": False,
    "vault_apy": False,
    "vault_tvl": False,
    # TradFi reference types — pass-through (no candle processing needed).
    "corporate_action_confirmed": False,
    "earnings_result": False,
    "macro_result": False,
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
        "volume_analysis": "dex_pool_swaps",
        "vwap": "dex_pool_swaps",
        "candlestick_patterns": "oracle_prices",
        "market_structure": "oracle_prices",
        "returns": "oracle_prices",
        "round_numbers": "oracle_prices",
        "streaks": "oracle_prices",
        "microstructure": "dex_pool_swaps",
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


def validate_data_type_for_venue(venue: str, data_type: str, *, strict: bool = False) -> bool:
    """Check if a data type is valid for a venue.

    Returns True if the data type is in the venue's asset group's allowed data types.

    For an UNKNOWN venue (no valid set): ``strict=False`` (default) returns True
    (permissive — advisory; preserves back-compat for callers that only WARN). The
    live CAPTURE path passes ``strict=True`` -> returns False (fail-CLOSED): a venue UAC
    does not recognise cannot have a valid (venue x data_type) combo, so we must NOT
    attempt/phantom-write it (Dimension-6 guardrail vs typo'd / non-existent venues).
    """
    valid = get_valid_data_types_for_venue(venue)
    if not valid:
        return not strict  # unknown venue: permissive (advisory) by default; fail-closed when strict
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


# ---------------------------------------------------------------------------
# G1-ENUM: Instrument-shape x data_type validity matrix
# ---------------------------------------------------------------------------
# Normalises catalogue ``instrument_type`` tokens (UPPERCASE shorthand used in
# the catalogue / tests) to canonical lowercase keys before a matrix lookup.
# An enum value that is already lowercase (e.g. "spot_pair") maps to itself.
# ``valid_data_types_for_instrument_type`` is the single public accessor.
# ---------------------------------------------------------------------------

_INSTRUMENT_TYPE_ALIASES: dict[str, str] = {
    # CeFi / TradFi shorthand tokens → canonical lowercase keys
    "spot": "spot_pair",
    "spot_pair": "spot_pair",
    "perp": "perpetual",
    "perpetual": "perpetual",
    "option": "option",
    "future": "future",
    "combo": "combo",
    "etf": "etf",
    "equity": "equity",
    "index": "index",
    "bond": "bond",
    "cds": "cds",
    "event_contract": "event_contract",
    "commodity": "commodity",
    "currency": "currency",
    # Bundle-grain types
    "options_chain": "options_chain",
    "futures_chain": "futures_chain",
    # Sports catalogue tokens (SPORTS_LEAGUE_INSTRUMENT_TYPE = "league")
    "fixture": "fixture",
    "league": "league",
    "exchange_odds": "exchange_odds",
    "fixed_odds": "fixed_odds",
    "prop": "prop",
    # DeFi instrument_type values (from InstrumentType enum; already-lowercase
    # after .strip().lower() → map to themselves)
    "lending": "lending",
    "dex": "dex",
    "pool": "pool",
    "dex_pool": "dex_pool",
    "perps": "perps",
    "staking": "staking",
    "yield_bearing": "yield_bearing",
    "spot_asset": "spot_asset",
    "solana_lending": "solana_lending",
    "solana_amm_pool": "solana_amm_pool",
}


# (asset_group_lower, canonical_instrument_type) → frozenset[data_type]
# Rule: ONLY include data_types that appear in DATA_TYPES_BY_ASSET_GROUP for that AG.
# frozenset() means the instrument type is a roll-up / bundle grain with NO
# per-leaf rows → the enumerator skips it entirely (yields zero rows).
# None (returned by the accessor) means "unmapped / unknown → fall back to ALL".
VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE: dict[tuple[str, str], frozenset[str]] = {
    # ── CeFi ──────────────────────────────────────────────────────────────────
    ("cefi", "spot_pair"): frozenset({"trades", "book_snapshot_5", "ohlcv_1m"}),
    ("cefi", "perpetual"): frozenset(
        # perp_funding: periodic funding settlements emitted by CFTC-regulated crypto perp
        # venues (kalshi_perp / polymarket_perp). Added 2026-06-21 alongside the new
        # ("cefi", "perp_funding") SOURCE_PRIORITY entry. See prediction-perps-sourcing.md.
        {"trades", "book_snapshot_5", "derivative_ticker", "liquidations", "ohlcv_1m", "perp_funding"}
    ),
    ("cefi", "future"): frozenset(  # UNCERTAIN — cefi-owner verify
        {"trades", "book_snapshot_5", "derivative_ticker", "liquidations", "ohlcv_1m"}
    ),
    # Leaf options/combos → NO per-leaf rows; roll up to chain bundle grain
    ("cefi", "option"): frozenset(),
    ("cefi", "combo"): frozenset(),
    # Bundle grain (ERA-B, operator 2026-06-07): options_chain / futures_chain
    # are INSTRUMENT_TYPES (one bundle per underlying), whose market data_type is
    # ``trades`` — matching the live writer (tardis_shared.py Phase 1.6, which
    # banned the data_type/instrument_type overload) + the on-disk object paths
    # (data_type=trades) + the CEFI_OPTIONS_CHAIN_TRADES schema (symbol=underlying).
    # They are NO LONGER data_types here (the legacy data_type=options_chain rows
    # are relabeled to trades by the per-AG v8→v9 migrators, OUT OF SCOPE here).
    ("cefi", "options_chain"): frozenset({"trades"}),
    ("cefi", "futures_chain"): frozenset({"trades"}),
    # ── TradFi ────────────────────────────────────────────────────────────────
    # TradFi options/combos roll up the same way (Era-B, generalised — NOT
    # special-cased). Leaf option/combo → frozenset() (zero per-contract rows;
    # the pre-G1-ENUM None fallback over-fanned ~563K false candidates).
    # Per-underlying options_chain/futures_chain BUNDLES (T-OLD-2b, operator
    # 2026-06-08 PRESERVE decision; tradfi-owner verified vs the
    # `market-data-tick-tradfi` present-set, slot-6): admit EXACTLY the captured
    # data_types — NOT just `trades` (which marked ~12K real captured chain cells
    # "impossible"). `options_chain` carries `trades`/`ohlcv_1m` PLUS the
    # schema-backed snapshot `data_type=options_chain` itself (the mark_iv/greeks
    # chain snapshot — 291 Era-A rows migrate to instrument_type=options_chain/
    # data_type=options_chain; `*_OPTIONS_CHAIN_SNAPSHOT`). `futures_chain`
    # carries `trades`/`ohlcv_1m`/`tbbo` (the present-set shows NO snapshot
    # data_type for the futures_chain instrument_type on tradfi disk → not
    # admitted, to avoid an over-fan; cefi futures_chain DOES carry
    # data_type=options_chain → slot-3 widens that slice).
    ("tradfi", "option"): frozenset(),
    ("tradfi", "combo"): frozenset(),
    ("tradfi", "options_chain"): frozenset({"trades", "ohlcv_1m", "options_chain"}),
    ("tradfi", "futures_chain"): frozenset({"trades", "ohlcv_1m", "tbbo"}),
    # Per-contract leaves (grain=leaf; NOT bundled). tradfi-owner verified 2026-06-08 (slot-6) against the
    # `market-data-tick-tradfi` manifest present-set + the databento futures/FX market-data capability: the
    # equity corporate events (`corporate_action_confirmed`/`earnings_result`) + `macro_result` are NOT futures/FX
    # data_types — leaving these UNMAPPED (None) made FUTURE/SPOT_PAIR fall back to all 9 → the residual G1-ENUM
    # over-fan (FUTURE was 84% of the post-bundle candidate set). `future` = the etf market-data set (databento
    # derives ohlcv_1m/15m/24h + tbbo/mbp_10 for any tradeable contract); `spot_pair` (FX) = intraday + top-of-book.
    # ohlcv_1s (Databento L0/free 16y) is fetched alongside ohlcv_1m for every GLBX.MDP3 /
    # DBEQ.BASIC tradeable instrument_type; 15m/1h/24h aggregate downstream (1s+1m are the
    # only fetched OHLCV schemas). SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.
    ("tradfi", "future"): frozenset({"trades", "ohlcv_1s", "ohlcv_1m", "ohlcv_15m", "ohlcv_24h", "tbbo", "mbp_10"}),
    ("tradfi", "spot_pair"): frozenset({"trades", "ohlcv_1s", "ohlcv_1m", "ohlcv_15m", "ohlcv_24h", "tbbo"}),
    ("tradfi", "etf"): frozenset({"trades", "ohlcv_1s", "ohlcv_1m", "ohlcv_15m", "ohlcv_24h", "tbbo", "mbp_10"}),
    ("tradfi", "equity"): frozenset(
        {
            "trades",
            "ohlcv_1s",
            "ohlcv_1m",
            "ohlcv_15m",
            "ohlcv_24h",
            "tbbo",
            "mbp_10",
            "corporate_action_confirmed",
            "earnings_result",
        }
    ),
    ("tradfi", "index"): frozenset({"ohlcv_1m", "ohlcv_15m", "ohlcv_24h"}),
    ("tradfi", "bond"): frozenset({"trades", "ohlcv_24h"}),  # UNCERTAIN — tradfi-owner verify
    ("tradfi", "cds"): frozenset({"trades"}),  # UNCERTAIN — tradfi-owner verify
    # CME Globex event contracts (EC* series — ECES/ECNQ/ECGC/ECCL/ECNG/EC6E/ECBTC…) on GLBX.MDP3;
    # captured under the 3-dataset lockdown (ohlcv-1s + ohlcv-1m fetched + trades/tbbo, all on the allowlist).
    ("tradfi", "event_contract"): frozenset({"trades", "ohlcv_1s", "ohlcv_1m", "tbbo"}),
    ("tradfi", "commodity"): frozenset(  # UNCERTAIN — tradfi-owner verify
        {"trades", "ohlcv_1m", "ohlcv_24h", "tbbo", "mbp_10"}
    ),
    ("tradfi", "currency"): frozenset({"trades", "ohlcv_24h"}),  # UNCERTAIN — tradfi-owner verify
    # ── Sports (league-grain — build_instrument_catalogue.py SPORTS_LEAGUE_INSTRUMENT_TYPE = "league") ──
    # ("sports", "league") is NOT in this static dict: it is the live could-exist grain and is
    # derived dynamically from SPORTS_DATA_TYPE_TO_SOURCE in valid_data_types_for_instrument_type()
    # (slot-4 verified 2026-06-07 — the prior literal silently dropped "ODDS"). The fixture/odds rows
    # below are NOT consulted by the league-grain producer (kept as future fixture-grain scaffolding).
    ("sports", "fixture"): frozenset(
        {"odds", "odds_snapshot", "odds_movement", "markets", "outcomes", "settlements"}
    ),  # UNCERTAIN — sports-owner verify
    ("sports", "exchange_odds"): frozenset(  # UNCERTAIN — sports-owner verify
        {"odds", "odds_snapshot", "odds_movement", "trades"}
    ),
    ("sports", "fixed_odds"): frozenset(  # UNCERTAIN — sports-owner verify
        {"odds", "odds_snapshot", "odds_movement", "markets", "outcomes", "settlements"}
    ),
    ("sports", "prop"): frozenset(  # UNCERTAIN — sports-owner verify
        {"odds", "odds_snapshot", "odds_movement"}
    ),
    # ── Prediction ────────────────────────────────────────────────────────────
    # Prediction uses per-row data_type GRAIN BINDING (instr.data_type field): the
    # enumerator's _row_data_types step-1 returns [instr.data_type] and NEVER
    # consults this matrix for a grain-bound prediction catalogue row. The grain
    # guard (per-market leaf vs per-cqg bundle) lives in grain-binding, NOT here —
    # the matrix filters impossible (instrument_type x data_type) cross-products,
    # which is orthogonal to grain. The row below is therefore a DEFENSE-IN-DEPTH /
    # documentation stub (slice-parity with cefi/tradfi/sports): it only takes
    # effect for a hypothetical NON-grain-bound prediction row, where it suppresses
    # the "unmapped instrument_type → fall back to all + WARN" path. Valid set =
    # the canonical prediction data_types (DATA_TYPES_BY_ASSET_GROUP["prediction"]);
    # all are legitimately attachable to a prediction market, so this never filters
    # a real cell — it is purely WARN-suppression + an explicit, audited slice.
    ("prediction", "prediction_market"): frozenset(
        {"trades", "prediction_canonical_question_group", "market_lifecycle", "MARKET_LIFECYCLE"}
    ),
}


# ── G1-ENUM bundle-grain axis ────────────────────────────────────────────────
# Per-(asset_group, instrument_type) capture GRAIN — the second half of the
# G1-ENUM shape-aware producer (validity FILTER above + GRAIN here). It tells the
# enumerator WHETHER an instrument is captured at per-instrument LEAF grain (one
# could-exist candidate per instrument_id) or rolled UP into a per-underlying
# CHAIN BUNDLE (options_chain / futures_chain — one candidate per underlying,
# carried by the per-underlying bundle catalogue entry).
#
# How the two halves compose for an options/futures chain venue (e.g. DERIBIT),
# ERA-B (operator 2026-06-07):
#   * Leaf OPTION / COMBO entries  → ``frozenset()`` in the validity matrix →
#     ZERO per-contract candidates (they roll up into the bundle).
#   * The per-underlying ``options_chain`` / ``futures_chain`` bundle INSTRUMENT
#     entry → ``{trades}`` in the validity matrix → exactly ONE bundle candidate
#     with data_type=trades (NOT data_type=options_chain — the chain name is the
#     instrument_type, the market data_type is trades).
# Net: one candidate per underlying with data_type=trades, never one per leaf
# contract (the slot-3/slot-6 2026-06-07 over-fan: 72K OPTION + 17K COMBO leaves
# were each fanned per-contract by the pre-G1-ENUM producer).
#
# GRAIN_BUNDLE_BY_UNDERLYING is the declarative SSOT a consumer can query without
# re-deriving the rule from the validity matrix's empty-set sentinel. Default is
# LEAF for any unmapped (asset_group, instrument_type).
#
# NOTE — venue-specific FUTURE bundling (F2, slot-3 2026-06-07) is expressed via
# the ``FUTURE_BUNDLE_VENUES`` overlay below + the optional ``venue`` argument to
# ``grain_for_instrument_type`` / ``bundle_instrument_type_for_leaf``: DERIBIT/OKX
# capture FUTURE as a per-underlying ``futures_chain`` bundle (the same bulk-chain
# shape as their options_chain) while BYBIT (and any per-contract venue) capture
# each ``future`` individually (leaf). The static map below is venue-AGNOSTIC and
# holds only the universally-true rules (option/combo/options_chain/futures_chain
# bundle everywhere); FUTURE-leaf grain is resolved venue-by-venue (a venue-blind
# FUTURE bundle would over-seed BYBIT's per-contract futures, and a venue-blind
# FUTURE leaf over-seeds DERIBIT/OKX with ~700 false per-contract candidates).
# ``VENUE_DATA_TYPE_CAPABILITIES`` is NOT a sound discriminator (BYBIT lists
# ``futures_chain`` yet captures per-contract), hence the explicit allow-list.
GRAIN_LEAF = "leaf"
GRAIN_BUNDLE_BY_UNDERLYING = "bundle_by_underlying"

INSTRUMENT_GRAIN_BY_AG_AND_INSTRUMENT_TYPE: dict[tuple[str, str], str] = {
    # CeFi options/futures chains — captured per-underlying (Deribit etc.).
    ("cefi", "option"): GRAIN_BUNDLE_BY_UNDERLYING,
    ("cefi", "combo"): GRAIN_BUNDLE_BY_UNDERLYING,
    ("cefi", "options_chain"): GRAIN_BUNDLE_BY_UNDERLYING,
    ("cefi", "futures_chain"): GRAIN_BUNDLE_BY_UNDERLYING,
    # TradFi options/combos roll up the same way (generalised, NOT special-cased).
    ("tradfi", "option"): GRAIN_BUNDLE_BY_UNDERLYING,
    ("tradfi", "combo"): GRAIN_BUNDLE_BY_UNDERLYING,
    ("tradfi", "options_chain"): GRAIN_BUNDLE_BY_UNDERLYING,
    ("tradfi", "futures_chain"): GRAIN_BUNDLE_BY_UNDERLYING,
}

# Venue-aware FUTURE bundle grain (F2, slot-3/slot-7 2026-06-07). The venues whose
# bare ``future`` leaf contracts are captured as a per-underlying ``futures_chain``
# BUNDLE (bulk chain download — DERIBIT/OKX) rather than one shard per contract
# (BYBIT and every other per-contract venue). Keyed by the BASE venue token (the
# part before the first ``-``) so ``OKX`` / ``OKX-FUTURES`` / ``OKX-SWAP`` all
# resolve. The option/combo → options_chain roll-up above is universally true and
# stays venue-agnostic; only FUTURE leaf grain needs this venue overlay.
FUTURE_BUNDLE_VENUES: dict[str, frozenset[str]] = {
    "cefi": frozenset({"DERIBIT", "OKX"}),
}


def _base_venue(venue: str) -> str:
    """Base venue token (uppercased, before the first ``-``) so ``OKX-FUTURES`` /
    ``OKX-SWAP`` resolve to ``OKX``. Blank input → ``""``."""
    return venue.strip().upper().split("-", 1)[0] if venue else ""


def _future_bundles_at_venue(asset_group: str, venue: str | None) -> bool:
    """True when a bare ``future`` leaf at ``venue`` is captured as a per-underlying
    futures_chain bundle (DERIBIT/OKX) rather than per-contract (BYBIT).

    Venue ``None``/blank → False: with no venue context, keep the per-contract leaf
    default (the SAFE under-bundle — a genuine bundle venue is corrected once the
    venue is known; over-bundling would wrongly collapse BYBIT per-contract rows).
    """
    if not venue:
        return False
    return _base_venue(venue) in FUTURE_BUNDLE_VENUES.get(asset_group.lower(), frozenset())


# Which bundle INSTRUMENT_TYPE a per-contract LEAF instrument_type rolls UP into
# (ERA-B). Only the LEAF types are keyed here — the bundle TYPES themselves
# (options_chain / futures_chain) are NOT (they ARE the per-underlying bundle
# entry and pass through). The enumerator collapses every leaf contract of an
# underlying into ONE synthetic catalogue entry of this INSTRUMENT_TYPE, keyed by
# the underlying; that bundle entry's data_type is then resolved from the
# validity matrix (options_chain/futures_chain → ``trades``), so the emitted
# candidate carries data_type=trades, NOT data_type=options_chain. None ⇒ not a
# roll-up leaf (the default). ``future`` is NOT keyed here because its roll-up is
# VENUE-SPECIFIC (DERIBIT/OKX → futures_chain bundle, BYBIT per-contract leaf; F2)
# — it is resolved by the ``FUTURE_BUNDLE_VENUES`` overlay when a ``venue`` is
# passed; with no venue it stays a per-contract leaf (returns None).
BUNDLE_INSTRUMENT_TYPE_BY_AG_AND_LEAF: dict[tuple[str, str], str] = {
    ("cefi", "option"): "options_chain",
    ("cefi", "combo"): "options_chain",
    ("tradfi", "option"): "options_chain",
    ("tradfi", "combo"): "options_chain",
}


def grain_for_instrument_type(asset_group: str, instrument_type: str, venue: str | None = None) -> str:
    """Return the capture GRAIN for ``(asset_group, instrument_type[, venue])``.

    ``GRAIN_BUNDLE_BY_UNDERLYING`` — captured as a per-underlying chain bundle
    (options_chain / futures_chain); the enumerator emits ONE candidate per
    underlying, never one per leaf option/combo contract.
    ``GRAIN_LEAF`` (default) — one candidate per instrument_id.

    ``venue`` (F2) makes the FUTURE-leaf grain venue-aware: a bare ``future`` at a
    ``FUTURE_BUNDLE_VENUES`` venue (DERIBIT/OKX) is captured as a per-underlying
    futures_chain bundle → ``GRAIN_BUNDLE_BY_UNDERLYING``; at any other venue (or
    with ``venue=None``) it stays per-contract → ``GRAIN_LEAF``. The
    option/combo/options_chain/futures_chain rules are universally true and ignore
    ``venue``.

    Normalises ``instrument_type`` via the same alias map as
    :func:`valid_data_types_for_instrument_type` so catalogue UPPERCASE tokens
    (OPTION, COMBO) and canonical lowercase keys resolve identically.
    """
    normalised = instrument_type.strip().lower() if instrument_type else ""
    normalised = _INSTRUMENT_TYPE_ALIASES.get(normalised, normalised)
    static = INSTRUMENT_GRAIN_BY_AG_AND_INSTRUMENT_TYPE.get((asset_group.lower(), normalised))
    if static is not None:
        return static
    # Venue-aware FUTURE overlay (F2): FUTURE bundles per-underlying only at
    # DERIBIT/OKX; elsewhere (BYBIT) + venue-unknown it stays a per-contract leaf.
    if normalised == "future" and _future_bundles_at_venue(asset_group, venue):
        return GRAIN_BUNDLE_BY_UNDERLYING
    return GRAIN_LEAF


def bundle_instrument_type_for_leaf(asset_group: str, instrument_type: str, venue: str | None = None) -> str | None:
    """Return the bundle INSTRUMENT_TYPE a LEAF instrument_type rolls up into (ERA-B).

    ``("cefi"|"tradfi", "option"|"combo")`` → ``"options_chain"`` (the per-contract
    leaves collapse into ONE per-underlying ``options_chain`` bundle entry). A bare
    ``("cefi", "future")`` leaf at a ``FUTURE_BUNDLE_VENUES`` venue (DERIBIT/OKX) →
    ``"futures_chain"`` (F2 venue overlay); at any other venue (or ``venue=None``)
    it returns None (per-contract leaf, no roll-up). The bundle TYPES themselves
    (``options_chain`` / ``futures_chain``) return None — they are already the
    per-underlying bundle entry and are enumerated as-is. The returned value is the
    bundle's INSTRUMENT_TYPE; its data_type is resolved separately via
    :func:`valid_data_types_for_instrument_type` (→ ``trades``), so the rolled-up
    candidate carries data_type=trades (Era-B), never data_type=options_chain. Used
    by the ``enumerate_expected_universe`` bundle-grain roll-up.
    """
    normalised = instrument_type.strip().lower() if instrument_type else ""
    normalised = _INSTRUMENT_TYPE_ALIASES.get(normalised, normalised)
    static = BUNDLE_INSTRUMENT_TYPE_BY_AG_AND_LEAF.get((asset_group.lower(), normalised))
    if static is not None:
        return static
    # Venue-aware FUTURE overlay (F2): a FUTURE leaf at DERIBIT/OKX rolls up to a
    # per-underlying futures_chain bundle; at BYBIT (+ venue-unknown) it stays leaf.
    if normalised == "future" and _future_bundles_at_venue(asset_group, venue):
        return "futures_chain"
    return None


# Module-level cache for the lazily-built DeFi sub-dict.
_defi_valid_data_types: dict[str, frozenset[str]] | None = None

# Module-level cache for the lazily-built sports league valid-set. Derived from
# ``SPORTS_DATA_TYPE_TO_SOURCE`` (the reference-data provider data_types) rather
# than a hand-written literal — a literal had silently dropped ``ODDS`` (it is a
# SPORTS_DATA_TYPE_TO_SOURCE key AND a DATA_TYPES_BY_ASSET_GROUP["sports"] member,
# so it failed both arms of the _row_data_types filter). Deriving keeps it in sync.
_sports_league_valid_data_types: frozenset[str] | None = None


def valid_data_types_for_instrument_type(asset_group: str, instrument_type: str) -> frozenset[str] | None:
    """Return the valid data_types for ``(asset_group, instrument_type)``.

    Normalises ``instrument_type`` via ``_INSTRUMENT_TYPE_ALIASES`` (strip +
    lower, then alias; unknown → the stripped-lower form) so both catalogue
    UPPERCASE tokens (SPOT, PERP) and canonical lowercase keys (spot_pair,
    perpetual) resolve correctly.

    Returns:
        frozenset[str]  — the valid data_types (may be empty → skip all rows).
        None            — unmapped entry → caller should fall back to ALL
                          data_types and log a warning.

    DeFi derivation: lazily built from ``PROTOCOL_CAPABILITIES`` (imported
    inside the function to avoid import cycles); maps each
    ``cap.instrument_type`` → union of ``cap.data_types`` across all protocols
    that use that instrument type.  Cache is module-level.
    """
    global _defi_valid_data_types, _sports_league_valid_data_types

    # Normalise instrument_type token.
    normalised = instrument_type.strip().lower() if instrument_type else ""
    normalised = _INSTRUMENT_TYPE_ALIASES.get(normalised, normalised)

    if asset_group.lower() == "sports" and normalised == "league":
        # League is the canonical sports could-exist grain (build_sports_catalogue_dataframe
        # → instrument_type="league"). Its valid data_types ARE the reference-data provider
        # data_types (SPORTS_DATA_TYPE_TO_SOURCE keys: MATCHES/ODDS/STANDINGS/FIXTURES/XG/…),
        # NOT the MTDS odds market-data types. Derived (not literal) so a future
        # SPORTS_DATA_TYPE_TO_SOURCE addition can never silently drop out of the could-exist seed.
        if _sports_league_valid_data_types is None:
            from unified_api_contracts.canonical.domain.sports import (  # noqa: imports-inside-functions
                SPORTS_DATA_TYPE_TO_SOURCE,
            )

            _sports_league_valid_data_types = frozenset(SPORTS_DATA_TYPE_TO_SOURCE)
        return _sports_league_valid_data_types

    if asset_group.lower() == "defi":
        if _defi_valid_data_types is None:
            from .capability_declarations._defi import PROTOCOL_CAPABILITIES  # noqa: imports-inside-functions

            defi: dict[str, set[str]] = {}
            for cap in PROTOCOL_CAPABILITIES.values():
                for it in cap.instrument_types:
                    it_key = it.strip().lower()
                    it_key = _INSTRUMENT_TYPE_ALIASES.get(it_key, it_key)
                    defi.setdefault(it_key, set()).update(cap.data_types)
            _defi_valid_data_types = {k: frozenset(v) for k, v in defi.items()}
        return _defi_valid_data_types.get(normalised)  # None if unmapped

    return VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE.get((asset_group.lower(), normalised))


def valid_data_types_for_venue_instrument_type(
    asset_group: str, venue: str | None, instrument_type: str
) -> frozenset[str] | None:
    """Per-``(venue, instrument_type)`` valid data_types — DeFi protocol-grain.

    :func:`valid_data_types_for_instrument_type` builds the DeFi validity set as
    the UNION across every protocol that declares an instrument_type, so a
    hybrid protocol's data_types leak to every instrument of that type — e.g.
    GMX declares both ``pool`` and ``perp_funding`` → ``perp_funding`` reads as
    valid for ALL pools incl. Uniswap → residual false ``expected_unattempted``
    for non-GMX pools.

    This narrows DeFi validity to the SPECIFIC protocol named by ``venue`` (the
    ``PROTOCOL`` segment of the canonical ``PROTOCOL-CHAIN`` id, e.g.
    ``UNISWAP_V3-ETHEREUM`` → ``uniswap_v3``): it returns ONLY that protocol's
    declared data_types. For every NON-DeFi asset_group, a missing ``venue``, an
    unmapped protocol, OR an instrument_type the protocol does not declare, it
    DELEGATES to :func:`valid_data_types_for_instrument_type` — i.e. it only ever
    narrows in the clearly-safe case and never under-reports a real cell.

    Returns:
        frozenset[str] — the valid data_types (narrowed for a known DeFi protocol).
        None           — unmapped (delegated) → caller falls back to ALL.
    """
    if asset_group.lower() != "defi" or not venue:
        return valid_data_types_for_instrument_type(asset_group, instrument_type)

    from .capability_declarations._defi import PROTOCOL_CAPABILITIES  # noqa: imports-inside-functions

    # Venue id is ``PROTOCOL-CHAIN``; the protocol segment keys PROTOCOL_CAPABILITIES.
    protocol = venue.split("-", 1)[0].strip().lower()
    cap = PROTOCOL_CAPABILITIES.get(protocol)
    if cap is None:
        # Belt-and-suspenders: match on the declared ``venue_prefix`` too.
        for candidate in PROTOCOL_CAPABILITIES.values():
            if candidate.venue_prefix.strip().lower() == protocol:
                cap = candidate
                break
    if cap is None:
        # Unmapped protocol → preserve the union behaviour (no regression).
        return valid_data_types_for_instrument_type(asset_group, instrument_type)

    normalised_it = instrument_type.strip().lower() if instrument_type else ""
    normalised_it = _INSTRUMENT_TYPE_ALIASES.get(normalised_it, normalised_it)
    cap_its = {_INSTRUMENT_TYPE_ALIASES.get(_it.strip().lower(), _it.strip().lower()) for _it in cap.instrument_types}
    if normalised_it not in cap_its:
        # The protocol does not declare this instrument_type → fall back to the
        # union rather than risk dropping a real cell on an incomplete cap.
        return valid_data_types_for_instrument_type(asset_group, instrument_type)
    return frozenset(cap.data_types)


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
    # REST, ~30-day rolling depth) are wired in _fetch_aster_rest. Genesis =
    # 2023-07-22 (operator-confirmed 2026-06-17 via the Astherus pre-rebrand
    # venue). book_snapshot_5 + liquidations both out of scope (no wired fetch
    # path). perp_funding: collected by perp_funding_handler (declared in
    # _defi.py _ProtocolCapability data_types=["perp_funding"]).
    # IMPORTANT — pre-2024 Aster funding is BINANCE-PROXIED (Astherus pre-rebrand
    # mirrored Binance funding); it is imported, NOT Aster-native — label `source`
    # honestly. SSOT: perp_funding_data_semantics_and_cadence_2026_06_16.md §GAP 2.
    "ASTER": {
        "trades": "2023-07-22",
        "derivative_ticker": "2023-07-22",
        "perp_funding": "2023-07-22",  # perp_funding_handler REST Aster API
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
        "ohlcv_1s": "2023-04-15",  # DBEQ.BASIC serves equity 1s (L0/free); operator 2026-06-21 in-scope
    },
    "NYSE": {
        "ohlcv_1m": "2023-04-15",
        "ohlcv_1s": "2023-04-15",  # DBEQ.BASIC serves equity 1s (L0/free); operator 2026-06-21 in-scope
    },
    "CME": {
        # ohlcv-1s + ohlcv-1m are BOTH fetched from Databento GLBX.MDP3 (both
        # L0/free 16y) — 1m completes the existing corpus, 1s is the finer add;
        # 15m/24h are aggregated downstream. SSOT:
        # codex/02-data/tradfi-databento-sourcing-ssot.md + the lockdown plan.
        "ohlcv_1s": "2019-01-01",
        "ohlcv_1m": "2019-01-01",
    },
    "ICE": {
        "ohlcv_1m": "2019-01-01",
    },
    "CBOE": {
        "ohlcv_15m": "2020-01-07",  # VIX cash INDEX — Barchart/Yahoo (not Databento)
        # VX FUTURES (the VIX futures curve) via Databento XCBF.PITCH (the
        # operator's "CFE" subscription, activated 2026-06-19). Both ohlcv-1s +
        # ohlcv-1m are L0/free 16y; coarser bars aggregate downstream. XCBF.PITCH
        # coverage starts 2018-11-04. NOTE: these are the FUTURES, distinct from
        # the ohlcv_15m VIX cash index above. SSOT:
        # codex/02-data/tradfi-databento-sourcing-ssot.md.
        "ohlcv_1s": "2018-11-04",
        "ohlcv_1m": "2018-11-04",
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
    # ── TradFi reference data venues (canonicalized 2026-05-23) ──
    "POLYGON": {
        "corporate_action_confirmed": "2020-01-01",
        "earnings_result": "2020-01-01",
    },
    "FRED": {
        "macro_result": "2010-01-01",
    },
    # ── DeFi — multi-chain entries live in defi_venue_capabilities.py and
    # are merged into this dict at module-load time (see below). Split out
    # to keep this file under the 900-line QG ceiling.
    # ── Sports ──
    # Corrected 2026-05-20 (mega-audit R2): ODDS_API emits "ODDS" (uppercase),
    # bookmaker venues emit "trades". Old data_types (odds_snapshot, odds_movement)
    # were the oracle bug root cause (25,652 MISSING_EXPECTED).
    "ODDS_API": {
        "ODDS": "2024-01-01",  # canonical uppercase per mega-audit R2 correction
        "odds": "2024-01-01",
        "odds_snapshot": "2024-01-01",
        "odds_movement": "2024-01-01",
        "arbitrage_opportunity": "2024-01-01",
        "odds_horizon_bucket": "2024-01-01",
        "markets": "2024-01-01",
        "outcomes": "2024-01-01",
        "settlements": "2024-01-01",
    },
    "PINNACLE": {
        "odds_snapshot": "2024-01-01",
        "odds_movement": "2024-01-01",
        "markets": "2024-01-01",
        "outcomes": "2024-01-01",
        "settlements": "2024-01-01",
    },
    "BETFAIR": {
        "odds_snapshot": "2024-01-01",
        "odds_movement": "2024-01-01",
        "markets": "2024-01-01",
        "outcomes": "2024-01-01",
        "settlements": "2024-01-01",
    },
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
# Placed after conditional setup to avoid circular import at load time.
from unified_api_contracts.registry.defi_prediction_instrument_seeds import (
    seed_for_venue_and_data_type,
)
from unified_api_contracts.registry.defi_venue_capabilities import (
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
    from .venue_mapping import VenueMapping  # noqa: imports-inside-functions

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
        # TradFi + CeFi DEX OHLCV (Phase 3.D.5 v2 enumerator — per-equity-ticker
        # and per-pool denominator; TradFi catalog reader provides equity tickers,
        # CeFi catalog reader provides DEX pool instrument IDs for LIGHTER/PACIFICA).
        # ohlcv_1s shares the SAME per-instrument shard grain as ohlcv_1m (TradFi
        # Databento 1s fetch) — same shard-key, denominator and Tier-3 fan-out.
        "ohlcv_1s",
        "ohlcv_1m",
        # DEFI per-pool / per-market / per-asset shards
        "dex_pool_swaps",
        "dex_pool_state",
        "lending_indices",
        "oracle_prices",
        "lst_rates",
        "rewards",
        "risk_params",
        # PREDICTION — uses canonical "trades" (retired prediction_* names 2026-04-19)
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
        ``AAVE_V3-ETHEREUM`` …) as used by ``VenueMapping``.
    data_type:
        Canonical MTDS data_type (``trades``, ``book_snapshot_5``,
        ``dex_pool_swaps`` …).
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
    # ohlcv_1m is per-instrument (Phase 3.D.5 v2). Per-instrument universe is
    # always provided by a catalog reader (TradFiCatalogReader for equity
    # tickers; CeFiCatalogReader for DEX pools on LIGHTER/PACIFICA). When no
    # catalog reader is registered for a venue, return () so Tier-3 degrades
    # to Tier-2 — same as today's behaviour (no regression on first-boot or
    # test environments where the catalog is absent).
    if data_type == "ohlcv_1m":
        return ()

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

    # DEFI per-instrument dts (dex_pool_state / dex_pool_swaps / lending_indices /
    # oracle_prices / lst_rates / rewards / risk_params) + PREDICTION
    # legacy `prediction_trades` / `prediction_book_snapshot` /
    # `prediction_market_metadata` — delegated to the Wave 8G seed module.
    return seed_for_venue_and_data_type(venue, data_type)
