"""Options chain normalizers: raw venue option quote -> CanonicalOptionsChainEntry."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.databento.schemas import (
    DATABENTO_PRICE_DIVISOR,
    DatabentoCMEOptionQuote,
    DatabentoOptionQuote,
)
from ...unified_api_contracts_external.deribit.schemas import (
    DeribitMarkPriceOption,
    DeribitOptionsGreeks,
)
from ...unified_api_contracts_external.ibkr.schemas import (
    IBKRContractDetails,
    IBKROptionGreeks,
    IBKRTicker,
)
from ...unified_api_contracts_external.tardis import TardisOptionQuote
from ...unified_api_contracts_external.yahoo_finance import YahooOptionContract
from ...unified_api_contracts_external.yahoo_finance.schemas import (
    YahooOptionContract as YahooOptionContractSchema,
)
from ...unified_api_contracts_external.yahoo_finance.schemas import (
    YahooOptionsChain,
)
from ..domain import CanonicalOptionsChainEntry


def _db_price(px: int) -> Decimal:
    return Decimal(str(float(px) / float(DATABENTO_PRICE_DIVISOR)))


def _d(value: float | int | str | Decimal | None) -> Decimal | None:
    """Convert any numeric value to Decimal; return None for None."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def normalize_databento_option_quote(
    raw: DatabentoOptionQuote, venue: str = "databento", symbol: str = ""
) -> CanonicalOptionsChainEntry:
    """Convert DatabentoOptionQuote (OPRA) to CanonicalOptionsChainEntry."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    opt_type = "call" if (raw.option_type or "C").upper() == "C" else "put"
    exp = datetime.fromtimestamp(raw.expiration / 1e9, tz=UTC) if raw.expiration else None
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        underlying=raw.underlying,
        strike=_db_price(raw.strike_price),
        option_type=opt_type,
        expiration=exp,
        bid_price=_db_price(raw.bid_px_00),
        ask_price=_db_price(raw.ask_px_00),
        bid_size=_d(raw.bid_sz_00),
        ask_size=_d(raw.ask_sz_00),
        implied_volatility=float(_db_price(raw.implied_volatility)) if raw.implied_volatility else None,
        delta=float(_db_price(raw.delta)) if raw.delta else None,
        gamma=float(_db_price(raw.gamma)) if raw.gamma else None,
        theta=float(_db_price(raw.theta)) if raw.theta else None,
        vega=float(_db_price(raw.vega)) if raw.vega else None,
        instrument_key=f"{venue}:OPTION:{symbol or raw.instrument_id}",
    )


def normalize_databento_cme_option_quote(
    raw: DatabentoCMEOptionQuote, venue: str = "databento", symbol: str = ""
) -> CanonicalOptionsChainEntry:
    """Convert DatabentoCMEOptionQuote (CME) to CanonicalOptionsChainEntry."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    opt_type = "call" if (raw.option_type or "C").upper() == "C" else "put"
    exp = datetime.fromtimestamp(raw.expiration / 1e9, tz=UTC) if raw.expiration else None
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        underlying=raw.underlying,
        strike=_db_price(raw.strike_price),
        option_type=opt_type,
        expiration=exp,
        bid_price=_db_price(raw.bid_px_00),
        ask_price=_db_price(raw.ask_px_00),
        bid_size=_d(raw.bid_sz_00),
        ask_size=_d(raw.ask_sz_00),
        implied_volatility=float(_db_price(raw.implied_volatility)) if raw.implied_volatility else None,
        delta=float(_db_price(raw.delta)) if raw.delta else None,
        gamma=float(_db_price(raw.gamma)) if raw.gamma else None,
        theta=float(_db_price(raw.theta)) if raw.theta else None,
        vega=float(_db_price(raw.vega)) if raw.vega else None,
        instrument_key=f"{venue}:OPTION:{symbol or raw.instrument_id}",
    )


