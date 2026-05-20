"""Unit tests for per-client lifecycle event contracts (Phase 1 UAC).

Validates:
1. Closed-set enums match plan spec.
2. Pydantic models round-trip via model_validate.
3. frozen=True / extra=forbid guard against schema drift.
4. HARD RULE: TransferIntent carries client_id on every instance.
5. Cross-client fund-movement prohibition captured in schema shape.

Ref: plans/active/per_client_isolation_and_venue_fanout_topology_2026_05_20.md Phase 1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts import (
    BusTransferType,
    ClientLifecycleEvent,
    ClientLifecycleKind,
    ClientQuarantinedEvent,
    ClientReadyEvent,
    QuarantineReason,
    ShardCapacityEvent,
    ShardRecommendedAction,
    TransferIntent,
    TransferResult,
    TransferResultStatus,
    VenueAuthStatus,
)

_NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# ClientLifecycleKind — closed-set sanity
# ---------------------------------------------------------------------------


def test_client_lifecycle_kind_closed_set() -> None:
    expected = {"REGISTER", "DEREGISTER", "QUARANTINE", "UNQUARANTINE", "CREDENTIAL_ROTATED"}
    assert {k.value for k in ClientLifecycleKind} == expected


def test_client_lifecycle_kind_no_duplicates() -> None:
    values = [k.value for k in ClientLifecycleKind]
    assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# ClientLifecycleEvent — round-trip + freeze
# ---------------------------------------------------------------------------


def _minimal_lifecycle(**overrides: object) -> ClientLifecycleEvent:
    base: dict[str, object] = {
        "kind": ClientLifecycleKind.REGISTER,
        "client_id": "odum-uk",
        "archetype_id": "carry_staked_basis",
        "shard_id": 0,
        "timestamp": _NOW,
    }
    base.update(overrides)
    return ClientLifecycleEvent.model_validate(base)


def test_client_lifecycle_event_register_happy_path() -> None:
    evt = _minimal_lifecycle()
    assert evt.kind == ClientLifecycleKind.REGISTER
    assert evt.client_id == "odum-uk"
    assert evt.archetype_id == "carry_staked_basis"
    assert evt.shard_id == 0
    assert evt.reason == ""
    assert evt.venue == ""


def test_client_lifecycle_event_credential_rotated_carries_venue() -> None:
    evt = _minimal_lifecycle(kind=ClientLifecycleKind.CREDENTIAL_ROTATED, venue="BINANCE-FUTURES")
    assert evt.venue == "BINANCE-FUTURES"


def test_client_lifecycle_event_frozen() -> None:
    evt = _minimal_lifecycle()
    with pytest.raises((AttributeError, ValidationError)):
        evt.client_id = "changed"  # type: ignore[misc]


def test_client_lifecycle_event_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ClientLifecycleEvent.model_validate(
            {
                "kind": "REGISTER",
                "client_id": "x",
                "archetype_id": "y",
                "shard_id": 0,
                "timestamp": _NOW,
                "unexpected_field": "bad",
            }
        )


def test_client_lifecycle_event_all_kinds_accepted() -> None:
    for kind in ClientLifecycleKind:
        evt = _minimal_lifecycle(kind=kind)
        assert evt.kind == kind


# ---------------------------------------------------------------------------
# VenueAuthStatus — closed-set
# ---------------------------------------------------------------------------


def test_venue_auth_status_closed_set() -> None:
    expected = {"OK", "FAILED", "SKIPPED"}
    assert {s.value for s in VenueAuthStatus} == expected


# ---------------------------------------------------------------------------
# ClientReadyEvent
# ---------------------------------------------------------------------------


def test_client_ready_event_happy_path() -> None:
    evt = ClientReadyEvent.model_validate(
        {
            "client_id": "odum-uk",
            "archetype_id": "carry_staked_basis",
            "shard_id": 0,
            "timestamp": _NOW,
            "venue_auth_status": {
                "BINANCE-FUTURES": "OK",
                "AAVE_V3": "OK",
                "HYPERLIQUID": "SKIPPED",
            },
        }
    )
    assert evt.venue_auth_status["BINANCE-FUTURES"] == VenueAuthStatus.OK
    assert evt.venue_auth_status["HYPERLIQUID"] == VenueAuthStatus.SKIPPED


def test_client_ready_event_empty_venue_status_allowed() -> None:
    evt = ClientReadyEvent.model_validate(
        {
            "client_id": "defi-client-1",
            "archetype_id": "arbitrage_price_dispersion",
            "shard_id": 1,
            "timestamp": _NOW,
        }
    )
    assert evt.venue_auth_status == {}


def test_client_ready_event_frozen() -> None:
    evt = ClientReadyEvent.model_validate({"client_id": "c", "archetype_id": "a", "shard_id": 0, "timestamp": _NOW})
    with pytest.raises((AttributeError, ValidationError)):
        evt.client_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# QuarantineReason — closed-set
# ---------------------------------------------------------------------------


def test_quarantine_reason_closed_set() -> None:
    expected = {
        "MAX_RESTART_ATTEMPTS",
        "PREFLIGHT_FAILED",
        "INSUFFICIENT_BALANCE",
        "VENUE_AUTH_TIMEOUT",
        "OPERATOR_QUARANTINE",
    }
    assert {r.value for r in QuarantineReason} == expected


# ---------------------------------------------------------------------------
# ClientQuarantinedEvent
# ---------------------------------------------------------------------------


def test_client_quarantined_event_happy_path() -> None:
    evt = ClientQuarantinedEvent.model_validate(
        {
            "client_id": "odum-uk",
            "archetype_id": "carry_staked_basis",
            "shard_id": 0,
            "timestamp": _NOW,
            "quarantine_reason": "MAX_RESTART_ATTEMPTS",
            "last_error_message": "Worker exited with code 1",
            "retry_after_seconds": 0,
            "restart_attempts": 5,
        }
    )
    assert evt.quarantine_reason == QuarantineReason.MAX_RESTART_ATTEMPTS
    assert evt.restart_attempts == 5


def test_client_quarantined_event_insufficient_balance() -> None:
    evt = ClientQuarantinedEvent.model_validate(
        {
            "client_id": "defi-client-1",
            "archetype_id": "arbitrage_price_dispersion",
            "shard_id": 0,
            "timestamp": _NOW,
            "quarantine_reason": "INSUFFICIENT_BALANCE",
        }
    )
    assert evt.quarantine_reason == QuarantineReason.INSUFFICIENT_BALANCE


def test_client_quarantined_event_frozen() -> None:
    evt = ClientQuarantinedEvent.model_validate(
        {
            "client_id": "c",
            "archetype_id": "a",
            "shard_id": 0,
            "timestamp": _NOW,
            "quarantine_reason": "PREFLIGHT_FAILED",
        }
    )
    with pytest.raises((AttributeError, ValidationError)):
        evt.client_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ShardRecommendedAction + ShardCapacityEvent
# ---------------------------------------------------------------------------


def test_shard_recommended_action_closed_set() -> None:
    assert {"SPAWN_NEW_SHARD"} == {a.value for a in ShardRecommendedAction}


def test_shard_capacity_event_happy_path() -> None:
    evt = ShardCapacityEvent.model_validate(
        {
            "archetype_id": "carry_staked_basis",
            "shard_id": 0,
            "timestamp": _NOW,
            "occupancy_pct": 90.0,
            "memory_pct": 72.5,
            "cpu_pct": 81.0,
            "client_count": 9,
            "shard_capacity_max": 10,
        }
    )
    assert evt.recommended_action == ShardRecommendedAction.SPAWN_NEW_SHARD
    assert evt.memory_pct == 72.5


def test_shard_capacity_event_frozen() -> None:
    evt = ShardCapacityEvent.model_validate(
        {
            "archetype_id": "a",
            "shard_id": 0,
            "timestamp": _NOW,
            "occupancy_pct": 50.0,
            "memory_pct": 50.0,
            "cpu_pct": 50.0,
            "client_count": 5,
            "shard_capacity_max": 10,
        }
    )
    with pytest.raises((AttributeError, ValidationError)):
        evt.archetype_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BusTransferType — closed-set
# ---------------------------------------------------------------------------


def test_bus_transfer_type_closed_set() -> None:
    expected = {"CEX_WITHDRAW", "DEFI_DEPOSIT", "DEFI_WITHDRAW", "BRIDGE", "SUBACCOUNT_MOVE"}
    assert {t.value for t in BusTransferType} == expected


# ---------------------------------------------------------------------------
# TransferIntent
# ---------------------------------------------------------------------------


def _minimal_transfer_intent(**overrides: object) -> TransferIntent:
    base: dict[str, object] = {
        "client_id": "odum-uk",
        "transfer_type": BusTransferType.DEFI_DEPOSIT,
        "source_venue": "BINANCE-FUTURES",
        "dest_venue": "AAVE_V3",
        "asset": "USDC",
        "amount": Decimal("10000"),
        "idempotency_key": "intent-abc-123",
        "timestamp": _NOW,
    }
    base.update(overrides)
    return TransferIntent.model_validate(base)


def test_transfer_intent_happy_path() -> None:
    intent = _minimal_transfer_intent()
    assert intent.client_id == "odum-uk"
    assert intent.transfer_type == BusTransferType.DEFI_DEPOSIT
    assert intent.amount == Decimal("10000")
    assert intent.idempotency_key == "intent-abc-123"


def test_transfer_intent_has_client_id() -> None:
    intent = _minimal_transfer_intent()
    assert hasattr(intent, "client_id")
    assert intent.client_id != ""


def test_transfer_intent_defi_carries_protocol() -> None:
    intent = _minimal_transfer_intent(protocol="aave_v3")
    assert intent.protocol == "aave_v3"


def test_transfer_intent_bridge_carries_chain_ids() -> None:
    intent = _minimal_transfer_intent(
        transfer_type=BusTransferType.BRIDGE,
        chain_id=1,
        dest_chain_id=137,
    )
    assert intent.chain_id == 1
    assert intent.dest_chain_id == 137


def test_transfer_intent_frozen() -> None:
    intent = _minimal_transfer_intent()
    with pytest.raises((AttributeError, ValidationError)):
        intent.client_id = "changed"  # type: ignore[misc]


def test_transfer_intent_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        _minimal_transfer_intent(unknown_field="bad")


def test_transfer_intent_all_types_accepted() -> None:
    for t in BusTransferType:
        intent = _minimal_transfer_intent(transfer_type=t)
        assert intent.transfer_type == t


# ---------------------------------------------------------------------------
# TransferResultStatus — closed-set
# ---------------------------------------------------------------------------


def test_transfer_result_status_closed_set() -> None:
    expected = {"SUBMITTED", "CONFIRMED", "FAILED"}
    assert {s.value for s in TransferResultStatus} == expected


# ---------------------------------------------------------------------------
# TransferResult
# ---------------------------------------------------------------------------


def _minimal_transfer_result(**overrides: object) -> TransferResult:
    base: dict[str, object] = {
        "idempotency_key": "intent-abc-123",
        "client_id": "odum-uk",
        "status": TransferResultStatus.CONFIRMED,
        "timestamp": _NOW,
    }
    base.update(overrides)
    return TransferResult.model_validate(base)


def test_transfer_result_happy_path() -> None:
    result = _minimal_transfer_result(tx_hash="0xdeadbeef", gas_used=150000)
    assert result.status == TransferResultStatus.CONFIRMED
    assert result.tx_hash == "0xdeadbeef"
    assert result.gas_used == 150000


def test_transfer_result_matches_intent_by_idempotency_key() -> None:
    intent = _minimal_transfer_intent(idempotency_key="key-xyz")
    result = _minimal_transfer_result(idempotency_key="key-xyz")
    assert result.idempotency_key == intent.idempotency_key


def test_transfer_result_failed_carries_error_message() -> None:
    result = _minimal_transfer_result(
        status=TransferResultStatus.FAILED,
        error_message="Insufficient gas",
    )
    assert result.status == TransferResultStatus.FAILED
    assert result.error_message == "Insufficient gas"


def test_transfer_result_frozen() -> None:
    result = _minimal_transfer_result()
    with pytest.raises((AttributeError, ValidationError)):
        result.client_id = "changed"  # type: ignore[misc]


def test_transfer_result_has_client_id() -> None:
    result = _minimal_transfer_result()
    assert hasattr(result, "client_id")
    assert result.client_id == "odum-uk"


# ---------------------------------------------------------------------------
# Cross-client fund-movement prohibition — schema-level enforcement
# ---------------------------------------------------------------------------


def test_transfer_intent_client_id_field_is_required() -> None:
    """TransferIntent MUST carry client_id — cross-client rejects at coordinator."""
    with pytest.raises(ValidationError):
        TransferIntent.model_validate(
            {
                "transfer_type": "DEFI_DEPOSIT",
                "source_venue": "BINANCE-FUTURES",
                "dest_venue": "AAVE_V3",
                "asset": "USDC",
                "amount": "10000",
                "idempotency_key": "k",
                "timestamp": _NOW,
                # client_id intentionally missing
            }
        )


def test_transfer_result_client_id_field_is_required() -> None:
    """TransferResult MUST carry client_id so consumers can route + audit."""
    with pytest.raises(ValidationError):
        TransferResult.model_validate(
            {
                "idempotency_key": "k",
                "status": "CONFIRMED",
                "timestamp": _NOW,
                # client_id intentionally missing
            }
        )
