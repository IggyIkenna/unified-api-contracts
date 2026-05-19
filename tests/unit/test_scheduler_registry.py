"""Unit tests for scheduler_registry — Phase D.1 SSOT.

Tests:
  1. Registry is non-empty and all entries are SchedulerSpec.
  2. All names are unique.
  3. All lifecycle_class values are SCHEDULED_RECURRING.
  4. env_tiers and cloud_targets are non-empty frozensets.
  5. Instruments-live entries exclude DEV tier.
  6. Infra entries include DEV tier.
  7. get_schedulers_for_env filters by tier correctly.
  8. get_schedulers_for_env filters by cloud_target correctly.
  9. Phase-1 instruments names are all present.
  10. Phase-1 infra names are all present.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import SCHEDULER_REGISTRY as ROOT_SCHEDULER_REGISTRY
from unified_api_contracts import SchedulerSpec as RootSchedulerSpec
from unified_api_contracts import SchedulerTargetKind as RootSchedulerTargetKind
from unified_api_contracts import get_schedulers_for_env as root_get_schedulers_for_env
from unified_api_contracts.canonical.crosscutting.cloud_target import CloudTarget
from unified_api_contracts.canonical.crosscutting.environment_tier import EnvironmentTier
from unified_api_contracts.canonical.crosscutting.lifecycle_class import LifecycleClass
from unified_api_contracts.canonical.crosscutting.scheduler_registry import (
    SCHEDULER_REGISTRY,
    SchedulerSpec,
    SchedulerTargetKind,
    get_schedulers_for_env,
)

_EXPECTED_INSTRUMENTS_NAMES = frozenset(
    {
        "cefi-ohlcv-15m",
        "tradfi-ohlcv-15m",
        "tradfi-vix-ohlcv-15m",
        "prediction-market-discovery-15m",
        "sports-fixtures-poll",
        "sports-fixture-stats",
        "sports-leagues-teams-season-roll",
        "sports-player-values-transfer-window",
        "sports-weather-prefixture",
        "sports-lineups-injuries",
    }
)

_EXPECTED_INFRA_NAMES = frozenset(
    {
        "manifest-consolidator-60s",
        "data-status-rollup",
        "manifest-aggregation-cron",
        "t1-audit",
    }
)


def test_registry_non_empty() -> None:
    assert len(SCHEDULER_REGISTRY) > 0


def test_all_entries_are_scheduler_spec() -> None:
    for entry in SCHEDULER_REGISTRY:
        assert isinstance(entry, SchedulerSpec)


def test_names_unique() -> None:
    names = [s.name for s in SCHEDULER_REGISTRY]
    assert len(names) == len(set(names)), "Duplicate names in SCHEDULER_REGISTRY"


def test_all_lifecycle_class_scheduled_recurring() -> None:
    for entry in SCHEDULER_REGISTRY:
        assert entry.lifecycle_class == LifecycleClass.SCHEDULED_RECURRING, (
            f"{entry.name} has unexpected lifecycle_class {entry.lifecycle_class}"
        )


def test_env_tiers_non_empty() -> None:
    for entry in SCHEDULER_REGISTRY:
        assert entry.env_tiers, f"{entry.name} has empty env_tiers"


def test_cloud_targets_non_empty() -> None:
    for entry in SCHEDULER_REGISTRY:
        assert entry.cloud_targets, f"{entry.name} has empty cloud_targets"


def test_instruments_entries_exclude_dev() -> None:
    instruments_entries = [s for s in SCHEDULER_REGISTRY if s.name in _EXPECTED_INSTRUMENTS_NAMES]
    for entry in instruments_entries:
        assert EnvironmentTier.DEV not in entry.env_tiers, (
            f"Instruments-live entry {entry.name!r} unexpectedly includes DEV tier"
        )


def test_infra_entries_include_all_tiers() -> None:
    infra_entries = [s for s in SCHEDULER_REGISTRY if s.name in _EXPECTED_INFRA_NAMES]
    for entry in infra_entries:
        for tier in EnvironmentTier:
            assert tier in entry.env_tiers, f"Infra entry {entry.name!r} missing tier {tier}"


def test_get_schedulers_for_env_staging_excludes_dev_only() -> None:
    staging = get_schedulers_for_env(EnvironmentTier.STAGING)
    dev_only = [s for s in SCHEDULER_REGISTRY if s.env_tiers == frozenset({EnvironmentTier.DEV})]
    for entry in dev_only:
        assert entry not in staging


def test_get_schedulers_for_env_dev_returns_infra_only() -> None:
    dev = get_schedulers_for_env(EnvironmentTier.DEV)
    dev_names = {s.name for s in dev}
    assert dev_names == _EXPECTED_INFRA_NAMES


def test_get_schedulers_for_env_prod_includes_instruments() -> None:
    prod = get_schedulers_for_env(EnvironmentTier.PROD)
    prod_names = {s.name for s in prod}
    assert _EXPECTED_INSTRUMENTS_NAMES.issubset(prod_names)


def test_get_schedulers_for_env_cloud_target_filter() -> None:
    gcp_only = get_schedulers_for_env(EnvironmentTier.PROD, cloud_target=CloudTarget.GCP)
    aws_only = get_schedulers_for_env(EnvironmentTier.PROD, cloud_target=CloudTarget.AWS)
    all_prod = get_schedulers_for_env(EnvironmentTier.PROD)
    assert set(gcp_only) | set(aws_only) == set(all_prod)


def test_phase1_instruments_names_present() -> None:
    registry_names = {s.name for s in SCHEDULER_REGISTRY}
    missing = _EXPECTED_INSTRUMENTS_NAMES - registry_names
    assert not missing, f"Phase-1 instruments names missing from registry: {missing}"


def test_phase1_infra_names_present() -> None:
    registry_names = {s.name for s in SCHEDULER_REGISTRY}
    missing = _EXPECTED_INFRA_NAMES - registry_names
    assert not missing, f"Phase-1 infra names missing from registry: {missing}"


def test_scheduler_target_kind_values() -> None:
    valid = {SchedulerTargetKind.CLOUD_RUN, SchedulerTargetKind.GCE_VM_LAUNCHER, SchedulerTargetKind.EVENTBRIDGE}
    for entry in SCHEDULER_REGISTRY:
        assert entry.target_kind in valid


def test_root_import_surface() -> None:
    assert ROOT_SCHEDULER_REGISTRY is SCHEDULER_REGISTRY
    assert RootSchedulerSpec is SchedulerSpec
    assert RootSchedulerTargetKind is SchedulerTargetKind
    assert root_get_schedulers_for_env is get_schedulers_for_env


@pytest.mark.parametrize(
    "name,expected_asset_group",
    [
        ("cefi-ohlcv-15m", "cefi"),
        ("tradfi-ohlcv-15m", "tradfi"),
        ("tradfi-vix-ohlcv-15m", "tradfi"),
        ("prediction-market-discovery-15m", "prediction"),
        ("sports-fixtures-poll", "sports"),
        ("manifest-consolidator-60s", "infra"),
        ("data-status-rollup", "infra"),
        ("manifest-aggregation-cron", "infra"),
        ("t1-audit", "infra"),
    ],
)
def test_asset_groups(name: str, expected_asset_group: str) -> None:
    entry = next((s for s in SCHEDULER_REGISTRY if s.name == name), None)
    assert entry is not None, f"Entry {name!r} not found in registry"
    assert entry.asset_group == expected_asset_group
