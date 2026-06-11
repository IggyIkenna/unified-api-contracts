"""DeFi hand-written ``SchemaSpec`` column tuples (CF-18 CITADEL — carry ALL
source columns; operator ratification 2026-06-11 decision #2).

Every tuple below is derived from the ACTUAL prod parquet footers sampled via
the CF-18 audit (``migration_schema_completeness.py`` riding the
``orphan_sweep_defi.parquet`` object list, 3-5 objects per
(data_type, venue) cell, 2026-06-11) cross-checked against the writing MTDS
handlers (``market_tick_data_service/cli/handlers/*``). CamelCase
subgraph-native legacy columns are canonicalised to snake_case with the raw
name declared in ``source_aliases`` (the migrator rename map); columns whose
physical name already matches the convention carry no alias.

Sampled shapes covered:

- ``dex_pool_state`` / ``dex_pool_swaps`` — legacy ``category=`` corpus:
  CURVE (pool-balance window), UNISWAP_V2 (pair hourly window), UNISWAP_V3
  (pool-hour candle + fee growth), UNISWAP_V4 (pool-hour candle + pool_id).
  One shared union: the legacy writer emitted the same frame to both paths.
- ``dex_pools`` / ``dex_swaps`` — current Solana/EVM writers (ORCA, RAYDIUM,
  AERODROME_V3, BALANCER, CAMELOT_V3, CURVE, PANCAKESWAP_V3, SUSHISWAP,
  SUSHISWAP_V3, UNISWAP_V3), already snake_case.
- ``lending_indices`` — Solana lenders (KAMINO, MARGINFI, SOLEND) on top of
  the original EVM a_token index shape.
- ``lst_rates`` — MARINADE.
- ``oracle_prices`` / ``rate_indices`` / ``risk_params`` / ``utilization`` —
  the AAVE_V3 reserve snapshot (one physical frame written to 4 data_type
  paths) + LST oracles (ETHENA / ETHERFI / LIDO) + MORPHO market indices.
- ``rewards`` — EIGENLAYER restaking rewards + ETHERFI LST reward snapshot.
"""

from __future__ import annotations

from unified_api_contracts.registry._schema_spec_types import ColumnSpec, merge_columns

# ---------------------------------------------------------------------------
# Legacy subgraph pool window (dex_pool_state + dex_pool_swaps share it)
# ---------------------------------------------------------------------------

