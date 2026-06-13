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


class TransferPurpose(StrEnum):
    """Why a :class:`TransferIntent` is being made — the SEMANTIC reason, distinct
    from :class:`BusTransferType` (the mechanical route).

    Margin-traceability gap (``capability_wizard_gap_discovery_2026_06_11.md``
    2026-06-12 § Margin traceability): today a USDC transfer to a perp venue is
    indistinguishable from any other transfer, so margin posting cannot be traced
    end-to-end on the CeFi side. Stamping the purpose lets the ledger /
    margin-health pipeline classify a transfer as collateral movement.

    Closed set; ``GENERAL`` is the non-margin default (back-compatible — existing
    emitters that omit the field get ``GENERAL``).
    """

    GENERAL = "general"
    """Unspecified / non-margin transfer (default)."""

    MARGIN_DEPOSIT = "margin_deposit"
    """Posting collateral to a venue to support a position (e.g. USDC → Hyperliquid)."""

    MARGIN_WITHDRAWAL = "margin_withdrawal"
    """Releasing collateral back from a venue after a position closes / de-risks."""

    COLLATERAL_POSTING = "collateral_posting"
    """Posting an asset as collateral to a lending/borrow protocol (DeFi supply)."""

    COLLATERAL_RELEASE = "collateral_release"
    """Withdrawing posted collateral from a lending/borrow protocol."""

    REBALANCE = "rebalance"
    """Intra-client reallocation of capital across strategies / wallets."""

    TREASURY_SWEEP = "treasury_sweep"
    """Sweeping profit / idle capital to the treasury wallet (per share-class split)."""

    FUNDING = "funding"
    """Funding a freshly-provisioned venue account ahead of trading."""


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

    transfer_purpose: TransferPurpose = TransferPurpose.GENERAL
    """SEMANTIC reason for the transfer (distinct from the mechanical
    :attr:`transfer_type`). Stamped so the ledger / margin-health pipeline can
    classify margin/collateral movements end-to-end (margin-traceability gap).
    Defaults to ``GENERAL`` — existing emitters that omit it are unaffected."""

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
    "TransferPurpose",
    "TransferResult",
    "TransferResultStatus",
]
