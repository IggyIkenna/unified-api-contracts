"""Declarative per-(category, instrument_type, data_type) dataframe schema contracts.

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
:data:`CONTRACT_REGISTRY` using the ``(category, instrument_type, data_type)``
tuple. For venue/protocol-specific schemas (e.g. Aave V3's
``liquidity_index``/``variable_borrow_index`` vs Compound V3's ``supply_rate``)
use :func:`lookup_contract` which consults :data:`VENUE_CONTRACT_OVERRIDES`
first and falls back to the base registry. New (category, instrument_type,
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
    "float64",
    "bool",
    "datetime64[ns, UTC]",
    "decimal",
]

CategoryLiteral = Literal[
    "cefi",
    "tradfi",
    "defi",
    "sports",
    "prediction",
    "onchain",
]

ViolationKind = Literal[
    "missing_column",
    "wrong_dtype",
    "null_rate_exceeded",
    "row_count_too_low",
    "extra_required_null",
]


class ColumnSpec(BaseModel):
    """Declarative spec for a single dataframe column."""

    model_config = ConfigDict(frozen=True)

    name: str
    dtype: DtypeLiteral
    nullable: bool = False
    description: str | None = None


class SchemaContract(BaseModel):
    """Declarative contract for a per-(category, instrument_type, data_type) dataframe.

    The ``symbol_column`` field names the column that per-row migration /
    read pipelines must consult to extract the instrument symbol for partition
    path construction and canonical ``instrument_id`` building. Defaults to
    ``"symbol"`` for back-compat with the ten original Phase-1.3 contracts;
    every new contract declares it explicitly so guessing (symbol → token →
    pool_id → asset) is eliminated at the root.
    """

    model_config = ConfigDict(frozen=True)

    category: CategoryLiteral
    instrument_type: str
    data_type: str
    columns: list[ColumnSpec]
    symbol_column: str = "symbol"
    required_row_count_min: int = 0
    null_rate_max: dict[str, float] = Field(default_factory=dict)


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

# ---------------------------------------------------------------------------
# Built-in contracts — CeFi
# ---------------------------------------------------------------------------

CEFI_PERPETUAL_TRADES = SchemaContract(
    category="cefi",
    instrument_type="perpetual",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_PERPETUAL_BOOK_SNAPSHOT_5 = SchemaContract(
    category="cefi",
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
    category="cefi",
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
    category="cefi",
    instrument_type="perpetual",
    data_type="liquidations",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_PERPETUAL_QUOTES = SchemaContract(
    category="cefi",
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
    category="cefi",
    instrument_type="spot_pair",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_SPOT_PAIR_BOOK_SNAPSHOT_5 = SchemaContract(
    category="cefi",
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
    category="cefi",
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
    category="cefi",
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

# ---------------------------------------------------------------------------
# Built-in contracts — TradFi
# ---------------------------------------------------------------------------

TRADFI_FUTURE_TRADES = SchemaContract(
    category="tradfi",
    instrument_type="future",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_OPTIONS_CHAIN_TRADES = SchemaContract(
    category="tradfi",
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
    category="tradfi",
    instrument_type="equity",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_INDEX_TRADES = SchemaContract(
    category="tradfi",
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
    category="tradfi",
    instrument_type="combo",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE],
    symbol_column="symbol",
    required_row_count_min=1,
)

TRADFI_FUTURE_OHLCV_1M = SchemaContract(
    category="tradfi",
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
    category="tradfi",
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

# ---------------------------------------------------------------------------
# Built-in contracts — DeFi
# ---------------------------------------------------------------------------

# lending_position lending_indices — generic shape (supply_index + borrow_index).
DEFI_LENDING_POSITION_LENDING_INDICES = SchemaContract(
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    category="defi",
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
    # TradFi
    ("tradfi", "future", "trades"): TRADFI_FUTURE_TRADES,
    ("tradfi", "future", "ohlcv_1m"): TRADFI_FUTURE_OHLCV_1M,
    ("tradfi", "options_chain", "trades"): TRADFI_OPTIONS_CHAIN_TRADES,
    ("tradfi", "equity", "trades"): TRADFI_EQUITY_TRADES,
    ("tradfi", "equity", "ohlcv_1m"): TRADFI_EQUITY_OHLCV_1M,
    ("tradfi", "index", "trades"): TRADFI_INDEX_TRADES,
    ("tradfi", "combo", "trades"): TRADFI_COMBO_TRADES,
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
}


# Venue/protocol-specific overrides. Keyed by ``(category, venue, instrument_type,
# data_type)``. Aave V3 and Compound V3 both emit ``lending_indices`` but with
# different column vocabularies — the override lets migration + read paths
# resolve the precise schema by venue without guessing.
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
        category: str,
        instrument_type: str,
        data_type: str,
        venue: str | None,
    ) -> None:
        self.category = category
        self.instrument_type = instrument_type
        self.data_type = data_type
        self.venue = venue
        msg = (
            f"No SchemaContract registered for category={category!r} "
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
            "category": self.category,
            "instrument_type": self.instrument_type,
            "data_type": self.data_type,
            "venue": self.venue or "",
        }


def lookup_contract(
    *,
    category: str,
    instrument_type: str,
    data_type: str,
    venue: str | None = None,
) -> SchemaContract:
    """Return the canonical :class:`SchemaContract` for a shard key.

    Resolution order:
        1. ``VENUE_CONTRACT_OVERRIDES[(category, venue.upper(), instrument_type, data_type)]``
           — only consulted when ``venue`` is supplied.
        2. ``CONTRACT_REGISTRY[(category, instrument_type, data_type)]``.

    Raises:
        SchemaContractNotFoundError: If neither lookup resolves. Callers are
            expected to emit ``log_event("DEPLOYMENT_FAILED", ...)`` (or
            equivalent) and re-raise; G3 forbids silent fallback.
    """
    if venue is not None:
        key_v = (category, venue.upper(), instrument_type, data_type)
        contract = VENUE_CONTRACT_OVERRIDES.get(key_v)
        if contract is not None:
            return contract
    key = (category, instrument_type, data_type)
    contract = CONTRACT_REGISTRY.get(key)
    if contract is None:
        raise SchemaContractNotFoundError(
            category=category,
            instrument_type=instrument_type,
            data_type=data_type,
            venue=venue,
        )
    return contract


__all__ = [
    "CEFI_FUTURES_CHAIN_TRADES",
    "CEFI_OPTIONS_CHAIN_TRADES",
    "CEFI_PERPETUAL_BOOK_SNAPSHOT_5",
    "CEFI_PERPETUAL_DERIVATIVE_TICKER",
    "CEFI_PERPETUAL_LIQUIDATIONS",
    "CEFI_PERPETUAL_QUOTES",
    "CEFI_PERPETUAL_TRADES",
    "CEFI_SPOT_PAIR_BOOK_SNAPSHOT_5",
    "CEFI_SPOT_PAIR_TRADES",
    "CONTRACT_REGISTRY",
    "DEFI_AAVE_V3_LENDING_INDICES",
    "DEFI_DEX_POOL_DEX_POOL_STATE",
    "DEFI_DEX_POOL_DEX_POOL_SWAPS",
    "DEFI_LENDING_INDICES_MARKET_ID",
    "DEFI_LENDING_LIQUIDATIONS",
    "DEFI_LENDING_POSITION_LENDING_INDICES",
    "DEFI_LST_LST_RATES",
    "DEFI_PERPETUAL_PERP_FUNDING",
    "DEFI_POOL_DEX_POOL_SWAPS",
    "DEFI_SPOT_ASSET_GAS_FEES",
    "DEFI_SPOT_ASSET_ORACLE_PRICES",
    "DEFI_STAKING_EIGENLAYER_REWARDS",
    "DEFI_STAKING_YIELD_SNAPSHOTS",
    "TRADFI_EQUITY_OHLCV_1M",
    "TRADFI_EQUITY_TRADES",
    "TRADFI_FUTURE_OHLCV_1M",
    "TRADFI_FUTURE_TRADES",
    "TRADFI_INDEX_TRADES",
    "TRADFI_OPTIONS_CHAIN_TRADES",
    "VENUE_CONTRACT_OVERRIDES",
    "ColumnSpec",
    "SchemaContract",
    "SchemaContractNotFoundError",
    "Violation",
    "lookup_contract",
    "validate_dataframe",
]