DEFI_POOL_WINDOW_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("pool_address", "string", nullable=True),
    ColumnSpec("pair_address", "string", nullable=True, description="UNISWAP_V2 pair contract"),
    ColumnSpec("pool_id", "string", nullable=True, description="UNISWAP_V4 pool id (hash)"),
    ColumnSpec("entity_id", "string", nullable=True, source_aliases=("id",), description="Subgraph entity id"),
    ColumnSpec(
        "instrument_key", "string", nullable=True, description="Legacy pre-v9 instrument key (carried verbatim)"
    ),
    ColumnSpec("block_number", "int64", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True, description="Source event/window timestamp"),
    ColumnSpec("tx_hash", "string", nullable=True),
    ColumnSpec("tx_count", "int64", nullable=True, source_aliases=("txCount",)),
    ColumnSpec("sender", "string", nullable=True),
    ColumnSpec("to_address", "string", nullable=True, source_aliases=("to",), description="Swap recipient"),
    # Uniswap V2/V3/V4 amounts
    ColumnSpec("amount0", "float64", nullable=True),
    ColumnSpec("amount1", "float64", nullable=True),
    ColumnSpec("amount0_in", "float64", nullable=True),
    ColumnSpec("amount0_out", "float64", nullable=True),
    ColumnSpec("amount1_in", "float64", nullable=True),
    ColumnSpec("amount1_out", "float64", nullable=True),
    ColumnSpec("amount_usd", "float64", nullable=True, source_aliases=("amountUSD",)),
    # Curve directional amounts
    ColumnSpec("amount_in", "float64", nullable=True),
    ColumnSpec("amount_in_usd", "float64", nullable=True),
    ColumnSpec("amount_out", "float64", nullable=True),
    ColumnSpec("amount_out_usd", "float64", nullable=True),
    ColumnSpec("token_in", "string", nullable=True),
    ColumnSpec("token_in_address", "string", nullable=True),
    ColumnSpec("token_out", "string", nullable=True),
    ColumnSpec("token_out_address", "string", nullable=True),
    ColumnSpec("pool_balances", "string", nullable=True, description="JSON-serialized per-token pool balances (Curve)"),
    ColumnSpec("total_liquidity_tokens", "float64", nullable=True, description="Curve LP token supply"),
    ColumnSpec("virtual_price", "float64", nullable=True, description="Curve pool virtual price"),
    # Token metadata
    ColumnSpec("token0_address", "string", nullable=True),
    ColumnSpec("token0_symbol", "string", nullable=True),
    ColumnSpec("token1_address", "string", nullable=True),
    ColumnSpec("token1_symbol", "string", nullable=True),
    # Pair reserves (V2)
    ColumnSpec("reserve0", "float64", nullable=True),
    ColumnSpec("reserve1", "float64", nullable=True),
    ColumnSpec("reserve_usd", "float64", nullable=True, source_aliases=("reserveUSD",)),
    ColumnSpec("hourly_txns", "int64", nullable=True, source_aliases=("hourlyTxns",)),
    ColumnSpec("hourly_volume_token0", "float64", nullable=True, source_aliases=("hourlyVolumeToken0",)),
    ColumnSpec("hourly_volume_token1", "float64", nullable=True, source_aliases=("hourlyVolumeToken1",)),
    ColumnSpec("hourly_volume_usd", "float64", nullable=True, source_aliases=("hourlyVolumeUSD",)),
    # Pool-hour candle (V3/V4 subgraph poolHourData)
    ColumnSpec("open", "float64", nullable=True),
    ColumnSpec("high", "float64", nullable=True),
    ColumnSpec("low", "float64", nullable=True),
    ColumnSpec("close", "float64", nullable=True),
    ColumnSpec("liquidity", "float64", nullable=True),
    ColumnSpec("sqrt_price", "float64", nullable=True, source_aliases=("sqrtPrice",)),
    ColumnSpec(
        "sqrt_price_x96",
        "string",
        nullable=True,
        source_aliases=("sqrtPriceX96",),
        description="Q64.96 fixed-point as string",
    ),
    ColumnSpec("tick", "int64", nullable=True),
    ColumnSpec("token0_price", "float64", nullable=True, source_aliases=("token0Price",)),
    ColumnSpec("token1_price", "float64", nullable=True, source_aliases=("token1Price",)),
    ColumnSpec("fee_growth_global0_x128", "string", nullable=True, source_aliases=("feeGrowthGlobal0X128",)),
    ColumnSpec("fee_growth_global1_x128", "string", nullable=True, source_aliases=("feeGrowthGlobal1X128",)),
    ColumnSpec("fees_usd", "float64", nullable=True, source_aliases=("feesUSD",)),
    ColumnSpec("tvl_usd", "float64", nullable=True, source_aliases=("tvlUSD",)),
    ColumnSpec("volume_token0", "float64", nullable=True, source_aliases=("volumeToken0",)),
    ColumnSpec("volume_token1", "float64", nullable=True, source_aliases=("volumeToken1",)),
    ColumnSpec("volume_usd", "float64", nullable=True, source_aliases=("volumeUSD",)),
    ColumnSpec(
        "source",
        "string",
        nullable=True,
        source_aliases=("data_source",),
        description="Row-level provenance (legacy data_source)",
    ),
)

# ---------------------------------------------------------------------------
# Current Solana/EVM DEX writers (snake_case already)
# ---------------------------------------------------------------------------

DEFI_DEX_POOLS_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("pool_id", "string"),
    ColumnSpec("pool_type", "string", nullable=True, description="RAYDIUM classic vs CLMM"),
    ColumnSpec("protocol", "string"),
    ColumnSpec("symbol", "string"),
    ColumnSpec("token_a", "string"),
    ColumnSpec("token_b", "string"),
    ColumnSpec("price", "float64", nullable=True),
    ColumnSpec("tvl_usd", "float64", nullable=True),
    ColumnSpec("volume_usd", "float64", nullable=True),
    ColumnSpec("volume_week", "float64", nullable=True),
    ColumnSpec("volume_month", "float64", nullable=True),
    ColumnSpec("fee_rate_bps", "float64", nullable=True),
    ColumnSpec("fee_apr_day", "float64", nullable=True),
    ColumnSpec("fee_apr_week", "float64", nullable=True),
    ColumnSpec("fee_apr_month", "float64", nullable=True),
    ColumnSpec("tick_spacing", "int64", nullable=True, description="ORCA whirlpool tick spacing"),
    ColumnSpec("timestamp", "timestamp[us, UTC]"),
)

