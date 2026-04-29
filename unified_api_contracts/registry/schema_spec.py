"""SchemaSpec registry — per (asset_group, data_type) parquet column shape.

The catalogue generator emits this registry's contents into
``shard-dynamics.json`` so consumers (UI matrix tooltip, AI agents reasoning
about how to query a parquet) can answer "what columns will I see?" without
opening the file.

For Pydantic-model-backed parquets (canonical Trade / FundingRate / etc.)
columns are derived via :func:`_columns_from_pydantic`. For shapes that
don't have a single canonical model (sports fixtures, DeFi pool snapshots
that vary per protocol) we hand-write the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from unified_api_contracts import (
    CanonicalDerivativeTicker,
    CanonicalFundingRate,
    CanonicalLiquidation,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    nullable: bool = False
    unit: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class SchemaSpec:
    asset_group: AssetGroup
    data_type: str
    columns: tuple[ColumnSpec, ...]
    source: str  # "pydantic:<ClassName>" | "manual"


# ---------------------------------------------------------------------------
# Pydantic reflection helper
# ---------------------------------------------------------------------------


_PYDANTIC_DTYPE_MAP: dict[type, str] = {
    str: "string",
    int: "int64",
    float: "float64",
    bool: "bool",
    bytes: "bytes",
}


def _annotation_dtype(annotation: object) -> tuple[str, bool]:
    """Best-effort mapping from a type annotation to a parquet dtype string.

    Returns ``(dtype, nullable)``.
    """
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type) and annotation in _PYDANTIC_DTYPE_MAP:
            return _PYDANTIC_DTYPE_MAP[annotation], False
        if isinstance(annotation, type):
            # Datetime / Decimal / nested BaseModel / etc — fall back to class name.
            return annotation.__name__, False
        return "any", False

    if origin is type(None):  # pragma: no cover — never appears as origin alone
        return "null", True

    # Union / Optional handling.
    args = get_args(annotation)
    if origin is type and len(args) == 1:
        return _annotation_dtype(args[0])

    # Optional[X] = Union[X, None]
    non_none = [a for a in args if a is not type(None)]
    nullable = len(non_none) != len(args)
    if len(non_none) == 1:
        dtype, _ = _annotation_dtype(non_none[0])
        return dtype, nullable

    if origin is list:
        if non_none:
            inner_dtype, _ = _annotation_dtype(non_none[0])
            return f"list<{inner_dtype}>", nullable
        return "list<any>", nullable

    if origin is dict:
        return "map<any,any>", nullable

    # tuple / set / etc — fall through.
    return getattr(origin, "__name__", "any"), nullable


def _columns_from_pydantic(cls: type[BaseModel]) -> tuple[ColumnSpec, ...]:
    cols: list[ColumnSpec] = []
    for name, field_info in cls.model_fields.items():
        dtype, nullable_from_annotation = _annotation_dtype(field_info.annotation)
        nullable = nullable_from_annotation or _is_optional(field_info)
        cols.append(
            ColumnSpec(
                name=name,
                dtype=dtype,
                nullable=nullable,
                description=field_info.description,
            )
        )
    return tuple(cols)


def _is_optional(field_info: FieldInfo) -> bool:
    """Pydantic ``FieldInfo.is_required`` is False for fields with defaults."""
    return not field_info.is_required()


# ---------------------------------------------------------------------------
# Hand-written specs (shapes without a single canonical Pydantic model)
# ---------------------------------------------------------------------------

_SPORTS_FIXTURE_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("fixture_id", "string", description="Canonical fixture id"),
    ColumnSpec("league_id", "string", description="Canonical league id"),
    ColumnSpec("kickoff_at", "timestamp[us, UTC]", description="Scheduled kickoff (UTC)"),
    ColumnSpec("home_team_id", "string"),
    ColumnSpec("away_team_id", "string"),
    ColumnSpec("season_id", "string", nullable=True),
    ColumnSpec("status", "string", description="scheduled | in_progress | finished | cancelled"),
    ColumnSpec("home_score", "int64", nullable=True),
    ColumnSpec("away_score", "int64", nullable=True),
)

_SPORTS_ODDS_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("fixture_id", "string"),
    ColumnSpec("bookmaker", "string"),
    ColumnSpec("market", "string", description="h2h | spreads | totals"),
    ColumnSpec("outcome", "string"),
    ColumnSpec("price", "float64", description="Decimal odds"),
    ColumnSpec("point", "float64", nullable=True, description="Spread/total handicap"),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
)

_DEFI_LENDING_INDICES_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("instrument_id", "string", description="VENUE-CHAIN:a_token:SYMBOL"),
    ColumnSpec("venue", "string"),
    ColumnSpec("chain", "string"),
    ColumnSpec("symbol", "string"),
    ColumnSpec("block_number", "int64"),
    ColumnSpec("liquidity_index", "float64"),
    ColumnSpec("variable_borrow_index", "float64"),
    ColumnSpec("supply_apr", "float64", nullable=True),
    ColumnSpec("borrow_apr", "float64", nullable=True),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
)

_DEFI_DEX_POOL_SWAPS_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("instrument_id", "string"),
    ColumnSpec("venue", "string"),
    ColumnSpec("chain", "string"),
    ColumnSpec("pool_address", "string"),
    ColumnSpec("token0", "string"),
    ColumnSpec("token1", "string"),
    ColumnSpec("amount0", "float64"),
    ColumnSpec("amount1", "float64"),
    ColumnSpec("fee_tier_bps", "int64", nullable=True),
    ColumnSpec("tx_hash", "string"),
    ColumnSpec("block_number", "int64"),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
)

_TRADFI_RATES_CURVE_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("series_id", "string", description="FRED DGS series identifier"),
    ColumnSpec("maturity_years", "float64"),
    ColumnSpec("rate_pct", "float64"),
    ColumnSpec("observed_at", "timestamp[us, UTC]"),
)

_TRADFI_OPTIONS_CHAIN_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("instrument_id", "string"),
    ColumnSpec("underlying", "string"),
    ColumnSpec("expiry", "date"),
    ColumnSpec("strike", "float64"),
    ColumnSpec("option_type", "string", description="call | put"),
    ColumnSpec("bid", "float64", nullable=True),
    ColumnSpec("ask", "float64", nullable=True),
    ColumnSpec("last", "float64", nullable=True),
    ColumnSpec("iv", "float64", nullable=True),
    ColumnSpec("delta", "float64", nullable=True),
    ColumnSpec("gamma", "float64", nullable=True),
    ColumnSpec("vega", "float64", nullable=True),
    ColumnSpec("theta", "float64", nullable=True),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
)

_PREDICTION_TRADES_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("instrument_id", "string"),
    ColumnSpec("venue", "string"),
    ColumnSpec("condition_id", "string"),
    ColumnSpec("outcome", "string"),
    ColumnSpec("price", "float64", description="Implied probability 0-1"),
    ColumnSpec("size", "float64"),
    ColumnSpec("side", "string"),
    ColumnSpec("trade_id", "string"),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
)

_PREDICTION_BOOK_SNAPSHOT_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("instrument_id", "string"),
    ColumnSpec("venue", "string"),
    ColumnSpec("condition_id", "string"),
    ColumnSpec("outcome", "string"),
    ColumnSpec("bids", "list<struct<price:float,size:float>>"),
    ColumnSpec("asks", "list<struct<price:float,size:float>>"),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCHEMA_SPEC_REGISTRY: Final[tuple[SchemaSpec, ...]] = (
    # =====================================================================
    # CeFi — canonical Pydantic-derived
    # =====================================================================
    SchemaSpec(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        columns=_columns_from_pydantic(CanonicalTrade),
        source=f"pydantic:{CanonicalTrade.__name__}",
    ),
    SchemaSpec(
        asset_group=AssetGroup.CEFI,
        data_type="funding_rate",
        columns=_columns_from_pydantic(CanonicalFundingRate),
        source=f"pydantic:{CanonicalFundingRate.__name__}",
    ),
    SchemaSpec(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        columns=_columns_from_pydantic(CanonicalLiquidation),
        source=f"pydantic:{CanonicalLiquidation.__name__}",
    ),
    SchemaSpec(
        asset_group=AssetGroup.CEFI,
        data_type="ticker",
        columns=_columns_from_pydantic(CanonicalTicker),
        source=f"pydantic:{CanonicalTicker.__name__}",
    ),
    SchemaSpec(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        columns=_columns_from_pydantic(CanonicalDerivativeTicker),
        source=f"pydantic:{CanonicalDerivativeTicker.__name__}",
    ),
    SchemaSpec(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot",
        columns=_columns_from_pydantic(CanonicalOrderBook),
        source=f"pydantic:{CanonicalOrderBook.__name__}",
    ),
    # =====================================================================
    # DeFi — manual
    # =====================================================================
    SchemaSpec(
        asset_group=AssetGroup.DEFI,
        data_type="lending_indices",
        columns=_DEFI_LENDING_INDICES_COLUMNS,
        source="manual",
    ),
    SchemaSpec(
        asset_group=AssetGroup.DEFI,
        data_type="dex_pool_swaps",
        columns=_DEFI_DEX_POOL_SWAPS_COLUMNS,
        source="manual",
    ),
    # =====================================================================
    # TradFi — manual (FRED + OPRA both have idiosyncratic shapes)
    # =====================================================================
    SchemaSpec(
        asset_group=AssetGroup.TRADFI,
        data_type="rates_curve",
        columns=_TRADFI_RATES_CURVE_COLUMNS,
        source="manual",
    ),
    SchemaSpec(
        asset_group=AssetGroup.TRADFI,
        data_type="options_chain",
        columns=_TRADFI_OPTIONS_CHAIN_COLUMNS,
        source="manual",
    ),
    # =====================================================================
    # Prediction — manual
    # =====================================================================
    SchemaSpec(
        asset_group=AssetGroup.PREDICTION,
        data_type="trades",
        columns=_PREDICTION_TRADES_COLUMNS,
        source="manual",
    ),
    SchemaSpec(
        asset_group=AssetGroup.PREDICTION,
        data_type="book_snapshot",
        columns=_PREDICTION_BOOK_SNAPSHOT_COLUMNS,
        source="manual",
    ),
    # =====================================================================
    # Sports — manual (fixture/odds vary by source)
    # =====================================================================
    SchemaSpec(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURES",
        columns=_SPORTS_FIXTURE_COLUMNS,
        source="manual",
    ),
    SchemaSpec(
        asset_group=AssetGroup.SPORTS,
        data_type="ODDS",
        columns=_SPORTS_ODDS_COLUMNS,
        source="manual",
    ),
)


def find_schema(
    asset_group: AssetGroup | str,
    data_type: str,
) -> SchemaSpec | None:
    """Return the schema spec for ``(asset_group, data_type)`` or ``None``."""
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    for spec in SCHEMA_SPEC_REGISTRY:
        if spec.asset_group == ag and spec.data_type == data_type:
            return spec
    return None


__all__ = [
    "SCHEMA_SPEC_REGISTRY",
    "ColumnSpec",
    "SchemaSpec",
    "find_schema",
]
