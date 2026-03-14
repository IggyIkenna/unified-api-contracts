"""Liquidation normalizers: raw venue liquidation event -> CanonicalLiquidation.

Covers all major CeFi venues:
  - Binance  (!forceOrder@arr WebSocket stream — BinanceLiquidationOrder)
  - Bybit    (allLiquidation WS stream — BybitLiquidationOrder)
  - OKX      (liquidation-orders WS channel — OKXLiquidationOrder)
  - Deribit  (user fills WS channel, type=liquidation — DeribitLiquidationOrder)
  - Hyperliquid (clearinghouse liquidation event — HyperliquidLiquidation)
  - CoinGlass (liquidation heatmap aggregator — CoinGlassLiquidation stub)

Field mapping conventions:
  - side: "buy" (liquidated a short — exchange buys back) or "sell" (liquidated a long)
  - price: execution/fill price of the liquidation order (Decimal, > 0 when known)
  - size: contracts/coins liquidated (Decimal, > 0 when known)
  - liquidated_account_value: total account value at time of liquidation (USD)
  - liquidated_ntl_pos: total notional position liquidated (USD)
  - liquidated_user: wallet address / userId — marked PII in CanonicalLiquidation
  - is_market_feed: True when from a public WebSocket feed; False when own-account event
    NOTE: is_market_feed is not a field on CanonicalLiquidation; it informs the caller
    which normalizer to use (public vs. private feed).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...external.aster.schemas import AsterLiquidationOrder
from ...external.binance.ws_schemas import BinanceLiquidationOrder
from ...external.bybit.schemas import BybitLiquidationOrder
from ...external.ccxt.schemas import CcxtLiquidation
from ...external.coinglass.schemas import LiquidationHeatmapResponse
from ...external.deribit.schemas import DeribitLiquidationOrder
from ...external.hyperliquid.schemas import HyperliquidLiquidation
from ...external.okx.schemas import OKXLiquidationOrder
from ...external.tardis.schemas import TardisLiquidations
from ..domain import CanonicalLiquidation

# ---------------------------------------------------------------------------
# Binance — !forceOrder@arr / {symbol}@forceOrder WebSocket
# ---------------------------------------------------------------------------
# Raw message structure:
#   {"e":"forceOrder","E":<event_time_ms>,"o":{
#     "s": symbol, "S": side (BUY|SELL), "o": orderType,
#     "q": origQty, "p": price, "ap": avgPrice,
#     "X": orderStatus, "l": lastFilledQty, "z": cumFilledQty, "T": tradeTime_ms
#   }}
# Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams
# ---------------------------------------------------------------------------


def normalize_binance_liquidation(
    raw: BinanceLiquidationOrder,
    venue: str = "binance",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert BinanceLiquidationOrder (forceOrder WS event) to CanonicalLiquidation.

    The `o` dict contains the order payload. Side convention: "BUY" means the exchange
    is buying back a short position (short liquidated); "SELL" means liquidating a long.
    Mapped to canonical "buy" / "sell" respectively.

    Args:
        raw: BinanceLiquidationOrder from !forceOrder@arr or {symbol}@forceOrder stream.
        venue: Venue tag, defaults to "binance".
        symbol: Instrument symbol; if empty, read from raw.o["s"].

    Returns:
        CanonicalLiquidation with price=avgPrice (ap), size=cumFilledQty (z).
    """
    order: dict[str, object] = raw.o

    raw_symbol: str = symbol or str(order.get("s") or "UNKNOWN")
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"

    raw_side: str = str(order.get("S") or "BUY").upper()
    side: str = "buy" if raw_side == "BUY" else "sell"

    # Prefer avgPrice (ap) over order price (p); fall back to 0 if absent
    ap_raw = order.get("ap") or order.get("p") or "0"
    price = Decimal(str(ap_raw))

    # Use cumFilledQty (z) as authoritative filled size
    z_raw = order.get("z") or order.get("q") or "0"
    size = Decimal(str(z_raw))

    trade_time_ms = order.get("T") or raw.E
    ts = datetime.fromtimestamp(int(str(trade_time_ms)) / 1000.0, tz=UTC)

    order_id_raw = order.get("i")  # order id if present
    order_id: str | None = str(order_id_raw) if order_id_raw is not None else None

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=order_id,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Bybit — allLiquidation WebSocket stream
# ---------------------------------------------------------------------------
# Raw message (WS topic: allLiquidation):
#   {"s": symbol, "S": side (Buy|Sell), "v": size, "p": price, "T": timestamp_ms}
# Short field names are documented in Bybit API v5 reference.
# Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/liquidation
# ---------------------------------------------------------------------------


