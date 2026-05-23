"""Yahoo Finance normalizers — all normalize_yahoo_* functions.

Extracted from normalize_utils/ modules (ohlcv, options, errors).
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.crosscutting.errors import (
    CanonicalError,
    ErrorAction,
)
from ...canonical.domain import CanonicalOhlcvBar, CanonicalOptionsChainEntry
from ...normalize_utils._helpers import d
from ...normalize_utils.errors._utils import from_http_status
from . import YahooOhlcv, YahooOptionContract
from .schemas import (
    YahooOhlcv24h,
    YahooOptionsChain,
)
from .schemas import (
    YahooOptionContract as YahooOptionContractSchema,
)

# ---------------------------------------------------------------------------
# Private helper (local _d for options — matches normalize_utils/options.py)
# ---------------------------------------------------------------------------


def _opt_d(value: float | int | str | Decimal | None) -> Decimal | None:
    """Decimal conversion for options fields — returns None for None input."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# ---------------------------------------------------------------------------
# OHLCV normalizers (from normalize_utils/ohlcv.py)
# ---------------------------------------------------------------------------


def normalize_yahoo_ohlcv(raw: YahooOhlcv, venue: str = "yahoo_finance") -> CanonicalOhlcvBar:
    """Convert YahooOhlcv to CanonicalOhlcvBar.

    timestamp_ms is Unix milliseconds (converted from pandas Timestamp by caller).
    """
    ts = datetime.fromtimestamp(raw.timestamp_ms / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=raw.symbol,
        open=d(raw.Open),
        high=d(raw.High),
        low=d(raw.Low),
        close=d(raw.Close),
        volume=d(raw.Volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_yahoo_finance_ohlcv24h(
    raw: YahooOhlcv24h, symbol: str = "", venue: str = "yahoo_finance"
) -> CanonicalOhlcvBar:
    """Convert YahooOhlcv24h (daily history bar) to CanonicalOhlcvBar.

    Date is a string like "2024-01-15"; treated as midnight UTC.
    """
    ts = datetime.now(UTC)
    if raw.Date:
        with contextlib.suppress(ValueError):
            ts = datetime.strptime(raw.Date, "%Y-%m-%d").replace(tzinfo=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=d(raw.Open),
        high=d(raw.High),
        low=d(raw.Low),
        close=d(raw.Close),
        volume=d(raw.Volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Options normalizers (from normalize_utils/options.py)
# ---------------------------------------------------------------------------


def normalize_yahoo_option(raw: YahooOptionContract, venue: str = "yahoo_finance") -> CanonicalOptionsChainEntry:
    """Convert YahooOptionContract to CanonicalOptionsChainEntry."""
    ts = (
        datetime.fromtimestamp(raw.lastTradeDate / 1000.0, tz=UTC)
        if raw.lastTradeDate is not None
        else datetime.now(tz=UTC)
    )
    exp = (
        datetime.fromtimestamp(raw.expiration / 1000.0, tz=UTC) if raw.expiration is not None else datetime.now(tz=UTC)
    )
    opt_type = (raw.option_type or "call").lower()
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=raw.contractSymbol,
        underlying=raw.underlying or raw.contractSymbol,
        strike=_opt_d(raw.strike) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_opt_d(raw.bid),
        ask_price=_opt_d(raw.ask),
        bid_size=None,
        ask_size=None,
        implied_volatility=raw.impliedVolatility,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        instrument_key=f"{venue}:OPTION:{raw.contractSymbol}",
    )


def normalize_yahoo_finance_option(
    raw: YahooOptionContractSchema,
    venue: str = "yahoo_finance",
) -> CanonicalOptionsChainEntry:
    """Convert YahooOptionContract (from schemas.py) to CanonicalOptionsChainEntry.

    This is the newer schema format with snake_case fields (from ticker.option_chain()).
    """
    ts = datetime.now(tz=UTC)
    exp: datetime = ts  # Default fallback
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
        strike=_opt_d(raw.strike) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_opt_d(raw.bid),
        ask_price=_opt_d(raw.ask),
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


# ---------------------------------------------------------------------------
# Error normalizer (from normalize_utils/errors/_normalize_b.py)
# ---------------------------------------------------------------------------


def normalize_yahoo_finance_error(
    error_code: str | int,
    message: str = "",
    venue: str = "yahoo_finance",
) -> CanonicalError:
    """Map a Yahoo Finance API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_yahoo_finance_error",
    "normalize_yahoo_finance_ohlcv24h",
    "normalize_yahoo_finance_option",
    "normalize_yahoo_finance_options_chain",
    "normalize_yahoo_ohlcv",
    "normalize_yahoo_option",
]
