"""Normalized alert ledger schema — the union shape every mirrored alert source writes to.

Gating deliverable for `deployment_alerts_ingestion_completeness_2026_07_20.md` (Plan A of the
alerts-ingestion workstream). Plan B (the alerts-page rebuild) builds its filter/sort/date-range
dimensions against this contract, so every alert source — GHA CI events, deployment-api's own
persisted alerts, alerting-service history, the VM zombie-watchdog reaper, and the kill-switch
audit log — normalizes into `NormalizedAlertRow` rather than inventing per-source fields.

`FIELD_COVERAGE` documents, per source plane, whether a field is:

- POPULATED   — already written today, no further work needed.
- POPULATABLE — the value exists at the emit site but isn't persisted/mapped yet; a sibling
  ingestion todo in the plan wires it. Flips to POPULATED only once that todo ships AND the
  plan's post-ingestion coverage re-measure observes it in the live ledger — never on self-report.
- ABSENT      — structurally inapplicable for that source (e.g. `subject_repo` for a VM-scoped
  zombie-watchdog reap). Readers/filters must treat this as a real, permanent gap, not a bug.

Cross-reference: plans/active/deployment_alerts_ingestion_completeness_2026_07_20.md
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field


class AlertSourcePlane(StrEnum):
    """Which durable store/emitter a normalized alert row originated from."""

    GHA_CI_EVENTS = "gha_ci_events"
    """`.github/actions/persist-event` -> `cicd/events/{repo_name}/{date}/events.jsonl`."""

    DEPLOYMENT_API = "deployment_api"
    """`deployment_api.routes.deployments_inventory._persist_alert` ->
    `cicd/alerts/{date}/alerts.jsonl`."""

    ALERTING_SERVICE = "alerting_service"
    """alerting-service's own store -> `alerting/history/date=.../*.jsonl`."""

    ZOMBIE_WATCHDOG = "zombie_watchdog"
    """`deployment-service/scripts/vm/vm_zombie_watchdog.py` VM-reap detections."""

    KILL_SWITCH_AUDIT = "kill_switch_audit"
    """UTL `kill_switch/audit_log.py` arm/disarm events, read-only projection."""


class FieldCoverage(StrEnum):
    """Per-source, per-field availability against the normalized schema."""

    POPULATED = "populated"
    POPULATABLE = "populatable"
    ABSENT = "absent"


class NormalizedAlertRow(BaseModel):
    """The union row shape every mirrored alert source normalizes into.

    A null field is either ABSENT (the concept doesn't exist for that source) or
    POPULATABLE-but-not-yet-wired (see `FIELD_COVERAGE`) — readers must not treat null as
    an ingestion error.
    """

    timestamp: str = Field(description="UTC ISO-8601 event time.")
    source_plane: AlertSourcePlane = Field(description="Which store this row was normalized from.")
    subject_repo: str | None = Field(
        default=None, description="The repo the alert is ABOUT (not the repo/service that emitted it)."
    )
    emitting_repo: str | None = Field(default=None, description="The repo/service that wrote this alert.")
    severity: str | None = Field(default=None, description="AlertSeverity-compatible string, when known.")
    alert_class: str | None = Field(default=None, description="Class/rule id for the alert (e.g. AlertCode value).")
    message: str | None = Field(default=None, description="Human-readable alert body.")
    service: str | None = Field(default=None, description="The service/component the alert concerns.")
    deployment_target: str | None = Field(
        default=None, description="VM name / deployment id the alert concerns, when applicable."
    )
    run_url: str | None = Field(default=None, description="Link back to the originating run/build, when one exists.")
    dedup_key: str | None = Field(default=None, description="De-duplication key, when the source defines one.")
    resolved_state: str | None = Field(
        default=None, description="Nullable — null while open/unknown, set once a source reports resolution."
    )


