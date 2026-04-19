"""Strategy availability + lock state + maturity registry.

Phase 10.5 of ``strategy_architecture_v2_finalization_2026_04_19``. SSOT:
``unified-trading-pm/codex/09-strategy/architecture-v2/cross-cutting/strategy-availability-and-locking.md``.

Two orthogonal dimensions ride on every slot:

* ``lock_state`` — who is allowed to see/use the slot at all (SaaS vs IM
  business-model gate). Four values.
* ``maturity`` — how production-ready the slot is, independent of lock
  state. Drives the internal-vs-external visibility threshold. Eight
  monotonic values, advanced automatically by the strategy-service
  maturity watchdog.

Filter helpers (``slots_visible_to``, ``validate_allocation_authorised``)
gate on BOTH dimensions — e.g. an IM-client only sees PUBLIC or their
own CLIENT_EXCLUSIVE slots that are also ``maturity >= BACKTESTED``.

Slots that do not appear in ``STRATEGY_AVAILABILITY_REGISTRY`` default to
``(PUBLIC, BACKTESTED)`` so behaviour is unchanged for already-shipped
slots.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LockState(StrEnum):
    """Business-model gate. Who is allowed to see/use the slot at all."""

    PUBLIC = "PUBLIC"
    INVESTMENT_MANAGEMENT_RESERVED = "INVESTMENT_MANAGEMENT_RESERVED"
    CLIENT_EXCLUSIVE = "CLIENT_EXCLUSIVE"
    RETIRED = "RETIRED"


class StrategyMaturity(StrEnum):
    """Monotonic production-readiness ladder.

    Order matters: ``CODE_NOT_WRITTEN`` < ``CODE_WRITTEN`` < ... <
    ``LIVE_ALLOCATED``. Use :func:`maturity_rank` to compare.
    """

    CODE_NOT_WRITTEN = "CODE_NOT_WRITTEN"
    CODE_WRITTEN = "CODE_WRITTEN"
    CODE_AUDITED = "CODE_AUDITED"
    BACKTESTED = "BACKTESTED"
    PAPER_TRADING = "PAPER_TRADING"
    PAPER_TRADING_VALIDATED = "PAPER_TRADING_VALIDATED"
    LIVE_TINY = "LIVE_TINY"
    LIVE_ALLOCATED = "LIVE_ALLOCATED"


_MATURITY_ORDER: tuple[StrategyMaturity, ...] = (
    StrategyMaturity.CODE_NOT_WRITTEN,
    StrategyMaturity.CODE_WRITTEN,
    StrategyMaturity.CODE_AUDITED,
    StrategyMaturity.BACKTESTED,
    StrategyMaturity.PAPER_TRADING,
    StrategyMaturity.PAPER_TRADING_VALIDATED,
    StrategyMaturity.LIVE_TINY,
    StrategyMaturity.LIVE_ALLOCATED,
)


def maturity_rank(m: StrategyMaturity) -> int:
    """Return the zero-based rank of ``m`` within the monotonic ladder."""

    return _MATURITY_ORDER.index(m)


# Audience → surface map. Consumers pass the audience string into
# ``slots_visible_to`` / ``validate_allocation_authorised``.
Audience = Literal[
    "admin",
    "im_desk",
    "im_client",
    "trading_platform_subscriber",
]


# External-visibility threshold — slots below this maturity are hidden
# from every non-internal audience. Internal ``admin``/``im_desk``
# surfaces see everything.
EXTERNAL_VISIBILITY_MIN_MATURITY: StrategyMaturity = StrategyMaturity.BACKTESTED

# Minimum maturity the allocator will push capital to. Slots below this
# raise ``StrategyNotAvailableError`` even when the lock state permits.
ALLOCATION_MIN_MATURITY: StrategyMaturity = StrategyMaturity.LIVE_TINY


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StrategyNotAvailableError(Exception):
    """Raised when a ``(client_id, business_unit)`` is not authorised to
    allocate to ``slot_label`` given its ``(lock_state, maturity)``."""

    def __init__(self, slot_label: str, reason: str) -> None:
        super().__init__(f"strategy not available: {slot_label!r} ({reason})")
        self.slot_label = slot_label
        self.reason = reason


class StrategyRetiredError(StrategyNotAvailableError):
    """Raised when a slot is ``RETIRED`` — no allocation, no iteration."""

    def __init__(self, slot_label: str) -> None:
        super().__init__(slot_label, reason="retired")


# ---------------------------------------------------------------------------
# Registry entry
# ---------------------------------------------------------------------------


class StrategyAvailabilityEntry(BaseModel):
    """One row per slot_label in the availability registry.

    Defaults preserve behaviour for slots that do not yet have an
    explicit registry row — they are ``PUBLIC`` + ``LIVE_ALLOCATED``, so
    the allocator allows capital flow and the catalogue shows them in
    every audience. New slots intentionally added at lower maturity via
    admin toggles or the watchdog's seed will gate correctly.

    Rationale: existing production slots are already live-allocated as
    of Phase 10.5 cutover. The plan's "no behavioural change at launch"
    requirement is met by defaulting the fallback to the top of the
    maturity ladder. Catalogue UI filters (BACKTESTED threshold) are a
    separate concern applied by ``slots_visible_to``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_label: str
    lock_state: LockState = LockState.PUBLIC
    maturity: StrategyMaturity = StrategyMaturity.LIVE_ALLOCATED

    # Populated when lock_state == CLIENT_EXCLUSIVE. Exactly one client_id per exclusive slot.
    exclusive_client_id: str | None = None
    # Populated when lock_state == INVESTMENT_MANAGEMENT_RESERVED. Which fund/desk claimed it.
    reserving_business_unit_id: str | None = None
    # ISO 8601 timestamp of the most recent lock_state OR maturity transition.
    changed_at_utc: str = ""
    # Human-readable reason (e.g. "bespoke contract with Acme Fund" / "14-day PROMOTE").
    reason: str = ""
    # For time-bounded locks. None for open-ended.
    expires_at_utc: str | None = None
    # Base slot this row derives from; used when minting v{N+1} locked variants
    # while keeping the PUBLIC base running.
    base_slot_label: str | None = None

    @model_validator(mode="after")
    def _consistency(self) -> StrategyAvailabilityEntry:
        if self.lock_state == LockState.CLIENT_EXCLUSIVE and not self.exclusive_client_id:
            raise ValueError("CLIENT_EXCLUSIVE requires exclusive_client_id")
        if self.lock_state != LockState.CLIENT_EXCLUSIVE and self.exclusive_client_id:
            raise ValueError("exclusive_client_id only valid when lock_state == CLIENT_EXCLUSIVE")
        if self.lock_state == LockState.INVESTMENT_MANAGEMENT_RESERVED and not self.reserving_business_unit_id:
            raise ValueError("INVESTMENT_MANAGEMENT_RESERVED requires reserving_business_unit_id")
        return self


