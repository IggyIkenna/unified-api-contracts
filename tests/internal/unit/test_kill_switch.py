"""Closed-set sanity tests for the UAC kill-switch event taxonomy.

Phase 1.F of ``disaster_recovery_circuit_breakers_2026_05_10.md``
(``unified-trading-pm/plans/active/``).

Verifies:

1. :class:`KillSwitchId` covers KILL_ALL_LIVE + the 2 cutover archetypes +
   the 6 perp venues + 2 cutover-relevant asset groups.
2. :class:`KillSwitchProvenance` is the closed 4-set per Q8 ratification.
3. :class:`KillSwitchArmRequest` / :class:`KillSwitchArmedEvent` /
   :class:`KillSwitchDisarmEvent` round-trip via model_validate.
4. :class:`KillSwitchDisarmEvent.recovery_mode` echoes the
   :class:`BreakerRecoveryMode` from the originating breaker.
5. Pydantic class docstrings cite the § 7 SSOT reconciliation seam.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts import (
    BreakerRecoveryMode,
    KillSwitchArmedEvent,
    KillSwitchArmRequest,
    KillSwitchDisarmEvent,
    KillSwitchId,
    KillSwitchProvenance,
)

# ---------------------------------------------------------------------------
# Closed-set sanity
# ---------------------------------------------------------------------------


def test_kill_switch_id_includes_kill_all_live() -> None:
    assert "KILL_ALL_LIVE" in {m.value for m in KillSwitchId}


def test_kill_switch_id_covers_cutover_archetypes() -> None:
    expected = {
        "KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS",
        "KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION",
    }
    enum_values = {m.value for m in KillSwitchId}
    assert expected.issubset(enum_values)


def test_kill_switch_id_covers_six_perp_venues() -> None:
    """The 6 perp hedge venues per master plan."""
    expected_venues = {
        "KILL_PER_VENUE_BYBIT",
        "KILL_PER_VENUE_DERIBIT",
        "KILL_PER_VENUE_BINANCE",
        "KILL_PER_VENUE_OKX",
        "KILL_PER_VENUE_HYPERLIQUID",
        "KILL_PER_VENUE_ASTER",
    }
    enum_values = {m.value for m in KillSwitchId}
    assert expected_venues.issubset(enum_values)


def test_kill_switch_id_covers_cutover_asset_groups() -> None:
    expected = {"KILL_PER_ASSET_GROUP_CEFI", "KILL_PER_ASSET_GROUP_DEFI"}
    enum_values = {m.value for m in KillSwitchId}
    assert expected.issubset(enum_values)


def test_kill_switch_id_no_duplicate_values() -> None:
    values = [m.value for m in KillSwitchId]
    assert len(values) == len(set(values))


def test_kill_switch_id_includes_kill_per_wallet_sentinel() -> None:
    """KILL_PER_WALLET is the runtime-targeted wallet-tier sentinel.

    Added 2026-05-12 per api_keys_wallets_accounts_readiness_2026_05_10.md
    Phase 5. Wallet ID is carried on KillSwitchArmRequest.target_wallet_id
    at runtime — no enum-per-wallet explosion.
    """
    assert KillSwitchId.KILL_PER_WALLET.value == "KILL_PER_WALLET"


def test_kill_switch_provenance_closed_four_set() -> None:
    assert {m.value for m in KillSwitchProvenance} == {
        "OPERATOR_MANUAL",
        "BREAKER_AUTO",
        "SCENARIO_SYNTHETIC",
        "SCHEDULED_DRILL",
    }


# ---------------------------------------------------------------------------
# Pydantic round-trip
# ---------------------------------------------------------------------------


def _ts() -> datetime:
    return datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC)


def test_kill_switch_arm_request_round_trip() -> None:
    req = KillSwitchArmRequest(
        switch_id=KillSwitchId.KILL_ALL_LIVE,
        provenance=KillSwitchProvenance.OPERATOR_MANUAL,
        requested_by="operator-ikenna",
        arm_timestamp=_ts(),
        metadata={"correlation_id": "abc-123"},
    )
    dump = req.model_dump()
    restored = KillSwitchArmRequest.model_validate(dump)
    assert restored == req


def test_kill_switch_arm_request_per_wallet_round_trip() -> None:
    """KILL_PER_WALLET request carries target_wallet_id at runtime."""
    req = KillSwitchArmRequest(
        switch_id=KillSwitchId.KILL_PER_WALLET,
        provenance=KillSwitchProvenance.OPERATOR_MANUAL,
        requested_by="operator-ikenna",
        arm_timestamp=_ts(),
        target_wallet_id="defi-eth-hot-aave-v1",
        metadata={"correlation_id": "wallet-freeze-001"},
    )
    dump = req.model_dump()
    restored = KillSwitchArmRequest.model_validate(dump)
    assert restored == req
    assert restored.target_wallet_id == "defi-eth-hot-aave-v1"


def test_kill_switch_arm_request_default_target_wallet_id_empty() -> None:
    """Non-wallet kill-switches default target_wallet_id to empty string."""
    req = KillSwitchArmRequest(
        switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
        provenance=KillSwitchProvenance.OPERATOR_MANUAL,
        requested_by="operator-ikenna",
        arm_timestamp=_ts(),
    )
    assert req.target_wallet_id == ""


def test_kill_switch_armed_event_round_trip() -> None:
    evt = KillSwitchArmedEvent(
        switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
        provenance=KillSwitchProvenance.BREAKER_AUTO,
        armed_at=_ts(),
        requested_by="breaker-LIQUIDATION_CASCADE_RISK#3",
        metadata={"breaker_serial": "3", "threshold_observed": "1.08"},
    )
    dump = evt.model_dump()
    restored = KillSwitchArmedEvent.model_validate(dump)
    assert restored == evt


def test_kill_switch_disarm_event_auto_cooldown_round_trip() -> None:
    evt = KillSwitchDisarmEvent(
        switch_id=KillSwitchId.KILL_PER_VENUE_BYBIT,
        disarmed_at=_ts(),
        disarmed_by="AUTO_COOLDOWN",
        recovery_mode=BreakerRecoveryMode.AUTO_COOLDOWN,
        cooldown_seconds_elapsed=300,
        metadata={"breaker_id": "VENUE_OUTAGE_SECONDS"},
    )
    dump = evt.model_dump()
    restored = KillSwitchDisarmEvent.model_validate(dump)
    assert restored == evt


def test_kill_switch_disarm_event_manual_unkill_round_trip() -> None:
    evt = KillSwitchDisarmEvent(
        switch_id=KillSwitchId.KILL_ALL_LIVE,
        disarmed_at=_ts(),
        disarmed_by="operator-ikenna",
        recovery_mode=BreakerRecoveryMode.MANUAL_UNKILL,
        cooldown_seconds_elapsed=None,
    )
    dump = evt.model_dump()
    restored = KillSwitchDisarmEvent.model_validate(dump)
    assert restored == evt


def test_kill_switch_arm_request_frozen() -> None:
    req = KillSwitchArmRequest(
        switch_id=KillSwitchId.KILL_ALL_LIVE,
        provenance=KillSwitchProvenance.OPERATOR_MANUAL,
        requested_by="operator",
        arm_timestamp=_ts(),
    )
    with pytest.raises(ValidationError):
        req.requested_by = "other"  # type: ignore[misc]


def test_kill_switch_armed_event_frozen() -> None:
    evt = KillSwitchArmedEvent(
        switch_id=KillSwitchId.KILL_ALL_LIVE,
        provenance=KillSwitchProvenance.OPERATOR_MANUAL,
        armed_at=_ts(),
        requested_by="operator",
    )
    with pytest.raises(ValidationError):
        evt.armed_at = _ts()  # type: ignore[misc]


def test_kill_switch_disarm_event_frozen() -> None:
    evt = KillSwitchDisarmEvent(
        switch_id=KillSwitchId.KILL_ALL_LIVE,
        disarmed_at=_ts(),
        disarmed_by="operator",
        recovery_mode=BreakerRecoveryMode.MANUAL_UNKILL,
    )
    with pytest.raises(ValidationError):
        evt.disarmed_by = "other"  # type: ignore[misc]


def test_kill_switch_arm_request_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        KillSwitchArmRequest.model_validate(
            {
                "switch_id": KillSwitchId.KILL_ALL_LIVE.value,
                "provenance": KillSwitchProvenance.OPERATOR_MANUAL.value,
                "requested_by": "x",
                "arm_timestamp": _ts(),
                "unknown_field": "y",
            }
        )


def test_kill_switch_armed_event_default_metadata_empty() -> None:
    evt = KillSwitchArmedEvent(
        switch_id=KillSwitchId.KILL_ALL_LIVE,
        provenance=KillSwitchProvenance.OPERATOR_MANUAL,
        armed_at=_ts(),
        requested_by="operator",
    )
    assert evt.metadata == {}


# ---------------------------------------------------------------------------
# § 7 SSOT reconciliation seam citation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "klass",
    [
        KillSwitchArmRequest,
        KillSwitchArmedEvent,
        KillSwitchDisarmEvent,
    ],
)
def test_pydantic_class_docstring_cites_section_7_seam(klass: type) -> None:
    """Every Pydantic class in kill_switch.py MUST cite the
    § 7 SSOT reconciliation seam per the risk-plan mandate."""
    doc = inspect.getdoc(klass) or ""
    assert "§ 7 SSOT reconciliation" in doc, f"{klass.__name__} docstring missing '§ 7 SSOT reconciliation' subsection"


@pytest.mark.parametrize("klass", [KillSwitchId, KillSwitchProvenance])
def test_enum_class_docstring_cites_section_7_seam(klass: type) -> None:
    doc = inspect.getdoc(klass) or ""
    assert "§ 7 SSOT reconciliation" in doc, f"{klass.__name__} docstring missing '§ 7 SSOT reconciliation' subsection"


# ---------------------------------------------------------------------------
# Facade re-export
# ---------------------------------------------------------------------------


def test_facade_exports_kill_switch_taxonomy() -> None:
    import unified_api_contracts as uac

    assert uac.KillSwitchId is KillSwitchId
    assert uac.KillSwitchProvenance is KillSwitchProvenance
    assert uac.KillSwitchArmRequest is KillSwitchArmRequest
    assert uac.KillSwitchArmedEvent is KillSwitchArmedEvent
    assert uac.KillSwitchDisarmEvent is KillSwitchDisarmEvent
