"""Unit tests for the feature-DAG UAC SSOT (Phase 1A).

Plan: ``unified-trading-pm/plans/active/feature_dag_uac_ssot_and_features_coverage_2026_05_06.md``.

Asserts the three Phase 1A invariants from the plan:

1. Every service in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` has a corresponding
   workspace directory.
2. Every entry in ``FEATURE_REQUIRED_INPUTS`` references a real
   ``(asset_group, data_type)`` pair from ``AVAILABILITY_AT_SEMANTICS`` AND
   the declared ``available_at_rule`` matches that registry.
3. ``FEATURE_REQUIRED_INPUTS`` is acyclic — no feature_group references
   itself directly or transitively. (Today the dict only declares external
   data-source inputs, not inter-feature_group inputs, so this check is
   trivially true; included as a regression guard for the day a derived
   feature_group is added.)
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from pathlib import Path

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
)
from unified_api_contracts.canonical.domain.features import (
    EXPECTED_FEATURE_GROUPS_BY_SERVICE,
    FEATURE_COVERAGE_START,
    FEATURE_REQUIRED_INPUTS,
    InputReq,
    get_feature_coverage_start,
    get_required_inputs,
    has_required_inputs,
    is_known_feature_group,
    list_feature_groups,
    list_services,
    validate_required_inputs,
)

# ---------------------------------------------------------------------------
# Invariant 1 — every service in registry has a workspace directory.
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """Return the workspace root (the directory containing this UAC repo)."""
    # tests/<this_file>.py -> tests/ -> repo root -> workspace root
    return Path(__file__).resolve().parents[2]


def test_every_service_has_workspace_directory() -> None:
    """Plan invariant (a): every service in EXPECTED_FEATURE_GROUPS_BY_SERVICE
    has a corresponding directory in the workspace."""
    workspace = _workspace_root()
    present = [service for service in EXPECTED_FEATURE_GROUPS_BY_SERVICE if (workspace / service).is_dir()]
    missing = [service for service in EXPECTED_FEATURE_GROUPS_BY_SERVICE if not (workspace / service).is_dir()]
    # Per-repo CI checks out only this repo (workspace-qg renders dep_repos=""), so no
    # sibling service dirs are present. This cross-repo workspace invariant can only be
    # verified from a full-workspace checkout (local quality-gates.sh or the full-workspace
    # SIT job); skip cleanly in isolated CI. When siblings ARE present (full workspace) the
    # assert still catches a service renamed/removed without updating the SSOT set.
    if not present:
        pytest.skip(
            f"per-repo CI checkout: no sibling service repos under {workspace}; cross-repo "
            "workspace invariant runs under local quality-gates.sh / full-workspace SIT"
        )
    assert not missing, (
        f"services declared in EXPECTED_FEATURE_GROUPS_BY_SERVICE but absent from {workspace}: {missing}"
    )


# ---------------------------------------------------------------------------
# Invariant 2 — every InputReq references a real AVAILABILITY_AT_SEMANTICS entry.
# ---------------------------------------------------------------------------


def test_validate_required_inputs_passes() -> None:
    """Plan invariant (b): the registry-internal validator returns no issues.

    ``validate_required_inputs()`` checks:
    - Every ``(asset_group, data_type)`` is a key in ``AVAILABILITY_AT_SEMANTICS``.
    - Every ``InputReq.available_at_rule`` matches ``AVAILABILITY_AT_SEMANTICS``.
    - No empty input lists (omit the key instead).
    """
    issues = validate_required_inputs()
    assert issues == [], "FEATURE_REQUIRED_INPUTS validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)


def test_every_input_req_has_registered_availability_semantic() -> None:
    """Same as above but spelt as a direct iteration so test failures
    point at the offending feature_group + (asset_group, data_type)."""
    for feature_group, reqs in FEATURE_REQUIRED_INPUTS.items():
        for req in reqs:
            key = (req.asset_group, req.data_type)
            assert key in AVAILABILITY_AT_SEMANTICS, (
                f"feature_group {feature_group!r} declares input "
                f"({req.asset_group}, {req.data_type}) but no "
                "AVAILABILITY_AT_SEMANTICS entry exists for that pair"
            )
            assert AVAILABILITY_AT_SEMANTICS[key] == req.available_at_rule, (
                f"feature_group {feature_group!r}: declared "
                f"available_at_rule={req.available_at_rule!r} but "
                f"AVAILABILITY_AT_SEMANTICS says "
                f"{AVAILABILITY_AT_SEMANTICS[key]!r}"
            )


# ---------------------------------------------------------------------------
# Invariant 3 — DAG has no cycles.
# ---------------------------------------------------------------------------


def test_feature_dag_has_no_cycles() -> None:
    """Plan invariant (c): the feature-input DAG is acyclic.

    ``FEATURE_REQUIRED_INPUTS`` declares only external ``(asset_group,
    data_type)`` inputs — there are no feature_group → feature_group
    edges in the dict's current shape. The DAG of inter-feature_group
    dependencies (e.g. ``aave_rate_impact`` depending on
    ``aave_lending_rates``) lives in each service's local
    ``feature_builder_registry.py`` ``BuilderEntry.depends_on`` and is
    Kahn-sorted there.

    This test therefore checks the trivially-true property that no
    feature_group is its own input. The check exists as a regression
    guard for when ``InputReq`` (or a successor) gains an explicit
    ``feature_group`` axis — at which point the cycle check becomes
    non-trivial.

    Note: ``data_type`` and ``feature_group`` are separate namespaces;
    feature_group ``"liquidations"`` (delta-one calculator) and
    data_type ``"liquidations"`` (cefi market-data shard) coincidentally
    share a string but are distinct nodes.
    """
    for feature_group, reqs in FEATURE_REQUIRED_INPUTS.items():
        # No InputReq today carries a `feature_group` axis. A self-loop
        # would only be possible via such an axis. The check is a
        # placeholder that becomes meaningful when the dataclass is
        # extended.
        for req in reqs:
            assert getattr(req, "feature_group", None) != feature_group, (
                f"feature_group {feature_group!r} self-references — introduces a cycle in the feature-input DAG"
            )


# ---------------------------------------------------------------------------
# Helper functions — sanity round-trip.
# ---------------------------------------------------------------------------


def test_get_required_inputs_round_trips() -> None:
    """``get_required_inputs`` returns the same list as direct dict access."""
    for fg, reqs in FEATURE_REQUIRED_INPUTS.items():
        assert get_required_inputs(fg) == reqs


def test_get_required_inputs_unknown_returns_empty() -> None:
    """Unknown feature_group → empty list (no lookahead-bias enforcement)."""
    assert get_required_inputs("definitely-not-a-real-feature-group") == []
    assert has_required_inputs("definitely-not-a-real-feature-group") is False


def test_has_required_inputs_true_for_seeded_groups() -> None:
    """Seeded groups report has_required_inputs=True."""
    assert has_required_inputs("lst_staking_yields") is True
    assert has_required_inputs("technical_indicators") is True


def test_phase_1a_2_lift_8_onchain_feature_groups_seeded() -> None:
    """Phase 1A.2 follow-up shipped 2026-05-07 — 8 of the 10 deferred onchain
    feature_groups now in FEATURE_REQUIRED_INPUTS after the
    AVAILABILITY_AT_SEMANTICS defi vocabulary gap closed (UAC@2f40c9d).

    Plan: ``feature_dag_uac_ssot_and_features_coverage_2026_05_06.md``
    § "Temporary states" — Half 2 of the AVAILABILITY_AT_SEMANTICS defi
    vocabulary gap.
    """
    expected_lifted = {
        "aave_lending_rates": ("defi", "lending_indices"),
        "aave_utilization": ("defi", "lending_indices"),
        "aave_risk_params": ("defi", "risk_params"),
        "eigen_rewards": ("defi", "eigenlayer_rewards"),
        "protocol_rewards": ("defi", "rewards"),
        "flash_loan_availability": ("defi", "flash_loan_events"),
        "aave_rate_impact": ("defi", "lending_indices"),
        # onchain_regime checked separately — has TWO inputs.
    }
    for fg, (asset_group, data_type) in expected_lifted.items():
        assert has_required_inputs(fg), f"{fg} missing from FEATURE_REQUIRED_INPUTS"
        inputs = get_required_inputs(fg)
        assert len(inputs) == 1, f"{fg} expected 1 input, got {len(inputs)}: {inputs}"
        assert inputs[0].asset_group == asset_group, f"{fg} asset_group mismatch"
        assert inputs[0].data_type == data_type, f"{fg} data_type mismatch"
        assert inputs[0].available_at_rule == "tick_timestamp", (
            f"{fg} expected tick_timestamp, got {inputs[0].available_at_rule}"
        )


def test_onchain_regime_has_two_inputs() -> None:
    """``onchain_regime`` is a Phase 2 derived calculator depending on two
    leaf data_types: lending_indices (via aave_*) + dex_pools (via
    defillama_tvl)."""
    inputs = get_required_inputs("onchain_regime")
    assert len(inputs) == 2
    pairs = {(i.asset_group, i.data_type) for i in inputs}
    assert pairs == {("defi", "lending_indices"), ("defi", "dex_pools")}
    assert all(i.available_at_rule == "tick_timestamp" for i in inputs)


def test_macro_sentiment_intentionally_not_seeded() -> None:
    """macro_sentiment does live HTTP fetches from external sentiment APIs
    (CoinGecko) — no registered DeFi raw data_type to enforce
    LookaheadBias against. Intentionally absent from FEATURE_REQUIRED_INPUTS;
    documented in the inline comment + the feature_dag plan's Temporary
    states section.
    """
    assert not has_required_inputs("macro_sentiment")


def test_list_feature_groups_returns_sorted() -> None:
    """``list_feature_groups()`` is deterministic and sorted."""
    groups = list_feature_groups()
    assert groups == sorted(groups)
    assert set(groups) == set(FEATURE_REQUIRED_INPUTS)


def test_list_services_returns_sorted_known() -> None:
    """``list_services()`` matches ``EXPECTED_FEATURE_GROUPS_BY_SERVICE``."""
    services = list_services()
    assert services == sorted(EXPECTED_FEATURE_GROUPS_BY_SERVICE)


def test_is_known_feature_group_round_trip() -> None:
    """is_known_feature_group(service, fg) is True iff fg is registered."""
    assert is_known_feature_group("features-service", "lst_staking_yields") is True
    assert is_known_feature_group("features-service", "definitely-not-real") is False
    assert is_known_feature_group("definitely-not-a-service", "lst_staking_yields") is False


# ---------------------------------------------------------------------------
# FEATURE_COVERAGE_START — sanity checks.
# ---------------------------------------------------------------------------


def test_feature_coverage_start_returns_date_or_none() -> None:
    """get_feature_coverage_start returns a date for registered pairs,
    None otherwise."""
    for (service, feature_group), expected in FEATURE_COVERAGE_START.items():
        assert get_feature_coverage_start(service, feature_group) == expected
    assert get_feature_coverage_start("nonexistent-service", "x") is None


def test_feature_coverage_start_dates_are_reasonable() -> None:
    """All registered floors fall in the 2018-2026 protocol-launch window
    (regression guard against typos like 1970 or 9999)."""
    for (service, feature_group), floor in FEATURE_COVERAGE_START.items():
        assert date(2018, 1, 1) <= floor <= date(2026, 12, 31), (
            f"({service}, {feature_group}) floor {floor} outside 2018-2026 window"
        )


def test_feature_coverage_start_keys_reference_known_feature_groups() -> None:
    """Every (service, feature_group) key in FEATURE_COVERAGE_START
    must be declared in EXPECTED_FEATURE_GROUPS_BY_SERVICE."""
    unknown = [
        (service, feature_group)
        for (service, feature_group) in FEATURE_COVERAGE_START
        if not is_known_feature_group(service, feature_group)
    ]
    assert not unknown, (
        f"FEATURE_COVERAGE_START references (service, feature_group) pairs "
        f"not declared in EXPECTED_FEATURE_GROUPS_BY_SERVICE: {unknown}"
    )


# ---------------------------------------------------------------------------
# InputReq dataclass — frozen + horizon defaults.
# ---------------------------------------------------------------------------


def test_input_req_is_frozen() -> None:
    """InputReq instances are frozen — mutation should raise."""
    req = InputReq(
        asset_group="cefi",
        data_type="ohlcv_1m",
        available_at_rule="tick_timestamp",
    )
    with pytest.raises(FrozenInstanceError):
        req.asset_group = "tradfi"  # type: ignore[misc]


def test_input_req_default_horizon_is_zero() -> None:
    """Default horizon is timedelta(0) — i.e. 'available by target_ts'."""
    req = InputReq(
        asset_group="cefi",
        data_type="ohlcv_1m",
        available_at_rule="tick_timestamp",
    )
    assert req.horizon == timedelta(0)
    assert req.source is None
