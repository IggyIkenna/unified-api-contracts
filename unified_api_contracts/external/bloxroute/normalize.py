"""bloXroute BDN normalizers — Block, tx, mempool schemas to canonical types.

Maps bloXroute BDN streams to:
- BloxrouteMempoolNotification -> CanonicalTrade (when tx_contents has value)
- BloxrouteTxSubmitResult -> CanonicalTrade (minimal submit confirmation)
- BloxrouteMempoolNotification -> CanonicalOraclePriceFeed | None (when oracle tx in mempool; stub)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.crosscutting.errors import CanonicalError, ErrorAction
from ...canonical.domain import CanonicalOraclePriceFeed, CanonicalTrade
from ...normalize_utils.errors._utils import from_http_status
from .schemas import BloxrouteMempoolNotification, BloxrouteTxSubmitResult

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


def _hex_to_decimal(hex_val: str | int | None) -> Decimal | None:
    """Convert hex string (0x...) to Decimal; return None on failure."""
    if hex_val is None:
        return None
    if isinstance(hex_val, int):
        return Decimal(str(hex_val))
    s = str(hex_val).strip()
    if not s:
        return None
    try:
        if s.lower().startswith("0x"):
            return Decimal(int(s, 16))
        return Decimal(s)
    except (ValueError, TypeError, InvalidOperation):
        return None


def _extract_tx_value(tx_contents: dict[str, object] | None) -> Decimal | None:
    """Extract native value from tx_contents dict (value field, hex or int)."""
    if not tx_contents:
        return None
    val = tx_contents.get("value") or tx_contents.get("Value")
    if val is None:
        return None
    if isinstance(val, str) and str(val).strip().lower().startswith("0x"):
        return _hex_to_decimal(val)
    return _d(val)


# ---------------------------------------------------------------------------
# bloXroute — mempool and tx submission
# ---------------------------------------------------------------------------


def normalize_bloxroute_mempool_to_trade(
    raw: BloxrouteMempoolNotification,
    venue: str = "bloxroute",
    symbol: str = "ETH",
) -> CanonicalTrade | None:
    """Normalize BloxrouteMempoolNotification to CanonicalTrade.

    Extracts value from tx_contents when present. Uses tx_hash as trade_id.
    price=1 for native transfer; side='buy' (incoming from mempool perspective).
    Returns None if tx_hash or value missing.
    """
    if not raw.tx_hash or raw.tx_hash.strip() == "":
        return None
    qty = _extract_tx_value(raw.tx_contents)
    if qty is None or qty <= 0:
        return None
    network = raw.blockchain_network or raw.network or "Mainnet"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol,
        trade_id=raw.tx_hash,
        timestamp=datetime.now(UTC),
        price=Decimal("1"),
        quantity=qty,
        side="buy",
        buyer_maker=None,
        venue_trade_id=raw.tx_hash,
        instrument_key=f"{venue}:{network}:{symbol}",
        is_liquidation=None,
        schema_version="1.0",
    )


def normalize_bloxroute_tx_submit_to_trade(
    raw: BloxrouteTxSubmitResult,
    venue: str = "bloxroute",
    symbol: str = "ETH",
    quantity: Decimal | None = None,
) -> CanonicalTrade | None:
    """Normalize BloxrouteTxSubmitResult to CanonicalTrade.

    Minimal trade representation for tx submission confirmation.
    quantity must be provided or defaults to Decimal('1') for valid CanonicalTrade.
    """
    if not raw.tx_hash or raw.tx_hash.strip() == "":
        return None
    qty = quantity if quantity is not None and quantity > 0 else Decimal("1")
    return CanonicalTrade(
        venue=venue,
        symbol=symbol,
        trade_id=raw.tx_hash,
        timestamp=datetime.now(UTC),
        price=Decimal("1"),
        quantity=qty,
        side="buy",
        buyer_maker=None,
        venue_trade_id=raw.tx_hash,
        instrument_key=None,
        is_liquidation=None,
        schema_version="1.0",
    )


def normalize_bloxroute_mempool_to_oracle_feed(
    raw: BloxrouteMempoolNotification,
    venue: str = "bloxroute",
) -> CanonicalOraclePriceFeed | None:
    """Normalize BloxrouteMempoolNotification to CanonicalOraclePriceFeed.

    Returns None — mempool notifications do not contain oracle price data.
    Reserved for future Block schema with oracle update parsing.
    """
    return None


def normalize_bloxroute_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bloxroute",
) -> CanonicalError:
    """Map a bloXroute JSON-RPC error code to CanonicalError."""
    code = str(error_code)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_bloxroute_error",
    "normalize_bloxroute_mempool_to_oracle_feed",
    "normalize_bloxroute_mempool_to_trade",
    "normalize_bloxroute_tx_submit_to_trade",
]
