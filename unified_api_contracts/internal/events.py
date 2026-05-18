"""Internal lifecycle event schemas — envelope structure, all event types, per-type metadata."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from unified_api_contracts.internal.modes import LogLevel

REQUIRED_EVENT_FIELDS: dict[str, list[str]] = {
    "ALL": ["correlation_id", "service_version", "local_timestamp"],
    "FAILED": ["stack_trace", "error_category"],
    "COMPLETED": ["duration_ms"],
    "MARKET_DATA": ["exchange_timestamp", "local_timestamp", "sequence_number"],
    "EXECUTION": ["client_order_id", "exchange_timestamp", "venue_response_id"],
}


class LifecycleEventType(StrEnum):
    # Universal
    STARTED = "STARTED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    DATA_INGESTION_STARTED = "DATA_INGESTION_STARTED"
    DATA_INGESTION_COMPLETED = "DATA_INGESTION_COMPLETED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    DATA_BROADCAST = "DATA_BROADCAST"
    PERSISTENCE_STARTED = "PERSISTENCE_STARTED"
    PERSISTENCE_COMPLETED = "PERSISTENCE_COMPLETED"
    # Security / audit
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    CONFIG_CHANGED = "CONFIG_CHANGED"
    SECRET_ACCESSED = "SECRET_ACCESSED"
    # Coordination — cross-service pipeline readiness signals
    DATA_READY = "DATA_READY"
    PREDICTIONS_READY = "PREDICTIONS_READY"
    STRATEGY_SIGNALS_READY = "STRATEGY_SIGNALS_READY"
    # Pipeline data availability
    UPSTREAM_NOT_READY = "UPSTREAM_NOT_READY"
    SHARD_INCOMPLETE = "SHARD_INCOMPLETE"
    WRITE_FAILED = "WRITE_FAILED"
    # Preflight short-circuit visibility — emitted EVERY time a service's
    # preflight guard / freshness check / skip-date guard short-circuits
    # before processing. Without this, silent skips look identical to
    # silent successes from the event stream alone (reference incident
    # 2026-05-07: features-onchain VM emitted STARTED → VALIDATION_*
    # → STOPPED in 9s with no PROCESSING events; took manual diagnosis
    # to determine whether skip-if-exists, dep-check-fail, or
    # date-out-of-range fired). Reason is a closed StrEnum (PreflightSkipReason).
    PREFLIGHT_SKIPPED = "PREFLIGHT_SKIPPED"
    # Upstream fetch lifecycle (data_pipeline_completion Phase 8.3 — no double-fetch)
    # Emitted by every external-data adapter (Tardis, Databento, ODDS_API, Polymarket,
    # FootyStats, The Graph) wrapping a paid upstream call. Migrations and backfills
    # consult these events to skip already-landed day partitions unless --force.
    UPSTREAM_FETCH_STARTED = "UPSTREAM_FETCH_STARTED"
    UPSTREAM_FETCH_COMPLETED = "UPSTREAM_FETCH_COMPLETED"
    UPSTREAM_DOUBLE_FETCH = "UPSTREAM_DOUBLE_FETCH"
    # CI/CD pipeline lifecycle
    QG_PASSED = "QG_PASSED"
    QG_FAILED = "QG_FAILED"
    DEPLOYMENT_STARTED = "DEPLOYMENT_STARTED"
    DEPLOYMENT_PROGRESS = "DEPLOYMENT_PROGRESS"
    DEPLOYMENT_COMPLETED = "DEPLOYMENT_COMPLETED"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    DEPLOYMENT_ROLLED_BACK = "DEPLOYMENT_ROLLED_BACK"
    # Orphan detector (data_pipeline_completion Phase 8.1 — nightly)
    # Emitted by deployments-registry sweeper for any DEPLOYMENT_STARTED whose
    # deployment_id has not emitted COMPLETED/FAILED within 24h.
    DEPLOYMENT_ORPHANED = "DEPLOYMENT_ORPHANED"
    # Debug-mode events (data_pipeline_completion Phase 8.2 — --debug flag)
    # Verbose per-shard / per-row / per-manifest-row diagnostic events. Default
    # off in prod to avoid flooding Pub/Sub; gated behind DEBUG_EVENTS=1 env var
    # or --debug CLI flag.
    DEBUG_SHARD_SCANNED = "DEBUG_SHARD_SCANNED"
    DEBUG_ROW_CLASSIFIED = "DEBUG_ROW_CLASSIFIED"
    DEBUG_MANIFEST_ROW = "DEBUG_MANIFEST_ROW"
    WORKFLOW_TRIGGERED = "WORKFLOW_TRIGGERED"
    VERSION_BUMPED = "VERSION_BUMPED"
    CASCADE_DISPATCHED = "CASCADE_DISPATCHED"
    SIT_STARTED = "SIT_STARTED"
    SIT_PASSED = "SIT_PASSED"
    SIT_FAILED = "SIT_FAILED"
    # Structured error events — emitted by classify_and_emit_error() in UTL
    SERVICE_ERROR = "SERVICE_ERROR"
    ADAPTER_FETCH_FAILED = "ADAPTER_FETCH_FAILED"
    # Circuit breaker — emitted by alerting-service
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    CIRCUIT_HALF_OPEN = "CIRCUIT_HALF_OPEN"
    CIRCUIT_CLOSED = "CIRCUIT_CLOSED"
    # Dead letter — exhausted retries
    DEAD_LETTERED = "DEAD_LETTERED"
    # Agent lifecycle
    AGENT_INVESTIGATION_TRIGGERED = "AGENT_INVESTIGATION_TRIGGERED"
    AGENT_INVESTIGATION_COMPLETED = "AGENT_INVESTIGATION_COMPLETED"
    AGENT_FIX_APPLIED = "AGENT_FIX_APPLIED"
    AGENT_FIX_FAILED = "AGENT_FIX_FAILED"
    # Instruments-live trigger lifecycle (instruments_live_master_2026_05_08
    # Phase A.5 — codifying the typed event surface for Cloud Scheduler /
    # Cloud Run instruments-live triggers across cefi / defi / tradfi /
    # sports / prediction). Per Phase A.4 alerting taxonomy:
    #   TRIGGER_FIRED        — every successful fire (operator visibility +
    #                          missed-fire watchdog input)
    #   TRIGGER_FAILED       — single-trigger fail; alerting threshold N
    #                          consecutive (default 3)
    #   SOURCE_DEGRADED      — primary source returns degraded data; alert
    #                          immediately + auto-switch to secondary
    #   SCHEMA_DRIFT         — adapter output schema diverges from canonical;
    #                          alert immediately + circuit-break (do not write)
    #   T1_AUDIT_DISCREPANCY — T+1 audit detects live≠batch beyond tolerance;
    #                          alert + page on-call
    #   PREFLIGHT_FAILED     — preflight chain check (instruments_live_master
    #                          Phase A.10 helper) detected missing or stale
    #                          upstream entity BEFORE the source call; high-
    #                          value early-warning surface (instant alert,
    #                          single instance, no consecutive threshold).
    #   UPSTREAM_STALE       — independent upstream-staleness monitor (Phase
    #                          A.11) detects an upstream is older than its
    #                          declared threshold BEFORE downstream fires;
    #                          early-warning, single instance.
    INSTRUMENTS_LIVE_TRIGGER_FIRED = "INSTRUMENTS_LIVE_TRIGGER_FIRED"
    INSTRUMENTS_LIVE_TRIGGER_FAILED = "INSTRUMENTS_LIVE_TRIGGER_FAILED"
    INSTRUMENTS_LIVE_SOURCE_DEGRADED = "INSTRUMENTS_LIVE_SOURCE_DEGRADED"
    INSTRUMENTS_LIVE_SCHEMA_DRIFT = "INSTRUMENTS_LIVE_SCHEMA_DRIFT"
    INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY = "INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY"
    INSTRUMENTS_LIVE_PREFLIGHT_FAILED = "INSTRUMENTS_LIVE_PREFLIGHT_FAILED"
    INSTRUMENTS_LIVE_UPSTREAM_STALE = "INSTRUMENTS_LIVE_UPSTREAM_STALE"
    # Live-mode connectivity-gap event family (mdps_streaming_and_backpressure
    # 2026-05-07 Phase 1, "Migrated issue 2026-05-08 — Live data recovery
    # self-detect"). Live WebSocket connectivity loss has no upstream
    # detection/signal/recovery today; gap windows silently lost; downstream
    # can't distinguish "venue quiet" from "MTDS disconnected"; manifests have
    # no LIVE_CONNECTIVITY_GAP rows; auto-backfill unimplemented. Violates
    # Live=Batch principle (batch has 4-state capture taxonomy; live has none
    # for outages). MTDS LiveConnectivityWatchdog wraps each per-venue WS
    # adapter, tracks heartbeats per (venue, data_type), and emits this
    # 3-event family on state transitions:
    #
    #   CONNECTIVITY_GAP_DETECTED  — heartbeat staleness exceeds per-venue
    #                                threshold (UAC VENUE_HEARTBEAT_INTERVAL).
    #                                Carries gap_start, last_received_at,
    #                                classification (WS_DISCONNECT |
    #                                STALE_HEARTBEAT | API_TIMEOUT | UNKNOWN).
    #                                Alerting tier-up via alerting-service
    #                                live rules.
    #   CONNECTIVITY_RECOVERED     — heartbeat resumes after gap. Carries
    #                                gap_end, gap_duration_seconds,
    #                                last_received_at. Triggers auto-backfill
    #                                of the gap window via SOURCE_PRIORITY
    #                                fallback REST source.
    #   CONNECTIVITY_GAP_BACKFILLED — auto-backfill completed for the gap
    #                                window; rows recorded via record_captured
    #                                so manifest reflects honest 4-state
    #                                coverage. Carries rows_backfilled,
    #                                backfill_completed_at.
    #
    # Cross-plan banner: complementary to TICK_STALENESS (MDPS, downstream-
    # detected) — this event family is the upstream-detected counterpart.
    # Operator decision 2026-05-08: keep both.
    CONNECTIVITY_GAP_DETECTED = "CONNECTIVITY_GAP_DETECTED"
    CONNECTIVITY_RECOVERED = "CONNECTIVITY_RECOVERED"
    CONNECTIVITY_GAP_BACKFILLED = "CONNECTIVITY_GAP_BACKFILLED"


# Backward-compat alias — LogLevel is the canonical severity enum (modes.py).
# EventSeverity was previously a standalone StrEnum with INFO/WARNING/ERROR/CRITICAL.
# Now it points to LogLevel which adds DEBUG; existing code that uses
# EventSeverity.INFO etc. continues to work unchanged.
EventSeverity = LogLevel


class ServiceMode(StrEnum):
    BATCH = "batch"
    LIVE = "live"


# ---------------------------------------------------------------------------
# Per-event metadata payloads (the ``details`` dict typed as a model)
# ---------------------------------------------------------------------------


class StartedDetails(BaseModel):
    """Metadata for STARTED events."""

    mode: ServiceMode | None = None
    config_snapshot: dict[str, str | int | float | bool] | None = None


class ValidationStartedDetails(BaseModel):
    validation_type: str = "preflight"
    dependencies: list[str] | None = None


class ValidationCompletedDetails(BaseModel):
    duration_ms: float | None = None
    dependencies_checked: int | None = None
    all_available: bool | None = None


class DataIngestionDetails(BaseModel):
    source: str | None = None
    shard: str | None = None
    date: str | None = None
    venue: str | None = None


class DataIngestionCompletedDetails(DataIngestionDetails):
    rows_loaded: int | None = None
    bytes_read: int | None = None
    duration_ms: float | None = None


class ProcessingStartedDetails(BaseModel):
    shard: str | None = None
    instrument_count: int | None = None


class ProcessingCompletedDetails(BaseModel):
    shard: str | None = None
    rows: int | None = None
    duration_ms: float | None = None
    success: bool | None = None


class DataBroadcastDetails(BaseModel):
    topic: str | None = None
    messages_published: int | None = None
    instrument_key: str | None = None


class PersistenceStartedDetails(BaseModel):
    bucket: str | None = None
    path: str | None = None


class PersistenceCompletedDetails(BaseModel):
    bucket: str | None = None
    path: str | None = None
    files_written: int | None = None
    total_bytes: int | None = None


class StoppedDetails(BaseModel):
    reason: str | None = None
    total_duration_ms: float | None = None


class FailedDetails(BaseModel):
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    stage: str | None = None
    shard: str | None = None
    error_category: str | None = None  # ErrorCategory value
    is_retryable: bool = False
    escalation_level: int = 0  # 0=none, 1=warn, 2=page, 3=incident
    retry_count: int = 0
    first_occurrence_ts: str | None = None  # ISO 8601 timestamp


class AuthFailureDetails(BaseModel):
    auth_type: Annotated[str, Field(description="api_key | oauth | jwt | mtls")] | None = None
    username: str | None = None
    failure_reason: str | None = None
    ip_address: str | None = None
    endpoint: str | None = None
    attempt_count: int | None = None


class UpstreamNotReadyDetails(BaseModel):
    """Details for UPSTREAM_NOT_READY — upstream data missing for a pipeline stage."""

    upstream_dataset: str = Field(description="PATH_REGISTRY key (e.g. raw_tick_data, instruments)")
    upstream_service: str = Field(description="Service that should have written the data")
    date: str = Field(description="Date for which data is missing (YYYY-MM-DD)")
    category: str = Field(default="", description="Market category (cefi, defi, tradfi)")
    message: str = Field(default="", description="Human-readable description of what's missing")
    required: bool = Field(default=True, description="True=blocking, False=advisory")


class ShardIncompleteDetails(BaseModel):
    """Details for SHARD_INCOMPLETE — expected venues missing after write."""

    date: str
    expected: int = Field(description="Number of expected shards/venues")
    written: int = Field(description="Number of actually written shards/venues")
    missing: list[str] = Field(default_factory=list, description="List of missing venue/shard names")


class PreflightSkipReason(StrEnum):
    """Closed taxonomy of reasons a service's preflight short-circuits.
    Every silent skip site (early-exit before processing emits its first
    work event) MUST emit PREFLIGHT_SKIPPED with a reason from this
    enum. New reasons must be added here, NOT free-form strings.
    Reference incident 2026-05-07: features-onchain-defi-backfill VM
    emitted STARTED -> VALIDATION_COMPLETED -> STOPPED in 9 seconds
    with no PROCESSING events; operator could not tell from the event
    stream alone whether (a) skip-if-exists fired (manifest already
    has captured rows), (b) dependency check raised
    DependencyError(fail_on_missing=True), or (c) date was before
    asset_group's earliest valid date. PREFLIGHT_SKIPPED with a
    structured reason resolves each case unambiguously.
    """

    # Manifest already has fresh captured rows for the (date,
    # feature_group) — orchestrator's check_shard_freshness fired.
    # Not an error; expected when re-running a backfill without --force.
    SHARD_ALREADY_FRESH = "SHARD_ALREADY_FRESH"
    # Requested date is before the asset_group's earliest valid date
    # (e.g. defi pre-genesis chain, sports pre-source-coverage-start).
    # Always honest absence; preflight skips without raising.
    DATE_BEFORE_EARLIEST_VALID = "DATE_BEFORE_EARLIEST_VALID"
    # Required upstream service hasn't written its data yet AND
    # fail_on_missing_deps=True. Service short-circuits with
    # DependencyError; downstream stops the pipeline. Emit BEFORE the
    # raise so the silent-skip is visible in the event stream.
    DEPENDENCIES_MISSING_FAIL_FAST = "DEPENDENCIES_MISSING_FAIL_FAST"
    # Required upstream is missing but fail_on_missing_deps=False.
    # Service continues processing with degraded inputs; this skip
    # event is the warning that downstream features may be NaN-heavy.
    DEPENDENCIES_MISSING_CONTINUE = "DEPENDENCIES_MISSING_CONTINUE"
    # Calendar pre-skip (weekend, holiday, half-day, paused-league,
    # known-coverage-gap). Manifest gets record_expected_empty per the
    # reason taxonomy; preflight emits this for visibility.
    CALENDAR_NON_TRADING_DAY = "CALENDAR_NON_TRADING_DAY"
    # Per-VM concurrency: another VM is already processing this shard
    # (per-VM shard isolation lock). Skip without retry.
    CONCURRENT_VM_OWNS_SHARD = "CONCURRENT_VM_OWNS_SHARD"


class PreflightSkippedDetails(BaseModel):
    """Metadata payload for PREFLIGHT_SKIPPED events.

    Every preflight short-circuit MUST emit this structured payload so
    operators can distinguish skip vs failure vs "all good" from the
    event stream alone.
    """

    reason: PreflightSkipReason
    service: str = Field(description="Service whose preflight short-circuited")
    asset_group: str | None = None
    feature_group: str | None = None
    date: str | None = Field(default=None, description="Affected date (YYYY-MM-DD)")
    shard: str | None = Field(default=None, description="Affected shard identifier")
    message: str = Field(default="", description="Human-readable detail")
    # Optional structured context for fail-fast cases — e.g. list of
    # missing upstream services, the earliest-valid date that caused
    # DATE_BEFORE_EARLIEST_VALID, etc.
    missing_dependencies: list[str] = Field(default_factory=list)
    earliest_valid_date: str | None = None


# ---------------------------------------------------------------------------
# Instruments-live trigger metadata payloads (Phase A.5 of
# instruments_live_master_2026_05_08). These payloads carry the metadata
# required by the Phase H.1 alerting rules (alerting_service_live_rules)
# to format Telegram / PagerDuty messages with operator-actionable detail —
# specifically `missing_dependencies` payloads name the exact upstream that
# is blocking, so the operator can act in seconds rather than diagnosing
# from logs. See `codex/04-architecture/alerting-batch-live.md` § Instruments-
# live failure rules (added Phase A.4) for the per-rule routing table.
# ---------------------------------------------------------------------------


class InstrumentsLiveTriggerFiredDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_TRIGGER_FIRED — every successful trigger
    fire emits this so the deployment-UI Scheduled Jobs tab + the missed-fire
    watchdog have a continuous heartbeat record of when each Cloud Scheduler
    / Cloud Run cron last actually ran.
    """

    asset_group: str = Field(description="cefi | defi | tradfi | sports | prediction")
    trigger_name: str = Field(description="UAC trigger taxonomy entry, e.g. sports.fixtures.daily_repoll")
    scheduled_fire_at: datetime = Field(description="Cloud Scheduler's intended fire time")
    actual_fire_at: datetime = Field(description="Time the orchestrator entrypoint actually started")
    correlation_id: str | None = None


class InstrumentsLiveTriggerFailedDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_TRIGGER_FAILED — a single trigger
    invocation completed in failure. Phase H.1 alerting rule (a) escalates
    to Telegram after N consecutive failures of the same trigger_name
    (default 3); the per-trigger circuit-breaker (Phase H.2) flips the
    Cloud Scheduler entry to ``paused`` after the same threshold.
    """

    asset_group: str
    trigger_name: str
    error_type: str = Field(description="Python exception class name, e.g. SourceTimeoutError")
    error_message: str = Field(description="Single-line summary of the failure")
    attempt_number: int = Field(default=1, description="1-based attempt index inside the same fire")
    consecutive_failures: int | None = Field(
        default=None,
        description=(
            "Cumulative consecutive failures for this trigger_name; populated by the alerting rule, not the emitter"
        ),
    )
    correlation_id: str | None = None


class InstrumentsLiveSourceDegradedDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_SOURCE_DEGRADED — primary source for
    the trigger returned degraded data (HTTP 5xx, partial payload, schema-
    valid but suspicious row count, rate-limit exhaustion). Phase H.1 rule
    (b) alerts immediately + the orchestrator auto-switches to the
    secondary source declared in UAC ``SOURCE_PRIORITY``.
    """

    asset_group: str
    trigger_name: str
    primary_source: str = Field(description="Source that degraded, e.g. polygon")
    secondary_source: str | None = Field(
        default=None, description="Fall-back source per UAC SOURCE_PRIORITY; None if no fall-back exists"
    )
    degradation_reason: str = Field(
        description="Closed taxonomy: HTTP_5XX | RATE_LIMIT | PARTIAL_PAYLOAD | SCHEMA_VALID_BUT_SUSPICIOUS | TIMEOUT"
    )
    switched_at: datetime | None = Field(
        default=None, description="When the orchestrator switched to the secondary source"
    )
    correlation_id: str | None = None


class InstrumentsLiveSchemaDriftDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_SCHEMA_DRIFT — the adapter's output
    DataFrame schema diverges from the UAC contract for this trigger's
    output entity-type. Phase H.1 rule (c) alerts immediately + the
    write-gate refuses the parquet write (no garbage-on-garbage downstream).
    """

    asset_group: str
    trigger_name: str
    source: str = Field(description="Source whose response shape drifted")
    entity_type: str = Field(description="e.g. fixtures, ohlcv_15m, market_lifecycle")
    expected_columns: list[str] = Field(description="Columns the UAC contract declares for this entity_type")
    observed_columns: list[str] = Field(description="Columns actually emitted by the adapter")
    missing_columns: list[str] = Field(default_factory=list)
    extra_columns: list[str] = Field(default_factory=list)
    correlation_id: str | None = None


class InstrumentsLiveT1AuditDiscrepancyDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY — the T+1
    retrospective audit (Phase I) detected that live-mode writes for
    ``(asset_group, entity_type, audit_date)`` diverge from what a fresh
    batch run would have produced beyond the per-asset-group tolerance.
    Phase H.1 rule (d) alerts AND pages on-call (single-iteration miss is
    not end-of-world per operator direction; consecutive-day miss is).
    """

    asset_group: str
    entity_type: str
    audit_date: str = Field(description="ISO YYYY-MM-DD — the day under audit")
    live_row_count: int
    batch_row_count: int
    mismatch_keys: list[str] = Field(
        default_factory=list,
        description="Sample of row-key tuples (stringified) that differ between live and batch",
    )
    tolerance_pct: float = Field(description="Per-asset-group divergence tolerance (0.0-1.0)")
    observed_divergence_pct: float
    correlation_id: str | None = None


