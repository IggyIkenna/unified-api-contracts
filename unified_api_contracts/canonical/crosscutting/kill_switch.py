"""Kill-switch event taxonomy — closed-set workspace SSOT.

Phase 1.C-D of ``disaster_recovery_circuit_breakers_2026_05_10.md``
(``unified-trading-pm/plans/active/``). Defines the canonical event
vocabulary for the
:class:`unified_trading_library.kill_switch.KillSwitchBus` arm/disarm cycle.

Five orthogonal axes per kill-switch event:

1. :class:`KillSwitchId` — closed-set identifier for what's being killed
   (KILL_ALL_LIVE / per-archetype / per-venue / per-asset_group).
2. :class:`KillSwitchProvenance` — closed-set source-of-the-arm
   (OPERATOR_MANUAL / BREAKER_AUTO / SCENARIO_SYNTHETIC / SCHEDULED_DRILL).
3. :class:`KillSwitchArmRequest` — the inbound request to the bus.
4. :class:`KillSwitchArmedEvent` — emitted to subscribers on arm transition.
5. :class:`KillSwitchDisarmEvent` — emitted on disarm transition with
   recovery-mode telemetry per
   :class:`unified_api_contracts.alerting.BreakerRecoveryMode`.

§ 7 SSOT reconciliation seam
----------------------------

Composes with:

- :class:`unified_api_contracts.alerting.KillSwitchScope` (canonical
  blast-radius vocabulary; this module's :class:`KillSwitchId` enumerates the
  specific kill-switches per archetype + venue).
- :class:`unified_api_contracts.circuit_breaker.BreakerAction` —
  ``KILL_ALL`` action engages :class:`KillSwitchId.KILL_ALL_LIVE`;
  per-venue / per-archetype breakers engage per-venue / per-archetype kill
  switches.
- :class:`unified_api_contracts.circuit_breaker.BreakerRecoveryMode` —
  :class:`KillSwitchDisarmEvent.recovery_mode` echoes the originating
  breaker's recovery semantics.
- ``codex/04-architecture/kill-switch-circuit-breaker.md`` — canonical
  kill-switch arm/disarm lifecycle.
- :class:`unified_api_contracts.alerting.AlertCode`
  ``KILL_SWITCH_AUTO_RECOVERED`` / ``KILL_SWITCH_MANUAL_UNKILLED`` (Sub-B
  ships these in the same cycle per Q8 ratification 2026-05-10).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .circuit_breaker import BreakerRecoveryMode


class KillSwitchId(StrEnum):
    """Closed-set identifier for kill-switch arming targets.

    Granularity matches the cutover-archetype work-split: full-platform
    halt, per-archetype halt, per-venue halt, per-asset_group halt.
    Reviewers MUST update the cutover plan if a new kill-switch is added
    here without a matching entry in the master plan's Group F item 20 row.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.alerting.KillSwitchScope` —
    each :class:`KillSwitchId` maps to a scope via its semantic prefix:

    - ``KILL_ALL_LIVE`` → ``KillSwitchScope.GLOBAL``
    - ``KILL_PER_ARCHETYPE_*`` → ``KillSwitchScope.ARCHETYPE``
    - ``KILL_PER_VENUE_*`` → ``KillSwitchScope.VENUE``
    - ``KILL_PER_ASSET_GROUP_*`` (no equivalent enum on
      :class:`KillSwitchScope` — at runtime, the consumer maps to GLOBAL
      filtered by asset_group)
    - ``KILL_PER_WALLET`` → ``KillSwitchScope.WALLET`` (runtime-targeted via
      :class:`KillSwitchArmRequest.target_wallet_id` — no enum-per-wallet
      explosion). Added 2026-05-12 per
      ``api_keys_wallets_accounts_readiness_2026_05_10.md`` Phase 5.
    """

    KILL_ALL_LIVE = "KILL_ALL_LIVE"
    """Halt every live archetype across every venue. Operator-only arming
    (provenance MUST be OPERATOR_MANUAL or SCHEDULED_DRILL)."""

    # Per-archetype halts (cutover archetypes)
    KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS = "KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS"
    KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION = "KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION"
    KILL_PER_ARCHETYPE_ML_DIRECTIONAL_CONTINUOUS = "KILL_PER_ARCHETYPE_ML_DIRECTIONAL_CONTINUOUS"
    """Halt ML_DIRECTIONAL_CONTINUOUS across OKX + Binance + Bybit.
    kill_switch_scope=ARCHETYPE per locked design (a CeFi-ML trip does NOT
    halt DeFi strategies). Armed by position-limit / drawdown / signal-staleness
    / model-drift breakers. Added 2026-06-12."""

    # Per-venue halts (6 perp hedge venues + DeFi)
    KILL_PER_VENUE_BYBIT = "KILL_PER_VENUE_BYBIT"
    KILL_PER_VENUE_DERIBIT = "KILL_PER_VENUE_DERIBIT"
    KILL_PER_VENUE_BINANCE = "KILL_PER_VENUE_BINANCE"
    KILL_PER_VENUE_OKX = "KILL_PER_VENUE_OKX"
    KILL_PER_VENUE_HYPERLIQUID = "KILL_PER_VENUE_HYPERLIQUID"
    KILL_PER_VENUE_ASTER = "KILL_PER_VENUE_ASTER"

    # Per-asset-group halts (cutover-relevant)
    KILL_PER_ASSET_GROUP_CEFI = "KILL_PER_ASSET_GROUP_CEFI"
    KILL_PER_ASSET_GROUP_DEFI = "KILL_PER_ASSET_GROUP_DEFI"

    # Per-treasury-source halts — wired to WithdrawalReconciler emergency threshold
    # (wallet_treasury_client_flow_2026_05_10.md Phase 5.E)
    KILL_PER_TREASURY_COPPER = "KILL_PER_TREASURY_COPPER"
    """Halt all Copper withdrawals. Armed by WithdrawalReconciler on balance drift > emergency threshold."""

    KILL_PER_TREASURY_CEFFU = "KILL_PER_TREASURY_CEFFU"
    """Halt all CEFFU withdrawals. Armed by WithdrawalReconciler on balance drift > emergency threshold."""

    KILL_PER_TREASURY_DEFI_HOT_WALLET = "KILL_PER_TREASURY_DEFI_HOT_WALLET"
    """Halt all DeFi hot wallet withdrawals. Armed by WithdrawalReconciler on balance drift > emergency threshold."""

    KILL_PER_TREASURY_SUB_ACCOUNT_HYPERLIQUID = "KILL_PER_TREASURY_SUB_ACCOUNT_HYPERLIQUID"
    """Halt Hyperliquid sub-account withdrawals."""

    # KILL_PER_TREASURY_SUB_ACCOUNT_DRIFT removed 2026-07-16 (operator ruling:
    # all Solana perp DEXes dropped except Jupiter, not integrated — the
    # DRIFT treasury sub-account no longer exists). SSOT: unified-trading-pm/
    # codex/04-architecture/solana-defi-coverage.md.

    KILL_PER_TREASURY_SUB_ACCOUNT_DYDX = "KILL_PER_TREASURY_SUB_ACCOUNT_DYDX"
    """Halt dYdX sub-account withdrawals."""

    # Per-wallet halt (sentinel — runtime-targeted via target_wallet_id)
    KILL_PER_WALLET = "KILL_PER_WALLET"
    """Freeze a single wallet by its ``wallet_id``. Runtime target carried on
    :class:`KillSwitchArmRequest.target_wallet_id` — no enum-per-wallet
    explosion. Per-wallet kill is the FINEST-grain switch (below per-venue +
    per-archetype) — engages only the named wallet's signing surface, leaving
    sibling wallets of the same archetype unaffected. Composes with
    :class:`unified_api_contracts.defi.WalletProvisioningConfig.kill_switch_id`
    (set to ``"KILL_PER_WALLET"`` for wallet-level freezes; broader prefixes
    for archetype/venue/asset-group/global freezes that cascade through this
    wallet)."""


class KillSwitchProvenance(StrEnum):
    """Closed-set source-of-arm classification.

    Drives downstream alert severity + recovery-mode policy:

    - ``OPERATOR_MANUAL`` — operator armed via deployment-UI kill-switch tab
      or CLI. Always emits ``KILL_SWITCH_*`` HIGH-severity alert.
    - ``BREAKER_AUTO`` — auto-armed by a :class:`CircuitBreakerId` firing per
      its :class:`BreakerAction`. Severity inherits from the breaker's
      :class:`BreakerConfig.alerting_severity`.
    - ``SCENARIO_SYNTHETIC`` — armed by the chaos-drill cron / scenario
      runner. Severity WARN by default; production scope guarded
      (cron VM cannot arm a kill-switch on the live live-defi-rollout
      account; only on the testnet account).
    - ``SCHEDULED_DRILL`` — armed by the nightly DR drill scheduler. Same
      severity as ``SCENARIO_SYNTHETIC`` but distinguishable in audit logs.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.alerting.AlertCode` — every
    kill-switch arm emits a ``KILL_SWITCH_*`` AlertCode with severity routing
    based on provenance.
    """

    OPERATOR_MANUAL = "OPERATOR_MANUAL"
    BREAKER_AUTO = "BREAKER_AUTO"
    SCENARIO_SYNTHETIC = "SCENARIO_SYNTHETIC"
    SCHEDULED_DRILL = "SCHEDULED_DRILL"


class KillSwitchArmRequest(BaseModel):
    """Inbound request to arm a kill-switch.

    Consumed by :class:`unified_trading_library.kill_switch.KillSwitchBus.arm`
    (Phase 2 of DR plan wires this); emits a :class:`KillSwitchArmedEvent` on
    success.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with the 8-event lifecycle SSOT — arming a kill-switch emits
    ``BREAKER_ARMED`` (for breaker-initiated arms) followed by a
    ``KILL_SWITCH_FIRED`` event consumed by execution-service +
    strategy-service + strategy-service/position subscribers.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    switch_id: KillSwitchId
    provenance: KillSwitchProvenance
    requested_by: str
    """Operator ID (for ``OPERATOR_MANUAL``), breaker ID + serial (for
    ``BREAKER_AUTO``), scenario ID (for ``SCENARIO_SYNTHETIC``), or drill ID
    (for ``SCHEDULED_DRILL``)."""

    arm_timestamp: datetime
    """When the arm was requested (UTC). The bus stamps the actual ``armed_at``
    in :class:`KillSwitchArmedEvent` — these may differ slightly if the bus
    queues the request."""

    target_wallet_id: str = ""
    """Wallet ID for ``switch_id=KILL_PER_WALLET`` runtime targeting. Empty
    for every other switch_id (broader scopes target archetype / venue /
    asset_group / all via the switch_id alone). Required when
    ``switch_id == KILL_PER_WALLET``; rejected otherwise. Per
    ``api_keys_wallets_accounts_readiness_2026_05_10.md`` Phase 5."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Free-form structured fields for downstream consumers
    (e.g. ``breaker_serial``, ``threshold_observed``, ``correlation_id``)."""


class KillSwitchArmedEvent(BaseModel):
    """Emitted by :class:`KillSwitchBus` on successful arm.

    Subscribers (execution-service matching engine, strategy-service signal
    generators, position-balance-monitor reconcilers) consume this event +
    transition their own state per their service contracts.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.alerting.KillSwitchScope` —
    subscribers route by mapping :attr:`switch_id` to its scope semantics.
    Composes with the 4-set strategy kill-switch behaviour
    (``STOP_NEW_ONLY`` / ``FAST_UNWIND`` / ``SLOW_UNWIND`` / ``DELTA_HEDGE``):
    the chosen behaviour is service-side and depends on
    :attr:`KillSwitchArmedEvent.metadata`'s breaker context.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    switch_id: KillSwitchId
    provenance: KillSwitchProvenance
    armed_at: datetime
    requested_by: str
    target_wallet_id: str = ""
    """Wallet ID for ``switch_id=KILL_PER_WALLET`` events; empty otherwise.
    Subscribers reading this event for routing decisions MUST consume both
    ``switch_id`` AND ``target_wallet_id`` when the former is
    ``KILL_PER_WALLET``."""
    metadata: dict[str, str] = Field(default_factory=dict)


