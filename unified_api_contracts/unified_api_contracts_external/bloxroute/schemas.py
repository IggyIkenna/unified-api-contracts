"""bloXroute BDN schemas: Gateway-API, Cloud-API, Protect RPC for Ethereum/BSC.

Sources (docs.bloxroute.com — public docs; some API details proprietary):
- blxr_tx: JSON-RPC transaction submission (transaction, blockchain_network, backrunme_reward_address)
- subscribe: bdnBlocks, newTxs, pendingTxs streams
- Protect RPC: eth-protect.rpc.blxrbdn.com (drop-in eth_sendRawTransaction)
- Cloud-API: api.blxrbdn.com (HTTPS), wss://api.blxrbdn.com/ws (WebSocket)

Gaps: Full streaming payload schemas (bdnBlocks, newTxs) require live samples; API docs
return 404 for some paths. Minimal stubs added for known endpoints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# --- blxr_tx (transaction submission) ---
class BloxrouteTxSubmitParams(BaseModel):
    """bloXroute blxr_tx JSON-RPC request params.

    Ref: docs.bloxroute.com (BSC/ETH APIs, sending-transactions).
    """

    transaction: str = Field(..., description="Raw transaction bytes without 0x prefix")
    blockchain_network: str = Field(
        ...,
        description="Target network (e.g. Mainnet, BSC-Mainnet, Base-Mainnet)",
    )
    backrunme_reward_address: str | None = Field(
        None,
        description="Wallet address for BackRunMe rewards; auto-enrolls in backrunning",
    )


class BloxrouteTxSubmitResult(BaseModel):
    """bloXroute blxr_tx JSON-RPC success result."""

    tx_hash: str = Field(..., description="Transaction hash of submitted tx")


class BloxrouteJsonRpcResponse(BaseModel):
    """Generic bloXroute JSON-RPC 2.0 response wrapper."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int = Field(..., description="Request id")
    result: BloxrouteTxSubmitResult | None = None
    error: BloxrouteError | None = None


# --- Error (JSON-RPC standard) ---
class BloxrouteError(BaseModel):
    """bloXroute JSON-RPC error object.

    Standard JSON-RPC 2.0 error: code (int), message (str). Optional data.
    """

    code: int = Field(..., description="JSON-RPC error code (e.g. -32600 invalid request)")
    message: str = Field(..., description="Human-readable error message")
    data: str | dict[str, object] | None = Field(None, description="Optional error details")


# --- subscribe (bdnBlocks, newTxs, pendingTxs) ---
class BloxrouteBdnBlocksParams(BaseModel):
    """bloXroute subscribe bdnBlocks stream params.

    Ref: docs.bloxroute.com/streams/bdnblocks.
    As of 2025-10, parsedTxs defaults to false (20-60 ms faster).
    """

    include: list[str] | None = Field(
        None,
        description="Fields to include: hash, header, transactions, uncles, future_validator_info, withdrawals",
    )
    parsedTxs: bool = Field(
        False,
        description="If true, return parsed tx JSON; if false, raw RLP (faster)",
    )


class BloxrouteSubscribeParams(BaseModel):
    """bloXroute subscribe params for newTxs, pendingTxs streams.

    Stub: full params documented at docs.bloxroute.com/streams/working-with-streams.
    """

    include: list[str] | None = Field(None, description="Fields to include in stream")


# --- Protect RPC endpoints ---
class BloxrouteProtectEndpoints(BaseModel):
    """bloXroute Protect RPC endpoints (frontrunning protection).

    Drop-in RPC replacement; uses eth_sendRawTransaction semantics.
    Ref: docs.bloxroute.com/protect-rpcs, eth-protect-rpc.
    """

    eth_protect: str = Field(
        "https://eth-protect.rpc.blxrbdn.com",
        description="ETH Protect RPC (frontrunning protection)",
    )
    eth_gas_protect: str = Field(
        "https://eth.rpc.blxrbdn.com",
        description="ETH Gas Protect RPC",
    )


class BloxrouteMempoolNotification(BaseModel):
    """bloXroute newTxs / pendingTxs stream notification."""

    tx_hash: str | None = None
    network: str | None = None
    blockchain_network: str | None = None
    tx_contents: dict[str, object] | None = None
