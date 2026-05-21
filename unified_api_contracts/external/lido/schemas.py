"""Pydantic schemas for Lido Finance REST API (api.lido.fi/v1/protocol/steth/apr/last)."""

from pydantic import BaseModel, Field


class LidoStethAprData(BaseModel):
    """Inner data object from GET /v1/protocol/steth/apr/last."""

    timeUnix: int = Field(description="Unix timestamp of the APR snapshot")
    apr: float = Field(description="stETH annualised percentage rate (e.g. 3.5 = 3.5%)")


class LidoStethApr(BaseModel):
    """Top-level response from GET /v1/protocol/steth/apr/last."""

    data: LidoStethAprData
