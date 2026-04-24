"""Regression tests for DataType ↔ SchemaContract coverage + the
``validate_row_df`` row-level helper.

Part of ``data_status_institutional_drilldown_2026_04_24``. The enum-coverage
test is the primary quality gate: every ``DataType`` enum value MUST have at
least one registered ``SchemaContract`` somewhere in UAC, otherwise the
institutional drilldown UI cannot render that shard. The per-function tests
pin ``validate_row_df``'s venue-scoped contract semantics so downstream
writers (MTDS handlers, instruments-service writers) cannot silently drop
required columns at the publish boundary.
"""

from __future__ import annotations

import pandas as pd
import pytest

from unified_api_contracts import (
    ColumnSpec,
    RowSchemaValidationError,
    SchemaContract,
    validate_row_df,
)
from unified_api_contracts.internal.domain.market_data_processing.candle_schema import (
    DataType,
)
from unified_api_contracts.internal.schemas.contracts import CONTRACT_REGISTRY


def test_every_datatype_has_at_least_one_schema_contract() -> None:
    """Every ``DataType`` enum value must appear as the third tuple element of
    at least one ``CONTRACT_REGISTRY`` key.

    If this test fails, add a ``SchemaContract`` for the missing data type(s)
    in the appropriate module (``contracts.py``, ``_snapshot_contracts.py``,
    ``_defi_v2_contracts.py``, or ``_sports_prediction_contracts.py``).
    """
    registered_data_types = {dt for (_, _, dt) in CONTRACT_REGISTRY}
    enum_values = {d.value for d in DataType}
    missing = sorted(enum_values - registered_data_types)
    assert not missing, (
        f"DataType enum values without SchemaContract coverage: {missing}. "
        "Every DataType must have at least one SchemaContract registered in "
        "UAC (in contracts.py or any of the *_contracts.py modules)."
    )


# ---------------------------------------------------------------------------
# validate_row_df — happy paths and failure modes
# ---------------------------------------------------------------------------


def _simple_contract() -> SchemaContract:
    """Small CeFi-shaped contract used across validate_row_df tests."""
    return SchemaContract(
        category="cefi",
        instrument_type="perpetual",
        data_type="trades",
        columns=[
            ColumnSpec(name="instrument_id", dtype="string", nullable=False),
            ColumnSpec(name="symbol", dtype="string", nullable=False),
            ColumnSpec(name="price", dtype="float64", nullable=False),
            ColumnSpec(name="size", dtype="float64", nullable=True),
        ],
        symbol_column="symbol",
        required_row_count_min=0,
    )


def test_validate_row_df_happy_path() -> None:
    """All required columns present + dtypes match → no exception."""
    contract = _simple_contract()
    df = pd.DataFrame(
        {
            "instrument_id": ["BTC-USDT-PERP"],
            "symbol": ["BTC-USDT"],
            "price": [50000.0],
            "size": [0.5],
        }
    )
    # Should not raise.
    validate_row_df(df, contract)


def test_validate_row_df_missing_required_column() -> None:
    """Missing required column → ``missing_required`` populated."""
    contract = _simple_contract()
    df = pd.DataFrame(
        {
            "instrument_id": ["BTC-USDT-PERP"],
            "symbol": ["BTC-USDT"],
            # price intentionally missing.
            "size": [0.5],
        }
    )
    with pytest.raises(RowSchemaValidationError) as exc_info:
        validate_row_df(df, contract)
    assert exc_info.value.missing_required == ["price"]


def test_validate_row_df_strict_rejects_extra_columns() -> None:
    """With ``strict=True``, columns beyond the contract raise; default passes."""
    contract = _simple_contract()
    df = pd.DataFrame(
        {
            "instrument_id": ["BTC-USDT-PERP"],
            "symbol": ["BTC-USDT"],
            "price": [50000.0],
            "size": [0.5],
            "extra": ["junk"],
        }
    )
    # Non-strict → passes even with extra column.
    validate_row_df(df, contract, strict=False)
    # Strict → extra column surfaces.
    with pytest.raises(RowSchemaValidationError) as exc_info:
        validate_row_df(df, contract, strict=True)
    assert "extra" in exc_info.value.extra_columns


def test_validate_row_df_dtype_mismatch() -> None:
    """Wrong dtype → ``dtype_mismatches`` populated with the offending triple."""
    contract = _simple_contract()
    df = pd.DataFrame(
        {
            "instrument_id": ["BTC-USDT-PERP"],
            "symbol": ["BTC-USDT"],
            "price": ["50000.0"],  # str not float64.
            "size": [0.5],
        }
    )
    with pytest.raises(RowSchemaValidationError) as exc_info:
        validate_row_df(df, contract)
    mismatches = exc_info.value.dtype_mismatches
    assert len(mismatches) == 1
    col, expected, actual = mismatches[0]
    assert col == "price"
    assert expected == "float64"
    assert actual in ("object", "string")


def test_validate_row_df_venue_scoped_required_column_absent_for_other_venue() -> None:
    """``provided_by_venues`` narrows the required-set: absent is OK off-venue."""
    contract = SchemaContract(
        category="cefi",
        instrument_type="options_chain",
        data_type="options_chain",
        columns=[
            ColumnSpec(name="instrument_id", dtype="string", nullable=False),
            ColumnSpec(name="underlying", dtype="string", nullable=False),
            # Only Deribit publishes mark_iv.
            ColumnSpec(
                name="mark_iv",
                dtype="float64",
                nullable=True,
                required=True,
                provided_by_venues=frozenset({"DERIBIT"}),
            ),
        ],
        symbol_column="underlying",
        required_row_count_min=0,
    )
    # For IBKR, mark_iv is not required — df without it passes.
    df_ibkr = pd.DataFrame({"instrument_id": ["AAPL-2026-01-01-150-C"], "underlying": ["AAPL"]})
    validate_row_df(df_ibkr, contract, venue="IBKR")

    # For Deribit, mark_iv is required — df without it fails.
    df_deribit = pd.DataFrame({"instrument_id": ["BTC-PERP"], "underlying": ["BTC"]})
    with pytest.raises(RowSchemaValidationError) as exc_info:
        validate_row_df(df_deribit, contract, venue="DERIBIT")
    assert exc_info.value.missing_required == ["mark_iv"]


def test_validate_row_df_non_nullable_with_nulls_raises() -> None:
    """Non-nullable column containing NaN → ``null_violations`` populated."""
    contract = _simple_contract()
    df = pd.DataFrame(
        {
            "instrument_id": ["BTC-USDT-PERP"],
            "symbol": ["BTC-USDT"],
            "price": [float("nan")],  # non-nullable — this should fail.
            "size": [0.5],
        }
    )
    with pytest.raises(RowSchemaValidationError) as exc_info:
        validate_row_df(df, contract)
    assert "price" in exc_info.value.null_violations
