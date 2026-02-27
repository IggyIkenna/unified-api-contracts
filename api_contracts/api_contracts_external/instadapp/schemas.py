"""Pydantic schemas for Instadapp DeFi position aggregator.

REST API for smart account positions, debt, collateral aggregated across
Aave, Compound, MakerDAO, Uniswap, Balancer.
Ref: https://docs.instadapp.io/
"""

from decimal import Decimal

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class InstadappPosition(BaseModel):
    """Single protocol position (Aave, Compound, MakerDAO, Uniswap, Balancer)."""

    protocol: str | None = Field(None, description="aave, compound, makerdao, uniswap, balancer")
    type: str | None = Field(None, description="lending, lp, vault, etc.")
    collateral: Decimal | None = None
    collateralUsd: Decimal | None = None
    debt: Decimal | None = None
    debtUsd: Decimal | None = None
    health_factor: Decimal | None = None
    ltv: Decimal | None = None
    liquidation_threshold: Decimal | None = None
    info: dict | None = None


class InstadappSmartAccount(BaseModel):
    """Smart account summary."""

    address: str | None = None
    total_collateral_usd: Decimal | None = None
    total_debt_usd: Decimal | None = None
    net_worth_usd: Decimal | None = None
    health_factor: Decimal | None = None
    positions: list[InstadappPosition] | None = None


class InstadappReserve(BaseModel):
    """Protocol reserve / market config."""

    protocol: str | None = None
    asset: str | None = None
    supply_apy: Decimal | None = None
    borrow_apy: Decimal | None = None
    ltv: Decimal | None = None
    liquidation_threshold: Decimal | None = None


class InstadappError(BaseModel):
    """Instadapp API error."""

    code: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, http_status: int | None = None) -> ErrorAction:
        """Map Instadapp error to retry action."""
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
