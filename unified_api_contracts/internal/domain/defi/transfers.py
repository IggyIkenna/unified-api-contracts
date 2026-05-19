"""DeFi transfer tracking and verification schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class TransferType(StrEnum):
    """Type of fund transfer operation."""

    SAME_CHAIN = "SAME_CHAIN"
    CROSS_CHAIN = "CROSS_CHAIN"
    CEX_WITHDRAWAL = "CEX_WITHDRAWAL"
    CEX_DEPOSIT = "CEX_DEPOSIT"
    SWEEP = "SWEEP"
    REBALANCE = "REBALANCE"


class TransferStatus(StrEnum):
    """Status of a fund transfer."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    CONFIRMING = "CONFIRMING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    BRIDGING = "BRIDGING"
    BRIDGE_COMPLETE = "BRIDGE_COMPLETE"


class BridgeProtocol(StrEnum):
    """Supported cross-chain bridge protocols."""

    NATIVE = "NATIVE"
    STARGATE = "STARGATE"
    ACROSS = "ACROSS"
    HOP = "HOP"
    LAYERZERO = "LAYERZERO"
    SOCKET = "SOCKET"
    LIFI = "LIFI"
    CCTP = "CCTP"


class TransferRecord(BaseModel):
    """Complete record of a fund transfer for tracking and reconciliation."""

    transfer_id: str
    transfer_type: TransferType
    status: TransferStatus
    source_chain_id: int
    dest_chain_id: int
    source_address: str
    dest_address: str
    token: str
    amount_wei: str
    tx_hash: str | None = None
    bridge_tx_hash: str | None = None
    gas_used: int | None = None
    gas_price_gwei: Decimal | None = None
    gas_cost_eth: Decimal | None = None
    gas_cost_usd: Decimal | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    bridge_protocol: BridgeProtocol | None = None
    error_code: str | None = None
    error_message: str | None = None


class TransferConfirmation(BaseModel):
    """Result of verifying a transfer on-chain via Alchemy Transfers API."""

    transfer_id: str
    tx_hash: str
    block_number: int
    confirmed: bool
    actual_value: Decimal
    expected_value: Decimal
    discrepancy_wei: Decimal
    confirmations: int
    timestamp: datetime
    # Whether the transfer's block has cleared the chain's reorg-depth
    # threshold (CHAIN_CONFIGS[chain_id].reorg_depth). Distinct from
    # ``confirmed`` (= "we found the matching transfer"); ``is_finalized``
    # answers "is the inclusion safe to treat as canonical now". Defaults
    # to False so consumers that don't populate it from the helper can't
    # accidentally treat unfinalised transfers as canonical.
    is_finalized: bool = False


class AlchemyTransferRecord(BaseModel):
    """Single transfer record from Alchemy alchemy_getAssetTransfers response."""

    block_num: str
    unique_id: str
    tx_hash: str
    from_address: str
    to_address: str
    value: Decimal | None = None
    asset: str | None = None
    category: str
    raw_contract_value: str | None = None
    raw_contract_address: str | None = None
    raw_contract_decimal: str | None = None


class AlchemyTransfersResponse(BaseModel):
    """Response from Alchemy alchemy_getAssetTransfers endpoint."""

    transfers: list[AlchemyTransferRecord]
    page_key: str | None = None
