"""Declarative per-(category, instrument_type, data_type) dataframe schema contracts.

Phase 1.3 of data_canonicalisation_mvp_2026_04_17.

Provides a minimal framework for validating pandas DataFrames written/read by
downstream data services (MTDS, instruments-service, features services, ML
pipelines) against a declarative schema. A ``SchemaContract`` names every
required column, its dtype, whether nulls are permitted, and per-column null
rate caps. Row-count floors can be enforced as a basic sanity gate.

Downstream services look up the canonical contract from
:data:`CONTRACT_REGISTRY` using the ``(category, instrument_type, data_type)``
tuple. New (category, instrument_type, data_type) triples are added by
appending to the module-level contract constants and the registry below — this
module is the single source of truth.
"""

from __future__ import annotations

from typing import Literal, cast

import pandas as pd
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
    """Declarative contract for a per-(category, instrument_type, data_type) dataframe."""

    model_config = ConfigDict(frozen=True)

    category: CategoryLiteral
    instrument_type: str
    data_type: str
    columns: list[ColumnSpec]
    required_row_count_min: int = 0
    null_rate_max: dict[str, float] = Field(default_factory=dict)


class Violation(BaseModel):
    """Single contract violation returned by :func:`validate_dataframe`."""

    model_config = ConfigDict(frozen=True)

    kind: ViolationKind
    column: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _dtype_matches(series: pd.Series, expected: DtypeLiteral) -> bool:
    """Return True if the pandas Series dtype matches ``expected``."""
    actual_str = str(series.dtype)
    if expected == "string":
        # Accept pandas "string" extension dtype or object (python str) arrays.
        if actual_str == "string":
            return True
        if actual_str == "object":
            non_null = series.dropna()
            if len(non_null) == 0:
                return True
            values = cast(list[object], non_null.tolist())
            return all(isinstance(value, str) for value in values)
        return False
    if expected == "int64":
        return actual_str in {"int64", "Int64"}
    if expected == "float64":
        return actual_str in {"float64", "Float64"}
    if expected == "bool":
        return actual_str in {"bool", "boolean"}
    if expected == "datetime64[ns, UTC]":
        return actual_str == "datetime64[ns, UTC]"
    if expected == "decimal":
        # Represented as object column of decimal.Decimal values, or pandas
        # Float64/float64 for fixed-precision numerics.
        return actual_str in {"object", "float64", "Float64"}
    return False


def validate_dataframe(df: pd.DataFrame, contract: SchemaContract) -> list[Violation]:
    """Validate ``df`` against ``contract`` and return a list of violations.

    Checks in order: required columns present, dtype per column, non-nullable
    columns contain zero nulls, per-column null rate caps respected, total row
    count meets ``required_row_count_min``.

    An empty list means the dataframe satisfies the contract.
    """
    violations: list[Violation] = []

    row_count = len(df)
    if row_count < contract.required_row_count_min:
        violations.append(
            Violation(
                kind="row_count_too_low",
                column=None,
                message=(f"row_count={row_count} < required_row_count_min={contract.required_row_count_min}"),
            )
        )

    for col in contract.columns:
        if col.name not in df.columns:
            violations.append(
                Violation(
                    kind="missing_column",
                    column=col.name,
                    message=f"column '{col.name}' missing from dataframe",
                )
            )
            continue

        series = df[col.name]

        if not _dtype_matches(series, col.dtype):
            violations.append(
                Violation(
                    kind="wrong_dtype",
                    column=col.name,
                    message=(f"column '{col.name}' has dtype '{series.dtype}', expected '{col.dtype}'"),
                )
            )

        null_count = int(series.isna().sum())
        if not col.nullable and null_count > 0:
            violations.append(
                Violation(
                    kind="extra_required_null",
                    column=col.name,
                    message=(f"non-nullable column '{col.name}' has {null_count} null value(s)"),
                )
            )

        cap = contract.null_rate_max.get(col.name)
        if cap is not None and row_count > 0:
            rate = null_count / row_count
            if rate > cap:
                violations.append(
                    Violation(
                        kind="null_rate_exceeded",
                        column=col.name,
                        message=(f"column '{col.name}' null_rate={rate:.4f} > cap={cap:.4f}"),
                    )
                )

    return violations


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
# Built-in contracts
# ---------------------------------------------------------------------------

