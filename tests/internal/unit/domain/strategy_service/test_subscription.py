"""Plan D — StrategyInstanceSubscription invariants + facade exports."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from unified_api_contracts.strategy import (
    ExclusiveLockViolation,
    StrategyInstanceSubscription,
    SubscriptionType,
)


def _now() -> datetime:
    return datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)


def test_dart_exclusive_holds_lock() -> None:
    sub = StrategyInstanceSubscription(
        instance_id="inst_alpha",
        client_id="client_a",
        subscription_type=SubscriptionType.DART_EXCLUSIVE,
        subscribed_at=_now(),
        version_id="v_genesis",
        fork_lineage=("v_genesis",),
        exclusive_lock=True,
    )
    assert sub.exclusive_lock is True
    assert sub.subscription_type is SubscriptionType.DART_EXCLUSIVE


def test_im_allocation_must_not_hold_exclusive_lock() -> None:
    with pytest.raises(ValueError, match="exclusive_lock=True is only valid"):
        StrategyInstanceSubscription(
            instance_id="inst_alpha",
            client_id="client_a",
            subscription_type=SubscriptionType.IM_ALLOCATION,
            subscribed_at=_now(),
            version_id="v_genesis",
            fork_lineage=("v_genesis",),
            exclusive_lock=True,
        )


def test_signals_in_must_not_hold_exclusive_lock() -> None:
    with pytest.raises(ValueError):
        StrategyInstanceSubscription(
            instance_id="inst_alpha",
            client_id="client_a",
            subscription_type=SubscriptionType.SIGNALS_IN,
            subscribed_at=_now(),
            version_id="v_genesis",
            fork_lineage=("v_genesis",),
            exclusive_lock=True,
        )


def test_released_at_after_subscribed_at() -> None:
    now = _now()
    sub = StrategyInstanceSubscription(
        instance_id="inst_alpha",
        client_id="client_a",
        subscription_type=SubscriptionType.DART_EXCLUSIVE,
        subscribed_at=now,
        version_id="v_genesis",
        fork_lineage=("v_genesis",),
        released_at=now + timedelta(hours=1),
        exclusive_lock=False,
    )
    assert sub.released_at is not None


def test_released_at_must_be_strictly_greater() -> None:
    now = _now()
    with pytest.raises(ValueError, match="released_at must be strictly greater"):
        StrategyInstanceSubscription(
            instance_id="inst_alpha",
            client_id="client_a",
            subscription_type=SubscriptionType.DART_EXCLUSIVE,
            subscribed_at=now,
            version_id="v_genesis",
            fork_lineage=("v_genesis",),
            released_at=now,
            exclusive_lock=False,
        )


def test_version_id_must_be_in_fork_lineage() -> None:
    with pytest.raises(ValueError, match="must appear in fork_lineage"):
        StrategyInstanceSubscription(
            instance_id="inst_alpha",
            client_id="client_a",
            subscription_type=SubscriptionType.DART_EXCLUSIVE,
            subscribed_at=_now(),
            version_id="v_other",
            fork_lineage=("v_genesis", "v_draft1"),
            exclusive_lock=True,
        )


def test_empty_fork_lineage_does_not_validate_version_membership() -> None:
    # An empty lineage is allowed — the version_id constraint only fires
    # when a lineage is present.
    sub = StrategyInstanceSubscription(
        instance_id="inst_alpha",
        client_id="client_a",
        subscription_type=SubscriptionType.IM_ALLOCATION,
        subscribed_at=_now(),
        version_id="v_genesis",
        fork_lineage=(),
    )
    assert sub.fork_lineage == ()


def test_exclusive_lock_violation_carries_holder() -> None:
    exc = ExclusiveLockViolation(existing_holder="client_b", instance_id="inst_alpha")
    assert exc.existing_holder == "client_b"
    assert exc.instance_id == "inst_alpha"
    assert "client_b" in str(exc)
    assert "inst_alpha" in str(exc)


def test_subscription_is_frozen() -> None:
    sub = StrategyInstanceSubscription(
        instance_id="inst_alpha",
        client_id="client_a",
        subscription_type=SubscriptionType.DART_EXCLUSIVE,
        subscribed_at=_now(),
        version_id="v_genesis",
        fork_lineage=("v_genesis",),
        exclusive_lock=True,
    )
    with pytest.raises(FrozenInstanceError):
        sub.client_id = "client_b"  # type: ignore[misc]
