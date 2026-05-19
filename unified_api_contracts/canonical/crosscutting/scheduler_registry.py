"""Scheduler registry SSOT — Phase D.1 of deployment_ui_lifecycle_tabs_2026_05_08.md.

Declares every Cloud Scheduler / EventBridge / VM-cron job that should exist
per (cloud_target, environment_tier) cell. The deployment-api
``POST /api/monitor/scheduled/deploy-missing`` reads this registry filtered by
the current tier; the Monitor → Scheduled sub-tab derives "expected but missing"
state from it.

Governance rule
---------------
Adding a new scheduler in ANY plan == adding a row here first.
No ad-hoc ``gcloud scheduler jobs create`` outside this registry.

Phase 1 entries (instruments_live_master_2026_05_08 Phase A.3 topology +
infra schedulers declared in deployment_ui_lifecycle_tabs_2026_05_08 Phase D.1):

  Instruments-live:
    cefi-ohlcv-15m, tradfi-ohlcv-15m, tradfi-vix-ohlcv-15m,
    prediction-market-discovery-15m,
    sports-fixtures-poll, sports-fixture-stats, sports-leagues-teams-season-roll,
    sports-player-values-transfer-window, sports-weather-prefixture,
    sports-lineups-injuries

  Infra:
    manifest-consolidator-60s, data-status-rollup,
    manifest-aggregation-cron, t1-audit

SSOT: ``deployment_ui_lifecycle_tabs_2026_05_08.md`` Phase D.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from unified_api_contracts.canonical.crosscutting.cloud_target import CloudTarget
from unified_api_contracts.canonical.crosscutting.environment_tier import EnvironmentTier
from unified_api_contracts.canonical.crosscutting.lifecycle_class import LifecycleClass


class SchedulerTargetKind(StrEnum):
    """How the scheduler invokes its target."""

    CLOUD_RUN = "CLOUD_RUN"
    """HTTP POST to a Cloud Run service endpoint."""

    GCE_VM_LAUNCHER = "GCE_VM_LAUNCHER"
    """Runs a VM launcher script in ``deployment-service/scripts/vm/``."""

    EVENTBRIDGE = "EVENTBRIDGE"
    """AWS EventBridge rule + target (mirror of a CLOUD_RUN entry on GCP)."""


@dataclass(frozen=True)
class SchedulerSpec:
    """Single scheduler entry in the workspace registry.

    Attributes:
        name: Unique scheduler job name (used verbatim as the Cloud Scheduler /
            EventBridge rule name). Must be kebab-case and globally unique.
        lifecycle_class: Always ``LifecycleClass.SCHEDULED_RECURRING``; kept
            explicit so display code can assert class uniformly across registry
            types.
        schedule_cron: Standard 5-field unix cron expression (UTC). Cloud
            Scheduler accepts this directly; EventBridge wraps it as
            ``cron(...)`` at deploy time.
        target_kind: How the scheduler invokes its target.
        target_ref: Cloud Run service name (CLOUD_RUN), launcher script
            relative path (GCE_VM_LAUNCHER), or EventBridge rule name
            (EVENTBRIDGE).
        asset_group: Canonical lowercase asset-group key this scheduler serves:
            ``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction`` /
            ``infra``. ``infra`` is for cross-cutting jobs (manifest
            consolidation, data-status rollup, T+1 audit).
        owning_plan: Plan filename (slug only, no path) that declared this
            scheduler.
        expected_max_runtime_seconds: Hard-kill timeout passed to the scheduler;
            Cloud Scheduler marks the job failed after this many seconds.
        max_consecutive_failures_before_page: Alert threshold. Monitoring fires
            when consecutive failures reach this count; 0 means alert on the
            first failure.
        env_tiers: Which environment tiers this scheduler is expected to exist
            in. Instruments-live triggers exclude DEV (no live credentials
            in local dev); infra triggers run in all tiers.
        cloud_targets: Which cloud targets this entry runs on. Both clouds by
            default; GCP-only entries have ``frozenset({CloudTarget.GCP})``.
    """

    name: str
    lifecycle_class: LifecycleClass
    schedule_cron: str
    target_kind: SchedulerTargetKind
    target_ref: str
    asset_group: str
    owning_plan: str
    expected_max_runtime_seconds: int
    max_consecutive_failures_before_page: int
    env_tiers: frozenset[EnvironmentTier]
    cloud_targets: frozenset[CloudTarget] = field(default_factory=lambda: frozenset({CloudTarget.GCP, CloudTarget.AWS}))


_STAGING_PROD: frozenset[EnvironmentTier] = frozenset({EnvironmentTier.STAGING, EnvironmentTier.PROD})
_ALL_TIERS: frozenset[EnvironmentTier] = frozenset({EnvironmentTier.DEV, EnvironmentTier.STAGING, EnvironmentTier.PROD})
_BOTH_CLOUDS: frozenset[CloudTarget] = frozenset({CloudTarget.GCP, CloudTarget.AWS})

_INSTRUMENTS_PLAN = "instruments_live_master_2026_05_08"
_DEPLOYMENT_UI_PLAN = "deployment_ui_lifecycle_tabs_2026_05_08"

SCHEDULER_REGISTRY: tuple[SchedulerSpec, ...] = (
    # ── CeFi 15-min OHLCV (CCXT; Phase D.1-2) ─────────────────────────────
    SchedulerSpec(
        name="cefi-ohlcv-15m",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="*/15 * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="cefi",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=600,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── TradFi 15-min OHLCV (Polygon; Phase C.1-2) ─────────────────────────
    # Cron scoped to NYSE trading hours (14:00-22:00 UTC Mon-Fri).
    SchedulerSpec(
        name="tradfi-ohlcv-15m",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="*/15 14-22 * * 1-5",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="tradfi",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=600,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── TradFi VIX OHLCV 15-min (Yahoo Finance live; Phase C.3) ────────────
    SchedulerSpec(
        name="tradfi-vix-ohlcv-15m",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="*/15 14-22 * * 1-5",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="tradfi",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=300,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Prediction market-discovery 15-min (Polymarket + Kalshi; Phase E.1) ─
    SchedulerSpec(
        name="prediction-market-discovery-15m",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="*/15 * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="prediction",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=300,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Sports: fixtures rolling-window poll (Phase B.1) ────────────────────
    SchedulerSpec(
        name="sports-fixtures-poll",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 6 * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="sports",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=1800,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Sports: fixture stats (Phase B.2) ───────────────────────────────────
    # Runs hourly 06-23 UTC to catch result ingestion after match windows.
    SchedulerSpec(
        name="sports-fixture-stats",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 6-23 * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="sports",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=1800,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Sports: leagues + teams season-roll (Phase B.3; 2 fires per season) ─
    SchedulerSpec(
        name="sports-leagues-teams-season-roll",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 4 * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="sports",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=1800,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Sports: player values transfer-window (Phase B.4) ───────────────────
    # Fires twice daily; trigger skips if not in a transfer window.
    SchedulerSpec(
        name="sports-player-values-transfer-window",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 8,20 * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="sports",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=1800,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Sports: weather pre-fixture (Phase B.5; 8 fires/fixture pre-kickoff) ─
    # Fires hourly; trigger fans out to fixtures kicking off within 8h window.
    SchedulerSpec(
        name="sports-weather-prefixture",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="sports",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=600,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Sports: lineups + injuries (Phase B.6; kickoff-60min + event-time) ──
    SchedulerSpec(
        name="sports-lineups-injuries",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="instruments-service",
        asset_group="sports",
        owning_plan=_INSTRUMENTS_PLAN,
        expected_max_runtime_seconds=600,
        max_consecutive_failures_before_page=3,
        env_tiers=_STAGING_PROD,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Infra: manifest consolidator (60s cadence) ──────────────────────────
    SchedulerSpec(
        name="manifest-consolidator-60s",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="* * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="deployment-api",
        asset_group="infra",
        owning_plan=_DEPLOYMENT_UI_PLAN,
        expected_max_runtime_seconds=55,
        max_consecutive_failures_before_page=5,
        env_tiers=_ALL_TIERS,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Infra: data-status rollup (5-min cadence) ───────────────────────────
    SchedulerSpec(
        name="data-status-rollup",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="*/5 * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="deployment-api",
        asset_group="infra",
        owning_plan=_DEPLOYMENT_UI_PLAN,
        expected_max_runtime_seconds=240,
        max_consecutive_failures_before_page=3,
        env_tiers=_ALL_TIERS,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Infra: manifest aggregation (15-min cadence) ─────────────────────────
    SchedulerSpec(
        name="manifest-aggregation-cron",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="*/15 * * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="deployment-api",
        asset_group="infra",
        owning_plan=_DEPLOYMENT_UI_PLAN,
        expected_max_runtime_seconds=600,
        max_consecutive_failures_before_page=3,
        env_tiers=_ALL_TIERS,
        cloud_targets=_BOTH_CLOUDS,
    ),
    # ── Infra: T+1 audit (daily 02:00 UTC) ──────────────────────────────────
    SchedulerSpec(
        name="t1-audit",
        lifecycle_class=LifecycleClass.SCHEDULED_RECURRING,
        schedule_cron="0 2 * * *",
        target_kind=SchedulerTargetKind.CLOUD_RUN,
        target_ref="deployment-api",
        asset_group="infra",
        owning_plan=_DEPLOYMENT_UI_PLAN,
        expected_max_runtime_seconds=3600,
        max_consecutive_failures_before_page=1,
        env_tiers=_ALL_TIERS,
        cloud_targets=_BOTH_CLOUDS,
    ),
)


def get_schedulers_for_env(
    env_tier: EnvironmentTier,
    cloud_target: CloudTarget | None = None,
) -> list[SchedulerSpec]:
    """Return schedulers expected in a given environment tier.

    Args:
        env_tier: The environment tier to filter for.
        cloud_target: If provided, further filter to entries expected on this
            cloud. If ``None``, returns all entries for the tier regardless of
            cloud target.

    Returns:
        Ordered list of :class:`SchedulerSpec` matching the filter. Preserves
        registry declaration order.
    """
    results = [s for s in SCHEDULER_REGISTRY if env_tier in s.env_tiers]
    if cloud_target is not None:
        results = [s for s in results if cloud_target in s.cloud_targets]
    return results
