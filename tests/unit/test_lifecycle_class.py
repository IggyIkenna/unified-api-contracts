"""Unit tests for the LifecycleClass taxonomy + classifiers.

Phase A.1 of the ``deployment_ui_lifecycle_tabs_2026_05_08`` plan — the
SSOT for the closed-set 4-class lifecycle taxonomy. Every later phase
(B-H) and every consumer (deployment-api routes, deployment-ui Monitor
sub-tabs, vm_zombie_watchdog) reads from this module, so the contract
is exercised here directly.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from unified_api_contracts.canonical.crosscutting.lifecycle_class import (
    LifecycleClass,
    VmPrefixSpec,
    classify_cloud_run_service,
    classify_experiment_run,
    classify_scheduled_job,
    classify_vm_name,
)

# ---------------------------------------------------------------------------
# LifecycleClass enum — closed-set 4-member taxonomy
# ---------------------------------------------------------------------------


def test_lifecycle_class_has_exactly_four_members() -> None:
    """The taxonomy is a closed set; adding a 5th member must be a deliberate UAC change."""
    assert {member.name for member in LifecycleClass} == {
        "EPHEMERAL_BATCH",
        "EPHEMERAL_EXPERIMENT",
        "SCHEDULED_RECURRING",
        "LONG_LIVED_LIVE",
    }


def test_lifecycle_class_is_str_enum() -> None:
    """StrEnum so values serialise straight to JSON / parquet without enum-to-str gymnastics."""
    assert LifecycleClass.EPHEMERAL_BATCH == "EPHEMERAL_BATCH"
    assert LifecycleClass.LONG_LIVED_LIVE == "LONG_LIVED_LIVE"


def test_lifecycle_class_value_matches_name() -> None:
    """Canonical UAC StrEnum convention — value equals name."""
    for member in LifecycleClass:
        assert member.value == member.name


# ---------------------------------------------------------------------------
# VmPrefixSpec — frozen dataclass
# ---------------------------------------------------------------------------


def test_vm_prefix_spec_frozen() -> None:
    spec = VmPrefixSpec(bucket="market-data-tick-cefi", lifecycle_class=LifecycleClass.EPHEMERAL_BATCH)
    with pytest.raises(FrozenInstanceError):
        spec.bucket = "other-bucket"  # type: ignore[misc]


def test_vm_prefix_spec_equality_and_roundtrip() -> None:
    a = VmPrefixSpec(bucket="market-data-tick-cefi", lifecycle_class=LifecycleClass.EPHEMERAL_BATCH)
    b = VmPrefixSpec(bucket="market-data-tick-cefi", lifecycle_class=LifecycleClass.EPHEMERAL_BATCH)
    assert a == b


def test_vm_prefix_spec_allows_none_bucket() -> None:
    """Heartbeat-only VMs (watchdog, consolidator) carry ``bucket=None``."""
    spec = VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.SCHEDULED_RECURRING)
    assert spec.bucket is None
    assert spec.lifecycle_class is LifecycleClass.SCHEDULED_RECURRING


# ---------------------------------------------------------------------------
# classify_vm_name — longest-prefix match
# ---------------------------------------------------------------------------


def _sample_registry() -> dict[str, VmPrefixSpec]:
    return {
        "cefi-bitfinex-": VmPrefixSpec(bucket="market-data-tick-cefi", lifecycle_class=LifecycleClass.EPHEMERAL_BATCH),
        "live-strategy-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.LONG_LIVED_LIVE),
        "manifest-consolidator-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.SCHEDULED_RECURRING),
        "exp-ml-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.EPHEMERAL_EXPERIMENT),
    }


def test_classify_vm_name_happy_path_cefi_backfill() -> None:
    registry = _sample_registry()
    result = classify_vm_name("cefi-bitfinex-spot-2023-heavy-20260504-194158", registry)
    assert result is LifecycleClass.EPHEMERAL_BATCH


def test_classify_vm_name_happy_path_live_strategy() -> None:
    registry = _sample_registry()
    result = classify_vm_name("live-strategy-carry-staked-basis-20260508-100000", registry)
    assert result is LifecycleClass.LONG_LIVED_LIVE


def test_classify_vm_name_happy_path_scheduled_consolidator() -> None:
    registry = _sample_registry()
    result = classify_vm_name("manifest-consolidator-20260508-090000", registry)
    assert result is LifecycleClass.SCHEDULED_RECURRING


def test_classify_vm_name_happy_path_experiment() -> None:
    registry = _sample_registry()
    result = classify_vm_name("exp-ml-018f3a4b-c5d6-7e89-abcd-ef0123456789-20260508", registry)
    assert result is LifecycleClass.EPHEMERAL_EXPERIMENT


def test_classify_vm_name_raises_on_unmatched() -> None:
    registry = _sample_registry()
    with pytest.raises(ValueError, match="rogue-vm-foo"):
        classify_vm_name("rogue-vm-foo-20260508-100000", registry)


def test_classify_vm_name_longest_prefix_wins() -> None:
    """When both ``live-`` and ``live-strategy-`` are registered, the more specific entry wins."""
    registry: dict[str, VmPrefixSpec] = {
        "live-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.SCHEDULED_RECURRING),
        "live-strategy-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.LONG_LIVED_LIVE),
    }
    result = classify_vm_name("live-strategy-foo-20260508-100000", registry)
    assert result is LifecycleClass.LONG_LIVED_LIVE


def test_classify_vm_name_longest_prefix_falls_back_to_generic() -> None:
    """A name that matches only the generic prefix gets the generic entry's class."""
    registry: dict[str, VmPrefixSpec] = {
        "live-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.SCHEDULED_RECURRING),
        "live-strategy-": VmPrefixSpec(bucket=None, lifecycle_class=LifecycleClass.LONG_LIVED_LIVE),
    }
    result = classify_vm_name("live-mtds-bybit-20260508-100000", registry)
    assert result is LifecycleClass.SCHEDULED_RECURRING


