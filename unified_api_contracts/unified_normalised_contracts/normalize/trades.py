"""Trade normalizers: raw venue trade -> CanonicalTrade."""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.aster.schemas import AsterTrade
from ...unified_api_contracts_external.binance.market_schemas import BinanceTrade
from ...unified_api_contracts_external.bybit.schemas import BybitTrade
from ...unified_api_contracts_external.ccxt.schemas import CcxtTrade
from ...unified_api_contracts_external.coinbase.schemas import CoinbaseTrade
from ...unified_api_contracts_external.databento.schemas import (
    DATABENTO_PRICE_DIVISOR,
    DatabentoMbo,
    DatabentoTrade,
)
from ...unified_api_contracts_external.deribit.schemas import DeribitTrade
from ...unified_api_contracts_external.ibkr.schemas import IBKRExecution
from ...unified_api_contracts_external.kalshi.schemas import KalshiTrade, KalshiWebSocketTradeMsg
from ...unified_api_contracts_external.manifold.schemas import ManifoldTrade
from ...unified_api_contracts_external.okx.schemas import OKXTrade
from ...unified_api_contracts_external.polymarket.schemas import PolymarketTrade
from ...unified_api_contracts_external.regulatory.schemas import MifidIITradeReport
from ...unified_api_contracts_external.sports.canonical.betting import BetExecution
from ...unified_api_contracts_external.tardis.schemas import TardisTrade
from ...unified_api_contracts_external.upbit.schemas import UpbitTrade
from ...unified_api_contracts_external.versifi.schemas import VersiFiChildOrderTrade
from ..domain import CanonicalTrade

_logger = logging.getLogger(__name__)


def normalize_binance_trade(raw: BinanceTrade, venue: str = "binance", symbol: str = "") -> CanonicalTrade:
    """Convert BinanceTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC)
    side = "buy" if not raw.isBuyerMaker else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.id),
        timestamp=ts,
        price=raw.price,
        quantity=raw.qty,
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=str(raw.id),
    )


def normalize_databento_mbo_to_trade(
    raw: DatabentoMbo, venue: str = "databento", symbol: str = ""
) -> CanonicalTrade | None:
    """Convert DatabentoMbo to CanonicalTrade when action is T (trade)."""
    if raw.action != "T":
        return None
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    price = Decimal(raw.price) / Decimal(str(DATABENTO_PRICE_DIVISOR))
    side = "sell" if raw.side == "A" else "buy"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        trade_id=str(raw.order_id),
        timestamp=ts,
        price=price,
        quantity=Decimal(raw.size),
        side=side,
        buyer_maker=None,
        venue_trade_id=str(raw.order_id),
    )


def normalize_databento_trade(raw: DatabentoTrade, venue: str = "databento", symbol: str = "") -> CanonicalTrade:
    """Convert DatabentoTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    price = Decimal(raw.price) / Decimal("1e9")
    side = "sell" if raw.side == "A" else "buy"
    trade_id = str(raw.sequence) if raw.sequence is not None else f"{raw.ts_event}-{raw.instrument_id}"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        trade_id=trade_id,
        timestamp=ts,
        price=price,
        quantity=Decimal(raw.size),
        side=side,
        buyer_maker=None,
        venue_trade_id=trade_id,
    )


def normalize_tardis_trade(raw: TardisTrade, venue: str | None = None, symbol: str | None = None) -> CanonicalTrade:
    """Convert TardisTrade to CanonicalTrade."""
    v = venue or (raw.exchange or "tardis")
    s = symbol or (raw.symbol or "")
    ts_str = raw.timestamp or "0"
    try:
        ts_val = int(float(ts_str) / 1000) if "." in ts_str else int(ts_str) // 1000
        ts = datetime.fromtimestamp(ts_val, tz=UTC)
    except (ValueError, TypeError):
        ts = datetime.now(UTC)
    return CanonicalTrade(
        venue=v,
        symbol=s or "UNKNOWN",
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.size or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


def normalize_coinbase_trade(raw: CoinbaseTrade, venue: str = "coinbase", symbol: str = "") -> CanonicalTrade:
    """Convert CoinbaseTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.time:
        try:
            ts = datetime.fromisoformat(raw.time.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _logger.debug("Coinbase trade time %r is not a valid ISO datetime; using current UTC time", raw.time)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.trade_id),
        timestamp=ts,
        price=raw.price,
        quantity=raw.size,
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.trade_id),
    )


def normalize_ccxt_trade(raw: CcxtTrade, venue: str = "ccxt", symbol: str = "") -> CanonicalTrade:
    """Convert CcxtTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    elif raw.datetime:
        try:
            ts = datetime.fromisoformat(str(raw.datetime).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _logger.debug("CCXT trade datetime %r is not a valid ISO datetime; using current UTC time", raw.datetime)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.symbol or "") or "UNKNOWN",
        trade_id=str(raw.id) if raw.id is not None else "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=raw.takerOrMaker == "maker" if raw.takerOrMaker else None,
        venue_trade_id=str(raw.id) if raw.id else None,
    )


