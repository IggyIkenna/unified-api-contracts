"""Order and fill normalizers: raw venue responses -> CanonicalOrder, CanonicalFill."""

from __future__ import annotations

from datetime import UTC

from ..canonical.domain.execution import (
    CanonicalFill,
    OrderSide,
)
from ..canonical.domain.execution.prime_broker import PrimeBrokerFill
from ..external.aster.normalize import normalize_aster_order
from ..external.binance.normalize import (
    normalize_binance_fill,
    normalize_binance_order,
)
from ..external.bybit.normalize import (
    normalize_bybit_fill,
    normalize_bybit_order,
)
from ..external.ccxt.normalize import (
    normalize_ccxt_order,
    normalize_ccxt_trade_to_fill,
)
from ..external.coinbase.normalize import (
    normalize_coinbase_fill,
    normalize_coinbase_order,
)
from ..external.deribit.normalize import normalize_deribit_order
from ..external.fix.normalize import (
    normalize_fix_execution_report_to_fill,
    normalize_fix_execution_report_to_order,
    normalize_fix_new_order_single,
)
from ..external.hyperliquid.normalize import (
    normalize_hyperliquid_fill,
    normalize_hyperliquid_order,
)
from ..external.ibkr.normalize import (
    normalize_ibkr_execution,
    normalize_ibkr_order,
)
from ..external.kalshi.normalize import normalize_kalshi_fill
from ..external.nautilus.normalize import (
    normalize_nautilus_fill,
    normalize_nautilus_order,
)
from ..external.okx.normalize import normalize_okx_order
from ..external.polymarket.normalize import (
    normalize_polymarket_fill,
    normalize_polymarket_order,
)
from ..external.upbit.normalize import normalize_upbit_order

# ---------------------------------------------------------------------------
# Prime Broker — no external/prime_broker/normalize.py; keep inline
# ---------------------------------------------------------------------------


def _normalize_side(s: str | None) -> OrderSide:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def normalize_prime_broker_fill(raw: PrimeBrokerFill, venue: str | None = None) -> CanonicalFill:
    """Convert PrimeBrokerFill to CanonicalFill."""
    v = venue or str(raw.prime_broker).lower()
    ts = raw.timestamp if raw.timestamp.tzinfo else raw.timestamp.replace(tzinfo=UTC)
    return CanonicalFill(
        fill_id=raw.fill_id,
        order_id=raw.order_id,
        timestamp=ts,
        venue=v,
        instrument_id=raw.instrument_id,
        side=_normalize_side(raw.side),
        price=raw.price,
        quantity=raw.quantity,
        fee=raw.pb_fee_usd,
        fee_currency="USD" if raw.pb_fee_usd else None,
        is_maker=None,
    )


__all__ = [
    "normalize_aster_order",
    "normalize_binance_fill",
    "normalize_binance_order",
    "normalize_bybit_fill",
    "normalize_bybit_order",
    "normalize_ccxt_order",
    "normalize_ccxt_trade_to_fill",
    "normalize_coinbase_fill",
    "normalize_coinbase_order",
    "normalize_deribit_order",
    "normalize_fix_execution_report_to_fill",
    "normalize_fix_execution_report_to_order",
    "normalize_fix_new_order_single",
    "normalize_hyperliquid_fill",
    "normalize_hyperliquid_order",
    "normalize_ibkr_execution",
    "normalize_ibkr_order",
    "normalize_kalshi_fill",
    "normalize_nautilus_fill",
    "normalize_nautilus_order",
    "normalize_okx_order",
    "normalize_polymarket_fill",
    "normalize_polymarket_order",
    "normalize_prime_broker_fill",
    "normalize_upbit_order",
]
