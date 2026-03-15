"""Alchemy normalizers — asset transfers, token balances, blocks, transactions.

Maps Alchemy RPC/API response shapes to canonical types:
- AlchemyAssetTransfer -> CanonicalTrade
- AlchemyTokenBalance -> CanonicalBalance
- AlchemyBlock -> CanonicalOnChainMetric (block-level)
- AlchemyTransaction -> CanonicalOnChainMetric (tx-level)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalBalance, CanonicalOnChainMetric, CanonicalTrade
from .schemas import (
    AlchemyAssetTransfer,
    AlchemyBlock,
    AlchemyTokenBalance,
    AlchemyTransaction,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _d(val: float | int | str | Decimal | None) -> Decimal | None:
    """Convert numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _hex_to_int(hex_val: str | int | None) -> int | None:
    """Convert hex string (0x...) to int; return None on failure."""
    if hex_val is None:
        return None
    if isinstance(hex_val, int):
        return hex_val
    s = str(hex_val).strip()
    if not s:
        return None
    try:
        return int(s, 16)
    except (ValueError, TypeError):
        return None


def _hex_to_ts(hex_val: str | int | None) -> datetime:
    """Convert hex Unix timestamp (seconds) to UTC datetime."""
    val = _hex_to_int(hex_val)
    if val is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(val), tz=UTC)
    except (ValueError, OSError, OverflowError):
        return datetime.now(UTC)


def _hex_to_decimal(hex_val: str | int | None) -> Decimal | None:
    """Convert hex string (wei/smallest unit) to Decimal."""
    val = _hex_to_int(hex_val)
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Alchemy — asset transfers, balances, blocks, transactions
# ---------------------------------------------------------------------------


def normalize_alchemy_asset_transfer(
    raw: AlchemyAssetTransfer,
    chain: str,
    venue: str = "alchemy",
) -> CanonicalTrade | None:
    """Normalize AlchemyAssetTransfer to CanonicalTrade.

    Treats asset transfer as a trade: quantity = value, price = 1.
    blockNum/timestamp are hex; value may be float (already converted) or need hex handling.
    """
    if raw.value is None or raw.value <= 0:
        return None
    qty = _d(raw.value)
    if qty is None or qty <= 0:
        return None
    ts = datetime.now(UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=raw.asset or "ETH",
        trade_id=raw.hash or "",
        timestamp=ts,
        price=Decimal("1"),
        quantity=qty,
        side="sell",
        buyer_maker=None,
        venue_trade_id=raw.hash,
        instrument_key=f"{venue}:{chain}:{raw.asset or 'ETH'}",
        is_liquidation=None,
        schema_version="1.0",
    )


def normalize_alchemy_token_balance(
    raw: AlchemyTokenBalance,
    address: str,
    chain: str,
    venue: str = "alchemy",
) -> CanonicalBalance | None:
    """Normalize AlchemyTokenBalance to CanonicalBalance.

    tokenBalance is hex string (wei/smallest unit); convert via _hex_to_decimal.
    """
    bal = _hex_to_decimal(raw.tokenBalance)
    if bal is None:
        return None
    decimals = raw.decimals or 18
    divisor = Decimal(10) ** decimals
    total = bal / divisor
    raw_dict: dict[str, object] = {
        "contractAddress": raw.contractAddress,
        "tokenBalance": raw.tokenBalance,
        "symbol": raw.symbol,
        "decimals": raw.decimals,
        "name": raw.name,
    }
    return CanonicalBalance(
        currency=raw.symbol or raw.name or "UNKNOWN",
        free=total,
        locked=Decimal("0"),
        total=total,
        venue=venue,
        available=total,
        timestamp=datetime.now(UTC),
        raw=raw_dict,
    )


def normalize_alchemy_block_to_metric(
    raw: AlchemyBlock,
    chain: str,
    venue: str = "alchemy",
) -> CanonicalOnChainMetric | None:
    """Normalize AlchemyBlock to CanonicalOnChainMetric (block-level metric).

    metric_type = "block"
    value = gasUsed, secondary_value = gasLimit.
    timestamp from block timestamp (hex).
    """
    ts = _hex_to_ts(raw.timestamp)
    gas_used = _hex_to_decimal(raw.gasUsed)
    gas_limit = _hex_to_decimal(raw.gasLimit)
    raw_dict: dict[str, float | int | str | None] = {
        "number": raw.number,
        "hash": raw.hash,
        "gasUsed": raw.gasUsed,
        "gasLimit": raw.gasLimit,
        "timestamp": raw.timestamp,
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="block",
        asset=None,
        value=gas_used,
        secondary_value=gas_limit,
        entity=raw.hash,
        chain=chain,
        raw=raw_dict,
        schema_version="1.0",
    )


def normalize_alchemy_transaction_to_metric(
    raw: AlchemyTransaction,
    chain: str,
    venue: str = "alchemy",
) -> CanonicalOnChainMetric | None:
    """Normalize AlchemyTransaction to CanonicalOnChainMetric (tx-level metric).

    metric_type = "transaction"
    value = value (wei), secondary_value = gasUsed or gas.
    """
    val = _hex_to_decimal(raw.value)
    gas = _hex_to_decimal(raw.gas)
    raw_dict: dict[str, float | int | str | None] = {
        "hash": raw.hash,
        "blockNumber": raw.blockNumber,
        "from": raw.from_,
        "to": raw.to,
        "value": raw.value,
        "gas": raw.gas,
        "gasPrice": raw.gasPrice,
    }
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="transaction",
        asset=None,
        value=val,
        secondary_value=gas,
        entity=raw.hash,
        chain=chain,
        raw=raw_dict,
        schema_version="1.0",
    )


__all__ = [
    "normalize_alchemy_asset_transfer",
    "normalize_alchemy_block_to_metric",
    "normalize_alchemy_token_balance",
    "normalize_alchemy_transaction_to_metric",
]
