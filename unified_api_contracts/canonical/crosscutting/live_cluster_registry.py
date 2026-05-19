"""Live-cluster registry SSOT — Phase E.1 of deployment_ui_lifecycle_tabs_2026_05_08.md.

Declares every long-lived live deployment per ``(cloud_target, environment_tier)``
cell. The deployment-api Monitor -> Live sub-tab reads this registry; lifecycle
action endpoints (start / stop / pause / restart / drain) scope to entries here.

Governance rule
---------------
Adding a new live cluster in ANY plan == adding a row here first.
No ad-hoc ``gcloud run services`` or ``kubectl`` scale operations outside
this registry's declared set.

Phase 1 entries (May-23 scope — live + staging tiers only):

  CeFi live-MTDS (market-tick-data-service per venue):
    mtds-live-binance, mtds-live-bybit, mtds-live-okx,
    mtds-live-deribit, mtds-live-hyperliquid, mtds-live-kraken

  Strategy (carry_staked_basis + arbitrage_price_dispersion):
    strategy-live-carry-staked-basis, strategy-live-arb-price-dispersion

  Execution (one Cloud Run per cloud):
    execution-live-gcp (GCP), execution-live-aws (AWS)

  Position/Risk/Alerting:
    position-balance-live, risk-live, alerting-live

SSOT: ``deployment_ui_lifecycle_tabs_2026_05_08.md`` Phase E.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from unified_api_contracts.canonical.crosscutting.cloud_target import CloudTarget
from unified_api_contracts.canonical.crosscutting.environment_tier import EnvironmentTier
from unified_api_contracts.canonical.crosscutting.lifecycle_class import LifecycleClass


class LiveClusterDeploymentKind(StrEnum):
    """How the live cluster is deployed in the cloud."""

    CLOUD_RUN = "CLOUD_RUN"
    """Google Cloud Run managed service (stateless; scale-to-N)."""

    GKE = "GKE"
    """Google Kubernetes Engine deployment."""

    EKS = "EKS"
    """Amazon Elastic Kubernetes Service deployment."""

    ECS_SERVICE = "ECS_SERVICE"
    """Amazon ECS service with Fargate or EC2 launch type."""


@dataclass(frozen=True)
class LiveClusterSpec:
    """Single live-cluster entry in the workspace registry.

    Attributes:
        name: Unique cluster name (kebab-case). Used as the Cloud Run service
            name, GKE deployment name, or ECS service name.
        lifecycle_class: Always ``LifecycleClass.LONG_LIVED_LIVE``; kept
            explicit so display code can assert class uniformly.
        cloud_target: Cloud where this entry runs (GCP or AWS). Entries
            are per-cloud, not multi-cloud; use two rows for dual-cloud.
        environment_tier: Which tier this entry belongs to (DEV, STAGING,
            or PROD). Entries are per-tier, not multi-tier; use two rows
            for staging + prod.
        deployment_kind: How this cluster is deployed.
        target_ref: Cloud Run service name (CLOUD_RUN), GKE deployment name
            (GKE), EKS deployment name (EKS), or ECS service name (ECS_SERVICE).
        asset_group: Canonical lowercase asset-group key: ``cefi`` / ``defi``
            / ``tradfi`` / ``sports`` / ``prediction`` / ``infra``.
        archetype_owners: Strategy archetypes this cluster serves. Empty for
            infra clusters.
        health_endpoint: HTTP path for health/readiness check. Relative to
            service root (e.g. ``/health``).
        expected_replicas: Desired replica count when running normally. Used
            to flag scale-to-0 as a stopped state.
        drain_timeout: Seconds to wait for in-flight requests before forceful
            stop. Passed as Cloud Run --timeout or k8s terminationGracePeriod.
        owning_plan: Plan filename (slug only, no path) that declared this
            cluster.
    """

    name: str
    lifecycle_class: LifecycleClass
    cloud_target: CloudTarget
    environment_tier: EnvironmentTier
    deployment_kind: LiveClusterDeploymentKind
    target_ref: str
    asset_group: str
    archetype_owners: tuple[str, ...]
    health_endpoint: str
    expected_replicas: int
    drain_timeout: int
    owning_plan: str = field(default="deployment_ui_lifecycle_tabs_2026_05_08")


_DEPLOYMENT_UI_PLAN = "deployment_ui_lifecycle_tabs_2026_05_08"
_INSTRUMENTS_LIVE_PLAN = "instruments_live_master_2026_05_08"

_MTDS_VENUES: tuple[str, ...] = (
    "binance",
    "bybit",
    "okx",
    "deribit",
    "hyperliquid",
    "kraken",
)

_STRATEGY_ARCHETYPES: tuple[tuple[str, str], ...] = (
    ("carry-staked-basis", "carry_staked_basis"),
    ("arb-price-dispersion", "arbitrage_price_dispersion"),
)


def _mtds_entries() -> list[LiveClusterSpec]:
    entries: list[LiveClusterSpec] = []
    for venue in _MTDS_VENUES:
        for tier in (EnvironmentTier.STAGING, EnvironmentTier.PROD):
            entries.append(
                LiveClusterSpec(
                    name=f"mtds-live-{venue}",
                    lifecycle_class=LifecycleClass.LONG_LIVED_LIVE,
                    cloud_target=CloudTarget.GCP,
                    environment_tier=tier,
                    deployment_kind=LiveClusterDeploymentKind.CLOUD_RUN,
                    target_ref=f"mtds-live-{venue}",
                    asset_group="cefi",
                    archetype_owners=("carry_staked_basis", "arbitrage_price_dispersion"),
                    health_endpoint="/health",
                    expected_replicas=1,
                    drain_timeout=60,
                    owning_plan=_INSTRUMENTS_LIVE_PLAN,
                )
            )
    return entries


def _strategy_entries() -> list[LiveClusterSpec]:
    entries: list[LiveClusterSpec] = []
    for slug, archetype in _STRATEGY_ARCHETYPES:
        for tier in (EnvironmentTier.STAGING, EnvironmentTier.PROD):
            entries.append(
                LiveClusterSpec(
                    name=f"strategy-live-{slug}",
                    lifecycle_class=LifecycleClass.LONG_LIVED_LIVE,
                    cloud_target=CloudTarget.GCP,
                    environment_tier=tier,
                    deployment_kind=LiveClusterDeploymentKind.CLOUD_RUN,
                    target_ref=f"strategy-live-{slug}",
                    asset_group="defi",
                    archetype_owners=(archetype,),
                    health_endpoint="/health",
                    expected_replicas=1,
                    drain_timeout=300,
                    owning_plan=_DEPLOYMENT_UI_PLAN,
                )
            )
    return entries


def _execution_entries() -> list[LiveClusterSpec]:
    entries: list[LiveClusterSpec] = []
    for cloud, suffix, kind in (
        (CloudTarget.GCP, "gcp", LiveClusterDeploymentKind.CLOUD_RUN),
        (CloudTarget.AWS, "aws", LiveClusterDeploymentKind.ECS_SERVICE),
    ):
        for tier in (EnvironmentTier.STAGING, EnvironmentTier.PROD):
            entries.append(
                LiveClusterSpec(
                    name=f"execution-live-{suffix}",
                    lifecycle_class=LifecycleClass.LONG_LIVED_LIVE,
                    cloud_target=cloud,
                    environment_tier=tier,
                    deployment_kind=kind,
                    target_ref=f"execution-live-{suffix}",
                    asset_group="defi",
                    archetype_owners=("carry_staked_basis", "arbitrage_price_dispersion"),
                    health_endpoint="/health",
                    expected_replicas=1,
                    drain_timeout=120,
                    owning_plan=_DEPLOYMENT_UI_PLAN,
                )
            )
    return entries


def _infra_entries() -> list[LiveClusterSpec]:
    entries: list[LiveClusterSpec] = []
    for service_slug, service_ref, drain in (
        ("position-balance-live", "position-balance-live", 60),
        ("risk-live", "risk-live", 60),
        ("alerting-live", "alerting-live", 30),
    ):
        for tier in (EnvironmentTier.STAGING, EnvironmentTier.PROD):
            entries.append(
                LiveClusterSpec(
                    name=service_slug,
                    lifecycle_class=LifecycleClass.LONG_LIVED_LIVE,
                    cloud_target=CloudTarget.GCP,
                    environment_tier=tier,
                    deployment_kind=LiveClusterDeploymentKind.CLOUD_RUN,
                    target_ref=service_ref,
                    asset_group="infra",
                    archetype_owners=(),
                    health_endpoint="/health",
                    expected_replicas=1,
                    drain_timeout=drain,
                    owning_plan=_DEPLOYMENT_UI_PLAN,
                )
            )
    return entries


LIVE_CLUSTER_REGISTRY: tuple[LiveClusterSpec, ...] = tuple(
    _mtds_entries() + _strategy_entries() + _execution_entries() + _infra_entries()
)


def get_clusters_for_env(
    env_tier: EnvironmentTier,
    cloud_target: CloudTarget | None = None,
) -> list[LiveClusterSpec]:
    """Return live clusters declared for a given environment tier.

    Args:
        env_tier: The environment tier to filter for.
        cloud_target: If provided, further filter to entries expected on this
            cloud. If ``None``, returns all entries for the tier regardless of
            cloud target.

    Returns:
        Ordered list of :class:`LiveClusterSpec` matching the filter. Preserves
        registry declaration order.
    """
    results = [c for c in LIVE_CLUSTER_REGISTRY if c.environment_tier == env_tier]
    if cloud_target is not None:
        results = [c for c in results if c.cloud_target == cloud_target]
    return results