CEFI_PERPETUAL_TRADES = SchemaContract(
    category="cefi",
    instrument_type="perpetual",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE, _SIDE],
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
    required_row_count_min=1,
)

TRADFI_FUTURE_TRADES = SchemaContract(
    category="tradfi",
    instrument_type="future",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE],
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
    required_row_count_min=1,
)

TRADFI_EQUITY_TRADES = SchemaContract(
    category="tradfi",
    instrument_type="equity",
    data_type="trades",
    columns=[_INSTRUMENT_ID, _SYMBOL, _TS_EVENT, _PRICE, _SIZE],
    required_row_count_min=1,
)

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
    required_row_count_min=1,
)

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
    required_row_count_min=1,
)

CONTRACT_REGISTRY: dict[tuple[str, str, str], SchemaContract] = {
    (
        CEFI_PERPETUAL_TRADES.category,
        CEFI_PERPETUAL_TRADES.instrument_type,
        CEFI_PERPETUAL_TRADES.data_type,
    ): CEFI_PERPETUAL_TRADES,
    (
        CEFI_PERPETUAL_BOOK_SNAPSHOT_5.category,
        CEFI_PERPETUAL_BOOK_SNAPSHOT_5.instrument_type,
        CEFI_PERPETUAL_BOOK_SNAPSHOT_5.data_type,
    ): CEFI_PERPETUAL_BOOK_SNAPSHOT_5,
    (
        CEFI_OPTIONS_CHAIN_TRADES.category,
        CEFI_OPTIONS_CHAIN_TRADES.instrument_type,
        CEFI_OPTIONS_CHAIN_TRADES.data_type,
    ): CEFI_OPTIONS_CHAIN_TRADES,
    (
        CEFI_FUTURES_CHAIN_TRADES.category,
        CEFI_FUTURES_CHAIN_TRADES.instrument_type,
        CEFI_FUTURES_CHAIN_TRADES.data_type,
    ): CEFI_FUTURES_CHAIN_TRADES,
    (
        TRADFI_FUTURE_TRADES.category,
        TRADFI_FUTURE_TRADES.instrument_type,
        TRADFI_FUTURE_TRADES.data_type,
    ): TRADFI_FUTURE_TRADES,
    (
        TRADFI_OPTIONS_CHAIN_TRADES.category,
        TRADFI_OPTIONS_CHAIN_TRADES.instrument_type,
        TRADFI_OPTIONS_CHAIN_TRADES.data_type,
    ): TRADFI_OPTIONS_CHAIN_TRADES,
    (
        TRADFI_EQUITY_TRADES.category,
        TRADFI_EQUITY_TRADES.instrument_type,
        TRADFI_EQUITY_TRADES.data_type,
    ): TRADFI_EQUITY_TRADES,
    (
        DEFI_LENDING_POSITION_LENDING_INDICES.category,
        DEFI_LENDING_POSITION_LENDING_INDICES.instrument_type,
        DEFI_LENDING_POSITION_LENDING_INDICES.data_type,
    ): DEFI_LENDING_POSITION_LENDING_INDICES,
    (
        DEFI_DEX_POOL_DEX_POOL_SWAPS.category,
        DEFI_DEX_POOL_DEX_POOL_SWAPS.instrument_type,
        DEFI_DEX_POOL_DEX_POOL_SWAPS.data_type,
    ): DEFI_DEX_POOL_DEX_POOL_SWAPS,
    (DEFI_LST_LST_RATES.category, DEFI_LST_LST_RATES.instrument_type, DEFI_LST_LST_RATES.data_type): DEFI_LST_LST_RATES,
}


__all__ = [
    "CEFI_FUTURES_CHAIN_TRADES",
    "CEFI_OPTIONS_CHAIN_TRADES",
    "CEFI_PERPETUAL_BOOK_SNAPSHOT_5",
    "CEFI_PERPETUAL_TRADES",
    "CONTRACT_REGISTRY",
    "DEFI_DEX_POOL_DEX_POOL_SWAPS",
    "DEFI_LENDING_POSITION_LENDING_INDICES",
    "DEFI_LST_LST_RATES",
    "TRADFI_EQUITY_TRADES",
    "TRADFI_FUTURE_TRADES",
    "TRADFI_OPTIONS_CHAIN_TRADES",
    "ColumnSpec",
    "SchemaContract",
    "Violation",
    "validate_dataframe",
]
