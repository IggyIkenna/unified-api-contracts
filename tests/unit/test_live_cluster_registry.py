"""Unit tests for the Phase E.1 live-cluster registry SSOT."""

from __future__ import annotations

from unified_api_contracts import LIVE_CLUSTER_REGISTRY as ROOT_REGISTRY
from unified_api_contracts import LiveClusterDeploymentKind as RootDeploymentKind
from unified_api_contracts import LiveClusterSpec as RootSpec
from unified_api_contracts import get_clusters_for_env as root_get_clusters_for_env
from unified_api_contracts.canonical.crosscutting.cloud_target import CloudTarget
from unified_api_contracts.canonical.crosscutting.environment_tier import EnvironmentTier
from unified_api_contracts.canonical.crosscutting.lifecycle_class import LifecycleClass
from unified_api_contracts.canonical.crosscutting.live_cluster_registry import (
    LIVE_CLUSTER_REGISTRY,
    LiveClusterDeploymentKind,
    LiveClusterSpec,
    get_clusters_for_env,
)


def test_registry_non_empty() -> None:
    assert len(LIVE_CLUSTER_REGISTRY) > 0


def test_all_entries_are_live_cluster_spec() -> None:
    for entry in LIVE_CLUSTER_REGISTRY:
        assert isinstance(entry, LiveClusterSpec)


def test_all_lifecycle_class_long_lived_live() -> None:
    for entry in LIVE_CLUSTER_REGISTRY:
        assert entry.lifecycle_class == LifecycleClass.LONG_LIVED_LIVE


def test_names_non_empty_kebab_case() -> None:
    for entry in LIVE_CLUSTER_REGISTRY:
        assert entry.name
        assert entry.name == entry.name.lower()
        assert " " not in entry.name


def test_health_endpoint_starts_with_slash() -> None:
    for entry in LIVE_CLUSTER_REGISTRY:
        assert entry.health_endpoint.startswith("/")


def test_expected_replicas_positive() -> None:
    for entry in LIVE_CLUSTER_REGISTRY:
        assert entry.expected_replicas >= 1


def test_drain_timeout_positive() -> None:
    for entry in LIVE_CLUSTER_REGISTRY:
        assert entry.drain_timeout > 0


def test_registry_has_staging_and_prod_tiers() -> None:
    tiers = {e.environment_tier for e in LIVE_CLUSTER_REGISTRY}
    assert EnvironmentTier.STAGING in tiers
    assert EnvironmentTier.PROD in tiers


def test_registry_no_dev_tier_entries() -> None:
    dev_entries = [e for e in LIVE_CLUSTER_REGISTRY if e.environment_tier == EnvironmentTier.DEV]
    assert dev_entries == [], "Live clusters should not exist in DEV tier (no live credentials)"


def test_get_clusters_for_env_staging_returns_subset() -> None:
    staging = get_clusters_for_env(EnvironmentTier.STAGING)
    assert len(staging) > 0
    for entry in staging:
        assert entry.environment_tier == EnvironmentTier.STAGING


def test_get_clusters_for_env_prod_returns_subset() -> None:
    prod = get_clusters_for_env(EnvironmentTier.PROD)
    assert len(prod) > 0
    for entry in prod:
        assert entry.environment_tier == EnvironmentTier.PROD


def test_get_clusters_for_env_staging_prod_same_count() -> None:
    staging = get_clusters_for_env(EnvironmentTier.STAGING)
    prod = get_clusters_for_env(EnvironmentTier.PROD)
    assert len(staging) == len(prod), "Each cluster should exist in both staging and prod"


def test_get_clusters_for_env_gcp_filter() -> None:
    staging_gcp = get_clusters_for_env(EnvironmentTier.STAGING, cloud_target=CloudTarget.GCP)
    assert all(e.cloud_target == CloudTarget.GCP for e in staging_gcp)


def test_get_clusters_for_env_aws_filter() -> None:
    staging_aws = get_clusters_for_env(EnvironmentTier.STAGING, cloud_target=CloudTarget.AWS)
    assert all(e.cloud_target == CloudTarget.AWS for e in staging_aws)


def test_mtds_entries_exist_for_all_venues() -> None:
    expected_venues = {"binance", "bybit", "okx", "deribit", "hyperliquid", "kraken"}
    staging = get_clusters_for_env(EnvironmentTier.STAGING)
    mtds_names = {e.name for e in staging if e.name.startswith("mtds-live-")}
    for venue in expected_venues:
        assert f"mtds-live-{venue}" in mtds_names, f"mtds-live-{venue} missing from staging registry"


def test_strategy_entries_exist_for_archetypes() -> None:
    staging = get_clusters_for_env(EnvironmentTier.STAGING)
    strategy_names = {e.name for e in staging if e.name.startswith("strategy-live-")}
    assert "strategy-live-carry-staked-basis" in strategy_names
    assert "strategy-live-arb-price-dispersion" in strategy_names


def test_execution_entries_exist_per_cloud() -> None:
    staging = get_clusters_for_env(EnvironmentTier.STAGING)
    exec_names = {e.name for e in staging if e.name.startswith("execution-live-")}
    assert "execution-live-gcp" in exec_names
    assert "execution-live-aws" in exec_names


def test_infra_entries_exist() -> None:
    staging = get_clusters_for_env(EnvironmentTier.STAGING)
    infra_names = {e.name for e in staging if e.asset_group == "infra"}
    assert "position-balance-live" in infra_names
    assert "risk-live" in infra_names
    assert "alerting-live" in infra_names


def test_total_registry_size() -> None:
    # 6 MTDS x 2 tiers + 2 strategy x 2 tiers + 2 execution x 2 tiers + 3 infra x 2 tiers = 26
    assert len(LIVE_CLUSTER_REGISTRY) == 26


def test_deployment_kind_enum_values() -> None:
    assert LiveClusterDeploymentKind.CLOUD_RUN == "CLOUD_RUN"
    assert LiveClusterDeploymentKind.GKE == "GKE"
    assert LiveClusterDeploymentKind.EKS == "EKS"
    assert LiveClusterDeploymentKind.ECS_SERVICE == "ECS_SERVICE"


def test_root_import_surface() -> None:
    assert ROOT_REGISTRY is LIVE_CLUSTER_REGISTRY
    assert RootSpec is LiveClusterSpec
    assert RootDeploymentKind is LiveClusterDeploymentKind
    assert root_get_clusters_for_env is get_clusters_for_env
