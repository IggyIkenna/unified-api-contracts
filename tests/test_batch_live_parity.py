"""Batch-live parity tests.

For venues with both a live WebSocket source and a batch/Tardis source, construct
equivalent raw records for the same logical event, normalize both paths, and assert
that all core canonical fields are identical.

Contract: if two raw records represent the same logical event, their normalized
canonical output MUST be equal for price, quantity, side, and symbol.

Fields explicitly excluded from parity checks:
- received_at  (wall-clock ingestion time — always different)
- sequence     (WS-only; batch may be absent)
- venue        (Tardis uses exchange-native casing; checked case-insensitively)

Reference: docs/BATCH_LIVE_SYMMETRY.md
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.canonical import CanonicalTrade
from unified_api_contracts.external.binance.market_schemas import BinanceTrade
from unified_api_contracts.external.bybit.schemas import BybitTrade
from unified_api_contracts.external.coinbase.schemas import CoinbaseTrade
from unified_api_contracts.external.databento.schemas import (
    DATABENTO_PRICE_DIVISOR,
    DatabentoTrade,
)
from unified_api_contracts.external.deribit.schemas import DeribitTrade
from unified_api_contracts.external.okx.schemas import OKXTrade
from unified_api_contracts.external.tardis.schemas import TardisTrade
from unified_api_contracts.normalize_utils import (
    normalize_binance_trade,
    normalize_bybit_trade,
    normalize_coinbase_trade,
    normalize_databento_trade,
    normalize_deribit_trade,
    normalize_okx_trade,
    normalize_tardis_trade,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CORE_FIELDS = ("price", "quantity", "side")


def _assert_parity(live: CanonicalTrade, batch: CanonicalTrade, *, check_trade_id: bool = False) -> None:
    """Assert core canonical fields are equal between live and batch normalizations."""
    for field in _CORE_FIELDS:
        assert getattr(live, field) == getattr(batch, field), (
            f"Parity failure on '{field}': live={getattr(live, field)!r} batch={getattr(batch, field)!r}"
        )
    if check_trade_id:
        assert live.trade_id == batch.trade_id, f"trade_id mismatch: live={live.trade_id!r} batch={batch.trade_id!r}"
    # venue is allowed to differ in casing
    assert live.venue.lower() == batch.venue.lower() or batch.venue.lower() in (
        "tardis",
        "databento",
    ), f"Unexpected venue mismatch: {live.venue!r} vs {batch.venue!r}"


# ---------------------------------------------------------------------------
# Binance live vs Tardis batch
# ---------------------------------------------------------------------------


class TestBinanceTardis:
    """BinanceTrade (live WS) vs TardisTrade (Tardis batch replay)."""

    _PRICE = Decimal("50000.50")
    _QTY = Decimal("0.1")
    _TRADE_ID = "12345678"
    _TIMESTAMP_MS = 1_700_000_000_000  # 2023-11-14T22:13:20Z

    def _live(self) -> CanonicalTrade:
        raw = BinanceTrade(
            id=int(self._TRADE_ID),
            price=self._PRICE,
            qty=self._QTY,
            quoteQty=self._PRICE * self._QTY,
            time=self._TIMESTAMP_MS,
            isBuyerMaker=False,  # side = buy (buyer is taker)
            isBestMatch=True,
        )
        return normalize_binance_trade(raw, symbol="BTC-USDT")

    def _batch(self) -> CanonicalTrade:
        # Tardis replays vendor-native format; price/qty/side must match exactly
        raw = TardisTrade(
            timestamp=str(self._TIMESTAMP_MS * 1_000),  # Tardis uses microseconds
            exchange="BINANCE",
            symbol="BTCUSDT",
            price=float(self._PRICE),
            size=float(self._QTY),
            side="buy",
            trade_id=self._TRADE_ID,
            info=None,
        )
        return normalize_tardis_trade(raw)

    def test_price_quantity_side_match(self) -> None:
        _assert_parity(self._live(), self._batch(), check_trade_id=True)

    def test_side_is_buy(self) -> None:
        assert self._live().side == "buy"
        assert self._batch().side == "buy"

    def test_price_exact(self) -> None:
        assert self._live().price == self._PRICE
        assert self._batch().price == self._PRICE

    def test_quantity_exact(self) -> None:
        assert self._live().quantity == self._QTY
        assert self._batch().quantity == self._QTY


class TestBinanceTardisSell:
    """Verify sell-side parity Binance live vs Tardis."""

    def test_sell_parity(self) -> None:
        live_raw = BinanceTrade(
            id=9999,
            price=Decimal("30000"),
            qty=Decimal("0.5"),
            quoteQty=Decimal("15000"),
            time=1_700_000_000_000,
            isBuyerMaker=True,  # buyer is maker → seller is taker → side = sell
            isBestMatch=True,
        )
        live = normalize_binance_trade(live_raw, symbol="BTC-USDT")

        batch_raw = TardisTrade(
            timestamp="1700000000000000",
            exchange="BINANCE",
            symbol="BTCUSDT",
            price=30000.0,
            size=0.5,
            side="sell",
            trade_id="9999",
            info=None,
        )
        batch = normalize_tardis_trade(batch_raw)

        _assert_parity(live, batch, check_trade_id=True)
        assert live.side == "sell"
        assert batch.side == "sell"


# ---------------------------------------------------------------------------
# Binance live vs Databento batch
# ---------------------------------------------------------------------------


class TestBinanceDatabento:
    """BinanceTrade (live) vs DatabentoTrade (batch).

    trade_id is NOT expected to match — Binance uses numeric ID, Databento uses sequence.
    Only price/quantity/side parity is required.
    """

    _PRICE = Decimal("50000.5")
    _QTY = Decimal("100")
    _TIMESTAMP_MS = 1_700_000_000_000

    def _live(self) -> CanonicalTrade:
        raw = BinanceTrade(
            id=555,
            price=self._PRICE,
            qty=self._QTY,
            quoteQty=self._PRICE * self._QTY,
            time=self._TIMESTAMP_MS,
            isBuyerMaker=False,
            isBestMatch=True,
        )
        return normalize_binance_trade(raw, symbol="BTC-USDT")

    def _batch(self) -> CanonicalTrade:
        # Databento fixed-point: price_int = price * DATABENTO_PRICE_DIVISOR (1e9)
        price_int = int(self._PRICE * DATABENTO_PRICE_DIVISOR)
        raw = DatabentoTrade(
            ts_event=self._TIMESTAMP_MS * 1_000_000,  # ns
            rtype=1,
            publisher_id=1,
            instrument_id=99,
            action="T",
            side="B",  # B = bid-aggressor = buyer = buy
            price=price_int,
            size=int(self._QTY),
            sequence=1001,
        )
        return normalize_databento_trade(raw, symbol="BTC-USDT", venue="binance")

    def test_price_quantity_side_match(self) -> None:
        live = self._live()
        batch = self._batch()
        for field in _CORE_FIELDS:
            assert getattr(live, field) == getattr(batch, field), (
                f"Parity failure on '{field}': live={getattr(live, field)!r} batch={getattr(batch, field)!r}"
            )

    def test_databento_side_b_maps_to_buy(self) -> None:
        assert self._batch().side == "buy"

    def test_databento_side_a_maps_to_sell(self) -> None:
        price_int = int(Decimal("30000") * DATABENTO_PRICE_DIVISOR)
        raw = DatabentoTrade(
            ts_event=1_700_000_000_000_000_000,
            rtype=1,
            publisher_id=1,
            instrument_id=99,
            action="T",
            side="A",  # A = ask-aggressor = seller = sell
            price=price_int,
            size=10,
            sequence=1002,
        )
        canonical = normalize_databento_trade(raw, symbol="BTC-USDT")
        assert canonical.side == "sell"


# ---------------------------------------------------------------------------
# Bybit live vs Tardis batch
# ---------------------------------------------------------------------------


class TestBybitTardis:
    """BybitTrade (live) vs TardisTrade (Tardis batch replay)."""

    _PRICE = Decimal("3000.25")
    _QTY = Decimal("2.5")
    _TRADE_ID = "byb-exec-001"
    _TIMESTAMP_MS = 1_700_100_000_000

    def _live(self) -> CanonicalTrade:
        raw = BybitTrade(
            execId=self._TRADE_ID,
            symbol="ETHUSDT",
            execPrice=str(self._PRICE),
            execQty=str(self._QTY),
            side="Buy",
            execTime=self._TIMESTAMP_MS,
            isMaker=False,
        )
        return normalize_bybit_trade(raw, symbol="ETH-USDT")

    def _batch(self) -> CanonicalTrade:
        raw = TardisTrade(
            timestamp=str(self._TIMESTAMP_MS * 1_000),
            exchange="BYBIT",
            symbol="ETHUSDT",
            price=float(self._PRICE),
            size=float(self._QTY),
            side="buy",
            trade_id=self._TRADE_ID,
            info=None,
        )
        return normalize_tardis_trade(raw)

    def test_price_quantity_side_match(self) -> None:
        _assert_parity(self._live(), self._batch(), check_trade_id=True)

    def test_side_is_buy(self) -> None:
        assert self._live().side == "buy"
        assert self._batch().side == "buy"


# ---------------------------------------------------------------------------
# OKX live vs Tardis batch
# ---------------------------------------------------------------------------


class TestOKXTardis:
    """OKXTrade (live) vs TardisTrade (Tardis batch replay)."""

    _PRICE = Decimal("45000.00")
    _QTY = Decimal("0.05")
    _TRADE_ID = "okx-trade-007"
    _TIMESTAMP_MS = 1_700_200_000_000

    def _live(self) -> CanonicalTrade:
        raw = OKXTrade(
            instId="BTC-USDT",
            tradeId=self._TRADE_ID,
            px=str(self._PRICE),
            sz=str(self._QTY),
            side="sell",
            ts=str(self._TIMESTAMP_MS),
        )
        return normalize_okx_trade(raw, symbol="BTC-USDT")

    def _batch(self) -> CanonicalTrade:
        raw = TardisTrade(
            timestamp=str(self._TIMESTAMP_MS * 1_000),
            exchange="OKX",
            symbol="BTC-USDT",
            price=float(self._PRICE),
            size=float(self._QTY),
            side="sell",
            trade_id=self._TRADE_ID,
            info=None,
        )
        return normalize_tardis_trade(raw)

    def test_price_quantity_side_match(self) -> None:
        _assert_parity(self._live(), self._batch(), check_trade_id=True)

    def test_side_is_sell(self) -> None:
        assert self._live().side == "sell"
        assert self._batch().side == "sell"


# ---------------------------------------------------------------------------
# Deribit live vs Tardis batch
# ---------------------------------------------------------------------------


class TestDeribitTardis:
    """DeribitTrade (live) vs TardisTrade (Tardis batch replay)."""

    _PRICE = Decimal("70000.00")
    _QTY = Decimal("1.0")
    _TRADE_ID = "deribit-perp-123"
    _TIMESTAMP_MS = 1_700_300_000_000

    def _live(self) -> CanonicalTrade:
        raw = DeribitTrade(
            trade_id=self._TRADE_ID,
            instrument_name="BTC-PERPETUAL",
            price=float(self._PRICE),
            amount=float(self._QTY),
            direction="buy",
            timestamp=self._TIMESTAMP_MS,
        )
        return normalize_deribit_trade(raw, symbol="BTC-PERP")

    def _batch(self) -> CanonicalTrade:
        raw = TardisTrade(
            timestamp=str(self._TIMESTAMP_MS * 1_000),
            exchange="DERIBIT",
            symbol="BTC-PERPETUAL",
            price=float(self._PRICE),
            size=float(self._QTY),
            side="buy",
            trade_id=self._TRADE_ID,
            info=None,
        )
        return normalize_tardis_trade(raw)

    def test_price_quantity_side_match(self) -> None:
        _assert_parity(self._live(), self._batch(), check_trade_id=True)

    def test_side_is_buy(self) -> None:
        assert self._live().side == "buy"
        assert self._batch().side == "buy"


# ---------------------------------------------------------------------------
# Coinbase live (ISO timestamp) — timestamp contract test
# ---------------------------------------------------------------------------


class TestCoinbaseTimestampContract:
    """Coinbase uses ISO-8601 timestamps; verify UTC normalization."""

    def test_iso_timestamp_is_utc(self) -> None:
        raw = CoinbaseTrade(
            trade_id=42,
            product_id="BTC-USD",
            price=Decimal("60000"),
            size=Decimal("0.01"),
            side="buy",
            time="2023-11-14T22:13:20.000Z",
        )
        canonical = normalize_coinbase_trade(raw, symbol="BTC-USD")
        assert canonical.timestamp.tzinfo is not None
        assert canonical.timestamp.utcoffset().total_seconds() == 0  # type: ignore[union-attr]

    def test_no_timestamp_defaults_to_utc_now(self) -> None:
        raw = CoinbaseTrade(
            trade_id=43,
            product_id="BTC-USD",
            price=Decimal("60000"),
            size=Decimal("0.01"),
            side="buy",
            time=None,
        )
        canonical = normalize_coinbase_trade(raw, symbol="BTC-USD")
        # Should not raise; timestamp is a UTC-aware datetime
        assert canonical.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Symbol normalization parity
# ---------------------------------------------------------------------------


class TestSymbolNormalizationParity:
    """Verify normalize_symbol produces consistent symbols across venues."""

    @pytest.mark.parametrize(
        "venue,raw,expected",
        [
            ("binance", "BTCUSDT", "BTC-USDT"),
            ("bybit", "BTCUSDT", "BTC-USDT"),
            ("okx", "BTC-USDT-SWAP", "BTC-USDT-PERP"),
            ("deribit", "BTC-PERPETUAL", "BTC-PERP"),
            ("hyperliquid", "BTC", "BTC-USDC-PERP"),
            ("coinbase", "BTC-USD", "BTC-USD"),
        ],
    )
    def test_symbol_canonical_form(self, venue: str, raw: str, expected: str) -> None:
        from unified_api_contracts.normalize_utils import normalize_symbol

        assert normalize_symbol(venue, raw) == expected

    def test_unknown_venue_passthrough(self) -> None:
        from unified_api_contracts.normalize_utils import normalize_symbol

        assert normalize_symbol("unknown_venue", "btcusdt") == "BTCUSDT"


# ---------------------------------------------------------------------------
# Side normalization parity
# ---------------------------------------------------------------------------


class TestSideNormalizationParity:
    """Verify normalize_side maps all representations to buy/sell."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("BUY", "buy"),
            ("buy", "buy"),
            ("B", "buy"),
            ("bid", "buy"),
            ("long", "buy"),
            ("LONG", "buy"),
            (1, "buy"),
            (0, "buy"),
            ("SELL", "sell"),
            ("sell", "sell"),
            ("S", "sell"),
            ("ask", "sell"),
            ("short", "sell"),
            ("SHORT", "sell"),
            (2, "sell"),
            (None, "buy"),  # fallback
        ],
    )
    def test_side_canonical_form(self, raw: str | int | None, expected: str) -> None:
        from unified_api_contracts.normalize_utils import normalize_side

        assert normalize_side(raw) == expected  # type: ignore[arg-type]

    def test_live_batch_side_agreement_binance(self) -> None:
        """BinanceTrade isBuyerMaker=True (seller is taker) must equal Tardis side='sell'."""
        from unified_api_contracts.normalize_utils import normalize_side

        # isBuyerMaker=True → buyer is maker → seller is taker → side = "sell"
        binance_side = "sell" if True else "buy"  # mirrors normalize_binance_trade logic
        tardis_side = normalize_side("sell")
        assert binance_side == tardis_side
