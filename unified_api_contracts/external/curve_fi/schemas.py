"""Curve Finance REST API response schemas.

Endpoint: https://api.curve.finance/v1/getPools/{chain}/main
Reference: https://docs.curve.finance/
"""

__api_version__ = "v1"

from pydantic import BaseModel


class CurvePool(BaseModel):
    """A single Curve liquidity pool from the REST API."""

    id: str | None = None
    address: str | None = None
    name: str | None = None
    symbol: str | None = None
    assetType: str | None = None
    implementationAddress: str | None = None
    coins: list[str] | None = None
    coinNames: list[str] | None = None
    coinDecimals: list[int] | None = None
    totalSupply: str | None = None
    virtualPrice: str | None = None
    amplificationCoefficient: str | None = None
    fee: str | None = None
    adminFee: str | None = None
    usdTotal: float | None = None
    usdTotalExcludingBasePool: float | None = None
    isMetaPool: bool | None = None
    basePoolAddress: str | None = None


class CurvePoolsData(BaseModel):
    """Data payload from the Curve pools endpoint."""

    poolData: list[CurvePool] | None = None
    tvl: float | None = None


class CurvePoolsResponse(BaseModel):
    """Top-level response from api.curve.finance/v1/getPools."""

    success: bool | None = None
    data: CurvePoolsData | None = None
