"""Reward position tracking — accrued, claimed, and sold reward tokens."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class RewardPosition(BaseModel):
    """Tracks reward token accrual, claiming, and selling for a protocol."""

    protocol: str
    reward_token: str
    accrued_amount: Decimal = Decimal("0")
    claimed_amount: Decimal = Decimal("0")
    sold_amount: Decimal = Decimal("0")
    accrued_value_usd: Decimal = Decimal("0")
    claimed_value_usd: Decimal = Decimal("0")
    last_claim_timestamp: str | None = None
    next_expected_claim: str | None = None
