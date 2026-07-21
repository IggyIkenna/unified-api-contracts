"""Closed-set sanity tests for the normalized alert ledger schema.

Gating deliverable for `deployment_alerts_ingestion_completeness_2026_07_20.md`. Enforces:

1. `FIELD_COVERAGE` has an entry for every `AlertSourcePlane` member — no source silently
   undocumented.
2. Each source's field set is exactly `NormalizedAlertRow`'s fields (minus `source_plane`, which
   is trivially self-populated) — no drift between the schema and the coverage matrix.
3. `NormalizedAlertRow` accepts a minimal row (only the required fields) and a fully-populated one.
"""

from __future__ import annotations

from unified_api_contracts.alerting import (
    FIELD_COVERAGE,
    AlertSourcePlane,
    FieldCoverage,
    NormalizedAlertRow,
)

# `source_plane` is excluded: it's the row's own tag, trivially populated by definition, so the
# coverage matrix documents every OTHER field (including required-but-source-dependent `timestamp`).
_COVERAGE_TRACKED_FIELDS = set(NormalizedAlertRow.model_fields) - {"source_plane"}


def test_field_coverage_has_every_source_plane() -> None:
    assert set(FIELD_COVERAGE.keys()) == set(AlertSourcePlane)


def test_field_coverage_matches_normalized_row_fields() -> None:
    for source_plane, coverage in FIELD_COVERAGE.items():
        assert set(coverage.keys()) == _COVERAGE_TRACKED_FIELDS, (
            f"{source_plane} field coverage drifted from NormalizedAlertRow's fields"
        )
        for field_name, verdict in coverage.items():
            assert isinstance(verdict, FieldCoverage), f"{source_plane}.{field_name} is not a FieldCoverage member"


def test_normalized_alert_row_accepts_minimal_row() -> None:
    row = NormalizedAlertRow(
        timestamp="2026-07-21T00:00:00Z",
        source_plane=AlertSourcePlane.ALERTING_SERVICE,
    )
    assert row.subject_repo is None
    assert row.resolved_state is None


def test_normalized_alert_row_accepts_fully_populated_row() -> None:
    row = NormalizedAlertRow(
        timestamp="2026-07-21T00:00:00Z",
        source_plane=AlertSourcePlane.DEPLOYMENT_API,
        subject_repo="unified-trading-library",
        emitting_repo="deployment-api",
        severity="CRITICAL",
        alert_class="CIRCUIT_BREAKER_OPEN",
        message="circuit breaker open",
        service="market-tick-data-service",
        deployment_target="vm-mtds-01",
        run_url="https://github.com/IggyIkenna/deployment-api/actions/runs/1",
        dedup_key="circuit-breaker-open:mtds",
        resolved_state=None,
    )
    assert row.source_plane is AlertSourcePlane.DEPLOYMENT_API
