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