# ---------------------------------------------------------------------------
# classify_cloud_run_service — pattern dispatch
# ---------------------------------------------------------------------------


def test_classify_cloud_run_service_live_prefix() -> None:
    assert classify_cloud_run_service("live-strategy-foo") is LifecycleClass.LONG_LIVED_LIVE


def test_classify_cloud_run_service_api_suffix() -> None:
    assert classify_cloud_run_service("deployment-api") is LifecycleClass.LONG_LIVED_LIVE


def test_classify_cloud_run_service_ui_suffix() -> None:
    assert classify_cloud_run_service("deployment-ui") is LifecycleClass.LONG_LIVED_LIVE


def test_classify_cloud_run_service_raises_on_unmatched() -> None:
    with pytest.raises(ValueError, match="some-batch-job"):
        classify_cloud_run_service("some-batch-job")


# ---------------------------------------------------------------------------
# classify_scheduled_job + classify_experiment_run — typed contracts
# ---------------------------------------------------------------------------


def test_classify_scheduled_job_returns_scheduled_recurring_for_any_name() -> None:
    assert classify_scheduled_job("manifest-consolidator-60s") is LifecycleClass.SCHEDULED_RECURRING
    assert classify_scheduled_job("live-instruments-trigger-bybit") is LifecycleClass.SCHEDULED_RECURRING
    assert classify_scheduled_job("data-status-rollup") is LifecycleClass.SCHEDULED_RECURRING


def test_classify_experiment_run_returns_ephemeral_experiment_for_any_run_id() -> None:
    assert classify_experiment_run("018f3a4b-c5d6-7e89-abcd-ef0123456789") is LifecycleClass.EPHEMERAL_EXPERIMENT
    assert classify_experiment_run("exp-strategy-carry-basis-20260508") is LifecycleClass.EPHEMERAL_EXPERIMENT