def normalize_bybit_liquidation(
    raw: BybitLiquidationOrder,
    venue: str = "bybit",
) -> CanonicalLiquidation:
    """Convert BybitLiquidationOrder (allLiquidation WS) to CanonicalLiquidation.

    BybitLiquidationOrder fields:
      s = symbol, S = side (Buy|Sell), v = size, p = price, T = timestamp_ms

    Args:
        raw: BybitLiquidationOrder from allLiquidation stream.
        venue: Venue tag, defaults to "bybit".

    Returns:
        CanonicalLiquidation with price and size from the liquidation fill.
    """
    raw_symbol: str = str(raw.s or "UNKNOWN")
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"

    raw_side: str = str(raw.S or "Buy")
    side: str = "buy" if raw_side.lower() == "buy" else "sell"

    price = Decimal(str(raw.p or "0"))
    size = Decimal(str(raw.v or "0"))

    ts_ms = raw.T or 0
    ts = datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=UTC)

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# OKX — liquidation-orders WebSocket channel
# ---------------------------------------------------------------------------
# Subscription: {"channel": "liquidation-orders", "instType": "SWAP"}
# Raw data item fields:
#   instType, instId, liqPx (liquidation price), sz (size), side (buy|sell), ts (ms)
# Note: OKX calls this the "bankruptcy price" in REST docs; WS field is liqPx.
# Docs: https://www.okx.com/docs-v5/en/#public-websocket-liquidation-orders
# ---------------------------------------------------------------------------


def normalize_okx_liquidation(
    raw: OKXLiquidationOrder,
    venue: str = "okx",
) -> CanonicalLiquidation:
    """Convert OKXLiquidationOrder (liquidation-orders WS) to CanonicalLiquidation.

    OKXLiquidationOrder fields:
      instType (SWAP|FUTURES|MARGIN|OPTION), instId, liqPx (bankruptcy/liq price),
      sz (liquidation size in contracts), side (buy|sell), ts (timestamp ms).

    Args:
        raw: OKXLiquidationOrder from liquidation-orders channel.
        venue: Venue tag, defaults to "okx".

    Returns:
        CanonicalLiquidation with price=liqPx (bankruptcy price) and size=sz.
    """
    raw_symbol: str = str(raw.instId or "UNKNOWN")
    inst_type_map: dict[str, str] = {
        "SWAP": "PERPETUAL",
        "FUTURES": "FUTURE",
        "MARGIN": "SPOT_PAIR",
        "OPTION": "OPTION",
    }
    inst_type: str = inst_type_map.get(str(raw.instType or "SWAP"), "PERPETUAL")
    instrument_key = f"{venue}:{inst_type}:{raw_symbol}"

    side: str = str(raw.side or "buy").lower()

    price = Decimal(str(raw.liqPx or "0"))
    size = Decimal(str(raw.sz or "0"))

    ts_ms_raw = raw.ts or "0"
    ts = datetime.fromtimestamp(int(ts_ms_raw) / 1000.0, tz=UTC)

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Deribit — user fills WebSocket, liquidation trades
# ---------------------------------------------------------------------------
# Deribit sends liquidation fills via the user.trades.{kind}.{currency} WS channel.
# Fills where `liquidation` flag is set are DeribitLiquidationOrder events.
# DeribitLiquidationOrder fields (from deribit/schemas.py):
#   instrument_name, price, amount, side (buy|sell), timestamp (ms)
# Docs: https://docs.deribit.com/v2/#user-trades-kind-currency-interval
# ---------------------------------------------------------------------------


def normalize_deribit_liquidation(
    raw: DeribitLiquidationOrder,
    venue: str = "deribit",
) -> CanonicalLiquidation:
    """Convert DeribitLiquidationOrder (user fills WS) to CanonicalLiquidation.

    DeribitLiquidationOrder fields:
      instrument_name, price (float), amount (float), side (buy|sell),
      timestamp (int ms).

    Args:
        raw: DeribitLiquidationOrder from user fills channel.
        venue: Venue tag, defaults to "deribit".

    Returns:
        CanonicalLiquidation derived from the liquidation fill event.
    """
    raw_symbol: str = str(raw.instrument_name or "UNKNOWN")
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"

    side: str = str(raw.side or "buy").lower()
    price = Decimal(str(raw.price or 0))
    size = Decimal(str(raw.amount or 0))

    ts_ms = raw.timestamp or 0
    ts = datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=UTC)

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Hyperliquid — clearinghouse liquidation event
# ---------------------------------------------------------------------------
# Hyperliquid WebSocket pushes liquidation events via the "userEvents" subscription
# for the affected user or via public fills.
# HyperliquidLiquidation fields (from hyperliquid/schemas.py):
#   lid (int): liquidation id
#   liquidator (str): address of liquidator (NOT PII — counterparty)
#   liquidated_user (str): address of liquidated account (PII)
#   liquidated_ntl_pos (str): notional position liquidated (USD)
#   liquidated_account_value (str): account equity at liquidation (USD)
#   markPx (float): mark price at liquidation
#   method (str): "market" | "backstop"
# Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions
# Note: Hyperliquid liquidations do not carry a per-fill size/side directly in this
# schema — size is inferred from liquidated_ntl_pos / markPx when available.
# ---------------------------------------------------------------------------


