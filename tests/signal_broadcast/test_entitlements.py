"""Unit tests for :class:`RateLimitConfig`, :class:`CounterpartyEntitlement`
and :class:`CounterpartyEntitlementProfile`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts.signal_broadcast import (
    CounterpartyEntitlement,
    CounterpartyEntitlementProfile,
    PayloadDepth,
    RateLimitConfig,
)


class TestRateLimitConfig:
    def test_valid(self) -> None:
        cfg = RateLimitConfig(name="rl-default", requests_per_second=10.0, burst=20)
        assert cfg.name == "rl-default"

    def test_rejects_zero_rps(self) -> None:
        with pytest.raises(ValidationError):
            RateLimitConfig(name="rl", requests_per_second=0.0, burst=5)

    def test_rejects_zero_burst(self) -> None:
        with pytest.raises(ValidationError):
            RateLimitConfig(name="rl", requests_per_second=1.0, burst=0)

    def test_frozen(self) -> None:
        cfg = RateLimitConfig(name="rl", requests_per_second=1.0, burst=1)
        with pytest.raises(ValidationError):
            cfg.burst = 99  # type: ignore[misc]

    def test_roundtrip(self) -> None:
        cfg = RateLimitConfig(name="rl", requests_per_second=5.5, burst=10)
        rebuilt = RateLimitConfig.model_validate(cfg.model_dump(mode="json"))
        assert rebuilt == cfg


class TestCounterpartyEntitlement:
    def test_open_ended(self) -> None:
        ent = CounterpartyEntitlement(
            counterparty_id="cp-1",
            slot_label="slot-a",
            active_from=datetime(2026, 9, 1, tzinfo=UTC),
        )
        assert ent.active_to is None

    def test_windowed(self) -> None:
        ent = CounterpartyEntitlement(
            counterparty_id="cp-1",
            slot_label="slot-a",
            active_from=datetime(2026, 9, 1, tzinfo=UTC),
            active_to=datetime(2027, 9, 1, tzinfo=UTC),
        )
        assert ent.active_to is not None

    def test_empty_slot_label_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CounterpartyEntitlement(
                counterparty_id="cp-1",
                slot_label="",
                active_from=datetime(2026, 9, 1, tzinfo=UTC),
            )


class TestCounterpartyEntitlementProfile:
    def test_valid(self) -> None:
        profile = CounterpartyEntitlementProfile(
            counterparty_id="cp-1",
            allowed_slots=frozenset({"slot-a", "slot-b"}),
            payload_depth=PayloadDepth.STANDARD,
            rate_limit_ref="rl-default",
            entitlements=(
                CounterpartyEntitlement(
                    counterparty_id="cp-1",
                    slot_label="slot-a",
                    active_from=datetime(2026, 9, 1, tzinfo=UTC),
                ),
            ),
        )
        assert profile.payload_depth is PayloadDepth.STANDARD
        assert len(profile.entitlements) == 1

    def test_roundtrip(self) -> None:
        profile = CounterpartyEntitlementProfile(
            counterparty_id="cp-1",
            allowed_slots=frozenset({"slot-a"}),
            payload_depth=PayloadDepth.MINIMAL,
            rate_limit_ref="rl",
        )
        rebuilt = CounterpartyEntitlementProfile.model_validate(profile.model_dump(mode="json"))
        assert rebuilt == profile
