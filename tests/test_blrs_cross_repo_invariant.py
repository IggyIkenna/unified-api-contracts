"""Cross-repo invariant: batch-live-reconciliation-service reconciliation contract.

Validates that batch-live-reconciliation-service's core engine surface and
the UAC canonical types it consumes remain contract-stable.

Invariant contract:
  - ReconciliationDimension carries all 12 dimensions that BLRS tags every
    DeviationRecord with; removing a dimension silently drops a deviance category.
  - ReconciliationAgeFields fields are present; BLRS's DeviationRecord inherits
    them and populates them at write-time per the alerting escalation contract.
  - DailyReconReport + ReconVerdictType are importable and carry the expected
    fields; recon_alert_client.py maps DailyReconReport → AlertEvent for alerting.
  - RECON_GREEN_THRESHOLDS carries bps_delta_max, drawdown_pct, fill_rate_min
    per-archetype; orchestrator.py gates the entire pipeline on these values.
  - run_reconciliation + ReconOrchestrator exist in engine/orchestrator.py;
    the CLI/entrypoint calls run_reconciliation as the pipeline entry point.

Uses static AST analysis for BLRS source (not installed in UAC venv).
UAC canonical types are imported directly (installed in this venv).

Negative-control contract: removing any of the 12 ReconciliationDimension
values, or any key from RECON_GREEN_THRESHOLDS, or run_reconciliation from
the orchestrator makes the relevant test fail — those are all read by
name/value in BLRS source and alerting consumers.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -008
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts.alerting import RECON_GREEN_THRESHOLDS, AlertCode
from unified_api_contracts.internal import AlertEvent, DailyReconReport, ReconVerdictType
from unified_api_contracts.internal.reconciliation import ReconciliationAgeFields, ReconciliationDimension

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _blrs_root() -> Path:
    return _workspace_root() / "batch-live-reconciliation-service" / "batch_live_reconciliation_service"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _exported_names(source_path: Path) -> set[str]:
    """Return all top-level names declared in a module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name
                names.add(exported)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name.split(".")[0]
                names.add(exported)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# The 12 reconciliation dimensions BLRS tags on every DeviationRecord.
# alerting-service evaluates thresholds per-dimension; removing any value
# silently drops an entire deviation category from alerting.
EXPECTED_RECON_DIMENSIONS: frozenset[str] = frozenset(
    [
        "ORDERS",
        "FILLS",
        "POSITIONS",
        "BALANCES",
        "FUNDING_PAYMENTS",
        "FEES",
        "TRANSFERS",
        "BORROW_LENDING_BALANCES",
        "COLLATERAL_BALANCES",
        "MARGIN_MODE_AND_LEVERAGE",
        "STRATEGY_LEVEL_ALLOCATION",
        "ACCOUNT_LEVEL_AGGREGATE",
    ]
)

# Keys in RECON_GREEN_THRESHOLDS that orchestrator.py reads by literal name.
# Removing any key breaks the green gate for the entire T+1 pipeline.
EXPECTED_THRESHOLD_KEYS: frozenset[str] = frozenset(
    [
        "bps_delta_max",
        "drawdown_pct",
        "fill_rate_min",
    ]
)

# ReconciliationAgeFields that BLRS.DeviationRecord inherits; alerting-service
# reads unreconciled_age_seconds for WARN/SEV1/SEV0 escalation (15-min/30-min).
EXPECTED_AGE_FIELDS: frozenset[str] = frozenset(
    [
        "first_seen_at",
        "last_seen_at",
        "unreconciled_age_seconds",
    ]
)

# DailyReconReport fields that recon_alert_client.py reads by attribute name.
EXPECTED_DAILY_RECON_REPORT_FIELDS: frozenset[str] = frozenset(
    [
        "verdict_type",
        "run_a_id",
        "run_b_id",
        "window_start",
        "window_end",
        "total_trades_a",
        "total_trades_b",
        "matched",
        "unmatched_a",
        "unmatched_b",
        "is_deterministic",
    ]
)

