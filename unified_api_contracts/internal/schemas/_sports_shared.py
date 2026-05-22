"""Shared building blocks for SPORTS SchemaContracts.

Module-private helpers used by ``_sports_contracts``, ``_sports_match_contracts``,
and ``_sports_derived_contracts``. Keeps each family file under the codex
900-line limit without duplicating ColumnSpec helpers.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas.contracts import ColumnSpec

DATA_AVAILABLE_AT = ColumnSpec(
    name="available_at",
    dtype="datetime64[ns, UTC]",
    nullable=False,
    description=(
        "UTC timestamp when the adapter last fetched / wrote this row. "
        "Used for freshness SLOs and cache-staleness checks. Always tz=UTC."
    ),
)


def stringy(name: str, desc: str, nullable: bool = True) -> ColumnSpec:
    """Helper for the many string-typed FootyStats / Understat columns."""
    return ColumnSpec(name=name, dtype="string", nullable=nullable, description=desc)


def f64(name: str, desc: str, nullable: bool = True) -> ColumnSpec:
    return ColumnSpec(name=name, dtype="float64", nullable=nullable, description=desc)


def i64(name: str, desc: str, nullable: bool = True) -> ColumnSpec:
    return ColumnSpec(name=name, dtype="int64", nullable=nullable, description=desc)