DEFI_DEX_SWAPS_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("swap_id", "string"),
    ColumnSpec("timestamp", "timestamp[us, UTC]"),
    ColumnSpec("protocol", "string"),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("pool_id", "string", nullable=True),
    ColumnSpec("pool_address", "string", nullable=True),
    ColumnSpec("pool_name", "string", nullable=True),
    ColumnSpec("pair_address", "string", nullable=True),
    ColumnSpec("token_a", "string", nullable=True),
    ColumnSpec("token_b", "string", nullable=True),
    ColumnSpec("token_in", "string", nullable=True),
    ColumnSpec("token_out", "string", nullable=True),
    ColumnSpec("amount0", "float64", nullable=True),
    ColumnSpec("amount1", "float64", nullable=True),
    ColumnSpec("amount_in", "float64", nullable=True),
    ColumnSpec("amount_in_usd", "float64", nullable=True),
    ColumnSpec("amount_out", "float64", nullable=True),
    ColumnSpec("amount_out_usd", "float64", nullable=True),
    ColumnSpec("amount_usd", "float64", nullable=True),
    ColumnSpec("fee_rate_bps", "float64", nullable=True),
    ColumnSpec("tick", "int64", nullable=True),
    ColumnSpec("sender", "string", nullable=True),
    ColumnSpec("recipient", "string", nullable=True),
    ColumnSpec("caller", "string", nullable=True, description="BALANCER vault caller"),
    ColumnSpec("user", "string", nullable=True, description="BALANCER swap user"),
    ColumnSpec("tx_hash", "string", nullable=True),
)

# ---------------------------------------------------------------------------
# Lending / LST / oracle shapes
# ---------------------------------------------------------------------------

DEFI_LENDING_INDICES_SOLANA_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("protocol", "string", nullable=True),
    ColumnSpec("market_id", "string", nullable=True),
    ColumnSpec("apy", "float64", nullable=True, description="Net borrow APY (Solana lenders)"),
    ColumnSpec("supply_apy", "float64", nullable=True),
    ColumnSpec("reward_apy", "float64", nullable=True),
    ColumnSpec("tvl_usd", "float64", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True),
    ColumnSpec("data_quality", "string", nullable=True, description="Writer data-quality marker (MARGINFI)"),
)

DEFI_LST_RATES_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("token", "string"),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("protocol", "string", nullable=True),
    ColumnSpec("quote_asset", "string", nullable=True),
    ColumnSpec("exchange_rate", "float64"),
    ColumnSpec("apy", "float64", nullable=True),
    ColumnSpec("total_staked", "float64", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]"),
)

# The AAVE_V3 reserve snapshot — ONE physical frame the legacy EVM handler
# wrote to oracle_prices / rate_indices / risk_params / utilization.
DEFI_AAVE_RESERVE_SNAPSHOT_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("token", "string", nullable=True),
    ColumnSpec(
        "instrument_key", "string", nullable=True, description="Legacy pre-v9 instrument key (carried verbatim)"
    ),
    ColumnSpec("block_number", "int64", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True),
    ColumnSpec("oracle_price", "float64", nullable=True),
    ColumnSpec("oracle_price_usd", "float64", nullable=True),
    ColumnSpec("price_usd", "float64", nullable=True),
    ColumnSpec("liquidity_index", "float64", nullable=True),
    ColumnSpec("variable_borrow_index", "float64", nullable=True),
    ColumnSpec("liquidity_rate_apy", "float64", nullable=True),
    ColumnSpec("supply_rate_apy", "float64", nullable=True),
    ColumnSpec("borrow_rate_apy", "float64", nullable=True),
    ColumnSpec("variable_borrow_rate_apy", "float64", nullable=True),
    ColumnSpec("stable_borrow_rate_apy", "float64", nullable=True),
    ColumnSpec("total_supply", "float64", nullable=True),
    ColumnSpec("total_borrow", "float64", nullable=True),
    ColumnSpec("utilization_rate", "float64", nullable=True),
    ColumnSpec("ltv", "float64", nullable=True),
    ColumnSpec("liquidation_threshold", "float64", nullable=True),
    ColumnSpec("liquidation_bonus", "float64", nullable=True),
    ColumnSpec("reserve_factor", "float64", nullable=True),
    ColumnSpec("emode_category_id", "int64", nullable=True),
    ColumnSpec(
        "source",
        "string",
        nullable=True,
        source_aliases=("data_source",),
        description="Row-level provenance (legacy data_source)",
    ),
)