# Seed tuple — most slots use the default entry and do not need a row.
# Operator-minted locks + watchdog-driven maturity advancements are
# layered on at runtime by ``strategy_service.availability`` stores.
STRATEGY_AVAILABILITY_REGISTRY: tuple[StrategyAvailabilityEntry, ...] = ()


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


class StrategyAvailabilityChangedEvent(BaseModel):
    """Fired on every lock_state OR maturity transition.

    Distinct from ``STRATEGY_LOCKED`` / ``STRATEGY_UNLOCKED`` /
    ``STRATEGY_MATURITY_ADVANCED`` / ``STRATEGY_MATURITY_REGRESSED``
    which are narrower signals. Consumers that want a single stream
    subscribe to this umbrella event.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: Literal["STRATEGY_AVAILABILITY_CHANGED"] = "STRATEGY_AVAILABILITY_CHANGED"
    slot_label: str
    prior_lock_state: LockState
    new_lock_state: LockState
    prior_maturity: StrategyMaturity
    new_maturity: StrategyMaturity
    prior_exclusive_client_id: str | None = None
    new_exclusive_client_id: str | None = None
    reason: str
    actor_id: str
    changed_at_utc: str
    correlation_id: str = ""


class StrategyMaturityTransitionEvent(BaseModel):
    """Narrow event: maturity changed (either direction).

    ``STRATEGY_MATURITY_ADVANCED`` when new_rank > prior_rank,
    ``STRATEGY_MATURITY_REGRESSED`` when new_rank < prior_rank. Event
    type is set by the emitter; the payload shape is shared.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: Literal[
        "STRATEGY_MATURITY_ADVANCED",
        "STRATEGY_MATURITY_REGRESSED",
    ]
    slot_label: str
    prior_maturity: StrategyMaturity
    new_maturity: StrategyMaturity
    reason: str
    actor_id: str
    changed_at_utc: str
    correlation_id: str = ""


# ---------------------------------------------------------------------------
# Pure query helpers (stateless — consult the passed-in registry only)
# ---------------------------------------------------------------------------


def availability_for(
    slot_label: str,
    registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
) -> StrategyAvailabilityEntry:
    """Return the entry for ``slot_label`` or the default PUBLIC / BACKTESTED row.

    Consumers that layer admin overrides + watchdog-driven maturity
    advancements on top of the static seed pass their own ``registry``
    iterable — typically a snapshot of a mutable availability store.
    """

    for entry in registry:
        if entry.slot_label == slot_label:
            return entry
    return StrategyAvailabilityEntry(slot_label=slot_label)


