"""Cloud-agnostic deployment schemas — shared across all repos.

These types are the canonical source of truth for deployment state, shard events,
and VM lifecycle events. All other repos (deployment-service, deployment-api,
deployment-ui backend) import from here rather than defining their own.

NO cloud SDKs (google-cloud-*, boto3). Pure Pydantic schemas + StrEnum only.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum  # still needed for DeploymentStatus, ComputeType, VMEventType
from typing import cast

from pydantic import BaseModel, Field

from unified_api_contracts.internal.modes import CloudProvider, PhaseMode, RuntimeMode


class DeploymentStatus(StrEnum):
    """Lifecycle status of a deployment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ComputeType(StrEnum):
    """Compute substrate used for the deployment."""

    CLOUD_RUN = "cloud_run"
    VM = "vm"
    BATCH = "batch"
    EC2 = "ec2"


class VMEventType(StrEnum):
    """Shard + VM lifecycle event types.

    Mirrors the TypeScript VMEventType union in deployment-ui.
    Values use UPPER_SNAKE_CASE to match the existing deployment-service events.py.
    """

    # VM infrastructure events
    VM_PREEMPTED = "VM_PREEMPTED"
    VM_DELETED = "VM_DELETED"
    VM_QUOTA_EXHAUSTED = "VM_QUOTA_EXHAUSTED"
    VM_ZONE_UNAVAILABLE = "VM_ZONE_UNAVAILABLE"
    VM_TIMEOUT = "VM_TIMEOUT"
    CONTAINER_OOM = "CONTAINER_OOM"

    # Cloud Run events
    CLOUD_RUN_REVISION_FAILED = "CLOUD_RUN_REVISION_FAILED"

    # Job lifecycle events
    JOB_RETRY = "JOB_RETRY"
    JOB_STARTED = "JOB_STARTED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCELLED = "JOB_CANCELLED"

    # Live deployment events
    LIVE_HEALTH_CHECK_PASSED = "LIVE_HEALTH_CHECK_PASSED"
    LIVE_HEALTH_CHECK_FAILED = "LIVE_HEALTH_CHECK_FAILED"
    LIVE_ROLLBACK_EXECUTED = "LIVE_ROLLBACK_EXECUTED"


#: VM infrastructure event types — subset used for the /vm-events endpoint filter
VM_INFRASTRUCTURE_EVENTS: frozenset[VMEventType] = frozenset(
    {
        VMEventType.VM_PREEMPTED,
        VMEventType.VM_DELETED,
        VMEventType.VM_QUOTA_EXHAUSTED,
        VMEventType.VM_ZONE_UNAVAILABLE,
        VMEventType.VM_TIMEOUT,
        VMEventType.CONTAINER_OOM,
        VMEventType.CLOUD_RUN_REVISION_FAILED,
    }
)


