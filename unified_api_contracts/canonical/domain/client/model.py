"""Client model + capital allocation matrix SSOT — cross_cutting deliverable #3.

The cross-cutting May-23 epic frames deliverable #3 as: _"Client model in UAC
stable + capital allocation matrix declared per (client, archetype, venue);
**respected at execution time**."_ This module is the canonical home for both
halves: the :class:`Client` shape (a client owns one or more
:class:`VenueAccount` entries — main + optional sub-accounts) and the
:class:`CapitalAllocation` shape (per ``(client_id, archetype, venue)`` triple
the operator-declared capital + position-cap + drawdown-cap that
execution-service reads at order time).

Plan:
``unified-trading-pm/plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #3.

Companion SSOTs:

* ``unified-trading-pm/codex/09-strategy/cross-cutting/onboarding-checklist.md``
  — the onboarding flow that creates each :class:`VenueAccount` and seeds the
  per-client capital allocation rows. The atomic unit of execution is the
  ``(strategy_id, client_id, config)`` triple.
* ``unified-trading-pm/codex/09-strategy/cross-cutting/client-onboarding.md``
  — operator-facing onboarding playbook.
* ``unified-trading-pm/codex/09-strategy/cross-cutting/client-strategy-config.md``
  — the per-client strategy config schema.

**Credential convention** (per CLAUDE.md "DeFi Execution Architecture →
Interface credential convention"). Clients have venue accounts; accounts have
credentials in Google Secret Manager fetched at runtime via
``ApiKeyReloader`` from UTL. The naming convention from
``onboarding-checklist.md`` Phase 1.2 is:

* ``{client_id}-{venue}-api-key`` — CeFi REST API key (e.g. ``odum-binance-api-key``)
* ``{client_id}-{venue}-api-secret`` — CeFi REST API secret
* ``{client_id}-defi-wallet-private-key`` — DeFi wallet private key
* ``{client_id}-{venue}-passphrase`` — venue-specific passphrase (OKX-style)

This module does NOT carry any credentials — it carries only the identity +
metadata needed to look credentials up in Secret Manager via the convention
above, plus the capital-cap envelope execution-service enforces at order time.

**Wave / scope notes**

* Wave 4 / slice (a) — schema floor only. Seed dictionaries below carry the
  May-23 cutover slice; per-client rollout extends them as new
  ``(client, archetype, venue)`` triples come online.
* The ``archetype`` axis is currently typed as :data:`ArchetypeRef`
  (= ``str``) because Sub-agent 6.A's strategy catalogue UAC is shipping in
  parallel. When that lands, :data:`ArchetypeRef` widens to
  ``"StrategyArchetype | str"`` (or tightens to ``StrategyArchetype``) in a
  single TypeAlias edit — no other call-site churn. Follow-up plan: the
  cross_cutting May-23 deliverables Open Questions section.

**Defaults + temporary state**

* :data:`CLIENTS_SEED` carries an ``ikenna`` placeholder client with one
  :class:`VenueAccount` per live CeFi venue (Bybit / Deribit / Binance / OKX) +
  a single DeFi wallet entry. Per-client onboarding extends this seed.
* :data:`CAPITAL_ALLOCATION_SEED` carries 3 rows covering the May-23 archetype
  slice (``carry_staked_basis`` on Aave / Arbitrum, ``carry_basis_perp`` on
  Bybit, ``ml_directional_continuous`` on Binance). Per the
  "Temporary state must have a named successor plan" workspace rule, the
  successor plan is the daily work-split's Harsh T6 thread — Harsh's
  mechanical-population sweep replaces this seed with the full operator-
  approved matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

# When Sub-agent 6.A ships
# ``unified_api_contracts.canonical.domain.strategy.catalogue.StrategyArchetype``,
# widen this alias to ``str | "StrategyArchetype"`` (or tighten to the enum
# directly). Single edit; every call-site picks up the change automatically
# because every consumer signature uses :data:`ArchetypeRef`.
type ArchetypeRef = str
"""Strategy archetype reference. Currently ``str`` (slugs like
``"carry_staked_basis"``); widens to ``str | StrategyArchetype`` once 6.A's
catalogue UAC lands."""


# ---------------------------------------------------------------------------
# Identity primitives — TypeAlias for clarity. Lowercase, alphanumeric +
# underscore, 1-32 chars. Documented bounds; no runtime validation here so
# constructors stay zero-cost (call sites validate at boundary if they want
# strict checks).
# ---------------------------------------------------------------------------


type ClientId = str
"""Canonical client identifier — lowercase, alphanumeric + underscore, 1-32
chars. Examples: ``"odum"``, ``"ikenna"``. Used as the prefix in Secret Manager
secret names — see module docstring for naming convention."""


type AccountId = str
"""Per-venue account identifier. May be the venue-native account id (Bybit
uid / Deribit user / Binance master uid) or a composite ``client:venue:label``
key for multi-strategy isolation per ``onboarding-checklist.md`` Phase 1.1."""


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
# VenueAccount — one row per (client, venue) (or per sub-account when the
# client splits exposure across isolated-margin sub-accounts).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VenueAccount:
    """A client's account at one venue. Frozen + hashable so it can be a key
    in dicts or a member of sets.

    Attributes:
        venue: Canonical venue identifier (e.g. ``"binance"``, ``"bybit"``,
            ``"aave_v3_arbitrum"``). Matches the ``venue`` axis used across
            the workspace's manifest + strategy IDs.
        account_id: Venue-native or composite account id (see
            :data:`AccountId`).
        is_subaccount: ``True`` when this row represents a sub-account under a
            parent. Default ``False``.
        parent_account_id: When ``is_subaccount`` is ``True``, this points at
            the parent main-account id. ``None`` for main accounts.
    """

    venue: str
    account_id: AccountId
    is_subaccount: bool = False
    parent_account_id: AccountId | None = None


# ---------------------------------------------------------------------------
# Client — one row per onboarded client. The accounts tuple is canonical;
# helper accessors avoid forcing call sites into tuple comprehensions.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Client:
    """An onboarded client.

    Frozen so :class:`Client` instances can be referenced from other frozen
    dataclasses (and sit in caches) without copy semantics. The ``accounts``
    field is a tuple — Python's frozen-dataclass + hashability requires
    immutable members.

    Attributes:
        client_id: See :data:`ClientId`.
        display_name: Human-readable label for operator UI rendering. NOT
            used for any keying or lookup — those go through ``client_id``.
        accounts: Tuple of :class:`VenueAccount`. Includes both main accounts
            and any sub-accounts (sub-accounts are flagged via
            ``is_subaccount=True``).
    """

    client_id: ClientId
    display_name: str
    accounts: tuple[VenueAccount, ...] = field(default_factory=tuple)

    def accounts_for_venue(self, venue: str) -> tuple[VenueAccount, ...]:
        """Return all of this client's accounts (main + sub-accounts) for the
        given ``venue``. Empty tuple if the client has no accounts at the
        venue.
        """
        return tuple(account for account in self.accounts if account.venue == venue)


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
        client_id: See :data:`ClientId`.
        archetype: Strategy archetype slug — see module docstring "Wave / scope
            notes". When 6.A's :class:`StrategyArchetype` enum lands, callers
            may pass enum members directly.
        venue: Venue identifier; must match the ``venue`` axis on
            :class:`VenueAccount`.
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

    client_id: ClientId
    archetype: ArchetypeRef
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


type AllocationKey = tuple[ClientId, ArchetypeRef, str]
"""``(client_id, archetype, venue)`` triple — the natural key for
:data:`CAPITAL_ALLOCATION_SEED`."""


# ---------------------------------------------------------------------------
# Seeded clients — initial onboarding scope for the May-23 cutover. Per-client
# onboarding via the onboarding-checklist Phase 1 extends this seed.
#
# NOTE: account_id values below are PLACEHOLDERS — operator-team replaces with
# real venue-native account ids during Phase 1.1 of onboarding. Placeholder
# shape is ``"<client>-<venue>-main"`` so it's obvious the operator hasn't
# overwritten them yet.
# ---------------------------------------------------------------------------


CLIENTS_SEED: Final[tuple[Client, ...]] = (
    Client(
        client_id="ikenna",
        display_name="Ikenna",
        accounts=(
            # 4 live CeFi venues from the May-23 master plan.
            VenueAccount(venue="bybit", account_id="ikenna-bybit-main"),
            VenueAccount(venue="deribit", account_id="ikenna-deribit-main"),
            VenueAccount(venue="binance", account_id="ikenna-binance-main"),
            VenueAccount(venue="okx", account_id="ikenna-okx-main"),
            # Live DeFi wallets per chain — credentials shared across wallets
            # but each chain has its own account_id for position tracking.
            VenueAccount(venue="aave_v3_arbitrum", account_id="ikenna-defi-arbitrum"),
            VenueAccount(venue="aave_v3_base", account_id="ikenna-defi-base"),
            VenueAccount(venue="aave_v3_polygon", account_id="ikenna-defi-polygon"),
        ),
    ),
)
"""Initial seeded clients for the May-23 cutover. Per-client onboarding
extends — see ``onboarding-checklist.md`` Phase 1 for the operator process."""


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
    ("ikenna", "carry_staked_basis", "aave_v3_arbitrum"): CapitalAllocation(
        client_id="ikenna",
        archetype="carry_staked_basis",
        venue="aave_v3_arbitrum",
        initial_capital_usd=50_000.0,
        max_position_pct=0.8,
        max_drawdown_pct=0.15,
    ),
    # Carry / vanilla basis perp — CeFi hedge leg on Bybit. Same $50k envelope.
    ("ikenna", "carry_basis_perp", "bybit"): CapitalAllocation(
        client_id="ikenna",
        archetype="carry_basis_perp",
        venue="bybit",
        initial_capital_usd=50_000.0,
        max_position_pct=0.8,
        max_drawdown_pct=0.15,
    ),
    # CeFi-ML directional — smaller $25k envelope until the ML pipeline ships
    # batch-vs-live reconciliation per Group F readiness criteria.
    ("ikenna", "ml_directional_continuous", "binance"): CapitalAllocation(
        client_id="ikenna",
        archetype="ml_directional_continuous",
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


def get_client(client_id: ClientId) -> Client:
    """Look up a :class:`Client` from :data:`CLIENTS_SEED` by ``client_id``.

    Raises:
        KeyError: when ``client_id`` is not present in the seed.
    """
    for client in CLIENTS_SEED:
        if client.client_id == client_id:
            return client
    msg = f"Unknown client_id={client_id!r}; seeded clients: {tuple(c.client_id for c in CLIENTS_SEED)}"
    raise KeyError(msg)


def get_capital_allocation(
    client_id: ClientId,
    archetype: ArchetypeRef,
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
    client_id: ClientId,
    archetype: ArchetypeRef,
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
    "CLIENTS_SEED",
    "AccountId",
    "AllocationKey",
    "AllocationViolationError",
    "ArchetypeRef",
    "CapitalAllocation",
    "Client",
    "ClientId",
    "VenueAccount",
    "get_capital_allocation",
    "get_client",
    "is_allocation_declared",
    "is_within_allocation",
    "validate_allocation_respect",
]
