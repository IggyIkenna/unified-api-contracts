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
    }
)
