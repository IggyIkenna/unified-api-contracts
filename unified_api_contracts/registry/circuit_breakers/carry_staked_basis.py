"""Circuit-breaker seed registry — ``CARRY_STAKED_BASIS`` archetype.

10 breakers covering oracle / RPC / gas / position / drawdown / liquidation /
venue / custody / manifest / batch-live for the cutover LST-leverage strategy.
Each breaker references the canonical :class:`CircuitBreakerId` + carries its
own :class:`BreakerConfig` + matching :class:`BreakerRecoveryRule`.

Reviewers reject changes that:

- Add a :class:`BreakerConfig` here without a matching :class:`BreakerRecoveryRule`.
- Override away from :data:`BREAKER_RECOVERY_DEFAULTS` without a written
  rationale in the description.
- Add a new :class:`CircuitBreakerId` here without first appending the
  identifier to the closed-set enum in
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

# ── Stablecoin depeg ladder helpers (D.1) ────────────────────────────────────

_STANDARD_STABLES: Final[tuple[str, ...]] = ("USDC", "USDT", "DAI", "GHO", "SUSDE")
_SYNTHETIC_STABLES: Final[tuple[str, ...]] = ("USDE", "CRVUSD", "FRAX")

# (breaker_id, base_bps, action, severity, cooldown_seconds, recovery_mode_override)
# STABLECOIN_DEPEG_MODERATE uses CANCEL_OPEN with explicit AUTO_COOLDOWN override —
# CANCEL_OPEN defaults to MANUAL_UNKILL per BREAKER_RECOVERY_DEFAULTS but 500bps
# depeg is an intermediate severity that auto-recovers after 30min (per DR plan D.1).
_DEPEG_TIERS: Final[
    tuple[tuple[CircuitBreakerId, int, BreakerAction, AlertSeverity, int | None, BreakerRecoveryMode | None], ...]
] = (
    (CircuitBreakerId.STABLECOIN_DEPEG_WARNING, 100, BreakerAction.BLOCK_NEW, AlertSeverity.WARN, 600, None),
    (CircuitBreakerId.STABLECOIN_DEPEG_SMALL, 300, BreakerAction.SCALE_DOWN, AlertSeverity.HIGH, 900, None),
    (
        CircuitBreakerId.STABLECOIN_DEPEG_MODERATE,
        500,
        BreakerAction.CANCEL_OPEN,
        AlertSeverity.HIGH,
        1800,
        BreakerRecoveryMode.AUTO_COOLDOWN,
    ),
    (CircuitBreakerId.STABLECOIN_DEPEG_CATASTROPHIC, 1000, BreakerAction.KILL_ALL, AlertSeverity.CRITICAL, None, None),
)


def _depeg_configs() -> tuple[BreakerConfig, ...]:
    configs: list[BreakerConfig] = []
    for stable in _STANDARD_STABLES + _SYNTHETIC_STABLES:
        is_synthetic = stable in _SYNTHETIC_STABLES
        multiplier = Decimal("0.5") if is_synthetic else Decimal("1")
        suffix = " (synthetic half-threshold)" if is_synthetic else ""
        for breaker_id, base_bps, action, severity, cooldown, recovery_override in _DEPEG_TIERS:
            effective_bps = int(Decimal(str(base_bps)) * multiplier)
            configs.append(
                BreakerConfig(
                    breaker_id=breaker_id,
                    scope=BreakerScope.PER_STABLE,
                    applies_to=stable,
                    trigger=BreakerTrigger(
                        trigger_type=breaker_id,
                        threshold_value=Decimal(str(effective_bps)),
                        threshold_unit=ThresholdUnit.BPS_OF_ONE,
                    ),
                    action=action,
                    cooldown_seconds=cooldown,
                    recovery_mode=recovery_override,
                    alerting_severity=severity,
                    description=f"{stable} peg deviation >= {effective_bps}bps{suffix}.",
                )
            )
    return tuple(configs)


BREAKERS: Final[tuple[BreakerConfig, ...]] = (
    BreakerConfig(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.ORACLE_DEVIATION_BPS,
            threshold_value=Decimal("100"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
            window_seconds=60,
            consecutive_count=3,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=300,
        alerting_severity=AlertSeverity.HIGH,
        description="Chainlink/Pyth oracle deviation > 100bps for 3 consecutive 60s windows.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.RPC_OUTAGE_SECONDS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.RPC_OUTAGE_SECONDS,
            threshold_value=Decimal("60"),
            threshold_unit=ThresholdUnit.MINUTES,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=120,
        alerting_severity=AlertSeverity.HIGH,
        description="Chain RPC endpoint unreachable >= 60s.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.GAS_PRICE_SURGE_GWEI,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.GAS_PRICE_SURGE_GWEI,
            threshold_value=Decimal("200"),
            threshold_unit=ThresholdUnit.COUNT_PER_MINUTE,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=180,
        alerting_severity=AlertSeverity.WARN,
        description="L1 gas > 200 gwei renders tx-cost economics negative.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.POSITION_LIMIT_EXCEEDED,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.POSITION_LIMIT_EXCEEDED,
            threshold_value=Decimal("1.0"),
            threshold_unit=ThresholdUnit.RATIO,
        ),
        action=BreakerAction.CANCEL_OPEN,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Gross archetype position exceeds configured cap. CANCEL_OPEN → MANUAL_UNKILL "
            "per defaults (cancelled orders are gone)."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            threshold_value=Decimal("300"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
        ),
        action=BreakerAction.SCALE_DOWN,
        cooldown_seconds=1800,
        alerting_severity=AlertSeverity.HIGH,
        description="Daily drawdown >= 300bps NAV → halve position; auto-recover after 30min if drawdown clears.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.LIQUIDATION_CASCADE_RISK,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.LIQUIDATION_CASCADE_RISK,
            threshold_value=Decimal("1.10"),
            threshold_unit=ThresholdUnit.RATIO,
        ),
        action=BreakerAction.KILL_ALL,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Aave health-factor <= 1.10 across >= 2 positions. KILL_ALL → MANUAL_UNKILL "
            "(full unwind requires operator sign-off before re-engaging leverage)."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.VENUE_OUTAGE_SECONDS,
        scope=BreakerScope.PER_VENUE,
        applies_to="*",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.VENUE_OUTAGE_SECONDS,
            threshold_value=Decimal("90"),
            threshold_unit=ThresholdUnit.MINUTES,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=300,
        alerting_severity=AlertSeverity.HIGH,
        description="Venue REST+WS both unreachable >= 90s — block new orders to that venue.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.CUSTODY_DISCONNECT_SECONDS,
        scope=BreakerScope.GLOBAL,
        applies_to="*",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.CUSTODY_DISCONNECT_SECONDS,
            threshold_value=Decimal("180"),
            threshold_unit=ThresholdUnit.MINUTES,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=600,
        alerting_severity=AlertSeverity.HIGH,
        description="Copper/CEFFU unreachable >= 180s — pause new deployments.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.MANIFEST_PHANTOM_RATE_BPS,
        scope=BreakerScope.PER_ASSET_GROUP,
        applies_to="defi",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.MANIFEST_PHANTOM_RATE_BPS,
            threshold_value=Decimal("200"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=3600,
        alerting_severity=AlertSeverity.WARN,
        description="Manifest phantom rate >= 200bps of expected shards — pause new backfills.",
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.BATCH_LIVE_DIVERGENCE_BPS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.BATCH_LIVE_DIVERGENCE_BPS,
            threshold_value=Decimal("50"),
            threshold_unit=ThresholdUnit.BPS_OF_ONE,
        ),
        action=BreakerAction.SCALE_DOWN,
        cooldown_seconds=1800,
        alerting_severity=AlertSeverity.HIGH,
        description="Batch-vs-live P&L divergence >= 50bps — auto-scale-down + recover when within 5bps.",
    ),
    # ── Phase 1.E additions — oracle staleness + lending pool unavailability ──
    BreakerConfig(
        breaker_id=CircuitBreakerId.ORACLE_STALENESS_SECONDS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.ORACLE_STALENESS_SECONDS,
            threshold_value=Decimal("120"),
            threshold_unit=ThresholdUnit.SECONDS,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=300,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Chainlink/Pyth oracle has not published for >= 120s — frozen feed."
            " BLOCK_NEW + fires KILL_SWITCH_ORACLE_DIVERGENCE → GLOBAL halt."
        ),
    ),
    BreakerConfig(
        breaker_id=CircuitBreakerId.LENDING_POOL_UNAVAILABLE_SECONDS,
        scope=BreakerScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=BreakerTrigger(
            trigger_type=CircuitBreakerId.LENDING_POOL_UNAVAILABLE_SECONDS,
            threshold_value=Decimal("300"),
            threshold_unit=ThresholdUnit.SECONDS,
        ),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=600,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Aave pool paused or borrow-cap-locked >= 300s — carry leverage"
            " cannot be resized. BLOCK_NEW until pool accepts borrows again."
        ),
    ),
    *_depeg_configs(),
)

RECOVERY_RULES: Final[tuple[BreakerRecoveryRule, ...]] = (
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        guard_description="Oracle deviation < 50bps for 5min (sustained recovery).",
        retry_policy="exponential",
        auto_disarm_after_seconds=300,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.RPC_OUTAGE_SECONDS,
        guard_description="RPC endpoint returns 200 for >= 5 consecutive health checks.",
        retry_policy="exponential",
        auto_disarm_after_seconds=120,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.GAS_PRICE_SURGE_GWEI,
        guard_description="L1 gas < 150 gwei sustained for 3min.",
        retry_policy="linear",
        auto_disarm_after_seconds=180,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.POSITION_LIMIT_EXCEEDED,
        guard_description="Operator confirms position resized below cap.",
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
        guard_description="Daily drawdown < 150bps NAV sustained for 30min.",
        retry_policy="exponential",
        auto_disarm_after_seconds=1800,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.LIQUIDATION_CASCADE_RISK,
        guard_description="Operator confirms positions unwound + health-factors > 1.5 across the book.",
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.VENUE_OUTAGE_SECONDS,
        guard_description="Venue REST + WS heartbeats green for >= 5min.",
        retry_policy="exponential",
        auto_disarm_after_seconds=300,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.CUSTODY_DISCONNECT_SECONDS,
        guard_description="Custody endpoint health-check 200 for 10 consecutive probes.",
        retry_policy="exponential",
        auto_disarm_after_seconds=600,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.MANIFEST_PHANTOM_RATE_BPS,
        guard_description="Phantom-audit shows < 50bps phantom rate post-reconcile.",
        retry_policy="linear",
        auto_disarm_after_seconds=3600,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.BATCH_LIVE_DIVERGENCE_BPS,
        guard_description="Batch-vs-live recon within 5bps for 30min.",
        retry_policy="linear",
        auto_disarm_after_seconds=1800,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.ORACLE_STALENESS_SECONDS,
        guard_description="Oracle publishes fresh price for >= 5 consecutive heartbeat intervals.",
        retry_policy="exponential",
        auto_disarm_after_seconds=300,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.LENDING_POOL_UNAVAILABLE_SECONDS,
        guard_description="Lending pool accepts a borrow quote (non-reverted health check) for 3 consecutive probes.",
        retry_policy="exponential",
        auto_disarm_after_seconds=600,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.STABLECOIN_DEPEG_WARNING,
        guard_description="Peg-monitor shows < 30bps deviation for 10min.",
        retry_policy="exponential",
        auto_disarm_after_seconds=600,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.STABLECOIN_DEPEG_SMALL,
        guard_description="Peg-monitor shows < 100bps deviation for 15min.",
        retry_policy="exponential",
        auto_disarm_after_seconds=900,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.STABLECOIN_DEPEG_MODERATE,
        guard_description="Peg-monitor shows < 200bps deviation for 30min.",
        retry_policy="linear",
        auto_disarm_after_seconds=1800,
    ),
    BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.STABLECOIN_DEPEG_CATASTROPHIC,
        guard_description="Operator confirms stable peg restored + all positions crystallized.",
        retry_policy="none",
        auto_disarm_after_seconds=None,
    ),
)
