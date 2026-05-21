"""Socket.tech bridge API schemas (api.socket.tech/v2/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SocketTokenInfo(BaseModel):
    """Token details within a Socket route."""

    address: str = Field(..., description="Token contract address")
    chainId: int = Field(..., description="Chain ID where token resides")
    decimals: int = Field(..., description="Token decimal precision")
    symbol: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token name")
    icon: str | None = Field(None, description="Token icon URL")


class SocketRoute(BaseModel):
    """A single bridge route returned by Socket quote."""

    routeId: str = Field(..., description="Unique route identifier")
    fromAmount: str = Field(..., description="Input amount as decimal string")
    toAmount: str = Field(..., description="Output amount as decimal string")
    minimumToAmount: str | None = Field(None, description="Minimum guaranteed output")
    estimatedGas: str | None = Field(None, description="Estimated gas cost in wei")
    serviceTime: int | None = Field(None, description="Estimated bridge time in seconds")
    fromAsset: SocketTokenInfo | None = None
    toAsset: SocketTokenInfo | None = None


class SocketQuoteResponse(BaseModel):
    """Response from GET /v2/quote.

    Requires API-KEY header (Socket API key).
    """

    success: bool = Field(..., description="True if routes were found")
    result: dict[str, object] = Field(default_factory=dict, description="Route results including routes list")
