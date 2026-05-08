"""Capital allocation matrix SSOT — cross_cutting deliverable #3 (Option A migration).

The cross-cutting May-23 epic frames deliverable #3 as: _"Client model in UAC
stable + capital allocation matrix declared per (client, archetype, venue);
**respected at execution time**."_

This module is the canonical home for the capital + risk envelope half. The
other half — client identity (``Client`` + ``VenueAccount``) — is **not** in
this module: per the Option A migration recorded in
`unified-trading-pm/plans/active/issues/cross_cutting_strategy_catalogue_already_shipped_2026_05_08.md`
the canonical client SSOTs already exist as
:class:`unified_api_contracts.internal.domain.strategy_service.client_registry.ClientDefinition`
(client identity + share-classes + account_type) and
:class:`unified_api_contracts.internal.domain.account.TradingAccount`
(per-venue account + ``WalletRole`` + composite ``client:venue:account_label``
key). Consumers needing client identity import those from
:mod:`unified_api_contracts.strategy` (the existing facade); consumers needing
the capital + risk envelope import :class:`CapitalAllocation` from the same
facade.

This file is the migrated form of code originally shipped in
``uac@3591037`` under ``canonical/domain/client/model.py``. Per the Option A
revert recorded in the issue doc above, the parallel ``Client`` /
``VenueAccount`` / ``ClientId`` / ``AccountId`` / ``ArchetypeRef`` / root
``client.py`` facade were deleted; only :class:`CapitalAllocation` (genuine
gap, no pre-existing UAC SSOT) survives.

Plan-of-record:
``unified-trading-pm/plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #3.

Issue doc:
``unified-trading-pm/plans/active/issues/cross_cutting_strategy_catalogue_already_shipped_2026_05_08.md``
(Option A migration recipe).

**archetype field**: typed as :class:`StrategyArchetype` (the canonical
``unified_api_contracts.internal.architecture_v2.enums.StrategyArchetype``
46-member enum) — tightened from the ``ArchetypeRef = str`` placeholder used
in the pre-revert shape, since the canonical enum is the SSOT for archetypes
across UAC.

**client_id field**: typed as ``str`` (matches
:attr:`ClientDefinition.client_id`). The canonical client identity SSOT is
:class:`unified_api_contracts.internal.domain.strategy_service.client_registry.ClientDefinition`;
allocations reference clients by their ``ClientDefinition.client_id`` string
key.

Companion SSOTs:

* ``unified-trading-pm/codex/09-strategy/cross-cutting/onboarding-checklist.md``
  — onboarding flow that seeds the per-client capital allocation rows.
* ``unified-trading-pm/codex/09-strategy/cross-cutting/client-onboarding.md``
  — operator-facing onboarding playbook.
* ``unified-trading-pm/codex/09-strategy/cross-cutting/client-strategy-config.md``
  — per-client strategy config schema.

**Defaults + temporary state**

:data:`CAPITAL_ALLOCATION_SEED` carries 3 rows covering the May-23 archetype
slice (``CARRY_STAKED_BASIS`` on Aave / Arbitrum, ``CARRY_BASIS_PERP`` on
Bybit, ``ML_DIRECTIONAL_CONTINUOUS`` on Binance). Per the
"Temporary state must have a named successor plan" workspace rule, the
successor plan is the daily work-split's Harsh T6 thread — Harsh's
mechanical-population sweep replaces this seed with the full operator-
approved matrix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

# ---------------------------------------------------------------------------
# AllocationViolationError — exception raised by validate_allocation_respect.
# ---------------------------------------------------------------------------


class AllocationViolationError(Exception):
    """Raised when a proposed position or observed drawdown exceeds the
    per-(client, archetype, venue) :class:`CapitalAllocation` envelope.

    execution-service is the canonical caller. Carries the offending
    allocation + the violated dimension so the alert / kill-switch path has
    full context.
    """


# ---------------------------------------------------------------------------
# CapitalAllocation — per (client_id, archetype, venue) envelope. Validated
# at construction time so seed-time + runtime constructors fail loud on
# malformed bounds. execution-service consumes via :func:`is_within_allocation`
# (advisory) or :func:`validate_allocation_respect` (fail-loud).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapitalAllocation:
    """Capital + risk envelope for a ``(client_id, archetype, venue)`` triple.

    The cross_cutting epic deliverable #3 framing pins the use-case:
    _"respected at execution time"_. execution-service reads via
    :func:`get_capital_allocation` and enforces via
    :func:`validate_allocation_respect` before every order.

    Attributes:
        client_id: Canonical client identifier — matches
            :attr:`ClientDefinition.client_id`. Lowercase, alphanumeric +
            underscore, 1-32 chars by convention. Examples: ``"odum"``,
            ``"ikenna"``.
        archetype: Strategy archetype — a member of
            :class:`unified_api_contracts.internal.architecture_v2.enums.StrategyArchetype`.
        venue: Venue identifier — matches the ``venue`` axis used across
            the workspace's manifest + strategy IDs (e.g. ``"binance"``,
            ``"bybit"``, ``"aave_v3_arbitrum"``). String-keyed because the
            venue universe spans cefi / defi / tradfi / sports / prediction
            and there is no single enum SSOT.
        initial_capital_usd: USD-denominated capital floor for the triple.
            Must be ``> 0``.
        max_position_pct: Maximum fraction of ``initial_capital_usd`` that any
            single open position may consume. Bounded ``0 < x ≤ 1.0`` (1.0 ⇒
            full notional allowed). Default 1.0 (no per-position cap above the
            capital ceiling).
        max_drawdown_pct: Maximum cumulative drawdown fraction before the
            kill-switch trips. Bounded ``0 < x ≤ 1.0``. Default 1.0
            (no drawdown gate beyond capital ceiling).
    """

    client_id: str
    archetype: StrategyArchetype
    venue: str
    initial_capital_usd: float
    max_position_pct: float = 1.0
    max_drawdown_pct: float = 1.0

    def __post_init__(self) -> None:
        if self.initial_capital_usd <= 0:
            msg = (
                f"CapitalAllocation.initial_capital_usd must be > 0, got "
                f"{self.initial_capital_usd!r} for "
                f"({self.client_id!r}, {self.archetype!r}, {self.venue!r})"
            )
            raise ValueError(msg)
        if not 0 < self.max_position_pct <= 1.0:
            msg = (
                f"CapitalAllocation.max_position_pct must be in (0, 1.0], got "
                f"{self.max_position_pct!r} for "
                f"({self.client_id!r}, {self.archetype!r}, {self.venue!r})"
            )
            raise ValueError(msg)
        if not 0 < self.max_drawdown_pct <= 1.0:
            msg = (
                f"CapitalAllocation.max_drawdown_pct must be in (0, 1.0], got "
                f"{self.max_drawdown_pct!r} for "
                f"({self.client_id!r}, {self.archetype!r}, {self.venue!r})"
            )
            raise ValueError(msg)


type AllocationKey = tuple[str, StrategyArchetype, str]
"""``(client_id, archetype, venue)`` triple — the natural key for
:data:`CAPITAL_ALLOCATION_SEED`."""


# ---------------------------------------------------------------------------
# Capital allocation seed — May-23 archetype slice. Harsh T6 (per the
# cross_cutting plan-of-record) extends this with the full operator-approved
# matrix. Until then, unseeded triples raise KeyError on lookup — fail-loud
# matches the "Temporary state must have a named successor plan" rule.
# ---------------------------------------------------------------------------


CAPITAL_ALLOCATION_SEED: Final[dict[AllocationKey, CapitalAllocation]] = {
    # Carry / staked basis — DeFi LST farming on Arbitrum (May-23 lead
    # archetype per master_to_live_defi). Seed cap of $50k matches the
    # paper-trade smoke envelope.
    ("ikenna", StrategyArchetype.CARRY_STAKED_BASIS, "aave_v3_arbitrum"): CapitalAllocation(
        client_id="ikenna",
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        venue="aave_v3_arbitrum",
        initial_capital_usd=50_000.0,
        max_position_pct=0.8,
        max_drawdown_pct=0.15,
    ),
    # Carry / vanilla basis perp — CeFi hedge leg on Bybit. Same $50k envelope.
    ("ikenna", StrategyArchetype.CARRY_BASIS_PERP, "bybit"): CapitalAllocation(
        client_id="ikenna",
        archetype=StrategyArchetype.CARRY_BASIS_PERP,
        venue="bybit",
        initial_capital_usd=50_000.0,
        max_position_pct=0.8,
        max_drawdown_pct=0.15,
    ),
    # CeFi-ML directional — smaller $25k envelope until the ML pipeline ships
    # batch-vs-live reconciliation per Group F readiness criteria.
    ("ikenna", StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS, "binance"): CapitalAllocation(
        client_id="ikenna",
        archetype=StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
        venue="binance",
        initial_capital_usd=25_000.0,
        max_position_pct=0.5,
        max_drawdown_pct=0.10,
    ),
}
"""Per-(client, archetype, venue) capital + risk envelope. Seeds the May-23
cutover archetype slice. **Not the final shape** — Harsh T6 extends with
operator-approved matrix as part of the cross_cutting plan."""


# ---------------------------------------------------------------------------
# Lookups + checks. KeyError on unknown key matches the workspace fail-loud
# default — execution-service should never fire orders against an undeclared
# capital envelope.
# ---------------------------------------------------------------------------


def get_capital_allocation(
    client_id: str,
    archetype: StrategyArchetype,
    venue: str,
) -> CapitalAllocation:
    """Look up a :class:`CapitalAllocation` from :data:`CAPITAL_ALLOCATION_SEED`.

    The execution-service contract is: every order MUST resolve to a declared
    allocation. Calling this with an undeclared triple raises ``KeyError`` —
    callers should not silently fall back to a permissive default.

    Raises:
        KeyError: when ``(client_id, archetype, venue)`` is not in the seed.
    """
    key: AllocationKey = (client_id, archetype, venue)
    if key not in CAPITAL_ALLOCATION_SEED:
        msg = (
            f"No CapitalAllocation declared for "
            f"client_id={client_id!r}, archetype={archetype!r}, venue={venue!r}. "
            f"Add to CAPITAL_ALLOCATION_SEED before any orders fire."
        )
        raise KeyError(msg)
    return CAPITAL_ALLOCATION_SEED[key]


def is_allocation_declared(
    client_id: str,
    archetype: StrategyArchetype,
    venue: str,
) -> bool:
    """Return ``True`` if ``(client_id, archetype, venue)`` has a declared
    :class:`CapitalAllocation`. The advisory companion to
    :func:`get_capital_allocation`'s fail-loud lookup — useful for UI gates
    and pre-flight checks.
    """
    return (client_id, archetype, venue) in CAPITAL_ALLOCATION_SEED


def is_within_allocation(
    allocation: CapitalAllocation,
    position_value_usd: float,
    drawdown_pct: float,
) -> bool:
    """Advisory check — return ``True`` if both the proposed
    ``position_value_usd`` AND the observed ``drawdown_pct`` sit inside the
    allocation envelope.

    This is the canonical entry-point execution-service uses to gate orders
    per cross_cutting epic deliverable #3 _"respected at execution time"_.
    The companion :func:`validate_allocation_respect` raises
    :class:`AllocationViolationError` for fail-loud usage.

    A position is "within" if ``position_value_usd <=
    allocation.initial_capital_usd * allocation.max_position_pct`` AND
    ``drawdown_pct <= allocation.max_drawdown_pct``.
    """
    position_cap_usd = allocation.initial_capital_usd * allocation.max_position_pct
    if position_value_usd > position_cap_usd:
        return False
    return drawdown_pct <= allocation.max_drawdown_pct


def validate_allocation_respect(
    allocation: CapitalAllocation,
    proposed_position_value_usd: float,
    current_drawdown_pct: float,
) -> None:
    """Fail-loud variant of :func:`is_within_allocation`.

    Raises:
        AllocationViolationError: if the proposed position exceeds the
            ``max_position_pct`` cap, OR the current drawdown exceeds
            ``max_drawdown_pct``. The exception message names the violated
            dimension so the alerting / kill-switch path can branch.
    """
    position_cap_usd = allocation.initial_capital_usd * allocation.max_position_pct
    if proposed_position_value_usd > position_cap_usd:
        msg = (
            f"Position {proposed_position_value_usd:.2f} USD exceeds cap "
            f"{position_cap_usd:.2f} USD "
            f"(initial_capital={allocation.initial_capital_usd:.2f} * "
            f"max_position_pct={allocation.max_position_pct}) for "
            f"client_id={allocation.client_id!r}, "
            f"archetype={allocation.archetype!r}, venue={allocation.venue!r}"
        )
        raise AllocationViolationError(msg)
    if current_drawdown_pct > allocation.max_drawdown_pct:
        msg = (
            f"Drawdown {current_drawdown_pct:.4f} exceeds max "
            f"{allocation.max_drawdown_pct} for "
            f"client_id={allocation.client_id!r}, "
            f"archetype={allocation.archetype!r}, venue={allocation.venue!r}"
        )
        raise AllocationViolationError(msg)


__all__ = [
    "CAPITAL_ALLOCATION_SEED",
    "AllocationKey",
    "AllocationViolationError",
    "CapitalAllocation",
    "get_capital_allocation",
    "is_allocation_declared",
    "is_within_allocation",
    "validate_allocation_respect",
]