class KillSwitchDisarmEvent(BaseModel):
    """Emitted by :class:`KillSwitchBus` on successful disarm.

    Carries enough telemetry to render the operator audit log + post-mortem
    timeline: who disarmed, via which :class:`BreakerRecoveryMode`, and how
    long the kill-switch was armed.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.circuit_breaker.BreakerRecoveryMode`:
    :attr:`recovery_mode` echoes the originating breaker's mode (or
    ``MANUAL_UNKILL`` for operator-initiated disarms with no upstream
    breaker). :attr:`cooldown_seconds_elapsed` is non-``None`` when
    ``recovery_mode == AUTO_COOLDOWN`` and reflects the actual elapsed time;
    ``None`` for manual disarms.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    switch_id: KillSwitchId
    target_wallet_id: str = ""
    """Wallet ID for ``switch_id=KILL_PER_WALLET`` events; empty otherwise."""
    disarmed_at: datetime
    disarmed_by: str
    """Operator ID for manual disarms; the literal ``"AUTO_COOLDOWN"`` for
    self-recovery disarms (which carry no operator identity)."""

    recovery_mode: BreakerRecoveryMode
    """``MANUAL_UNKILL`` for operator-initiated disarms; ``AUTO_COOLDOWN`` for
    breaker self-recovery."""

    cooldown_seconds_elapsed: int | None = Field(default=None)
    """Elapsed seconds between arm and disarm. Required when
    ``recovery_mode == AUTO_COOLDOWN``; ``None`` for ``MANUAL_UNKILL``."""

    metadata: dict[str, str] = Field(default_factory=dict)
