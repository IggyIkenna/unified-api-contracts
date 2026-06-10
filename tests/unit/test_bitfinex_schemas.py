"""Tests for external/bitfinex/schemas.py — Bitfinex v2 schema models and from_list classmethods."""

from __future__ import annotations

from unified_api_contracts.external.bitfinex.schemas import (
    BitfinexOrder,
    BitfinexOrderBook,
    BitfinexOrderBookLevel,
    BitfinexTrade,
)

# ---------------------------------------------------------------------------
# BitfinexTrade.from_list
# ---------------------------------------------------------------------------


def test_trade_from_list_full() -> None:
    row = [123456789, 1704067200000, 0.5, 43000.0]
    trade = BitfinexTrade.from_list(row)
    assert trade.ID == 123456789
    assert trade.MTS == 1704067200000
    assert trade.AMOUNT == 0.5
    assert trade.PRICE == 43000.0
    assert trade.trade_type == "te"


def test_trade_from_list_custom_trade_type() -> None:
    row = [1, 2, 3.0, 4.0]
    trade = BitfinexTrade.from_list(row, trade_type="tu")
    assert trade.trade_type == "tu"


def test_trade_from_list_short_row() -> None:
    """Rows shorter than expected fill missing fields with None."""
    trade = BitfinexTrade.from_list([42])
    assert trade.ID == 42
    assert trade.MTS is None
    assert trade.AMOUNT is None
    assert trade.PRICE is None


def test_trade_from_list_empty_row() -> None:
    trade = BitfinexTrade.from_list([])
    assert trade.ID is None


def test_trade_sell_side_negative_amount() -> None:
    row = [99, 1000, -1.0, 42000.0]
    trade = BitfinexTrade.from_list(row)
    assert trade.AMOUNT == -1.0


# ---------------------------------------------------------------------------
# BitfinexOrderBookLevel.from_list
# ---------------------------------------------------------------------------


def test_order_book_level_from_list() -> None:
    row = [43000.0, 5, 2.5]
    level = BitfinexOrderBookLevel.from_list(row)
    assert level.PRICE == 43000.0
    assert level.COUNT == 5
    assert level.AMOUNT == 2.5


def test_order_book_level_bid_positive_amount() -> None:
    level = BitfinexOrderBookLevel.from_list([100.0, 1, 10.0])
    assert level.AMOUNT > 0


def test_order_book_level_ask_negative_amount() -> None:
    level = BitfinexOrderBookLevel.from_list([100.0, 1, -10.0])
    assert level.AMOUNT < 0


def test_order_book_level_remove_level_count_zero() -> None:
    """COUNT=0 signals price level removal."""
    level = BitfinexOrderBookLevel.from_list([99.0, 0, 0.0])
    assert level.COUNT == 0


# ---------------------------------------------------------------------------
# BitfinexOrderBook (model construction)
# ---------------------------------------------------------------------------


def test_order_book_defaults() -> None:
    book = BitfinexOrderBook()
    assert book.bids == []
    assert book.asks == []
    assert book.symbol is None


def test_order_book_with_levels() -> None:
    bid = BitfinexOrderBookLevel.from_list([100.0, 3, 5.0])
    ask = BitfinexOrderBookLevel.from_list([101.0, 2, -5.0])
    book = BitfinexOrderBook(bids=[bid], asks=[ask], symbol="tBTCUSD")
    assert len(book.bids) == 1
    assert len(book.asks) == 1
    assert book.symbol == "tBTCUSD"


# ---------------------------------------------------------------------------
# BitfinexOrder (minimal — validates model construction)
# ---------------------------------------------------------------------------


def test_bitfinex_order_defaults() -> None:
    order = BitfinexOrder()
    # Should construct without errors; key fields default to None
    assert order.ID is None
    assert order.SYMBOL is None
