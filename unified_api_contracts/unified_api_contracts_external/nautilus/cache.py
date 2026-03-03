"""Cache Protocol and MockCache for NautilusTrader-like cache in execution-services testing.

Mirrors NautilusTrader Cache interface for order, position, instrument, fill, and account lookups.
Reference: https://nautilustrader.io/docs/nightly/concepts/cache/
"""

from typing import Protocol

from .schemas import Account, Fill, Instrument, Order, Position


class Cache(Protocol):
    """Abstract interface for NautilusTrader-like cache.

    Used for dependency injection in execution-services tests.
    """

    def get_order(self, order_id: str) -> Order | None:
        """Return order by ID or None if not found."""
        ...

    def get_position(self, position_id: str) -> Position | None:
        """Return position by ID or None if not found."""
        ...

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        """Return instrument by ID or None if not found."""
        ...

    def get_fills(self, order_id: str | None = None) -> list[Fill]:
        """Return fills, optionally filtered by order_id."""
        ...

    def get_account(self, account_id: str) -> Account | None:
        """Return account by ID or None if not found."""
        ...


class MockCache:
    """In-memory mock implementation of Cache for testing."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self._instruments: dict[str, Instrument] = {}
        self._fills: list[Fill] = []
        self._accounts: dict[str, Account] = {}

    def add_order(self, order: Order) -> None:
        """Add or overwrite an order."""
        self._orders[order.order_id] = order

    def add_position(self, position: Position) -> None:
        """Add or overwrite a position."""
        self._positions[position.position_id] = position

    def add_instrument(self, instrument: Instrument) -> None:
        """Add or overwrite an instrument."""
        self._instruments[instrument.instrument_id] = instrument

    def add_fill(self, fill: Fill) -> None:
        """Add a fill."""
        self._fills.append(fill)

    def add_account(self, account: Account) -> None:
        """Add or overwrite an account."""
        self._accounts[account.account_id] = account

    def get_order(self, order_id: str) -> Order | None:
        """Return order by ID or None if not found."""
        return self._orders.get(order_id)

    def get_position(self, position_id: str) -> Position | None:
        """Return position by ID or None if not found."""
        return self._positions.get(position_id)

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        """Return instrument by ID or None if not found."""
        return self._instruments.get(instrument_id)

    def get_fills(self, order_id: str | None = None) -> list[Fill]:
        """Return fills, optionally filtered by order_id."""
        if order_id is None:
            return list(self._fills)
        return [f for f in self._fills if f.order_id == order_id]

    def get_account(self, account_id: str) -> Account | None:
        """Return account by ID or None if not found."""
        return self._accounts.get(account_id)

    def clear(self) -> None:
        """Clear all cached data."""
        self._orders.clear()
        self._positions.clear()
        self._instruments.clear()
        self._fills.clear()
        self._accounts.clear()
