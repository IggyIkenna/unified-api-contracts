"""Instadapp DeFi position aggregator schemas."""

from pydantic import BaseModel


class InstadappReserve(BaseModel):
    """Instadapp reserve/asset position within a protocol."""

    protocol: str | None = None
    asset: str | None = None
    supply_apy: str | None = None
    borrow_apy: str | None = None
    ltv: str | None = None
    liquidation_threshold: str | None = None


class InstadappPosition(BaseModel):
    """Instadapp position within a protocol (supply/borrow)."""

    protocol: str | None = None
    collateral: str | None = None
    debt: str | None = None


class InstadappSmartAccount(BaseModel):
    """Instadapp smart account aggregating positions across protocols."""

    address: str | None = None
    total_collateral_usd: str | None = None
    total_debt_usd: str | None = None
    net_worth_usd: str | None = None
    health_factor: str | None = None
    positions: list[InstadappPosition] | None = None
    reserves: list[InstadappReserve] | None = None
