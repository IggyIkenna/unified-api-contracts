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

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .alerting.codes import AlertCode, AlertSeverity
from .alerting.thresholds import ThresholdUnit


class CircuitBreakerId(StrEnum):
    """Closed-set breaker identifiers — per-trigger, archetype-agnostic.

    The same identifier may register at multiple :class:`BreakerScope` values
    across archetypes (e.g. ``ORACLE_DEVIATION_BPS`` fires both for
    ``CARRY_STAKED_BASIS`` and ``ARBITRAGE_PRICE_DISPERSION``); per-archetype
    threshold tuning lives in the registry seeds, not here.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with:

    - ``codex/04-architecture/kill-switch-circuit-breaker.md`` — canonical
      breaker taxonomy + 5-set kill-switch trigger mapping.
    - The 8-event lifecycle SSOT — ``BREAKER_ARMED`` / ``BREAKER_DISARMED``
      events are emitted on every transition (per
      ``codex/04-architecture/autonomous-recovery-matrix.md``).
    - :class:`unified_api_contracts.alerting.AlertCode` —
      ``CIRCUIT_BREAKER_OPEN`` / ``CIRCUIT_BREAKER_DEGRADED`` /
      ``CIRCUIT_BREAKER_CLOSED`` mirror breaker transitions; new per-breaker
      alert codes (if needed) are added in the alerting codes module.
    - ``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md`` —
      Layer-2 risk rule consequences feed into Layer-3 breakers via the
      ``BREAKER_ESCALATION_REQUESTED`` event seam.
    """

    # ── carry_staked_basis breakers (LST leverage family)
    ORACLE_DEVIATION_BPS = "ORACLE_DEVIATION_BPS"
    """Oracle price deviation from canonical mid (Chainlink / Pyth) >= threshold bps."""
    RPC_OUTAGE_SECONDS = "RPC_OUTAGE_SECONDS"
    """Chain RPC endpoint unreachable for >= threshold seconds."""
    GAS_PRICE_SURGE_GWEI = "GAS_PRICE_SURGE_GWEI"
    """L1 gas price >= threshold gwei (renders tx-cost economics negative)."""
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    """Per-archetype / per-venue gross position exceeds configured cap."""
    DRAWDOWN_DAILY_BPS = "DRAWDOWN_DAILY_BPS"
    """Daily drawdown >= threshold bps of NAV."""
    LIQUIDATION_CASCADE_RISK = "LIQUIDATION_CASCADE_RISK"
    """Aave / lending health-factor approaches liquidation across multiple positions."""
    VENUE_OUTAGE_SECONDS = "VENUE_OUTAGE_SECONDS"
    """Venue REST + WS both unreachable >= threshold seconds."""
    CUSTODY_DISCONNECT_SECONDS = "CUSTODY_DISCONNECT_SECONDS"
    """Copper / CEFFU custody endpoint unreachable >= threshold seconds."""
    MANIFEST_PHANTOM_RATE_BPS = "MANIFEST_PHANTOM_RATE_BPS"
    """Manifest phantom rate (captured-but-no-parquet) >= threshold bps of expected shards."""
    BATCH_LIVE_DIVERGENCE_BPS = "BATCH_LIVE_DIVERGENCE_BPS"
    """Batch-vs-live P&L divergence >= threshold bps (UTL batch_live_reconciler)."""

    # ── ARBITRAGE_PRICE_DISPERSION breakers (funding-arb family)
    FUNDING_RATE_FLIP_BPS = "FUNDING_RATE_FLIP_BPS"
    """Funding rate flips sign or moves >= threshold bps in one funding window."""
    BASIS_INVERSION_BPS = "BASIS_INVERSION_BPS"
    """Cash-perp basis inverts or moves >= threshold bps adverse."""
    SPREAD_BLOWOUT_BPS = "SPREAD_BLOWOUT_BPS"
    """Quoted bid-ask spread >= threshold bps (illiquidity / venue degradation)."""
    CROSS_VENUE_DIVERGENCE_BPS = "CROSS_VENUE_DIVERGENCE_BPS"
    """Same-instrument mid-price across hedge venues diverges >= threshold bps."""
    INVENTORY_IMBALANCE_RATIO = "INVENTORY_IMBALANCE_RATIO"
    """Cross-venue inventory imbalance >= threshold ratio (hedge leg out of sync)."""
    FILL_LATENCY_BREACH_MS = "FILL_LATENCY_BREACH_MS"
    """Order ack -> fill latency p99 >= threshold ms (venue performance degradation)."""
    REJECT_RATE_BPS = "REJECT_RATE_BPS"
    """Order rejection rate over rolling window >= threshold bps."""
    PNL_VARIANCE_SIGMA = "PNL_VARIANCE_SIGMA"
    """Realised PnL variance >= threshold sigma vs expected (live-vs-backtest drift)."""
    HEDGE_GAP_NOTIONAL_USD = "HEDGE_GAP_NOTIONAL_USD"
    """Unhedged delta notional >= threshold USD."""
    CLOCK_SKEW_MS = "CLOCK_SKEW_MS"
    """Local clock vs venue ts skew >= threshold ms (timestamp-mismatch correctness risk)."""

    # ── Cross-archetype shared: oracle staleness + lending pool unavailability ─
    ORACLE_STALENESS_SECONDS = "ORACLE_STALENESS_SECONDS"
    """Oracle data feed has not updated for >= threshold seconds.
    Distinct from ``ORACLE_DEVIATION_BPS`` (price divergence) — this breaker
    guards against a *frozen* oracle, not a *wrong* oracle price.
    Applies to both carry_staked_basis (Chainlink/Pyth LST price feeds) and
    arbitrage_price_dispersion (cross-venue reference prices)."""
    LENDING_POOL_UNAVAILABLE_SECONDS = "LENDING_POOL_UNAVAILABLE_SECONDS"
    """Aave / lending pool has been paused OR borrow-cap-locked for >= threshold
    seconds. Covers two sub-modes: ``PAUSED`` (guardian action; repayments still
    live) and ``BORROW_CAP_REACHED`` (pool full; new borrows blocked). Both
    sub-modes prevent carry_staked_basis from resizing leverage."""

    # ── Stablecoin depeg ladder (D.1 — risk plan Phase D) ─────────────────────
    STABLECOIN_DEPEG_WARNING = "STABLECOIN_DEPEG_WARNING"
    """Stablecoin peg deviation ≥ 100bps (standard) / 50bps (synthetic: USDE/CRVUSD/FRAX) — BLOCK_NEW."""
    STABLECOIN_DEPEG_SMALL = "STABLECOIN_DEPEG_SMALL"
    """Stablecoin peg deviation ≥ 300bps (standard) / 150bps (synthetic) — SCALE_DOWN."""
    STABLECOIN_DEPEG_MODERATE = "STABLECOIN_DEPEG_MODERATE"
    """Stablecoin peg deviation ≥ 500bps (standard) / 250bps (synthetic) — CANCEL_OPEN."""
    STABLECOIN_DEPEG_CATASTROPHIC = "STABLECOIN_DEPEG_CATASTROPHIC"
    """Stablecoin peg deviation ≥ 1000bps (standard) / 500bps (synthetic) — KILL_ALL + MANUAL_UNKILL."""

    # ── DR Phase 1.A+4 extensions — simulation_scenarios Day-1 follow-up (2026-05-13) ──
    # 4 breakers surfaced from simulation_scenarios_topology_price_shocks_2026_05_09
    # Day-1 run: per-chain RPC outage disambiguation, oracle staleness, lending
    # pool unavailability, and ARBITRAGE_PRICE_DISPERSION applies_to seed.
    #
    # NOTE 2026-05-13 (slot 5): ORACLE_STALENESS_SECONDS was duplicated here
    # in commit adcfcf5 — already defined at line 147 above with the same
    # semantic. Duplicate removed to unblock workspace-wide UAC imports
    # (StrEnum raises TypeError on duplicate names). The original definition
    # already covers Chainlink heartbeat semantics ("Chainlink/Pyth LST price
    # feeds and cross-venue reference prices"); the 2026-05-13 docstring
    # extension (Chainlink ETH/USD heartbeat = 3600s; threshold default =
    # heartbeat + 15min grace = 4500s) belongs in the breaker registry's
    # threshold defaults rather than the enum docstring.

    RPC_OUTAGE_SECONDS_ETHEREUM = "RPC_OUTAGE_SECONDS_ETHEREUM"
    """Ethereum chain RPC endpoint unreachable for >= threshold seconds.
    Disambiguates from the generic ``RPC_OUTAGE_SECONDS`` (used by
    ``CARRY_STAKED_BASIS`` cross-chain) — per-chain breakers allow
    chain-specific thresholds and recovery semantics. ETHEREUM = 30s threshold
    (fast finality expectations on L1). Added 2026-05-13."""

    RPC_OUTAGE_SECONDS_SOLANA = "RPC_OUTAGE_SECONDS_SOLANA"
    """Solana chain RPC endpoint unreachable for >= threshold seconds.
    Solana slot time ≈ 400ms; 30s outage = ~75 missed slots. Threshold
    default = 30s (same as Ethereum for operational simplicity; per-archetype
    override can tighten). Added 2026-05-13 per simulation_scenarios Day-1."""

    # NOTE 2026-05-13 (slot 5): LENDING_POOL_UNAVAILABLE_SECONDS was duplicated
    # here in commit adcfcf5 — already defined at line 153 above with the same
    # semantic ("Aave / lending pool paused OR borrow-cap-locked"). Duplicate
    # removed to unblock workspace-wide UAC imports.


