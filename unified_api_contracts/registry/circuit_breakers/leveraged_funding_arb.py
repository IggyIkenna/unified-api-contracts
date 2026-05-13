"""Circuit-breaker seed registry — ``LEVERAGED_FUNDING_ARB`` archetype.

Stablecoin depeg ladder (D.1): 8 stables x 4 severity tiers (32 BreakerConfig
entries). Synthetic stables (USDE/CRVUSD/FRAX) use HALF thresholds vs standard.

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


BREAKERS: Final[tuple[BreakerConfig, ...]] = _depeg_configs()

RECOVERY_RULES: Final[tuple[BreakerRecoveryRule, ...]] = (
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
