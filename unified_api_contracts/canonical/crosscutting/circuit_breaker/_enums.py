"""Circuit breaker enums — breaker IDs, scopes, actions and recovery modes."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


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

    # ── LST depeg ladder (D.2 — risk plan Phase D) ────────────────────────────────────
    LST_DEPEG_WARNING = "LST_DEPEG_WARNING"
    """LST/ETH peg deviation ≥ 100bps — BLOCK_NEW. Monitors stETH/rETH/cbETH/JitoSOL/mSOL
    secondary-market price vs protocol exchange rate. 100bps is notable (stETH 2022 event
    touched -630bps at trough); normal rebalancing noise is ≤ 30bps."""
    LST_DEPEG_SMALL = "LST_DEPEG_SMALL"
    """LST/ETH peg deviation ≥ 300bps — SCALE_DOWN. Meaningful adverse move; reduce
    carry_staked_basis leverage before redemption-queue pressure worsens."""
    LST_DEPEG_MODERATE = "LST_DEPEG_MODERATE"
    """LST/ETH peg deviation ≥ 500bps — CANCEL_OPEN. Mirrors the
    ``DEFI_LST_DEPEG_STETH_5PCT`` scenario trigger point; carry leg loses 5% vs perp
    hedge; replaces generic ``DRAWDOWN_DAILY_BPS`` trip for LST-specific depeg path."""
    LST_DEPEG_CATASTROPHIC = "LST_DEPEG_CATASTROPHIC"
    """LST/ETH peg deviation ≥ 1500bps — KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS +
    MANUAL_UNKILL. Extreme event (e.g. mass validator slashing + redemption freeze);
    carry position structurally broken; requires operator review before re-arming."""

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
    PER_LST = "PER_LST"
    """Per-LST scope — ``applies_to`` is the LST symbol (e.g. ``"stETH"``)."""
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


__all__ = [
    "BREAKER_RECOVERY_DEFAULTS",
    "BreakerAction",
    "BreakerRecoveryMode",
    "BreakerScope",
    "CircuitBreakerId",
]