class BreakerScope(StrEnum):
    """Blast-radius scope for a breaker.

    Mirrors :class:`unified_api_contracts.alerting.KillSwitchScope` but at the
    breaker layer — same axes, different vocabulary so docs / readers can
    distinguish "what fires" (breaker) from "what halts" (kill-switch).

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`KillSwitchScope` per
    ``codex/04-architecture/kill-switch-circuit-breaker.md``. A breaker firing
    at ``BreakerScope.PER_VENUE`` typically engages a kill-switch at
    ``KillSwitchScope.VENUE``; ``BreakerScope.GLOBAL`` engages
    ``KillSwitchScope.GLOBAL``.
    """

    PER_VENUE = "PER_VENUE"
    PER_ARCHETYPE = "PER_ARCHETYPE"
    PER_ACCOUNT = "PER_ACCOUNT"
    PER_ASSET_GROUP = "PER_ASSET_GROUP"
    PER_STABLE = "PER_STABLE"
    """Per-stablecoin scope — ``applies_to`` is the stable symbol (e.g. ``"USDC"``)."""
    GLOBAL = "GLOBAL"


class BreakerAction(StrEnum):
    """Execution-side response when a breaker trigger fires.

    Closed set of four. Severity escalates left-to-right:

    - ``BLOCK_NEW`` — least restrictive. New orders refused; in-flight kept.
    - ``CANCEL_OPEN`` — open orders cancelled; existing positions held.
    - ``SCALE_DOWN`` — proportional unwind (e.g. halve position).
    - ``KILL_ALL`` — full unwind / delta-neutral exit per
      :class:`unified_api_contracts.internal.KillSwitchReason`.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Distinct from :class:`unified_api_contracts.errors.ErrorAction`
    (``RETRY`` / ``RECONNECT`` / ``SKIP`` / ``FAIL`` — Layer-4 venue-rejection
    classification per ``codex/04-architecture/autonomous-recovery-matrix.md``).
    Distinct from :class:`unified_api_contracts.alerting.AlertChannel`
    routing — actions are execution-side; channels are notification-side.

    Composes with the 3-set circuit-breaker action vocabulary in
    ``alerting_service_live_rules_2026_05_07.md`` (``stop_new_signals`` /
    ``force_exit_only`` / ``halt_strategy``): BLOCK_NEW maps to
    ``stop_new_signals`` (DEGRADED); CANCEL_OPEN + SCALE_DOWN map to
    ``force_exit_only``; KILL_ALL maps to ``halt_strategy`` (OPEN cascade).
    """

    BLOCK_NEW = "BLOCK_NEW"
    CANCEL_OPEN = "CANCEL_OPEN"
    SCALE_DOWN = "SCALE_DOWN"
    KILL_ALL = "KILL_ALL"