class ShardEvent(BaseModel):
    """A single event in a shard's lifecycle.

    Written to GCS as one JSON line in:
      deployments/{deployment_id}/shards/{shard_id}/events.jsonl

    Compatible with the dataclass ShardEvent in deployment-service/events.py —
    same field names and serialisation format.
    """

    deployment_id: str
    shard_id: str
    event_type: VMEventType
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def is_vm_event(self) -> bool:
        """True if this is a VM infrastructure event (not a job lifecycle event)."""
        return self.event_type in VM_INFRASTRUCTURE_EVENTS

    def to_jsonl(self) -> str:
        """Single-line JSON suitable for JSONL append."""
        return json.dumps(
            {
                "deployment_id": self.deployment_id,
                "shard_id": self.shard_id,
                "event_type": str(self.event_type),
                "message": self.message,
                "timestamp": self.timestamp.isoformat(),
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_jsonl(cls, line: str) -> ShardEvent:
        """Parse a single JSONL line back into a ShardEvent."""
        raw = cast(dict[str, object], json.loads(line))
        raw_metadata = raw.get("metadata")
        metadata: dict[str, str] = (
            {str(k): str(v) for k, v in cast(dict[str, object], raw_metadata).items()}
            if isinstance(raw_metadata, dict)
            else {}
        )
        return cls(
            deployment_id=str(raw["deployment_id"]),
            shard_id=str(raw["shard_id"]),
            event_type=VMEventType(str(raw["event_type"])),
            message=str(raw["message"]),
            timestamp=datetime.fromisoformat(str(raw["timestamp"])),
            metadata=metadata,
        )


class DeploymentState(BaseModel):
    """Canonical state record for a deployment.

    Stored as JSON in GCS at:
      deployments/{deployment_id}/state.json

    All fields added after the initial schema version have defaults to maintain
    backwards compatibility when reading older state files.
    """

    deployment_id: str
    service: str
    status: DeploymentStatus
    tag: str
    region: str
    created_at: str
    updated_at: str
    total_shards: int
    completed_shards: int
    failed_shards: int

    # Fields added in schema v2 — default for backwards compat
    deploy_mode: RuntimeMode = RuntimeMode.BATCH
    compute_type: ComputeType = ComputeType.VM
    cloud_provider: CloudProvider = CloudProvider.GCP
    phase_mode: PhaseMode = PhaseMode.PHASE_3

    parameters: dict[str, object] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """True if the deployment has reached a terminal state."""
        return self.status in {
            DeploymentStatus.COMPLETED,
            DeploymentStatus.FAILED,
            DeploymentStatus.CANCELLED,
            DeploymentStatus.TIMED_OUT,
        }

    @property
    def progress_pct(self) -> float:
        """Percentage of shards completed (0-100)."""
        if self.total_shards == 0:
            return 0.0
        return round(self.completed_shards / self.total_shards * 100, 1)


class BackfillLaunchTaskKind(StrEnum):
    """Closed set of supported backfill / migration / forward-poll launcher tasks.

    Each value maps 1:1 to a `deployment-service/scripts/vm/launch-*.sh` script. Adding a
    new task = (1) add a launcher script, (2) add a value here, (3) update
    `_TASK_TO_LAUNCHER` in `deployment-api/deployment_api/routes/backfill_launch.py`,
    (4) ensure the resolved vm-name prefix is in `VM_PREFIX_TO_BUCKET` in
    `deployment-service/scripts/vm/vm_zombie_watchdog.py`. Failure to do any of these
    leaves an unwatched zombie or a 400 from the launch endpoint.
    """

    CEFI_BACKFILL = "cefi_backfill"
    CEFI_FORWARD_POLL = "cefi_forward_poll"
    TRADFI_BACKFILL = "tradfi_backfill"
    TRADFI_FORWARD_POLL = "tradfi_forward_poll"
    DEFI_FORWARD_POLL = "defi_forward_poll"
    PREDICTION_FORWARD_POLL = "prediction_forward_poll"
    SPORTS_FORWARD_POLL = "sports_forward_poll"
    AF_BACKFILL = "af_backfill"
    FOOTYSTATS_BACKFILL = "footystats_backfill"
    SFI_BACKFILL = "sfi_backfill"
    UNDERSTAT_BACKFILL = "understat_backfill"
    TRANSFERMARKT_BACKFILL = "transfermarkt_backfill"
    OPENMETEO_BACKFILL = "openmeteo_backfill"
    MTDS_PREDICTION_BACKFILL = "mtds_prediction_backfill"
    MTDS_PERP_FUNDING_BACKFILL = "mtds_perp_funding_backfill"
    MTDS_GAS_FEES_BACKFILL = "mtds_gas_fees_backfill"
    MTDS_LST_RATES_BACKFILL = "mtds_lst_rates_backfill"
    MTDS_VAULT_SHARE_PRICE_BACKFILL = "mtds_vault_share_price_backfill"
    MTDS_LENDING_INDICES_BACKFILL = "mtds_lending_indices_backfill"
    MDPS_BACKFILL = "mdps_backfill"
    FEATURES_BACKFILL = "features_backfill"
    FEATURES_SPORTS_BACKFILL = "features_sports_backfill"
    CANONICAL_MIGRATION = "canonical_migration"


class BackfillLaunchRequest(BaseModel):
    """Request payload for `POST /api/backfill/launch`.

    The endpoint resolves `(task, asset_group, venue?)` to a `launch-*.sh` script and
    constructs the gcloud-launch invocation. Either `dry_run=True` or
    `_cfg.is_mock_mode()` short-circuits before any subprocess call — production VMs
    are never created from CI / unit tests.

    Field semantics mirror the env-var contract in `setup-data-pipeline-vm.sh`:
    `VM_NAME` / `MANIFEST_PER_VM_SHARDS` / `VM_FORCE` / `SKIP_DEPENDENCY_CHECK` /
    `RUN_TS` / `VM_FORCE_WINDOW` are always set; task-specific
    `VM_VENUE`/`VM_START_DATE`/`VM_END_DATE`/`VM_DATA_TYPES`/`VM_INSTRUMENT_IDS`/
    `VM_ASSET_GROUP` are set when the corresponding fields are populated.
    """

    task: BackfillLaunchTaskKind
    asset_group: str = Field(
        ...,
        description=(
            "Lowercase asset_group dict key — one of {cefi, defi, tradfi, prediction, "
            "sports}. Per the workspace dict-keys-stay-lowercase exception."
        ),
        pattern=r"^(cefi|defi|tradfi|prediction|sports)$",
    )
    venue: str | None = Field(default=None, description="Venue identifier (e.g. binance, bybit, cme, deribit).")
    start_date: str | None = Field(
        default=None,
        description="ISO date YYYY-MM-DD; required for backfill tasks, optional for forward-poll.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    end_date: str | None = Field(
        default=None,
        description="ISO date YYYY-MM-DD; required for backfill tasks, optional for forward-poll.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    data_types: list[str] | None = Field(
        default=None,
        description="Optional data_types filter (e.g. ['ohlcv_1m', 'trades']).",
    )
    instrument_ids: list[str] | None = Field(default=None, description="Optional explicit instrument-id list.")
    tier_plan: str | None = Field(
        default=None,
        description=(
            "Optional tier-plan string (e.g. 'crypto-basis-2023-05+2024-06'). Forwarded to "
            "the launcher's --tier-plan flag."
        ),
    )
    year: str | None = Field(default=None, description="Optional 4-digit year (e.g. '2025') for year-shard launchers.")
    month: str | None = Field(
        default=None,
        description="Optional YYYY-MM (e.g. '2025-06') for month-shard launchers.",
        pattern=r"^\d{4}-\d{2}$",
    )
    root_symbol: str | None = Field(
        default=None,
        description="Optional root symbol (ES, BTC, ETH, IBIT, ETHA) for TradFi launchers.",
    )
    extra_metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Forward-compat metadata pass-through — keys + values are added verbatim to the "
            "VM's `gcloud --metadata` payload. Use sparingly; prefer first-class fields when "
            "the launcher already supports the env var."
        ),
    )
    force: bool = Field(
        default=False,
        description=(
            "Bypass singleton-lock for shared-API-key launchers (sfi-forward-poll, "
            "mtds-prediction-backfill). Equivalent to the launcher's --force flag."
        ),
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "Echo-only mode — endpoint resolves argv + env but does NOT shell out. Same "
            "semantics as the launcher's --dry-run flag. Required for staging tests + CI."
        ),
    )
    skip_dependency_check: bool = Field(
        default=False,
        description=(
            "Sets SKIP_DEPENDENCY_CHECK=true on the VM, bypassing the upstream-data "
            "pre-flight gate. Use only for forward-poll re-runs after manifest correction."
        ),
    )


