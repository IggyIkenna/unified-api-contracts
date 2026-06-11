"""Core dataclasses for the per-(asset_group, data_type) ``SchemaSpec`` registry.

Split out of ``schema_spec.py`` so the per-asset-group column modules
(``_schema_spec_defi.py`` / ``_schema_spec_tradfi.py`` /
``_schema_spec_prediction.py``) can import :class:`ColumnSpec` without a
circular import (``schema_spec.py`` imports those modules to assemble the
registry).

``source_aliases`` (CF-18 / operator ratification 2026-06-11 decision #2 —
CITADEL, carry ALL source columns) declares the RAW/legacy source column
names a canonical column carries: the rename map the G4 migrator applies when
canonicalising a legacy parquet to v9 (e.g. polymarket ``conditionId`` →
canonical ``condition_id``), and what the CF-18 schema-attribute completeness
audit (``instruments-service/scripts/migration_schema_completeness.py``)
consults via :func:`carried_column_names` so a renamed-but-carried column is
GREEN while a genuinely dropped column stays RED.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from unified_api_contracts.canonical.gcs_paths import AssetGroup


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: str
    nullable: bool = False
    unit: str | None = None
    description: str | None = None
    source_aliases: tuple[str, ...] = field(default=())
    """Raw/legacy source column names this canonical column CARRIES (rename
    map for the v9 canonicalisation migrator + the CF-18 completeness audit).
    Empty when the canonical name equals the physical source name."""


@dataclass(frozen=True)
class SchemaSpec:
    asset_group: AssetGroup
    data_type: str
    columns: tuple[ColumnSpec, ...]
    source: str  # "pydantic:<ClassName>" | "manual"


def carried_column_names(spec: SchemaSpec) -> frozenset[str]:
    """Every physical column name the spec carries into the v9 contract:
    the canonical names PLUS every declared ``source_aliases`` entry.

    This is the CF-18 matching SSOT — a sampled source column is "carried"
    (not silently truncated) iff it appears in this set. Keeping the union
    here (rather than in the audit script) makes the GREEN condition real:
    the same alias map drives the migrator's renames and the audit's verdict.
    """
    names: set[str] = set()
    for col in spec.columns:
        names.add(col.name)
        names.update(col.source_aliases)
    return frozenset(names)


def merge_columns(*tuples: tuple[ColumnSpec, ...]) -> tuple[ColumnSpec, ...]:
    """Union column tuples, deduplicating by canonical name (first wins).

    Used where one physical writer frame lands under several data_type paths
    (e.g. the AAVE_V3 reserve snapshot is written to ``oracle_prices`` /
    ``rate_indices`` / ``risk_params`` / ``utilization``) so the shared core
    is declared once.
    """
    seen: set[str] = set()
    merged: list[ColumnSpec] = []
    for cols in tuples:
        for col in cols:
            if col.name not in seen:
                seen.add(col.name)
                merged.append(col)
    return tuple(merged)


__all__ = [
    "ColumnSpec",
    "SchemaSpec",
    "carried_column_names",
    "merge_columns",
]
