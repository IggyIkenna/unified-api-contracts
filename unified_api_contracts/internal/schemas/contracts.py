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
2026-05-07, manifest_migration_master_2026_05_07.md § Audit findings).

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

from unified_api_contracts.internal.schemas._validation import (  # noqa: E402 — after type defs
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

CEFI_PERPETUAL_BOOK_SNAPSHOT_5 = SchemaContract(
    asset_group="cefi",
    instrument_type="perpetual",
    data_type="book_snapshot_5",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(
            name="bids",
            dtype="string",
            nullable=False,
            description="Serialised list of top-5 bid (price, size) levels.",
        ),
        ColumnSpec(
            name="asks",
            dtype="string",
            nullable=False,
            description="Serialised list of top-5 ask (price, size) levels.",
        ),
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
        ColumnSpec(name="bids", dtype="string", nullable=False),
        ColumnSpec(name="asks", dtype="string", nullable=False),
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

# Uniswap V2/V3/V4, Curve, Balancer — pool-scoped rows use ``pool_id`` as the
# canonical row symbol. ``dex_pool_state`` carries liquidity/price snapshots.
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
    # Live dex-pool handlers emit the pool identifier under ``symbol``
    # (``USDC-WETH-500`` etc.) — legacy handler convention. A future
    # canonicalisation pass can move it to ``pool_id``; the override
    # registry is the place to flip that per-venue when it lands.
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

# Pool-variant swap dataset (instrument_type=pool used by the evm_defi handler
# and dex_pools_handler for historical swaps snapshots).
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
    symbol_column="pool_id",
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
    ("tradfi", "combo", "trades"): TRADFI_COMBO_TRADES,
    # TradFi options_chain / futures_chain snapshot registered via
    # _snapshot_contracts side-effect import (see end of file).
    # DeFi
    ("defi", "lending_position", "lending_indices"): DEFI_LENDING_POSITION_LENDING_INDICES,
    ("defi", "a_token", "lending_indices"): DEFI_AAVE_V3_LENDING_INDICES,
    ("defi", "lending", "lending_indices"): DEFI_LENDING_INDICES_MARKET_ID,
    ("defi", "lending", "liquidations"): DEFI_LENDING_LIQUIDATIONS,
    ("defi", "pool", "dex_pool_state"): DEFI_DEX_POOL_DEX_POOL_STATE,
    ("defi", "pool", "dex_pool_swaps"): DEFI_POOL_DEX_POOL_SWAPS,
    ("defi", "dex_pool", "dex_pool_swaps"): DEFI_DEX_POOL_DEX_POOL_SWAPS,
    ("defi", "lst", "lst_rates"): DEFI_LST_LST_RATES,
    ("defi", "spot_asset", "gas_fees"): DEFI_SPOT_ASSET_GAS_FEES,
    ("defi", "spot_asset", "oracle_prices"): DEFI_SPOT_ASSET_ORACLE_PRICES,
    ("defi", "perpetual", "perp_funding"): DEFI_PERPETUAL_PERP_FUNDING,
    ("defi", "staking", "eigenlayer_rewards"): DEFI_STAKING_EIGENLAYER_REWARDS,
    ("defi", "staking", "yield_snapshots"): DEFI_STAKING_YIELD_SNAPSHOTS,
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


def lookup_contract(
    *,
    asset_group: str,
    instrument_type: str,
    data_type: str,
    venue: str | None = None,
) -> SchemaContract:
    """Return the canonical :class:`SchemaContract` for a shard key.

    Resolution order:
        1. ``VENUE_CONTRACT_OVERRIDES[(asset_group, venue.upper(), instrument_type, data_type)]``
           — only consulted when ``venue`` is supplied.
        2. ``CONTRACT_REGISTRY[(asset_group, instrument_type, data_type)]``.

    Raises:
        SchemaContractNotFoundError: If neither lookup resolves. Callers are
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
        raise SchemaContractNotFoundError(
            asset_group=asset_group,
            instrument_type=instrument_type,
            data_type=data_type,
            venue=venue,
        )
    return contract


# Side-effect imports — must appear after CONTRACT_REGISTRY construction.
from unified_api_contracts.internal.schemas import _candle_contracts as _candle_contracts  # noqa: E402
from unified_api_contracts.internal.schemas import _defi_v2_contracts as _defi_v2_contracts  # noqa: E402
from unified_api_contracts.internal.schemas import _feature_contracts as _feature_contracts  # noqa: E402

# Instrument-catalogue contract — derives a single SchemaContract from
# INSTRUMENTS_PARQUET_SCHEMA (instruments-service write SSOT) and registers it
# under (asset_group, "instrument_catalogue", "instrument_catalogue") for each
# of cefi/tradfi/defi/prediction/sports. Required so deployment-api's View
# Schema endpoint can resolve schemas for the legacy v4 manifest rows that
# carry empty instrument_type and data_type axes.
from unified_api_contracts.internal.schemas import (  # noqa: E402
    _instrument_catalogue_contract as _instrument_catalogue_contract,
)
from unified_api_contracts.internal.schemas import _legacy_venue_overrides as _legacy_venue_overrides  # noqa: E402
from unified_api_contracts.internal.schemas import _snapshot_contracts as _snapshot_contracts  # noqa: E402

# _sports_contracts / _sports_match_contracts / _sports_derived_contracts
# together register 19 additional SPORTS SchemaContracts via module-level
# CONTRACT_REGISTRY side-effects (every live SPORTS data_type except ODDS,
# which lives in _sports_prediction_contracts). Split into 3 files to stay
# under the codex 900-line limit. SSOT plan:
# sports_uac_schema_contracts_registration_2026_04_24.md.
from unified_api_contracts.internal.schemas import _sports_contracts as _sports_contracts  # noqa: E402
from unified_api_contracts.internal.schemas import _sports_derived_contracts as _sports_derived_contracts  # noqa: E402
from unified_api_contracts.internal.schemas import _sports_match_contracts as _sports_match_contracts  # noqa: E402
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_DEBT_TOKEN_LENDING_INDICES as DEFI_DEBT_TOKEN_LENDING_INDICES,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_LENDING_FLASH_LOAN_EVENTS as DEFI_LENDING_FLASH_LOAN_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_LENDING_LIQUIDATION_EVENTS as DEFI_LENDING_LIQUIDATION_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_LENDING_POSITION_DATA as DEFI_LENDING_POSITION_DATA,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_POOL_DEX_POOLS as DEFI_POOL_DEX_POOLS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_POOL_DEX_SWAPS as DEFI_POOL_DEX_SWAPS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_SPOT_ASSET_BRIDGE_EVENTS as DEFI_SPOT_ASSET_BRIDGE_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_SPOT_ASSET_GOVERNANCE_EVENTS as DEFI_SPOT_ASSET_GOVERNANCE_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_SPOT_ASSET_MEV_EVENTS as DEFI_SPOT_ASSET_MEV_EVENTS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_SPOT_ASSET_TOKEN_TRANSFERS as DEFI_SPOT_ASSET_TOKEN_TRANSFERS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_STAKING_STAKING_YIELDS as DEFI_STAKING_STAKING_YIELDS,
)
from unified_api_contracts.internal.schemas._defi_v2_contracts import (  # noqa: E402
    DEFI_YIELD_BEARING_YIELD_SNAPSHOTS as DEFI_YIELD_BEARING_YIELD_SNAPSHOTS,
)
from unified_api_contracts.internal.schemas._ml_training_contract import (  # noqa: E402
    ML_TRAINING_MANIFEST as ML_TRAINING_MANIFEST,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    KEYWORD_TO_CATEGORY as KEYWORD_TO_CATEGORY,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    OUTCOME_TO_MARKET_TYPE as OUTCOME_TO_MARKET_TYPE,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    SLUG_PREFIX_MAP as SLUG_PREFIX_MAP,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    PredictionShardCategory as PredictionShardCategory,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    PredictionShardMarketType as PredictionShardMarketType,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    PredictionShardResolutionPeriod as PredictionShardResolutionPeriod,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (  # noqa: E402
    classify_polymarket_market as classify_polymarket_market,
)
from unified_api_contracts.internal.schemas._row_validation import (  # noqa: E402
    RowSchemaValidationError as RowSchemaValidationError,
)
from unified_api_contracts.internal.schemas._row_validation import (  # noqa: E402
    validate_row_df as validate_row_df,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_COMBO_CHAIN_SNAPSHOT as CEFI_COMBO_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_FUTURES_CHAIN_SNAPSHOT as CEFI_FUTURES_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_OPTIONS_CHAIN_SNAPSHOT as CEFI_OPTIONS_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_PERPETUAL_OHLCV_24H as CEFI_PERPETUAL_OHLCV_24H,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_PERPETUAL_TBBO as CEFI_PERPETUAL_TBBO,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_SPOT_PAIR_OHLCV_24H as CEFI_SPOT_PAIR_OHLCV_24H,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    CEFI_SPOT_PAIR_TBBO as CEFI_SPOT_PAIR_TBBO,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    TRADFI_FUTURES_CHAIN_SNAPSHOT as TRADFI_FUTURES_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._snapshot_contracts import (  # noqa: E402
    TRADFI_OPTIONS_CHAIN_SNAPSHOT as TRADFI_OPTIONS_CHAIN_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (  # noqa: E402
    PREDICTION_PREDICTION_MARKET_TRADES as PREDICTION_PREDICTION_MARKET_TRADES,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (  # noqa: E402
    SPORTS_ODDS_ARBITRAGE as SPORTS_ODDS_ARBITRAGE,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (  # noqa: E402
    SPORTS_ODDS_MOVEMENT as SPORTS_ODDS_MOVEMENT,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (  # noqa: E402
    SPORTS_ODDS_SNAPSHOT as SPORTS_ODDS_SNAPSHOT,
)
from unified_api_contracts.internal.schemas._sports_prediction_contracts import (  # noqa: E402
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
    "DEFI_PERPETUAL_PERP_FUNDING",
    "DEFI_POOL_DEX_POOLS",
    "DEFI_POOL_DEX_POOL_SWAPS",
    "DEFI_POOL_DEX_SWAPS",
    "DEFI_SPOT_ASSET_BRIDGE_EVENTS",
    "DEFI_SPOT_ASSET_GAS_FEES",
    "DEFI_SPOT_ASSET_GOVERNANCE_EVENTS",
    "DEFI_SPOT_ASSET_MEV_EVENTS",
    "DEFI_SPOT_ASSET_ORACLE_PRICES",
    "DEFI_SPOT_ASSET_TOKEN_TRANSFERS",
    "DEFI_STAKING_EIGENLAYER_REWARDS",
    "DEFI_STAKING_STAKING_YIELDS",
    "DEFI_STAKING_YIELD_SNAPSHOTS",
    "DEFI_YIELD_BEARING_YIELD_SNAPSHOTS",
    "KEYWORD_TO_CATEGORY",
    "ML_TRAINING_MANIFEST",
    "OUTCOME_TO_MARKET_TYPE",
    "PREDICTION_PREDICTION_MARKET_TRADES",
    "SLUG_PREFIX_MAP",
    "SPORTS_ODDS_ARBITRAGE",
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