def normalize_deribit_option_ticker(
    raw: DeribitOptionsGreeks,
    venue: str = "deribit",
    underlying: str = "",
    expiration_ms: int | None = None,
    option_type: str = "call",
) -> CanonicalOptionsChainEntry:
    """Convert DeribitOptionsGreeks to CanonicalOptionsChainEntry.

    DeribitOptionsGreeks carries per-instrument greeks (delta, gamma, theta, vega, iv)
    and mark_price. Bid/ask prices are not available on this schema; use DeribitTickerFull
    for live bid/ask. Expiration, option_type and underlying must be supplied by the caller
    (parseable from instrument_name: e.g. BTC-29MAR24-50000-C).
    """
    ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC) if raw.timestamp is not None else datetime.now(tz=UTC)
    exp = datetime.fromtimestamp(expiration_ms / 1000.0, tz=UTC) if expiration_ms is not None else None
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=raw.instrument_name,
        underlying=underlying or raw.instrument_name.split("-")[0] if raw.instrument_name else "",
        strike=Decimal(str(raw.mark_price)) if raw.mark_price is not None else Decimal("0"),
        option_type=option_type,
        expiration=exp,
        bid_price=None,
        ask_price=None,
        bid_size=None,
        ask_size=None,
        implied_volatility=float(raw.iv) if raw.iv is not None else None,
        delta=float(raw.delta) if raw.delta is not None else None,
        gamma=float(raw.gamma) if raw.gamma is not None else None,
        theta=float(raw.theta) if raw.theta is not None else None,
        vega=float(raw.vega) if raw.vega is not None else None,
        instrument_key=f"{venue}:OPTION:{raw.instrument_name}",
    )


def normalize_tardis_option_quote(raw: TardisOptionQuote, venue: str = "tardis") -> CanonicalOptionsChainEntry:
    """Convert TardisOptionQuote to CanonicalOptionsChainEntry."""
    ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    exp = datetime.fromtimestamp(raw.expiration / 1000.0, tz=UTC) if raw.expiration is not None else None
    opt_type = (raw.option_type or "call").lower()
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=raw.symbol,
        underlying=(raw.underlying_price is not None and str(raw.underlying_price)) or raw.symbol.split("-")[0],
        strike=_d(raw.strike_price) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_d(raw.bid_price),
        ask_price=_d(raw.ask_price),
        bid_size=_d(raw.bid_amount),
        ask_size=_d(raw.ask_amount),
        implied_volatility=raw.mark_iv,
        delta=raw.delta,
        gamma=raw.gamma,
        theta=raw.theta,
        vega=raw.vega,
        instrument_key=f"{venue}:OPTION:{raw.symbol}",
    )


def normalize_yahoo_option(raw: YahooOptionContract, venue: str = "yahoo_finance") -> CanonicalOptionsChainEntry:
    """Convert YahooOptionContract to CanonicalOptionsChainEntry."""
    ts = (
        datetime.fromtimestamp(raw.lastTradeDate / 1000.0, tz=UTC)
        if raw.lastTradeDate is not None
        else datetime.now(tz=UTC)
    )
    exp = datetime.fromtimestamp(raw.expiration / 1000.0, tz=UTC) if raw.expiration is not None else None
    opt_type = (raw.option_type or "call").lower()
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=raw.contractSymbol,
        underlying=raw.underlying or raw.contractSymbol,
        strike=_d(raw.strike) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_d(raw.bid),
        ask_price=_d(raw.ask),
        bid_size=None,
        ask_size=None,
        implied_volatility=raw.impliedVolatility,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        instrument_key=f"{venue}:OPTION:{raw.contractSymbol}",
    )


def normalize_ibkr_option_quote(
    raw: IBKRContractDetails,
    ticker: IBKRTicker | None = None,
    greeks: IBKROptionGreeks | None = None,
    venue: str = "ibkr",
) -> CanonicalOptionsChainEntry:
    """Convert IBKRContractDetails (+ optional live ticker + greeks) to CanonicalOptionsChainEntry.

    IBKRContractDetails carries the static option contract definition (strike, right, expiry).
    IBKRTicker carries live bid/ask. IBKROptionGreeks carries computed greeks.
    """
    ts = datetime.now(tz=UTC)
    opt_type = "put" if (raw.right or "C").upper() == "P" else "call"
    # IBKR expiry format: YYYYMMDD or YYYYMM
    exp: datetime | None = None
    if raw.lastTradeDateOrContractMonth:
        raw_exp = raw.lastTradeDateOrContractMonth.strip()
        try:
            if len(raw_exp) == 8:
                exp = datetime.strptime(raw_exp, "%Y%m%d").replace(tzinfo=UTC)
            elif len(raw_exp) == 6:
                exp = datetime.strptime(raw_exp, "%Y%m").replace(tzinfo=UTC)
        except ValueError:
            exp = None

    bid = ticker.bid if ticker is not None else None
    ask = ticker.ask if ticker is not None else None
    bid_sz = ticker.bidSize if ticker is not None else None
    ask_sz = ticker.askSize if ticker is not None else None
    iv = greeks.impliedVol if greeks is not None else None
    delta = greeks.delta if greeks is not None else None
    gamma = greeks.gamma if greeks is not None else None
    theta = greeks.theta if greeks is not None else None
    vega = greeks.vega if greeks is not None else None

    symbol = raw.localSymbol or raw.symbol or str(raw.conid or "")
    underlying = raw.symbol or ""

    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        underlying=underlying,
        strike=_d(raw.strike) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_d(bid),
        ask_price=_d(ask),
        bid_size=_d(bid_sz),
        ask_size=_d(ask_sz),
        implied_volatility=iv,
        delta=delta,
        gamma=gamma,
        theta=theta,
        vega=vega,
        instrument_key=f"{venue}:OPTION:{symbol}",
    )


