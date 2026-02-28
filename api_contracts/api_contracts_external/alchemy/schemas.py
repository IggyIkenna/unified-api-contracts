"""Pydantic schemas for Alchemy RPC/API response shapes. Full surface per plan."""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class AlchemyRpcResponse(BaseModel):
    """Generic JSON-RPC response wrapper."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: dict | list | str | int | float | bool | None = None
    error: dict | None = None


class AlchemyAssetTransfer(BaseModel):
    """Asset transfer (e.g. from alchemy_getAssetTransfers)."""

    blockNum: str | None = None
    hash: str | None = None
    from_: str | None = Field(None, alias="from")
    to: str | None = None
    value: float | None = None
    asset: str | None = None
    category: str | None = None
    metadata: dict | None = None

    model_config = {"populate_by_name": True}


class AlchemyTokenBalance(BaseModel):
    """Token balance from Alchemy."""

    contractAddress: str | None = None
    tokenBalance: str | None = None
    symbol: str | None = None
    decimals: int | None = None
    name: str | None = None


class AlchemyError(BaseModel):
    """Alchemy API/RPC error."""

    code: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, http_status: int | None = None) -> ErrorAction:
        """Map Alchemy JSON-RPC/HTTP error to retry action."""
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == -32603:  # Internal error
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == -32600:  # Invalid request
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD


# --- Block / Transaction ---
class AlchemyBlock(BaseModel):
    """Block from eth_getBlockByNumber/eth_getBlockByHash."""

    number: str | None = None
    hash: str | None = None
    parentHash: str | None = None
    nonce: str | None = None
    sha3Uncles: str | None = None
    logsBloom: str | None = None
    transactionsRoot: str | None = None
    stateRoot: str | None = None
    receiptsRoot: str | None = None
    miner: str | None = None
    difficulty: str | None = None
    totalDifficulty: str | None = None
    extraData: str | None = None
    size: str | None = None
    gasLimit: str | None = None
    gasUsed: str | None = None
    timestamp: str | None = None
    transactions: list[str] | list[dict] | None = None
    uncles: list[str] | None = None
    baseFeePerGas: str | None = None


class AlchemyTransaction(BaseModel):
    """Transaction from eth_getTransactionByHash / block.transactions."""

    hash: str | None = None
    nonce: str | None = None
    blockHash: str | None = None
    blockNumber: str | None = None
    transactionIndex: str | None = None
    from_: str | None = Field(None, alias="from")
    to: str | None = None
    value: str | None = None
    gas: str | None = None
    gasPrice: str | None = None
    input: str | None = None
    maxFeePerGas: str | None = None
    maxPriorityFeePerGas: str | None = None
    type: str | None = None
    accessList: list | None = None
    chainId: str | None = None

    model_config = {"populate_by_name": True}


class AlchemyTransactionReceipt(BaseModel):
    """Transaction receipt from eth_getTransactionReceipt."""

    transactionHash: str | None = None
    transactionIndex: str | None = None
    blockHash: str | None = None
    blockNumber: str | None = None
    from_: str | None = Field(None, alias="from")
    to: str | None = None
    cumulativeGasUsed: str | None = None
    gasUsed: str | None = None
    contractAddress: str | None = None
    logs: list[dict] | None = None
    logsBloom: str | None = None
    type: str | None = None
    status: str | None = None
    effectiveGasPrice: str | None = None

    model_config = {"populate_by_name": True}


class AlchemyLog(BaseModel):
    """Raw log from transaction receipt / eth_getLogs."""

    address: str | None = None
    topics: list[str] | None = None
    data: str | None = None
    blockNumber: str | None = None
    transactionHash: str | None = None
    transactionIndex: str | None = None
    blockHash: str | None = None
    logIndex: str | None = None
    removed: bool | None = None


# --- Decoded logs (Transfer, Approval, Swap, Mint, Burn) ---
class AlchemyDecodedLog(BaseModel):
    """Decoded log (Alchemy decoded logs API)."""

    name: str | None = None  # Transfer, Approval, Swap, Mint, Burn, etc.
    signature: str | None = None
    decoded: dict | None = None  # event-specific params
    address: str | None = None
    topics: list[str] | None = None
    data: str | None = None


# --- Gas oracle ---
class AlchemyGasOracle(BaseModel):
    """Gas oracle from alchemy_getGasPrice / alchemy_gasPrice."""

    maxPriorityFeePerGas: str | None = None
    maxFeePerGas: str | None = None
    gasPrice: str | None = None
    suggestedMaxPriorityFeePerGas: str | None = None
    suggestedMaxFeePerGas: str | None = None


# --- ENS ---
class AlchemyEnsResolution(BaseModel):
    """ENS resolution result."""

    address: str | None = None
    name: str | None = None
    avatar: str | None = None
    records: dict | None = None


# --- NFT ---
class AlchemyNFTMetadata(BaseModel):
    """NFT metadata from Alchemy NFT API."""

    name: str | None = None
    description: str | None = None
    image: str | None = None
    external_url: str | None = None
    attributes: list[dict] | None = None
    animation_url: str | None = None
    background_color: str | None = None


class AlchemyNFTOwnership(BaseModel):
    """NFT ownership / balance."""

    contractAddress: str | None = None
    tokenId: str | None = None
    balance: str | None = None
    owner: str | None = None
    tokenType: str | None = None
    metadata: dict | None = None


class AlchemyTokenMetadata(BaseModel):
    """ERC20/ERC721/ERC1155 token metadata."""

    name: str | None = None
    symbol: str | None = None
    decimals: int | None = None
    totalSupply: str | None = None
    contractAddress: str | None = None


# --- Webhooks (Notify API) ---
class AlchemyWebhookSubscription(BaseModel):
    """Alchemy webhook subscription (create/list response).

    Ref: Alchemy Notify API - alchemy_createWebhook, dashboard create-webhook.
    Webhook types: ADDRESS_ACTIVITY, MINED_TRANSACTIONS, DROPPED_AND_REPLACED, etc.
    """

    id: str | None = Field(None, description="Webhook ID")
    webhook_id: str | None = Field(None, alias="webhookId", description="Webhook ID (alternate)")
    webhook_url: str | None = Field(None, alias="webhookUrl")
    network: str | None = None
    chain_id: int | None = Field(None, alias="chainId")
    webhook_type: str | None = Field(None, alias="webhookType")
    addresses: list[str] | None = None
    event_types: list[str] | None = Field(None, alias="eventTypes")
    skip_empty_messages: bool | None = Field(None, alias="skipEmptyMessages")
    created_at: str | None = Field(None, alias="createdAt")

    model_config = {"populate_by_name": True}


class AlchemyWebhookCreateParams(BaseModel):
    """Params for alchemy_createWebhook / create-webhook."""

    addresses: list[str] = Field(..., description="Addresses to monitor")
    webhook_url: str = Field(..., alias="webhookUrl")
    chain_id: int | None = Field(None, alias="chainId")
    network: str | None = None
    webhook_type: str | None = Field(None, alias="webhookType")
    event_types: list[str] | None = Field(None, alias="eventTypes")
    skip_empty_messages: bool | None = Field(None, alias="skipEmptyMessages")

    model_config = {"populate_by_name": True}


# --- Simulation ---
class AlchemySimulationResult(BaseModel):
    """Transaction simulation result (alchemy_simulateAssetChanges / debug_trace)."""

    changes: list[dict] | None = None
    error: dict | None = None
    gasUsed: str | None = None
    blockNumber: str | None = None


# --- WebSocket ---
class AlchemyWsNotification(BaseModel):
    """Alchemy WebSocket notification message."""

    method: str | None = None
    params: dict[str, object] | None = None
    id: str | None = None
    jsonrpc: str | None = None


class AlchemyWsMinedTransaction(BaseModel):
    """Mined transaction from alchemy_minedTransactions WebSocket."""

    hash: str | None = None
    blockNumber: str | None = None
    to: str | None = None
    from_address: str | None = Field(None, alias="from")
    input: str | None = None
    value: str | None = None
    gas: str | None = None
    gasPrice: str | None = None

    model_config = {"populate_by_name": True}


class AlchemyWsLog(BaseModel):
    """Log from eth_subscribe logs WebSocket."""

    address: str | None = None
    topics: list[str] | None = None
    data: str | None = None
    transactionHash: str | None = None
    blockNumber: str | None = None
    logIndex: str | None = None
    transactionIndex: str | None = None
