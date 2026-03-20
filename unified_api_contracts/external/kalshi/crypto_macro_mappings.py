"""Kalshi crypto and macro market ticker mappings.

Kalshi uses structured tickers for binary markets:
- BTC: KXBTC-{DATE}-T{STRIKE} (e.g. KXBTC-26MAR21-T95000)
- S&P: KXSPY-{DATE}-T{STRIKE} (e.g. KXSPY-26MAR21-T5800)
- Fed rate: KXFED-{DATE}-T{RATE} (e.g. KXFED-26MAR19-T525)
"""

from __future__ import annotations

import re

# Kalshi series prefixes for crypto/macro underlyings
KALSHI_CRYPTO_SERIES: dict[str, str] = {
    "BTC": "KXBTC",
    "ETH": "KXETH",
    "SOL": "KXSOL",
}

KALSHI_MACRO_SERIES: dict[str, str] = {
    "SPX": "KXSPY",
    "FED": "KXFED",
    "CPI": "KXCPI",
    "GDP": "KXGDP",
    "NASDAQ": "KXNDX",
}

_KALSHI_TICKER_RE = re.compile(r"^(?P<series>[A-Z]+)-(?P<date>\d{2}[A-Z]{3}\d{2})-T(?P<strike>\d+)$")


def build_kalshi_crypto_ticker(
    underlying: str,
    date_str: str,
    strike: int,
) -> str | None:
    """Build a Kalshi crypto ticker.

    Args:
        underlying: "BTC", "ETH", "SOL"
        date_str: Date in DDMMMYY format (e.g. "21MAR26")
        strike: Strike price as integer (e.g. 95000)

    Returns:
        Ticker (e.g. "KXBTC-21MAR26-T95000") or None if underlying not mapped.
    """
    series = KALSHI_CRYPTO_SERIES.get(underlying.upper())
    if series is None:
        return None
    return f"{series}-{date_str}-T{strike}"


def build_kalshi_macro_ticker(
    underlying: str,
    date_str: str,
    strike: int,
) -> str | None:
    """Build a Kalshi macro ticker.

    Args:
        underlying: "SPX", "FED", "CPI", "GDP", "NASDAQ"
        date_str: Date in DDMMMYY format
        strike: Strike level as integer (e.g. 5800 for S&P)

    Returns:
        Ticker (e.g. "KXSPY-21MAR26-T5800") or None if underlying not mapped.
    """
    series = KALSHI_MACRO_SERIES.get(underlying.upper())
    if series is None:
        return None
    return f"{series}-{date_str}-T{strike}"


def parse_kalshi_ticker(ticker: str) -> dict[str, str | int] | None:
    """Parse a Kalshi structured ticker into components.

    Returns dict with keys: series, underlying, date, strike
    or None if not a recognized ticker format.
    """
    match = _KALSHI_TICKER_RE.match(ticker)
    if not match:
        return None

    series = match.group("series")

    # Reverse-lookup underlying
    underlying: str | None = None
    for asset, prefix in {**KALSHI_CRYPTO_SERIES, **KALSHI_MACRO_SERIES}.items():
        if prefix == series:
            underlying = asset
            break

    if underlying is None:
        return None

    return {
        "series": series,
        "underlying": underlying,
        "date": match.group("date"),
        "strike": int(match.group("strike")),
    }
