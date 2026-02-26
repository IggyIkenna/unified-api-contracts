"""Pydantic schemas for Alchemy RPC/API response shapes. Full surface per plan."""

from pydantic import BaseModel, Field


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
