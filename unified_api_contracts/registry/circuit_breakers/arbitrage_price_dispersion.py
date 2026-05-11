"""Circuit-breaker seed registry — ``ARBITRAGE_PRICE_DISPERSION`` archetype.

10 breakers covering funding-arb-family risks: funding flip / basis inversion /
spread blowout / cross-venue divergence / inventory imbalance / fill latency /
reject rate / PnL variance / hedge gap / clock skew. Plus a shared
position-limit + venue-outage entry inherited from the cross-archetype set.

Reviewers reject changes that:

- Add a :class:`BreakerConfig` without matching :class:`BreakerRecoveryRule`.
- Override away from :data:`BREAKER_RECOVERY_DEFAULTS` without rationale.
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
    BreakerRecoveryRule,
    BreakerScope,
    BreakerTrigger,
    CircuitBreakerId,
)

BREAKERS: Final[tuple[BreakerConfig, ...]] = (
    BreakerConfig(
        breaker_id=CircuitBreakerId.FUNDING_RATE_FLIP_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.FUNDING_RATE_FLIP_BPS,
            threshold_value=Decimal("50"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
            window_seconds=28800,
        ),
        action=BreakerAction.SCALE_DOWN,
        cooldown_seconds=1800,
        alerting_severity=AlertSeverity.HIGH,
        description="Funding rate moves >= 50bps adversely in one funding window → halve position.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.BASIS_INVERSION_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.BASIS_INVERSION_BPS,
            threshold_value=Decimal("80"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
            window_seconds=300,
        ),
        action=BreakerAction.SCALE_DOWN,
        cooldown_seconds=900,
        alerting_severity=AlertSeverity.HIGH,
        description="Cash-perp basis inverts or moves >= 80bps adverse over 5min → unwind half.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
        scope=BreakerScope.PER_VENUE,
        applies_to="*",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
            threshold_value=Decimal("30"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
            window_seconds=60,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=180,
        alerting_severity=AlertSeverity.WARN,
        description="Quoted spread >= 30bps for 60s → block new orders on that venue.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.CROSS_VENUE_DIVERGENCE_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.CROSS_VENUE_DIVERGENCE_BPS,
            threshold_value=Decimal("40"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
            window_seconds=120,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=300,
        alerting_severity=AlertSeverity.HIGH,
        description="Same-instrument mid diverges >= 40bps across hedge venues → block new entries.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.INVENTORY_IMBALANCE_RATIO,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.INVENTORY_IMBALANCE_RATIO,
            threshold_value=Decimal("0.20"),
            threshold_unit=ThresholdUnit.RATIO,
        ),
        action=BreakerAction.CANCEL_OPEN,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Cross-venue inventory imbalance > 20% notional → cancel open hedges "
            "(MANUAL_UNKILL — operator confirms hedge rebalance)."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.FILL_LATENCY_BREACH_MS,
        scope=BreakerScope.PER_VENUE,
        applies_to="*",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.FILL_LATENCY_BREACH_MS,
            threshold_value=Decimal("2000"),
            threshold_unit=ThresholdUnit.MILLISECONDS,
            window_seconds=300,
            consecutive_count=10,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=300,
        alerting_severity=AlertSeverity.HIGH,
        description="Fill latency p99 >= 2000ms over 5min (10 samples) → block new orders.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.REJECT_RATE_BPS,
        scope=BreakerScope.PER_VENUE,
        applies_to="*",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.REJECT_RATE_BPS,
            threshold_value=Decimal("500"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
            window_seconds=300,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=180,
        alerting_severity=AlertSeverity.HIGH,
        description="Reject rate >= 5.00% over rolling 5min → pause new orders.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.PNL_VARIANCE_SIGMA,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.PNL_VARIANCE_SIGMA,
            threshold_value=Decimal("3.0"),
            threshold_unit=ThresholdUnit.RATIO,
        ),
        action=BreakerAction.SCALE_DOWN,
        cooldown_seconds=3600,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Realised PnL >= 3 sigma vs backtest expectation → halve position; auto-recover after 1h within tolerance."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.HEDGE_GAP_NOTIONAL_USD,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.HEDGE_GAP_NOTIONAL_USD,
            threshold_value=Decimal("100000"),
            threshold_unit=ThresholdUnit.USD,
        ),
        action=BreakerAction.KILL_ALL,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Unhedged delta >= $100k notional → full unwind. KILL_ALL → MANUAL_UNKILL "
            "(operator confirms delta-neutral state before re-engaging)."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.CLOCK_SKEW_MS,
        scope=BreakerScope.PER_VENUE,
        applies_to="*",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.CLOCK_SKEW_MS,
            threshold_value=Decimal("500"),
            threshold_unit=ThresholdUnit.MILLISECONDS,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=120,
        alerting_severity=AlertSeverity.WARN,
        description="Local vs venue ts skew >= 500ms → pause new orders until NTP resync.",
    ),
)

RECOVERY_RULES: Final[tuple[BreakerRecoveryRule, ...]] = (
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.FUNDING_RATE_FLIP_BPS,
        guard_description="Funding rate within 20bps of pre-flip level for full funding window.",
        retry_policy="linear",
        auto_disarm_after_seconds=1800,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.BASIS_INVERSION_BPS,
        guard_description="Basis returns to expected sign + |basis - mean| < 40bps for 10min.",
        retry_policy="linear",
        auto_disarm_after_seconds=900,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
        guard_description="Quoted spread < 15bps for 3min sustained.",
        retry_policy="linear",
        auto_disarm_after_seconds=180,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.CROSS_VENUE_DIVERGENCE_BPS,
        guard_description="Cross-venue mid converges within 10bps for 5min.",
        retry_policy="exponential",
        auto_disarm_after_seconds=300,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.INVENTORY_IMBALANCE_RATIO,
        guard_description="Operator confirms hedge rebalanced within 5% across venues.",
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.FILL_LATENCY_BREACH_MS,
        guard_description="Fill latency p99 < 800ms over 5min for 3 consecutive windows.",
        retry_policy="exponential",
        auto_disarm_after_seconds=300,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.REJECT_RATE_BPS,
        guard_description="Reject rate < 100bps over rolling 5min.",
        retry_policy="exponential",
        auto_disarm_after_seconds=180,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.PNL_VARIANCE_SIGMA,
        guard_description="Realised PnL within 1.5 sigma of backtest for 1h.",
        retry_policy="linear",
        auto_disarm_after_seconds=3600,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.HEDGE_GAP_NOTIONAL_USD,
        guard_description="Operator confirms delta-neutral state across venues; hedge gap < $10k.",
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.CLOCK_SKEW_MS,
        guard_description="Local clock skew < 100ms after NTP resync.",
        retry_policy="linear",
        auto_disarm_after_seconds=120,
    ),
)
