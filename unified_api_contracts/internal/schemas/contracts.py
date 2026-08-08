"""Declarative per-(asset_group, instrument_type, data_type) dataframe schema contracts.

Phase 1.3 of data_canonicalisation_mvp_2026_04_17, expanded under gates G3+G7
(zero silent drops + typed SchemaContract lookup on every read/migration).

Provides a minimal framework for validating pandas DataFrames written/read by
downstream data services (MTDS, instruments-service, features services, ML
pipelines) against a declarative schema. A ``SchemaContract`` names every
required column, its dtype, whether nulls are permitted, per-column null rate
caps, and — crucially — the ``symbol_column`` that migration/read pipelines
must use to extract the per-row instrument symbol. Row-count floors can be
enforced as a basic sanity gate.

Downstream services look up the canonical contract from
:data:`CONTRACT_REGISTRY` using the ``(asset_group, instrument_type, data_type)``
tuple. For venue/protocol-specific schemas (e.g. Aave V3's
``liquidity_index``/``variable_borrow_index`` vs Compound V3's ``supply_rate``)
use :func:`lookup_contract` which consults :data:`VENUE_CONTRACT_OVERRIDES`
first and falls back to the base registry. New (asset_group, instrument_type,
data_type) triples are added by appending to the module-level contract
constants and the registry below — this module is the single source of truth.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

DtypeLiteral = Literal[
    "string",
    "int64",
    "int32",
    "float64",
    "float32",
    "bool",
    "datetime64[ns, UTC]",
    "decimal",
]

AssetGroupLiteral = Literal[
    "cefi",
    "tradfi",
    "defi",
    "sports",
    "prediction",
    "onchain",
    # Meta-dimensions for manifest-only contracts (Phase 5d.1).
    "ml_training",
    "ml_inference",
]

ViolationKind = Literal[
    "missing_column",
    "wrong_dtype",
    "null_rate_exceeded",
    "row_count_too_low",
    "extra_required_null",
]


class ColumnSpec(BaseModel):
    """Declarative spec for a single dataframe column.

    ``required`` and ``provided_by_venues`` let us model schemas where a column
    is optional overall (not every venue publishes it) without losing the
    ability to hard-enforce its presence for the venues that do.

    - ``required=False`` → column may be absent entirely on any venue.
    - ``required=True`` (default) + ``provided_by_venues=None`` (default) →
      column must be present for every venue writing this schema.
    - ``required=True`` + ``provided_by_venues=frozenset({...})`` → column is
      required only when the writing venue is in that set; absent is OK
      otherwise (e.g. Deribit publishes ``mark_iv`` on ``options_chain`` but
      IBKR does not).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    dtype: DtypeLiteral
    nullable: bool = False
    required: bool = True
    provided_by_venues: frozenset[str] | None = None
    description: str | None = None


CadenceLiteral = Literal["singleton", "per_season", "per_day"]
"""Refdata cadence — how often a data_type's shard atom changes (C.11 audit
2026-05-07, manifest_migration_SUPERSEDED_2026_05_21.md § Audit findings).

* ``"singleton"`` — one shard per (asset_group, data_type) total. Source
  data effectively never changes (e.g. VENUES geo coordinates). Manifest
  expected denominator = 1, regardless of date range.
* ``"per_season"`` — one shard per (entity, season) tuple. Source data
  changes per-season at most (e.g. TEAMS rosters refresh at season start;
  league registries refresh per FootyStats season). Manifest expected
  denominator = (entities x active_seasons), NOT (entities x days).
* ``"per_day"`` — one shard per (entity, day) tuple. Source data is
  genuinely time-series with daily resolution (CeFi ohlcv_*, sports
  FIXTURES). Manifest expected denominator = (entities x days).

Default is ``"per_day"`` for back-compat — existing contracts that don't
declare cadence keep their per-day shard atom. New refdata contracts MUST
declare cadence explicitly. Data-status panel reads this field to compute
cadence-aware expected denominators (instead of the default
entities x days everything).
"""


class SchemaContract(BaseModel):
    """Declarative contract for a per-(asset_group, instrument_type, data_type) dataframe.

    The ``symbol_column`` field names the column that per-row migration /
    read pipelines must consult to extract the instrument symbol for partition
    path construction and canonical ``instrument_id`` building. Defaults to
    ``"symbol"`` for back-compat with the ten original Phase-1.3 contracts;
    every new contract declares it explicitly so guessing (symbol → token →
    pool_id → asset) is eliminated at the root.

    The ``cadence`` field (added 2026-05-07 under the C.11 refdata-cadence
    audit) names the shard atom's renewal frequency: ``"singleton"`` |
    ``"per_season"`` | ``"per_day"``. Used by the data-status panel to
    compute expected denominators correctly — without it, refdata that
    only changes per-season (TEAMS, STANDINGS) gets denominator-inflated
    across every date in the window and renders thousands of phantom-
    missing days. Default ``"per_day"`` preserves back-compat for the
    existing per-day-cadence contracts (CeFi ohlcv_*, sports FIXTURES,
    etc.); new refdata contracts MUST declare cadence explicitly.
    """

    model_config = ConfigDict(frozen=True)

    asset_group: AssetGroupLiteral
    instrument_type: str
    data_type: str
    columns: list[ColumnSpec]
    symbol_column: str = "symbol"
    required_row_count_min: int = 0
    null_rate_max: dict[str, float] = Field(default_factory=dict)
    cadence: CadenceLiteral = "per_day"


class Violation(BaseModel):
    """Single contract violation returned by :func:`validate_dataframe`."""

    model_config = ConfigDict(frozen=True)

    kind: ViolationKind
    column: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Validation — implementation lives in ``_validation.py`` to keep this module
# under the 900-line codex-compliance limit. Imported here for back-compat so
# callers keep using ``from ...schemas.contracts import validate_dataframe``.
# ---------------------------------------------------------------------------

from unified_api_contracts.internal.schemas._validation import (
    validate_dataframe as validate_dataframe,
)

# ---------------------------------------------------------------------------
# Built-in column specs (shared building blocks)
# ---------------------------------------------------------------------------

_INSTRUMENT_ID = ColumnSpec(
    name="instrument_id",
    dtype="string",
    nullable=False,
    description="Canonical instrument identifier (see Phase 1.2 builder).",
)
_TS_EVENT = ColumnSpec(
    name="ts_event",
    dtype="datetime64[ns, UTC]",
    nullable=False,
    description="UTC event timestamp.",
)
_SYMBOL = ColumnSpec(name="symbol", dtype="string", nullable=False)
_SIDE = ColumnSpec(name="side", dtype="string", nullable=False)
_PRICE = ColumnSpec(name="price", dtype="float64", nullable=False)
_SIZE = ColumnSpec(name="size", dtype="float64", nullable=False)
_UNDERLYING = ColumnSpec(name="underlying", dtype="string", nullable=False)
_STRIKE = ColumnSpec(name="strike", dtype="float64", nullable=False)
_EXPIRY_DATE = ColumnSpec(name="expiry_date", dtype="datetime64[ns, UTC]", nullable=False)
_OPTION_RIGHT = ColumnSpec(name="option_right", dtype="string", nullable=False)
_VENUE = ColumnSpec(name="venue", dtype="string", nullable=False)
_CHAIN = ColumnSpec(name="chain", dtype="string", nullable=False)