def normalize_deribit_mark_price_option(
    raw: DeribitMarkPriceOption,
    venue: str = "deribit",
) -> CanonicalOptionsChainEntry:
    """Convert DeribitMarkPriceOption (markprice.options WS channel) to CanonicalOptionsChainEntry.

    Mark price option publishes mark_price and IV; greeks not available in this channel.
    instrument_name encodes type: ends with "-C" (call) or "-P" (put).
    """
    ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    instrument_name = raw.instrument_name
    opt_type = "put" if instrument_name.endswith("-P") else "call"
    # Extract strike from instrument_name: e.g. "BTC-28JUN24-70000-C" → 70000
    parts = instrument_name.split("-")
    strike: Decimal = Decimal("0")
    if len(parts) >= 3:
        with contextlib.suppress(ValueError, IndexError):
            strike = Decimal(parts[-2])
    iv = float(raw.iv) if raw.iv is not None else None
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=instrument_name,
        underlying=parts[0] if parts else instrument_name,
        strike=strike,
        option_type=opt_type,
        expiration=None,
        bid_price=None,
        ask_price=None,
        bid_size=None,
        ask_size=None,
        implied_volatility=iv,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        instrument_key=f"{venue}:OPTION:{instrument_name}",
    )


def normalize_yahoo_finance_option(
    raw: YahooOptionContractSchema,
    venue: str = "yahoo_finance",
) -> CanonicalOptionsChainEntry:
    """Convert YahooOptionContract (from schemas.py) to CanonicalOptionsChainEntry.

    This is the newer schema format with snake_case fields (from ticker.option_chain()).
    """
    ts = datetime.now(tz=UTC)
    exp: datetime | None = None
    if raw.expiration:
        with contextlib.suppress(ValueError, AttributeError):
            exp = datetime.fromisoformat(raw.expiration.replace("Z", "+00:00"))
    sym = raw.contract_symbol or raw.ticker or ""
    opt_type = (raw.option_type or "call").lower()
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=sym,
        underlying=raw.ticker or sym,
        strike=_d(raw.strike) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_d(raw.bid),
        ask_price=_d(raw.ask),
        bid_size=None,
        ask_size=None,
        implied_volatility=raw.implied_volatility,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        instrument_key=f"{venue}:OPTION:{sym}",
    )


def normalize_yahoo_finance_options_chain(
    raw: YahooOptionsChain,
    venue: str = "yahoo_finance",
) -> list[CanonicalOptionsChainEntry]:
    """Convert YahooOptionsChain to a list of CanonicalOptionsChainEntry.

    Iterates both calls and puts lists, yielding one entry per contract.
    """
    results: list[CanonicalOptionsChainEntry] = []
    for contract in raw.calls or []:
        results.append(normalize_yahoo_finance_option(contract, venue=venue))
    for contract in raw.puts or []:
        results.append(normalize_yahoo_finance_option(contract, venue=venue))
    return results


__all__ = [
    "normalize_databento_cme_option_quote",
    "normalize_databento_option_quote",
    "normalize_deribit_mark_price_option",
    "normalize_deribit_option_ticker",
    "normalize_ibkr_option_quote",
    "normalize_tardis_option_quote",
    "normalize_yahoo_finance_option",
    "normalize_yahoo_finance_options_chain",
    "normalize_yahoo_option",
]
