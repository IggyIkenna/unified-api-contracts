"""Market-data-processing candle schema — market state and data type enumerations.

These enums are the SSOT for market-state classification and data-type routing
used by market-data-processing-service adapters, calculators, and writers.

MarketState is written into every candle row as the ``market_state`` column;
downstream services (features-delta-one, etc.) filter out non-NORMAL candles.

DataType drives schema selection (SCHEMA_BY_DATA_TYPE in models.py) and GCS
path construction.
"""

from __future__ import annotations

from enum import StrEnum


class MarketState(StrEnum):
    """Classification of the market session for a candle time window."""

    NORMAL = "normal"
    HALTED = "halted"
    AUCTION = "auction"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    CLOSED = "closed"


class DataType(StrEnum):
    """Canonical data-type identifiers used to select processing schemas and GCS paths."""

    TRADES = "trades"
    BOOK_SNAPSHOT_5 = "book_snapshot_5"
    DERIVATIVE_TICKER = "derivative_ticker"
    LIQUIDATIONS = "liquidations"
    OHLCV_1M = "ohlcv_1m"
    OHLCV_15M = "ohlcv_15m"
    OHLCV_24H = "ohlcv_24h"
    TBBO = "tbbo"
    # NOTE (A11c 2026-06-02): these two legacy candle-input members are LEFT on the
    # pre-collapse values deliberately. The operator-locked canonical pool/swap names
    # are `dex_pool_state` / `dex_pool_swaps`, but this enum ALSO declares a DISTINCT
    # Phase-2 member `DEX_POOL_STATE = "dex_pool_state"` (spot-DEX time-series state,
    # declared below) — renaming DEX_POOLS's VALUE to `dex_pool_state` would
    # StrEnum-alias-collide the two members. These members are not consumed by
    # member-name anywhere; the canonical collapse is enforced on the functional
    # denominator/capability registries (market_data_categories / expected_coverage /
    # defi_venue_capabilities). Reconciling this enum (merge legacy DEX_POOLS/DEX_SWAPS
    # into the Phase-2 DEX_POOL_STATE taxonomy, resolving snapshot-vs-timeseries) is the
    # tracked follow-up A11c-candle-enum in defi_manifest_canonicalisation_2026_06_01.md.
    DEX_POOLS = "dex_pools"
    DEX_SWAPS = "dex_swaps"
    LENDING_INDICES = "lending_indices"
    # Per-protocol lending-rate breakouts (folded in from
    # plans/active/defi_recursive_borrow_archetypes_2026_05_10.md Phase 1
    # via plans/active/defi_catalogue_chain_primitives_2026_05_10.md
    # Phase 1-LENDING per Q11 ratification 2026-05-10). LENDING_INDICES
    # remains the coarse-grain aggregate; per-protocol adapters
    # (Aave V3 / Compound V3 / Spark / Morpho) classify into the granular
    # variants when the subgraph response carries the underlying field.
    SUPPLY_APY = "supply_apy"
    BORROW_APY = "borrow_apy"
    UTILISATION = "utilisation"
    LIQUIDATION_THRESHOLD = "liquidation_threshold"
    EMODE_PARAMS = "emode_params"
    PERP_FUNDING = "perp_funding"
    # Solana basis-trading MVP scope (plan:
    # plans/active/solana_basis_trading_mvp_2026_06_01.md Phase 1+2).
    # `PERP_TRADES` is per-fill ground truth for CLOB / hybrid-AMM venues
    # (Drift V2 backtest); `PERP_MARK_ORACLE` + `PERP_OPEN_INTEREST` are
    # downstream-consumable derivatives of `PERP_FUNDING` row columns
    # (`oraclePriceTwap`/`markPriceTwap` and `baseAssetAmountWithAmm`).
    PERP_TRADES = "perp_trades"
    PERP_MARK_ORACLE = "perp_mark_oracle"
    PERP_OPEN_INTEREST = "perp_open_interest"
    # Spot DEX time-series state (distinct from the existing `DEX_POOLS`
    # *snapshot* type already declared above). `DEX_POOL_STATE` carries
    # reserves OR concentrated-liquidity tick arrays at block heights for
    # backtest replay. `DEX_ORDERBOOK` is CLOB-style bid/ask levels at
    # block heights (Phoenix). `DEX_QUOTE` is aggregator-sampled quote
    # responses (Jupiter). `DEX_TRADES` is per-swap fill events on AMM
    # venues (Orca/Raydium swap event stream).
    DEX_POOL_STATE = "dex_pool_state"
    DEX_ORDERBOOK = "dex_orderbook"
    DEX_QUOTE = "dex_quote"
    DEX_TRADES = "dex_trades"
    LST_RATES = "lst_rates"
    ORACLE_PRICES = "oracle_prices"
    GAS_FEES = "gas_fees"
    OPTIONS_CHAIN = "options_chain"
    FUTURES_CHAIN = "futures_chain"
    COMBO_CHAIN = "combo_chain"
    SPORTS_ARBITRAGE = "sports_arbitrage"
    SPORTS_ODDS_SNAPSHOT = "sports_odds_snapshot"
    SPORTS_ODDS_MOVEMENT = "sports_odds_movement"
    LIQUIDATION_EVENTS = "liquidation_events"
    FLASH_LOAN_EVENTS = "flash_loan_events"
    STAKING_YIELDS = "staking_yields"
    TOKEN_TRANSFERS = "token_transfers"
    BRIDGE_EVENTS = "bridge_events"
    POSITION_DATA = "position_data"
    MEV_EVENTS = "mev_events"
    GOVERNANCE_EVENTS = "governance_events"
    EIGENLAYER_REWARDS = "eigenlayer_rewards"
    NATIVE_STAKING_RATES = "native_staking_rates"
    AGGREGATOR_ROUTE = "aggregator_route"


__all__ = ["DataType", "MarketState"]
