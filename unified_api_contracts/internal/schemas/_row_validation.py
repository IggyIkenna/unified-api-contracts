"""Per-row DataFrame validation against ``SchemaContract``.

Provides :class:`RowSchemaValidationError` + :func:`validate_row_df` for
downstream services (MTDS, instruments-service, features-*) that need a
strict, venue-aware check before writing a DataFrame to GCS / BigQuery.

Distinct from :func:`validate_dataframe` (in ``_validation.py``): that helper
returns a list of :class:`Violation` objects suitable for audit logging,
while this helper raises a single aggregated exception with full context so
the caller can emit one ``SCHEMA_VALIDATION_FAILED`` event and halt.

Split out of ``contracts.py`` to keep that module under the 900-line
codex-compliance limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from unified_api_contracts.internal.schemas.contracts import (
    ColumnSpec,
    SchemaContract,
)


@dataclass
class RowSchemaValidationError(Exception):
    """Aggregated validation failure raised by :func:`validate_row_df`.

    Carries every distinct violation class (missing required columns, extra
    unexpected columns, dtype mismatches, null-rule violations) so callers
    can emit a single ``SCHEMA_VALIDATION_FAILED`` event with full context.
    """

    expected_columns: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    # (column_name, expected_dtype, actual_dtype) triples.
    dtype_mismatches: list[tuple[str, str, str]] = field(default_factory=list)
    # Non-nullable columns that contain at least one NaN/None.
    null_violations: list[str] = field(default_factory=list)
    venue: str | None = None

    def __post_init__(self) -> None:
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        parts: list[str] = []
        if self.missing_required:
            parts.append(f"missing required columns: {self.missing_required}")
        if self.extra_columns:
            parts.append(f"unexpected extra columns: {self.extra_columns}")
        if self.dtype_mismatches:
            parts.append(f"dtype mismatches: {self.dtype_mismatches}")
        if self.null_violations:
            parts.append(f"non-nullable columns contain nulls: {self.null_violations}")
        venue_tag = f" (venue={self.venue})" if self.venue else ""
        body = "; ".join(parts) if parts else "no details"
        return f"RowSchemaValidationError{venue_tag}: {body}"

    def __str__(self) -> str:
        return self._build_message()


# ---------------------------------------------------------------------------
# Dtype compatibility table — permissive mapping pandas ↔ contract dtype
# ---------------------------------------------------------------------------

# Contract dtype → acceptable pandas ``str(dtype)`` values.
_DTYPE_COMPAT: dict[str, frozenset[str]] = {
    "int64": frozenset({"int64", "Int64"}),
    "int32": frozenset({"int32", "Int32"}),
    "float64": frozenset({"float64", "Float64"}),
    "float32": frozenset({"float32", "Float32"}),
    "bool": frozenset({"bool", "boolean"}),
    "string": frozenset({"string", "object"}),
    "datetime64[ns, UTC]": frozenset({"datetime64[ns, UTC]", "datetime64[ns]"}),
    # ``decimal`` contract columns show up as pandas ``object`` under pyarrow.
    "decimal": frozenset({"object", "decimal"}),
}


def _dtype_matches(expected: str, actual: str) -> bool:
    compat = _DTYPE_COMPAT.get(expected)
    if compat is None:
        # Unknown contract dtype — fall back to exact match.
        return expected == actual
    return actual in compat


def _column_applies(spec: ColumnSpec, venue: str | None) -> bool:
    """Return True if *spec* is required for the given *venue*.

    A column applies when:
      - ``spec.required`` is True, AND
      - ``spec.provided_by_venues`` is None (all venues) OR
        *venue* is a member of the set (venue-scoped).

    Columns with ``required=False`` never apply (they may be absent entirely).
    When ``venue`` is None and ``provided_by_venues`` is a set, the column is
    treated as not-required (we have no way to know whether this particular
    row came from one of the publishing venues).
    """
    if not spec.required:
        return False
    if spec.provided_by_venues is None:
        return True
    if venue is None:
        return False
    return venue in spec.provided_by_venues


def validate_row_df(
    df: pd.DataFrame,
    contract: SchemaContract,
    venue: str | None = None,
    *,
    strict: bool = False,
) -> None:
    """Validate *df* against *contract*.

    Checks, in order:
      1. Every ``required`` column (resolved against *venue* via
         ``provided_by_venues``) is present.
      2. Column dtypes match permissively (int32/int64 interchangeable,
         pandas ``object`` accepts ``string``, etc.).
      3. ``nullable=False`` columns contain zero null values.
      4. When *strict* is True, no columns beyond those declared in the
         contract are permitted.

    Empty DataFrames (zero rows) are valid iff every required-for-venue
    column is present in ``df.columns`` — we still check column presence but
    skip null / dtype checks.

    Raises:
        RowSchemaValidationError: On any violation. The exception aggregates
            every distinct class of problem so the caller can surface one
            consolidated error.
    """
    expected: list[ColumnSpec] = list(contract.columns)
    expected_names = [c.name for c in expected]
    actual_columns = set(df.columns)

    missing_required: list[str] = [
        spec.name for spec in expected if _column_applies(spec, venue) and spec.name not in actual_columns
    ]

    extra_columns: list[str] = sorted(actual_columns - set(expected_names)) if strict else []

    dtype_mismatches: list[tuple[str, str, str]] = []
    null_violations: list[str] = []

    if not df.empty:
        # df.dtypes carries an untyped element under pandas' stubs; call
        # ``str()`` on both axes so we end up with a plain ``dict[str, str]``.
        actual_dtypes: dict[str, str] = {
            str(col): str(df.dtypes[col])  # pyright: ignore[reportAny]
            for col in df.columns  # pyright: ignore[reportAny]
        }
        for spec in expected:
            if spec.name not in actual_columns:
                continue  # Absence handled by missing_required.
            actual_dtype = actual_dtypes.get(spec.name, "")
            if not _dtype_matches(spec.dtype, actual_dtype):
                dtype_mismatches.append((spec.name, spec.dtype, actual_dtype))
            if not spec.nullable and bool(df[spec.name].isna().any()):
                null_violations.append(spec.name)

    if missing_required or extra_columns or dtype_mismatches or null_violations:
        raise RowSchemaValidationError(
            expected_columns=expected_names,
            missing_required=missing_required,
            extra_columns=extra_columns,
            dtype_mismatches=dtype_mismatches,
            null_violations=null_violations,
            venue=venue,
        )


__all__ = [
    "RowSchemaValidationError",
    "validate_row_df",
]
