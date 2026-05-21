"""Pydantic schemas for Marinade Finance REST API (api.marinade.finance)."""

from pydantic import BaseModel, Field


class MarinadeApyExtras(BaseModel):
    """Breakdown of mSOL APY components."""

    stakingRewards: float = Field(description="Base SOL staking reward APY component")
    mevRewards: float = Field(description="MEV tip reward APY component")


class MarinadeApyResponse(BaseModel):
    """Response from GET /msol/apy/{days}d — mSOL annualised percentage yield.

    The 'value' field is the total APY as a decimal fraction (0.07 = 7%).
    """

    value: float = Field(description="Total mSOL APY as a decimal fraction (e.g. 0.0698 = 6.98%)")
    extras: MarinadeApyExtras | None = Field(default=None, description="APY breakdown by component")
