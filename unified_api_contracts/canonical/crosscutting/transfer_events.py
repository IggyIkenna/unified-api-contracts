"""Transfer intent + result event taxonomy for strategy-service → execution-service.

These bus events replace the fragmented transfer surfaces in execution-service
(CEX withdrawals, DeFi protocol deposits/withdrawals, bridges, sub-account moves)
with a single :class:`TransferIntent` → :class:`TransferResult` request/response
pair routed through ``execution_service.transfer_coordinator.TransferCoordinator``.

§ SSOT reconciliation
---------------------

Composes with:

- :class:`unified_api_contracts.internal.domain.execution_service.transfer_types.TransferType`
  — the execution-service internal ``TransferType`` enum has overlapping values
  (``CEX_WITHDRAWAL``, ``BRIDGE``). This module's :class:`BusTransferType`
  is the canonical bus-facing closed set; the internal enum drives routing.
- ``plans/active/per_client_isolation_and_venue_fanout_topology_2026_05_20.md``
  Phase 1 — canonical field specs for :class:`TransferIntent` / :class:`TransferResult`.

HARD RULE: ``TransferIntent.source_venue`` and ``dest_venue`` MUST belong to the
same ``client_id``. ``TransferCoordinator`` raises ``CrossClientTransferForbiddenError``
for any intent where source/dest client scopes differ. Funds NEVER move
between different clients (custody + legal boundary).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BusTransferType(StrEnum):
    """Closed-set transfer type discriminant for :class:`TransferIntent`.

    Routes the intent to the correct ``TransferCoordinator`` handler:

    - ``CEX_WITHDRAW``:    CeFi withdrawal to external address via CCXT.
    - ``DEFI_DEPOSIT``:    Deposit into a DeFi protocol (Aave, Morpho, etc.).
    - ``DEFI_WITHDRAW``:   Withdraw from a DeFi protocol.
    - ``BRIDGE``:          Cross-chain bridge (Across, Stargate, etc.).
    - ``SUBACCOUNT_MOVE``: Intra-exchange sub-account transfer (Binance + OKX
      only for May-23; other venues raise ``NotSupported`` in the coordinator).
    """

    CEX_WITHDRAW = "CEX_WITHDRAW"
    DEFI_DEPOSIT = "DEFI_DEPOSIT"
    DEFI_WITHDRAW = "DEFI_WITHDRAW"
    BRIDGE = "BRIDGE"
    SUBACCOUNT_MOVE = "SUBACCOUNT_MOVE"


class TransferResultStatus(StrEnum):
    """Execution outcome for :class:`TransferResult`."""

    SUBMITTED = "SUBMITTED"
    """Transfer accepted by the execution-service; awaiting confirmation."""

    CONFIRMED = "CONFIRMED"
    """On-chain tx confirmed (DeFi/bridge) or CEX withdrawal completed."""

    FAILED = "FAILED"
    """Transfer rejected or failed; see :attr:`TransferResult.error_message`."""


class TransferIntent(BaseModel):
    """Transfer request emitted by strategy-service, consumed by execution-service.

    ``TransferCoordinator`` routes by :attr:`transfer_type` to the appropriate
    existing implementation in execution-service. Idempotency is enforced by
    :attr:`idempotency_key`; duplicate submissions return the cached
    :class:`TransferResult` without re-executing.

    HARD RULE: :attr:`source_venue` and :attr:`dest_venue` must be accounts
    belonging to the same :attr:`client_id`. ``TransferCoordinator`` rejects
    cross-client intents with ``CrossClientTransferForbiddenError``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_id: str
    """Owning client. Both source and destination must belong to this client."""

    transfer_type: BusTransferType
    source_venue: str
    """Canonical source venue name (e.g. ``"BINANCE-FUTURES"``, ``"AAVE_V3"``)."""

    dest_venue: str
    """Canonical destination venue name."""

    asset: str
    """Asset symbol (e.g. ``"USDC"``, ``"ETH"``, ``"BTC"``)."""

    amount: Decimal
    """Transfer amount in base asset units (not wei; the executor converts)."""

    idempotency_key: str
    """Unique key per intent. Second submission with same key returns cached result."""

    timestamp: datetime
    """When the intent was emitted by strategy-service (UTC)."""

    protocol: str = ""
    """DeFi protocol identifier for DEFI_DEPOSIT / DEFI_WITHDRAW
    (e.g. ``"aave_v3"``, ``"morpho"``, ``"yearn"``). Empty for non-DeFi types."""

    chain_id: int = 0
    """Source chain ID for on-chain transfers / bridges (EIP-155; 0 = not applicable)."""

    dest_chain_id: int = 0
    """Destination chain ID for BRIDGE transfers (0 = same-chain)."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Free-form structured context (e.g. ``strategy_id``, ``signal_id``)."""


class TransferResult(BaseModel):
    """Outcome of a :class:`TransferIntent` emitted by execution-service.

    Matches the originating intent via :attr:`idempotency_key`. Published on
    the event bus for strategy-service to consume and update its per-client
    transfer ledger.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    idempotency_key: str
    """Matches :attr:`TransferIntent.idempotency_key` of the originating intent."""

    client_id: str
    status: TransferResultStatus
    timestamp: datetime
    """When the result was emitted by execution-service (UTC)."""

    tx_hash: str = ""
    """On-chain transaction hash (DeFi/bridge transfers). Empty for CeFi."""

    withdrawal_id: str = ""
    """CEX withdrawal ID (CeFi withdrawals). Empty for DeFi/bridge."""

    fee: Decimal = Decimal("0")
    """Total fee charged (exchange fee + gas, in base asset units)."""

    gas_used: int = 0
    """Gas consumed (on-chain transfers only; 0 for CeFi)."""

    error_message: str = ""
    """Non-empty when :attr:`status` is ``FAILED``."""

    metadata: dict[str, str] = Field(default_factory=dict)


__all__ = [
    "BusTransferType",
    "TransferIntent",
    "TransferResult",
    "TransferResultStatus",
]
