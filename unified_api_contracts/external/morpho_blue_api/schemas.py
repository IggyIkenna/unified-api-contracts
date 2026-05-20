"""Morpho Blue API response schemas.

Endpoint: https://blue-api.morpho.org/graphql (GraphQL, no auth required for market reads).
Reference: https://docs.morpho.org/
"""

__api_version__ = "v1"

from pydantic import BaseModel


class MorphoBlueAsset(BaseModel):
    """Token asset in a Morpho market."""

    address: str | None = None
    symbol: str | None = None
    decimals: int | None = None


class MorphoBlueMarketState(BaseModel):
    """Current market state from Morpho Blue API."""

    supplyAssets: object = None
    borrowAssets: object = None
    supplyApy: float | None = None
    borrowApy: float | None = None


class MorphoBlueMarket(BaseModel):
    """Single Morpho Blue market entry from GraphQL response."""

    uniqueKey: str | None = None
    loanAsset: MorphoBlueAsset | None = None
    collateralAsset: MorphoBlueAsset | None = None
    lltv: str | None = None
    state: MorphoBlueMarketState | None = None


class MorphoBlueMarketsResponse(BaseModel):
    """POST https://blue-api.morpho.org/graphql — GetMarkets query response."""

    data: dict[str, object] | None = None
    errors: list[dict[str, object]] | None = None
