"""Options chain normalizers: raw venue option quote -> CanonicalOptionsChainEntry."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ..canonical.domain import CanonicalOptionsChainEntry
from ..external.databento.normalize import (
    normalize_databento_cme_option_quote,
    normalize_databento_option_quote,
)
from ..external.deribit.schemas import (
    DeribitMarkPriceOption,
    DeribitOptionsGreeks,
)
from ..external.ibkr.normalize import normalize_ibkr_option_quote
from ..external.tardis.normalize import normalize_tardis_option_quote
from ..external.yahoo_finance.normalize import (
    normalize_yahoo_finance_option,
    normalize_yahoo_finance_options_chain,
    normalize_yahoo_option,
)

# Deribit option expiry settlement convention: 08:00 UTC on expiry day.
_DERIBIT_EXPIRY_HOUR_UTC = 8

_DERIBIT_MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def _parse_deribit_option_expiry(instrument_name: str) -> datetime:
    """Parse Deribit option instrument expiry from the symbol.

    Deribit option symbols use the format ``<asset>-<DDMMMYY>-<strike>-<type>``
    where ``<type>`` is ``C`` (call) or ``P`` (put) and ``<DDMMMYY>`` is
    e.g. ``28JUN24``. Settlement convention is 08:00 UTC on the expiry day.

    Args:
        instrument_name: Deribit option symbol (e.g. "BTC-28JUN24-70000-C").

    Returns:
        Timezone-aware datetime at 08:00 UTC on the expiry day.

    Raises:
        ValueError: If the symbol does not have a parseable expiry segment.
    """
    parts = instrument_name.split("-")
    if len(parts) < 4:
        raise ValueError(
            f"Cannot parse Deribit option expiry: instrument_name {instrument_name!r} "
            f"has {len(parts)} segments, expected 4+ (e.g. 'BTC-28JUN24-70000-C')"
        )
    expiry_str = parts[1]  # e.g. "28JUN24"
    if len(expiry_str) < 6:
        raise ValueError(
            f"Cannot parse Deribit option expiry: segment {expiry_str!r} too short (expected DDMMMYY like '28JUN24')"
        )
    day_str = expiry_str[:-5]  # leading digits (1 or 2)
    month_str = expiry_str[-5:-2]  # 3-letter month
    year_str = expiry_str[-2:]  # 2-digit year
    month = _DERIBIT_MONTH_MAP.get(month_str.upper())
    if month is None:
        raise ValueError(f"Unknown Deribit month code {month_str!r} in {instrument_name!r}")
    try:
        day = int(day_str)
        year = 2000 + int(year_str)  # Deribit options run 2020-2099 era
    except ValueError as e:
        raise ValueError(f"Cannot parse Deribit expiry day/year from {expiry_str!r}: {e}") from e
    return datetime(year, month, day, _DERIBIT_EXPIRY_HOUR_UTC, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Deribit — option-specific normalizers not yet in external/deribit/normalize.py
# ---------------------------------------------------------------------------


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
    # Prefer caller-supplied expiration_ms; fall back to parsing from instrument_name.
    if expiration_ms is not None:
        exp = datetime.fromtimestamp(expiration_ms / 1000.0, tz=UTC)
    else:
        exp = _parse_deribit_option_expiry(raw.instrument_name)
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
    expiration = _parse_deribit_option_expiry(instrument_name)
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=instrument_name,
        underlying=parts[0] if parts else instrument_name,
        strike=strike,
        option_type=opt_type,
        expiration=expiration,
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