class BreakerRecoveryMode(StrEnum):
    """How a breaker disarms.

    Per Q8 ratification 2026-05-10 (cross-plan audit between DR plan Phase 1.A
    and risk plan Phase 1.F). Closed two-set:

    - ``MANUAL_UNKILL`` — armed state persists until operator action via
      deployment-UI kill-switch tab or ``kill-switch unkill`` CLI. Recovery
      emits ``KILL_SWITCH_MANUAL_UNKILLED`` alert with
      ``unkilled_by_operator_id``. Used for actions whose effects cannot be
      auto-restored (e.g. ``CANCEL_OPEN`` — cancelled orders don't come back;
      ``KILL_ALL`` — full unwind needs operator sign-off before re-engaging).
    - ``AUTO_COOLDOWN`` — guard predicate re-evaluated every ``cooldown_seconds``;
      on N consecutive green readings the breaker auto-disarms. Emits
      ``KILL_SWITCH_AUTO_RECOVERED`` alert with ``recovered_after_seconds`` +
      guard-evaluation trail. Used for least-restrictive actions whose effects
      naturally inverse (``BLOCK_NEW`` — resume safely when metric clears;
      ``SCALE_DOWN`` — re-scale up when conditions improve).

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.alerting.AlertCode`:
    recovery transitions emit ``KILL_SWITCH_AUTO_RECOVERED`` /
    ``KILL_SWITCH_MANUAL_UNKILLED`` (added to closed set by Sub-B in same
    cycle).
    """

    MANUAL_UNKILL = "manual_unkill"
    AUTO_COOLDOWN = "auto_cooldown"


