"""Unit tests for the service_emission_policy SSOT.

Covers the Wave 4 schema floor — :class:`ServiceEmissionPolicy`,
:data:`SERVICE_OUTPUT_POLICIES` seed, lifecycle event names, and the
default-fail-loud resolution semantics.

Plan: ``writegate_honest_coverage_endtoend_2026_05_06.plan`` § Phase 3.D.5
Wave 4 (slice a — schema floor only; per-service rollout deferred).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.service_emission_policy import (
    EMISSION_LIFECYCLE_EVENTS,
    SERVICE_OUTPUT_POLICIES,
    EmissionLifecycleEvent,
    ServiceEmissionPolicy,
    get_emission_policy,
    is_emission_policy_declared,
    next_state,
    policy_is_alert,
    policy_is_publish_row,
)
from unified_api_contracts.canonical.crosscutting.service_emission_state import (
    ServiceEmissionStateEnum,
)

# ---------------------------------------------------------------------------
# ServiceEmissionPolicy enum
# ---------------------------------------------------------------------------


def test_policy_enum_has_four_members() -> None:
    assert {m.value for m in ServiceEmissionPolicy} == {
        "strict_fail",
        "partial_ok",
        "nan_fill",
        "block_critical",
    }


def test_policy_enum_is_str() -> None:
    """Members must be string-valued so they serialise without enum-to-str gymnastics."""
    assert ServiceEmissionPolicy.STRICT_FAIL == "strict_fail"
    assert ServiceEmissionPolicy.PARTIAL_OK == "partial_ok"


# ---------------------------------------------------------------------------
# EmissionLifecycleEvent + EMISSION_LIFECYCLE_EVENTS
# ---------------------------------------------------------------------------


def test_lifecycle_events_has_four_members() -> None:
    assert {m.value for m in EmissionLifecycleEvent} == {
        "PUBLISHED_OK",
        "PUBLISHED_DEGRADED",
        "STALE_DATA",
        "BLOCKED",
    }


def test_lifecycle_events_frozenset_matches_enum() -> None:
    assert frozenset(m.value for m in EmissionLifecycleEvent) == EMISSION_LIFECYCLE_EVENTS


def test_lifecycle_events_frozenset_is_immutable() -> None:
    assert isinstance(EMISSION_LIFECYCLE_EVENTS, frozenset)


# ---------------------------------------------------------------------------
# SERVICE_OUTPUT_POLICIES seed
# ---------------------------------------------------------------------------


def test_seed_contains_mdps_ohlcv_current_strict_fail() -> None:
    """Operator-msg-10 framing — current 1m bar is real-time; partial = wrong."""
    assert (
        SERVICE_OUTPUT_POLICIES[("market-data-processing-service", "ohlcv_1m:current")]
        is ServiceEmissionPolicy.STRICT_FAIL
    )


def test_seed_contains_mdps_ohlcv_24h_partial_ok() -> None:
    """Operator-msg-10 framing — 24h high/low denominator stable across inner gaps."""
    assert SERVICE_OUTPUT_POLICIES[("market-data-processing-service", "ohlcv_24h")] is ServiceEmissionPolicy.PARTIAL_OK


def test_seed_contains_features_volatility_high_low_partial_ok() -> None:
    """Operator-flagged example: 24h high/low publishes with completeness_fraction."""
    assert SERVICE_OUTPUT_POLICIES[("features-volatility-service", "high_low_24h")] is ServiceEmissionPolicy.PARTIAL_OK


def test_seed_contains_features_volatility_vol_30d_nan_fill() -> None:
    """ML downstream NaN-fills natively — rolling vol gets NaN_FILL not STRICT_FAIL."""
    assert SERVICE_OUTPUT_POLICIES[("features-volatility-service", "vol_30d")] is ServiceEmissionPolicy.NAN_FILL


def test_seed_contains_features_cross_instrument_paired_spec_strict_fail() -> None:
    """Two-leg pair must have both legs current; partial = leak risk."""
    assert (
        SERVICE_OUTPUT_POLICIES[("features-cross-instrument-service", "paired_spec")]
        is ServiceEmissionPolicy.STRICT_FAIL
    )


def test_seed_contains_ml_training_model_version_block_critical() -> None:
    """Training a model on incomplete data is silent corruption — operator review forced."""
    assert SERVICE_OUTPUT_POLICIES[("ml-training-service", "model_version")] is ServiceEmissionPolicy.BLOCK_CRITICAL


def test_seed_contains_strategy_per_archetype_signal_strict_fail() -> None:
    """Strategy signal off stale features = wrong order."""
    assert SERVICE_OUTPUT_POLICIES[("strategy-service", "per_archetype_signal")] is ServiceEmissionPolicy.STRICT_FAIL


def test_seed_contains_execution_fill_confirmation_block_critical() -> None:
    """Position-state truth — partial intolerable."""
    assert SERVICE_OUTPUT_POLICIES[("execution-service", "fill_confirmation")] is ServiceEmissionPolicy.BLOCK_CRITICAL


def test_seed_contains_position_balance_monitor_portfolio_state_block_critical() -> None:
    assert (
        SERVICE_OUTPUT_POLICIES[("position-balance-monitor-service", "portfolio_state")]
        is ServiceEmissionPolicy.BLOCK_CRITICAL
    )


def test_seed_contains_instruments_catalog_snapshot_partial_ok() -> None:
    """Catalog snapshot is best-effort union of multiple sources; partial publish is normal."""
    assert SERVICE_OUTPUT_POLICIES[("instruments-service", "catalog_snapshot")] is ServiceEmissionPolicy.PARTIAL_OK


def test_all_seed_values_are_valid_policies() -> None:
    """No stray strings — every value must be a real :class:`ServiceEmissionPolicy`."""
    for policy in SERVICE_OUTPUT_POLICIES.values():
        assert isinstance(policy, ServiceEmissionPolicy)


def test_all_seed_keys_are_two_tuples_of_strings() -> None:
    """Key shape is ``(service, output_data_type)`` — both strings."""
    for key in SERVICE_OUTPUT_POLICIES:
        assert isinstance(key, tuple)
        assert len(key) == 2
        assert isinstance(key[0], str)
        assert isinstance(key[1], str)


# ---------------------------------------------------------------------------
# get_emission_policy resolution
# ---------------------------------------------------------------------------


def test_get_emission_policy_returns_seeded_value() -> None:
    assert get_emission_policy("market-data-processing-service", "ohlcv_24h") is ServiceEmissionPolicy.PARTIAL_OK


def test_get_emission_policy_defaults_to_strict_fail() -> None:
    """Unseeded pairs default to STRICT_FAIL — fail-loud, force explicit declaration."""
    assert get_emission_policy("not-a-real-service", "not-a-real-output") is ServiceEmissionPolicy.STRICT_FAIL


def test_get_emission_policy_distinguishes_current_vs_historical_slice() -> None:
    """The ``"<data_type>:<slice>"`` shape lets the same data_type carry different policies."""
    assert (
        get_emission_policy("market-data-processing-service", "ohlcv_1m:current") is ServiceEmissionPolicy.STRICT_FAIL
    )
    assert (
        get_emission_policy("market-data-processing-service", "ohlcv_1m:historical") is ServiceEmissionPolicy.PARTIAL_OK
    )


# ---------------------------------------------------------------------------
# is_emission_policy_declared
# ---------------------------------------------------------------------------


def test_is_emission_policy_declared_seeded_pair_true() -> None:
    assert is_emission_policy_declared("market-data-processing-service", "ohlcv_24h") is True


def test_is_emission_policy_declared_unseeded_pair_false() -> None:
    """Unseeded pair returns False even though :func:`get_emission_policy` returns STRICT_FAIL."""
    assert is_emission_policy_declared("not-a-real-service", "not-a-real-output") is False


# ---------------------------------------------------------------------------
# policy_is_publish_row branching helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (ServiceEmissionPolicy.PARTIAL_OK, True),
        (ServiceEmissionPolicy.NAN_FILL, True),
        (ServiceEmissionPolicy.STRICT_FAIL, False),
        (ServiceEmissionPolicy.BLOCK_CRITICAL, False),
    ],
)
def test_policy_is_publish_row(policy: ServiceEmissionPolicy, expected: bool) -> None:
    assert policy_is_publish_row(policy) is expected


# ---------------------------------------------------------------------------
# policy_is_alert branching helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (ServiceEmissionPolicy.BLOCK_CRITICAL, True),
        (ServiceEmissionPolicy.STRICT_FAIL, False),
        (ServiceEmissionPolicy.PARTIAL_OK, False),
        (ServiceEmissionPolicy.NAN_FILL, False),
    ],
)
def test_policy_is_alert(policy: ServiceEmissionPolicy, expected: bool) -> None:
    assert policy_is_alert(policy) is expected


# ---------------------------------------------------------------------------
# next_state resolver (Phase 1.B of manifest_schema_final_gate plan)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("event", "expected_state"),
    [
        (EmissionLifecycleEvent.PUBLISHED_OK, ServiceEmissionStateEnum.PUBLISHED_OK),
        (EmissionLifecycleEvent.PUBLISHED_DEGRADED, ServiceEmissionStateEnum.PUBLISHED_DEGRADED),
        (EmissionLifecycleEvent.STALE_DATA, ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY),
        (EmissionLifecycleEvent.BLOCKED, ServiceEmissionStateEnum.BLOCKED),
    ],
)
def test_next_state_maps_every_event(
    event: EmissionLifecycleEvent,
    expected_state: ServiceEmissionStateEnum,
) -> None:
    """Every :class:`EmissionLifecycleEvent` resolves to a manifest state under all policies."""
    for policy in ServiceEmissionPolicy:
        assert next_state(policy=policy, event=event) is expected_state, (
            f"policy={policy} event={event} should resolve to {expected_state}"
        )


def test_next_state_strict_fail_full_window_publishes_ok() -> None:
    """``STRICT_FAIL`` + ``completeness == 1.0`` → ``PUBLISHED_OK`` event → ``PUBLISHED_OK`` state."""
    state = next_state(
        policy=ServiceEmissionPolicy.STRICT_FAIL,
        event=EmissionLifecycleEvent.PUBLISHED_OK,
    )
    assert state is ServiceEmissionStateEnum.PUBLISHED_OK


def test_next_state_strict_fail_with_gap_stales() -> None:
    """Per ``publish_with_policy``: ``STRICT_FAIL`` + gap → ``STALE_DATA`` event → STALE_DATA_HEARTBEAT_ONLY state."""
    state = next_state(
        policy=ServiceEmissionPolicy.STRICT_FAIL,
        event=EmissionLifecycleEvent.STALE_DATA,
    )
    assert state is ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY


def test_next_state_block_critical_with_gap_blocks() -> None:
    """Per ``publish_with_policy``: ``BLOCK_CRITICAL`` + gap → ``BLOCKED`` event → BLOCKED state."""
    state = next_state(
        policy=ServiceEmissionPolicy.BLOCK_CRITICAL,
        event=EmissionLifecycleEvent.BLOCKED,
    )
    assert state is ServiceEmissionStateEnum.BLOCKED


def test_next_state_partial_ok_with_gap_publishes_degraded() -> None:
    """Per ``publish_with_policy``: ``PARTIAL_OK`` + gap → ``PUBLISHED_DEGRADED`` event → PUBLISHED_DEGRADED state."""
    state = next_state(
        policy=ServiceEmissionPolicy.PARTIAL_OK,
        event=EmissionLifecycleEvent.PUBLISHED_DEGRADED,
    )
    assert state is ServiceEmissionStateEnum.PUBLISHED_DEGRADED


def test_next_state_nan_fill_with_gap_publishes_degraded() -> None:
    """Per ``publish_with_policy``: ``NAN_FILL`` + gap → ``PUBLISHED_DEGRADED`` event → PUBLISHED_DEGRADED state."""
    state = next_state(
        policy=ServiceEmissionPolicy.NAN_FILL,
        event=EmissionLifecycleEvent.PUBLISHED_DEGRADED,
    )
    assert state is ServiceEmissionStateEnum.PUBLISHED_DEGRADED


def test_next_state_kwargs_only() -> None:
    """Signature is keyword-only — protects against positional-arg drift."""
    with pytest.raises(TypeError):
        next_state(ServiceEmissionPolicy.STRICT_FAIL, EmissionLifecycleEvent.PUBLISHED_OK)  # pyright: ignore[reportCallIssue]


def test_next_state_returns_strenum_value() -> None:
    """Result is a :class:`ServiceEmissionStateEnum` member, not a bare string.

    Writers can then use ``.value`` to serialise; type checkers see the enum
    on the boundary.
    """
    state = next_state(
        policy=ServiceEmissionPolicy.STRICT_FAIL,
        event=EmissionLifecycleEvent.PUBLISHED_OK,
    )
    assert isinstance(state, ServiceEmissionStateEnum)
    assert state.value == "PUBLISHED_OK"


def test_next_state_pure_function() -> None:
    """No mutation, no I/O — deterministic across repeated invocations."""
    for _ in range(3):
        assert (
            next_state(
                policy=ServiceEmissionPolicy.BLOCK_CRITICAL,
                event=EmissionLifecycleEvent.BLOCKED,
            )
            is ServiceEmissionStateEnum.BLOCKED
        )
