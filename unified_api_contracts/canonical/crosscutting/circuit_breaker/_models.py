"""Circuit breaker Pydantic models — configurations, triggers and events."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..alerting.codes import AlertCode, AlertSeverity
from ..alerting.thresholds import ThresholdUnit
from ._enums import (
    BREAKER_RECOVERY_DEFAULTS,
    BreakerAction,
    BreakerRecoveryMode,
    BreakerScope,
    CircuitBreakerId,
)


class BreakerTrigger(BaseModel):
    """Typed condition union — what the breaker watches.

    Captures the numeric threshold (value + unit) plus optional time-window
    semantics (consecutive-count + window-seconds). Concrete trigger semantics
    are implementation-side (strategy-service/risk consumes these and
    evaluates against live metrics).

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.alerting.AlertThreshold` —
    breaker triggers use the same :class:`ThresholdUnit` vocabulary so the
    unit-disambiguation rules (bps vs ratio vs USD) carry through. Where a
    breaker maps 1:1 to an existing :class:`AlertThreshold` entry, the
    registry seed should reuse the threshold key rather than duplicate the
    value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trigger_type: CircuitBreakerId
    """Which :class:`CircuitBreakerId` this trigger evaluates."""

    threshold_value: Decimal
    """Numeric threshold the metric must cross to fire."""

    threshold_unit: ThresholdUnit
    """Unit of the threshold value. Mirrors
    :class:`unified_api_contracts.alerting.ThresholdUnit` vocabulary so
    consumers normalise observed values to the same unit."""

    window_seconds: int | None = Field(default=None)
    """Optional rolling-window length for time-window-based triggers
    (e.g. ``REJECT_RATE_BPS`` over a 60s window). ``None`` = instantaneous."""

    consecutive_count: int | None = Field(default=None)
    """Optional consecutive-evaluation count required before firing
    (e.g. trigger fires only after 3 consecutive readings above threshold).
    ``None`` = single-evaluation fire."""


class BreakerConfig(BaseModel):
    """A single breaker's full configuration.

    Each entry in the per-archetype registry seed (under
    ``unified_api_contracts/registry/circuit_breakers/<archetype>.py``) is a
    :class:`BreakerConfig` instance. Reviewers cross-check that every
    :class:`CircuitBreakerId` listed for an archetype has both a config here
    AND a recovery rule in :class:`BreakerRecoveryRule`.

    Validator semantics
    ~~~~~~~~~~~~~~~~~~~

    - If ``recovery_mode is None`` at construction, the default from
      :data:`BREAKER_RECOVERY_DEFAULTS` is filled in via :class:`model_validator`.
    - If ``recovery_mode == BreakerRecoveryMode.AUTO_COOLDOWN``,
      ``cooldown_seconds`` MUST be a positive int.
    - If ``recovery_mode == BreakerRecoveryMode.MANUAL_UNKILL``,
      ``cooldown_seconds`` MUST be ``None``.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with the cross-plan seam declared in
    ``risk_simulations_limits_alerting_2026_05_10.md:44-87``: this
    :class:`BreakerConfig` ships from DR plan Phase 1.A; the risk plan
    Phase 1.F flips on the same UAC commit since both depend on
    :class:`BreakerRecoveryMode` + :data:`BREAKER_RECOVERY_DEFAULTS` being
    available in UAC.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    breaker_id: CircuitBreakerId
    scope: BreakerScope
    applies_to: str = Field(default="*")
    """Scope-key (e.g. venue name when scope=PER_VENUE; archetype string when
    scope=PER_ARCHETYPE). ``"*"`` means scope-wide (every member of the scope)."""

    trigger: BreakerTrigger
    action: BreakerAction
    recovery_mode: BreakerRecoveryMode | None = Field(default=None)
    """Recovery mode; if ``None``, falls back to
    :data:`BREAKER_RECOVERY_DEFAULTS[action]` at validation time."""

    cooldown_seconds: int | None = Field(default=None)
    """Required when ``recovery_mode == AUTO_COOLDOWN``; MUST be ``None`` when
    ``recovery_mode == MANUAL_UNKILL``."""

    alerting_severity: AlertSeverity
    """Severity tier for the ``BREAKER_ARMED`` / ``BREAKER_DISARMED`` alert
    rule. Mirrors :class:`AlertSeverity` 4-set."""

    description: str = Field(default="")

    @model_validator(mode="after")
    def _fill_recovery_default_and_validate(self) -> BreakerConfig:
        # Fill default recovery mode if not set
        effective_recovery = self.recovery_mode
        if effective_recovery is None:
            effective_recovery = BREAKER_RECOVERY_DEFAULTS[self.action]
            object.__setattr__(self, "recovery_mode", effective_recovery)
        # Validate cooldown_seconds consistency with recovery_mode
        if effective_recovery == BreakerRecoveryMode.AUTO_COOLDOWN:
            if self.cooldown_seconds is None or self.cooldown_seconds <= 0:
                raise ValueError(
                    f"BreakerConfig({self.breaker_id.value}): cooldown_seconds REQUIRED "
                    f"and > 0 when recovery_mode=AUTO_COOLDOWN; got {self.cooldown_seconds!r}"
                )
        else:  # MANUAL_UNKILL
            if self.cooldown_seconds is not None:
                raise ValueError(
                    f"BreakerConfig({self.breaker_id.value}): cooldown_seconds MUST be None "
                    f"when recovery_mode=MANUAL_UNKILL; got {self.cooldown_seconds!r}"
                )
        return self


class BreakerRecoveryRule(BaseModel):
    """Per-breaker recovery semantics — guard predicate + retry policy.

    One :class:`BreakerRecoveryRule` per :class:`CircuitBreakerId` is required
    in the per-archetype registry. The rule encodes:

    - What named guard the breaker must observe green before disarming
      (e.g. ``"oracle deviation < 5 sigma for 5min"``).
    - Whether retry escalates (exponential / linear / none).
    - Whether the breaker auto-disarms after a hard timeout regardless of
      guard state, or stays armed until manual action.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :data:`BREAKER_RECOVERY_DEFAULTS` — the rule's
    ``auto_disarm_after_seconds`` semantics are gated by the
    :class:`BreakerRecoveryMode` from the matching :class:`BreakerConfig`:
    ``MANUAL_UNKILL`` rules ignore ``auto_disarm_after_seconds`` (always
    ``None``); ``AUTO_COOLDOWN`` rules MUST declare a positive value matching
    ``BreakerConfig.cooldown_seconds``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    breaker_id: CircuitBreakerId
    guard_description: str
    """One-line description of the green-condition guard the breaker checks
    before disarming. Operator-readable; not parsed by code."""

    retry_policy: str = Field(default="none")
    """``"exponential"`` / ``"linear"`` / ``"none"`` — retry semantics if the
    breaker tries to disarm and the guard is still red."""

    auto_disarm_after_seconds: int | None = Field(default=None)
    """If set, breaker auto-disarms after this many seconds regardless of
    guard state. ``None`` = breaker stays armed indefinitely (manual disarm
    only) — typical for ``MANUAL_UNKILL`` mode."""


class BreakerFiredEvent(BaseModel):
    """Emitted when a circuit breaker arms (``state="armed"``) or disarms
    (``state="disarmed"``).

    Mirrors :class:`unified_api_contracts.canonical.crosscutting.risk_rule.RiskRuleFiredEvent`.
    Frozen + extra=forbid.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    breaker_id: CircuitBreakerId
    scope: BreakerScope
    applies_to: str
    """Archetype name, venue slug, or ``"*"`` for global scope."""
    action: BreakerAction
    recovery_mode: BreakerRecoveryMode
    cooldown_seconds: int | None
    alerting_severity: AlertSeverity
    alert_code: AlertCode
    fired_at: datetime
    state: Literal["armed", "disarmed"]
    metadata: dict[str, str] = Field(default_factory=dict)


__all__ = [
    "BreakerConfig",
    "BreakerFiredEvent",
    "BreakerRecoveryRule",
    "BreakerTrigger",
]
