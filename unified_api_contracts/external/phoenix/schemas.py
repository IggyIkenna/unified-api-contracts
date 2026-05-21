"""Pydantic schemas for Phoenix DEX API (api.phoenix.trade/markets).

NOTE: Phoenix REST API deprecated 2026-05-15. Schema preserved for canary
drift detection. Quote data now flows via Jupiter (lite-api.jup.ag).
"""

from pydantic import BaseModel, Field


class PhoenixMarket(BaseModel):
    """A single Phoenix on-chain order book market."""

    market_address: str = Field(description="Phoenix market account address on Solana")
    base_mint: str = Field(description="Base token mint address")
    quote_mint: str = Field(description="Quote token mint address")
    base_symbol: str
    quote_symbol: str
    tick_size: float = Field(description="Minimum price increment")
    base_lot_size: float = Field(description="Minimum order size in base token units")


class PhoenixMarketsResponse(BaseModel):
    """Response from GET /markets."""

    markets: list[PhoenixMarket]