def normalize_okx_trade(raw: OKXTrade, venue: str = "okx", symbol: str = "") -> CanonicalTrade:
    """Convert OKXTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.ts:
        ts = datetime.fromtimestamp(int(raw.ts) / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.instId or "") or "UNKNOWN",
        trade_id=str(raw.tradeId) if raw.tradeId else "",
        timestamp=ts,
        price=Decimal(str(raw.px or 0)),
        quantity=Decimal(str(raw.sz or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.tradeId) if raw.tradeId else None,
    )


def normalize_bybit_trade(raw: BybitTrade, venue: str = "bybit", symbol: str = "") -> CanonicalTrade:
    """Convert BybitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.execTime is not None:
        ts = datetime.fromtimestamp(raw.execTime / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.symbol or "") or "UNKNOWN",
        trade_id=str(raw.execId) if raw.execId else "",
        timestamp=ts,
        price=Decimal(str(raw.execPrice or 0)),
        quantity=Decimal(str(raw.execQty or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=raw.isMaker,
        venue_trade_id=str(raw.execId) if raw.execId else None,
    )


def normalize_deribit_trade(raw: DeribitTrade, venue: str = "deribit", symbol: str = "") -> CanonicalTrade:
    """Convert DeribitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.instrument_name or "") or "UNKNOWN",
        trade_id=str(raw.trade_id) if raw.trade_id else "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side=(raw.direction or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.trade_id) if raw.trade_id else None,
    )


def normalize_aster_trade(raw: AsterTrade, venue: str = "aster", symbol: str = "") -> CanonicalTrade:
    """Convert AsterTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC) if raw.time else datetime.now(UTC)
    side = "sell" if raw.isBuyerMaker else "buy"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.id),
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.qty or 0)),
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=str(raw.id),
    )


