"""Pydantic schemas for OpenBB Platform data.

Source: OpenBB Python SDK — openbb-fixedincome
Requires OpenBB API key / provider credentials.

Used by unified-market-interface OpenBBAdapter for US Treasury bond bid/ask/YTM data.
"""

from pydantic import BaseModel


class OpenBBTreasuryPrice(BaseModel):
    """Single treasury price observation from OpenBB Platform."""
    
    symbol: str | None = None
    name: str | None = None
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    yield_to_maturity: float | None = None
    date: str | None = None


class OpenBBTreasuryPricesResponse(BaseModel):
    """OpenBB treasury prices response containing bond bid/ask/YTM data."""
    
    results: list[OpenBBTreasuryPrice] | None = None
    provider: str | None = None
    warnings: list[str] | None = None
    chart: dict[str, object] | None = None
    extra: dict[str, object] | None = None