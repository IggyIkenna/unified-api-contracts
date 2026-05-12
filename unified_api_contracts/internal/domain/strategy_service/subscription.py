"""Plan D — Strategy-instance subscription record + DART exclusive-lock semantics.

Three subscription types coexist on a single ``StrategyInstance``:

  * ``DART_EXCLUSIVE`` — at most ONE active per instance (exclusive_lock=True);
    the holder is the only DART client owning the strategy's config and is the
    only client with research-fork rights.
  * ``IM_ALLOCATION`` — pooled / SMA allocations; any number coexist on the
    same instance. Never holds the exclusive lock.
  * ``SIGNALS_IN`` — counterparty consumes the Odum-owned signal feed;
    coexists with both of the above. Never forks.

SSOT:
    plans/active/dart_exclusive_subscription_research_fork_2026_04_21.md
    codex/09-strategy/architecture-v2/dart-exclusive-research-fork.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

__all__ = [
    "ExclusiveLockViolation",
    "StrategyInstanceSubscription",
    "SubscriptionType",
]


class SubscriptionType(StrEnum):
    """Mutually-exclusive subscription product types."""

    DART_EXCLUSIVE = "dart_exclusive"
    IM_ALLOCATION = "im_allocation"
    SIGNALS_IN = "signals_in"


class ExclusiveLockViolation(Exception):
    """Raised when a DART_EXCLUSIVE create would collide with an existing holder.

    Carries enough context for HTTP layers to convert into a 409 with a
    helpful body and for UTL events to log who currently holds the lock.
    """

    existing_holder: str
    instance_id: str

    def __init__(self, existing_holder: str, instance_id: str) -> None:
        self.existing_holder = existing_holder
        self.instance_id = instance_id
        super().__init__(
            f"instance_id={instance_id} is already held under DART_EXCLUSIVE "
            f"by client_id={existing_holder}; release before re-subscribing."
        )


@dataclass(frozen=True)
class StrategyInstanceSubscription:
    """Frozen subscription record.

    Lifecycle:
      - Created when a client subscribes (released_at=None, exclusive_lock per type).
      - On release, the store writes a NEW frozen record with released_at set
        and exclusive_lock=False (the lock follows the active row).
      - ``fork_lineage`` orders the version IDs the subscriber has touched —
        starts as ``(genesis_version_id,)`` and grows on each fork.
    """

    instance_id: str
    client_id: str
    subscription_type: SubscriptionType
    subscribed_at: datetime
    version_id: str
    fork_lineage: tuple[str, ...] = field(default_factory=tuple)
    released_at: datetime | None = None
    exclusive_lock: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.exclusive_lock and self.subscription_type is not SubscriptionType.DART_EXCLUSIVE:
            raise ValueError(
                "exclusive_lock=True is only valid for subscription_type=DART_EXCLUSIVE; "
                f"got {self.subscription_type.value}."
            )
        if self.released_at is not None and self.released_at <= self.subscribed_at:
            raise ValueError(
                "released_at must be strictly greater than subscribed_at; "
                f"subscribed_at={self.subscribed_at.isoformat()} "
                f"released_at={self.released_at.isoformat()}."
            )
        if self.fork_lineage and self.version_id not in self.fork_lineage:
            raise ValueError(
                f"version_id={self.version_id} must appear in fork_lineage="
                f"{self.fork_lineage} (the active version is part of its own lineage)."
            )
