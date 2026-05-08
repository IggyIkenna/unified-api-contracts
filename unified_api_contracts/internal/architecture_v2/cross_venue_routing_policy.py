"""Cross-venue routing policies — G2.9 gap #10.

Stage 3E § 2.9 gap #10 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
Declares the cross-venue leg-pairing + routing policies used by:

* ``CARRY_BASIS_DATED x TradFi`` — spot-ETF (IBKR) vs index-future
  (CME) basis trade. Needs explicit leg-venue + settlement currency
  pairing so execution-service can fair-price the basis.
* ``ARBITRAGE_PRICE_DISPERSION x TradFi x dated_future`` — cross-product
  spreads (CME ES vs ICE Brent, CME WTI vs ICE Brent).
* ``VOL_TRADING_OPTIONS x TradFi x option`` — when the hedge leg is on
  a different venue from the option leg (e.g. SPY option on CBOE +
  ES future hedge on CME).

Each policy declares:

* ``leg_venues`` — ordered tuple of venue IDs for each leg.
* ``leg_roles`` — ``SPOT_LEG`` / ``FUTURE_LEG`` / ``OPTION_LEG``.
* ``settlement_currency`` — reconciliation currency for PnL attribution
  and margin netting.
* ``max_execution_spread_bps`` — pre-trade gate: if the observed spread
  over synthetic fair value exceeds this, the algo aborts.
* ``leg_latency_p50_ms`` — expected latency between leg executions;
  used to size slippage reserves.

Consumer integration points (tracked via ``CONSUMER_CALL_SITES`` at
module bottom):

* ``execution-service/execution_service/v2/router.py`` — SOR routes
  cross-venue legs using this registry.
* ``execution-service/execution_service/algo_library/sor_cross_chain.py``
  — basis algo reads the ``max_execution_spread_bps`` pre-trade gate.
* ``strategy-service/strategy_service/portfolio_allocator/service.py``
  — allocator refuses to deploy a cross-venue archetype to an
  (archetype, venues) tuple with no matching policy entry.

Gates **G2.5** (Execution Algo Catalogue refactor) —
``plans/active/refactor_g2_5_execution_algo_catalogue_refactor_2026_04_20.md``.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class CrossVenueLegRole(StrEnum):
    """Role of a leg within a cross-venue routing policy."""

    SPOT_LEG = "spot_leg"
    """Cash / spot instrument leg (stock ETF, spot crypto)."""

    FUTURE_LEG = "future_leg"
    """Dated future or perpetual future leg."""

    OPTION_LEG = "option_leg"
    """Option leg (call / put) — may be single or multi-leg combo."""

    PERP_LEG = "perp_leg"
    """Perpetual swap leg (crypto-specific)."""


class RoutingPriority(StrEnum):
    """Leg-selection priority when multiple venues could carry the leg."""

    PRICE = "price"
    """Prefer venue with tightest spread / best mid-price."""

    LATENCY = "latency"
    """Prefer venue with lowest leg-pair execution latency."""

    FEE = "fee"
    """Prefer venue with lowest combined taker/maker fees."""

    LIQUIDITY = "liquidity"
    """Prefer venue with deepest top-of-book depth."""


class CrossVenueRoutingPolicy(BaseModel):
    """One cross-venue leg-pairing policy.

    Keyed by ``policy_id``. ``leg_venues`` and ``leg_roles`` are
    parallel tuples of equal length (enforced at import-time).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str
    """Stable slug (e.g. "ibkr_spy_cme_es_basis")."""

    leg_venues: tuple[str, ...]
    """Ordered tuple of venue IDs — one per leg."""

    leg_roles: tuple[CrossVenueLegRole, ...]
    """Parallel tuple of leg roles, same length as ``leg_venues``."""

    settlement_currency: str
    """ISO 4217 code (e.g. "USD") used for PnL / margin reconciliation."""

    max_execution_spread_bps: int = Field(ge=0, le=10_000)
    """Pre-trade gate: abort if observed spread over fair > this bps."""

    leg_latency_p50_ms: int = Field(ge=0)
    """p50 latency between leg executions. Used for slippage reserve."""

    priority: RoutingPriority = RoutingPriority.PRICE
    """Primary selection priority."""

    notes: str = ""
    """Author notes; not surfaced in prospect UI."""