BREAKER_RECOVERY_DEFAULTS: Final[dict[BreakerAction, BreakerRecoveryMode]] = {
    BreakerAction.BLOCK_NEW: BreakerRecoveryMode.AUTO_COOLDOWN,
    BreakerAction.CANCEL_OPEN: BreakerRecoveryMode.MANUAL_UNKILL,
    BreakerAction.SCALE_DOWN: BreakerRecoveryMode.AUTO_COOLDOWN,
    BreakerAction.KILL_ALL: BreakerRecoveryMode.MANUAL_UNKILL,
}
"""Per-action default :class:`BreakerRecoveryMode`.

Rationale per Q8 ratification 2026-05-10:

- ``BLOCK_NEW → AUTO_COOLDOWN`` — least-restrictive; auto-resume safe when
  metric clears.
- ``CANCEL_OPEN → MANUAL_UNKILL`` — cancelled orders are gone; auto-recovery
  doesn't restore them.
- ``SCALE_DOWN → AUTO_COOLDOWN`` — partial unwind has a natural inverse
  (re-scale up when conditions improve).
- ``KILL_ALL → MANUAL_UNKILL`` — full unwind needs operator sign-off before
  re-engaging.

Per-breaker override via :attr:`BreakerConfig.recovery_mode`. Reviewers reject
new breakers that override away from these defaults without a written
rationale in the registry seed.
"""


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


def breaker_fired_event(
    config: BreakerConfig,
    *,
    fired_at: datetime,
    alert_code: AlertCode,
    state: Literal["armed", "disarmed"],
    metadata: dict[str, str] | None = None,
) -> BreakerFiredEvent:
    """Convenience constructor that hydrates :class:`BreakerFiredEvent` from a
    :class:`BreakerConfig`.
    """
    recovery_mode = config.recovery_mode
    assert recovery_mode is not None  # model_validator always fills this field
    return BreakerFiredEvent(
        breaker_id=config.breaker_id,
        scope=config.scope,
        applies_to=config.applies_to,
        action=config.action,
        recovery_mode=recovery_mode,
        cooldown_seconds=config.cooldown_seconds,
        alerting_severity=config.alerting_severity,
        alert_code=alert_code,
        fired_at=fired_at,
        state=state,
        metadata=metadata or {},
    )
