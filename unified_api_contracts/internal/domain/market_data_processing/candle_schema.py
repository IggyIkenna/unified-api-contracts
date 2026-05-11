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


__all__ = ["DataType", "MarketState"]