# Public aliases for cross-module use inside this package (avoids
# reportPrivateUsage when sibling modules like ``_legacy_venue_overrides``
# or ``_sports_prediction_contracts`` reference these shared building
# blocks).
INSTRUMENT_ID_COL = _INSTRUMENT_ID
TS_EVENT_COL = _TS_EVENT
SYMBOL_COL = _SYMBOL
SIDE_COL = _SIDE
PRICE_COL = _PRICE
SIZE_COL = _SIZE
UNDERLYING_COL = _UNDERLYING
STRIKE_COL = _STRIKE
EXPIRY_DATE_COL = _EXPIRY_DATE
OPTION_RIGHT_COL = _OPTION_RIGHT
VENUE_COL = _VENUE
CHAIN_COL = _CHAIN

# ---------------------------------------------------------------------------
# Built-in contracts — CeFi
# ---------------------------------------------------------------------------

CEFI_PERPETUAL_TRADES = SchemaContract(
    asset_group="cefi",
    instrument_type="perpetual",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
    symbol_column="symbol",
    required_row_count_min=1,
)

# The real Tardis book_snapshot_5 wire/write format (verified against
# tardis_csv_transport.py's own pyarrow ConvertOptions and the ONLY real
# consumer, market-data-processing-service's book_snapshot_adapter.py, which
# maps these exact column names to ask_price_i/ask_volume_i/bid_price_i/
# bid_volume_i) is 5 flat per-level columns per side, never a single
# serialised "bids"/"asks" string -- no writer ever produced that shape and
# no reader ever consumed it (cefi_book_snapshot5_schema_contract_ts_event_
# levels_mismatch_2026_07_28.md). Replaces the aspirational single-string
# ColumnSpec pair that was never implemented, exposed the moment validate=True
# was flipped on for every CeFi Tardis write site (2026-07-27).
#
# nullable=True (corrected 2026-07-31, same issue doc, §"deep-level nullable
# gap"): a real order book legitimately does not always carry 5 resting
# levels on both sides -- illiquid/thin pairs (e.g. a newly-listed quote
# asset) routinely have Tardis emit NaN for the deeper levels[2..4] at a
# given snapshot instant. The ORIGINAL nullable=False (2026-07-28) rejected
# every such thin-book row as a FATAL schema violation (raising before any
# write), silently discarding real market data and re-failing continuously as
# backfills work through low-liquidity symbol/date combinations -- confirmed
# via direct reproduction against finalise_rows_and_path with a partial-depth
# row. The write-time gate's job is to catch malformed writes (wrong dtype,
# missing required columns), not to reject an honestly-thin book; the ONLY
# real consumer already NaN-tolerates throughout (book_snapshot_adapter.py's
# time-weighted stats mask on ~np.isnan). Mirrors the existing nullable=True
# precedent for CEFI_PERPETUAL_DERIVATIVE_TICKER's funding_rate/open_interest/
# mark_price/index_price -- another "legitimately absent per-row" numeric set.
_BOOK_SNAPSHOT_5_LEVEL_COLUMNS = [
    ColumnSpec(
        name=f"{side}[{level}].{field}",
        dtype="float64",
        nullable=True,
        description=(
            f"Level-{level} {side[:-1]} {field} (top-5 book_snapshot_5 depth; "
            f"absent/NaN when the book has fewer than {level + 1} levels on this side)."
        ),
    )
    for side in ("bids", "asks")
    for level in range(5)
    for field in ("price", "amount")
]

