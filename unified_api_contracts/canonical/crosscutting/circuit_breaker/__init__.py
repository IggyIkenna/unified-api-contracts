"""Circuit-breaker taxonomy — closed-set workspace SSOT.

Phase 1.A of ``disaster_recovery_circuit_breakers_2026_05_10.md``
(``unified-trading-pm/plans/active/``). Defines the canonical breaker
taxonomy that the strategy-service/risk, execution-service, and
alerting-service all consume.

Five orthogonal axes per breaker:

1. :class:`CircuitBreakerId` — closed-set identifier (per-archetype x per-trigger).
2. :class:`BreakerScope` — applicability blast radius
   (per-venue / per-archetype / per-account / per-asset_group / global).
3. :class:`BreakerTrigger` — typed condition the breaker watches
   (threshold value + unit + optional window / consecutive-count).
4. :class:`BreakerAction` — execution-side response when the trigger fires
   (BLOCK_NEW / CANCEL_OPEN / SCALE_DOWN / KILL_ALL).
5. :class:`BreakerRecoveryMode` — recovery semantics
   (``manual_unkill`` / ``auto_cooldown``).

The :data:`BREAKER_RECOVERY_DEFAULTS` SSOT maps :class:`BreakerAction` to its
default :class:`BreakerRecoveryMode`. Per-breaker override is supported via
:attr:`BreakerConfig.recovery_mode`. Per Q8 ratification 2026-05-10 cross-plan
audit with
[`risk_simulations_limits_alerting_2026_05_10.md`](../../../../unified-trading-pm/plans/active/risk_simulations_limits_alerting_2026_05_10.md)
Phase 1.F, recovery wiring is owned here (DR plan Phase 1.A) and the risk plan
Phase 1.F flips to ``[x]`` once this module ships.

§ 7 SSOT reconciliation seam
----------------------------

Every Pydantic class docstring below includes a "§ 7 SSOT reconciliation"
subsection per the seam mandate in
[`risk_simulations_limits_alerting_2026_05_10.md:44-87`](../../../../unified-trading-pm/plans/active/risk_simulations_limits_alerting_2026_05_10.md).
The seam:

- :class:`BreakerAction` is a Layer-3 execution-side response distinct from
  :class:`unified_api_contracts.errors.ErrorAction` (Layer-4 post-venue-error
  classification per
  ``codex/04-architecture/autonomous-recovery-matrix.md``).
- :class:`BreakerScope` composes with
  :class:`unified_api_contracts.alerting.KillSwitchScope`
  (per ``codex/04-architecture/kill-switch-circuit-breaker.md``) —
  breaker firing at ``PER_VENUE`` may engage a :class:`KillSwitchId` at
  ``KillSwitchScope.VENUE``.
- :class:`BreakerRecoveryMode` orthogonal to the kill-switch 4-set strategy
  behaviours (``STOP_NEW_ONLY`` / ``FAST_UNWIND`` / ``SLOW_UNWIND`` /
  ``DELTA_HEDGE``) — recovery decides WHEN the breaker disarms; strategy
  behaviour decides WHAT the strategy does while armed.

Adding a new breaker
--------------------

1. Append the identifier to :class:`CircuitBreakerId` here.
2. Add a :class:`BreakerConfig` entry to the per-archetype registry under
   ``unified_api_contracts/registry/circuit_breakers/<archetype>.py``.
3. If the trigger maps to an alert, append the corresponding :class:`AlertCode`
   in ``alerting/codes.py`` (Sub-B's scope).
4. Update the codex doc list per
   ``disaster_recovery_circuit_breakers_2026_05_10.md`` Phase 8.
"""

from ..alerting.thresholds import ThresholdUnit
from ._enums import (
    BREAKER_RECOVERY_DEFAULTS,
    BreakerAction,
    BreakerRecoveryMode,
    BreakerScope,
    CircuitBreakerId,
)
from ._functions import breaker_fired_event
from ._models import BreakerConfig, BreakerFiredEvent, BreakerRecoveryRule, BreakerTrigger

__all__ = [
    "BREAKER_RECOVERY_DEFAULTS",
    "BreakerAction",
    "BreakerConfig",
    "BreakerFiredEvent",
    "BreakerRecoveryMode",
    "BreakerRecoveryRule",
    "BreakerScope",
    "BreakerTrigger",
    "CircuitBreakerId",
    "ThresholdUnit",
    "breaker_fired_event",
]