def normalize_hyperliquid_liquidation(
    raw: HyperliquidLiquidation,
    venue: str = "hyperliquid",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert HyperliquidLiquidation (clearinghouse event) to CanonicalLiquidation.

    HyperliquidLiquidation fields:
      lid, liquidator, liquidated_user (PII), liquidated_ntl_pos (USD str),
      liquidated_account_value (USD str), markPx (float), method.

    Size is approximated as |liquidated_ntl_pos| / markPx when markPx > 0.
    Side defaults to "sell" (forced closure of a long) unless no information
    is available to determine direction; callers may override via symbol context.

    Args:
        raw: HyperliquidLiquidation event from userEvents WS subscription.
        venue: Venue tag, defaults to "hyperliquid".
        symbol: Optional instrument symbol (coin name, e.g. "BTC").

    Returns:
        CanonicalLiquidation with PII user field, ntl_pos, and account_value populated.
    """
    raw_symbol: str = symbol or "UNKNOWN"
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"

    mark_px_raw = raw.markPx or 0.0
    mark_px = Decimal(str(mark_px_raw))

    ntl_pos_str = raw.liquidated_ntl_pos or "0"
    ntl_pos = Decimal(str(ntl_pos_str))

    account_value_str = raw.liquidated_account_value or "0"
    account_value = Decimal(str(account_value_str))

    # Hyperliquid marks positions with signed ntl: negative = short, positive = long
    # A liquidation of a long position results in a "sell" from the clearing engine
    side: str = "sell" if ntl_pos >= Decimal("0") else "buy"

    # Approximate size from ntl / mark price; 0 if mark price unknown
    size: Decimal = abs(ntl_pos) / mark_px if mark_px > Decimal("0") and ntl_pos != Decimal("0") else Decimal("0")

    price = mark_px  # best available price at liquidation event

    # Timestamp: Hyperliquid liquidation schema has no timestamp field;
    # use current UTC time as the ingest time.
    ts = datetime.now(UTC)

    # Normalise liquidated_user: prefer the snake_case field, fall back to camelCase
    liq_user: str | None = raw.liquidated_user or raw.liquidatedUser or None

    order_id: str | None = str(raw.lid) if raw.lid is not None else None

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=order_id,
        liquidated_account_value=account_value if account_value != Decimal("0") else None,
        liquidated_ntl_pos=ntl_pos if ntl_pos != Decimal("0") else None,
        liquidated_user=liq_user,
    )


# ---------------------------------------------------------------------------
# CoinGlass — liquidation heatmap aggregator
# ---------------------------------------------------------------------------
# CoinGlass is NOT a trading venue; it aggregates liquidation level estimates
# across exchanges. The LiquidationHeatmapResponse contains estimated liq volumes
# at each price level for a given symbol/exchange combination.
#
# Mapping convention for a single LiquidationLevel:
#   - side: "sell" for long liquidations (long_liq_usd > short_liq_usd), else "buy"
#   - price: the heatmap price level
#   - size: max(long_liq_usd, short_liq_usd) / price  (approx contracts)
#   - liquidated_account_value: long_liq_usd + short_liq_usd at that level
#
# For heatmap data, callers typically iterate levels and call this per-level.
# Docs: https://docs.coinglass.com/reference/liquidation-heatmap
# ---------------------------------------------------------------------------


def normalize_coinglass_liquidation(
    raw: LiquidationHeatmapResponse,
    venue: str,
    level_index: int = 0,
) -> CanonicalLiquidation:
    """Convert a single CoinGlass heatmap level to CanonicalLiquidation.

    CoinGlass is a data aggregator, not a trading venue. Each LiquidationLevel
    represents estimated liquidation USD volume at a price point across an exchange.
    This function maps one level (by `level_index`) to a canonical event.

    For batch processing of all levels, callers should iterate:
        for i, _ in enumerate(response.levels):
            canonical = normalize_coinglass_liquidation(response, venue="binance", level_index=i)

    Args:
        raw: LiquidationHeatmapResponse from CoinGlass API.
        venue: The underlying exchange this heatmap is for (e.g. "binance").
        level_index: Index into raw.levels to normalize; defaults to 0.

    Returns:
        CanonicalLiquidation representing the dominant liquidation direction at this level.
    """
    instrument_key = f"{venue}:PERPETUAL:{raw.symbol}"

    ts = datetime.fromtimestamp(raw.timestamp_ms / 1000.0, tz=UTC)

    levels = raw.levels
    if not levels or level_index >= len(levels):
        # Return zero-sized sentinel if level is missing
        return CanonicalLiquidation(
            instrument_key=instrument_key,
            venue=venue,
            timestamp=ts,
            side="sell",
            price=Decimal(str(raw.current_price)),
            size=Decimal("0"),
        )

    level = levels[level_index]
    level_price = Decimal(str(level.price))
    long_liq = Decimal(str(level.long_liq_usd))
    short_liq = Decimal(str(level.short_liq_usd))
    total_liq = long_liq + short_liq

    # Dominant side: long liq -> sell side (longs are force-sold); short liq -> buy
    side: str = "sell" if long_liq >= short_liq else "buy"
    dominant_liq = max(long_liq, short_liq)

    # Approximate contracts as dominant_usd / price (avoid division by zero)
    size: Decimal = dominant_liq / level_price if level_price > Decimal("0") else Decimal("0")

    account_value: Decimal | None = total_liq if total_liq > Decimal("0") else None

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=level_price,
        size=size,
        order_id=None,
        liquidated_account_value=account_value,
        liquidated_ntl_pos=dominant_liq if dominant_liq > Decimal("0") else None,
        liquidated_user=None,
    )


def normalize_aster_liquidation(
    raw: AsterLiquidationOrder,
    venue: str = "aster",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert AsterLiquidationOrder (@forceOrder WS event) to CanonicalLiquidation.

    Aster is Binance Futures-compatible; the `o` dict contains the order object.
    Side: "BUY" = short liquidated (exchange buys back), "SELL" = long liquidated.
    """
    o: dict[str, object] = raw.o or {}
    sym = symbol or str(o.get("s") or "")
    ik = f"{venue.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.E or 0) / 1000.0, tz=UTC)
    side_raw = str(o.get("S") or "").upper()
    side = "buy" if side_raw == "BUY" else "sell"
    price = Decimal(str(o.get("ap") or o.get("p") or "0"))
    size = Decimal(str(o.get("q") or "0"))
    return CanonicalLiquidation(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price if price > Decimal("0") else Decimal("0"),
        size=size if size > Decimal("0") else Decimal("0"),
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


def normalize_ccxt_liquidation(
    raw: CcxtLiquidation,
    venue: str = "ccxt",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert CcxtLiquidation to CanonicalLiquidation.

    CCXT unified liquidation has symbol, price, amount, side, timestamp (ms).
    side: "long" (long liquidated → sell), "short" (short liquidated → buy).
    """
    sym = symbol or raw.symbol or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC)
    side_raw = (raw.side or "").lower()
    side = "sell" if side_raw == "long" else "buy"
    price = Decimal(str(raw.price or 0))
    size = Decimal(str(raw.amount or 0))
    return CanonicalLiquidation(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price if price > Decimal("0") else Decimal("0"),
        size=size if size > Decimal("0") else Decimal("0"),
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


def normalize_tardis_liquidation(
    raw: TardisLiquidations,
    venue: str = "",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert TardisLiquidations to CanonicalLiquidation.

    Tardis timestamp is microseconds. side: "buy" = short liquidated, "sell" = long liquidated.
    Amount/price not directly in schema; set to 0 as Tardis provides exchange-specific info field.
    """
    v = venue or raw.exchange or "tardis"
    sym = symbol or raw.symbol or ""
    ik = f"{v.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1_000_000.0, tz=UTC)
    side = raw.side if raw.side in ("buy", "sell") else "sell"
    return CanonicalLiquidation(
        instrument_key=ik,
        venue=v,
        timestamp=ts,
        side=side,
        price=Decimal("0"),
        size=Decimal("0"),
        order_id=raw.id,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


__all__ = [
    "normalize_aster_liquidation",
    "normalize_binance_liquidation",
    "normalize_bybit_liquidation",
    "normalize_ccxt_liquidation",
    "normalize_coinglass_liquidation",
    "normalize_deribit_liquidation",
    "normalize_hyperliquid_liquidation",
    "normalize_okx_liquidation",
    "normalize_tardis_liquidation",
]
