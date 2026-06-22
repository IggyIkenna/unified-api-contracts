"""Lifecycle-class taxonomy for deployable / monitorable workspace surfaces.

SSOT for the four mutually-orthogonal lifecycle classes the deployment-UI,
deployment-api, VM zombie-watchdog, and experiment-tracker all classify
runtime artefacts against. Defined by ``deployment_ui_lifecycle_tabs_2026_05_08``
plan Phase A.1 — the doc-touchpoint plan section names this module as the
single source of truth for the closed-set 4-class taxonomy.

The four classes
----------------

* :attr:`LifecycleClass.EPHEMERAL_BATCH` — data + pricing pipeline jobs
  (instruments-service, market-tick-data-service, market-data-processing-service,
  features-* backfills + smokes + migrations + forward-poll). Has start +
  end; progress measured in dates x shards captured / empty / failed. The
  Monitor → Backfill sub-tab surfaces these.

* :attr:`LifecycleClass.EPHEMERAL_EXPERIMENT` — research jobs each tagged
  with a ``run_id`` (UUIDv7 sortable). Three experiment kinds today:
  ML training, strategy backtest, execution backtest. Has start + end;
  progress measured in epochs / folds / backtest-day cursors; produces
  model artefacts + result blobs. The Monitor → Experiments sub-tab
  surfaces these.

* :attr:`LifecycleClass.SCHEDULED_RECURRING` — recurring triggers
  (Cloud Scheduler / EventBridge / VM cron). Expected to fire forever;
  alive / dead / stale / paused / missing states matter. The Monitor →
  Scheduled sub-tab surfaces these.

* :attr:`LifecycleClass.LONG_LIVED_LIVE` — continuous deployment clusters
  (live strategy, execution, live-MTDS, position-balance, risk, alerting).
  Lifecycle actions are start / stop / pause / restart / drain. The
  Monitor → Live sub-tab surfaces these.

Layer split
-----------

* **[UAC]** — this module. The 4-class enum, the ``VmPrefixSpec``
  dataclass, and the four ``classify_*`` helpers.
* **[deployment-service]** — ``vm_zombie_watchdog.py``'s ``VM_PREFIX_TO_BUCKET``
  registry uses ``VmPrefixSpec`` values (Phase A.2). New VM-name prefixes
  MUST tag a ``lifecycle_class`` per the CLAUDE.md "VM Naming Convention"
  section update.
* **[deployment-api]** — Monitor sub-tab routes call ``classify_vm_name`` /
  ``classify_cloud_run_service`` to filter by lifecycle class.
* **[deployment-ui]** — the four Monitor sub-tabs render the four classes
  with a shared row-template.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class LifecycleClass(StrEnum):
    """Closed-set 4-class lifecycle taxonomy.

    Each member's value equals its name (canonical UAC StrEnum convention,
    see :class:`unified_api_contracts.canonical.crosscutting.share_class.ShareClass`
    for the precedent).
    """

    EPHEMERAL_BATCH = "EPHEMERAL_BATCH"
    """Data + pricing pipeline jobs (instruments / MTDS / MDPS / features-*).

    Has start + end. Progress is dates x shards captured / empty / failed.
    Surfaced in Monitor → Backfill.
    """

    EPHEMERAL_EXPERIMENT = "EPHEMERAL_EXPERIMENT"
    """ML training / strategy backtest / execution backtest research jobs.

    Has start + end. Each run is tagged with a ``run_id`` (UUIDv7).
    Progress is epochs / folds / backtest-day cursors. Produces model
    artefacts + result blobs. Surfaced in Monitor → Experiments.
    """

    SCHEDULED_RECURRING = "SCHEDULED_RECURRING"
    """Recurring triggers — Cloud Scheduler / EventBridge / VM cron.

    Expected to fire forever. ``alive`` / ``dead`` / ``stale`` / ``paused``
    / ``missing`` states matter. Surfaced in Monitor → Scheduled.
    """

    LONG_LIVED_LIVE = "LONG_LIVED_LIVE"
    """Continuous deployment clusters (strategy / execution / live-MTDS /
    position-balance / risk / alerting).

    Lifecycle actions are start / stop / pause / restart / drain.
    Surfaced in Monitor → Live.
    """


@dataclass(frozen=True)
class VmPrefixSpec:
    """Per-VM-name-prefix declaration for the zombie-watchdog registry.

    Replaces the bare ``{prefix: bucket | None}`` shape with a typed
    spec carrying the lifecycle class. Phase A.2 of the
    ``deployment_ui_lifecycle_tabs_2026_05_08`` plan migrates the
    ``VM_PREFIX_TO_BUCKET`` dict in ``vm_zombie_watchdog.py`` to this
    shape.

    Attributes:
        bucket: GCS shard-output bucket the VM writes to, or ``None``
            for heartbeat-only VMs (e.g. the watchdog itself, the
            manifest consolidator).
        lifecycle_class: Which Monitor sub-tab this VM appears under.
    """

    bucket: str | None
    lifecycle_class: LifecycleClass


def classify_vm_name(
    vm_name: str,
    registry: Mapping[str, VmPrefixSpec],
) -> LifecycleClass:
    """Classify a VM by name against a prefix registry.

    Uses **longest-prefix-match** so callers can register a generic
    prefix (e.g. ``"live-"``) alongside a more specific one
    (e.g. ``"live-strategy-"``) and the more specific entry wins for
    matching VM names.

    Args:
        vm_name: The full VM name (e.g.
            ``"cefi-bitfinex-spot-2023-heavy-20260504-194158"``).
        registry: Mapping from prefix → :class:`VmPrefixSpec`. Typically
            the ``VM_PREFIX_TO_BUCKET`` dict from ``vm_zombie_watchdog.py``.

    Returns:
        The lifecycle class of the matching prefix's spec.

    Raises:
        ValueError: If no prefix in the registry is a prefix of
            ``vm_name``. The error message includes ``vm_name`` so
            callers can fix the registry (CLAUDE.md "VM Naming
            Convention" rule — every prefix MUST be registered).
    """
    best_match: str | None = None
    for prefix in registry:
        if vm_name.startswith(prefix) and (best_match is None or len(prefix) > len(best_match)):
            best_match = prefix
    if best_match is None:
        raise ValueError(
            f"VM name {vm_name!r} matches no registered prefix; add a VmPrefixSpec entry to VM_PREFIX_TO_BUCKET."
        )
    return registry[best_match].lifecycle_class


def classify_cloud_run_service(name: str) -> LifecycleClass:
    """Classify a Cloud Run service by name.

    Cloud Run services hosted in the workspace are long-lived by
    definition — Cloud Run does not run ephemeral batch jobs (those go
    on GCE VMs). Service-name patterns:

    * ``live-*`` → :attr:`LifecycleClass.LONG_LIVED_LIVE`
    * Names ending ``-api`` or ``-ui`` (e.g. ``deployment-api``,
      ``deployment-ui``, ``trading-system-ui``) →
      :attr:`LifecycleClass.LONG_LIVED_LIVE`

    Args:
        name: The Cloud Run service name.

    Returns:
        :attr:`LifecycleClass.LONG_LIVED_LIVE` for any matching pattern.

    Raises:
        ValueError: If the name does not match a known pattern. Callers
            must update the patterns here when adding a new long-lived
            service shape.
    """
    if name.startswith("live-") or name.endswith("-api") or name.endswith("-ui"):
        return LifecycleClass.LONG_LIVED_LIVE
    raise ValueError(
        f"Cloud Run service name {name!r} matches no known lifecycle pattern; expected 'live-*', '*-api', or '*-ui'."
    )


def classify_scheduled_job(name: str) -> LifecycleClass:
    """Classify a Cloud Scheduler / EventBridge / VM cron job.

    All scheduler-managed jobs are :attr:`LifecycleClass.SCHEDULED_RECURRING`
    by definition; this helper exists so call-sites have a single typed
    surface to dispatch through (parallel shape with
    :func:`classify_vm_name`, :func:`classify_cloud_run_service`,
    :func:`classify_experiment_run`).

    Args:
        name: Scheduler job name (passed for symmetry + future per-name
            overrides; currently unused in the classification).

    Returns:
        :attr:`LifecycleClass.SCHEDULED_RECURRING`.
    """
    del name  # Reserved for future per-name overrides.
    return LifecycleClass.SCHEDULED_RECURRING


def classify_experiment_run(run_id: str) -> LifecycleClass:
    """Classify an experiment run by its ``run_id``.

    All experiment runs are :attr:`LifecycleClass.EPHEMERAL_EXPERIMENT`
    by definition; this helper exists so call-sites have a single typed
    surface (parallel shape with the other three classifiers).

    Args:
        run_id: UUIDv7 of the experiment run (passed for symmetry +
            future use; currently unused in the classification).

    Returns:
        :attr:`LifecycleClass.EPHEMERAL_EXPERIMENT`.
    """
    del run_id  # Reserved for future per-run overrides.
    return LifecycleClass.EPHEMERAL_EXPERIMENT


# ===========================================================================
# Deployment-observability umbrella model
# ===========================================================================
#
# The umbrella is the deployment-observability classification the whole
# /deployments surface hangs off (deployment-api ``/api/deployments``,
# deployment-ui Deployments page, the Slack deployment notifier). Every
# compute unit (a GCE/EC2 **VM** or a Cloud Run **job execution**) classifies
# to exactly one umbrella x cloud x service x asset_group.
#
# Umbrella vs lifecycle_class: the 4-class :class:`LifecycleClass` taxonomy is
# the VM-level Monitor sub-tab classification (batch / experiment / scheduled /
# live). The umbrella is the higher-level deployment grouping the operator
# reasons about — ``live`` / ``batch`` / ``paper`` / ``experiment``. The mapping
# is :data:`UMBRELLA_FOR_LIFECYCLE_CLASS`, with PAPER as an explicit override
# (paper crons are ``SCHEDULED_RECURRING`` by lifecycle but ``paper`` by
# umbrella). SSOT: ``deployment_observability_parity_live_batch_paper_2026_06_22``
# plan, Phase 0.


class DeploymentUmbrella(StrEnum):
    """Closed-set 4-umbrella deployment-observability classification.

    Each compute unit (VM or Cloud Run job execution) belongs to exactly one
    umbrella. The operator's /deployments surface tabs on Live / Batch / Paper
    (Experiment folds under Batch in the UI by default).
    """

    LIVE = "LIVE"
    """Long-lived continuous deployments — live capture / trading / risk /
    execution clusters. Derives from :attr:`LifecycleClass.LONG_LIVED_LIVE`."""

    BATCH = "BATCH"
    """Bounded data/pricing pipeline jobs + recurring infra jobs — backfills,
    forward-polls, Cloud Run audits / consolidator / catalogue / expected-universe.
    Derives from :attr:`LifecycleClass.EPHEMERAL_BATCH` +
    :attr:`LifecycleClass.SCHEDULED_RECURRING`."""

    PAPER = "PAPER"
    """Paper-trading deployments (paper VMs + paper crons). Has NO single
    lifecycle_class — an explicit override carried on ``VmPrefixSpec.umbrella``
    or passed as ``is_paper`` to :func:`classify_deployment_target`, because a
    paper cron is ``SCHEDULED_RECURRING`` by lifecycle yet ``paper`` by
    umbrella."""

    EXPERIMENT = "EXPERIMENT"
    """Research jobs (ML training / strategy backtest / execution backtest).
    Derives from :attr:`LifecycleClass.EPHEMERAL_EXPERIMENT`. Folded under Batch
    in the UI by default."""


class DeploymentCloud(StrEnum):
    """Cloud a deployment runs on. GCP first (operator), then AWS."""

    GCP = "GCP"
    AWS = "AWS"


class DeploymentKind(StrEnum):
    """The runtime kind of a compute unit.

    A ``VM`` is a GCE / EC2 instance; a ``CLOUD_RUN_JOB`` is a GCP Cloud Run
    job (AWS equivalent is Batch Fargate, also modelled as a job kind).
    """

    VM = "VM"
    CLOUD_RUN_JOB = "CLOUD_RUN_JOB"


@dataclass(frozen=True)
class DeploymentTarget:
    """A classified compute unit on the deployment-observability surface.

    Built by :func:`classify_deployment_target` (deployment-service) and read by
    every observability surface (deployment-api ``/api/deployments``,
    deployment-ui Deployments page, the Slack deployment notifier). Carries the
    full classification so no surface re-derives it.

    Attributes:
        name: The VM-name prefix-match target, full VM name, or Cloud Run job
            name being classified.
        kind: Whether this is a VM or a Cloud Run job.
        umbrella: The Live / Batch / Paper / Experiment grouping.
        cloud: GCP or AWS.
        service: The owning logical service (e.g. ``market-tick-data-service``,
            ``strategy-service``, ``manifest-consolidator``).
        asset_group: The asset_group (``cefi`` / ``defi`` / ``tradfi`` /
            ``sports`` / ``prediction``), or ``""`` for cross-asset infra
            (audits / consolidator / catalogue).
        lifecycle_class: The canonical lifecycle-class string this target maps
            to (a :class:`LifecycleClass` value), or ``""`` for Cloud Run jobs
            that have no VM lifecycle class.
    """

    name: str
    kind: DeploymentKind
    umbrella: DeploymentUmbrella
    cloud: DeploymentCloud
    service: str
    asset_group: str
    lifecycle_class: str


UMBRELLA_FOR_LIFECYCLE_CLASS: Final[Mapping[str, DeploymentUmbrella]] = {
    LifecycleClass.EPHEMERAL_BATCH.value: DeploymentUmbrella.BATCH,
    LifecycleClass.SCHEDULED_RECURRING.value: DeploymentUmbrella.BATCH,
    LifecycleClass.LONG_LIVED_LIVE.value: DeploymentUmbrella.LIVE,
    LifecycleClass.EPHEMERAL_EXPERIMENT.value: DeploymentUmbrella.EXPERIMENT,
}
"""Umbrella for each lifecycle_class.

Note PAPER is absent — paper deployments have no lifecycle_class of their own
(a paper cron is ``SCHEDULED_RECURRING``), so PAPER is always an explicit
override (``VmPrefixSpec.umbrella`` or the ``is_paper`` arg to
:func:`classify_deployment_target`)."""
