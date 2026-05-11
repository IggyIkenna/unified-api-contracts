"""Unit tests for the v8 manifest schema column declarations.

Covers Phase 1.C of ``manifest_schema_final_gate_2026_05_09.md``: the three
NEW v8 columns + version constant + back-compat defaults.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.manifest_schema import (
    EXPECTED_WINDOW_COMPLETENESS_PCT_COLUMN,
    LAST_EMISSION_DECISION_AT_COLUMN,
    MANIFEST_SCHEMA_VERSION_V8,
    READER_FALLBACK_WINDOW_DAYS,
    SERVICE_EMISSION_STATE_COLUMN,
    V8_COLUMN_DEFAULTS,
    V8_NEW_COLUMNS,
)


def test_v8_schema_version_is_eight() -> None:
    """Schema version pinned at 8 (v7 → v8 bump per Phase 1.C)."""
    assert MANIFEST_SCHEMA_VERSION_V8 == 8


def test_v8_new_columns_pins_exactly_three() -> None:
    """Three NEW columns per the writegate slice-b spec — no more, no less."""
    assert len(V8_NEW_COLUMNS) == 3
    assert set(V8_NEW_COLUMNS) == {
        SERVICE_EMISSION_STATE_COLUMN,
        LAST_EMISSION_DECISION_AT_COLUMN,
        EXPECTED_WINDOW_COMPLETENESS_PCT_COLUMN,
    }


def test_v8_column_names_match_canonical_strings() -> None:
    """Column-name SSOT — parquet headers + kwargs MUST use these strings."""
    assert SERVICE_EMISSION_STATE_COLUMN == "service_emission_state"
    assert LAST_EMISSION_DECISION_AT_COLUMN == "last_emission_decision_at"
    assert EXPECTED_WINDOW_COMPLETENESS_PCT_COLUMN == "expected_window_completeness_pct"


def test_v8_column_ordering_stable() -> None:
    """``V8_NEW_COLUMNS`` ordering is the SSOT for migration-script row construction."""
    assert V8_NEW_COLUMNS == (
        "service_emission_state",
        "last_emission_decision_at",
        "expected_window_completeness_pct",
    )


def test_v8_column_defaults_all_none() -> None:
    """All three v8 columns default to ``None`` for v7 row back-compat."""
    assert V8_COLUMN_DEFAULTS == {
        "service_emission_state": None,
        "last_emission_decision_at": None,
        "expected_window_completeness_pct": None,
    }
    assert set(V8_COLUMN_DEFAULTS.keys()) == set(V8_NEW_COLUMNS)


def test_reader_fallback_window_is_thirty_days() -> None:
    """Reader fallback tolerates missing v8 columns for 30 days post-migration."""
    assert READER_FALLBACK_WINDOW_DAYS == 30
