"""DeFi phase-2 schema contracts — flash loans, staking yields, token transfers, bridge events,
position data, MEV events, governance events, and liquidation events.

Split out of ``contracts.py`` to keep the main module under the 900-line
codex-compliance limit. This module is imported at module load time by
``contracts.py`` via a side-effect import so the mutations to
``CONTRACT_REGISTRY`` happen before any consumer performs a lookup.

Do NOT import this module directly — import from
``unified_api_contracts.internal.schemas.contracts`` which re-exports the
public SchemaContract names.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas.contracts import (
    CHAIN_COL,
    CONTRACT_REGISTRY,
    INSTRUMENT_ID_COL,
    TS_EVENT_COL,
    VENUE_COL,
    ColumnSpec,
    SchemaContract,
)

# Aliases for local use
_INSTRUMENT_ID = INSTRUMENT_ID_COL
_TS_EVENT = TS_EVENT_COL
_VENUE = VENUE_COL
_CHAIN = CHAIN_COL

# ---------------------------------------------------------------------------
# DeFi — New data types (defi_data_types_completeness_2026_04_24)
# ---------------------------------------------------------------------------

# Aave V3 / Morpho — LiquidationCall events via subgraph.
# Per-row symbol = collateral asset (e.g. WETH, USDC).
DEFI_LENDING_LIQUIDATION_EVENTS = SchemaContract(
    category="defi",
    instrument_type="lending",
    data_type="liquidation_events",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="collateral_asset", dtype="string", nullable=False),
        ColumnSpec(name="debt_asset", dtype="string", nullable=False),
        ColumnSpec(name="collateral_amount", dtype="float64", nullable=False),
        ColumnSpec(name="debt_amount", dtype="float64", nullable=False),
        ColumnSpec(name="liquidator", dtype="string", nullable=True),
        ColumnSpec(name="user", dtype="string", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=0,
)

# Aave V3 — FlashLoan events via subgraph.
# Per-row symbol = flash loan asset (e.g. WETH, USDC).
DEFI_LENDING_FLASH_LOAN_EVENTS = SchemaContract(
    category="defi",
    instrument_type="lending",
    data_type="flash_loan_events",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="asset", dtype="string", nullable=False),
        ColumnSpec(name="amount", dtype="float64", nullable=False),
        ColumnSpec(name="premium", dtype="float64", nullable=True),
        ColumnSpec(name="initiator", dtype="string", nullable=True),
        ColumnSpec(name="borrower", dtype="string", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=0,
)

# Lido / EigenLayer — staking APY snapshots.
# Per-row symbol = token (e.g. stETH, EIGEN).
DEFI_STAKING_STAKING_YIELDS = SchemaContract(
    category="defi",
    instrument_type="staking",
    data_type="staking_yields",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="apy", dtype="float64", nullable=False),
        ColumnSpec(name="total_staked", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# ERC-20 transfer events for top DeFi tokens.
# Per-row symbol = token ticker (e.g. WETH, USDC).
DEFI_SPOT_ASSET_TOKEN_TRANSFERS = SchemaContract(
    category="defi",
    instrument_type="spot_asset",
    data_type="token_transfers",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="token_address", dtype="string", nullable=False),
        ColumnSpec(name="from_address", dtype="string", nullable=True),
        ColumnSpec(name="to_address", dtype="string", nullable=True),
        ColumnSpec(name="amount", dtype="float64", nullable=False),
        ColumnSpec(name="tx_hash", dtype="string", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Cross-chain bridge transfer events (Across, Stargate, etc.).
# Per-row symbol = token being bridged (e.g. USDC).
DEFI_SPOT_ASSET_BRIDGE_EVENTS = SchemaContract(
    category="defi",
    instrument_type="spot_asset",
    data_type="bridge_events",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="source_chain", dtype="string", nullable=False),
        ColumnSpec(name="dest_chain", dtype="string", nullable=False),
        ColumnSpec(name="token", dtype="string", nullable=False),
        ColumnSpec(name="amount", dtype="float64", nullable=False),
        ColumnSpec(name="depositor", dtype="string", nullable=True),
        ColumnSpec(name="recipient", dtype="string", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=0,
)

# Aave V3 / Uniswap V3 — user position snapshots.
# Per-row symbol = collateral/LP token (e.g. WETH).
DEFI_LENDING_POSITION_DATA = SchemaContract(
    category="defi",
    instrument_type="lending",
    data_type="position_data",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="user", dtype="string", nullable=True),
        ColumnSpec(name="supplied_usd", dtype="float64", nullable=True),
        ColumnSpec(name="borrowed_usd", dtype="float64", nullable=True),
        ColumnSpec(name="health_factor", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# MEV-Boost relay builder/relay stats.
# Per-row symbol = relay name (e.g. FLASHBOTS).
DEFI_SPOT_ASSET_MEV_EVENTS = SchemaContract(
    category="defi",
    instrument_type="spot_asset",
    data_type="mev_events",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="relay", dtype="string", nullable=False),
        ColumnSpec(name="block_number", dtype="int64", nullable=True),
        ColumnSpec(name="builder_pubkey", dtype="string", nullable=True),
        ColumnSpec(name="value_eth", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=0,
)

# DAO proposal + vote events (Compound, Aave, Uniswap).
# Per-row symbol = protocol name (e.g. COMPOUND).
DEFI_SPOT_ASSET_GOVERNANCE_EVENTS = SchemaContract(
    category="defi",
    instrument_type="spot_asset",
    data_type="governance_events",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="proposal_id", dtype="string", nullable=False),
        ColumnSpec(name="event_type", dtype="string", nullable=False),
        ColumnSpec(name="voter", dtype="string", nullable=True),
        ColumnSpec(name="support", dtype="string", nullable=True),
        ColumnSpec(name="votes", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=0,
)

# ---------------------------------------------------------------------------
# DEX pool + swap DataType enum coverage (data_status_institutional_drilldown).
# Distinct from ``dex_pool_state`` / ``dex_pool_swaps`` (canonical MTDS write
# path — see contracts.py): ``dex_pools`` / ``dex_swaps`` here are the raw
# handler-side data-type labels from UAC ``DataType`` enum, matching the
# availability-manifest row emitted by ``dex_pools_handler`` /
# ``dex_swaps_handler`` in market-tick-data-service. Columns mirror the raw
# subgraph-parsed DataFrame before it is rewritten to the canonical
# ``dex_pool_state`` / ``dex_pool_swaps`` schema. UniV3-family pools publish
# ``tick`` / ``sqrt_price_x96`` / ``liquidity``; V2-era pools do not.
# ---------------------------------------------------------------------------

_UNIV3_VENUES: frozenset[str] = frozenset(
    {
        "UNISWAP_V3-ETHEREUM",
        "UNISWAP_V3-ARBITRUM",
        "UNISWAP_V3-BASE",
        "UNISWAP_V3-POLYGON",
        "UNISWAP_V3-OPTIMISM",
        "PANCAKESWAP_V3-BSC",
        "SUSHISWAP_V3-ETHEREUM",
        "SUSHISWAP_V3-ARBITRUM",
    }
)

DEFI_POOL_DEX_POOLS = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pools",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="pool_id", dtype="string", nullable=False),
        ColumnSpec(name="protocol", dtype="string", nullable=False),
        ColumnSpec(name="token_a", dtype="string", nullable=True),
        ColumnSpec(name="token_b", dtype="string", nullable=True),
        ColumnSpec(name="price_a", dtype="float64", nullable=True),
        ColumnSpec(name="price_b", dtype="float64", nullable=True),
        ColumnSpec(name="fee_rate_bps", dtype="int64", nullable=True),
        ColumnSpec(name="tvl_usd", dtype="float64", nullable=True),
        ColumnSpec(name="volume_usd", dtype="float64", nullable=True),
        ColumnSpec(name="fees_usd", dtype="float64", nullable=True),
        ColumnSpec(name="tx_count", dtype="int64", nullable=True),
        ColumnSpec(
            name="liquidity",
            dtype="string",
            nullable=True,
            required=False,
            provided_by_venues=_UNIV3_VENUES,
            description="UniV3/Algebra-fork pools publish raw liquidity; V2 / Messari-basic pools do not.",
        ),
    ],
    symbol_column="pool_id",
    required_row_count_min=0,
)

DEFI_POOL_DEX_SWAPS = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_swaps",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="swap_id", dtype="string", nullable=False),
        ColumnSpec(name="pool_id", dtype="string", nullable=False),
        ColumnSpec(name="protocol", dtype="string", nullable=False),
        ColumnSpec(name="amount0", dtype="float64", nullable=True),
        ColumnSpec(name="amount1", dtype="float64", nullable=True),
        ColumnSpec(name="amount_usd", dtype="float64", nullable=True),
        ColumnSpec(name="sender", dtype="string", nullable=True),
        ColumnSpec(name="recipient", dtype="string", nullable=True),
        # V3-family pools publish tick / sqrt_price_x96 / liquidity per swap;
        # V2-era (Balancer, Curve) swaps carry token_in / token_out / amount_in / amount_out instead.
        ColumnSpec(
            name="tick",
            dtype="int64",
            nullable=True,
            required=False,
            provided_by_venues=_UNIV3_VENUES,
        ),
        ColumnSpec(
            name="sqrt_price_x96",
            dtype="string",
            nullable=True,
            required=False,
            provided_by_venues=_UNIV3_VENUES,
        ),
        ColumnSpec(
            name="liquidity",
            dtype="string",
            nullable=True,
            required=False,
            provided_by_venues=_UNIV3_VENUES,
        ),
    ],
    symbol_column="pool_id",
    required_row_count_min=0,
)

# ---------------------------------------------------------------------------
# Register into CONTRACT_REGISTRY (side-effect on import)
# ---------------------------------------------------------------------------

CONTRACT_REGISTRY.update(
    {
        ("defi", "lending", "liquidation_events"): DEFI_LENDING_LIQUIDATION_EVENTS,
        ("defi", "lending", "flash_loan_events"): DEFI_LENDING_FLASH_LOAN_EVENTS,
        ("defi", "staking", "staking_yields"): DEFI_STAKING_STAKING_YIELDS,
        ("defi", "spot_asset", "token_transfers"): DEFI_SPOT_ASSET_TOKEN_TRANSFERS,
        ("defi", "spot_asset", "bridge_events"): DEFI_SPOT_ASSET_BRIDGE_EVENTS,
        ("defi", "lending", "position_data"): DEFI_LENDING_POSITION_DATA,
        ("defi", "spot_asset", "mev_events"): DEFI_SPOT_ASSET_MEV_EVENTS,
        ("defi", "spot_asset", "governance_events"): DEFI_SPOT_ASSET_GOVERNANCE_EVENTS,
        ("defi", "pool", "dex_pools"): DEFI_POOL_DEX_POOLS,
        ("defi", "pool", "dex_swaps"): DEFI_POOL_DEX_SWAPS,
    }
)
