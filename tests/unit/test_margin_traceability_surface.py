"""Tests for the margin-traceability UAC surface (2026-06-13).

Adds the schema surface that lets a margin/collateral transfer be distinguished
from any other transfer and traced through the ledger:
  - ``TransferPurpose`` enum + optional ``TransferIntent.transfer_purpose`` field
    (default ``GENERAL`` — back-compatible).
  - ledger ``EventType.COLLATERAL_POSTED`` / ``MARGIN_RELEASED``.

Gap: ``capability_wizard_gap_discovery_2026_06_11.md`` 2026-06-12 § Margin
traceability ([SPEC] P1). The downstream emission (CeFi margin_event_emitter,
margin_health API) is strategy-service-engine-coupled and remains under LOGIC
FREEZE — this is the additive contract surface only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts import TransferIntent, TransferPurpose
from unified_api_contracts.canonical.crosscutting.ledger import EventType
from unified_api_contracts.canonical.crosscutting.transfer_events import BusTransferType


def test_transfer_purpose_closed_set() -> None:
    values = {p.value for p in TransferPurpose}
    assert values == {
        "general",
        "margin_deposit",
        "margin_withdrawal",
        "collateral_posting",
        "collateral_release",
        "rebalance",
        "treasury_sweep",
        "funding",
    }


def test_transfer_intent_defaults_to_general_purpose() -> None:
    """Back-compat: an emitter that omits transfer_purpose gets GENERAL."""
    intent = TransferIntent(
        client_id="c1",
        transfer_type=BusTransferType.CEX_WITHDRAW,
        source_venue="BINANCE-FUTURES",
        dest_venue="HYPERLIQUID",
        asset="USDC",
        amount=Decimal("1000"),
        idempotency_key="k1",
        timestamp=datetime(2026, 6, 13, tzinfo=UTC),
    )
    assert intent.transfer_purpose == TransferPurpose.GENERAL


def test_transfer_intent_carries_margin_purpose() -> None:
    """A margin deposit is now distinguishable from any other transfer."""
    intent = TransferIntent(
        client_id="c1",
        transfer_type=BusTransferType.CEX_WITHDRAW,
        source_venue="TREASURY",
        dest_venue="HYPERLIQUID",
        asset="USDC",
        amount=Decimal("5000"),
        idempotency_key="k2",
        timestamp=datetime(2026, 6, 13, tzinfo=UTC),
        transfer_purpose=TransferPurpose.MARGIN_DEPOSIT,
    )
    assert intent.transfer_purpose == TransferPurpose.MARGIN_DEPOSIT


def test_ledger_event_types_for_margin_traceability_exist() -> None:
    assert EventType.COLLATERAL_POSTED.value == "collateral_posted"
    assert EventType.MARGIN_RELEASED.value == "margin_released"