CEFI_PERPETUAL_BOOK_SNAPSHOT_5 = SchemaContract(
    asset_group="cefi",
    instrument_type="perpetual",
    data_type="book_snapshot_5",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        *_BOOK_SNAPSHOT_5_LEVEL_COLUMNS,
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_PERPETUAL_DERIVATIVE_TICKER = SchemaContract(
    asset_group="cefi",
    instrument_type="perpetual",
    data_type="derivative_ticker",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="funding_rate", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="mark_price", dtype="float64", nullable=True),
        ColumnSpec(name="index_price", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_PERPETUAL_LIQUIDATIONS = SchemaContract(
    asset_group="cefi",
    instrument_type="perpetual",
    data_type="liquidations",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_PERPETUAL_QUOTES = SchemaContract(
    asset_group="cefi",
    instrument_type="perpetual",
    data_type="quotes",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="bid_price", dtype="float64", nullable=False),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=False),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_SPOT_PAIR_TRADES = SchemaContract(
    asset_group="cefi",
    instrument_type="spot_pair",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_SPOT_PAIR_BOOK_SNAPSHOT_5 = SchemaContract(
    asset_group="cefi",
    instrument_type="spot_pair",
    data_type="book_snapshot_5",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        *_BOOK_SNAPSHOT_5_LEVEL_COLUMNS,
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_OPTIONS_CHAIN_TRADES = SchemaContract(
    asset_group="cefi",
    instrument_type="options_chain",
    data_type="trades",
    columns=[
        _INSTRUMENT_ID,
        _UNDERLYING,
        _TS_EVENT,
        _PRICE,
        _SIZE,
        _SIDE,
        _STRIKE,
        _EXPIRY_DATE,
        _OPTION_RIGHT,
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

CEFI_FUTURES_CHAIN_TRADES = SchemaContract(
    asset_group="cefi",
    instrument_type="futures_chain",
    data_type="trades",
    columns=[
        _INSTRUMENT_ID,
        _UNDERLYING,
        _TS_EVENT,
        _PRICE,
        _SIZE,
        _SIDE,
        _EXPIRY_DATE,
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

# Snapshot contracts (options_chain / futures_chain / combo_chain / tbbo /
# ohlcv_24h) live in ``_snapshot_contracts`` — imported below via a
# side-effect import to keep this module under the 900-line codex-compliance
# limit.

# ---------------------------------------------------------------------------
# Built-in contracts — TradFi
# ---------------------------------------------------------------------------

TRADFI_FUTURE_TRADES = SchemaContract(
    asset_group="tradfi",
    instrument_type="future",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_OPTIONS_CHAIN_TRADES = SchemaContract(
    asset_group="tradfi",
    instrument_type="options_chain",
    data_type="trades",
    columns=[
        _INSTRUMENT_ID,
        _UNDERLYING,
        _TS_EVENT,
        _PRICE,
        _SIZE,
        _STRIKE,
        _EXPIRY_DATE,
        _OPTION_RIGHT,
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

TRADFI_EQUITY_TRADES = SchemaContract(
    asset_group="tradfi",
    instrument_type="equity",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_INDEX_TRADES = SchemaContract(
    asset_group="tradfi",
    instrument_type="index",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE],
    symbol_column="symbol",
    required_row_count_min=1,
)

# COMBO = calendar spread (NGH0-NGJ0), butterfly (CLZ0-CLF1-CLG1), iron
# condor, etc. Per-underlying bundled (one file per underlying per day
# carrying every multi-leg instruction). ``symbol`` is the Databento-style
# leg-combo string (``ESH0-ESM0``); canonical ``instrument_id`` is built
# upstream via MultiLegInstrument.
TRADFI_COMBO_TRADES = SchemaContract(
    asset_group="tradfi",
    instrument_type="combo",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_FUTURE_OHLCV_1M = SchemaContract(
    asset_group="tradfi",
    instrument_type="future",
    data_type="ohlcv_1m",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="open", dtype="float64", nullable=False),
        ColumnSpec(name="high", dtype="float64", nullable=False),
        ColumnSpec(name="low", dtype="float64", nullable=False),
        ColumnSpec(name="close", dtype="float64", nullable=False),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_EQUITY_OHLCV_1M = SchemaContract(
    asset_group="tradfi",
    instrument_type="equity",
    data_type="ohlcv_1m",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="open", dtype="float64", nullable=False),
        ColumnSpec(name="high", dtype="float64", nullable=False),
        ColumnSpec(name="low", dtype="float64", nullable=False),
        ColumnSpec(name="close", dtype="float64", nullable=False),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# TradFi options_chain / futures_chain snapshot contracts live in
# ``_snapshot_contracts`` alongside their CeFi counterparts.

# ---------------------------------------------------------------------------
# Built-in contracts — Sports / Prediction
# ---------------------------------------------------------------------------
# Sports (odds) and Prediction (Polymarket CLOB) contracts are declared in
# ``_sports_prediction_contracts`` and imported here via a side-effect import
# to keep this module under the 900-line codex-compliance limit. Re-exports
# below preserve ``from ...contracts import SPORTS_ODDS_TRADES`` API.

# ---------------------------------------------------------------------------
# Built-in contracts — DeFi
# ---------------------------------------------------------------------------

# lending_position lending_indices — generic shape (supply_index + borrow_index).
DEFI_LENDING_POSITION_LENDING_INDICES = SchemaContract(
    asset_group="defi",
    instrument_type="lending_position",
    data_type="lending_indices",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="supply_index", dtype="float64", nullable=False),
        ColumnSpec(name="borrow_index", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Aave V3 emits liquidityIndex/variableBorrowIndex naming; canonicalise via the
# protocol-specific contract below. ``symbol`` is the aToken symbol (aUSDC).
DEFI_AAVE_V3_LENDING_INDICES = SchemaContract(
    asset_group="defi",
    instrument_type="a_token",
    data_type="lending_indices",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="liquidity_index", dtype="float64", nullable=False),
        ColumnSpec(name="variable_borrow_index", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Generic lending (Compound V3, Morpho, Spark, Fluid, Instadapp) — row-level
# column is the asset/market identifier.
DEFI_LENDING_INDICES_MARKET_ID = SchemaContract(
    asset_group="defi",
    instrument_type="lending",
    data_type="lending_indices",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="supply_rate", dtype="float64", nullable=True),
        ColumnSpec(name="borrow_rate", dtype="float64", nullable=True),
    ],
    symbol_column="market_id",
    required_row_count_min=1,
)

DEFI_LENDING_LIQUIDATIONS = SchemaContract(
    asset_group="defi",
    instrument_type="lending",
    data_type="liquidations",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="collateral_asset", dtype="string", nullable=True),
        ColumnSpec(name="debt_asset", dtype="string", nullable=True),
        ColumnSpec(name="collateral_amount", dtype="float64", nullable=True),
        ColumnSpec(name="debt_amount", dtype="float64", nullable=True),
    ],
    # Liquidations are keyed on the per-row ``symbol`` (underlying collateral
    # pair) in the live liquidations-handler. ``market_id`` is reserved for
    # protocol-level shards (lending_indices).
    symbol_column="symbol",
    required_row_count_min=1,
)

# All DEX-pool protocols (Uniswap V2/V3/V4, Balancer, Curve, PancakeSwap_V3,
# Sushiswap/_V3, Camelot_V3, Aerodrome_V3, TraderJoe_V2, Velodrome_V2) write
# the canonical ``TOKEN0-TOKEN1[-FEE_TIER]`` pool symbol (dash-separated, real
# basis points — instrument_id_format_canonicalization_2026_07_08.md finding 2,
# mirrored from the instruments-service sibling fix commit 4e072d93) under
# ``symbol`` (market_tick_data_service.cli.handlers._dex_pool_symbol is the MTDS
# SSOT for resolving it; defi_dex_pool_symbol_shape_fix_2026_07_09 migration).
# ``dex_pool_state`` carries liquidity/price snapshots.
DEFI_DEX_POOL_DEX_POOL_STATE = SchemaContract(
    asset_group="defi",
    instrument_type="pool",
    data_type="dex_pool_state",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="liquidity", dtype="float64", nullable=True),
        ColumnSpec(name="sqrt_price_x96", dtype="string", nullable=True),
        ColumnSpec(name="price", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

DEFI_DEX_POOL_DEX_POOL_SWAPS = SchemaContract(
    asset_group="defi",
    instrument_type="dex_pool",
    data_type="dex_pool_swaps",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="amount0", dtype="float64", nullable=False),
        ColumnSpec(name="amount1", dtype="float64", nullable=False),
        ColumnSpec(name="price", dtype="float64", nullable=False),
    ],
    symbol_column="pool_id",
    required_row_count_min=1,
)

# Pool-variant swap dataset (instrument_type=pool, written by dex_swaps_handler
# for the 13 DEX-pool protocols). Same canonical ``symbol`` shape as
# DEFI_DEX_POOL_DEX_POOL_STATE above (defi_dex_pool_symbol_shape_fix_2026_07_09):
# was ``pool_id`` (bare on-chain address) until this migration.
DEFI_POOL_DEX_POOL_SWAPS = SchemaContract(
    asset_group="defi",
    instrument_type="pool",
    data_type="dex_pool_swaps",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="amount0", dtype="float64", nullable=False),
        ColumnSpec(name="amount1", dtype="float64", nullable=False),
        ColumnSpec(name="price", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Lido / EtherFi / Ethena LST: per-row ``symbol`` is the LST token ticker.
DEFI_LST_LST_RATES = SchemaContract(
    asset_group="defi",
    instrument_type="lst",
    data_type="lst_rates",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="exchange_rate", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# --- Solana DeFi (distinct instrument_types; legacy→canonical migration
# 2026-05-27, plan solana_defi_legacy_migration_2026_05_27). Kamino/Solend
# lending is an APY-snapshot shape (NOT the EVM rate/index shape); Solana AMM
# pools (Orca/Raydium) and Kamino vaults each carry venue-specific fields the
# EVM pool contracts don't. Same data_type, distinct instrument_type partition.
#
# ``symbol_column`` corrected 2026-07-21 ("eliminate the address/UUID fallback"
# P0, defi_consolidated_closeout_2026_07_18.md sub-item 3/5): was ``market_id``
# (the DeFiLlama pool UUID) -- meaning ``write_defi_rows`` built the canonical
# ``instrument_id`` AND the per-instrument GCS leaf from the UUID for EVERY
# Solana-lending row, regardless of what the ``symbol`` column carried. The
# handler-side resolver fix (market-tick-data-service's
# ``lending_indices_handler._resolve_blank_solana_lending_symbols``) populates
# a REAL resolved token symbol into the ``symbol`` column before this contract
# is consulted -- it had NO effect on the written object until this column
# pointer also moved from ``market_id`` to ``symbol``. Verified no other caller
# relies on the ``market_id`` default: the two migration/fold one-off scripts
# (``migrate_legacy_solana_defi_to_canonical.py`` /
# ``fold_legacy_solana_defi_to_consolidated_canonical_2026_07_21.py``) and
# ``risk_params_handler.py`` all pass an explicit ``symbol_column=`` to
# ``write_defi_rows`` and never consult this contract's default.
DEFI_SOLANA_LENDING_LENDING_INDICES = SchemaContract(
    asset_group="defi",
    instrument_type="solana_lending",
    data_type="lending_indices",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="supply_apy", dtype="float64", nullable=True),
        ColumnSpec(name="reward_apy", dtype="float64", nullable=True),
        ColumnSpec(name="apy", dtype="float64", nullable=True),
        ColumnSpec(name="tvl_usd", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

DEFI_SPOT_ASSET_GAS_FEES = SchemaContract(
    asset_group="defi",
    instrument_type="spot_asset",
    data_type="gas_fees",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="base_fee_gwei", dtype="float64", nullable=True),
        ColumnSpec(name="priority_fee_gwei", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

DEFI_SPOT_ASSET_ORACLE_PRICES = SchemaContract(
    asset_group="defi",
    instrument_type="spot_asset",
    data_type="oracle_prices",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="price", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

DEFI_PERPETUAL_PERP_FUNDING = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="perp_funding",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="funding_rate", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# perp_daily_ctx (2026-08-04, defi_perp_daily_ctx_manifest_gap_reader_risk issue):
# daily-close context sibling of perp_funding — mark_price (the tick mid),
# day_ntl_vlm (day notional volume), open_interest. CanonicalPerpFundingProvider
# (strategy-service engine/core/canonical_perp_funding_provider.py) reads this
# data_type from the SAME shared defi tick-data bucket TODAY for the funding-
# driven archetypes' mark price — this registration adds the missing
# data_type/SchemaContract so its already-real, already-migrated production rows
# stop being structurally invisible to the honest-coverage manifest. Mirrors
# DEFI_PERPETUAL_PERP_FUNDING's shape exactly (same 4 common columns); day_ntl_vlm
# / open_interest are nullable because one of the two current writers
# (features-service cefi/calculators/perp_funding_corpus.py) does not populate
# them (it only ever writes mark_price) while the other (MTDS HL backfill script)
# does — nullable keeps both writers' existing row shape valid unchanged.
DEFI_PERPETUAL_PERP_DAILY_CTX = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="perp_daily_ctx",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="mark_price", dtype="float64", nullable=False),
        ColumnSpec(name="day_ntl_vlm", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# perp_mark_price (2026-08-05, defi_perp_daily_ctx_manifest_gap_reader_risk issue follow-up): the
# real, already-migrated HYPERLIQUID mark-price corpus (316 days) copied into the shared bucket by
# the same 2026-07-13 dedicated-bucket migration that brought over perp_funding/perp_daily_ctx —
# confirmed via defi_dedicated_bucket_shared_migration_2026_07_13.md: "no current reader consumes
# it (canonical_perp_funding_provider reads marks from perp_daily_ctx)". Unlike perp_daily_ctx, this
# registration is a PURE manifest-visibility fix with ZERO live-reader risk (nothing reads this
# data_type today). Real file shape verified directly (one row per coin per day): instrument_id/
# venue/chain/ts_event + a single non-nullable mark_price column, no day_ntl_vlm/open_interest.
DEFI_PERPETUAL_PERP_MARK_PRICE = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="perp_mark_price",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="mark_price", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# derivative_ticker (2026-07-15, defi_perp_funding_canonicalisation_derivative_ticker_all_perps
# issue, operator ruling): the canonical RAW-funding home for ALL DeFi perp venues, captured
# at the highest resolution each source offers — even where the source genuinely has no OI
# (Drift/Aster/Pacifica/Extended omit it at settlement grain). Mirrors
# CEFI_PERPETUAL_DERIVATIVE_TICKER's shape —
# funding_rate mandatory, open_interest/mark_price/index_price nullable (never fabricated).
DEFI_PERPETUAL_DERIVATIVE_TICKER = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="derivative_ticker",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="funding_rate", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="mark_price", dtype="float64", nullable=True),
        ColumnSpec(name="index_price", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Solana basis-trading MVP (plans/active/solana_basis_trading_mvp_2026_06_01.md
# Phase 1). Drift V2 per-fill ground truth via the Velocity Data API endpoint
# ``data.api.drift.trade/market/{market}/trades/{Y}/{M}/{D}?format=csv``.
# Symbol is the market label (e.g. ``SOL-PERP``); per-fill numerical columns
# include ``baseAssetAmountFilled`` + ``quoteAssetAmountFilled`` + ``oraclePrice``
# + ``takerFee`` + ``makerRebate``. ``ts`` is the per-fill UNIX timestamp.
DEFI_PERPETUAL_PERP_TRADES = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="perp_trades",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="base_asset_amount_filled", dtype="float64", nullable=False),
        ColumnSpec(name="quote_asset_amount_filled", dtype="float64", nullable=False),
        ColumnSpec(name="oracle_price", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# TWAP marks at funding cadence (~hourly on Drift V2). Distinct from the
# ``perp_funding`` row's funding-rate field — this is the matching-engine
# top-of-book proxy used by the backtest fill simulator. Derivable from
# the same Velocity Data API funding response (``oraclePriceTwap`` /
# ``markPriceTwap`` columns) but emitted as a separate downstream-consumable
# data_type so consumers don't have to grep funding rows for it.
DEFI_PERPETUAL_PERP_MARK_ORACLE = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="perp_mark_oracle",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="oracle_price_twap", dtype="float64", nullable=False),
        ColumnSpec(name="mark_price_twap", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Signed AMM-side OI at funding cadence — derivable from
# ``baseAssetAmountWithAmm`` column on each ``perp_funding`` row. Sign
# convention matches Drift's: positive = net-long AMM exposure (longs out-pay
# shorts at positive funding); negative = net-short. Used for position-sizing
# + carry-magnitude calculations in the basis-trade archetype.
DEFI_PERPETUAL_PERP_OPEN_INTEREST = SchemaContract(
    asset_group="defi",
    instrument_type="perpetual",
    data_type="perp_open_interest",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="base_asset_amount_with_amm", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Phase 2 — Solana spot-DEX time-series state. CLOB-style orderbook snapshots
# (Phoenix) at block heights: top-N bid + ask levels with price + size.
# Distinct from ``dex_pool_state`` (AMM curve) — this is the orderbook
# vocabulary. Used by the backtest fill simulator for the long-spot leg of
# the basis trade when routing through Phoenix.
DEFI_DEX_POOL_DEX_ORDERBOOK = SchemaContract(
    asset_group="defi",
    instrument_type="dex_pool",
    data_type="dex_orderbook",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="bid_price", dtype="float64", nullable=True),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Phase 2 — Aggregator quote samples (Jupiter v6 ``/quote``). Sampled at
# fixed input notionals (e.g. 100/1K/10K USDC -> SOL) for routing-cost
# analysis + backtest comparison vs the underlying venue states.
DEFI_DEX_POOL_DEX_QUOTE = SchemaContract(
    asset_group="defi",
    instrument_type="dex_pool",
    data_type="dex_quote",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="input_amount", dtype="float64", nullable=False),
        ColumnSpec(name="output_amount", dtype="float64", nullable=False),
        ColumnSpec(name="price_impact_pct", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Phase 2 — Per-swap event stream on AMM venues (Orca / Raydium swap
# instructions). Distinct from ``dex_pool_swaps`` (subgraph-aggregated) —
# this is the per-fill canonical event with input + output amounts.
DEFI_DEX_POOL_DEX_TRADES = SchemaContract(
    asset_group="defi",
    instrument_type="dex_pool",
    data_type="dex_trades",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="input_amount", dtype="float64", nullable=False),
        ColumnSpec(name="output_amount", dtype="float64", nullable=False),
        ColumnSpec(name="input_token", dtype="string", nullable=True),
        ColumnSpec(name="output_token", dtype="string", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

DEFI_STAKING_EIGENLAYER_REWARDS = SchemaContract(
    asset_group="defi",
    instrument_type="staking",
    data_type="eigenlayer_rewards",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="reward_amount", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

DEFI_STAKING_YIELD_SNAPSHOTS = SchemaContract(
    asset_group="defi",
    instrument_type="staking",
    data_type="yield_snapshots",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="apy", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# Solana native-staking per-epoch APR data. Produced by the MTDS
# native_staking_handler. ``symbol`` is "SOL" (network-aggregate row) or a
# validator moniker. ``validator_vote_account`` is the base58 vote pubkey
# (nullable for network-aggregate rows). Sources: Solana RPC getInflationRate +
# getEpochInfo; Helius APY endpoint for per-validator breakdown.
DEFI_STAKING_NATIVE_STAKING_RATES = SchemaContract(
    asset_group="defi",
    instrument_type="staking",
    data_type="native_staking_rates",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="epoch", dtype="int64", nullable=False),
        ColumnSpec(name="validator_vote_account", dtype="string", nullable=True),
        ColumnSpec(name="commission_pct", dtype="float64", nullable=True),
        ColumnSpec(name="base_apy", dtype="float64", nullable=False),
        ColumnSpec(name="mev_apy", dtype="float64", nullable=True),
        ColumnSpec(name="total_apy", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# ERC-4626 vault share-price snapshots — produced by the MTDS
# vault_share_price_handler. ``symbol`` is the vault ticker (yvUSDC, sUSDe,
# sFRAX, ...). ``share_price`` is the result of
# ``convertToAssets(10**underlying_decimals)`` divided by 10**underlying_decimals.
DEFI_YIELD_BEARING_VAULT_SHARE_PRICE = SchemaContract(
    asset_group="defi",
    instrument_type="yield_bearing",
    data_type="vault_share_price",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _CHAIN,
        _TS_EVENT,
        ColumnSpec(name="share_price", dtype="float64", nullable=False),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CONTRACT_REGISTRY: dict[tuple[str, str, str], SchemaContract] = {
    # CeFi
    ("cefi", "perpetual", "trades"): CEFI_PERPETUAL_TRADES,
    ("cefi", "perpetual", "book_snapshot_5"): CEFI_PERPETUAL_BOOK_SNAPSHOT_5,
    ("cefi", "perpetual", "derivative_ticker"): CEFI_PERPETUAL_DERIVATIVE_TICKER,
    ("cefi", "perpetual", "liquidations"): CEFI_PERPETUAL_LIQUIDATIONS,
    ("cefi", "perpetual", "quotes"): CEFI_PERPETUAL_QUOTES,
    ("cefi", "spot_pair", "trades"): CEFI_SPOT_PAIR_TRADES,
    ("cefi", "spot_pair", "book_snapshot_5"): CEFI_SPOT_PAIR_BOOK_SNAPSHOT_5,
    ("cefi", "options_chain", "trades"): CEFI_OPTIONS_CHAIN_TRADES,
    ("cefi", "futures_chain", "trades"): CEFI_FUTURES_CHAIN_TRADES,
    # Chain / BBO / rolling-candle snapshot contracts registered via
    # _snapshot_contracts side-effect import (see end of file).
    # TradFi
    ("tradfi", "future", "trades"): TRADFI_FUTURE_TRADES,
    ("tradfi", "future", "ohlcv_1m"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "options_chain", "trades"): TRADFI_OPTIONS_CHAIN_TRADES,
    ("tradfi", "equity", "trades"): TRADFI_EQUITY_TRADES,
    ("tradfi", "equity", "ohlcv_1m"): TRADFI_EQUITY_OHLCV_1M,
    ("tradfi", "index", "trades"): TRADFI_INDEX_TRADES,
    ("tradfi", "index", "ohlcv_1m"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "combo", "trades"): TRADFI_COMBO_TRADES,
    # Databento continuous (futures_chain) and multi-leg (combo) instruments
    # write instrument_type="UNKNOWN" in parquet row data (stype_out=UNKNOWN for
    # continuous + calendar spread contracts). These entries allow MDPS to read
    # existing data without SchemaContract errors. Same column schema as future/ohlcv_1m.
    ("tradfi", "futures_chain", "ohlcv_1m"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "combo", "ohlcv_1m"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "UNKNOWN", "ohlcv_1m"): TRADFI_FUTURE_OHLCV_1M,
    # ohlcv_1s mirrors ohlcv_1m's column shape (open/high/low/close/volume are
    # timeframe-agnostic) — only the timeframe partition differs, so the same
    # TRADFI_FUTURE_OHLCV_1M contract is reused. Missing until 2026-07-31
    # (dp_vm_gone_no_capture_mdps_tradfi_ohlcv_1s_missing_contract_2026_07_31.md):
    # every CME future/futures_chain/combo ohlcv_1s file raised
    # SchemaContractNotFoundError on every date of a full-year (2024) tradfi
    # backfill VM, which cascaded to the 15m/1h/4h/24h candles derived FROM the
    # 1s source (chain-bundle aggregation reads the same file), so the VM's
    # entire ohlcv_1s-and-derived capture stayed at zero for the whole run.
    ("tradfi", "future", "ohlcv_1s"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "futures_chain", "ohlcv_1s"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "combo", "ohlcv_1s"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "UNKNOWN", "ohlcv_1s"): TRADFI_FUTURE_OHLCV_1M,
    # TradFi options_chain / futures_chain snapshot registered via
    # _snapshot_contracts side-effect import (see end of file).
    # DeFi
    ("defi", "lending_position", "lending_indices"): DEFI_LENDING_POSITION_LENDING_INDICES,
    ("defi", "a_token", "lending_indices"): DEFI_AAVE_V3_LENDING_INDICES,
    ("defi", "lending", "lending_indices"): DEFI_LENDING_INDICES_MARKET_ID,
    # Flat LENDING retired to the A_TOKEN/DEBT_TOKEN split (operator ruling 2026-07-18):
    # EVM lending-market liquidations now key to the reserve's A_TOKEN. The legacy
    # ``("defi", "lending", "liquidations")`` key is KEPT so historical lending-partitioned
    # liquidations parquets stay readable (Wave-D data re-key), mirroring the dual
    # registration Wave B used for ``lending_indices`` above; both point at the same schema.
    ("defi", "a_token", "liquidations"): DEFI_LENDING_LIQUIDATIONS,
    ("defi", "lending", "liquidations"): DEFI_LENDING_LIQUIDATIONS,
    ("defi", "solana_lending", "lending_indices"): DEFI_SOLANA_LENDING_LENDING_INDICES,
    ("defi", "pool", "dex_pool_state"): DEFI_DEX_POOL_DEX_POOL_STATE,
    ("defi", "pool", "dex_pool_swaps"): DEFI_POOL_DEX_POOL_SWAPS,
    ("defi", "dex_pool", "dex_pool_swaps"): DEFI_DEX_POOL_DEX_POOL_SWAPS,
    ("defi", "lst", "lst_rates"): DEFI_LST_LST_RATES,
    ("defi", "spot_asset", "gas_fees"): DEFI_SPOT_ASSET_GAS_FEES,
    ("defi", "spot_asset", "oracle_prices"): DEFI_SPOT_ASSET_ORACLE_PRICES,
    ("defi", "perpetual", "perp_funding"): DEFI_PERPETUAL_PERP_FUNDING,
    ("defi", "perpetual", "perp_daily_ctx"): DEFI_PERPETUAL_PERP_DAILY_CTX,
    ("defi", "perpetual", "perp_mark_price"): DEFI_PERPETUAL_PERP_MARK_PRICE,
    ("defi", "perpetual", "derivative_ticker"): DEFI_PERPETUAL_DERIVATIVE_TICKER,
    # Solana basis MVP (plans/active/solana_basis_trading_mvp_2026_06_01.md)
    ("defi", "perpetual", "perp_trades"): DEFI_PERPETUAL_PERP_TRADES,
    ("defi", "perpetual", "perp_mark_oracle"): DEFI_PERPETUAL_PERP_MARK_ORACLE,
    ("defi", "perpetual", "perp_open_interest"): DEFI_PERPETUAL_PERP_OPEN_INTEREST,
    ("defi", "dex_pool", "dex_orderbook"): DEFI_DEX_POOL_DEX_ORDERBOOK,
    ("defi", "dex_pool", "dex_quote"): DEFI_DEX_POOL_DEX_QUOTE,
    ("defi", "dex_pool", "dex_trades"): DEFI_DEX_POOL_DEX_TRADES,
    ("defi", "staking", "eigenlayer_rewards"): DEFI_STAKING_EIGENLAYER_REWARDS,
    ("defi", "staking", "yield_snapshots"): DEFI_STAKING_YIELD_SNAPSHOTS,
    ("defi", "staking", "native_staking_rates"): DEFI_STAKING_NATIVE_STAKING_RATES,
    ("defi", "yield_bearing", "vault_share_price"): DEFI_YIELD_BEARING_VAULT_SHARE_PRICE,
    # Sports + Prediction registered via _sports_prediction_contracts side-effect import (see end of file).
    # DeFi phase-2 contracts registered via _defi_v2_contracts side-effect import (see end of file).
}


# Venue/protocol-specific overrides. Keyed by ``(asset_group, venue, instrument_type,
# data_type)``. Aave V3 and Compound V3 both emit ``lending_indices`` but with
# different column vocabularies — the override lets migration + read paths
# resolve the precise schema by venue without guessing.
#
# **Composite venue convention for DeFi**: DeFi override keys MUST use the
# composite venue format ``<PROTOCOL>-<CHAIN>`` (e.g. ``AAVE_V3-ETHEREUM``,
# ``MORPHO-ETHEREUM``, ``UNISWAP_V3-ARBITRUM``). This matches the
# instruments-service availability-manifest naming convention where a single
# logical deployment is identified by protocol+chain (Aave V3 on Ethereum is a
# distinct venue from Aave V3 on Polygon). For CeFi / TradFi, ``venue`` is a
# single identifier (``DERIBIT``, ``BINANCE-SPOT``, ``CME``) — no chain suffix.
# Legacy DeFi entries below predate this convention and use the bare protocol
# name; they are kept for back-compat and will converge to the composite form
# as the migration lands.
VENUE_CONTRACT_OVERRIDES: dict[tuple[str, str, str, str], SchemaContract] = {
    # Aave V3 is the only lending protocol whose column vocabulary
    # meaningfully differs from the base contracts, so it's the primary
    # override we carry. Handlers currently emit ``instrument_type=LENDING``
    # while the long-term canonical is ``a_token`` — both keys point to the
    # same contract so live and migration code converge on one schema.
    ("defi", "AAVE_V3", "a_token", "lending_indices"): DEFI_AAVE_V3_LENDING_INDICES,
    ("defi", "AAVE_V3", "lending", "lending_indices"): DEFI_AAVE_V3_LENDING_INDICES,
    ("defi", "AAVE_V3", "lending_position", "lending_indices"): DEFI_AAVE_V3_LENDING_INDICES,
}


# Legacy venue-specific overrides (Uniswap V2/V3/V4, Curve, Balancer, Ethena,
# Aave a_token extensions) have been extracted to _legacy_venue_overrides
# to keep this module under the 900-line codex-compliance limit. The import
# below executes their side effects (mutations to CONTRACT_REGISTRY and
# VENUE_CONTRACT_OVERRIDES) at module load time, and the subsequent
# re-exports preserve the original ``from ...contracts import <NAME>`` API.


class SchemaContractNotFoundError(LookupError):
    """Raised when :func:`lookup_contract` cannot resolve a contract.

    The ``details`` mapping carries the exact lookup coordinates so the
    caller can emit a ``DEPLOYMENT_FAILED`` / ``SCHEMA_CONTRACT_MISSING``
    event and halt the pipeline. G3 (zero silent drops) depends on this
    being a hard error, never a warning.
    """

    def __init__(
        self,
        *,
        asset_group: str,
        instrument_type: str,
        data_type: str,
        venue: str | None,
    ) -> None:
        self.asset_group = asset_group
        self.instrument_type = instrument_type
        self.data_type = data_type
        self.venue = venue
        msg = (
            f"No SchemaContract registered for asset_group={asset_group!r} "
            f"instrument_type={instrument_type!r} data_type={data_type!r} "
            f"venue={venue!r}. Add a contract to "
            f"unified_api_contracts.internal.schemas.contracts.CONTRACT_REGISTRY "
            f"(and VENUE_CONTRACT_OVERRIDES if the schema is venue-specific) "
            f"before rerunning the read/migration pipeline."
        )
        super().__init__(msg)

    @property
    def details(self) -> dict[str, str]:
        """Structured fields suitable for ``log_event(details=...)``."""
        return {
            "asset_group": self.asset_group,
            "instrument_type": self.instrument_type,
            "data_type": self.data_type,
            "venue": self.venue or "",
        }


# Sports odds-derived-candle data_type PREFIXES whose instrument_type axis is
# unbounded at the CALLER (MDPS `_infer_instrument_type` extracts the raw
# per-market token — MATCH_ODDS, MATCH_ODDS_LAY, ASIAN_HANDICAP_0_25,
# OVER_UNDER_2_5, ... — from the canonical instrument_id; market/handicap
# combinations are continuously parameterised by `build_instrument_id`'s
# `point` float, so no finite instrument_type enumeration is ever complete)
# but whose CandleOutput column shape is IDENTICAL for every market, venue,
# and timeframe — verified against all four adapter sources
# (market_data_processing_service/app/adapters/sports/{odds_movement,
# odds_snapshot,bucket_assignment,arbitrage}_adapter.py all return the same
# OHLC+trade_count CandleOutput regardless of which market they were fed).
# The contracts themselves are registered once under the generic
# ("sports", "odds", data_type) key (_candle_contracts.py); this fallback
# widens which LOOKUP KEYS route to that already-correct, already-registered
# contract — it never changes what gets validated. Root-caused + fixed
# 2026-07-27: plans/active/issues/mdps_t1_recon_job_oom_failing_7_days_2026_07_26.md
# Update 5 (registering ~20 venues x per-market instrument_type was considered
# and rejected — the missing axis is instrument_type, not venue, and it is
# unbounded, so a finite venue x instrument_type list would recur indefinitely).
_SPORTS_ODDS_DERIVED_CANDLE_PREFIXES: tuple[str, ...] = (
    "odds_movement_",
    "odds_snapshot_",
    "odds_horizon_bucket_",
    "arbitrage_opportunity_",
)

# Sports EXCHANGE_ODDS/FIXED_ODDS instrument_types — retired as forward-written
# types in P1 (sports_taxonomy_p1_capture_and_contracts_2026_08_08.md, operator
# ruling 9). Exchange-vs-sportsbook is now derived at read time from
# SportsVenueType (is_exchange_venue()). Existing GCS/manifest rows written
# under these instrument_types resolve here via fallback step 5 below — this is
# the PERMANENT backward-compat mechanism until P2 re-stamps those rows to
# "odds". The dedicated CONTRACT_REGISTRY entries for ("sports",
# "exchange_odds"/"fixed_odds", "trades") were removed in P1; every lookup now
# falls through to ("sports", "odds", data_type).
_SPORTS_ODDS_FORK_INSTRUMENT_TYPES: tuple[str, ...] = ("exchange_odds", "fixed_odds")


def lookup_contract(
    *,
    asset_group: str,
    instrument_type: str,
    data_type: str,
    venue: str | None = None,
) -> SchemaContract:
    """Return the canonical :class:`SchemaContract` for a shard key.

    Resolution order (each step falls through to the next on miss):
        1. ``VENUE_CONTRACT_OVERRIDES[(asset_group, venue.upper(), instrument_type, data_type)]``
           — only consulted when ``venue`` is supplied.
        2. ``CONTRACT_REGISTRY[(asset_group, instrument_type, data_type)]``.
        3. Repeat steps 1-2 with case-normalised ``instrument_type`` AND
           ``data_type`` as a fallback.  Raw tick parquets written by MTDS use
           uppercase ``instrument_type`` (e.g. ``POOL``, ``DEX_POOL``) and the
           sports manifest convention uses uppercase ``data_type`` (e.g. ``XG``,
           ``XG_SHOTS``); the registry uses lowercase for both (``pool``,
           ``xg_shots``).  The fallback ensures every case combination resolves
           without requiring a schema-version migration.
        4. For ``asset_group == "sports"`` and a ``data_type`` prefixed by one
           of :data:`_SPORTS_ODDS_DERIVED_CANDLE_PREFIXES` (odds_movement /
           odds_snapshot / odds_horizon_bucket / arbitrage_opportunity candles),
           fall back to ``CONTRACT_REGISTRY[(asset_group, "odds", data_type)]``
           regardless of ``instrument_type``. These candle writers key
           ``instrument_type`` off the per-market token embedded in the
           canonical instrument_id (``MATCH_ODDS``, ``ASIAN_HANDICAP_0_25``,
           ``OVER_UNDER_2_5``, ...) — an open-ended vocabulary — but every
           market produces the identical column shape, so the single generic
           ``"odds"``-keyed contract is correct for all of them.
        5. Dual-read for the EXCHANGE_ODDS/FIXED_ODDS fork (migration window,
           ``sports_closeout_exchange_fixed_odds_fork_2026_07_25.md``): for
           ``asset_group == "sports"`` and ``instrument_type`` in
           :data:`_SPORTS_ODDS_FORK_INSTRUMENT_TYPES` (``exchange_odds`` /
           ``fixed_odds``), fall back to
           ``CONTRACT_REGISTRY[(asset_group, "odds", data_type)]``. Only the
           ``trades`` data_type has its own fork-specific registry entry so
           far — the legacy ``odds`` entry backs every other odds data_type
           (``sports_odds_snapshot`` / ``sports_odds_movement`` /
           ``sports_arbitrage`` / ...) under the new instrument_types too,
           since the fork only splits the partition key, not the row schema.

    Raises:
        SchemaContractNotFoundError: If no lookup resolves. Callers are
            expected to emit ``log_event("DEPLOYMENT_FAILED", ...)`` (or
            equivalent) and re-raise; G3 forbids silent fallback.
    """
    if venue is not None:
        key_v = (asset_group, venue.upper(), instrument_type, data_type)
        contract = VENUE_CONTRACT_OVERRIDES.get(key_v)
        if contract is not None:
            return contract
    key = (asset_group, instrument_type, data_type)
    contract = CONTRACT_REGISTRY.get(key)
    if contract is None:
        # Case-normalisation fallback on BOTH axes: raw parquets store uppercase
        # instrument_type (POOL → pool, DEX_POOL → dex_pool) and the sports
        # manifest convention stores uppercase data_type (XG_SHOTS → xg_shots).
        # Try each case-normalised variant that differs from the exact key.
        norm_it = instrument_type.lower()
        norm_dt = data_type.lower()
        for cand_it, cand_dt in (
            (instrument_type, norm_dt),
            (norm_it, data_type),
            (norm_it, norm_dt),
        ):
            if (cand_it, cand_dt) == (instrument_type, data_type):
                continue
            if venue is not None:
                contract = VENUE_CONTRACT_OVERRIDES.get((asset_group, venue.upper(), cand_it, cand_dt))
                if contract is not None:
                    break
            contract = CONTRACT_REGISTRY.get((asset_group, cand_it, cand_dt))
            if contract is not None:
                break
    if contract is None and asset_group == "sports" and data_type.startswith(_SPORTS_ODDS_DERIVED_CANDLE_PREFIXES):
        contract = CONTRACT_REGISTRY.get((asset_group, "odds", data_type))
    if contract is None and asset_group == "sports" and instrument_type in _SPORTS_ODDS_FORK_INSTRUMENT_TYPES:
        contract = CONTRACT_REGISTRY.get((asset_group, "odds", data_type))
    if contract is None:
        raise SchemaContractNotFoundError(
            asset_group=asset_group,
            instrument_type=instrument_type,
            data_type=data_type,
            venue=venue,
        )
    return contract


# Side-effect imports — must appear after CONTRACT_REGISTRY construction.
from unified_api_contracts.internal.schemas import _candle_contracts as _candle_contracts
from unified_api_contracts.internal.schemas import _defi_v2_contracts as _defi_v2_contracts
from unified_api_contracts.internal.schemas import _feature_contracts as _feature_contracts

# Instrument-catalogue contract — derives a single SchemaContract from
# INSTRUMENTS_PARQUET_SCHEMA (instruments-service write SSOT) and registers it
# under (asset_group, "instrument_catalogue", "instrument_catalogue") for each
# of cefi/tradfi/defi/prediction/sports. Required so deployment-api's View
# Schema endpoint can resolve schemas for the legacy v4 manifest rows that
# carry empty instrument_type and data_type axes.
from unified_api_contracts.internal.schemas import (
    _instrument_catalogue_contract as _instrument_catalogue_contract,
)
from unified_api_contracts.internal.schemas import _legacy_venue_overrides as _legacy_venue_overrides
from unified_api_contracts.internal.schemas import _snapshot_contracts as _snapshot_contracts

# _sports_contracts / _sports_match_contracts / _sports_derived_contracts
# together register 19 additional SPORTS SchemaContracts via module-level
# CONTRACT_REGISTRY side-effects (every live SPORTS data_type except ODDS,
# which lives in _sports_prediction_contracts). Split into 3 files to stay
# under the codex 900-line limit. SSOT plan:
# sports_uac_schema_contracts_registration_2026_04_24.md.
from unified_api_contracts.internal.schemas import _sports_contracts as _sports_contracts
from unified_api_contracts.internal.schemas import _sports_derived_contracts as _sports_derived_contracts
from unified_api_contracts.internal.schemas import _sports_match_contracts as _sports_match_contracts
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_DEBT_TOKEN_LENDING_INDICES as DEFI_DEBT_TOKEN_LENDING_INDICES,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_LENDING_FLASH_LOAN_EVENTS as DEFI_LENDING_FLASH_LOAN_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_LENDING_LIQUIDATION_EVENTS as DEFI_LENDING_LIQUIDATION_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_LENDING_POSITION_DATA as DEFI_LENDING_POSITION_DATA,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_SPOT_ASSET_AGGREGATOR_ROUTE as DEFI_SPOT_ASSET_AGGREGATOR_ROUTE,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_SPOT_ASSET_BRIDGE_EVENTS as DEFI_SPOT_ASSET_BRIDGE_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_SPOT_ASSET_GOVERNANCE_EVENTS as DEFI_SPOT_ASSET_GOVERNANCE_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_SPOT_ASSET_MEV_EVENTS as DEFI_SPOT_ASSET_MEV_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_SPOT_ASSET_TOKEN_TRANSFERS as DEFI_SPOT_ASSET_TOKEN_TRANSFERS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_STAKING_STAKING_YIELDS as DEFI_STAKING_STAKING_YIELDS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (
    DEFI_YIELD_BEARING_YIELD_SNAPSHOTS as DEFI_YIELD_BEARING_YIELD_SNAPSHOTS,
)
from unified_api_contracts.internal.schemas._ml_training_contract import (
    ML_TRAINING_MANIFEST as ML_TRAINING_MANIFEST,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    KEYWORD_TO_CATEGORY as KEYWORD_TO_CATEGORY,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    OUTCOME_TO_MARKET_TYPE as OUTCOME_TO_MARKET_TYPE,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    SLUG_PREFIX_MAP as SLUG_PREFIX_MAP,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    PredictionShardCategory as PredictionShardCategory,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    PredictionShardMarketType as PredictionShardMarketType,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    PredictionShardResolutionPeriod as PredictionShardResolutionPeriod,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    classify_polymarket_market as classify_polymarket_market,
)
from unified_api_contracts.internal.schemas._row_validation import (
    RowSchemaValidationError as RowSchemaValidationError,
)
from unified_api_contracts.internal.schemas._row_validation import (
    validate_row_df as validate_row_df,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_COMBO_CHAIN_SNAPSHOT as CEFI_COMBO_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_FUTURES_CHAIN_SNAPSHOT as CEFI_FUTURES_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_OPTIONS_CHAIN_SNAPSHOT as CEFI_OPTIONS_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_PERPETUAL_OHLCV_24H as CEFI_PERPETUAL_OHLCV_24H,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_PERPETUAL_TBBO as CEFI_PERPETUAL_TBBO,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_SPOT_PAIR_OHLCV_24H as CEFI_SPOT_PAIR_OHLCV_24H,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    CEFI_SPOT_PAIR_TBBO as CEFI_SPOT_PAIR_TBBO,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    TRADFI_FUTURES_CHAIN_SNAPSHOT as TRADFI_FUTURES_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (
    TRADFI_OPTIONS_CHAIN_SNAPSHOT as TRADFI_OPTIONS_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
    PREDICTION_PREDICTION_MARKET_TRADES as PREDICTION_PREDICTION_MARKET_TRADES,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
    SPORTS_ODDS_ARBITRAGE as SPORTS_ODDS_ARBITRAGE,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
    SPORTS_ODDS_HORIZON_BUCKET as SPORTS_ODDS_HORIZON_BUCKET,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
    SPORTS_ODDS_MOVEMENT as SPORTS_ODDS_MOVEMENT,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
    SPORTS_ODDS_SNAPSHOT as SPORTS_ODDS_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
    SPORTS_ODDS_TRADES as SPORTS_ODDS_TRADES,
)

__all__ = [
    "CEFI_COMBO_CHAIN_SNAPSHOT",
    "CEFI_FUTURES_CHAIN_SNAPSHOT",
    "CEFI_FUTURES_CHAIN_TRADES",
    "CEFI_OPTIONS_CHAIN_SNAPSHOT",
    "CEFI_OPTIONS_CHAIN_TRADES",
    "CEFI_PERPETUAL_BOOK_SNAPSHOT_5",
    "CEFI_PERPETUAL_DERIVATIVE_TICKER",
    "CEFI_PERPETUAL_LIQUIDATIONS",
    "CEFI_PERPETUAL_OHLCV_24H",
    "CEFI_PERPETUAL_QUOTES",
    "CEFI_PERPETUAL_TBBO",
    "CEFI_PERPETUAL_TRADES",
    "CEFI_SPOT_PAIR_BOOK_SNAPSHOT_5",
    "CEFI_SPOT_PAIR_OHLCV_24H",
    "CEFI_SPOT_PAIR_TBBO",
    "CEFI_SPOT_PAIR_TRADES",
    "CONTRACT_REGISTRY",
    "DEFI_AAVE_V3_LENDING_INDICES",
    "DEFI_DEBT_TOKEN_LENDING_INDICES",
    "DEFI_DEX_POOL_DEX_POOL_STATE",
    "DEFI_DEX_POOL_DEX_POOL_SWAPS",
    "DEFI_LENDING_FLASH_LOAN_EVENTS",
    "DEFI_LENDING_INDICES_MARKET_ID",
    "DEFI_LENDING_LIQUIDATIONS",
    "DEFI_LENDING_LIQUIDATION_EVENTS",
    "DEFI_LENDING_POSITION_DATA",
    "DEFI_LENDING_POSITION_LENDING_INDICES",
    "DEFI_LST_LST_RATES",
    "DEFI_PERPETUAL_DERIVATIVE_TICKER",
    "DEFI_PERPETUAL_PERP_FUNDING",
    "DEFI_POOL_DEX_POOL_SWAPS",
    "DEFI_SPOT_ASSET_BRIDGE_EVENTS",
    "DEFI_SPOT_ASSET_GAS_FEES",
    "DEFI_SPOT_ASSET_GOVERNANCE_EVENTS",
    "DEFI_SPOT_ASSET_MEV_EVENTS",
    "DEFI_SPOT_ASSET_ORACLE_PRICES",
    "DEFI_SPOT_ASSET_TOKEN_TRANSFERS",
    "DEFI_STAKING_EIGENLAYER_REWARDS",
    "DEFI_STAKING_NATIVE_STAKING_RATES",
    "DEFI_STAKING_STAKING_YIELDS",
    "DEFI_STAKING_YIELD_SNAPSHOTS",
    "DEFI_YIELD_BEARING_YIELD_SNAPSHOTS",
    "KEYWORD_TO_CATEGORY",
    "ML_TRAINING_MANIFEST",
    "OUTCOME_TO_MARKET_TYPE",
    "PREDICTION_PREDICTION_MARKET_TRADES",
    "SLUG_PREFIX_MAP",
    "SPORTS_ODDS_ARBITRAGE",
    "SPORTS_ODDS_HORIZON_BUCKET",
    "SPORTS_ODDS_MOVEMENT",
    "SPORTS_ODDS_SNAPSHOT",
    "SPORTS_ODDS_TRADES",
    "TRADFI_COMBO_TRADES",
    "TRADFI_EQUITY_OHLCV_1M",
    "TRADFI_EQUITY_TRADES",
    "TRADFI_FUTURES_CHAIN_SNAPSHOT",
    "TRADFI_FUTURE_OHLCV_1M",
    "TRADFI_FUTURE_TRADES",
    "TRADFI_INDEX_TRADES",
    "TRADFI_OPTIONS_CHAIN_SNAPSHOT",
    "TRADFI_OPTIONS_CHAIN_TRADES",
    "VENUE_CONTRACT_OVERRIDES",
    "ColumnSpec",
    "PredictionShardCategory",
    "PredictionShardMarketType",
    "PredictionShardResolutionPeriod",
    "RowSchemaValidationError",
    "SchemaContract",
    "SchemaContractNotFoundError",
    "Violation",
    "classify_polymarket_market",
    "lookup_contract",
    "validate_dataframe",
    "validate_row_df",
]
