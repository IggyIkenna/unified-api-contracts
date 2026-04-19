"""Tests for architecture_v2 strategy availability + lock + maturity (Phase 10.5)."""

from __future__ import annotations

import itertools

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal import (
    ALLOCATION_MIN_MATURITY,
    EXTERNAL_VISIBILITY_MIN_MATURITY,
    STRATEGY_AVAILABILITY_REGISTRY,
    LockState,
    StrategyAvailabilityChangedEvent,
    StrategyAvailabilityEntry,
    StrategyMaturity,
    StrategyMaturityTransitionEvent,
    StrategyNotAvailableError,
    StrategyRetiredError,
    availability_for,
    maturity_rank,
    slots_visible_to,
    validate_allocation_authorised,
)

# ---------------------------------------------------------------------------
# Registry + defaults
# ---------------------------------------------------------------------------


def test_seed_registry_is_empty_tuple() -> None:
    assert STRATEGY_AVAILABILITY_REGISTRY == ()


def test_availability_for_returns_default_public_live_allocated_when_missing() -> None:
    # Default preserves behaviour for already-shipped slots — they can
    # receive capital without a registry row. Explicitly-registered slots
    # with lower maturity override the default.
    entry = availability_for("SLOT_A")
    assert entry.slot_label == "SLOT_A"
    assert entry.lock_state == LockState.PUBLIC
    assert entry.maturity == StrategyMaturity.LIVE_ALLOCATED


def test_availability_for_returns_custom_registry_row() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.INVESTMENT_MANAGEMENT_RESERVED,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            reserving_business_unit_id="fund-alpha",
        )
    ]
    entry = availability_for("SLOT_A", registry=reg)
    assert entry.lock_state == LockState.INVESTMENT_MANAGEMENT_RESERVED
    assert entry.maturity == StrategyMaturity.LIVE_ALLOCATED
    assert entry.reserving_business_unit_id == "fund-alpha"


# ---------------------------------------------------------------------------
# Maturity ordering
# ---------------------------------------------------------------------------


def test_maturity_rank_is_strictly_monotonic() -> None:
    ladder = [
        StrategyMaturity.CODE_NOT_WRITTEN,
        StrategyMaturity.CODE_WRITTEN,
        StrategyMaturity.CODE_AUDITED,
        StrategyMaturity.BACKTESTED,
        StrategyMaturity.PAPER_TRADING,
        StrategyMaturity.PAPER_TRADING_VALIDATED,
        StrategyMaturity.LIVE_TINY,
        StrategyMaturity.LIVE_ALLOCATED,
    ]
    for lo, hi in itertools.pairwise(ladder):
        assert maturity_rank(lo) < maturity_rank(hi)
    assert maturity_rank(ladder[0]) == 0
    assert maturity_rank(ladder[-1]) == len(ladder) - 1


def test_external_threshold_and_allocation_floor_constants() -> None:
    assert EXTERNAL_VISIBILITY_MIN_MATURITY == StrategyMaturity.BACKTESTED
    assert ALLOCATION_MIN_MATURITY == StrategyMaturity.LIVE_TINY


# ---------------------------------------------------------------------------
# Entry consistency validators
# ---------------------------------------------------------------------------


def test_client_exclusive_requires_exclusive_client_id() -> None:
    with pytest.raises(ValueError, match="CLIENT_EXCLUSIVE requires exclusive_client_id"):
        _ = StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.CLIENT_EXCLUSIVE,
        )


def test_exclusive_client_id_not_permitted_when_not_client_exclusive() -> None:
    with pytest.raises(ValueError, match="exclusive_client_id only valid"):
        _ = StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.PUBLIC,
            exclusive_client_id="client-a",
        )


def test_im_reserved_requires_reserving_business_unit() -> None:
    with pytest.raises(ValueError, match="INVESTMENT_MANAGEMENT_RESERVED requires"):
        _ = StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.INVESTMENT_MANAGEMENT_RESERVED,
        )


def test_entry_is_frozen() -> None:
    entry = StrategyAvailabilityEntry(slot_label="SLOT_A")
    with pytest.raises(ValidationError):
        entry.slot_label = "SLOT_B"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# slots_visible_to — per-audience filtering
# ---------------------------------------------------------------------------


