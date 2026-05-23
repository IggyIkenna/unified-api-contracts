"""Instadapp normalizers — DeFi position aggregator.

Maps Instadapp schemas to canonical types:
- InstadappPosition -> CanonicalPosition
- InstadappReserve -> CanonicalBalance (metadata; amounts in raw when available)
- InstadappSmartAccount -> list of CanonicalPosition, CanonicalBalance
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalBalance, CanonicalPosition
from ...normalize_utils._helpers import _d
from .schemas import InstadappPosition, InstadappReserve, InstadappSmartAccount


def normalize_instadapp_position(
    raw: InstadappPosition,
    venue: str = "instadapp",
    timestamp: datetime | None = None,
) -> CanonicalPosition | None:
    """Normalize InstadappPosition to CanonicalPosition.

    Maps protocol to instrument_id, collateral to quantity (LONG), debt in raw.
    Uses default price=1 when not provided.
    """
    if raw.protocol is None and raw.collateral is None and raw.debt is None:
        return None
    collateral = _d(raw.collateral)
    debt = _d(raw.debt)
    quantity = collateral
    if quantity <= 0 and debt <= 0:
        return None
    side = "LONG" if collateral >= debt else "SHORT"
    if quantity <= 0:
        quantity = debt
    ts = timestamp or datetime.now(UTC)
    raw_dict: dict[str, object] = {
        "protocol": raw.protocol,
        "collateral": raw.collateral,
        "debt": raw.debt,
    }
    return CanonicalPosition(
        instrument_id=raw.protocol or "unknown",
        side=side,
        quantity=quantity,
        entry_price=Decimal("1"),
        mark_price=Decimal("1"),
        unrealized_pnl=Decimal("0"),
        venue=venue,
        timestamp=ts,
        raw=raw_dict,
    )


def normalize_instadapp_reserve(
    raw: InstadappReserve,
    venue: str = "instadapp",
    timestamp: datetime | None = None,
) -> CanonicalBalance | None:
    """Normalize InstadappReserve to CanonicalBalance.

    Reserve holds APY/ltv metadata; balance amounts are typically from elsewhere.
    Maps asset to currency; supply_apy, borrow_apy, ltv, liquidation_threshold in raw.
    """
    if raw.asset is None and raw.protocol is None:
        return None
    ts = timestamp or datetime.now(UTC)
    raw_dict: dict[str, object] = {
        "protocol": raw.protocol,
        "supply_apy": raw.supply_apy,
        "borrow_apy": raw.borrow_apy,
        "ltv": raw.ltv,
        "liquidation_threshold": raw.liquidation_threshold,
    }
    return CanonicalBalance(
        currency=raw.asset or raw.protocol or "unknown",
        free=Decimal("0"),
        locked=Decimal("0"),
        total=Decimal("0"),
        venue=venue,
        timestamp=ts,
        raw=raw_dict,
    )


def normalize_instadapp_smart_account(
    raw: InstadappSmartAccount,
    venue: str = "instadapp",
) -> tuple[list[CanonicalPosition], list[CanonicalBalance]]:
    """Normalize InstadappSmartAccount to lists of CanonicalPosition and CanonicalBalance.

    Aggregates positions and reserves; total_collateral_usd, total_debt_usd, health_factor
    stored in first position/balance raw for account-level context.
    """
    ts = datetime.now(UTC)
    account_raw: dict[str, object] = {
        "address": raw.address,
        "total_collateral_usd": raw.total_collateral_usd,
        "total_debt_usd": raw.total_debt_usd,
        "net_worth_usd": raw.net_worth_usd,
        "health_factor": raw.health_factor,
    }
    positions: list[CanonicalPosition] = []
    if raw.positions:
        for p in raw.positions:
            pos = normalize_instadapp_position(p, venue=venue, timestamp=ts)
            if pos is not None:
                merged_raw = dict(account_raw)
                merged_raw.update(pos.raw or {})
                pos.raw = merged_raw
                positions.append(pos)
    balances: list[CanonicalBalance] = []
    if raw.reserves:
        for r in raw.reserves:
            bal = normalize_instadapp_reserve(r, venue=venue, timestamp=ts)
            if bal is not None:
                merged_raw = dict(account_raw)
                merged_raw.update(bal.raw or {})
                bal.raw = merged_raw
                balances.append(bal)
    return (positions, balances)


__all__ = [
    "normalize_instadapp_position",
    "normalize_instadapp_reserve",
    "normalize_instadapp_smart_account",
]
