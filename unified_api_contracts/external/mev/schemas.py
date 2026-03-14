"""MEV protection schemas: Flashbots, MEV-Share v0.1, MEV Blocker.

Sources:
- Flashbots: https://flashbots.github.io/api-specs/latest/openrpc.json
- MEV-Share: https://github.com/flashbots/mev-share/blob/main/specs/bundles/v0.1.md
- MEV Blocker: https://docs.mevblocker.io/reference/api/transaction-endpoints
- eth_sendPrivateTransaction: https://docs.flashbots.net/flashbots-protect/additional-documentation/eth-sendPrivateTransaction
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from typing import Literal

from pydantic import BaseModel, Field


# --- Flashbots eth_sendBundle ---
class FlashbotsBundleParams(BaseModel):
    """Flashbots eth_sendBundle request params.

    Ref: https://flashbots.github.io/api-specs/latest/openrpc.json
    """

    txs: list[str] = Field(..., description="Signed transactions (hex) for atomic bundle")
    blockNumber: str = Field(..., description="Hex-encoded block number bundle is valid for")
    replacementUuid: str | None = Field(None, description="UUID to cancel/replace this bundle")
    minTimestamp: int | None = Field(None, description="Min timestamp (unix seconds) for validity")
    maxTimestamp: int | None = Field(None, description="Max timestamp (unix seconds) for validity")
    revertingTxHashes: list[str] | None = Field(None, description="Tx hashes allowed to revert")
    builders: list[str] | None = Field(None, description="Block builder names to share with")

    model_config = {"populate_by_name": True}


class FlashbotsBundleResult(BaseModel):
    """Flashbots eth_sendBundle response."""

    bundleHash: str = Field(..., description="Hash of submitted bundle")
    smart: bool | None = Field(None, description="Present when builders specified")


# --- Flashbots eth_callBundle (simulation) ---
class FlashbotsCallBundleParams(BaseModel):
    """Flashbots eth_callBundle request params (bundle simulation).

    Simulates bundle before submission. EVM timestamp/block/state overridable.
    """

    txs: list[str] = Field(..., description="Signed transactions to simulate")
    blockNumber: str = Field(..., description="Hex block number to simulate against")
    stateBlockNumber: str | None = Field(None, description="Block for SLOAD state")
    timestamp: int | None = Field(None, description="EVM block.timestamp override")


class FlashbotsCallBundleResult(BaseModel):
    """Flashbots eth_callBundle response (simulation results)."""

    bundleHash: str | None = None
    coinbaseDiff: str | None = Field(None, description="Total coinbase diff (wei hex)")
    results: list[dict[str, object]] | None = Field(None, description="Per-tx simulation results")
    totalGasUsed: int | None = None


# --- Flashbots eth_sendPrivateTransaction ---
class FlashbotsPrivateTransactionPreferences(BaseModel):
    """Preferences for eth_sendPrivateTransaction."""

    fast: bool | None = Field(None, description="Send to all builders; MEV-Share 50% revenue")
    privacy: dict[str, object] | None = Field(
        None,
        description="hints: calldata|logs|function_selector|contract_address|hash|tx_hash|full; builders",
    )
    validity: dict[str, object] | None = Field(
        None,
        description="refund: [{address, percent}] for backrun refund allocation",
    )


class FlashbotsPrivateTransactionParams(BaseModel):
    """Flashbots eth_sendPrivateTransaction request params.

    Ref: https://docs.flashbots.net/flashbots-protect/additional-documentation/eth-sendPrivateTransaction
    """

    tx: str = Field(..., description="Raw signed transaction (hex)")
    maxBlockNumber: str | None = Field(None, description="Highest block for inclusion (hex)")
    preferences: FlashbotsPrivateTransactionPreferences | None = None


# --- MEV-Share v0.1 mev_sendBundle ---
MevShareHint = Literal[
    "calldata",
    "contract_address",
    "logs",
    "function_selector",
    "hash",
    "tx_hash",
]


class MevShareRefundItem(BaseModel):
    """MEV-Share validity refund config."""

    bodyIdx: int = Field(..., description="Index in body for refund")
    percent: float = Field(..., ge=0, le=100)


class MevShareRefundConfigItem(BaseModel):
    """MEV-Share refundConfig address/percent."""

    address: str = Field(..., description="Refund recipient")
    percent: float = Field(..., ge=0, le=100)


class MevShareBundleBodyItem(BaseModel):
    """MEV-Share body item: hash, tx+canRevert, or nested bundle.

    Exactly one of hash, tx, or bundle must be set.
    """

    hash: str | None = Field(None, description="Tx or bundle hash (from event stream)")
    tx: str | None = Field(None, description="Signed tx (hex)")
    canRevert: bool | None = Field(None, description="Allow tx to revert or be discarded")
    bundle: dict[str, object] | None = Field(None, description="Nested MevSendBundleParams (recursive)")


class MevShareInclusion(BaseModel):
    """MEV-Share inclusion block range."""

    block: str = Field(..., description="First block for inclusion (hex)")
    maxBlock: str | None = Field(None, description="Max block for inclusion (hex)")


class MevShareBundleParams(BaseModel):
    """MEV-Share v0.1 mev_sendBundle request params.

    Ref: https://github.com/flashbots/mev-share/blob/main/specs/bundles/v0.1.md
    """

    version: Literal["v0.1"] = "v0.1"
    inclusion: MevShareInclusion = Field(
        ...,
        description="block (hex), maxBlock? (hex) - block range for inclusion",
    )
    body: list[MevShareBundleBodyItem] = Field(
        ...,
        description="Ordered txs/hashes/bundles; supports nesting",
    )
    validity: dict[str, object] | None = Field(
        None,
        description="refund, refundConfig - post-inclusion predicates",
    )
    privacy: dict[str, object] | None = Field(
        None,
        description="hints: calldata|contract_address|logs|function_selector|hash|tx_hash; builders",
    )


class MevShareBundleResult(BaseModel):
    """MEV-Share mev_sendBundle response."""

    bundleHash: str = Field(..., description="Hash of bundle body")


# --- Flashbots eth_cancelPrivateTransaction ---
class FlashbotsCancelPrivateTransactionParams(BaseModel):
    """Flashbots eth_cancelPrivateTransaction request params.

    Cancels a previously submitted private transaction. Must be signed by same key
    as the original eth_sendPrivateTransaction call.
    Ref: https://docs.flashbots.net/flashbots-protect/additional-documentation/eth-sendPrivateTransaction
    """

    txHash: str = Field(..., description="Transaction hash of the private tx to cancel")


# --- MEV Blocker ---
class MevBlockerEndpoints(BaseModel):
    """MEV Blocker RPC endpoints (CoW DAO).

    Drop-in RPC replacement; uses eth_sendPrivateTransaction semantics.
    Base: https://rpc.mevblocker.io
    """

    fast: str = "https://rpc.mevblocker.io/fast"
    noreverts: str = "https://rpc.mevblocker.io/noreverts"
    fullprivacy: str = "https://rpc.mevblocker.io/fullprivacy"
    maxbackruns: str = "https://rpc.mevblocker.io/maxbackruns"
    nochecks: str = "https://rpc.mevblocker.io/nochecks"