def _fixture_registry() -> list[StrategyAvailabilityEntry]:
    return [
        StrategyAvailabilityEntry(
            slot_label="PUBLIC_READY",
            lock_state=LockState.PUBLIC,
            maturity=StrategyMaturity.BACKTESTED,
        ),
        StrategyAvailabilityEntry(
            slot_label="PUBLIC_EARLY",
            lock_state=LockState.PUBLIC,
            maturity=StrategyMaturity.CODE_WRITTEN,  # below audit floor — hidden from IM desk + SaaS
        ),
        StrategyAvailabilityEntry(
            slot_label="IM_RESERVED",
            lock_state=LockState.INVESTMENT_MANAGEMENT_RESERVED,
            maturity=StrategyMaturity.LIVE_TINY,
            reserving_business_unit_id="im-desk-core",
        ),
        StrategyAvailabilityEntry(
            slot_label="CLIENT_ALPHA_ONLY",
            lock_state=LockState.CLIENT_EXCLUSIVE,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            exclusive_client_id="client-alpha",
        ),
        StrategyAvailabilityEntry(
            slot_label="RETIRED_SLOT",
            lock_state=LockState.RETIRED,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
        ),
    ]


def test_admin_sees_everything_including_retired_and_placeholders() -> None:
    reg = _fixture_registry()
    visible = set(slots_visible_to("admin", registry=reg))
    assert visible == {
        "PUBLIC_READY",
        "PUBLIC_EARLY",
        "IM_RESERVED",
        "CLIENT_ALPHA_ONLY",
        "RETIRED_SLOT",
    }


def test_im_desk_sees_full_universe_minus_pre_audit_placeholders() -> None:
    reg = _fixture_registry()
    visible = set(slots_visible_to("im_desk", registry=reg))
    assert "PUBLIC_READY" in visible
    assert "IM_RESERVED" in visible
    assert "CLIENT_ALPHA_ONLY" in visible
    assert "RETIRED_SLOT" in visible
    # Pre-audit placeholder is hidden even from IM desk.
    assert "PUBLIC_EARLY" not in visible


def test_im_client_sees_public_plus_own_exclusive_backtested_plus() -> None:
    reg = _fixture_registry()
    visible = set(slots_visible_to("im_client", client_id="client-alpha", registry=reg))
    assert visible == {"PUBLIC_READY", "CLIENT_ALPHA_ONLY"}


def test_im_client_without_matching_client_id_sees_public_only() -> None:
    reg = _fixture_registry()
    visible = set(slots_visible_to("im_client", client_id="client-beta", registry=reg))
    assert visible == {"PUBLIC_READY"}


def test_trading_platform_subscriber_hides_im_reserved() -> None:
    reg = _fixture_registry()
    visible = set(
        slots_visible_to(
            "trading_platform_subscriber",
            client_id="client-alpha",
            registry=reg,
        )
    )
    assert "IM_RESERVED" not in visible
    assert "RETIRED_SLOT" not in visible
    assert "PUBLIC_READY" in visible
    assert "CLIENT_ALPHA_ONLY" in visible


def test_slots_visible_to_includes_defaulted_labels_from_known_set() -> None:
    reg: list[StrategyAvailabilityEntry] = []
    known = ["UNREGISTERED_A", "UNREGISTERED_B"]
    visible = set(
        slots_visible_to(
            "trading_platform_subscriber",
            client_id="c",
            registry=reg,
            known_slot_labels=known,
        )
    )
    # Default is (PUBLIC, LIVE_ALLOCATED) → visible to subscribers (>= BACKTESTED threshold).
    assert visible == {"UNREGISTERED_A", "UNREGISTERED_B"}


# ---------------------------------------------------------------------------
# validate_allocation_authorised — enforcement
# ---------------------------------------------------------------------------


def test_validate_rejects_retired() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.RETIRED,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
        )
    ]
    with pytest.raises(StrategyRetiredError):
        validate_allocation_authorised("SLOT_A", "client-a", "saas", registry=reg)


def test_validate_rejects_below_maturity_floor() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.PUBLIC,
            maturity=StrategyMaturity.PAPER_TRADING_VALIDATED,
        )
    ]
    with pytest.raises(StrategyNotAvailableError, match="maturity"):
        validate_allocation_authorised("SLOT_A", "client-a", "saas", registry=reg)