# Public symbols that must remain in engine/orchestrator.py.
# CLI entrypoint calls run_reconciliation as the pipeline entry point.
EXPECTED_ORCHESTRATOR_SYMBOLS: frozenset[str] = frozenset(
    [
        "run_reconciliation",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard (skip in per-repo CI; fail LOUDLY in full-workspace SIT)
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    blrs_sibling = _workspace_root() / "batch-live-reconciliation-service"
    if not blrs_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: batch-live-reconciliation-service not present at {blrs_sibling}; "
            "cross-repo invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_blrs_orchestrator_entry_point_stable() -> None:
    """run_reconciliation exists in engine/orchestrator.py.

    Skips in per-repo CI (no batch-live-reconciliation-service sibling); runs
    in full-workspace SIT. Fails CLOSED if run_reconciliation disappears —
    the CLI entrypoint and deployment scripts call it by name.
    """
    _skip_if_absent()

    orchestrator_py = _blrs_root() / "engine" / "orchestrator.py"
    assert orchestrator_py.is_file(), (
        f"batch-live-reconciliation-service engine/orchestrator.py missing at {orchestrator_py}"
    )

    names = _exported_names(orchestrator_py)
    missing = sorted(EXPECTED_ORCHESTRATOR_SYMBOLS - names)
    assert not missing, (
        f"batch_live_reconciliation_service/engine/orchestrator.py is MISSING the following symbols:\n"
        f"  {missing}\n\n"
        "run_reconciliation is the T+1 pipeline entry point — removing it breaks the CLI and "
        "any caller that drives reconciliation."
    )


def test_blrs_reconciliation_dimensions_stable() -> None:
    """ReconciliationDimension carries all 12 expected dimension values.

    BLRS tags every DeviationRecord with a ReconciliationDimension;
    alerting-service applies per-dimension thresholds. Removing any dimension
    silently drops an entire category of deviation alerting.
    """
    _skip_if_absent()

    dimension_values = {d.value for d in ReconciliationDimension}
    missing = sorted(EXPECTED_RECON_DIMENSIONS - dimension_values)
    assert not missing, (
        f"ReconciliationDimension is MISSING dimension values that BLRS uses:\n"
        f"  {missing}\n\n"
        "Every BLRS DeviationRecord.dimension must resolve to a valid ReconciliationDimension — "
        "removing any value drops an entire deviation category from alerting."
    )


def test_blrs_recon_age_fields_stable() -> None:
    """ReconciliationAgeFields carries the age-tracking fields that alerting reads.

    alerting-service reads unreconciled_age_seconds for WARN/SEV1/SEV0 escalation
    at the 15-min / 30-min thresholds from disaster_recovery.md §7.
    """
    _skip_if_absent()

    age_field_names = set(ReconciliationAgeFields.model_fields.keys())
    missing = sorted(EXPECTED_AGE_FIELDS - age_field_names)
    assert not missing, (
        f"ReconciliationAgeFields is MISSING fields that alerting-service reads:\n"
        f"  {missing}\n\n"
        "BLRS DeviationRecord inherits ReconciliationAgeFields; unreconciled_age_seconds "
        "drives WARN/SEV1/SEV0 escalation in alerting-service."
    )


def test_blrs_recon_green_thresholds_stable() -> None:
    """RECON_GREEN_THRESHOLDS carries all required per-archetype keys.

    orchestrator.py reads bps_delta_max, drawdown_pct, fill_rate_min by
    literal key name for every archetype in the dict. A missing key raises
    KeyError at runtime, blocking the entire T+1 pipeline.
    """
    _skip_if_absent()

    for archetype, thresholds in RECON_GREEN_THRESHOLDS.items():
        missing = sorted(EXPECTED_THRESHOLD_KEYS - set(thresholds.keys()))
        assert not missing, (
            f"RECON_GREEN_THRESHOLDS['{archetype}'] is MISSING keys that orchestrator reads:\n"
            f"  {missing}\n\n"
            "orchestrator.py accesses these keys by literal name — a missing key raises "
            "KeyError at runtime and blocks the T+1 reconciliation pipeline."
        )


def test_blrs_uac_canonical_types_importable() -> None:
    """UAC exports all canonical types that BLRS and alerting consumers import.

    Confirms DailyReconReport, ReconVerdictType, ReconciliationDimension,
    ReconciliationAgeFields, AlertEvent, AlertCode, and RECON_GREEN_THRESHOLDS
    are importable with the expected field shapes.
    """
    _skip_if_absent()

    # DailyReconReport must carry the fields recon_alert_client.py maps to AlertEvent
    report_fields = set(DailyReconReport.model_fields.keys())
    missing = sorted(EXPECTED_DAILY_RECON_REPORT_FIELDS - report_fields)
    assert not missing, (
        f"DailyReconReport is MISSING fields that recon_alert_client.py reads:\n"
        f"  {missing}\n\n"
        "recon_alert_client.py maps DailyReconReport fields to AlertEvent for alerting-service — "
        "missing fields break the daily T+1 recon verdict reporting."
    )

    # ReconVerdictType must be a StrEnum with DETERMINISM, EXECUTION, COMPOSITE
    verdict_values = {v.value for v in ReconVerdictType}
    for expected in ("DETERMINISM", "EXECUTION", "COMPOSITE"):
        assert expected in verdict_values, (
            f"ReconVerdictType is MISSING value '{expected}' — "
            "recon_alert_client.py and the daily determinism stage use all three verdict types."
        )

    # AlertEvent must be importable (recon_alert_client POSTs it to alerting-service)
    assert hasattr(AlertEvent, "model_fields"), (
        "AlertEvent must be a Pydantic model — "
        "recon_alert_client.py wraps the DailyReconReport in an AlertEvent for the alerting POST."
    )

    # AlertCode must be importable (recon_alert_client sets the alert code)
    assert AlertCode is not None, (
        "AlertCode must be importable from unified_api_contracts.alerting — "
        "recon_alert_client.py uses it to tag the AlertEvent with the correct alert type."
    )

    # RECON_GREEN_THRESHOLDS must be a non-empty dict
    assert isinstance(RECON_GREEN_THRESHOLDS, dict) and len(RECON_GREEN_THRESHOLDS) > 0, (
        "RECON_GREEN_THRESHOLDS must be a non-empty dict — "
        "orchestrator.py iterates all archetypes to evaluate the green gate."
    )