def normalize_upbit_trade(raw: UpbitTrade, venue: str = "upbit", symbol: str = "") -> CanonicalTrade:
    """Convert UpbitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    elif raw.sequential_id is not None:
        pass  # no ts from sequential_id
    side = "buy" if (raw.ask_bid or "").upper() == "BID" else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.market or "") or "UNKNOWN",
        trade_id=str(raw.sequential_id) if raw.sequential_id is not None else "",
        timestamp=ts,
        price=Decimal(str(raw.trade_price or 0)),
        quantity=Decimal(str(raw.trade_volume or 0)),
        side=side,
        buyer_maker=None,
        venue_trade_id=str(raw.sequential_id) if raw.sequential_id is not None else None,
    )


def normalize_ibkr_trade(
    raw: IBKRExecution,
    venue: str = "ibkr",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert IBKRExecution to CanonicalTrade.

    IBKRExecution is an execution (fill) from execDetails; side is "BOT"/"SLD".
    Mapped as a public trade record. time is a string like "20240101 09:30:00 EST".
    """
    ts = datetime.now(UTC)
    if raw.time:
        with contextlib.suppress(ValueError, TypeError):
            # IBKR format: "20240101 09:30:00 EST" or "20240101  09:30:00"
            ts = datetime.strptime(raw.time[:16].strip(), "%Y%m%d %H:%M").replace(tzinfo=UTC)
    sym = symbol or raw.exchange or ""
    side = "buy" if (raw.side or "").upper() in ("BOT", "BUY") else "sell"
    price = Decimal(str(raw.price or 0))
    qty = Decimal(str(raw.shares or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym if sym else "UNKNOWN",
        trade_id=raw.execId or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.000001"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.execId,
    )


def normalize_kalshi_trade(
    raw: KalshiTrade,
    venue: str = "kalshi",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert KalshiTrade (REST) to CanonicalTrade.

    yes_price_dollars is the price of a Yes contract in dollars (string decimal).
    count_fp is the number of contracts (string float).
    taker_side: "yes"/"no" — mapped to "buy"/"sell".
    """
    sym = symbol or raw.ticker or "UNKNOWN"
    ts = datetime.now(UTC)
    if raw.created_time:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromisoformat(raw.created_time.replace("Z", "+00:00"))
    side = "buy" if (raw.taker_side or "").lower() == "yes" else "sell"
    price = Decimal(str(raw.yes_price_dollars or 0))
    qty = Decimal(str(raw.count_fp or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.01"),
        quantity=qty if qty > Decimal("0") else Decimal("1"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


def normalize_kalshi_ws_trade(
    raw: KalshiWebSocketTradeMsg,
    venue: str = "kalshi",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert KalshiWebSocketTradeMsg to CanonicalTrade.

    yes_price in cents (int). count in integer contracts.
    """
    sym = symbol or raw.market_ticker or "UNKNOWN"
    ts = datetime.fromtimestamp((raw.ts or 0) / 1000.0, tz=UTC) if raw.ts else datetime.now(UTC)
    side = "buy" if (raw.taker_side or "").lower() == "yes" else "sell"
    price = Decimal(str(raw.yes_price or 0)) / Decimal("100")
    qty = Decimal(str(raw.count or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.01"),
        quantity=qty if qty > Decimal("0") else Decimal("1"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


def normalize_manifold_trade(
    raw: ManifoldTrade,
    venue: str = "manifold",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert ManifoldTrade to CanonicalTrade.

    Manifold prediction market: price is probability (0-1), amount is mana wagered.
    """
    sym = symbol or raw.contract_id or "UNKNOWN"
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.id or "",
        timestamp=datetime.now(UTC),
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side="buy",  # Manifold doesn't have directional sides
        buyer_maker=None,
        venue_trade_id=raw.id,
    )


def normalize_polymarket_trade(
    raw: PolymarketTrade,
    venue: str = "polymarket",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert PolymarketTrade to CanonicalTrade.

    Polymarket CLOB: price (float), size (float), side (BUY/SELL), timestamp (ms).
    """
    sym = symbol or raw.market or raw.asset_id or "UNKNOWN"
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC) if raw.timestamp else datetime.now(UTC)
    side = "buy" if (raw.side or "").upper() == "BUY" else "sell"
    price = Decimal(str(raw.price or 0))
    qty = Decimal(str(raw.size or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.id or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.000001"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.id,
    )


def normalize_regulatory_trade_report(
    raw: MifidIITradeReport,
    venue: str = "regulatory",
) -> CanonicalTrade:
    """Convert MifidIITradeReport to CanonicalTrade.

    MiFID II trade report is a regulatory filing; maps to CanonicalTrade for record-keeping.
    instrument_key uses trading venue MIC.
    """
    sym = raw.instrument_isin or ""
    return CanonicalTrade(
        venue=venue or raw.trading_venue_mic,
        symbol=sym if sym else "UNKNOWN",
        trade_id=raw.exec_id,
        timestamp=raw.trading_datetime,
        price=raw.price,
        quantity=raw.quantity,
        side="buy",  # MiFID report doesn't specify buy/sell (depends on reporting entity)
        buyer_maker=None,
        venue_trade_id=raw.exec_id,
    )


def normalize_sports_trade(
    raw: BetExecution,
    venue: str = "sports",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert BetExecution (sports canonical) to CanonicalTrade.

    BetExecution represents a filled bet at a bookmaker.
    filled_odds as price, filled_stake as quantity.
    """
    sym = symbol or raw.order_id
    ts = datetime.now(UTC)
    price = raw.filled_odds if raw.filled_odds is not None else Decimal("0")
    qty = raw.filled_stake if raw.filled_stake is not None else Decimal("0")
    return CanonicalTrade(
        venue=venue or raw.bookmaker_ref or "sports",
        symbol=sym if sym else "UNKNOWN",
        trade_id=raw.execution_id,
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("1"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side="buy",  # sports bets are always "backing"
        buyer_maker=None,
        venue_trade_id=raw.execution_id,
        is_liquidation=None,
    )


def normalize_versifi_child_order_trade(
    raw: VersiFiChildOrderTrade,
    venue: str = "versifi",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert VersiFiChildOrderTrade to CanonicalTrade.

    VersiFi child order trades are individual fills on a child (venue) order.
    price/quantity are decimal strings.
    """
    sym = symbol or raw.symbol or "UNKNOWN"
    side = "buy" if (raw.side or "").lower() in ("buy", "b") else "sell"
    price = Decimal(str(raw.price or 0))
    qty = Decimal(str(raw.quantity or 0))
    trade_id = raw.exchange_trade_id or str(raw.child_order_id or "")
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=datetime.now(UTC),
        price=price if price > Decimal("0") else Decimal("0.000001"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.exchange_trade_id,
    )


def normalize_trade(
    raw: object,
    venue: str = "",
    symbol: str = "",
) -> CanonicalTrade:
    """Dispatch to venue-specific normalizer. Raises TypeError for unsupported raw types."""
    if isinstance(raw, BinanceTrade):
        return normalize_binance_trade(raw, venue=venue or "binance", symbol=symbol)
    if isinstance(raw, DatabentoTrade):
        return normalize_databento_trade(raw, venue=venue or "databento", symbol=symbol)
    if isinstance(raw, TardisTrade):
        return normalize_tardis_trade(raw, venue=venue or None, symbol=symbol or None)
    if isinstance(raw, AsterTrade):
        return normalize_aster_trade(raw, venue=venue or "aster", symbol=symbol)
    raise TypeError("Unsupported raw type for trade normalization")
