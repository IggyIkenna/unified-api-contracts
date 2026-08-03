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
from unified_api_contracts.registry.defi_venues import DEFI_VENUE_PHASE as _DEFI_VENUE_PHASE

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
        # 2026-05-07: ohlcv_1m for DEX venues (Lighter /candles). Lighter zkSync
        # per-trade /recentTrades is hard-capped at last ~100 trades with no
        # cursor, so /candles OHLCV bars are the only historical-capable path.
        # (Pacifica /kline was the same shape — Pacifica removed 2026-07-16,
        # operator ruling.) Tardis CeFi venues do not expose OHLCV bars —
        # their adapters return empty for ohlcv_1m, which the manifest
        # records as empty_confirmed (honest absence per workspace "honest
        # absence vs fake placeholders" rule).
        "ohlcv_1m",
        # 2026-06-21: periodic funding settlements for CFTC-regulated crypto perp venues.
        # kalshi_perp (launched 2026-05-29) + polymarket_perp (launched 2026-04-21) expose
        # a dedicated /markets/{ticker}/funding_rates REST endpoint (cursor-paginated,
        # public-read). Source priority: ("cefi", "perp_funding"). SSOT: prediction-perps-sourcing.md.
        "perp_funding",
        # volatility_index — DERIBIT captures real PROD data (DVOL implied-vol index,
        # public REST /public/get_volatility_index_data, already a live DataTypeCapability
        # and SOURCE_PRIORITY[("cefi", "volatility_index")] entry) but this enumeration
        # list omitted it, leaving any consumer that enumerates from
        # DATA_TYPES_BY_ASSET_GROUP directly (e.g. expected_universe._expected_generic,
        # the data-status Axis Value Census) blind to the cell — same class of
        # enumeration-blind-spot bug as the OKX-FUTURES/OKX-SWAP fix above. SSOT:
        # cefi_shard_enumeration_blindspots_and_canonical_fetch_dependency_2026_07_18.md.
        "volatility_index",
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
        # "macro_result" was declared as FRED's data_type here, but the live
        # ``FredAdapter.write_canonical_shard`` has never written it — it writes
        # ``yield_curve``/``ohlcv_1d`` (below), already the SSOT MTDS's local
        # ``tradfi_shared.TRADFI_DATA_TYPES`` legalizes and features-service's
        # ``mtds_fred_reader.py`` (shipped 2026-07-27) already reads. Kept
        # (not deleted) — legacy manifest rows may still carry it from a
        # different Databento-sourced producer; only the FRED attribution was
        # wrong. Found + corrected 2026-07-29 scoping FRED's backfill invocation
        # (unified-trading-pm/plans/active/issues/macro_micro_econ_data_capture_audit_2026_06_05.md).
        "macro_result",  # Macro economic results — legacy data_type, NOT written by FredAdapter
        "yield_curve",  # FRED: BOND-classified series (Treasury yields, TIPS, rates, spreads, credit)
        "ohlcv_1d",  # FRED: INDEX-classified series, degenerate 1-obs/day bar (VIXCLS, CPI, GDP, UNRATE, …)
    ],
    "defi": [
        "dex_pool_state",  # DEX pool metrics (TVL, liquidity depth)
        "dex_pool_swaps",  # DEX swap events (requires candle sampling)
        "lending_indices",  # Lending rate indices (supply/borrow APY, utilization)
        "liquidations",  # DeFi liquidation events
        # Perpetual funding rates for defi-asset-group perp DEXes. HYPERLIQUID/
        # ASTER/LIGHTER-ZKSYNC are NOT covered by this entry — they are
        # cefi-asset-group venues (VENUES_BY_ASSET_GROUP["cefi"], "On-chain
        # CLOBs reclassified from DEFI" below); their perp_funding scope is the
        # "cefi" list's own entry. ASTER/LIGHTER-ZKSYNC's standalone
        # perp_funding stays RETIRED (code-proven byte-identical to
        # derivative_ticker); HYPERLIQUID's was RESTORED 2026-07-30 (disproven
        # byte-identical — see VENUE_DATA_TYPE_CAPABILITIES["HYPERLIQUID"]
        # below). (DRIFT/PACIFICA (Solana) + GMX (Arbitrum/Avalanche) were
        # defi-asset-group perp venues this entry originally covered; all
        # removed — DRIFT/PACIFICA 2026-07-16 (operator ruling: all Solana perp
        # DEXes dropped except Jupiter, not integrated), GMX 2026-07-25
        # (unreliable historical funding data — see
        # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).)
        "perp_funding",
        # derivative_ticker (2026-07-15, defi_perp_funding_canonicalisation_derivative_
        # ticker_all_perps issue, operator ruling): the canonical RAW-funding home for
        # ALL perp venues, defi-asset-group ones included — captured at the
        # highest resolution each source offers, even when the source has no OI. Was
        # previously declared only under "cefi" (where HYPERLIQUID/ASTER/
        # EXTENDED-STARKNET/LIGHTER-ZKSYNC already emit it, despite their DeFi
        # on-chain settlement — those stay cefi-asset-group per
        # VENUES_BY_ASSET_GROUP's "on-chain CLOBs reclassified from DEFI" note above).
        "derivative_ticker",
        # Per-trade prints for on-chain perp venues. Schema existed
        # (DataType.PERP_TRADES, DEFI_PERPETUAL_PERP_TRADES contract) and the
        # MTDS writer already handles it; this enumeration entry was the
        # missing piece blocking expected_unattempted catalog seeding for the
        # data_type. (The Drift V2 historical ingester that originally
        # motivated this entry was removed 2026-07-16 along with the rest of
        # the Drift venue — operator ruling.)
        "perp_trades",
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
        # ── MDPS Phase-5b.1 processed-candle data_types (2026-08-02) ──
        # DefiSwapAdapter-produced OHLCV candles derived from dex_pool_swaps raw
        # ticks, co-located under processed_candles/ (see
        # internal/schemas/_candle_contracts.py). Mirrors the analogous cefi
        # "ohlcv_1m"/tradfi "ohlcv_1s" MDPS candle keys already present in their
        # own asset_group lists above. instruments-service's
        # enumerate_expected_universe.py excludes these from the MTDS raw-tick
        # manifest's expected-universe seeding via a dedicated
        # _DEFI_MTDS_TICK_MANIFEST_EXCLUDED_DATA_TYPES guard (mirroring the
        # tradfi corporate_action_confirmed/earnings_result exclusion) — the
        # real capture pipeline for these 7 keys is MDPS, not MTDS, so seeding
        # them into the MTDS tick manifest without that guard would create a
        # permanently-unsatisfiable expected_unattempted/attempted_failed cell.
        # See unified-trading-pm/plans/active/issues/
        # defi_swaps_ohlcv_candle_data_types_axis_gap_2026_07_22.md.
        "swaps_ohlcv_15s",
        "swaps_ohlcv_1m",
        "swaps_ohlcv_5m",
        "swaps_ohlcv_15m",
        "swaps_ohlcv_1h",
        "swaps_ohlcv_4h",
        "swaps_ohlcv_1d",
    ],
    "sports": [
        "odds",  # Raw bookmaker odds from Odds API (MTDS raw tick data)
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
        # NOTE: "TRADES" (uppercase) briefly existed here 2026-07-23..2026-07-27 (K1,
        # mtds@2536b91c) as a "canonical uppercase form" — REVERTED: the 2026-07-23
        # reconciliation (sports_consolidated_closeout_2026_07_19.md) decided sports
        # data_type/instrument_type is lower-case for the whole vocabulary, no UPPER
        # exception. Do not re-add without re-opening that decision.
        # 2026-07-17 (operator ruling OR-5b(c), sports legacy-bucket cutover): POST-KICKOFF
        # ("in-play") bookmaker quotes recovered from the legacy MDT bucket, kept as a
        # population DISTINCT from pre-match ``trades`` so the observations survive the
        # legacy-bucket delete without contaminating the pre-match T-0 horizon path.
        # Discriminator at write time: ``bm_minutes_to_kickoff < 0``.
        #
        # Three deliberate NON-registrations keep this inert for the LIVE sports fleet —
        # do NOT "complete" them without re-measuring, they are the safety design:
        #   1. NOT in ``SPORTS_DATA_TYPE_TO_SOURCE`` — that (not this dict) is the axis the
        #      v2 expected-universe enumerator iterates for sports
        #      (``instruments-service/scripts/enumerate_expected_universe.py::_sports_data_types``).
        #      Adding it there would mint ``expected_unattempted`` rows across every sports
        #      instrument x date — the flood this exclusion exists to prevent.
        #   2. NO ``AVAILABILITY_AT_SEMANTICS`` entry — mirrors ``("sports","trades")``, which
        #      also has none. Registering one would switch the availability gate ON for the
        #      live MDT sports fleet (the hazard @57bcc7c5 refused for PLAYER_STATS).
        #   3. NOT in ``total_universe`` — that enumerates data_types for cefi/defi/tradfi only.
        # Readers are filename-scoped too: the quarantined objects are written as
        # ``inplay_ticks.parquet`` (never ``ticks.parquet``), because
        # ``reprocess_sports_odds.py::_is_consumable_trades_blob`` matches on FILENAME alone.
        "trades_inplay",
    ],
    "prediction": [
        # Canonical names — aligned with CeFi. Legacy prediction_* names retired
        # 2026-04-19. book_snapshot_5 RE-ADDED 2026-06-23: the "re-add if/when a
        # prediction adapter starts emitting book snapshots" condition is now MET —
        # BOTH venues emit book_snapshot_5 (LIVE via polymarket_clob_ws/kalshi_clob_ws
        # top-5 ladder; BATCH via polymarket_adapter REST /book, mtds@7c849d7). It is
        # an instrument-day-grain depth snapshot (same grain as trades), in scope for
        # both POLYMARKET + KALSHI (expected_coverage._PREDICTION).
        "trades",
        "book_snapshot_5",
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

# @contract-surface — a removed asset_group key or a removed venue from a group's list
# is a cross-repo contract break (downstream consumers, e.g. instruments-service
# build_expected(), enumerate this dict to materialise the expected coverage universe —
# plans/active/issues/breaking_change_differ_blind_to_registry_data_dicts_2026_07_09.md).
# Adding a key/member stays non-breaking.
# Venues per asset group
VENUES_BY_ASSET_GROUP: dict[str, list[str]] = {
    "cefi": [
        # Centralized exchanges (Tardis API)
        "BINANCE-SPOT",
        "BINANCE-FUTURES",
        # Binance COIN-M (inverse/delivery) perps + dated futures. Distinct endpoint
        # from BINANCE-FUTURES (USDT-M linear). cefi_universe_capture_rule 2026-06-24.
        "BINANCE-DELIVERY",
        "BYBIT",
        "OKX",
        # OKX-SPOT declared its own distinct cefi venue (Option A,
        # 2026-07-10 operator decision — mirrors the BYBIT-SPOT precedent
        # below): bare "OKX" has ZERO real SPOT_PAIR captures in production
        # (confirmed via a direct GCS availability_index read,
        # unified-api-contracts@23fa3a99) — Tardis's own routing table
        # already sends (OKX, SPOT_PAIR) to the same "okex" source as
        # canonical OKX-SPOT, so the bare-OKX capability was a redundant
        # alias, not a distinct real capability. Declaring OKX-SPOT here
        # (instead of relying on instruments-service's _CEFI_VENUE_FOLD to
        # fold captured OKX-SPOT rows up to bare "OKX") makes the real
        # captured OKX spot data visible to Layer-1/Layer-2 honest-coverage
        # directly, matching BYBIT/BYBIT-SPOT's shape. SSOT:
        # unified-trading-pm/plans/active/issues/
        # instruments_service_cefi_qg_red_on_ldr_head_2026_07_08.md,
        # cefi_layer1_denominator_gaps_2026_07_03.md.
        "OKX-SPOT",
        # OKX-FUTURES / OKX-SWAP declared their own distinct cefi venues (2026-07-21,
        # mirrors the OKX-SPOT precedent above): both are real, actively-captured
        # venues in production (119,706 and 423,313 captured manifest rows
        # respectively) but were wholly absent from this list — only bare "OKX" and
        # "OKX-SPOT" were declared. canonical_mappings.py already carries the
        # wire-alias mappings for both ("okex-swap": "OKX-SWAP",
        # "okex-futures": "OKX-FUTURES") plus their own VENUE_TO_DATA_SOURCE entries, so
        # these were already real, recognized canonical vocabulary elsewhere — this
        # list alone was out of sync. Omitting them here previously left
        # expected_universe._expected_generic("cefi") (which iterates THIS list, not
        # canonical_mappings.py's keys) blind to their entire expected-capture set,
        # AND left deployment-api's data-status Axis Value Census
        # (_distinct_values.py::_canonical_set() reads VENUES_BY_ASSET_GROUP.get(ag,
        # []) directly, no separate hardcoded venue set) badging real captured OKX
        # futures/swap rows as "non-canonical" — a false-positive drift alarm (the
        # exact D2a-class regression the COINBASE-SPOT comment below documents).
        "OKX-FUTURES",
        "OKX-SWAP",
        "DERIBIT",
        "UPBIT",
        # RE-KEYED from bare "COINBASE" (coinbase_bare_name_migration_2026_07_06.md
        # S3, 2026-07-10). Real bug found during execution: this list had NO
        # separate "COINBASE-SPOT" entry — INSTRUMENT_TYPES_BY_VENUE's
        # COINBASE_SPOT key was declared but unreachable because
        # expected_universe._expected_generic("cefi") iterates THIS list
        # (VENUES_BY_ASSET_GROUP.get(ag, [])), not INSTRUMENT_TYPES_BY_VENUE's
        # keys directly. Deleting bare COINBASE without adding this entry would
        # have silently zeroed COINBASE's entire cefi EXPECTED set — exactly
        # the D2a regression the migration plan exists to prevent.
        "COINBASE-SPOT",
        # 2026-06-23: Bybit spot + Coinbase Derivatives (perps) as DISTINCT
        # canonical venues so the perp-gate pairs BYBIT-SPOT↔BYBIT perps and
        # COINBASE-SPOT↔COINBASE-FUTURES (cefi_universe_capture_rule).
        "BYBIT-SPOT",
        "COINBASE-FUTURES",
        # Coinbase Derivatives Exchange (CDE) — 2026-07-10, COINBASE-FUTURES/#3-vs-#8
        # resolution. Real dated futures + far-dated "nano perpetual" contracts, zero
        # Tardis coverage under any name — native Advanced Trade REST source (see
        # venue_adapter_keys.py "coinbase_cde"). SEPARATE product from COINBASE-FUTURES
        # (Coinbase INTX). SSOT: unified-trading-pm/plans/active/issues/
        # instruments_remaining_work_audit_2026_07_10.md Progress Log.
        "COINBASE-CDE",
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
        # PACIFICA (Solana) removed 2026-07-16 (operator ruling: all Solana perp
        # DEXes dropped except Jupiter, not integrated). SSOT: unified-
        # trading-pm/codex/04-architecture/solana-defi-coverage.md.
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
        "CBOE",  # Cboe Futures Exchange (CFE) — VX / VIX futures (Databento XCBF.PITCH)
        "KRX",  # Korea Exchange — single stocks via Yahoo Finance (.KS tickers), source=yahoo
        # External data providers
        "FX",  # FX rates (KRW/USD via Yahoo Finance data provider)
        # FRED (Federal Reserve Economic Data) — macro rates/curve/inflation series,
        # source=fred (FRED REST API, no Databento analog). Added 2026-07-29: the
        # adapter (market_interface/adapters/tradfi/fred_adapter.py) existed but was
        # never in this list, so VENUE_TO_ASSET_GROUP had no entry for it and
        # validate_data_type_for_venue("FRED", ...) always failed. See
        # VENUE_DATA_TYPE_CAPABILITIES["FRED"] below for its data_types.
        "FRED",
        # NOTE: BARCHART removed 2026-06-24 (VIX 15m now aggregates from VX futures
        # via Databento XCBF.PITCH — Barchart CSV preload retired).
        # YAHOO_FINANCE removed 2026-07-15: legacy source-as-venue artifact, NOT a real
        # venue — real Yahoo-sourced rows land under REAL venues (DXY→ICE, KRW/USD→FX,
        # treasuries→CBOE) with source=yahoo (see data_source_continuity.py). No fetch
        # code ever stamps venue=YAHOO_FINANCE. Do NOT re-add it here: enumerating a
        # source-as-venue with no caps re-arms the get_expected_data_types_for_venue
        # empty-caps→all-asset-group-types fallback (documented on that function).
    ],
    # Honest-coverage denominator: only IS-producible venues (phase=="live").
    # _ALL_DEFI_VENUES is the full registry (unchanged); _DEFI_VENUE_PHASE gates
    # which venues count as "could-exist" for honest-coverage purposes.
    # dict.fromkeys dedups while preserving order (ALL_DEFI_VENUES has duplicates
    # from the extend() block for alias coverage testing).
    # Denominator semantics owned by plans/active/honest_coverage_v2_instrument_denominator_2026_06_28.md
    # (check_enumeration_completeness.py) — do NOT edit that script here.
    "defi": list(dict.fromkeys(v for v in _ALL_DEFI_VENUES if _DEFI_VENUE_PHASE.get(v) == "live")),
    "sports": [
        # Sports betting exchanges and bookmakers active in the May-23 universe.
        #
        # DEFERRED-INDEFINITELY 2026-05-12 per operator: SCRAPER bookmakers are out
        # of the active venue universe; their venue constants + capability flags +
        # execution adapter stubs remain as future-work scaffolding. See
        # `unified-trading-pm/plans/epics/sports_master.md` §
        # "Scrapers DEFERRED-INDEFINITELY 2026-05-12 per operator".
        #
        # ── 2026-07-20 addition REVERTED 2026-07-22 (operator, same plan,
        # "Operator decisions — RULED 2026-07-22" § "Sports ODDS_API bookmakers"):
        # "do NOT add them, in fact remove them everywhere so they don't come up
        # in audit" — a stronger reversal of the 2026-07-20 add-to-registry fix
        # below. The 20 ODDS_API fan-out bookmakers (BETMGM/BETONLINEAG/
        # BETOPENLY/BETRIVERS/BETSSON/BETVICTOR/BETWAY/BOVADA/CASUMO/CORAL/
        # LIVESCOREBET/MATCHBOOK/NOVIG/ONEXBET/PADDYPOWER/PROPHETX/SKYBET/UNIBET/
        # VIRGINBET/WILLIAMHILL) are REMOVED from this canonical set again — the
        # 2026-05-12 scraper-deferral decision (above) is UNCHANGED, this is
        # purely about whether the registry treats them as canonical/expected.
        # They are STILL real manifest values (ODDS_API fan-out genuinely writes
        # venue=BETMGM etc.), so simply removing them here would reopen the exact
        # non-canonical-value audit finding the 2026-07-20 addition existed to
        # silence — see `SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS` below,
        # which the distinct-values detector (deployment-api::_distinct_values.py)
        # reads to exclude these specific values from its findings WITHOUT
        # badging them canonical.
        "ODDS_API",  # Multi-bookmaker odds aggregator (raw tick data source)
        "PINNACLE",  # Bookmaker API (ODDS_API fan-out + direct)
        "BETFAIR",  # Canonical exchange venue constant (execution/reference)
        "BETFAIR_SB_UK",  # MTDS manifest sub-venue: Betfair Sportsbook UK
        "BETFAIR_EX_UK",  # MTDS manifest sub-venue: Betfair Exchange UK
        "BETFAIR_EX_EU",  # MTDS manifest sub-venue: Betfair Exchange EU
        "DRAFTKINGS",  # US bookmaker via ODDS_API fan-out (manifest-confirmed)
        "FANDUEL",  # US bookmaker via ODDS_API fan-out (manifest-confirmed)
        # Added 2026-07-30 (distinct-values census review, sports_consolidated_native_ao_
        # extract_2026_07_25.md Track C + sports_distinct_values_registry_cleanup_2026_07_30.md):
        # real VenueConstant already existed for all 3 below, just never added here.
        # NOTE: FOOTYSTATS is deliberately NOT here — see SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS
        # below (two-registry-model collision with IS's own FOOTYSTATS reference-data-provider venue,
        # ldr_qg_failure escalation agt-57430c 2026-07-30).
        "LADBROKES",  # ODDS_API fan-out bookmaker; fold target of SPORTS_VENUE_FOLD
        # ("ladbrokes_uk" wire spelling); raw-tick shape re-stamped + GCS-verified 2026-07-27/30.
        "BET888SPORT",  # ODDS_API fan-out bookmaker; fold target of SPORTS_VENUE_FOLD
        # ("sport888" wire spelling); raw-tick shape re-stamped + GCS-verified 2026-07-27/30.
        "SMARKETS",  # UK betting exchange, ODDS_API fan-out — confirmed live production
        # data (1.1M+ rows through 2026-07-26, GCS-path-clean); was missing a VenueConstant
        # entirely (see venue_constants.py) — see sports_consolidated_native_ao_extract_
        # 2026_07_25.md's explicit "SMARKETS is NOT stale/deleted-venue residue" correction.
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

# The 20 ODDS_API fan-out bookmakers reverted out of VENUES_BY_ASSET_GROUP
# ["sports"] above (operator ruling 2026-07-22,
# `plans/active/distinct_values_noncanonical_audit_2026_07_20.md`), PLUS 2 added
# 2026-07-27 (UNIBET_EU/UNIBET_UK — see the SPORTS_VENUE_FOLD comment above for
# why these are here as their OWN accepted entries rather than folded into bare
# UNIBET: live content comparison proved them genuinely distinct bookmaker feeds,
# not a casing/alias duplicate of it). They are
# deliberately NOT canonical (do NOT add to any canonical venue list — the
# 2026-05-12 scraper-deferral decision stands, no per-bookmaker capture
# adapter exists or is planned) but ARE real raw manifest values (the
# ODDS_API fan-out genuinely writes venue=BETMGM etc.), so a plain removal
# would reopen the exact non-canonical-value finding this set exists to
# suppress. Consumed by deployment-api's distinct-values detector
# (`_distinct_values.py`) to exclude these specific, permanently-accepted
# values from its non-canonical findings count — "known and accepted", not
# "drift needing a fix". NOT a canonical set — never merge into
# VENUES_BY_ASSET_GROUP/ALL_VENUES or any canonicality check.
#
# FOOTYSTATS (added 2026-07-30, ldr_qg_failure escalation agt-57430c) is here rather than in
# VENUES_BY_ASSET_GROUP["sports"] above for a DIFFERENT reason than the bookmakers above: it is a
# genuine ODDS_API fan-out bookmaker source (pipeline_mode=batch_footystats; legacy venue=ODDS_API
# mislabel re-stamped + GCS-verified 2026-07-30, 42,476 shards) — but the literal string "FOOTYSTATS"
# is ALREADY a canonical instruments-service reference-data-provider venue (get_venues_for_asset_
# groups(["SPORTS"]) in instruments-service, the FootyStats match-stats/xG-adjacent API — a completely
# different data stream). The IS/UAC sports registries are a deliberate two-registry model required to
# stay DISJOINT (operator Decision C, 2026-06-29;
# instruments-service::tests/unit/test_orchestrator_helpers.py::test_sports_exempt_is_disjoint_from_
# uac_sports), so adding FOOTYSTATS to VENUES_BY_ASSET_GROUP here broke that invariant. Accepted-non-
# canonical (this set) silences the same distinct-values finding without claiming canonical venue
# status, mirroring the treatment of the bookmakers below.
SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS: frozenset[str] = frozenset(
    {
        "BETMGM",
        "BETONLINEAG",
        "BETOPENLY",
        "BETRIVERS",
        "BETSSON",
        "BETVICTOR",
        "BETWAY",
        "BOVADA",
        "CASUMO",
        "CORAL",
        "FOOTYSTATS",
        "LIVESCOREBET",
        "MATCHBOOK",
        "NOVIG",
        "ONEXBET",
        "PADDYPOWER",
        "PROPHETX",
        "SKYBET",
        "UNIBET",
        "UNIBET_EU",
        "UNIBET_UK",
        "VIRGINBET",
        "WILLIAMHILL",
    }
)

# TradFi "chain snapshot" bundle data_types (options_chain/futures_chain) — the
# per-underlying options/futures chain snapshot rows the DERIBIT/CME writers
# genuinely emit (mark_iv/greeks + the futures-chain analogue), operator
# PRESERVE-ruled (T-OLD-2b, 2026-06-08). They are deliberately NOT members of
# DATA_TYPES_BY_ASSET_GROUP["tradfi"] — that list stays the per-contract-leaf
# market-data vocabulary (trades/ohlcv_*/tbbo/mbp_10/...), and
# options_chain/futures_chain are conceptually INSTRUMENT_TYPES (one bundle per
# underlying), not data_types (see the "Bundle grain (ERA-B...)" comment above
# VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE). But real captured rows DO carry
# data_type=options_chain (242,210 rows, 100% captured — the Era-A mark_iv/
# greeks chain snapshot the CEFI_OPTIONS_CHAIN_TRADES/*_SNAPSHOT schema
# protects) and data_type=futures_chain (8 rows, 100% captured — the small
# genuine legacy futures-chain-snapshot cohort, same shape). Neither is junk
# and neither should be relabelled/purged (options_chain: REFUTED-relabel
# verdict; futures_chain: the same precedent, carved out 2026-07-22) — see
# `plans/active/distinct_values_noncanonical_audit_2026_07_20.md` "LIVE
# row-count evidence" + "Refined worklist". Until this export, the
# distinct-values detector had no way to know that: both still badged
# non-canonical every run despite the audit's own "is canonical"/"carve-out"
# verdicts never actually being wired to silence them. Mirrors
# SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS exactly: consumed by
# deployment-api's `_distinct_values.py` `_ACCEPTED_EXCEPTIONS` to drop these
# two values from the tradfi `data_types` axis finding count — "known and
# accepted", not "drift needing a fix". NOT a canonical set — never merge into
# DATA_TYPES_BY_ASSET_GROUP/ALL_DATA_TYPES or any canonicality check.
TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES: frozenset[str] = frozenset(
    {
        "options_chain",
        "futures_chain",
    }
)

# CeFi venue-dialect fold (honest_coverage_uac_writer_matrix_reconciliation
# Decision 6): the writer captures under Tardis-grain suffixed venues
# (OKX-SWAP/-FUTURES from expand_cefi_tardis_endpoints; legacy raw Tardis
# exchange ids on older rows) while this registry keys those venues at the
# bare canonical grain (OKX). Maps each known dialect spelling to its
# canonical venue. Venues that are themselves canonical suffixed forms
# (OKX-SPOT, BYBIT-SPOT, KRAKEN-FUTURES, BITFINEX-*, ...) are deliberately
# NOT present here — OKX-SPOT was REMOVED 2026-07-10 (Option A follow-
# through: OKX-SPOT is its own declared cefi venue with its own EXPECTED
# entry now; folding it to bare OKX would make real captured OKX-SPOT rows
# compare against the wrong EXPECTED tuple). COINBASE is the exception: the
# canonical EXPECTED token for spot Coinbase is COINBASE-SPOT (not bare
# COINBASE), so that entry folds legacy bare-COINBASE tokens UP instead of
# down. Moved here from instruments-service's `check_enumeration_completeness.py`
# (audit follow-up 2026-07-22, distinct-values D2) so instruments-service's
# canonicalisation AND deployment-api's distinct-values detector share ONE
# source of truth instead of instruments-service hardcoding its own copy that
# deployment-api could never see — see
# `plans/active/distinct_values_noncanonical_audit_2026_07_20.md` "D2".
CEFI_VENUE_FOLD: dict[str, str] = {
    # Tardis-grain splits emitted by expand_cefi_tardis_endpoints()
    "OKX-SWAP": "OKX",
    "OKX-FUTURES": "OKX",
    # INVERTED (coinbase_bare_name_migration_2026_07_06 S1): COINBASE-SPOT is
    # now the canonical EXPECTED token; legacy manifest rows that stamped bare
    # COINBASE fold UP to COINBASE-SPOT so they still match EXPECTED instead
    # of landing in the stray bucket.
    "COINBASE": "COINBASE-SPOT",
    # Writer-side names for venues UAC keys differently
    "BYBIT-FUTURES": "BYBIT",
    "COINBASE-INTERNATIONAL": "COINBASE-FUTURES",
    # Legacy raw Tardis exchange ids (pre-canonicalisation manifest rows)
    "OKEX": "OKX",
    "OKEX-SWAP": "OKX",
    "OKEX-FUTURES": "OKX",
    "CRYPTOFACILITIES": "KRAKEN-FUTURES",
    "BITFINEX-DERIVATIVES": "BITFINEX-FUTURES",
}

# The dialect spellings above are real manifest values (writers genuinely
# stamp them), not junk. Most are also not members of
# VENUES_BY_ASSET_GROUP["cefi"] (the bare-canonical grain), so the
# distinct-values panel badges them non-canonical every run despite them
# being fully understood, folded, honest data. TWO entries (OKX-SWAP,
# OKX-FUTURES) were SEPARATELY promoted to direct VENUES_BY_ASSET_GROUP
# membership 2026-07-21 (real, actively-captured cefi venues in their own
# right) — excluded here via the set difference so they keep badging
# canonical=True (visibly correct) rather than being silently dropped from
# the panel's enumeration entirely, which is what accepted-exception
# treatment does (see `enumerate_distinct_values` — a value here is REMOVED
# from output, not just marked canonical). Mirrors
# SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS /
# TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES exactly for the
# genuinely-still-non-canonical remainder: consumed by deployment-api's
# `_distinct_values.py` `_ACCEPTED_EXCEPTIONS` to drop those from the cefi
# `venues` axis finding count. NOT a canonical set — never merge into
# VENUES_BY_ASSET_GROUP/ALL_VENUES or any canonicality check.
CEFI_VENUE_ACCEPTED_NONCANONICAL_ALIASES: frozenset[str] = frozenset(CEFI_VENUE_FOLD) - frozenset(
    VENUES_BY_ASSET_GROUP["cefi"]
)

# Sports bookmaker-venue fold (sports_consolidated_native_ao_extract_2026_07_25.md Track C):
# the ODDS_API adapter stamps `venue` from the vendor's raw, unnormalised bookmaker key
# (`odds_api_adapter.py`'s `bm.key`) with no alias pass, so vendor spelling drift reaches the
# manifest verbatim. Unlike CEFI_VENUE_FOLD (dialects tolerated permanently), every key here
# has a confirmed correctly-cased canonical entry in `venue_constants.py` already, AND (unlike
# UNIBET_UK/UNIBET_EU below) zero pre-existing canonical-spelling rows to collide with — this
# fold is consumed by BOTH the adapter (to normalise at capture time, stopping new pollution)
# and the historical-backlog re-stamp migration (to fix already-written manifest rows + GCS
# objects). Live-census-confirmed 2026-07-27: both are actively captured through the day
# before this fold shipped, so the writer-side fix is NOT optional — a re-stamp alone would be
# undone by the very next capture cycle. NOT a canonical set — never merge into
# VENUES_BY_ASSET_GROUP/ALL_VENUES or any canonicality check.
#
# UNIBET_UK/UNIBET_EU were REMOVED from this fold 2026-07-27 (originally shipped here, then
# corrected same-day) after live content comparison proved them GENUINELY DISTINCT bookmakers
# from bare UNIBET, not a casing/alias variant: on a shared (day, league, fixture, market) —
# 2022-10-17, ALLSVENSKAN, IFK Goteborg vs Malmo FF — UNIBET_UK and UNIBET stamped DIFFERENT
# simultaneous odds (HOME 4.25 vs 4.10, AWAY 1.85 vs 1.81, DRAW 3.65 vs 3.55) at slightly
# different bm_time (05:05:30Z vs 05:01:25Z), with 1,066/1,090 UNIBET_UK dates and 9,028/9,443
# (date, league_id) shards overlapping bare UNIBET's own captured population — i.e. the vendor
# fans BOTH out as separate real bookmaker feeds every day, not a rename event. Folding would
# have silently conflated two distinct bookmakers' live market data under one venue key on
# every future capture — see `SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS` below, where
# they now live as their own accepted, non-canonical, non-folded bookmaker entries instead
# (mirroring BETMGM/BETONLINEAG/... exactly). UNIBET_EU treated the same way on the strength
# of the identical UK-vs-EU sub-brand pattern (0 shared dates with bare UNIBET to compare
# directly, but no basis to assume it's an alias when its UK sibling demonstrably isn't). NOTE:
# `_odds_api_maps.ODDS_API_KEY_MAP["UNIBET"]` (unused dead code -- zero real consumers in any
# capture/manifest path, grep-confirmed) lists "unibet_uk" as folding to UNIBET; that entry
# predates this finding and was never validated against real captured data -- the vendor's own
# `bookmakers[]` response structurally lists "unibet"/"unibet_uk" as separate entries each with
# an independent `bookmaker_key`/`bookmaker_title`/`last_update`, which is the stronger, more
# direct signal. Flagged, not silently fixed here (out of this fold's scope) -- see the plan's
# issue-doc finding for the other untouched regional variants that reverse-map may also
# mis-declare (ladbrokes_au, sport888_se, unibet_fr/it/nl/se, betfair_ex_au, bet365_au, ...).
#
# KEYS ARE THE VENDOR'S RAW LOWERCASE WIRE SPELLING, NOT the uppercase canonical form
# (confirmed via `_odds_api_maps.ODDS_API_KEY_MAP["LADBROKES"]`/["BET888SPORT"]`: the real
# `OddsApiBookmaker.key` values are "ladbrokes_uk"/"sport888", never "LADBROKES_UK"/"SPORT888"
# — those uppercase forms only ever appear in the GCS PATH segment and `instrument_id`, which
# get separately uppercased downstream (`venue_fetch.py`'s local `bm_str = bm_raw.upper()` for
# the path; `build_instrument_id`'s internal `_slug().upper()` for the id) regardless of this
# dict's casing. A dict keyed on the uppercase form is a SILENT NO-OP: `.get()` never matches
# the real lowercase `bm.key`, so `odds_api_adapter.py`'s call site looked correct but folded
# nothing -- caught 2026-07-27 by testing the fold against a real captured object's `venue`
# COLUMN value (lowercase "ladbrokes_uk"), not just its GCS path/instrument_id (uppercase).
SPORTS_VENUE_FOLD: dict[str, str] = {
    "ladbrokes_uk": "LADBROKES",
    "sport888": "BET888SPORT",
}

# Bundle-grain "chain snapshot" instrument_type tokens (audit follow-up 2026-07-22,
# distinct_values_noncanonical_audit_2026_07_20.md § "D5 — bundle-grain
# recognition"): ``options_chain``/``futures_chain`` are the REAL, deliberate
# shard-grain ``instrument_type`` stamp MTDS's Tardis writers use for TradFi +
# CeFi options/futures chain-snapshot bundles — one manifest atom per underlying
# per day, bundling every strike/expiry leg into a single file (see MTDS
# ``tardis_bulk_download.py::shard_it_str = "options_chain" if ... else
# "futures_chain"``; mirrored by this registry's OWN
# ``canonical.partition_paths.TRADFI_CHAIN_INSTRUMENT_TYPES`` /
# ``CEFI_CHAIN_INSTRUMENT_TYPES``, which already recognise the identical pair as
# legitimate path-building bundle tokens — this export gives the distinct-values
# detector the same recognition for a DIFFERENT axis: MTDS's raw
# ``instrument_type`` manifest COLUMN, not the GCS path). Real production rows:
# tradfi ``futures_chain`` (154,147 captured) + ``options_chain`` (121,031
# captured) at this axis-grain, 2026-07-21 live rollup.
#
# Neither is a member of the ``InstrumentType`` enum (that enum is per-CONTRACT
# grain — ``FUTURE``/``OPTION`` — the individual legs the bundle contains), and
# neither should be ADDED to it: ``InstrumentType`` feeds the
# expected-universe/completeness_pct denominator at the per-instrument grain, so
# admitting a per-BUNDLE token there would misrepresent the bundle as an
# individually-tradable instrument (same category of error D1b already fixed for
# defi venues — conflating a real value with the wrong grain's registry).
#
# ``combo`` is deliberately NOT included here — it mirrors
# ``TRADFI_CHAIN_INSTRUMENT_TYPES``'s own exclusion (its leg-aware id format is
# unsettled, per ``canonical/partition_paths.py``'s comment). Tradfi's lowercase
# ``combo``/``equity``/``etf``/``future``/``index`` spellings are a SEPARATE,
# already-classified finding (real case-drift owned by the in-flight tradfi
# uppercase migration — see this audit's D3 note); this export does not touch
# them. Mirrors SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS /
# TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES exactly: consumed by
# deployment-api's `_distinct_values.py` `_ACCEPTED_EXCEPTIONS` to drop these two
# values from the tradfi AND cefi `instrument_types` axis finding count — "known
# and accepted", not "drift needing a fix". NOT a canonical set — never merge
# into the `InstrumentType` enum or any canonicality check.
CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES: frozenset[str] = frozenset(
    {
        "options_chain",
        "futures_chain",
    }
)

# TradFi venue-axis dead/legacy residue (distinct_values_noncanonical_audit_2026_07_20.md
# follow-up, 2026-07-30 census review). BARCHART: removed from VENUES_BY_ASSET_GROUP
# ["tradfi"] 2026-06-24 (VIX 15m preload retired) but the live manifest still carries
# 9,119 quarantine-with-tracking rows (operator ruling 2026-07-20, tradfi_consolidated_
# closeout Progress Log: "barchart + ICE qualifier variants quarantine-with-tracking"),
# 100% capture_status=empty_confirmed (0 captured, no real data at risk) — never had an
# accepted-exception entry despite the ruling, so it kept re-badging as fresh drift every
# census run. YAHOO_FINANCE: removed 2026-07-15 (see the NOTE above in VENUES_BY_ASSET_
# GROUP["tradfi"] — "legacy source-as-venue artifact... Do NOT re-add it here"); the
# manifest rows behind this badge are pre-2026-07-15 legacy captures (GCS-confirmed
# 2026-07-30 at day=2025-01-02) from before the writer was fixed to stamp real venues
# (DXY→ICE, KRW/USD→FX) with source=yahoo instead — genuinely dead, not a registry gap.
# Mirrors CEFI_VENUE_ACCEPTED_NONCANONICAL_ALIASES exactly: consumed by deployment-api's
# `_distinct_values.py` `_ACCEPTED_EXCEPTIONS` to drop these from the tradfi `venues` axis
# finding count. NOT a canonical set — never merge into VENUES_BY_ASSET_GROUP/ALL_VENUES.
TRADFI_VENUE_ACCEPTED_NONCANONICAL_ALIASES: frozenset[str] = frozenset(
    {
        "BARCHART",
        "YAHOO_FINANCE",
    }
)

# TradFi chain-axis dead residue (2026-07-30 census review,
# tradfi_distinct_values_net_new_clusters_2026_07_28.md). `chain` is meaningless for
# tradfi (manifest_finalize.py::_resolve_manifest_venue_chain short-circuits chain=""
# for every non-DeFi venue) — these 14 rows are the ONLY non-empty `chain` rows in the
# entire tradfi manifest, all venue=CME/instrument_type=combo/capture_status=
# attempted_failed/row_count=0/error_reason=SCHEMA_VALIDATION_FAILED from a failed
# 2020-01-01/02 capture attempt. GCS-confirmed 2026-07-30: zero underlying=ESM0* objects
# anywhere — pure dead manifest bookkeeping, not a live writer bug. NOT a canonical set —
# `chain` has no canonical set for tradfi at all; consumed by deployment-api's
# `_ACCEPTED_EXCEPTIONS[("chains", "tradfi")]`.
TRADFI_CHAIN_AXIS_ACCEPTED_DEAD_RESIDUE: frozenset[str] = frozenset(
    {
        "ESM0",
        "ESM0_MIGRATED_20260418T131054Z",
    }
)

# TradFi instrument_type-axis unresolved residue (2026-07-30 census review,
# tradfi_distinct_values_net_new_clusters_2026_07_28.md). `UD` — 3,607 captured rows,
# venue=CME, spanning 2021-2026 in disjoint yearly chunks. Investigated twice (this
# session): no writer found stamping bare instrument_type="UD" (CBOE's real `UD:` combo
# classifier tags a `CBOE:UD:...` instrument_id, not this shape); GCS checked at 3 dates
# found no `instrument_type=UD/` or `instrument_type=ud/` path. Quarantined per the
# operator's standing classify-or-quarantine precedent (UNKNOWN, 2026-07-18) — root cause
# NOT fully confirmed, flagged here for a deeper trace, not a closed finding. NOT a
# canonical set — consumed by `_ACCEPTED_EXCEPTIONS[("instrument_types", "tradfi")]`.
TRADFI_INSTRUMENT_TYPE_ACCEPTED_UNRESOLVED_RESIDUE: frozenset[str] = frozenset(
    {
        "UD",
    }
)

# Sports venue-axis cross-asset-group bleed (2026-07-30 census review). KALSHI is a real,
# registered `prediction` venue (VENUES_BY_ASSET_GROUP["prediction"]) whose rows also
# appear in the SPORTS manifest — 20,785 rows, 100% capture_status=empty_confirmed/
# row_count=0, paired with source=polymarket_clob, dates 2020-06-06..2026-05-21.
# GCS-confirmed 2026-07-30: zero real objects under asset_group=sports/venue=KALSHI at 3
# dates spanning the full range — purely a manifest phantom, no data at risk. Root-cause
# classification (fleet-wide manifest_consolidator TOCTOU vs. legacy artifact) remains open
# on `sports_satellite_ao_dispatch_batch3_2026_07_25.md`; this only silences the panel
# badge for the confirmed-phantom population. NOT a canonical set — never merge into
# VENUES_BY_ASSET_GROUP["sports"] (KALSHI belongs to prediction, not sports). Consumed by
# `_ACCEPTED_EXCEPTIONS[("venues", "sports")]`.
SPORTS_VENUE_ACCEPTED_CROSS_AG_BLEED: frozenset[str] = frozenset(
    {
        "KALSHI",
    }
)

# Sports data_type-axis stale uppercase residue (2026-07-30 census review,
# sports_consolidated_closeout_2026_07_19.md "K1/K2 revert"). `ODDS`/`ODDS_MOVEMENT`/
# `ODDS_SNAPSHOT` (uppercase) are dead — the registry+writer revert shipped 2026-07-27
# and the 345,852 uppercase GCS objects were deleted+re-verified-0-remaining 2026-07-28.
# GCS-confirmed 2026-07-30: zero uppercase data_type= objects on 2 recent dates; the
# current writer (market-data-processing-service canonical_writer.py) correctly lowercases
# both the path and the manifest row. The only remaining badge source is 4 stale
# capture_status=empty_confirmed/row_count=0 manifest rows with zero backing GCS content —
# bookkeeping residue, not a live regression. NOT a canonical set — never merge into
# DATA_TYPES_BY_ASSET_GROUP["sports"] (the K1/K2 revert deliberately keeps this lowercase-
# only). Consumed by `_ACCEPTED_EXCEPTIONS[("data_types", "sports")]`.
SPORTS_DATA_TYPE_ACCEPTED_STALE_UPPERCASE_RESIDUE: frozenset[str] = frozenset(
    {
        "ODDS",
        "ODDS_MOVEMENT",
        "ODDS_SNAPSHOT",
    }
)

# Sports MDPS market-token instrument_type values (sports_instrument_type_market_token_
# ssot_gap_2026_07_28.md). These 30 values are real, DELIBERATELY-produced MDPS output —
# `canonical_writer_shaping.py::_type_token_from_canonical_id` resolves a sports candle
# row's instrument_type from the market segment of the canonical id via
# ODDS_API_MARKET_TO_CANONICAL (the operator's "branch the OHLCV mapping by instrument
# market type" ruling), not a writer bug. Mirrors the tradfi/cefi
# CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES precedent exactly: these are
# bundle/market-grain tokens, never members of the per-CONTRACT-grain `InstrumentType`
# enum, and never going to be added to it (operator decision 2026-07-30 — accepted-
# exception over global enum growth, avoiding cross-asset-group enum bloat + denominator
# blast radius). NOT a canonical set — consumed by
# `_ACCEPTED_EXCEPTIONS[("instrument_types", "sports")]`.
SPORTS_MARKET_TOKEN_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES: frozenset[str] = frozenset(
    {
        "ASIAN_HANDICAP_-0",
        "ASIAN_HANDICAP_0",
        "ASIAN_HANDICAP_0_25",
        "ASIAN_HANDICAP_0_5",
        "ASIAN_HANDICAP_0_75",
        "ASIAN_HANDICAP_1",
        "ASIAN_HANDICAP_1_25",
        "ASIAN_HANDICAP_1_5",
        "ASIAN_HANDICAP_1_75",
        "ASIAN_HANDICAP_2",
        "ASIAN_HANDICAP_M0_25",
        "ASIAN_HANDICAP_M0_5",
        "ASIAN_HANDICAP_M0_75",
        "ASIAN_HANDICAP_M1",
        "ASIAN_HANDICAP_M1_25",
        "ASIAN_HANDICAP_M1_5",
        "ASIAN_HANDICAP_M1_75",
        "ASIAN_HANDICAP_M2",
        "MATCH_ODDS",
        "MATCH_ODDS_LAY",
        "OVER_UNDER_1_5",
        "OVER_UNDER_1_75",
        "OVER_UNDER_2",
        "OVER_UNDER_2_25",
        "OVER_UNDER_2_5",
        "OVER_UNDER_2_75",
        "OVER_UNDER_3",
        "OVER_UNDER_3_25",
        "OVER_UNDER_3_5",
        "SPORT",
    }
)


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
    # swaps_ohlcv_{15s,1m,5m,15m,1h,4h,1d} — these ARE the MDPS candle-adapter
    # OUTPUT of "dex_pool_swaps" above (DefiSwapAdapter), not a raw input that
    # itself needs further candle processing — False, same reasoning as
    # dex_pool_state. No candle adapter is registered for these output keys
    # (would be circular); the omitted-key default of True would otherwise
    # route them to a non-existent adapter (test_defi_data_type_has_explicit_
    # candle_classification enforces this explicitly for every defi data_type).
    "swaps_ohlcv_15s": False,
    "swaps_ohlcv_1m": False,
    "swaps_ohlcv_5m": False,
    "swaps_ohlcv_15m": False,
    "swaps_ohlcv_1h": False,
    "swaps_ohlcv_4h": False,
    "swaps_ohlcv_1d": False,
    # Bypass — periodic supply/borrow-index snapshot read raw by features-onchain
    # (aave_lending_rates / aave_utilization); no lending_ohlcv consumer exists.
    # Same class as oracle_prices / lst_rates. Do NOT re-enable without a real
    # lending_ohlcv consumer (see issue defi_code_codex_drift D3; reverts 4c98a635).
    "lending_indices": False,
    # Note: "liquidations" already declared in CeFi section above (True — same for DeFi)
    "perp_funding": False,
    # Per-fill prints; SEMANTICALLY the same class as "trades"/"dex_pool_swaps" (True).
    # Pass-through ONLY because no defi/perp_trades candle adapter exists in MDPS and no
    # defi-asset-group venue currently emits it — the Drift V2 ingester that motivated the
    # DATA_TYPES_BY_ASSET_GROUP entry was removed 2026-07-16 with the Drift venue (operator
    # ruling); the on-chain CLOBs that do emit per-fill prints are cefi-asset-group and use
    # "trades". Omitting the key is NOT equivalent: needs_candle_processing() defaults
    # unknown types to True, which routes perp_trades to a non-existent adapter. Flip to
    # True ONLY together with a real defi/perp_trades adapter (cf. "lending_indices" below).
    "perp_trades": False,
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
        # Candle-based groups: FEATURE_GROUP_DATA_TYPES's "trades" default is CeFi's raw
        # data_type; TradFi's own candle stream is "ohlcv_1m" (TradfiTradesAdapter writes
        # output_data_type=ohlcv_1m, and build-continuous's stitched continuous_future
        # series carries the same data_type) -- leaving these unmapped meant
        # dependency_checker's lookback validation (keyed on data_type) could never find
        # ANY TradFi candle history regardless of real data on disk (0/N candles on every
        # check), even after the MDPS writer-side fix landed
        # (tradfi_mdps_build_continuous_mismatches_2_and_4_still_open_2026_07_26.md).
        "technical_indicators": "ohlcv_1m",
        "moving_averages": "ohlcv_1m",
        "oscillators": "ohlcv_1m",
        "volatility_realized": "ohlcv_1m",
        "momentum": "ohlcv_1m",
        "volume_analysis": "ohlcv_1m",
        "vwap": "ohlcv_1m",
        "candlestick_patterns": "ohlcv_1m",
        "market_structure": "ohlcv_1m",
        "returns": "ohlcv_1m",
        "round_numbers": "ohlcv_1m",
        "streaks": "ohlcv_1m",
        "futures_basis": "ohlcv_1m",
        "volume_flow": "ohlcv_1m",
        "temporal": "ohlcv_1m",
        "targets": "ohlcv_1m",
        "supply_demand_zones": "ohlcv_1m",
        "fibonacci": "ohlcv_1m",
        "level_confluence": "ohlcv_1m",
        "market_structure_sequence": "ohlcv_1m",
        "risk_reward": "ohlcv_1m",
        "wedge_quality": "ohlcv_1m",
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
    # TradFi COMBO rolls up to its OWN per-underlying ``instrument_type=combo`` bundle
    # (BUNDLE_INSTRUMENT_TYPE_BY_AG_AND_LEAF[("tradfi","combo")]="combo", 2026-06-22),
    # so — unlike option/option_chain — the ``combo`` row IS consulted (it drives the
    # synthetic bundle entry's data_types). CME spread/combo cells are the SAME OHLCV
    # stream as the outright futures the legs reference, so the captured set mirrors
    # ``futures_chain`` + ``ohlcv_1s`` (fetched alongside ohlcv_1m for every GLBX.MDP3
    # tradeable; SSOT codex/02-data/tradfi-databento-sourcing-ssot.md). Kept tight
    # (no mbp_10/24h) to avoid over-fanning cells the writer never captures.
    ("tradfi", "combo"): frozenset({"trades", "ohlcv_1s", "ohlcv_1m", "tbbo"}),
    ("tradfi", "options_chain"): frozenset({"trades", "ohlcv_1m", "options_chain"}),
    # ohlcv_1s added 2026-06-22 (writer-grain alignment): the MTDS writer captures
    # CME/ICE futures_chain cells with ohlcv_1s alongside ohlcv_1m (both L0/free,
    # fetched for every GLBX.MDP3 tradeable) — the prior set omitted it, marking the
    # real ohlcv_1s chain cells phantom-``expected_unattempted``.
    ("tradfi", "futures_chain"): frozenset({"trades", "ohlcv_1s", "ohlcv_1m", "tbbo"}),
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
        {"odds", "odds_snapshot", "odds_movement", "markets", "outcomes", "settlements", "trades"}
    ),
    ("sports", "prop"): frozenset(  # UNCERTAIN — sports-owner verify
        {"odds", "odds_snapshot", "odds_movement"}
    ),
    # ("sports", "odds") — closes the matrix hole found by
    # sports_shard_enumeration_cartesian_blowup_2026_07_20.md Part 2 item 2.3
    # (2026-07-22). Unlike its four neighbours above, this entry is CONFIRMED,
    # not UNCERTAIN: CONTRACT_REGISTRY[("sports","odds","trades")] =
    # SPORTS_ODDS_TRADES is a real, registered SchemaContract
    # (_sports_prediction_contracts.py), and prod carries 1,806,527 rows under
    # exactly this (instrument_type=odds, data_type=trades) pair. Before this
    # entry existed the pair had NO matrix row at all, so every one of those
    # rows silently rode the "unmapped instrument_type" fallback path instead
    # of an audited entry.
    # "TRADES" (uppercase) was added to the value set 2026-07-23 when K1
    # (mtds@2536b91c, 2026-07-22) flipped the live writer to emit
    # instrument_type=ODDS/data_type=TRADES and K2 migrated the historical
    # corpus to match. **REVERTED 2026-07-27**: the same-day 2026-07-23
    # reconciliation (sports_consolidated_closeout_2026_07_19.md, "Canonical
    # target") decided sports data_type/instrument_type is LOWER-case for the
    # WHOLE vocabulary, no UPPER exception — K1/K2 are being reverted, not kept.
    # The lowercase "odds"/"trades" pair is the sole canonical form again.
    ("sports", "odds"): frozenset({"trades"}),
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


# ── Layer-1 venue-axis exclusions (two-layer combinator redesign, finding 1) ──
# uac_data_type_validity_combinator_fragmentation_2026_07_07.md's target shape
# generalises theoretical validity to (asset_group, protocol, instrument_type);
# for TradFi, "venue" plays the protocol role — CME and ICE are NOT
# interchangeable data providers despite sharing an instrument_type (CME =
# Databento GLBX.MDP3 full tick; ICE has ZERO Databento coverage — see
# VENUES_BY_ASSET_GROUP's "Yahoo-sourced ICE/NYBOT DXY index only" comment
# above). Before this table, ``valid_data_types_for_venue_instrument_type``
# discarded ``venue`` for every non-DeFi asset_group (:1019 old behaviour),
# so ICE silently inherited CME's AG-level ``("tradfi","futures_chain")`` set
# including ``ohlcv_1s`` — a live, provably-wrong cell (finding 1).
#
# Live-verified 2026-07-10 against
# gs://market-data-tick-tradfi-prd-<project>/_index/
# availability_index.parquet: CME/futures_chain/ohlcv_1s has 151,153 real
# ``captured`` rows; ICE/futures_chain/ohlcv_1s (2,108 rows) + ICE/combo/
# ohlcv_1s (360,270 rows) + bare-ICE/ohlcv_1s are ALL 100% ``empty_confirmed``
# (ZERO ``captured`` anywhere) while ICE's ``trades``/``ohlcv_1m``/``tbbo`` DO
# have real captured rows at the same grains (ICE/futures_chain: 110 trades +
# 135 ohlcv_1m captured; ICE/combo: 83 trades + 95 ohlcv_1m captured) — so the
# fix SUBTRACTS only the proven-wrong ``ohlcv_1s`` cell, not a hand-authored
# replacement set (avoids silently dropping a real, unverified cell like tbbo
# at this grain). Keyed ``(asset_group, base_venue, instrument_type)`` — empty
# for every venue but ICE, so every other TradFi/CeFi/DeFi venue (CME
# included) is byte-identical to pre-fix behaviour (no regression).
VALID_DATA_TYPES_VENUE_EXCLUSIONS: dict[tuple[str, str, str], frozenset[str]] = {
    ("tradfi", "ICE", "futures_chain"): frozenset({"ohlcv_1s"}),
    ("tradfi", "ICE", "combo"): frozenset({"ohlcv_1s"}),
    # The former DRIFT spot_pair/perp_funding exclusion (DRIFT's capability
    # declaration bundled PERPETUAL + SPOT_PAIR under one entry, leaking
    # perp_funding onto SPOT markets) was removed 2026-07-16 along with the
    # rest of the DRIFT venue — operator ruling: all Solana perp DEXes
    # dropped except Jupiter, not integrated.
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
#
# ── TradFi (CME / ICE) — writer-grain alignment 2026-06-22 ──────────────────────
# The MTDS writer (``symbol_rules._VENUE_INSTRUMENT_TYPE``) stamps EVERY CME/ICE
# captured cell ``instrument_type=futures_chain`` (a per-underlying chain bundle),
# NOT per-contract ``future`` — its grain comes from the venue default + the dated
# -future symbol regex, NOT from this map (MTDS never imports it), so adding TradFi
# here only re-grains the IS expected-universe SEED to match what the writer
# already captures. Without this, a CME ``FUTURE`` leaf seeded ``future`` (passthrough)
# and matched only the ~2K per-contract cells, leaving the ~144K real ``futures_chain``
# cells phantom-``expected_unattempted``. CME/ICE are the ONLY TradFi futures venues
# (databento ``_DATASET_TO_VENUE``: GLBX.MDP3→CME, IFEU/IFUS.IMPACT→ICE); equities
# (NASDAQ/NYSE→equity), FX (→spot_pair) and CBOE (→index) are unaffected.
FUTURE_BUNDLE_VENUES: dict[str, frozenset[str]] = {
    "cefi": frozenset({"DERIBIT", "OKX"}),
    "tradfi": frozenset({"CME", "ICE"}),
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
    # TradFi COMBO (CME calendar / inter-commodity spreads + UD_1V_* user-defined
    # combos — databento class ``T``) rolls up per-underlying like options/futures,
    # but the MTDS writer keeps its OWN ``instrument_type=combo`` partition (it is
    # in ``symbol_rules._UNDERLYING_PARTITIONED_TYPES`` and ``manifest_finalize``
    # routes ``itype != "combo"`` away from the options_chain bundle row, so combo
    # captured cells carry ``instrument_type=combo``, NOT ``options_chain``). Seeding
    # ``options_chain`` here (the pre-2026-06-22 value) mis-grained the largest TradFi
    # bundle bucket (~53K combo cells) → phantom-``expected_unattempted``. The bundle
    # TYPE is therefore ``combo`` (roll-up to one per-underlying entry, instrument_type
    # preserved); its data_types come from the ``("tradfi", "combo")`` validity row.
    ("tradfi", "combo"): "combo",
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
            # gas_fees is CHAIN-LEVEL (collected once per chain at the synthetic
            # venue=ALCHEMY, instrument_type=spot_asset — never per protocol), so
            # it is intentionally NOT declared on any protocol in
            # PROTOCOL_CAPABILITIES. Inject it onto the chain-level spot_asset set
            # so the SOURCE_PRIORITY pair ("defi","gas_fees") stays reachable from
            # the validity matrix. (token_transfers / mev_events remain reachable
            # via their synthetic ALCHEMY-ONCHAIN / FLASHBOTS pseudo-protocols.)
            defi.setdefault("spot_asset", set()).add("gas_fees")
            _defi_valid_data_types = {k: frozenset(v) for k, v in defi.items()}
        return _defi_valid_data_types.get(normalised)  # None if unmapped

    return VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE.get((asset_group.lower(), normalised))


def valid_data_types_for_venue_instrument_type(
    asset_group: str, venue: str | None, instrument_type: str
) -> frozenset[str] | None:
    """Per-``(venue, instrument_type)`` valid data_types — the combinator JOIN.

    Two-layer redesign (uac_data_type_validity_combinator_fragmentation_2026_07_07.md):
    this is the single accessor that composes Layer 1 (theoretical validity,
    chain/protocol-agnostic — :func:`valid_data_types_for_instrument_type`) with
    the venue axis, in two ways:

    1. **DeFi protocol narrowing** (pre-existing). :func:`valid_data_types_for_instrument_type`
       builds the DeFi validity set as the UNION across every protocol that
       declares an instrument_type, so a hybrid protocol's data_types leak to
       every instrument of that type — e.g. a protocol declaring both ``pool``
       and ``perp_funding`` would make ``perp_funding`` read as valid for ALL
       pools incl. Uniswap → residual false ``expected_unattempted`` for
       non-hybrid pools.
       This narrows DeFi validity to the SPECIFIC protocol named by ``venue``
       (the ``PROTOCOL`` segment of the canonical ``PROTOCOL-CHAIN`` id, e.g.
       ``UNISWAP_V3-ETHEREUM`` → ``uniswap_v3``): it returns ONLY that
       protocol's declared data_types.
    2. **Venue-axis exclusions** (finding 1 fix — ``VALID_DATA_TYPES_VENUE_EXCLUSIONS``,
       any asset_group). Some venues sharing an instrument_type are NOT
       interchangeable data providers (CME vs ICE both stamp ``futures_chain``
       but only CME has Databento sub-second coverage) — venue no longer
       silently discarded for non-DeFi asset_groups (the pre-fix bug: CME/ICE
       shared an identical valid-set despite ICE having zero real coverage
       for part of it).

    For a missing ``venue``, an unmapped DeFi protocol, or an instrument_type
    the protocol does not declare, DeFi narrowing DELEGATES to
    :func:`valid_data_types_for_instrument_type` — i.e. it only ever narrows in
    the clearly-safe case and never under-reports a real cell. The exclusion
    layer only ever SUBTRACTS explicitly-proven-wrong cells (empty for any
    venue not in the table) — same non-regression guarantee.

    Returns:
        frozenset[str] — the valid data_types (narrowed for a known DeFi
                          protocol and/or a declared venue exclusion).
        None           — unmapped (delegated) → caller falls back to ALL.
    """
    ag = asset_group.lower()
    normalised_it = instrument_type.strip().lower() if instrument_type else ""
    normalised_it = _INSTRUMENT_TYPE_ALIASES.get(normalised_it, normalised_it)

    if ag == "defi" and venue:
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
        cap_its: set[str] = (
            {_INSTRUMENT_TYPE_ALIASES.get(_it.strip().lower(), _it.strip().lower()) for _it in cap.instrument_types}
            if cap is not None
            else set()
        )
        if cap is not None and normalised_it in cap_its:
            result: frozenset[str] | None = frozenset(cap.data_types)
        else:
            # Unmapped protocol, or the protocol does not declare this
            # instrument_type → fall back to the union rather than risk
            # dropping a real cell on an incomplete cap.
            result = valid_data_types_for_instrument_type(asset_group, instrument_type)
    else:
        result = valid_data_types_for_instrument_type(asset_group, instrument_type)

    if result is None or not venue:
        return result

    excluded = VALID_DATA_TYPES_VENUE_EXCLUSIONS.get((ag, _base_venue(venue), normalised_it))
    return (result - excluded) if excluded else result


# Override entries needed when:
# - A venue's data type started later than the venue itself (e.g. Deribit options added later)
# - A venue only supports a subset of its category's data types (e.g. ICE has ohlcv_24h only)
# - A data type has a different start date per venue (e.g. TradFi venues)

# @contract-surface — a removed venue key or a removed data_type from a venue's
# capability entry is a cross-repo contract break (downstream consumers gate expected
# coverage on this dict —
# plans/active/issues/breaking_change_differ_blind_to_registry_data_dicts_2026_07_09.md).
# Adding a key/data_type stays non-breaking; changing a start-date VALUE is not tracked
# (an operational data update, not a structural removal).
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
    # ``liquidations`` REMOVED 2026-07-15 (cefi_completion_program workstream E,
    # operator ruling): only 3 ``captured`` DERIBIT liquidation rows exist in the
    # live manifest (noise, not a real feed) — DERIBIT is NOT one of the 6
    # real-feed liquidations venues. With ``liquidations`` now a PERPETUAL-leg
    # CeFi MVP data_type, a stale gate entry here would seed a phantom liquidations
    # EXPECTED cell for every DERIBIT perp instrument-day. Gated OUT here; the 6
    # real-feed venues keep their entries.
    "DERIBIT": {
        "trades": "2019-03-30",
        "book_snapshot_5": "2019-03-30",
        "derivative_ticker": "2019-03-30",
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
    # BYBIT-SPOT — DISTINCT canonical venue from bare "BYBIT" (perps). Registered
    # in VENUES_BY_ASSET_GROUP["cefi"] 2026-06-23 (cefi_universe_capture_rule)
    # so the perp-gate pairs BYBIT-SPOT ↔ BYBIT perps. Start date =
    # VenueMapping.venue_start_dates["BYBIT-SPOT"] = Tardis ``bybit-spot``
    # availableSince 2021-12-04. Data types mirror expected_coverage.py
    # (trades + book_snapshot_5) — SPOT venue, no derivatives feeds.
    # Populated 2026-07-07 (bybit_spot_manifest_stray_captures-004) — absent
    # entry previously triggered Carve-out 1 zeroing every data_type at the
    # cefi Layer-1 EXPECTED denominator.
    "BYBIT-SPOT": {
        "trades": "2021-12-04",
        "book_snapshot_5": "2021-12-04",
    },
    "OKX": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
        # ``liquidations`` KEPT on bare OKX (2026-07-15, cefi_completion_program
        # workstream E — CORRECTION to the initial removal): bare ``OKX`` is the
        # canonical Layer-1 EXPECTED token for the OKX perp. The Layer-1
        # completeness checker FOLDS the writer's Tardis-grain ``OKX-SWAP`` /
        # ``OKX-FUTURES`` / ``OKEX-SWAP`` rows UP to bare ``OKX``
        # (check_enumeration_completeness.py ``_CEFI_VENUE_FOLD``), so OKX-SWAP's
        # 191,923 captured liquidations rows compare against the bare-``OKX``
        # EXPECTED tuple. ``build_expected`` (expected_universe.py) iterates
        # ``VENUES_BY_ASSET_GROUP["cefi"]`` which carries bare ``OKX`` (NOT
        # OKX-SWAP) — dropping liquidations here would silently zero OKX out of
        # the honest-coverage BATCH denominator even though it is one of the 6
        # real-feed liquidations venues. (The catalogue-driven enumerator
        # ``enumerate_expected_universe.py`` uses the OKX-SWAP sub-venue directly,
        # which retains its own ``liquidations`` entry below — so BOTH producers
        # now agree that OKX perp liquidations IS expected.)
        # options_chain added 2026-07-12 (cefi_deribit_combo_and_okx_bare_venue_gaps_2026_07_12.md
        # Bug C) — real Tardis okex-options data confirmed live (247,540 option
        # symbols, availableSince verified via api.tardis.dev/v1/exchanges/okex-options
        # this session, NOT assumed). This closes the UAC-capability half of Bug C;
        # the venue->adapter-class routing half (bare OKX resolving to OKXAdapter,
        # which has no download_batch) still needs a fix in
        # market_tick_data_service/adapters/umi_tick_provider.py.
        "options_chain": "2020-02-01",
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
    # bare "COINBASE" REMOVED (coinbase_bare_name_migration_2026_07_06.md S3,
    # 2026-07-10) — was a byte-identical duplicate of the COINBASE-SPOT entry
    # below; COINBASE-SPOT is the sole canonical cefi spot key now.
    "COINBASE-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    # HYPERLIQUID — verified 2026-05-04 against the actual S3 archive layout.
    # Tardis added Hyperliquid 2024-10-29 but our adapter does not wire the
    # Tardis trades fetch path (returns []), so trades start = S3 archive start
    # 2025-03-22. liquidations is out of scope (Hyperliquid does not publish a
    # liquidations feed — no S3 prefix, no Tardis channel).
    # perp_funding (standalone data_type) RESTORED 2026-07-30 (RULED 2026-07-28,
    # defi_hyperliquid_perp_funding_derivative_ticker_divergence_2026_07_28.md) —
    # REVERSES the 2026-07-08 retirement below. A cross-source parity check
    # measured this row's derivative_ticker.funding_rate (S3 asset_ctxs, a
    # continuously-updating LIVE snapshot) against perp_funding's realized
    # hourly-settlement value (POST /info fundingHistory) over 169 overlapping
    # historical days: only 60.7% of 2,640 rows matched within a 2e-5 tolerance
    # (worst-case divergence 1.2e-3, >10x the signal's typical magnitude) —
    # disproving the 2026-07-08 "byte-identical/same-source" premise for this
    # venue. perp_funding is the canonical REALIZED-funding source; collector
    # restored in market-tick-data-service/cli/handlers/_perp_funding_hyperliquid.py.
    "HYPERLIQUID": {
        "trades": "2025-03-22",  # S3 hl-mainnet-node-data/node_fills
        "book_snapshot_5": "2023-04-15",  # S3 hyperliquid-archive/market_data/
        "derivative_ticker": "2023-05-20",  # S3 hyperliquid-archive/asset_ctxs/
        "perp_funding": "2023-05-20",  # perp_funding_handler REST /info fundingHistory
    },
    # ASTER — batch+live: derivative_ticker (fundingRate REST) and trades
    # (aggTrades REST, ~30-day rolling depth) are wired in _fetch_aster_rest;
    # live-only: book_snapshot_5 + liquidations via aster_book_liq_ws.py
    # (Binance-Futures-compatible WS at wss://fstream.asterdex.com — depth5@100ms
    # + !forceOrder@arr). Batch REST has no historical depth or force-order
    # feed, so pre-wire history stays typed honest absence
    # (EXPECTED_PRE_SOURCE_COVERAGE_START via the enumerator's per-(venue,dt)
    # start_date gate). Genesis = 2023-07-22 (operator-confirmed 2026-06-17
    # via the Astherus pre-rebrand venue). perp_funding (standalone data_type)
    # RETIRED 2026-07-08 and STAYS RETIRED (re-confirmed 2026-07-30,
    # defi_hyperliquid_perp_funding_derivative_ticker_divergence_2026_07_28.md,
    # in the same review that RESTORED perp_funding for HYPERLIQUID above) — code
    # inspection of the pre-retirement collector (``_perp_funding_hl_aster.py``,
    # git history) shows ASTER's perp_funding rows and its derivative_ticker row
    # were derived from the exact SAME ``/fapi/v1/fundingRate`` REST response in
    # one fetch ("Also emit the canonical CeFi derivative_ticker ... from the
    # SAME funding settlements — one fetch"): genuinely byte-identical by
    # construction, unlike HYPERLIQUID where the two are separate endpoints.
    # Restoring a standalone shard here would duplicate storage, not add a
    # second independent signal.
    # IMPORTANT — pre-2024 Aster funding is BINANCE-PROXIED (Astherus pre-rebrand
    # mirrored Binance funding); it is imported, NOT Aster-native — label `source`
    # honestly. SSOT: perp_funding_data_semantics_and_cadence_2026_06_16.md §GAP 2.
    # ``liquidations`` REMOVED 2026-07-15 (cefi_completion_program workstream E,
    # operator ruling): ASTER liquidations is a genuine LIVE feed (asterdex WS
    # !forceOrder@arr) but has ZERO batch capture (0 ``captured`` liquidations
    # rows in the live manifest — batch REST has no force-order history). Now
    # that ``liquidations`` is a PERPETUAL-leg CeFi MVP data_type (CeFiMvpRule),
    # a stale gate entry here would seed ASTER liquidations into the BATCH honest-
    # coverage denominator; per the ruling "live-only feeds must NOT seed the
    # batch denominator" (batch-absence is honest, not a gap). ``book_snapshot_5``
    # (also live-only) is intentionally left untouched here — its live-vs-batch
    # seeding is tracked separately in workstream I.
    "ASTER": {
        "trades": "2023-07-22",
        "derivative_ticker": "2023-07-22",
        "book_snapshot_5": "2026-06-23",  # live-only via aster_book_liq_ws
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
    # DERIBIT-COMBO — DEREGISTERED 2026-07-21 (operator decision, verbatim: "delete
    # everything to do with deribit combo since it is [a] once venue in practice —
    # manifest/GCS path wise etc. all migrated to split venue+instrument_type").
    # Manifest-verified data-safe before deletion: 0 captured rows (196 total rows,
    # all expected_unattempted/empty_confirmed/attempted_failed — re-confirmed via a
    # direct availability_index read this session) and 0 GCS objects (manifest-oracle
    # corpus-wide + bounded delimiter-descent). The venue's own manifest rows were
    # purged by instruments-service/scripts/complete_cefi_manifest_canonical_dedup_v2_
    # 2026_07_20.py (--deribit-combo purge). Removing the entry here (rather than
    # leaving it registered) closes the gap that would otherwise make
    # expected_universe show DERIBIT-COMBO as "expected but 0% captured" FOREVER — a
    # permanent false gap in the honest-coverage denominator, defeating the point of
    # the purge. See VENUES_BY_ASSET_GROUP["cefi"] (DERIBIT-COMBO removed from there
    # too, same commit).
    # ── DEX-perp on-chain CLOBs (D2b, honest_coverage cefi gate-authority fix,
    # 2026-07-06) — EXTENDED-STARKNET / LIGHTER-ZKSYNC are declared cefi
    # venues (VENUES_BY_ASSET_GROUP["cefi"]) whose itype-gate the D2a fix now
    # admits (INSTRUMENT_TYPES_BY_VENUE, venue_constants.py), but
    # they had NO entry here — absent from this dict means Carve-out 1 (this
    # is a cefi/tradfi skip-filter; see check_enumeration_completeness.py
    # VENUE_CAPABILITY_AGS) zeroes EVERY data_type, independent of the itype
    # fix. data_types sourced from the existing DataTypeCapability catalogue
    # entries for these venues (data_type_capability.py — trades +
    # book_snapshot_5 + derivative_ticker(perpetual); native REST/WS APIs, NOT
    # Tardis routed pre-2026-04-17). Start dates = VenueMapping.
    # venue_start_dates (venue_mapping.py — documented "single source of
    # truth"/"earliest manifest data, NOT exchange founding dates"). No
    # liquidations feed wired for either (same minimum-perp-surface note as
    # data_type_capability.py). LIGHTER-ZKSYNC's perp_funding stays unwired too
    # — re-confirmed 2026-07-30
    # (defi_hyperliquid_perp_funding_derivative_ticker_divergence_2026_07_28.md,
    # in the same review that RESTORED perp_funding for HYPERLIQUID): the
    # pre-retirement collector (``_perp_funding_pacifica_lighter.py``, git
    # history) fetched Tardis's OWN derivative_ticker dataset directly and
    # relabeled it perp_funding — there was never a second, independent source
    # to restore. (PACIFICA (Solana) was a third venue here until removed
    # 2026-07-16 — operator ruling: all Solana perp DEXes dropped except
    # Jupiter, not integrated.)
    "EXTENDED-STARKNET": {
        "trades": "2024-10-01",
        "book_snapshot_5": "2024-10-01",
        "derivative_ticker": "2024-10-01",
    },
    "LIGHTER-ZKSYNC": {
        "trades": "2024-08-01",
        "book_snapshot_5": "2024-08-01",
        # derivative_ticker start CORRECTED 2026-07-15 (defi_perp_funding_canonicalisation_
        # derivative_ticker_all_perps issue, todo 2) from a copy-pasted 2024-08-01 (matching
        # trades/book_snapshot_5's venue-genesis floor) to 2026-04-17 — the real coverage-start
        # of the ONLY source that actually serves LIGHTER-ZKSYNC derivative_ticker.
        # adapters/umi_tick_provider.py's _route_lighter (:356-405) gates Tardis routing on
        # `date >= "2026-04-17"`; before that date it falls to the native REST adapter
        # (adapters/_umi_lighter.py), which has ZERO funding/derivative_ticker code (only
        # trades/book_snapshot_5/candles — confirmed via full-file grep). The prior
        # 2024-08-01 declaration would have the enumerator schedule ~20 months of dates
        # against a source with nothing to return.
        "derivative_ticker": "2026-04-17",
    },
    # Coinbase Derivatives (perps) — D2b, 2026-07-06. COINBASE-FUTURES passed
    # the itype-gate even pre-D2a (it already had a tardis routing entry) but
    # had NO entry here, so Carve-out 1 zeroed it regardless. Mirrors the
    # BITGET-FUTURES / BITFINEX-FUTURES Tier-3 perp shape (trades /
    # book_snapshot_5 / derivative_ticker / liquidations); start date = Tardis
    # coinbase-international availableSince 2024-10-31 (VenueMapping.
    # venue_start_dates). NOTE: the MVP override
    # (mvp_scope.py CeFiMvpRule.venue_data_types["COINBASE-FUTURES"] =
    # {"trades"}) independently narrows the MVP-scope EXPECTED set to
    # trades-only — that is a SEPARATE concern (Carve-out 2); this entry
    # states genuine capture CAPABILITY (Carve-out 1), not MVP scope.
    "COINBASE-FUTURES": {
        "trades": "2024-10-31",
        "book_snapshot_5": "2024-10-31",
        "derivative_ticker": "2024-10-31",
        "liquidations": "2024-10-31",
    },
    # Coinbase Derivatives Exchange (CDE) — 2026-07-10. Live-only for now: Tardis has
    # ZERO coverage of this venue under any name, so there is no historical/batch
    # source — only the re-keyed coinbase_cde_ws.py live connector (Advanced Trade
    # WS market_trades channel) captures real data. Start date = the date this venue
    # was registered (honest floor — no fabricated pre-registration history; see
    # honest-absence-downstream-handling.md).
    "COINBASE-CDE": {
        "trades": "2026-07-10",
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
    # ICE — narrowed to ohlcv_24h only (2026-07-13, operator decision). No ICE
    # Databento datasets are in the 3-dataset subscription (IFEU.IMPACT/
    # IFUS.IMPACT dropped 2026-06-18), so ohlcv_1m was declared capable with
    # ZERO working fetch path. The only real ICE instrument is the Yahoo-
    # sourced ICE/NYBOT DXY index (ICE:INDEX:DXY-USD), a DAILY series — start
    # date matches YAHOO_INDICES' DXY genesis (tradfi_instrument_universe.py:
    # YahooIndexDef("DXY", "ICE", "DXY", "DX-Y.NYB", date(2019, 1, 2), "fx")),
    # mirroring the KRX convention (both Yahoo-daily, both dated to their
    # registry's real genesis date). See
    # tradfi_ice_ohlcv_1m_no_working_fetch_path_2026_07_13.md.
    "ICE": {
        "ohlcv_24h": "2019-01-02",
    },
    "CBOE": {
        # VX FUTURES (the VIX futures curve) via Databento XCBF.PITCH (the
        # operator's "CFE" subscription, activated 2026-06-19). Both ohlcv-1s +
        # ohlcv-1m are L0/free 16y; coarser bars aggregate downstream. XCBF.PITCH
        # coverage starts 2018-11-04. SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.
        "ohlcv_1s": "2018-11-04",
        "ohlcv_1m": "2018-11-04",
        # ohlcv_24h: US Treasury-yield tenors (US3M/US2Y/US5Y/US10Y/US30Y) via Yahoo
        # daily OHLCV — the Yahoo-sourced fixed_income leg, mirroring the ICE:DXY / KRX
        # Yahoo-daily convention above. Routed by market-tick-data-service@764e7170's
        # data_type discriminator (ohlcv_24h -> Yahoo; VX-futures ohlcv_1s/1m stay on the
        # Databento path untouched). Start = US_TREASURY_YIELD_DAILY_FIRST_DATE (earliest
        # tenor genesis: ^IRX/^FVX/^TNX/^TYX 2000-01-03; US2Y 2018-08-13). ENABLED 2026-07-15
        # per operator decision (data_pipeline_alerts_batch_remediation_2026_07_15) — treasury
        # yields are wanted macro reference data, distinct from the mbp_10/CME MVP-scope gate
        # deliberately left closed (see the tradfi_unreachable_databento_* issue doc).
        "ohlcv_24h": "2000-01-03",
        # ohlcv_15m REMOVED 2026-07-15 (was the VIX cash INDEX — Barchart/Yahoo,
        # "2020-01-07" start; not Databento). That fetch path was retired
        # 2026-06-25/26 (operator) — no adapter serves (CBOE, ohlcv_15m) anymore,
        # so declaring the capability made every request fall through to the
        # Databento path (no 15m schema) and 100% attempted_fail. Matches the
        # already-shipped KRX/ICE narrowing precedent. See
        # tradfi_unreachable_databento_data_types_mbp10_ohlcv_coarse_calendar_2026_07_15.md.
    },
    "FX": {
        "ohlcv_24h": "2020-01-01",  # KRW/USD daily via Yahoo Finance
    },
    # KRX (Korea Exchange) single stocks — Yahoo-sourced (.KS tickers). Real
    # registry gap (2026-07-13, pipeline_e2e_check TRADFI diagnostic pass):
    # this venue had NO entry here at all, so get_expected_data_types_for_venue
    # fell through to a cross-product of ALL 10 TradFi data_types
    # (get_valid_data_types_for_venue), contradicting expected_coverage.py's
    # narrowed KRX entry (below) and the equity-basis MVP carve-out
    # (_mvp_scope_predicate.py), both already scoped to ohlcv_24h-only
    # (2026-07-12/13 operator decision: the only real fetch path,
    # _fetch_yahoo_equities -> YahooFinanceAdapter.download_daily, has no
    # intraday capability — see
    # krx_intraday_ohlcv_registry_vs_adapter_mismatch_2026_07_12.md, resolved).
    # Start date matches venue_mapping.py's KRX floor (2019-01-02, Yahoo daily
    # history probed 2026-06-24).
    "KRX": {
        "ohlcv_24h": "2019-01-02",
    },
    # BARCHART capability block removed 2026-07-15 (wider-sweep audit,
    # cefi_live_only_data_types_vs_layer1_denominator_contradiction issue P3) —
    # BARCHART was removed from VENUES_BY_ASSET_GROUP["tradfi"] 2026-06-24 (VIX
    # 15m now aggregates from VX futures via Databento XCBF.PITCH), making this
    # entry unreachable dead code (expected-universe producers iterate
    # VENUES_BY_ASSET_GROUP, never this dict's keys directly).
    # YAHOO_FINANCE caps block removed 2026-07-15 — source-as-venue modeling error
    # (kept the SOURCE modeling in data_source_continuity.py / _tradfi.py capability).
    # POLYGON (the TradFi reference-data VENDOR, formerly-Polygon.io — NOT the DeFi chain
    # of the same name) capability block REMOVED (found + fixed via the
    # breaking_change_differ_blind_to_registry_data_dicts_2026_07_09.md cross-repo
    # invariant): Polygon.io was removed as a tradfi source 2026-07-19
    # (/codex/02-data/tradfi-databento-sourcing-ssot.md), but this entry — dated
    # 2026-05-23, predating the removal — was never cleaned up. Same unreachable-dead-code
    # class as the BARCHART removal above (VENUES_BY_ASSET_GROUP has no bare "POLYGON"
    # tradfi/reference-data venue; expected-universe producers iterate
    # VENUES_BY_ASSET_GROUP, never this dict's keys directly).
    # Corrected 2026-07-29 (scoping the FRED backfill invocation — see
    # macro_micro_econ_data_capture_audit_2026_06_05.md todo "Scope + build the
    # actual FRED backfill invocation"): the live FredAdapter.write_canonical_shard
    # writes ``yield_curve`` (BOND-classified KEY_SERIES: yield curve/TIPS/rates/
    # spreads/credit) and ``ohlcv_1d`` (INDEX-classified: volatility/inflation/macro)
    # — never ``macro_result``, which this entry previously (and wrongly) declared.
    # Start date mirrors coverage_starts.py's existing per-venue
    # SOURCE_COVERAGE_START["FRED"] = date(1962, 1, 2) (DGS Treasury series depth) —
    # this per-data_type start is necessarily a whole-venue approximation (some
    # KEY_SERIES, e.g. SOFR, start far later; FRED has no per-series start-date axis
    # here). get_expected_data_types_for_venue("FRED") drives the actual pre-flight
    # data_types filter in venue_fetch.py — without this fix a live capture run only
    # ever requested "macro_result", which FredAdapter never emits, so the fetch
    # honest-emptied every day.
    "FRED": {
        "yield_curve": "1962-01-02",
        "ohlcv_1d": "1962-01-02",
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
    # Prediction CLOBs emit canonical "trades" + "book_snapshot_5" (same keys as
    # CeFi). book_snapshot_5 RE-ADDED 2026-06-23 (start 2026-06-22 = live-capture
    # onset): the 2026-04-19 retirement ("phantom-inflated completion_pct") is
    # superseded — BOTH venues now genuinely emit it (LIVE via the CLOB WS
    # connectors top-5 ladder, capturing on prd; BATCH via the REST /book path,
    # mtds@7c849d7). The 2026-06-22 start keeps the denominator honest (pre-onset
    # dates are EXPECTED_PRE_* not gaps), so no completion_pct phantom-inflation.
    # This is the gate `get_expected_data_types_for_venue` reads — REQUIRED so the
    # MTDS batch pre-flight does not drop book_snapshot_5 before the adapter runs.
    "POLYMARKET": {
        "trades": "2024-06-01",
        "book_snapshot_5": "2026-06-22",
    },
    "KALSHI": {
        "trades": "2024-06-01",
        "book_snapshot_5": "2026-06-22",
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


def defi_actual_data_types_not_declared_valid() -> dict[str, frozenset[str]]:
    """DeFi Layer-3 JOIN — ``actual ⊆ theoretical`` audit (two-layer redesign,
    uac_data_type_validity_combinator_fragmentation_2026_07_07.md § "The target
    shape").

    For every ``PROTOCOL-CHAIN`` venue in ``DEFI_VENUE_DATA_TYPE_CAPABILITIES``
    (Layer 2 — actual/genesis: what's declared as genuinely captured, with a
    start date), returns any data_type that is NOT in that protocol's
    ``PROTOCOL_CAPABILITIES`` entry (Layer 1 — theoretical validity: what the
    protocol conceptually CAN produce). A non-empty result means the two
    registries have drifted: something is declared captured that was never
    declared theoretically possible — exactly what finding 2 identified for
    ``oracle_prices`` on the AAVE_V3 family (a real, live-verified 3,160-row
    gap, fixed 2026-07-10 by adding ``oracle_prices`` to ``aave_v3``'s
    declared data_types).

    Scoped to DeFi only (NOT a general CeFi/TradFi ``VENUE_DATA_TYPE_CAPABILITIES``
    checker): unlike DeFi's per-chain dict, the CeFi/TradFi portion of
    ``VENUE_DATA_TYPE_CAPABILITIES`` is a SPARSE start-date OVERRIDE table (a
    venue's dict entry omits any data_type whose start date equals the venue's
    own default launch date — see the module docstring above), so an entry's
    ABSENCE there does not mean "not captured". DeFi's per-chain dict has no
    such default-omission convention (every genuinely-declared data_type for a
    venue is a literal dict key), so the subset check is sound there.

    NOT wired into any runtime hot path — a pure audit/CI helper (see tests).
    A caller wanting the mirror direction (theoretical-declared-but-never-
    captured — finding 2's ``liquidations``/``risk_params`` on Euler/Radiant)
    should cross-reference this function's output against a live manifest
    read; that direction is legitimately EXPECTED for aspirational entries
    (declared-but-not-yet-wired, per this module's own convention) so it is
    NOT flagged as a violation by this function.

    Returns:
        {venue: frozenset[undeclared_data_type]} — empty when Layer 1 and
        Layer 2 are fully reconciled for every DeFi venue.
    """
    from .capability_declarations._defi import PROTOCOL_CAPABILITIES  # noqa: imports-inside-functions

    violations: dict[str, frozenset[str]] = {}
    for venue, actual in DEFI_VENUE_DATA_TYPE_CAPABILITIES.items():
        protocol = venue.split("-", 1)[0].strip().lower()
        cap = PROTOCOL_CAPABILITIES.get(protocol)
        if cap is None:
            for candidate in PROTOCOL_CAPABILITIES.values():
                if candidate.venue_prefix.strip().lower() == protocol:
                    cap = candidate
                    break
        if cap is None:
            continue  # unmapped protocol -- not this audit's concern
        undeclared = frozenset(actual) - frozenset(cap.data_types)
        if undeclared:
            violations[venue] = undeclared
    return violations


# TradFi venue → the writer-grain instrument_types the MTDS writer stamps for it.
# Promoted here 2026-07-03 (honest_coverage_uac_writer_matrix_reconciliation) from
# the instruments-service Layer-1 checker replica so it stops drifting: UAC is the
# shared contract lib both IS and MTDS may import (service↔service imports are
# banned). Writer-side counterpart: market-tick-data-service
# ``symbol_rules._VENUE_INSTRUMENT_TYPE`` holds the per-venue DEFAULT stamp
# (CME/ICE → futures_chain); the richer sets here add the instrument_type-column
# overrides the writer also emits (CME/ICE options_chain + combo, CBOE
# futures/options chains). YAHOO_FINANCE/KRX stamp no instrument_type (legacy
# source-as-venue) and are deliberately absent — consumers must treat a missing
# venue as "not gated", never as "cannot exist".
TRADFI_VENUE_INSTRUMENT_TYPES: dict[str, frozenset[str]] = {
    "CME": frozenset({"futures_chain", "options_chain", "combo"}),
    # "index" added 2026-07-14: the Yahoo-sourced DXY index (ICE:INDEX:DXY-USD,
    # ohlcv_24h) is ICE's only FETCHABLE instrument post-narrowing
    # (tradfi_ice_ohlcv_1m_no_working_fetch_path_2026_07_13.md) and was missing
    # from the could-exist axis. The chain types stay: real HISTORICAL captured
    # rows exist at those grains (finding 1, 2026-07-07) even though their
    # Databento fetch path is retired.
    "ICE": frozenset({"index", "futures_chain", "options_chain", "combo"}),
    "NASDAQ": frozenset({"equity", "etf"}),
    "NYSE": frozenset({"equity", "etf"}),
    "CBOE": frozenset({"index", "futures_chain", "options_chain"}),
    "FX": frozenset({"spot_pair"}),
}


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


# Batch/historical-source capability — a DIFFERENT axis from
# VENUE_DATA_TYPE_CAPABILITIES (which declares the data_type exists for the
# venue AT ALL, live-or-batch, with a start_date). Some (venue, data_type)
# pairs are declared capabilities (they DO exist, captured by a live
# WebSocket connector going forward) but have ZERO viable batch/historical
# source — no vendor archive (Tardis etc.), no venue REST history endpoint,
# nothing. "Short of magic" that historical data cannot be retrieved
# (operator ruling 2026-07-15,
# unified-trading-pm/plans/active/issues/
# cefi_live_only_data_types_vs_layer1_denominator_contradiction_2026_07_12.md):
# such cells must NOT be seeded into the BATCH expected/reachable universe at
# all (no expected_unattempted, no empty_confirmed) — they simply are not a
# batch-mode concern, tracked (if at all) by the live pipeline's own
# event-log/heartbeat accounting, never by this manifest-eu machinery.
#
# This is DELIBERATELY a separate registry from VENUE_DATA_TYPE_CAPABILITIES
# so the live-mode capability declaration is UNTOUCHED (removing these entries
# from VENUE_DATA_TYPE_CAPABILITIES outright would silently tell every live
# consumer the data_type doesn't exist at all — breaking the live pipeline,
# per the operator's 2026-07-15 explicit "NOT deleting the tuple from UAC
# wholesale" instruction).
#
# Moved here from market-tick-data-service's
# `_onchain_perp_batch_live_only.py::LIVE_ONLY_DATA_TYPES` (2026-07-13) per
# the SSOT rule "venue lists + capability declarations are UAC data" — MTDS
# now imports this registry rather than declaring its own copy.
#
# NOT included: COINBASE-CDE/trades — it WAS live-only-no-batch-source when
# the original issue doc was filed (2026-07-12), but market-tick-data-service
# shipped a genuine native-REST batch adapter
# (`adapters/coinbase_cde_batch.py`, mtds@28ad6b38, 2026-07-13) that backfills
# real historical trades — probed live back to 2025-12-12
# (`venue_mapping.py::venue_start_dates["COINBASE-CDE"]`, 2026-07-14). This
# tuple has a real batch source now; it is NOT a "short of magic" case.
#
# Consulted by instruments-service's `expected_universe.py` (Layer-1/Layer-2
# EXPECTED-matrix producer) and `enumerate_expected_universe.py` (the
# per-instrument-day writer that materialises expected_unattempted rows) —
# both make the batch expected-universe seeding BATCH-source-aware.
VENUE_DATA_TYPE_NO_BATCH_SOURCE: dict[str, frozenset[str]] = {
    # ASTER: book endpoint is current-snapshot-only (no historical range
    # param); liquidations feed has no batch OR live source via this venue's
    # adapters (kept here too — harmless superset, matches the proven MTDS
    # dict exactly so nothing is missed in the UAC move).
    "ASTER": frozenset({"book_snapshot_5", "liquidations"}),
    # EXTENDED-STARKNET: same current-snapshot-only book endpoint limitation
    # as ASTER. (PACIFICA (Solana) had the same entry until removed 2026-07-16
    # — operator ruling: all Solana perp DEXes dropped except Jupiter, not
    # integrated.)
    "EXTENDED-STARKNET": frozenset({"book_snapshot_5"}),
    # LIGHTER-ZKSYNC: own REST (/recentTrades, /orderBookOrders) is
    # snapshot-only for BOTH trades and book — no historical range param on
    # either. derivative_ticker (funding) is NOT listed — it has a real batch
    # source via Tardis (see market-tick-data-service's
    # _onchain_perp_batch_lighter.py).
    "LIGHTER-ZKSYNC": frozenset({"trades", "book_snapshot_5"}),
}


def venue_data_type_has_batch_source(venue: str, data_type: str) -> bool:
    """True unless (venue, data_type) is a declared no-batch-source cell.

    A declared capability (``VENUE_DATA_TYPE_CAPABILITIES``) can still lack a
    batch/historical source — this is the batch-vs-live distinction consumers
    building the BATCH expected/reachable universe must apply. Unknown venues
    default to True (no carve-out information == assume batch-capable; the
    existing ``VENUE_DATA_TYPE_CAPABILITIES`` carve-out already excludes
    genuinely undeclared capabilities upstream of this check).
    """
    return data_type not in VENUE_DATA_TYPE_NO_BATCH_SOURCE.get(venue, frozenset())


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
    *,
    for_batch: bool = False,
) -> list[str]:
    """Return the list of data types a venue is expected to produce.

    ``for_batch=True`` additionally drops any data_type declared in
    ``VENUE_DATA_TYPE_NO_BATCH_SOURCE`` for this venue (a real capability the
    venue has, but only via a live-only transport with no historical/batch
    query surface — e.g. LIGHTER-ZKSYNC ``trades``). Callers driving an actual
    BATCH fetch attempt (or its expected-vs-captured sentinel/coverage math)
    MUST pass this so a physically-unattemptable combo is never even seeded
    into the batch expected/reachable universe, per the 2026-07-15 operator
    ruling documented in market-tick-data-service's
    ``_onchain_perp_batch_live_only.py``. Default ``False`` preserves the
    existing "full declared capability, any transport" behavior for every
    other caller (coverage-display / documentation-style consumers that
    legitimately want the complete capability list regardless of transport).

    The capabilities registry is split by service layer:
    - instruments-service → VENUE_REFERENCE_DATA_CAPABILITIES (static metadata)
    - MTDS/MDPS/features → VENUE_DATA_TYPE_CAPABILITIES (market data)

    Market shards (BTC, ETH, SPX for prediction) are emergent from the index
    and not declared in either registry — they appear automatically.

    FOOTGUN / by-design fallback (read before adding a "venue"): when a venue has
    NO ``VENUE_DATA_TYPE_CAPABILITIES`` entry we deliberately fall through to
    ``get_valid_data_types_for_venue`` — the FULL asset-group cross-product (all
    ~10 tradfi / cefi / etc. data_types). This is the INTENDED default for a
    legit venue whose caps are simply not narrowed (e.g. the 5 sports odds venues
    BETFAIR_*/DRAFTKINGS/FANDUEL genuinely rely on it — MTDS produces their data).
    The safety this rests on: ``get_valid_data_types_for_venue`` is empty for a
    venue that is NOT enumerated in ``VENUES_BY_ASSET_GROUP`` (no asset_group → []).
    So a *source-as-venue artifact* (a data SOURCE like Yahoo Finance that has no
    real adapter and no fetch code stamping ``venue=<it>``) must NEVER be listed in
    ``VENUES_BY_ASSET_GROUP`` — if it were, this fallback would silently inflate it
    to all ~10 types and seed phantom EXPECTED cells across the honest-coverage
    denominator. Model such artifacts as a SOURCE only (data_source_continuity.py /
    capability_declarations), never as a venue. There is deliberately NO code guard
    here (it would break the legit empty-caps venues above) — the invariant is
    enforced by simply not enumerating non-venues. (YAHOO_FINANCE was removed as a
    venue on 2026-07-15 for exactly this reason.)

    ``service="market-data-processing-service"`` (MDPS, added
    mtds_data_status_page_parity_2026_07_21) NARROWS the venue's raw-capable
    dt list to :data:`~unified_api_contracts.registry.processed_data_dependencies.MDPS_DERIVABLE_DATA_TYPES`
    — the manifest ``data_type`` axis for MDPS rows is the SOURCE token
    (operator ruling 2026-07-21: "path==manifest on data_type"), the SAME
    vocabulary as MTDS raw-tick rows, so without this narrowing MDPS would
    inherit the full MTDS raw vocabulary (``gas_fees``, ``perp_funding``, ...)
    as "expected", most of which MDPS never candle-derives — producing
    permanent false ``missing_data_types`` and tanking ``completion_pct``.
    """
    if service == "instruments-service":
        ref_caps = VENUE_REFERENCE_DATA_CAPABILITIES.get(venue, {})
        return sorted(ref_caps.keys()) if ref_caps else []
    caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
    dts = sorted(caps.keys()) if caps else get_valid_data_types_for_venue(venue)
    if service == "market-data-processing-service":
        from unified_api_contracts.registry.processed_data_dependencies import (
            MDPS_DERIVABLE_DATA_TYPES,
        )

        dts = sorted(set(dts) & MDPS_DERIVABLE_DATA_TYPES)
    if for_batch:
        dts = [dt for dt in dts if venue_data_type_has_batch_source(venue, dt)]
    return dts


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
        # CeFi catalog reader provides DEX pool instrument IDs for LIGHTER).
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
    explicit_scope: bool = False,
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
    explicit_scope:
        ``True`` when ``instruments_provider`` returns an instrument list the
        CALLER named explicitly (MTDS ``--instrument-ids`` / VM metadata
        ``VM_INSTRUMENT_IDS``), as opposed to a discovered catalog or a seed
        table. An explicit scope is NEVER capped.

        Rationale (2026-07-20 root-cause). ``cap`` exists to bound the Tier-3
        fan-out over an *unbounded, discovered* universe. Applied to an
        explicitly-named list it does not bound anything — it silently DROPS
        instruments the operator asked for. Worse, callers hand this function
        a ``sorted()`` list, so ``resolved[:cap]`` is an **alphabetical
        prefix**: a systematically biased truncation, not a sample.

        Measured damage: the TradFi equity launchers pass 622 sorted tickers;
        ``cap=50`` cut the denominator to ``A..BKNG``, which produced 104,623
        phantom absence rows clustered in tickers A-C (AAPL, AMZN, AVGO, BAC,
        BRK.B, C, CAT ...) and left D-Z with no per-instrument row at all. The
        invariant broke visibly in production: VM log
        ``tradfi-bf-nasdaq-ohlcv-1m-2024-20260719-112444`` reports
        ``expected_instruments=50 captured=58`` — a denominator SMALLER than
        its own numerator.

        This flag is not a tier promotion (tier caps stay operator-gated per
        ``codex/02-data/per-instrument-sentinel-rollout.md`` § 3); it only
        stops the cap from being applied where it was never meaningful.

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

    # An explicitly-named scope is never capped: `resolved` is already exactly
    # what the caller asked for, and `[:cap]` over a sorted list would silently
    # truncate it to an alphabetical prefix (see `explicit_scope` in the
    # docstring for the measured NASDAQ/NYSE damage).
    if cap is not None and cap >= 0 and not explicit_scope:
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
    # tickers; CeFiCatalogReader for DEX pools on LIGHTER). When no
    # catalog reader is registered for a venue, return () so Tier-3 degrades
    # to Tier-2 — same as today's behaviour (no regression on first-boot or
    # test environments where the catalog is absent).
    if data_type == "ohlcv_1m":
        return ()

    # CEFI spot_pair path for `trades` + `book_snapshot_5`. PREDICTION
    # venues also write canonical `trades` (the legacy `prediction_trades`
    # data_type was retired 2026-04-19) so they branch off first.
    if data_type in ("trades", "book_snapshot_5"):
        if venue in ("POLYMARKET", "KALSHI"):
            return seed_for_venue_and_data_type(venue, data_type)
        venue_caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
        # If the venue's capability table doesn't declare this data_type at
        # all, the venue isn't wired to publish it — empty seed so the
        # Tier-3 sentinel doesn't fan out an expectation that can never be
        # satisfied.
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
    # oracle_prices / lst_rates / rewards / risk_params) — delegated to the
    # Wave 8G seed module. (PREDICTION canonical `trades` is served by the
    # POLYMARKET/KALSHI branch above; the legacy `prediction_trades` /
    # `prediction_book_snapshot` / `prediction_market_metadata` data_types were
    # retired 2026-04-19 and are no longer per-instrument shard types.)
    return seed_for_venue_and_data_type(venue, data_type)
