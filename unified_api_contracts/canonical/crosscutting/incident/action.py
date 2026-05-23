"""AgentActionEvent — structured record of every Layer-0 / Layer-1.5 / manual recovery action.

Emitted by Layer-0 deterministic scripts (``deployment-service/scripts/recovery/``)
+ Layer-1.5 LLM wrapper (``llm_invoke_layer0.py``) + Layer-M operator manual
actions (DART Safety Ops tab). The alerting-service Incident Gateway state
machine consumes these to update incident state.

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionType(StrEnum):
    """Closed set of 10 Layer-0 recovery actions.

    Adding a new action requires (1) appending here, (2) registering in
    ``unified_trading_library.recovery.RecoveryScriptRegistry``, (3) shipping
    the script at ``deployment-service/scripts/recovery/<action_type>.py``,
    (4) writing the operator runbook at
    ``codex/15-runbooks/incidents/RB-<class>-<NNN>.md``.
    """

    RESTART_SERVICE = "restart_service"
    RESTART_CONTAINER = "restart_container"
    REDEPLOY_KNOWN_GOOD = "redeploy_known_good"
    RESIZE_MACHINE_AFTER_OOM = "resize_machine_after_oom"
    FAILOVER_FEED = "failover_feed"
    PAUSE_STRATEGY = "pause_strategy"
    CANCEL_OPEN_ORDERS = "cancel_open_orders"
    DISABLE_VENUE = "disable_venue"
    ENTER_SAFE_MODE = "enter_safe_mode"
    ENTER_READONLY_RECON_MODE = "enter_readonly_recon_mode"


class ActionStatus(StrEnum):
    """Lifecycle status of a single AgentActionEvent."""

    STARTED = "STARTED"
    """Action invocation has begun; no result yet."""
    SUCCEEDED = "SUCCEEDED"
    """Action returned non-error exit + post-action state matches expected."""
    FAILED = "FAILED"
    """Action returned error OR post-action state did not match expected.
    Layer-1.5 LLM backup actuator may pick up; otherwise escalates."""
    BLOCKED_BY_LOOP_DETECTOR = "BLOCKED_BY_LOOP_DETECTOR"
    """RepeatedRepairLoopDetector returned LoopDetected — 3+ identical
    actions within sliding window. Bails out without executing + escalates
    to SEV0."""
    DRY_RUN = "DRY_RUN"
    """Action ran in --dry-run mode; no side effects; plan output captured."""


class ActionProvenance(StrEnum):
    """Closed set — who triggered this action."""

    AUTOMATIC = "AUTOMATIC"
    """Layer-0 deterministic script fired from a detector trigger."""
    MANUAL_OPERATOR = "MANUAL_OPERATOR"
    """Operator clicked a Safety Ops tab button (typed-confirm-string required)."""
    LLM_LAYER15 = "LLM_LAYER15"
    """Layer-1.5 LLM recovery-audit-signoff agent invoked Layer-0 script as
    backup actuator via ``llm_invoke_layer0.py`` closed-set wrapper."""
    GATEWAY_DISPUTE = "GATEWAY_DISPUTE"
    """Incident Gateway state machine fired the action because the LLM
    recovery-audit verdict was DISPUTE_AUTOMATED_ACTION."""
    BREAKER_AUTO = "BREAKER_AUTO"
    """Circuit-breaker tripped from threshold breach (e.g. failure_rate > 60%)."""


class RecoveryVerificationResult(BaseModel):
    """5-tuple of booleans recorded on RECOVERY_VERIFICATION_STARTED transition.

    All 5 must be True for the state machine to transition to
    RECOVERY_CONFIRMED. Any False → RECOVERY_UNCERTAIN → SAFE_MODE_ACTIVE.

    Per-service callbacks register at gateway startup and populate one or
    more of these fields based on their scope (execution-service populates
    positions_reconciled + orders_reconciled; mtds populates market_data_fresh;
    strategy-service populates strategy_state_restored; etc).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    health_checks_passed: bool
    positions_reconciled: bool
    orders_reconciled: bool
    market_data_fresh: bool
    strategy_state_restored: bool
    """True OR strategy is intentionally paused — both are acceptable."""

    failure_reasons: tuple[str, ...] = Field(default=())
    """Free-text reasons populated when any boolean is False. Empty when all 5 True."""

    def all_passed(self) -> bool:
        """True iff all 5 recovery booleans are True."""
        return (
            self.health_checks_passed
            and self.positions_reconciled
            and self.orders_reconciled
            and self.market_data_fresh
            and self.strategy_state_restored
        )


class AgentActionEvent(BaseModel):
    """Structured record of a single recovery action.

    Published to PubSub topic ``agent-recovery-actions`` for the LLM
    recovery-audit-signoff agent + persisted to GCS at
    ``incidents/{YYYY-MM-DD}/{incident_key}/actions/{event_id}.json``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    """UUID for this single action event."""
    parent_incident_key: str
    """Stable dedup key linking to the parent IncidentEnvelope."""
    timestamp: datetime
    """tz-aware UTC."""
    agent_id: str
    """e.g. 'agent-recovery-controller' (Layer-0), 'recovery-audit-signoff'
    (Layer-1.5), 'operator:ikenna@odum-research.com' (manual)."""
    action_type: ActionType
    action_status: ActionStatus
    provenance: ActionProvenance
    runbook_id: str
    """e.g. 'RB-INFRA-001' — links to the operator runbook in
    ``codex/15-runbooks/incidents/``."""
    pre_action_state: dict[str, str | bool | int | float | None] = Field(default_factory=dict)
    """Free-form snapshot of service state BEFORE action."""
    post_action_state: dict[str, str | bool | int | float | None] = Field(default_factory=dict)
    """Free-form snapshot AFTER action."""
    recovery_verification: RecoveryVerificationResult | None = None
    """5-tuple result, populated when state transitions through
    RECOVERY_VERIFICATION_STARTED. None during STARTED status."""
    config_hash: str
    """git rev-parse HEAD of unified-trading-pm + service repo at action time."""
    code_version: str
    """Image digest of running container OR git sha for VM-hosted services."""
    failure_reason: str | None = None
    """Populated when action_status=FAILED."""
    scope: dict[str, str] = Field(default_factory=dict)
    """Scope of the action — keys: service, venue, strategy, instrument_id."""

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes — UTC required."""
        if v.tzinfo is None:
            raise ValueError("timestamp must be tz-aware UTC")
        return v

    @field_validator("runbook_id")
    @classmethod
    def _runbook_id_shape(cls, v: str) -> str:
        """Runbook IDs follow ``RB-<CLASS>-<NNN>`` shape."""
        if not v.startswith("RB-"):
            raise ValueError(f"runbook_id must start with 'RB-'; got {v!r}")
        return v