# The contract Plan B's filter/sort dimensions are built against. Keep in sync with
# `deployment_alerts_ingestion_completeness_2026_07_20.md`'s per-source ingestion todos.
FIELD_COVERAGE: Final[dict[AlertSourcePlane, dict[str, FieldCoverage]]] = {
    AlertSourcePlane.GHA_CI_EVENTS: {
        "timestamp": FieldCoverage.POPULATED,
        "subject_repo": FieldCoverage.POPULATED,  # `repo_name` — the workflow's own repo
        "emitting_repo": FieldCoverage.ABSENT,  # each repo reports on itself; no distinct emitter
        "severity": FieldCoverage.ABSENT,
        "alert_class": FieldCoverage.ABSENT,
        "message": FieldCoverage.ABSENT,
        "service": FieldCoverage.ABSENT,
        "deployment_target": FieldCoverage.ABSENT,
        "run_url": FieldCoverage.POPULATABLE,  # derivable from `run_id` + `repo_name`, not written today
        "dedup_key": FieldCoverage.ABSENT,
        "resolved_state": FieldCoverage.ABSENT,
    },
    AlertSourcePlane.DEPLOYMENT_API: {
        "timestamp": FieldCoverage.POPULATED,
        "subject_repo": FieldCoverage.POPULATABLE,  # the emitting-vs-subject defect this plan fixes
        "emitting_repo": FieldCoverage.POPULATED,  # hardcoded "deployment-api" today
        "severity": FieldCoverage.POPULATED,
        "alert_class": FieldCoverage.POPULATED,
        "message": FieldCoverage.POPULATED,
        "service": FieldCoverage.ABSENT,
        "deployment_target": FieldCoverage.POPULATABLE,  # `_persist_alert()` takes no vm_name/deployment_id param yet
        "run_url": FieldCoverage.POPULATED,  # field exists, written as "" today
        "dedup_key": FieldCoverage.POPULATED,
        "resolved_state": FieldCoverage.ABSENT,
    },
    AlertSourcePlane.ALERTING_SERVICE: {
        "timestamp": FieldCoverage.POPULATED,
        "subject_repo": FieldCoverage.ABSENT,  # infra/venue-scoped, not repo-scoped
        "emitting_repo": FieldCoverage.POPULATABLE,  # constant "alerting-service", not currently stamped
        "severity": FieldCoverage.POPULATED,
        "alert_class": FieldCoverage.POPULATABLE,  # decision 2 — persist alongside delivery status
        "message": FieldCoverage.POPULATABLE,  # present on the decision record only, absent on delivery record
        "service": FieldCoverage.POPULATABLE,  # router.py `source` — routed to Slack only today
        "deployment_target": FieldCoverage.POPULATABLE,  # `details.get("vm_name"/...)` — Slack-only today
        "run_url": FieldCoverage.ABSENT,
        "dedup_key": FieldCoverage.ABSENT,
        "resolved_state": FieldCoverage.ABSENT,
    },
    AlertSourcePlane.ZOMBIE_WATCHDOG: {
        "timestamp": FieldCoverage.POPULATABLE,  # available at fire time, no persistence at all today
        "subject_repo": FieldCoverage.ABSENT,
        "emitting_repo": FieldCoverage.POPULATABLE,  # constant "deployment-service"
        "severity": FieldCoverage.ABSENT,
        "alert_class": FieldCoverage.POPULATABLE,  # `WatchdogVerdict.verdict` reason string
        "message": FieldCoverage.POPULATABLE,  # constructible from zone/age/reason
        "service": FieldCoverage.ABSENT,
        "deployment_target": FieldCoverage.POPULATABLE,  # `vm_name`
        "run_url": FieldCoverage.ABSENT,
        "dedup_key": FieldCoverage.POPULATABLE,  # derivable from vm_name
        "resolved_state": FieldCoverage.ABSENT,
    },
    AlertSourcePlane.KILL_SWITCH_AUDIT: {
        "timestamp": FieldCoverage.POPULATED,  # `event_timestamp`
        "subject_repo": FieldCoverage.ABSENT,
        "emitting_repo": FieldCoverage.POPULATABLE,  # constant "unified-trading-library"
        "severity": FieldCoverage.ABSENT,  # armed/disarmed is not a severity axis
        "alert_class": FieldCoverage.POPULATABLE,  # `event_type` (armed/disarmed)
        "message": FieldCoverage.POPULATABLE,  # composable from actor/provenance/metadata_json
        "service": FieldCoverage.POPULATABLE,  # `switch_id`
        "deployment_target": FieldCoverage.ABSENT,
        "run_url": FieldCoverage.ABSENT,
        "dedup_key": FieldCoverage.POPULATABLE,  # switch_id + event_timestamp
        "resolved_state": FieldCoverage.POPULATABLE,  # null while armed, set on disarm (`recovery_mode`)
    },
}
