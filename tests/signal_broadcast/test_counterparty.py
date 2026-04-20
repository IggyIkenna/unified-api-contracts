"""Unit tests for :class:`Counterparty` + :class:`CounterpartyStatus`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts.signal_broadcast import (
    Counterparty,
    CounterpartyStatus,
)


class TestCounterpartyStatus:
    def test_members(self) -> None:
        assert CounterpartyStatus.ACTIVE == "ACTIVE"
        assert CounterpartyStatus.SUSPENDED == "SUSPENDED"
        assert CounterpartyStatus.REVOKED == "REVOKED"

    def test_enum_completeness(self) -> None:
        assert {s.value for s in CounterpartyStatus} == {"ACTIVE", "SUSPENDED", "REVOKED"}


def _now() -> datetime:
    return datetime(2026, 4, 20, 0, 0, 0, tzinfo=UTC)


class TestCounterparty:
    def test_minimal_valid(self) -> None:
        cp = Counterparty(
            id="cp-1",
            name="Counterparty One",
            endpoint="https://example.invalid/hook",
            allowed_slots=frozenset({"slot-a"}),
            hmac_secret_ref="projects/-/secrets/cp1",
            rate_limit_ref="rl-default",
            created_at=_now(),
            updated_at=_now(),
        )
        assert cp.id == "cp-1"
        assert cp.status is CounterpartyStatus.ACTIVE
        assert "slot-a" in cp.allowed_slots

    def test_frozen(self) -> None:
        cp = Counterparty(
            id="cp-1",
            name="Counterparty One",
            endpoint="https://example.invalid/hook",
            hmac_secret_ref="ref",
            rate_limit_ref="rl",
            created_at=_now(),
            updated_at=_now(),
        )
        with pytest.raises(ValidationError):
            cp.name = "other"  # type: ignore[misc]

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            Counterparty(  # type: ignore[call-arg]
                id="cp-1",
                name="Counterparty One",
                endpoint="https://example.invalid/hook",
                # hmac_secret_ref missing
                rate_limit_ref="rl",
                created_at=_now(),
                updated_at=_now(),
            )

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Counterparty(
                id="",
                name="Counterparty",
                endpoint="https://example.invalid/hook",
                hmac_secret_ref="ref",
                rate_limit_ref="rl",
                created_at=_now(),
                updated_at=_now(),
            )

    def test_roundtrip_serialisation(self) -> None:
        cp = Counterparty(
            id="cp-1",
            name="Counterparty One",
            status=CounterpartyStatus.SUSPENDED,
            endpoint="https://example.invalid/hook",
            allowed_slots=frozenset({"slot-a", "slot-b"}),
            hmac_secret_ref="ref",
            rate_limit_ref="rl",
            created_at=_now(),
            updated_at=_now(),
        )
        payload = cp.model_dump(mode="json")
        rebuilt = Counterparty.model_validate(payload)
        assert rebuilt == cp
        assert rebuilt.status is CounterpartyStatus.SUSPENDED