def slots_visible_to(
    audience: Audience,
    client_id: str | None = None,
    registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
    known_slot_labels: Iterable[str] | None = None,
) -> Iterator[str]:
    """Yield slot labels the audience is authorised to see.

    ``registry`` supplies explicit rows; slots not present default to
    ``PUBLIC / BACKTESTED``. ``known_slot_labels`` is an optional
    extension of the iteration set — caller passes in every slot in the
    universe (e.g. the coverage-matrix keys) when they also want to see
    defaulted rows, not only explicitly-registered ones.
    """

    slots_by_label: dict[str, StrategyAvailabilityEntry] = {e.slot_label: e for e in registry}
    if known_slot_labels is not None:
        for label in known_slot_labels:
            slots_by_label.setdefault(label, StrategyAvailabilityEntry(slot_label=label))

    for entry in slots_by_label.values():
        if _visible(entry, audience=audience, client_id=client_id):
            yield entry.slot_label


def _visible(
    entry: StrategyAvailabilityEntry,
    *,
    audience: Audience,
    client_id: str | None,
) -> bool:
    if audience == "admin":
        # Admin sees everything — retired included so historical views render.
        return True

    # im_desk sees full universe minus pre-audit placeholders.
    # Retired slots stay visible to IM desk for audit context.
    if audience == "im_desk":
        return maturity_rank(entry.maturity) >= maturity_rank(StrategyMaturity.CODE_AUDITED)

    # Everyone else: external-visibility threshold + no retired.
    if maturity_rank(entry.maturity) < maturity_rank(EXTERNAL_VISIBILITY_MIN_MATURITY):
        return False
    if entry.lock_state == LockState.RETIRED:
        return False

    if audience == "im_client":
        if entry.lock_state == LockState.PUBLIC:
            return True
        if entry.lock_state == LockState.CLIENT_EXCLUSIVE:
            return entry.exclusive_client_id == client_id
        # IM_RESERVED is hidden from IM clients.
        return False

    if audience == "trading_platform_subscriber":
        if entry.lock_state == LockState.PUBLIC:
            return True
        if entry.lock_state == LockState.CLIENT_EXCLUSIVE:
            return entry.exclusive_client_id == client_id
        # IM_RESERVED is hidden from DIY subscribers.
        return False

    return False


def validate_allocation_authorised(
    slot_label: str,
    client_id: str,
    business_unit: Literal["saas", "im_desk", "admin"],
    registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
) -> None:
    """Raise ``StrategyNotAvailableError`` if the caller cannot allocate.

    Called from ``portfolio-allocator`` for every strategy in an outgoing
    ``AllocationDirective``. ``business_unit`` identifies which side of
    the business owns the allocator instance — SaaS clients hit
    ``"saas"``, investment-management desks hit ``"im_desk"``, admin
    overrides hit ``"admin"``.
    """

    entry = availability_for(slot_label, registry=registry)

    if entry.lock_state == LockState.RETIRED:
        raise StrategyRetiredError(slot_label)

    # Maturity floor: allocator cannot push capital to a slot that has
    # not been live-traded at least tiny size. Applies to every BU.
    if maturity_rank(entry.maturity) < maturity_rank(ALLOCATION_MIN_MATURITY):
        raise StrategyNotAvailableError(
            slot_label,
            reason=f"maturity {entry.maturity.value} < {ALLOCATION_MIN_MATURITY.value}",
        )

    if entry.lock_state == LockState.INVESTMENT_MANAGEMENT_RESERVED and business_unit != "im_desk":
        raise StrategyNotAvailableError(slot_label, reason="IM-reserved")

    if entry.lock_state == LockState.CLIENT_EXCLUSIVE:
        if business_unit == "im_desk":
            # IM may observe but cannot allocate new capital to a client-exclusive slot.
            raise StrategyNotAvailableError(slot_label, reason="client-exclusive (IM observe-only)")
        if business_unit == "admin":
            return
        if client_id != entry.exclusive_client_id:
            raise StrategyNotAvailableError(slot_label, reason="client-exclusive")


__all__ = [
    "ALLOCATION_MIN_MATURITY",
    "EXTERNAL_VISIBILITY_MIN_MATURITY",
    "STRATEGY_AVAILABILITY_REGISTRY",
    "Audience",
    "LockState",
    "StrategyAvailabilityChangedEvent",
    "StrategyAvailabilityEntry",
    "StrategyMaturity",
    "StrategyMaturityTransitionEvent",
    "StrategyNotAvailableError",
    "StrategyRetiredError",
    "availability_for",
    "maturity_rank",
    "slots_visible_to",
    "validate_allocation_authorised",
]