class MissingDependency(BaseModel):
    """Per-dependency entry in PREFLIGHT_FAILED / UPSTREAM_STALE payloads.

    Names the specific upstream entity that's blocking the downstream
    trigger so the alerting Telegram message body can format
    operator-actionable detail (e.g. ``"sports.weather_cascade [-3h] for
    fixture 1234567 BLOCKED — fixture upstream last seen 36h ago,
    threshold 24h"``). Per CLAUDE.md "Honest absence vs fake placeholders"
    rule, every preflight short-circuit must surface the missing-dep set
    in structured form, not just a free-text reason.
    """

    entity_type: str = Field(
        description="UAC entity_type that's missing or stale (e.g. fixtures, instrument-catalog, lineups)"
    )
    expected_max_age_seconds: int = Field(description="Max staleness tolerance per the preflight DAG SSOT (Phase A.9)")
    actual_age_seconds: int | None = Field(
        default=None,
        description="Observed age at probe time; None if the entity is missing entirely (no row in manifest)",
    )
    last_seen_at: datetime | None = Field(
        default=None,
        description="Most recent ``attempted_at`` for the entity in the upstream manifest; None if never captured",
    )


class InstrumentsLivePreflightFailedDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_PREFLIGHT_FAILED — a downstream trigger
    detected upstream entities that are missing or stale (per the Phase A.9
    preflight DAG SSOT) BEFORE making the source call. Phase H.1 rule (f)
    alerts IMMEDIATELY (single instance, no consecutive threshold) — this
    is the high-value early-warning surface that turns a "live pipeline
    degraded but nobody noticed for 4 hours" silent failure into a
    sub-minute Telegram alert with the missing-dep detail in the message
    body.
    """

    asset_group: str
    trigger_name: str
    missing_dependencies: list[MissingDependency] = Field(
        description=(
            "One entry per upstream entity that failed preflight; each names "
            "which entity, expected vs actual age, and last-seen timestamp. "
            "Must be non-empty: the event fires BECAUSE deps are missing — "
            "an empty list would be a contract violation."
        )
    )
    correlation_id: str | None = None


class InstrumentsLiveUpstreamStaleDetails(BaseModel):
    """Metadata for INSTRUMENTS_LIVE_UPSTREAM_STALE — the independent
    upstream-staleness monitor (Phase A.11) detected an upstream is older
    than its declared staleness threshold BEFORE any downstream trigger
    has fired. Phase H.1 rule (g) alerts IMMEDIATELY — earlier than the
    PREFLIGHT_FAILED path, because the staleness monitor runs on its own
    Cloud Scheduler cron (every 5min per asset_group) regardless of
    whether a downstream trigger is due to fire.
    """

    asset_group: str
    upstream_entity_type: str = Field(
        description="UAC entity_type of the stale upstream (e.g. instrument-catalog, fixtures)"
    )
    last_captured_at: datetime | None = Field(
        default=None, description="Most recent successful ``attempted_at`` in the upstream manifest"
    )
    staleness_threshold_seconds: int = Field(
        description="Per-(asset_group, entity_type) threshold from the preflight DAG SSOT"
    )
    actual_age_seconds: int = Field(description="Observed age at the monitor's probe time")
    downstream_triggers_blocked: list[str] = Field(
        default_factory=list,
        description="Downstream trigger_names that would fail preflight if they fired now (declared in the DAG SSOT)",
    )
    correlation_id: str | None = None


class ConfigChangedDetails(BaseModel):
    config_file: str | None = None
    changed_by: str | None = None
    change_type: Annotated[str, Field(description="update | create | delete")] | None = None
    authorized: bool | None = None
    git_commit_sha: str | None = None
    fields_changed: list[str] | None = None


class SecretAccessedDetails(BaseModel):
    secret_name: str
    caller_identity: str
    operation: Annotated[str, Field(description="access | create | delete | rotate")] = "access"
    success: bool = True
    version: str | None = None


# ---------------------------------------------------------------------------
# CI/CD detail payloads
# ---------------------------------------------------------------------------


class QualityGateDetails(BaseModel):
    """Metadata for QG_PASSED / QG_FAILED events."""

    repo: str
    duration_seconds: float
    tests_passed: int
    tests_failed: int
    coverage_pct: float
    basedpyright_clean: bool = True


class DeploymentDetails(BaseModel):
    """Metadata for DEPLOYMENT_STARTED / COMPLETED / FAILED / ROLLED_BACK events."""

    repo: str
    environment: str  # staging, production
    version: str
    trigger: str  # manual, cascade, hotfix
    rollback_reason: str | None = None  # populated for DEPLOYMENT_ROLLED_BACK


class VersionBumpDetails(BaseModel):
    """Metadata for VERSION_BUMPED events."""

    repo: str
    old_version: str
    new_version: str
    bump_type: str  # major, minor, patch
    is_breaking: bool


class CascadeDispatchDetails(BaseModel):
    """Metadata for CASCADE_DISPATCHED events."""

    source_repo: str
    source_version: str
    target_repos: list[str]
    bump_type: str  # major, minor, patch


# ---------------------------------------------------------------------------
# Agent detail payloads
# ---------------------------------------------------------------------------


class AgentEventDetails(BaseModel):
    """Metadata for AGENT_* lifecycle events."""

    agent_type: str  # conflict-resolution, semver, overnight
    repo: str
    trigger_reason: str
    resolution: str | None = None
    investigation_id: str | None = None
    decision: str | None = None
    reasoning_summary: str | None = None
    files_changed: list[str] | None = None
    commit_sha: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Categorized error detail payload (extends FailedDetails with classification)
# ---------------------------------------------------------------------------


class CategorizedErrorDetails(BaseModel):
    """Structured error details with category, retryability, and escalation level.

    Used alongside FailedDetails when a richer error classification is needed.
    """

    error_category: str  # ErrorCategory value (infrastructure, application, data, execution, compliance)
    error_type: str
    error_message: str
    is_retryable: bool
    escalation_level: str  # INFO, WARN, PAGE


# ---------------------------------------------------------------------------
# Event envelope — what GCSEventSink writes (one JSON line in JSONL)
# ---------------------------------------------------------------------------


class EventMetadata(BaseModel):
    """Inner metadata dict embedded in every event."""

    timestamp: datetime
    service_name: str
    severity: EventSeverity = EventSeverity.INFO
    details: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
    client_id: str | None = Field(default=None, json_schema_extra={"pii": True})
    correlation_id: str | None = None


class LifecycleEventEnvelope(BaseModel):
    """Top-level shape of every event written to GCS JSONL or published to Pub/Sub.

    GCS path: ```events/{service_name}/{YYYY-MM-DD}/events.jsonl```
    """

    event: LifecycleEventType
    service: str
    timestamp: datetime
    metadata: EventMetadata


class PubSubLifecycleEventMessage(BaseModel):
    """Pub/Sub variant — no top-level timestamp (only in metadata)."""

    event: LifecycleEventType
    service: str
    metadata: EventMetadata


# ---------------------------------------------------------------------------
# Typed convenience wrappers for well-known event types
# ---------------------------------------------------------------------------


class StartedEvent(BaseModel):
    event: Literal[LifecycleEventType.STARTED] = LifecycleEventType.STARTED
    service: str
    timestamp: datetime
    details: StartedDetails = Field(default_factory=StartedDetails)


class PreflightSkippedEvent(BaseModel):
    event: Literal[LifecycleEventType.PREFLIGHT_SKIPPED] = LifecycleEventType.PREFLIGHT_SKIPPED
    service: str
    timestamp: datetime
    details: PreflightSkippedDetails


class FailedEvent(BaseModel):
    event: Literal[LifecycleEventType.FAILED] = LifecycleEventType.FAILED
    service: str
    timestamp: datetime
    details: FailedDetails = Field(default_factory=FailedDetails)


class AuthFailureEvent(BaseModel):
    event: Literal[LifecycleEventType.AUTH_FAILURE] = LifecycleEventType.AUTH_FAILURE
    service: str
    timestamp: datetime
    details: AuthFailureDetails


class ConfigChangedEvent(BaseModel):
    event: Literal[LifecycleEventType.CONFIG_CHANGED] = LifecycleEventType.CONFIG_CHANGED
    service: str
    timestamp: datetime
    details: ConfigChangedDetails


class SecretAccessedEvent(BaseModel):
    event: Literal[LifecycleEventType.SECRET_ACCESSED] = LifecycleEventType.SECRET_ACCESSED
    service: str
    timestamp: datetime
    details: SecretAccessedDetails


# ---------------------------------------------------------------------------
# Instruments-live trigger typed convenience wrappers (Phase A.5)
# ---------------------------------------------------------------------------


class InstrumentsLiveTriggerFiredEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FIRED] = (
        LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FIRED
    )
    service: str
    timestamp: datetime
    details: InstrumentsLiveTriggerFiredDetails


class InstrumentsLiveTriggerFailedEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FAILED] = (
        LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FAILED
    )
    service: str
    timestamp: datetime
    details: InstrumentsLiveTriggerFailedDetails


class InstrumentsLiveSourceDegradedEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_SOURCE_DEGRADED] = (
        LifecycleEventType.INSTRUMENTS_LIVE_SOURCE_DEGRADED
    )
    service: str
    timestamp: datetime
    details: InstrumentsLiveSourceDegradedDetails


class InstrumentsLiveSchemaDriftEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_SCHEMA_DRIFT] = LifecycleEventType.INSTRUMENTS_LIVE_SCHEMA_DRIFT
    service: str
    timestamp: datetime
    details: InstrumentsLiveSchemaDriftDetails


class InstrumentsLiveT1AuditDiscrepancyEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY] = (
        LifecycleEventType.INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY
    )
    service: str
    timestamp: datetime
    details: InstrumentsLiveT1AuditDiscrepancyDetails


class InstrumentsLivePreflightFailedEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_PREFLIGHT_FAILED] = (
        LifecycleEventType.INSTRUMENTS_LIVE_PREFLIGHT_FAILED
    )
    service: str
    timestamp: datetime
    details: InstrumentsLivePreflightFailedDetails


class InstrumentsLiveUpstreamStaleEvent(BaseModel):
    event: Literal[LifecycleEventType.INSTRUMENTS_LIVE_UPSTREAM_STALE] = (
        LifecycleEventType.INSTRUMENTS_LIVE_UPSTREAM_STALE
    )
    service: str
    timestamp: datetime
    details: InstrumentsLiveUpstreamStaleDetails


# ---------------------------------------------------------------------------
# Live-mode connectivity-gap event family (mdps_streaming_and_backpressure
# 2026-05-07 Phase 1 — "Migrated issue 2026-05-08 — Live data recovery
# self-detect"). MTDS LiveConnectivityWatchdog emits these on state
# transitions per (venue, data_type) heartbeat tracking.
# ---------------------------------------------------------------------------


class ConnectivityGapDetectedDetails(BaseModel):
    """Metadata for CONNECTIVITY_GAP_DETECTED.

    Emitted by MTDS LiveConnectivityWatchdog when (venue, data_type)
    heartbeat staleness exceeds the per-venue threshold (UAC
    VENUE_HEARTBEAT_INTERVAL — empirical 99th percentile per venue).
    """

    venue: str
    data_type: str
    gap_start: datetime
    last_received_at: datetime
    # Closed-set classification of the gap source. WS_DISCONNECT = explicit
    # WebSocket close; STALE_HEARTBEAT = no message for > threshold;
    # API_TIMEOUT = REST fallback timed out; UNKNOWN = other.
    classification: Literal["WS_DISCONNECT", "STALE_HEARTBEAT", "API_TIMEOUT", "UNKNOWN"]
    # Optional context: how many messages received during the gap window
    # (typically 0 — set to a non-zero value if the gap was a heartbeat-rate
    # drop rather than a complete blackout).
    message_count_during_gap: int = 0


class ConnectivityRecoveredDetails(BaseModel):
    """Metadata for CONNECTIVITY_RECOVERED.

    Emitted by MTDS LiveConnectivityWatchdog when a (venue, data_type) pair
    that was previously in GAP state receives a heartbeat. Triggers
    auto-backfill of the gap window via SOURCE_PRIORITY fallback REST source.
    """

    venue: str
    data_type: str
    gap_start: datetime
    gap_end: datetime
    gap_duration_seconds: float
    last_received_at: datetime


class ConnectivityGapBackfilledDetails(BaseModel):
    """Metadata for CONNECTIVITY_GAP_BACKFILLED.

    Emitted by MTDS auto-backfill loop after the gap window is filled via
    REST batch fetch. Per CLAUDE.md "Manifest concurrency principle":
    read-once + per-date freshness check + write-time CAS. Each filled row
    is recorded via ManifestWriter.record_captured so the manifest reflects
    honest 4-state coverage.
    """

    venue: str
    data_type: str
    gap_start: datetime
    gap_end: datetime
    backfill_completed_at: datetime
    rows_backfilled: int


class ConnectivityGapDetectedEvent(BaseModel):
    event: Literal[LifecycleEventType.CONNECTIVITY_GAP_DETECTED] = LifecycleEventType.CONNECTIVITY_GAP_DETECTED
    service: str
    timestamp: datetime
    details: ConnectivityGapDetectedDetails


class ConnectivityRecoveredEvent(BaseModel):
    event: Literal[LifecycleEventType.CONNECTIVITY_RECOVERED] = LifecycleEventType.CONNECTIVITY_RECOVERED
    service: str
    timestamp: datetime
    details: ConnectivityRecoveredDetails


class ConnectivityGapBackfilledEvent(BaseModel):
    event: Literal[LifecycleEventType.CONNECTIVITY_GAP_BACKFILLED] = LifecycleEventType.CONNECTIVITY_GAP_BACKFILLED
    service: str
    timestamp: datetime
    details: ConnectivityGapBackfilledDetails


# ---------------------------------------------------------------------------
# Resource metrics snapshot — shard-aware monitoring labels
# ---------------------------------------------------------------------------


class ResourceMetricsSnapshot(BaseModel):
    """System resource metrics for monitoring."""

    service_name: str
    timestamp: datetime
    cpu_usage_pct: float | None = None
    memory_rss_bytes: int | None = None
    memory_rss_pct: float | None = None
    active_connections: int | None = None
    queue_depth: int | None = None
    shard_id: str | None = Field(default=None, description="batch shard ID if applicable")
    venue_id: str | None = Field(default=None, description="live venue ID if applicable")
    strategy_id: str | None = Field(default=None, description="live strategy ID if applicable")
