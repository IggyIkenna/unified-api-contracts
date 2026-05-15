"""Unit tests for SHARD_AXIS_MATRIX consistency (data_status_comprehensive_test_coverage B.1 / A.1).

data_status_comprehensive_test_coverage_2026_05_07.md A.1.

Invariants guarded here:
1. Every axis in SHARD_AXIS_MATRIX is either a valid UTL manifest kwarg OR a DISPLAY_AXES-only
   axis (i.e. not used as a manifest row_key). Drift = silent correctness bug.
2. No (service, asset_group) entry has duplicate axes.
3. Every asset_group key is in the workspace-canonical lowercase set.
4. PRIMARY_AXIS for every entry is either in SHARD_AXIS_MATRIX OR DISPLAY_AXES for that key.
5. BREAKDOWN_AXES derivation is deterministic (re-derive and compare).

Known drifts (xfail tests):
- ``canonical_question_group`` appears in SHARD_AXIS_MATRIX for prediction entries but is NOT
  in UTL _ROW_KEY_COLUMNS (the actual manifest write uses ``underlying``). This drift means
  the SHARD_AXIS_MATRIX claims a shard granularity the writer does not honour.
  Tracking: data_status_comprehensive_test_coverage_2026_05_07.md § A.1.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.data_status_axis_matrix import (
    BREAKDOWN_AXES,
    CEFI,
    DEFI,
    DISPLAY_AXES,
    PREDICTION,
    PRIMARY_AXIS,
    SHARD_AXIS_MATRIX,
    SHARED,
    SPORTS,
    TRADFI,
    _derive_breakdown_axes,
)

# ---------------------------------------------------------------------------
# UTL _ROW_KEY_COLUMNS as of 2026-05-14. SSOT: UTL manifest_writer.py:784.
# When UTL adds a valid kwarg, add it here too to keep test in sync.
# ---------------------------------------------------------------------------
_VALID_MANIFEST_KWARGS: frozenset[str] = frozenset(
    {
        "date",
        "venue",
        "data_type",
        "timeframe",
        "league_id",
        "chain",
        "instrument_type",
        "underlying",
        "feature_group",
        "feature_family",
        "model_family",
        "training_period",
        "strategy_id",
        "client_id",
        "instruction_type",
        "instrument_id",
        "quote_asset",
        "margin_type",
        "combo_type",
        "fixture_id",
        "job_id",
        "pipeline_mode",
    }
)

# Canonical lowercase asset_group keys per workspace CLAUDE.md
_WORKSPACE_ASSET_GROUPS: frozenset[str] = frozenset({CEFI, DEFI, TRADFI, SPORTS, PREDICTION, SHARED})

# Known drifts: axes in SHARD_AXIS_MATRIX not in _VALID_MANIFEST_KWARGS.
# Each must have a fix path below.
_KNOWN_DRIFT_AXES: frozenset[str] = frozenset(
    {
        # canonical_question_group: prediction entries in SHARD_AXIS_MATRIX claim this as a
        # shard axis, but instruments-service manifest writes use ``underlying=<group>`` not
        # canonical_question_group. Fix: update SHARD_AXIS_MATRIX to use ``underlying`` for
        # prediction entries, OR add canonical_question_group to UTL _ROW_KEY_COLUMNS and
        # update instruments-service. Tracking: A.1.
        "canonical_question_group",
    }
)


def test_all_shard_axes_are_valid_manifest_kwargs_or_known_drift() -> None:
    """Every SHARD_AXIS_MATRIX axis is a UTL manifest kwarg (excl. _KNOWN_DRIFT_AXES)."""
    invalid: dict[tuple[str, str], list[str]] = {}
    for (service, asset_group), axes in SHARD_AXIS_MATRIX.items():
        bad = [ax for ax in axes if ax not in _VALID_MANIFEST_KWARGS and ax not in _KNOWN_DRIFT_AXES]
        if bad:
            invalid[(service, asset_group)] = bad
    assert not invalid, (
        "SHARD_AXIS_MATRIX axes not in UTL _ROW_KEY_COLUMNS (and not in _KNOWN_DRIFT_AXES):\n"
        + "\n".join(f"  {k}: {v}" for k, v in sorted(invalid.items()))
        + "\nEither add the axis to UTL _ROW_KEY_COLUMNS or add it to _KNOWN_DRIFT_AXES with a fix path."
    )


def test_no_duplicate_axes_per_shard_entry() -> None:
    """No (service, asset_group) entry lists the same axis twice."""
    for key, axes in SHARD_AXIS_MATRIX.items():
        assert len(axes) == len(set(axes)), f"Duplicate axes in SHARD_AXIS_MATRIX[{key!r}]: {axes}"


def test_all_asset_groups_are_workspace_canonical() -> None:
    """Every asset_group key is one of the workspace-canonical lowercase identifiers."""
    for service, asset_group in SHARD_AXIS_MATRIX:
        assert asset_group in _WORKSPACE_ASSET_GROUPS, (
            f"SHARD_AXIS_MATRIX key ({service!r}, {asset_group!r}) uses unknown asset_group. "
            f"Allowed: {sorted(_WORKSPACE_ASSET_GROUPS)}"
        )


def test_primary_axis_is_in_shard_or_display_axes() -> None:
    """For each (service, asset_group), the PRIMARY_AXIS value appears in SHARD or DISPLAY axes."""
    mismatches: list[str] = []
    for key, primary in PRIMARY_AXIS.items():
        shard = set(SHARD_AXIS_MATRIX.get(key, ()))
        display = set(DISPLAY_AXES.get(key, ()))
        if primary not in shard and primary not in display:
            mismatches.append(
                f"PRIMARY_AXIS[{key!r}]={primary!r} not in SHARD_AXIS_MATRIX={sorted(shard)} "
                f"or DISPLAY_AXES={sorted(display)}"
            )
    assert not mismatches, "\n".join(mismatches)


def test_breakdown_axes_derivation_is_deterministic() -> None:
    """Re-deriving BREAKDOWN_AXES from SHARD + DISPLAY - PRIMARY produces the same result."""
    rederived = _derive_breakdown_axes()
    assert rederived == dict(BREAKDOWN_AXES), (
        "BREAKDOWN_AXES is stale — re-derive detected drift. "
        "If you edited SHARD_AXIS_MATRIX or DISPLAY_AXES, BREAKDOWN_AXES auto-updates at import; "
        "this failure means the derivation function is broken."
    )


def test_display_axes_has_no_duplicate_axes_per_entry() -> None:
    """No DISPLAY_AXES entry lists the same axis twice."""
    for key, axes in DISPLAY_AXES.items():
        assert len(axes) == len(set(axes)), f"Duplicate axes in DISPLAY_AXES[{key!r}]: {axes}"


def test_shard_and_display_axes_do_not_overlap_per_entry() -> None:
    """Shard axes and display axes for the same key should not overlap (no axis counted twice)."""
    overlaps: list[str] = []
    for key in SHARD_AXIS_MATRIX:
        shard = set(SHARD_AXIS_MATRIX[key])
        display = set(DISPLAY_AXES.get(key, ()))
        both = shard & display
        if both:
            overlaps.append(f"{key!r}: {sorted(both)}")
    assert not overlaps, (
        "Axes appear in both SHARD_AXIS_MATRIX and DISPLAY_AXES (should be in exactly one):\n" + "\n".join(overlaps)
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known drift: canonical_question_group is in SHARD_AXIS_MATRIX for prediction entries "
        "but is NOT a UTL manifest kwarg. instruments-service uses ``underlying`` instead. "
        "Fix path: update SHARD_AXIS_MATRIX prediction entries to ``underlying`` OR add "
        "canonical_question_group to UTL _ROW_KEY_COLUMNS."
    ),
)
def test_canonical_question_group_drift_is_resolved() -> None:
    """Asserts that canonical_question_group is absent from SHARD_AXIS_MATRIX (xfail until fixed)."""
    entries_with_drift = [key for key, axes in SHARD_AXIS_MATRIX.items() if "canonical_question_group" in axes]
    assert not entries_with_drift, f"canonical_question_group still in SHARD_AXIS_MATRIX: {entries_with_drift}"