class BackfillLaunchResult(BaseModel):
    """Response payload for `POST /api/backfill/launch`.

    Returned regardless of dry_run / mock-mode — caller MUST verify event emission via
    `GET /api/vm/events?vm_name=<vm_name>` per the no-fire-and-forget rule.
    """

    vm_name: str = Field(
        ...,
        description="Resolved GCP VM name (validated against [a-z](?:[-a-z0-9]{0,61}[a-z0-9])?).",
    )
    vm_name_prefix: str = Field(
        ...,
        description="vm_name's prefix segment — must appear in VM_PREFIX_TO_BUCKET.",
    )
    zone: str = Field(default="asia-northeast1-c", description="GCP zone.")
    project_id: str
    launched_at: datetime
    correlation_id: str = Field(..., description="UUID4 — sub-partition under the events bucket.")
    launcher_script: str = Field(..., description="Resolved launch-*.sh script name.")
    dry_run: bool
    events_uri: str = Field(
        ...,
        description=(
            "GCS URI prefix for the VM's lifecycle events: gs://{project_id}-events/events/{service}/{date}/{vm_name}/"
        ),
    )
    argv: list[str] = Field(
        default_factory=list,
        description=(
            "Resolved subprocess argv (bash launcher_path + flags) — populated for "
            "dry_run inspection. Empty in non-dry-run responses to keep payload small."
        ),
    )
    env_diff: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "VM_* env vars + custom metadata applied on top of the launcher's defaults — "
            "populated for dry_run inspection."
        ),
    )


class VMLifecycleEvent(BaseModel):
    """One parsed JSONL row from the events bucket.

    Mirrors the schema documented in `codex/03-observability/lifecycle-events.md` and
    confirmed via live probe of `gs://central-element-323112-events/...` 2026-05-07.
    """

    event: str = Field(..., description="Event type (e.g. STARTED, STOPPED, INSTRUMENT_PROCESSED).")
    service: str
    timestamp: datetime
    severity: str = Field(default="INFO", description="One of INFO / WARNING / ERROR / CRITICAL.")
    correlation_id: str | None = None
    details: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Stringified subset of metadata.details — keys preserved verbatim. Use "
            "raw_metadata for the unparsed payload (objects, lists, nested dicts)."
        ),
    )
    raw_metadata: dict[str, object] = Field(
        default_factory=dict,
        description="Verbatim contents of metadata.* — keep for callers that need the full payload.",
    )


class VMEventListResult(BaseModel):
    """Response payload for `GET /api/vm/events`."""

    vm_name: str
    service: str
    date: str = Field(..., description="UTC date scanned (YYYY-MM-DD).", pattern=r"^\d{4}-\d{2}-\d{2}$")
    hours_scanned: list[int] = Field(default_factory=list)
    total_events: int
    events: list[VMLifecycleEvent] = Field(default_factory=list)
    truncated: bool = Field(
        default=False,
        description="True if `len(events) == limit` — caller should follow next_page_token.",
    )
    next_page_token: str | None = Field(
        default=None,
        description="Opaque base64 cursor encoding (last_timestamp, blob_index, row_index).",
    )


__all__ = [
    "VM_INFRASTRUCTURE_EVENTS",
    "BackfillLaunchRequest",
    "BackfillLaunchResult",
    "BackfillLaunchTaskKind",
    "ComputeType",
    "DeploymentState",
    "DeploymentStatus",
    "ShardEvent",
    "VMEventListResult",
    "VMEventType",
    "VMLifecycleEvent",
]
