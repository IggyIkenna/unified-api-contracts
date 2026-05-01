"""Instrument-catalogue SchemaContract — derived from INSTRUMENTS_PARQUET_SCHEMA.

instruments-service writes one bundled parquet per ``(venue, day)`` (DeFi: per
``(venue, chain, day)``) under
``instrument_availability/by_date/day=.../venue=.../instruments.parquet``. The
parquet has a single fixed shape — the catalogue — that does not vary with
data_type or instrument_type. Manifest rows for these shards carry empty
``instrument_type`` and empty ``data_type`` columns (legacy v4 shape).

This module synthesises the SchemaContract for that catalogue programmatically
from INSTRUMENTS_PARQUET_SCHEMA (the SSOT for the parquet write itself), then
registers the same contract under each asset_group with the synthetic
``("instrument_catalogue", "instrument_catalogue")`` axis pair so downstream
schema-lookup callers can resolve it without inventing missing axes.

Side-effect on import: mutates CONTRACT_REGISTRY in ``contracts.py``.
"""

from __future__ import annotations

from typing import cast

from unified_api_contracts.internal.domain.instruments._instruments_parquet_schema import (
    INSTRUMENTS_PARQUET_SCHEMA,
)
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    AssetGroupLiteral,
    ColumnSpec,
    DtypeLiteral,
    SchemaContract,
)

# Map pandas/numpy dtype strings used in INSTRUMENTS_PARQUET_SCHEMA to the
# SchemaContract DtypeLiteral set. Keep this table tiny and explicit — silent
# coercion of unknown dtypes is exactly the kind of drift G7 forbids.
_DTYPE_MAP: dict[str, DtypeLiteral] = {
    "string": "string",
    "int64": "int64",
    "int32": "int32",
    "float64": "float64",
    "float32": "float32",
    "bool": "bool",
    # INSTRUMENTS_PARQUET_SCHEMA stores naive UTC datetimes ("datetime64[ns]").
    # SchemaContract's DtypeLiteral only includes the tz-aware variant; the
    # parquet read path coerces tz-naive UTC ↔ tz-aware UTC at the boundary
    # (see ``build_canonical_instruments_dataframe``), so mapping to the
    # tz-aware literal here is correct for the contract surface.
    "datetime64[ns]": "datetime64[ns, UTC]",
}


def _build_catalogue_columns() -> list[ColumnSpec]:
    out: list[ColumnSpec] = []
    for raw in INSTRUMENTS_PARQUET_SCHEMA:
        name = cast(str, raw["name"])
        raw_dtype = cast(str, raw["type"])
        dtype = _DTYPE_MAP.get(raw_dtype)
        if dtype is None:
            # Unknown dtype — surface as schema-build failure rather than
            # silently dropping the column (matches the no-silent-drift rule).
            raise ValueError(
                f"INSTRUMENTS_PARQUET_SCHEMA column {name!r} has unmapped dtype "
                f"{raw_dtype!r}. Extend _DTYPE_MAP in "
                f"_instrument_catalogue_contract.py."
            )
        required = bool(raw.get("required", False))
        nullable_raw = raw.get("nullable")
        # If "nullable" is absent, treat required→non-nullable, optional→nullable.
        nullable = bool(nullable_raw) if nullable_raw is not None else (not required)
        description_raw = raw.get("description")
        description = description_raw if isinstance(description_raw, str) else None
        out.append(
            ColumnSpec(
                name=name,
                dtype=dtype,
                nullable=nullable,
                required=required,
                description=description,
            )
        )
    return out


_CATALOGUE_COLUMNS = _build_catalogue_columns()


def _make_catalogue_contract(asset_group: AssetGroupLiteral) -> SchemaContract:
    return SchemaContract(
        asset_group=asset_group,
        instrument_type="instrument_catalogue",
        data_type="instrument_catalogue",
        columns=_CATALOGUE_COLUMNS,
        symbol_column="instrument_key",
        required_row_count_min=0,
    )


# Register one contract per asset_group that uses instruments-service. Sports
# already populates instrument_type/data_type properly per shard so it doesn't
# strictly need this fallback, but registering it keeps behaviour uniform when
# a caller asks for the bare catalogue shape.
CEFI_INSTRUMENT_CATALOGUE: SchemaContract = _make_catalogue_contract("cefi")
TRADFI_INSTRUMENT_CATALOGUE: SchemaContract = _make_catalogue_contract("tradfi")
DEFI_INSTRUMENT_CATALOGUE: SchemaContract = _make_catalogue_contract("defi")
PREDICTION_INSTRUMENT_CATALOGUE: SchemaContract = _make_catalogue_contract("prediction")
SPORTS_INSTRUMENT_CATALOGUE: SchemaContract = _make_catalogue_contract("sports")

# Side-effect registration — same pattern used by _legacy_venue_overrides,
# _sports_prediction_contracts, _defi_v2_contracts, _snapshot_contracts.
CONTRACT_REGISTRY[("cefi", "instrument_catalogue", "instrument_catalogue")] = CEFI_INSTRUMENT_CATALOGUE
CONTRACT_REGISTRY[("tradfi", "instrument_catalogue", "instrument_catalogue")] = TRADFI_INSTRUMENT_CATALOGUE
CONTRACT_REGISTRY[("defi", "instrument_catalogue", "instrument_catalogue")] = DEFI_INSTRUMENT_CATALOGUE
CONTRACT_REGISTRY[("prediction", "instrument_catalogue", "instrument_catalogue")] = PREDICTION_INSTRUMENT_CATALOGUE
CONTRACT_REGISTRY[("sports", "instrument_catalogue", "instrument_catalogue")] = SPORTS_INSTRUMENT_CATALOGUE


__all__ = [
    "CEFI_INSTRUMENT_CATALOGUE",
    "DEFI_INSTRUMENT_CATALOGUE",
    "PREDICTION_INSTRUMENT_CATALOGUE",
    "SPORTS_INSTRUMENT_CATALOGUE",
    "TRADFI_INSTRUMENT_CATALOGUE",
]