CROSS_VENUE_ROUTING_POLICIES: Final[tuple[CrossVenueRoutingPolicy, ...]] = (
    # ── TradFi index-basis pairs ───────────────────────────────────────
    CrossVenueRoutingPolicy(
        policy_id="ibkr_spy_cme_es_basis",
        leg_venues=("ibkr", "cme"),
        leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
        settlement_currency="USD",
        max_execution_spread_bps=8,
        leg_latency_p50_ms=120,
        priority=RoutingPriority.PRICE,
        notes="SPY (IBKR cash ETF) vs CME ES front-month basis. Settles USD.",
    ),
    CrossVenueRoutingPolicy(
        policy_id="ibkr_qqq_cme_nq_basis",
        leg_venues=("ibkr", "cme"),
        leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
        settlement_currency="USD",
        max_execution_spread_bps=10,
        leg_latency_p50_ms=130,
        priority=RoutingPriority.PRICE,
        notes="QQQ (IBKR) vs CME NQ. Nasdaq-100 basis.",
    ),
    CrossVenueRoutingPolicy(
        policy_id="ibkr_iwm_cme_rty_basis",
        leg_venues=("ibkr", "cme"),
        leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
        settlement_currency="USD",
        max_execution_spread_bps=15,
        leg_latency_p50_ms=150,
        priority=RoutingPriority.LIQUIDITY,
        notes="IWM (IBKR) vs CME RTY. Russell 2000 basis; thinner than S&P / Nasdaq.",
    ),
    # ── Commodity cross-product spreads ────────────────────────────────
    CrossVenueRoutingPolicy(
        policy_id="cme_wti_ice_brent_spread",
        leg_venues=("cme", "ice"),
        leg_roles=(CrossVenueLegRole.FUTURE_LEG, CrossVenueLegRole.FUTURE_LEG),
        settlement_currency="USD",
        max_execution_spread_bps=25,
        leg_latency_p50_ms=180,
        priority=RoutingPriority.PRICE,
        notes="CME WTI vs ICE Brent cross-product spread.",
    ),
    # ── Crypto spot vs perp basis ──────────────────────────────────────
    CrossVenueRoutingPolicy(
        policy_id="binance_spot_binance_perp_basis",
        leg_venues=("binance", "binance"),
        leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.PERP_LEG),
        settlement_currency="USDT",
        max_execution_spread_bps=5,
        leg_latency_p50_ms=40,
        priority=RoutingPriority.LATENCY,
        notes="Same-venue crypto spot vs perp basis. Lowest leg latency.",
    ),
    CrossVenueRoutingPolicy(
        policy_id="coinbase_spot_hyperliquid_perp_basis",
        leg_venues=("coinbase", "hyperliquid"),
        leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.PERP_LEG),
        settlement_currency="USD",
        max_execution_spread_bps=12,
        leg_latency_p50_ms=150,
        priority=RoutingPriority.PRICE,
        notes="Cross-venue: Coinbase cash vs Hyperliquid perp. Settlement-currency mismatch handled via USDC bridge.",
    ),
    # ── Option hedge routing ───────────────────────────────────────────
    CrossVenueRoutingPolicy(
        policy_id="ibkr_spy_option_cme_es_hedge",
        leg_venues=("ibkr", "cme"),
        leg_roles=(CrossVenueLegRole.OPTION_LEG, CrossVenueLegRole.FUTURE_LEG),
        settlement_currency="USD",
        max_execution_spread_bps=20,
        leg_latency_p50_ms=160,
        priority=RoutingPriority.PRICE,
        notes="SPY option on IBKR hedged with ES future on CME (delta-hedge).",
    ),
)


class PolicyNotFoundError(LookupError):
    """Raised when ``routing_policy_for(policy_id)`` can't resolve."""


def routing_policy_for(
    policy_id: str,
    *,
    registry: Iterable[CrossVenueRoutingPolicy] = CROSS_VENUE_ROUTING_POLICIES,
) -> CrossVenueRoutingPolicy:
    """Resolve a policy by ID. Fail-loud on miss."""

    for entry in registry:
        if entry.policy_id == policy_id:
            return entry
    raise PolicyNotFoundError(
        f"policy_id={policy_id!r} not in CROSS_VENUE_ROUTING_POLICIES",
    )


def policies_for_venue_pair(
    venue_a: str,
    venue_b: str,
    *,
    registry: Iterable[CrossVenueRoutingPolicy] = CROSS_VENUE_ROUTING_POLICIES,
) -> tuple[CrossVenueRoutingPolicy, ...]:
    """All policies whose ``leg_venues`` is exactly ``{venue_a, venue_b}``
    (order-insensitive)."""

    target = frozenset((venue_a, venue_b))
    return tuple(entry for entry in registry if frozenset(entry.leg_venues) == target)


def policies_for_settlement_currency(
    currency: str,
    *,
    registry: Iterable[CrossVenueRoutingPolicy] = CROSS_VENUE_ROUTING_POLICIES,
) -> tuple[CrossVenueRoutingPolicy, ...]:
    """All policies settling in a given currency (e.g. all USD-settled)."""

    return tuple(entry for entry in registry if entry.settlement_currency == currency)


def _validate_registry_invariants(
    registry: Iterable[CrossVenueRoutingPolicy] = CROSS_VENUE_ROUTING_POLICIES,
) -> None:
    """Import-time invariants.

    * ``policy_id`` unique.
    * ``leg_venues`` and ``leg_roles`` same length + length >= 2.
    * ``settlement_currency`` is 3 uppercase letters (ISO 4217) or a
      known crypto stablecoin (USDT / USDC / DAI) — enforced as
      3-5 uppercase letters.
    """

    seen: set[str] = set()
    for entry in registry:
        if entry.policy_id in seen:
            raise ValueError(
                f"duplicate policy_id in CROSS_VENUE_ROUTING_POLICIES: {entry.policy_id!r}",
            )
        seen.add(entry.policy_id)
        if len(entry.leg_venues) != len(entry.leg_roles):
            raise ValueError(
                f"policy {entry.policy_id!r}: leg_venues ({len(entry.leg_venues)}) "
                f"and leg_roles ({len(entry.leg_roles)}) must have equal length",
            )
        if len(entry.leg_venues) < 2:
            raise ValueError(
                f"policy {entry.policy_id!r}: cross-venue routing needs >=2 legs",
            )
        cur = entry.settlement_currency
        if not (3 <= len(cur) <= 5) or not cur.isupper():
            raise ValueError(
                f"policy {entry.policy_id!r}: settlement_currency {cur!r} must be 3-5 upper letters",
            )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "execution-service/execution_service/v2/router.py",
    "execution-service/execution_service/algo_library/sor_cross_chain.py",
    "execution-service/execution_service/algo_library/sor_twap.py",
    "strategy-service/strategy_service/portfolio_allocator/service.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "CROSS_VENUE_ROUTING_POLICIES",
    "CrossVenueLegRole",
    "CrossVenueRoutingPolicy",
    "PolicyNotFoundError",
    "RoutingPriority",
    "policies_for_settlement_currency",
    "policies_for_venue_pair",
    "routing_policy_for",
]
