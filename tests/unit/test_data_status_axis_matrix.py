"""Cross-registry consistency tests for data_status_axis_matrix.py.

Data-status plan
``data_status_multi_axis_shard_propagation_2026_05_06.plan.md`` Phase 0.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.data_status_axis_matrix import (
    _KNOWN_ASSET_GROUPS,
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
    get_breakdown_axes,
    get_display_axes,
    get_primary_axis,
    get_shard_axes,
    is_shard_axis,
)


def test_asset_group_keys_are_lowercase() -> None:
    """Every (service, asset_group) key uses lowercase asset_group per
    workspace CLAUDE.md asset-group vocabulary rule."""
    for matrix in (SHARD_AXIS_MATRIX, DISPLAY_AXES, PRIMARY_AXIS):
        for service, asset_group in matrix:
            assert asset_group == asset_group.lower(), f"asset_group must be lowercase: ({service!r}, {asset_group!r})"
            assert asset_group in _KNOWN_ASSET_GROUPS, f"unknown asset_group {asset_group!r} for service {service!r}"


def test_every_shard_key_has_primary_axis() -> None:
    """Every entry in SHARD_AXIS_MATRIX MUST have a PRIMARY_AXIS entry —
    the deployment-api consumer reads PRIMARY_AXIS to pick the cell-grid
    main dimension; missing = silent fall-through to a default."""
    missing = sorted(set(SHARD_AXIS_MATRIX) - set(PRIMARY_AXIS))
    assert not missing, f"SHARD_AXIS_MATRIX entries without PRIMARY_AXIS: {missing}"


def test_primary_axis_is_in_shard_or_display() -> None:
    """The primary axis MUST be one of the columns the writer actually
    populates (shard atom OR display column). Otherwise the cell-grid
    main dimension would always be empty."""
    for key, primary in PRIMARY_AXIS.items():
        shard = SHARD_AXIS_MATRIX.get(key, ())
        display = DISPLAY_AXES.get(key, ())
        assert primary in shard or primary in display, (
            f"primary axis {primary!r} for {key} not in shard {shard} or display {display}"
        )


def test_breakdown_axes_excludes_primary() -> None:
    """BREAKDOWN_AXES MUST NOT contain the primary axis — the cell-grid
    is already showing it as the main dimension."""
    for key, breakdowns in BREAKDOWN_AXES.items():
        primary = PRIMARY_AXIS.get(key)
        if primary is not None:
            assert primary not in breakdowns, f"primary axis {primary!r} leaked into BREAKDOWN_AXES for {key}"


def test_breakdown_axes_is_union_of_shard_and_display() -> None:
    """BREAKDOWN_AXES = (shard union display) - {primary}. No drift."""
    for key, shard in SHARD_AXIS_MATRIX.items():
        display = DISPLAY_AXES.get(key, ())
        primary = PRIMARY_AXIS.get(key)
        seen: set[str] = set()
        expected: list[str] = []
        for axis in (*shard, *display):
            if axis == primary or axis in seen:
                continue
            seen.add(axis)
            expected.append(axis)
        assert BREAKDOWN_AXES[key] == tuple(expected), (
            f"breakdown drift for {key}: got {BREAKDOWN_AXES[key]} expected {tuple(expected)}"
        )


def test_data_pipeline_defi_entries_have_chain_in_shard() -> None:
    """Data-pipeline DEFI shard atoms MUST include ``chain`` per
    CLAUDE.md shard-key matrix — each chain is a separate RPC/subgraph
    endpoint with independent failure modes. Experiment-keyed services
    (strategy / execution) shard on job_id / strategy_id instead."""
    data_pipeline_services = {
        "instruments-service",
        "market-tick-data-service",
        "market-data-processing-service",
        "features-delta-one-service",
        "features-volatility-service",
        "features-onchain-service",
        "features-cross-instrument-service",
        "features-multi-timeframe-service",
    }
    for (service, asset_group), shard in SHARD_AXIS_MATRIX.items():
        if asset_group != DEFI or service not in data_pipeline_services:
            continue
        assert "chain" in shard, f"DEFI service {service!r} missing chain in shard axes: {shard}"


def test_prediction_entries_have_canonical_question_group_in_shard() -> None:
    """Every PREDICTION shard atom that touches market-side data MUST
    include ``canonical_question_group`` per the predictions plan +
    CLAUDE.md prediction shard-key matrix."""
    pricing_services = {
        "instruments-service",
        "market-tick-data-service",
        "market-data-processing-service",
        "features-cross-instrument-service",
    }
    for (service, asset_group), shard in SHARD_AXIS_MATRIX.items():
        if asset_group != PREDICTION or service not in pricing_services:
            continue
        assert "canonical_question_group" in shard, (
            f"PREDICTION service {service!r} missing canonical_question_group: {shard}"
        )


def test_experiment_services_have_job_id_in_shard() -> None:
    """ml-training / ml-inference / strategy / execution MUST shard on
    job_id so each experiment run is independently visible. Re-running
    the same configs = a new job_id, NOT idempotent skip."""
    experiment_services = {
        "ml-training-service",
        "ml-inference-service",
        "strategy-service",
        "execution-service",
    }
    for (service, _asset_group), shard in SHARD_AXIS_MATRIX.items():
        if service not in experiment_services:
            continue
        assert "job_id" in shard, f"experiment service {service!r} missing job_id in shard: {shard}"


def test_sports_entries_do_not_have_fixture_id_in_shard() -> None:
    """``fixture_id`` is display-axis only per the data-status plan
    (2026-05-06): ``(league_id, day)`` already bounds the fixture set
    per cell; per-fixture detail comes from the parquet at drill-down."""
    for (service, asset_group), shard in SHARD_AXIS_MATRIX.items():
        if asset_group != SPORTS:
            continue
        assert "fixture_id" not in shard, f"sports service {service!r} has fixture_id in shard atoms: {shard}"


def test_shared_pseudo_group_only_for_cross_asset_services() -> None:
    """Only ml-training, ml-inference, features-calendar shard on the
    ``shared`` pseudo-asset-group; everything else keys on a real
    asset_group."""
    expected_shared_services = {
        "ml-training-service",
        "ml-inference-service",
        "features-calendar-service",
    }
    actual_shared_services = {service for (service, asset_group) in SHARD_AXIS_MATRIX if asset_group == SHARED}
    assert actual_shared_services == expected_shared_services, (
        f"shared services drift: {actual_shared_services} vs {expected_shared_services}"
    )


def test_features_onchain_only_covers_defi() -> None:
    """features-onchain is DEFI-only; no other asset_group should have
    a SHARD entry under that service."""
    onchain_groups = {
        asset_group for (service, asset_group) in SHARD_AXIS_MATRIX if service == "features-onchain-service"
    }
    assert onchain_groups == {DEFI}, f"features-onchain coverage drift: {onchain_groups}"


def test_features_sports_only_covers_sports() -> None:
    """features-sports is SPORTS-only."""
    sports_groups = {
        asset_group for (service, asset_group) in SHARD_AXIS_MATRIX if service == "features-sports-service"
    }
    assert sports_groups == {SPORTS}, f"features-sports coverage drift: {sports_groups}"


def test_get_shard_axes_returns_tuple() -> None:
    assert get_shard_axes("instruments-service", "defi") == ("venue", "chain")
    assert get_shard_axes("instruments-service", "DEFI") == ("venue", "chain")
    assert get_shard_axes("nonexistent-service", "cefi") == ()


def test_get_display_axes_returns_tuple() -> None:
    assert get_display_axes("instruments-service", "cefi") == (
        "instrument_type",
        "data_type",
    )
    assert get_display_axes("nonexistent-service", "cefi") == ()


def test_get_primary_axis_returns_string_or_none() -> None:
    assert get_primary_axis("instruments-service", "defi") == "venue"
    assert get_primary_axis("instruments-service", "sports") == "data_type"
    assert get_primary_axis("ml-training-service", "shared") == "model_family"
    assert get_primary_axis("nonexistent-service", "cefi") is None


def test_get_breakdown_axes_excludes_primary() -> None:
    """For instruments-service+DEFI: shard=(venue, chain),
    display=(instrument_type, data_type), primary=venue, so
    breakdowns = (chain, instrument_type, data_type)."""
    assert get_breakdown_axes("instruments-service", "defi") == (
        "chain",
        "instrument_type",
        "data_type",
    )


def test_is_shard_axis() -> None:
    assert is_shard_axis("instruments-service", "defi", "chain") is True
    assert is_shard_axis("instruments-service", "defi", "instrument_type") is False
    assert is_shard_axis("market-tick-data-service", "sports", "fixture_id") is False
    assert is_shard_axis("execution-service", "cefi", "job_id") is True


def test_uppercase_asset_group_input_is_normalised() -> None:
    """Helpers accept both upper- and lowercase asset_group; deployment-api
    consumer doesn't have to .lower() before calling."""
    assert get_shard_axes("instruments-service", "DEFI") == get_shard_axes("instruments-service", "defi")
    assert get_primary_axis("ml-training-service", "SHARED") == "model_family"


@pytest.mark.parametrize(
    ("service", "asset_group"),
    [
        ("instruments-service", CEFI),
        ("instruments-service", TRADFI),
        ("instruments-service", DEFI),
        ("instruments-service", SPORTS),
        ("instruments-service", PREDICTION),
        ("market-tick-data-service", CEFI),
        ("market-tick-data-service", DEFI),
        ("market-tick-data-service", PREDICTION),
        ("market-data-processing-service", CEFI),
        ("market-data-processing-service", DEFI),
        ("ml-training-service", SHARED),
        ("ml-inference-service", SHARED),
        ("strategy-service", DEFI),
        ("execution-service", DEFI),
    ],
)
def test_every_canonical_pairing_has_full_coverage(service: str, asset_group: str) -> None:
    """Sanity check: each canonical (service, asset_group) pair we expect
    to ship has shard + display + primary + breakdown all populated."""
    key = (service, asset_group)
    assert key in SHARD_AXIS_MATRIX
    assert key in DISPLAY_AXES
    assert key in PRIMARY_AXIS
    assert key in BREAKDOWN_AXES