# LST oracle snapshot (ETHENA sUSDe / ETHERFI weETH / LIDO wstETH).
DEFI_LST_ORACLE_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("token", "string", nullable=True),
    ColumnSpec(
        "instrument_key", "string", nullable=True, description="Legacy pre-v9 instrument key (carried verbatim)"
    ),
    ColumnSpec("block_number", "int64", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True),
    ColumnSpec("oracle_price", "float64", nullable=True),
    ColumnSpec("price_usd", "float64", nullable=True),
    ColumnSpec("eth_price_usd", "float64", nullable=True),
    ColumnSpec("exchange_rate_eth", "float64", nullable=True),
    ColumnSpec("daily_yield_pct", "float64", nullable=True),
    ColumnSpec("reward_per_eeth", "float64", nullable=True),
    ColumnSpec("reward_token", "string", nullable=True),
    ColumnSpec("reward_type", "string", nullable=True),
    ColumnSpec("data_quality", "string", nullable=True),
    ColumnSpec("source", "string", nullable=True, source_aliases=("data_source",)),
)

DEFI_ORACLE_PRICES_COLUMNS: tuple[ColumnSpec, ...] = merge_columns(
    DEFI_AAVE_RESERVE_SNAPSHOT_COLUMNS,
    DEFI_LST_ORACLE_COLUMNS,
    (ColumnSpec("feed", "string", nullable=True, description="Oracle feed id (chainlink/pyth current writer)"),),
)

DEFI_RATE_INDICES_COLUMNS: tuple[ColumnSpec, ...] = merge_columns(
    DEFI_AAVE_RESERVE_SNAPSHOT_COLUMNS,
    (
        # MORPHO market index shape
        ColumnSpec("supply_index", "float64", nullable=True),
        ColumnSpec("borrow_index", "float64", nullable=True),
        ColumnSpec("supply_apy", "float64", nullable=True),
        ColumnSpec("borrow_apy", "float64", nullable=True),
        ColumnSpec("input_token_price_usd", "float64", nullable=True),
        ColumnSpec("tvl_usd", "float64", nullable=True),
    ),
)

DEFI_REWARDS_COLUMNS: tuple[ColumnSpec, ...] = merge_columns(
    (
        # EIGENLAYER restaking reward events
        ColumnSpec("earner", "string", nullable=True),
        ColumnSpec("amount", "float64", nullable=True),
        ColumnSpec("amount_eth", "float64", nullable=True),
        ColumnSpec("amount_usd", "float64", nullable=True),
        ColumnSpec("usd_price", "float64", nullable=True),
        ColumnSpec("token_address", "string", nullable=True),
        ColumnSpec("token_symbol", "string", nullable=True),
        ColumnSpec("eigenlayer_tvl_usd", "float64", nullable=True),
    ),
    DEFI_LST_ORACLE_COLUMNS,
)

__all__ = [
    "DEFI_AAVE_RESERVE_SNAPSHOT_COLUMNS",
    "DEFI_DEX_POOLS_COLUMNS",
    "DEFI_DEX_SWAPS_COLUMNS",
    "DEFI_LENDING_INDICES_SOLANA_COLUMNS",
    "DEFI_LST_ORACLE_COLUMNS",
    "DEFI_LST_RATES_COLUMNS",
    "DEFI_ORACLE_PRICES_COLUMNS",
    "DEFI_POOL_WINDOW_COLUMNS",
    "DEFI_RATE_INDICES_COLUMNS",
    "DEFI_REWARDS_COLUMNS",
]
