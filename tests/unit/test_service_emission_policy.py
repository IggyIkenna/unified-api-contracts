"""Unit tests for the service_emission_policy SSOT.

Covers the Wave 4 schema floor — :class:`ServiceEmissionPolicy`,
:data:`SERVICE_OUTPUT_POLICIES` seed, lifecycle event names, and the
default-fail-loud resolution semantics.

Plan: ``writegate_honest_coverage_endtoend_2026_05_06.plan.md`` § Phase 3.D.5
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
    policy_is_alert,
    policy_is_publish_row,
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
        SERVICE_OUTPUT_POLICIES[("market-data-pipeline-service", "ohlcv_1m:current")]
        is ServiceEmissionPolicy.STRICT_FAIL
    )


def test_seed_contains_mdps_ohlcv_24h_partial_ok() -> None:
    """Operator-msg-10 framing — 24h high/low denominator stable across inner gaps."""
    assert SERVICE_OUTPUT_POLICIES[("market-data-pipeline-service", "ohlcv_24h")] is ServiceEmissionPolicy.PARTIAL_OK


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
    assert get_emission_policy("market-data-pipeline-service", "ohlcv_24h") is ServiceEmissionPolicy.PARTIAL_OK


def test_get_emission_policy_defaults_to_strict_fail() -> None:
    """Unseeded pairs default to STRICT_FAIL — fail-loud, force explicit declaration."""
    assert get_emission_policy("not-a-real-service", "not-a-real-output") is ServiceEmissionPolicy.STRICT_FAIL


def test_get_emission_policy_distinguishes_current_vs_historical_slice() -> None:
    """The ``"<data_type>:<slice>"`` shape lets the same data_type carry different policies."""
    assert get_emission_policy("market-data-pipeline-service", "ohlcv_1m:current") is ServiceEmissionPolicy.STRICT_FAIL
    assert (
        get_emission_policy("market-data-pipeline-service", "ohlcv_1m:historical") is ServiceEmissionPolicy.PARTIAL_OK
    )


# ---------------------------------------------------------------------------
# is_emission_policy_declared
# ---------------------------------------------------------------------------


def test_is_emission_policy_declared_seeded_pair_true() -> None:
    assert is_emission_policy_declared("market-data-pipeline-service", "ohlcv_24h") is True


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