def test_validate_default_slot_allows_allocation() -> None:
    # Default fallback (PUBLIC + LIVE_ALLOCATED) preserves behaviour for
    # already-shipped slots — they allocate without a registry row.
    validate_allocation_authorised("UNKNOWN_SLOT", "client-a", "saas")


def test_validate_rejects_saas_on_im_reserved() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.INVESTMENT_MANAGEMENT_RESERVED,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            reserving_business_unit_id="fund-1",
        )
    ]
    with pytest.raises(StrategyNotAvailableError, match="IM-reserved"):
        validate_allocation_authorised("SLOT_A", "client-a", "saas", registry=reg)


def test_validate_allows_im_desk_on_im_reserved() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.INVESTMENT_MANAGEMENT_RESERVED,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            reserving_business_unit_id="fund-1",
        )
    ]
    validate_allocation_authorised("SLOT_A", "fund-1", "im_desk", registry=reg)


def test_validate_rejects_saas_on_client_exclusive_wrong_client() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.CLIENT_EXCLUSIVE,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            exclusive_client_id="client-a",
        )
    ]
    with pytest.raises(StrategyNotAvailableError, match="client-exclusive"):
        validate_allocation_authorised("SLOT_A", "client-b", "saas", registry=reg)


def test_validate_allows_saas_on_own_client_exclusive() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.CLIENT_EXCLUSIVE,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            exclusive_client_id="client-a",
        )
    ]
    validate_allocation_authorised("SLOT_A", "client-a", "saas", registry=reg)


def test_validate_rejects_im_desk_on_client_exclusive_observe_only() -> None:
    """IM desk can SEE a client-exclusive slot for oversight but cannot allocate new capital."""
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.CLIENT_EXCLUSIVE,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            exclusive_client_id="client-a",
        )
    ]
    with pytest.raises(StrategyNotAvailableError, match="observe-only"):
        validate_allocation_authorised("SLOT_A", "im-desk-1", "im_desk", registry=reg)


def test_validate_allows_admin_on_any_non_retired_non_placeholder() -> None:
    reg = [
        StrategyAvailabilityEntry(
            slot_label="SLOT_A",
            lock_state=LockState.CLIENT_EXCLUSIVE,
            maturity=StrategyMaturity.LIVE_ALLOCATED,
            exclusive_client_id="client-a",
        )
    ]
    validate_allocation_authorised("SLOT_A", "admin-1", "admin", registry=reg)


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


def test_availability_changed_event_roundtrip() -> None:
    ev = StrategyAvailabilityChangedEvent(
        slot_label="SLOT_A",
        prior_lock_state=LockState.PUBLIC,
        new_lock_state=LockState.CLIENT_EXCLUSIVE,
        prior_maturity=StrategyMaturity.LIVE_ALLOCATED,
        new_maturity=StrategyMaturity.LIVE_ALLOCATED,
        new_exclusive_client_id="client-a",
        reason="contract signed",
        actor_id="admin-1",
        changed_at_utc="2026-04-19T12:00:00Z",
    )
    assert ev.event_type == "STRATEGY_AVAILABILITY_CHANGED"


def test_maturity_transition_event_advance_and_regress() -> None:
    advance = StrategyMaturityTransitionEvent(
        event_type="STRATEGY_MATURITY_ADVANCED",
        slot_label="SLOT_A",
        prior_maturity=StrategyMaturity.PAPER_TRADING,
        new_maturity=StrategyMaturity.PAPER_TRADING_VALIDATED,
        reason="14-day window cleared",
        actor_id="watchdog",
        changed_at_utc="2026-04-19T12:00:00Z",
    )
    assert advance.event_type == "STRATEGY_MATURITY_ADVANCED"

    regress = StrategyMaturityTransitionEvent(
        event_type="STRATEGY_MATURITY_REGRESSED",
        slot_label="SLOT_A",
        prior_maturity=StrategyMaturity.LIVE_TINY,
        new_maturity=StrategyMaturity.PAPER_TRADING,
        reason="data quality incident",
        actor_id="admin-1",
        changed_at_utc="2026-04-19T12:00:00Z",
    )
    assert regress.event_type == "STRATEGY_MATURITY_REGRESSED"
