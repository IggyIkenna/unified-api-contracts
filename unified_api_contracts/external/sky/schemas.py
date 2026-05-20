"""Sky Protocol (formerly MakerDAO) savings rate API response schemas.

Endpoint: https://api.sky.money (Sky Savings Rate / sUSDS yield data).
Reference: https://sky.money/
Note: adapter not yet implemented in MTDS. Sky Protocol is the MakerDAO ecosystem
rebrand; provides DAI Savings Rate (DSR) and Sky Savings Rate (SSR) yield products.
"""

__api_version__ = "v1"

from pydantic import BaseModel


class SkySavingsRate(BaseModel):
    """A single savings rate record from the Sky Protocol API."""

    product: str | None = None
    rate_bps: int | None = None
    apy: float | None = None
    total_deposits_usd: float | None = None
    token_symbol: str | None = None


class SkySavingsRateResponse(BaseModel):
    """GET https://api.sky.money/... — Sky Savings Rate product list."""

    rates: list[SkySavingsRate] | None = None
    dsr_apy: float | None = None
    ssr_apy: float | None = None
