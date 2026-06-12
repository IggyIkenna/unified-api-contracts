"""Circuit-breaker seed registry — ``ML_DIRECTIONAL_CONTINUOUS`` archetype.

4 breakers covering the CeFi ML directional signal family: position-limit,
P&L drawdown, signal-staleness, and model-drift.  Locked design parameters
(per ``cefi_ml_directional_continuous_live_2026_06_20.md``):

- ``position_cap_usd = 10000`` per venue
- ``kill_switch_drawdown_pct = 5`` (500 BPS daily)
- ``kill_switch_position_breach_pct = 20`` (position > 120% of cap → 1.2 ratio)
- ``kill_switch_scope = ARCHETYPE`` (CeFi-ML trip does NOT halt DeFi)

Reviewers reject changes that:

- Add a :class:`BreakerConfig` without a matching :class:`BreakerRecoveryRule`.
- Override away from :data:`BREAKER_RECOVERY_DEFAULTS` without a written
  rationale in the description.
- Add a new :class:`CircuitBreakerId` here without first appending to the
  closed-set enum in
  ``unified_api_contracts/canonical/crosscutting/circuit_breaker.py``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from ...canonical.crosscutting.alerting.codes import AlertSeverity
from ...canonical.crosscutting.alerting.thresholds import ThresholdUnit
from ...canonical.crosscutting.circuit_breaker import (
    BreakerAction,
    BreakerConfig,
    BreakerRecoveryMode,
    BreakerRecoveryRule,
    BreakerScope,
    BreakerTrigger,
    CircuitBreakerId,
)

BREAKERS: Final[tuple[BreakerConfig, ...]] = (
    BreakerConfig(
        breaker_id=CircuitBreakerId.POSITION_LIMIT_EXCEEDED,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ML_DIRECTIONAL_CONTINUOUS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.POSITION_LIMIT_EXCEEDED,
            threshold_value=Decimal("1.2"),
            threshold_unit=ThresholdUnit.RATIO,
        ),
        action=BreakerAction.CANCEL_OPEN,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Per-venue gross position exceeds 120% of $10k cap "
            "(kill_switch_position_breach_pct=20). CANCEL_OPEN → MANUAL_UNKILL "
            "— cancelled orders don't self-restore."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ML_DIRECTIONAL_CONTINUOUS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            threshold_value=Decimal("500"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
        ),
        action=BreakerAction.KILL_ALL,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Daily drawdown >= 500 BPS (kill_switch_drawdown_pct=5) — full "
            "unwind. KILL_ALL → MANUAL_UNKILL: operator sign-off required before "
            "re-engaging the ML signal on live capital."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.ML_SIGNAL_STALENESS_SECONDS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ML_DIRECTIONAL_CONTINUOUS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.ML_SIGNAL_STALENESS_SECONDS,
            threshold_value=Decimal("86400"),
            threshold_unit=ThresholdUnit.SECONDS,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=1800,
        recovery_mode=BreakerRecoveryMode.AUTO_COOLDOWN,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "ML inference signal stale >= 24h (hard budget per locked design). "
            "BLOCK_NEW: no new CeFi-ML directional trades until features refresh. "
            "AUTO_COOLDOWN: re-evaluates every 30min; resumes when fresh signals "
            "arrive. Warn at 4h / critical at 12h handled by alerting-service."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.ML_MODEL_DRIFT_ACCURACY_DROP,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ML_DIRECTIONAL_CONTINUOUS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.ML_MODEL_DRIFT_ACCURACY_DROP,
            threshold_value=Decimal("0.05"),
            threshold_unit=ThresholdUnit.RATIO,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=3600,
        recovery_mode=BreakerRecoveryMode.AUTO_COOLDOWN,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Rolling model accuracy dropped >= 5% from baseline over 14-day "
            "window (matches InferenceConfig.drift_accuracy_drop_threshold). "
            "Armed by DriftMonitor via MODEL_DRIFT_DETECTED event. BLOCK_NEW + "
            "AUTO_COOLDOWN: re-evaluates after 1h (time for overnight retrain + "
            "hot-reload). Existing positions held; only new signal entry blocked."
        ),
    ),
)

RECOVERY_RULES: Final[tuple[BreakerRecoveryRule, ...]] = (
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.POSITION_LIMIT_EXCEEDED,
        guard_description=(
            "Operator confirms per-venue position resized below $10k cap across all 3 venues (OKX + Binance + Bybit)."
        ),
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
        guard_description=(
            "Operator confirms full unwind complete + daily P&L loss < 500 BPS "
            "over the trailing window; reviews root cause before re-engaging."
        ),
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.ML_SIGNAL_STALENESS_SECONDS,
        guard_description=(
            "ML inference pipeline emits a fresh prediction within staleness "
            "budget (feature age < 6h soft / 24h hard) for >= 2 consecutive "
            "inference cycles."
        ),
        retry_policy="exponential",
        auto_disarm_after_seconds=1800,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.ML_MODEL_DRIFT_ACCURACY_DROP,
        guard_description=(
            "Model retrained + hot-reloaded; rolling accuracy >= baseline - 2% "
            "(within 3% of baseline) over the next inference window."
        ),
        retry_policy="linear",
        auto_disarm_after_seconds=3600,
    ),
)
