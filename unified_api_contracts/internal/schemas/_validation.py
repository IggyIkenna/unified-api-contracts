"""DataFrame validation helpers for SchemaContract.

Split out of ``contracts.py`` to keep the main module under the 900-line
codex-compliance limit. ``validate_dataframe`` is re-exported from
``contracts.py`` so downstream callers can continue to import
``from unified_api_contracts.internal.schemas.contracts import validate_dataframe``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pandas as pd

if TYPE_CHECKING:
    from unified_api_contracts.internal.schemas.contracts import (
        DtypeLiteral,
        SchemaContract,
        Violation,
    )


def _dtype_matches(series: pd.Series, expected: DtypeLiteral) -> bool:
    """Return True if the pandas Series dtype matches ``expected``."""
    actual_str = str(series.dtype)
    if expected == "string":
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
        return actual_str in {"object", "float64", "Float64"}
    return False


def validate_dataframe(df: pd.DataFrame, contract: SchemaContract) -> list[Violation]:
    """Validate ``df`` against ``contract`` and return a list of violations.

    Checks in order: required columns present, dtype per column, non-nullable
    columns contain zero nulls, per-column null rate caps respected, total row
    count meets ``required_row_count_min``.

    An empty list means the dataframe satisfies the contract.
    """
    # Lazy import to avoid circular dependency with contracts.py.
    from unified_api_contracts.internal.schemas.contracts import Violation

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
