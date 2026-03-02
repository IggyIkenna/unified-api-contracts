"""Factory functions for creating NautilusTrader-like test data.

Use these in execution-services tests to create Order, Position, Instrument, Fill, Account,
MockCache, and MockClock instances without the full nautilus-trader dependency.
"""

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.nautilus.cache import MockCache
from unified_api_contracts.nautilus.clock import MockClock
from unified_api_contracts.nautilus.schemas import Account, Fill, Instrument, Order, Position


def mock_order(
    *,
    order_id: str = "O-001",
    instrument_id: str = "BTCUSDT-PERP.BINANCE",
    side: str = "BUY",
    quantity: Decimal | str = "1.0",
    price: Decimal | str | None = "50000",
    status: str = "FILLED",
    timestamp: datetime | None = None,
    client_order_id: str | None = None,
    order_type: str = "LIMIT",
    filled_qty: Decimal | str = "1.0",
    avg_px: Decimal | str | None = "50000",
    account_id: str | None = "SIM-001",
    strategy_id: str | None = "strategy-001",
) -> Order:
    """Create a test Order with sensible defaults."""
    qty = Decimal(str(quantity)) if isinstance(quantity, str) else quantity
    ts = timestamp or datetime.now(UTC)
    return Order(
        order_id=order_id,
        instrument_id=instrument_id,
        side=side,
        quantity=qty,
        price=Decimal(str(price)) if price is not None else None,
        status=status,
        timestamp=ts,
        client_order_id=client_order_id or order_id,
        order_type=order_type,
        filled_qty=Decimal(str(filled_qty)) if isinstance(filled_qty, str) else filled_qty,
        avg_px=Decimal(str(avg_px)) if avg_px is not None else None,
        venue_order_id=None,
        account_id=account_id,
        strategy_id=strategy_id,
    )


def mock_position(
    *,
    position_id: str = "P-001",
    instrument_id: str = "BTCUSDT-PERP.BINANCE",
    side: str = "LONG",
    quantity: Decimal | str = "1.0",
    signed_qty: Decimal | str = "1.0",
    entry_price: Decimal | str = "50000",
    unrealized_pnl: Decimal | str = "0",
    realized_pnl: Decimal | str = "0",
    timestamp: datetime | None = None,
    account_id: str | None = "SIM-001",
    strategy_id: str | None = "strategy-001",
    venue: str | None = "BINANCE",
    is_open: bool = True,
) -> Position:
    """Create a test Position with sensible defaults."""
    qty = Decimal(str(quantity)) if isinstance(quantity, str) else quantity
    ts = timestamp or datetime.now(UTC)
    return Position(
        position_id=position_id,
        instrument_id=instrument_id,
        side=side,
        quantity=qty,
        signed_qty=Decimal(str(signed_qty)) if isinstance(signed_qty, str) else signed_qty,
        entry_price=Decimal(str(entry_price)) if isinstance(entry_price, str) else entry_price,
        unrealized_pnl=Decimal(str(unrealized_pnl)) if isinstance(unrealized_pnl, str) else unrealized_pnl,
        realized_pnl=Decimal(str(realized_pnl)) if isinstance(realized_pnl, str) else realized_pnl,
        timestamp=ts,
        account_id=account_id,
        strategy_id=strategy_id,
        venue=venue,
        is_open=is_open,
    )


def mock_instrument(
    *,
    instrument_id: str = "BTCUSDT-PERP.BINANCE",
    symbol: str = "BTCUSDT-PERP",
    venue: str = "BINANCE",
    asset_class: str = "CRYPTO",
    tick_size: Decimal | str = "0.01",
    lot_size: Decimal | str = "0.001",
    price_precision: int = 2,
    size_precision: int = 3,
    base_currency: str | None = "BTC",
    quote_currency: str | None = "USDT",
    is_inverse: bool = False,
    multiplier: Decimal | str = "1",
) -> Instrument:
    """Create a test Instrument with sensible defaults."""
    return Instrument(
        instrument_id=instrument_id,
        symbol=symbol,
        venue=venue,
        asset_class=asset_class,
        tick_size=Decimal(str(tick_size)) if isinstance(tick_size, str) else tick_size,
        lot_size=Decimal(str(lot_size)) if isinstance(lot_size, str) else lot_size,
        price_precision=price_precision,
        size_precision=size_precision,
        base_currency=base_currency,
        quote_currency=quote_currency,
        is_inverse=is_inverse,
        multiplier=Decimal(str(multiplier)) if isinstance(multiplier, str) else multiplier,
    )


def mock_fill(
    *,
    fill_id: str = "F-001",
    order_id: str = "O-001",
    instrument_id: str = "BTCUSDT-PERP.BINANCE",
    quantity: Decimal | str = "1.0",
    price: Decimal | str = "50000",
    timestamp: datetime | None = None,
    side: str = "BUY",
    commission: Decimal | str = "0",
    commission_currency: str | None = "USDT",
    position_id: str | None = None,
) -> Fill:
    """Create a test Fill with sensible defaults."""
    ts = timestamp or datetime.now(UTC)
    return Fill(
        fill_id=fill_id,
        order_id=order_id,
        instrument_id=instrument_id,
        quantity=Decimal(str(quantity)) if isinstance(quantity, str) else quantity,
        price=Decimal(str(price)) if isinstance(price, str) else price,
        timestamp=ts,
        side=side,
        commission=Decimal(str(commission)) if isinstance(commission, str) else commission,
        commission_currency=commission_currency,
        venue_trade_id=None,
        position_id=position_id,
    )


def mock_account(
    *,
    account_id: str = "SIM-001",
    balance: Decimal | str = "100000",
    equity: Decimal | str = "100000",
    margin: Decimal | str = "0",
    free_margin: Decimal | str = "100000",
    currency: str = "USDT",
    timestamp: datetime | None = None,
    venue: str | None = "BINANCE",
    is_margin_account: bool = True,
) -> Account:
    """Create a test Account with sensible defaults."""
    ts = timestamp or datetime.now(UTC)
    return Account(
        account_id=account_id,
        balance=Decimal(str(balance)) if isinstance(balance, str) else balance,
        equity=Decimal(str(equity)) if isinstance(equity, str) else equity,
        margin=Decimal(str(margin)) if isinstance(margin, str) else margin,
        free_margin=Decimal(str(free_margin)) if isinstance(free_margin, str) else free_margin,
        currency=currency,
        timestamp=ts,
        venue=venue,
        is_margin_account=is_margin_account,
    )


def mock_cache(
    *,
    orders: list[Order] | None = None,
    positions: list[Position] | None = None,
    instruments: list[Instrument] | None = None,
    fills: list[Fill] | None = None,
    accounts: list[Account] | None = None,
) -> MockCache:
    """Create a MockCache pre-populated with test data."""
    cache = MockCache()
    for o in orders or [mock_order()]:
        cache.add_order(o)
    for p in positions or [mock_position()]:
        cache.add_position(p)
    for i in instruments or [mock_instrument()]:
        cache.add_instrument(i)
    for f in fills or [mock_fill()]:
        cache.add_fill(f)
    for a in accounts or [mock_account()]:
        cache.add_account(a)
    return cache


def mock_clock(*, timestamp_ns: int | None = None) -> MockClock:
    """Create a MockClock, optionally with fixed timestamp for deterministic tests."""
    return MockClock(timestamp_ns=timestamp_ns)
