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

from unified_api_contracts import (
    UMBRELLA_FOR_LIFECYCLE_CLASS as ROOT_UMBRELLA_FOR_LIFECYCLE_CLASS,
)
from unified_api_contracts import (
    DeploymentTarget as RootDeploymentTarget,
)
from unified_api_contracts import (
    DeploymentUmbrella as RootDeploymentUmbrella,
)
from unified_api_contracts import (
    ShardResponsibility as RootShardResponsibility,
)
from unified_api_contracts import (
    ShardResponsibilityKind as RootShardResponsibilityKind,
)
from unified_api_contracts.canonical.crosscutting.lifecycle_class import (
    UMBRELLA_FOR_LIFECYCLE_CLASS,
    DeploymentCloud,
    DeploymentKind,
    DeploymentTarget,
    DeploymentUmbrella,
    LifecycleClass,
    ShardResponsibility,
    ShardResponsibilityKind,
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


# ---------------------------------------------------------------------------
# Deployment-observability umbrella model
# ---------------------------------------------------------------------------


def test_deployment_umbrella_has_exactly_four_members() -> None:
    """Closed-set 4-umbrella taxonomy; a 5th umbrella must be a deliberate UAC change."""
    assert {member.name for member in DeploymentUmbrella} == {"LIVE", "BATCH", "PAPER", "EXPERIMENT"}


def test_deployment_umbrella_values_equal_names() -> None:
    for member in DeploymentUmbrella:
        assert member.value == member.name


def test_deployment_cloud_members() -> None:
    assert {member.name for member in DeploymentCloud} == {"GCP", "AWS"}


def test_deployment_kind_members() -> None:
    assert {member.name for member in DeploymentKind} == {"VM", "CLOUD_RUN_JOB", "CLOUD_RUN_SERVICE"}


def test_umbrella_for_lifecycle_class_maps_all_four_lifecycle_classes() -> None:
    """Every lifecycle_class resolves to an umbrella (no UNCLASSIFIED gap)."""
    assert set(UMBRELLA_FOR_LIFECYCLE_CLASS) == {member.value for member in LifecycleClass}


def test_umbrella_for_lifecycle_class_mapping() -> None:
    assert UMBRELLA_FOR_LIFECYCLE_CLASS[LifecycleClass.EPHEMERAL_BATCH.value] is DeploymentUmbrella.BATCH
    assert UMBRELLA_FOR_LIFECYCLE_CLASS[LifecycleClass.SCHEDULED_RECURRING.value] is DeploymentUmbrella.BATCH
    assert UMBRELLA_FOR_LIFECYCLE_CLASS[LifecycleClass.LONG_LIVED_LIVE.value] is DeploymentUmbrella.LIVE
    assert UMBRELLA_FOR_LIFECYCLE_CLASS[LifecycleClass.EPHEMERAL_EXPERIMENT.value] is DeploymentUmbrella.EXPERIMENT


def test_umbrella_for_lifecycle_class_has_no_paper_entry() -> None:
    """PAPER has no lifecycle_class — it is always an explicit override."""
    assert DeploymentUmbrella.PAPER not in UMBRELLA_FOR_LIFECYCLE_CLASS.values()


def test_deployment_target_is_frozen() -> None:
    target = DeploymentTarget(
        name="cefi-binance-",
        kind=DeploymentKind.VM,
        umbrella=DeploymentUmbrella.BATCH,
        cloud=DeploymentCloud.GCP,
        service="market-tick-data-service",
        asset_group="cefi",
        lifecycle_class=LifecycleClass.EPHEMERAL_BATCH.value,
    )
    with pytest.raises(FrozenInstanceError):
        target.umbrella = DeploymentUmbrella.LIVE  # type: ignore[misc]  # frozen-dataclass mutation is the assertion


def test_deployment_target_allows_empty_lifecycle_class_for_cloud_run_jobs() -> None:
    """Cloud Run jobs have no VM lifecycle class; "" is the canonical sentinel."""
    target = DeploymentTarget(
        name="cf-manifest-audit",
        kind=DeploymentKind.CLOUD_RUN_JOB,
        umbrella=DeploymentUmbrella.BATCH,
        cloud=DeploymentCloud.GCP,
        service="manifest-audit",
        asset_group="",
        lifecycle_class="",
    )
    assert target.lifecycle_class == ""
    assert target.asset_group == ""


def test_deployment_symbols_exported_from_uac_root() -> None:
    """The root UAC import surface re-exports the umbrella contracts (same objects)."""
    assert RootDeploymentUmbrella is DeploymentUmbrella
    assert RootDeploymentTarget is DeploymentTarget
    assert ROOT_UMBRELLA_FOR_LIFECYCLE_CLASS is UMBRELLA_FOR_LIFECYCLE_CLASS


# ---------------------------------------------------------------------------
# ShardResponsibility — data-freshness binding contract
# ---------------------------------------------------------------------------


class TestShardResponsibilityKind:
    def test_closed_set(self) -> None:
        assert set(ShardResponsibilityKind) == {
            ShardResponsibilityKind.ASSET_GROUP_CAPTURE,
            ShardResponsibilityKind.MANIFEST_CONSOLIDATION,
            ShardResponsibilityKind.STRATEGY_SHARD,
            ShardResponsibilityKind.NONE,
        }

    def test_string_values(self) -> None:
        assert ShardResponsibilityKind.ASSET_GROUP_CAPTURE == "asset_group_capture"
        assert ShardResponsibilityKind.MANIFEST_CONSOLIDATION == "manifest_consolidation"
        assert ShardResponsibilityKind.STRATEGY_SHARD == "strategy_shard"
        assert ShardResponsibilityKind.NONE == "none"


class TestShardResponsibility:
    def test_asset_group_capture(self) -> None:
        r = ShardResponsibility(
            kind=ShardResponsibilityKind.ASSET_GROUP_CAPTURE,
            asset_group="cefi",
            data_types=("book_snapshot_5", "trades"),
        )
        assert r.kind == ShardResponsibilityKind.ASSET_GROUP_CAPTURE
        assert r.asset_group == "cefi"
        assert r.data_types == ("book_snapshot_5", "trades")
        assert r.archetype == ""
        assert r.shard == ""
        assert r.mode == ""

    def test_manifest_consolidation(self) -> None:
        r = ShardResponsibility(
            kind=ShardResponsibilityKind.MANIFEST_CONSOLIDATION,
            asset_group="defi",
        )
        assert r.kind == ShardResponsibilityKind.MANIFEST_CONSOLIDATION
        assert r.asset_group == "defi"
        assert r.data_types == ()

    def test_strategy_shard(self) -> None:
        r = ShardResponsibility(
            kind=ShardResponsibilityKind.STRATEGY_SHARD,
            archetype="carry_staked_basis",
            shard="shard-0",
            mode="live",
        )
        assert r.kind == ShardResponsibilityKind.STRATEGY_SHARD
        assert r.archetype == "carry_staked_basis"
        assert r.shard == "shard-0"
        assert r.mode == "live"
        assert r.asset_group == ""

    def test_none_liveness_only(self) -> None:
        r = ShardResponsibility(kind=ShardResponsibilityKind.NONE)
        assert r.kind == ShardResponsibilityKind.NONE
        assert r.asset_group == ""
        assert r.data_types == ()
        assert r.archetype == ""

    def test_frozen(self) -> None:
        r = ShardResponsibility(
            kind=ShardResponsibilityKind.NONE,
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            r.asset_group = "tradfi"  # type: ignore[misc]

    def test_root_export(self) -> None:
        assert RootShardResponsibility is ShardResponsibility
        assert RootShardResponsibilityKind is ShardResponsibilityKind
