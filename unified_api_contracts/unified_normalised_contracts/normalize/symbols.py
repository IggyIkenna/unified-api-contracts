"""Symbol normalization — convert raw venue symbols to canonical format.

Canonical format: BASE-QUOTE (e.g. BTC-USDT, ETH-USD).
Perpetuals: BASE-USDT-PERP or BASE-PERP.
Futures: BASE-USDT-YYMMDD.

Each venue has its own raw format; this module converts to a consistent
cross-venue representation so batch and live paths produce identical symbols.
"""

from __future__ import annotations

import re
from collections.abc import Callable

# ---------------------------------------------------------------------------
# Binance
# ---------------------------------------------------------------------------

# Common quote assets for Binance symbol splitting (order matters — longer first)
_BINANCE_QUOTES = (
    "USDT",
    "BUSD",
    "USDC",
    "TUSD",
    "FDUSD",
    "DAI",
    "BTC",
    "ETH",
    "BNB",
    "EUR",
    "GBP",
    "AUD",
    "TRY",
)


def _normalize_binance(raw: str) -> str:
    """BTCUSDT -> BTC-USDT, BTCUSDT_PERP -> BTC-USDT-PERP."""
    upper = raw.upper()
    # Perpetual suffix
    if upper.endswith("_PERP"):
        base_part = upper[:-5]
        for q in _BINANCE_QUOTES:
            if base_part.endswith(q):
                return f"{base_part[: -len(q)]}-{q}-PERP"
        return f"{base_part}-PERP"
    for q in _BINANCE_QUOTES:
        if upper.endswith(q):
            base = upper[: -len(q)]
            if base:
                return f"{base}-{q}"
    return upper


# ---------------------------------------------------------------------------
# Bybit
# ---------------------------------------------------------------------------


def _normalize_bybit(raw: str) -> str:
    """BTCUSDT -> BTC-USDT (spot/linear), BTCUSD -> BTC-USD (inverse)."""
    return _normalize_binance(raw)  # same format


# ---------------------------------------------------------------------------
# Coinbase
# ---------------------------------------------------------------------------


def _normalize_coinbase(raw: str) -> str:
    """BTC-USD -> BTC-USD (already canonical), BTC-USDT -> BTC-USDT."""
    return raw.upper()


# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------


def _normalize_okx(raw: str) -> str:
    """BTC-USDT -> BTC-USDT, BTC-USDT-SWAP -> BTC-USDT-PERP, BTC-USD-231229 -> BTC-USD-231229."""
    upper = raw.upper()
    if upper.endswith("-SWAP"):
        return upper[:-5] + "-PERP"
    return upper


# ---------------------------------------------------------------------------
# Deribit
# ---------------------------------------------------------------------------

_DERIBIT_PERP_PAT = re.compile(r"^([A-Z0-9]+)-PERPETUAL$")
_DERIBIT_FUT_PAT = re.compile(r"^([A-Z0-9]+)-(\d{1,2}[A-Z]{3}\d{2})$")


def _normalize_deribit(raw: str) -> str:
    """BTC-PERPETUAL -> BTC-PERP, BTC-31DEC24 -> BTC-31DEC24, BTC-31DEC24-50000-C -> unchanged."""
    upper = raw.upper()
    m = _DERIBIT_PERP_PAT.match(upper)
    if m:
        return f"{m.group(1)}-PERP"
    return upper


# ---------------------------------------------------------------------------
# Hyperliquid
# ---------------------------------------------------------------------------


def _normalize_hyperliquid(raw: str) -> str:
    """BTC -> BTC-USDC-PERP (all Hyperliquid markets are USDC-settled perps)."""
    upper = raw.upper()
    if "-" not in upper:
        return f"{upper}-USDC-PERP"
    return upper


# ---------------------------------------------------------------------------
# Kraken
# ---------------------------------------------------------------------------

_KRAKEN_LEGACY = {
    # Longer/X-prefixed forms must come before shorter forms to avoid partial matches
    "XXBT": "BTC",
    "XXRP": "XRP",
    "XXLM": "XLM",
    "XETH": "ETH",
    "XLTC": "LTC",
    "XDG": "DOGE",
    "XBT": "BTC",
    "ZUSD": "USD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
}


def _normalize_kraken(raw: str) -> str:
    """XXBTZUSD -> BTC-USD, XBTUSD -> BTC-USD."""
    upper = raw.upper()
    # Futures: PI_XBTUSD -> BTC-USD-PERP
    if upper.startswith("PI_"):
        inner = upper[3:]
        for old, new in _KRAKEN_LEGACY.items():
            inner = inner.replace(old, new)
        if len(inner) == 6:
            return f"{inner[:3]}-{inner[3:]}-PERP"
    # Spot pairs (6 or 8 chars with legacy prefixes)
    normalized = upper
    for old, new in _KRAKEN_LEGACY.items():
        normalized = normalized.replace(old, new)
    if len(normalized) == 6:
        return f"{normalized[:3]}-{normalized[3:]}"
    # Try splitting on known quotes
    return _normalize_binance(normalized)


# ---------------------------------------------------------------------------
# Gate.io
# ---------------------------------------------------------------------------


def _normalize_gateio(raw: str) -> str:
    """BTC_USDT -> BTC-USDT, BTC_USDT_20240329 -> BTC-USDT-20240329."""
    return raw.upper().replace("_", "-")


# ---------------------------------------------------------------------------
# KuCoin
# ---------------------------------------------------------------------------


def _normalize_kucoin(raw: str) -> str:
    """BTC-USDT -> BTC-USDT (already dash-separated)."""
    return raw.upper()


# ---------------------------------------------------------------------------
# Bitfinex
# ---------------------------------------------------------------------------


def _normalize_bitfinex(raw: str) -> str:
    """tBTCUSD -> BTC-USD, tBTCUST -> BTC-USDT."""
    upper = raw.upper()
    if upper.startswith("T"):
        inner = upper[1:]
        if ":" in inner:
            base, quote = inner.split(":", 1)
            quote = quote.replace("UST", "USDT")
            return f"{base}-{quote}"
        if len(inner) == 6:
            base, quote = inner[:3], inner[3:]
            quote = quote.replace("UST", "USDT")
            return f"{base}-{quote}"
    return upper


# ---------------------------------------------------------------------------
# dYdX
# ---------------------------------------------------------------------------


def _normalize_dydx(raw: str) -> str:
    """BTC-USD -> BTC-USD-PERP (all dYdX v4 markets are perps)."""
    upper = raw.upper()
    if not upper.endswith("-PERP"):
        return f"{upper}-PERP"
    return upper


# ---------------------------------------------------------------------------
# Tardis / Databento passthrough
# ---------------------------------------------------------------------------


def _normalize_tardis(raw: str) -> str:
    """Tardis uses venue-native symbols; return uppercase as-is."""
    return raw.upper()


def _normalize_databento(raw: str) -> str:
    """Databento uses exchange-native symbols; return uppercase as-is."""
    return raw.upper()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_VENUE_MAP: dict[str, Callable[[str], str]] = {
    "binance": _normalize_binance,
    "binance_spot": _normalize_binance,
    "binance_futures": _normalize_binance,
    "binance_unified": _normalize_binance,
    "bybit": _normalize_bybit,
    "coinbase": _normalize_coinbase,
    "okx": _normalize_okx,
    "deribit": _normalize_deribit,
    "hyperliquid": _normalize_hyperliquid,
    "kraken": _normalize_kraken,
    "kucoin": _normalize_kucoin,
    "gateio": _normalize_gateio,
    "gate": _normalize_gateio,
    "bitfinex": _normalize_bitfinex,
    "dydx": _normalize_dydx,
    "tardis": _normalize_tardis,
    "databento": _normalize_databento,
}


def normalize_symbol(venue: str, raw: str) -> str:
    """Convert a raw venue symbol to canonical BASE-QUOTE format.

    Canonical rules:
    - Spot: BASE-QUOTE (e.g. BTC-USDT)
    - Perpetual: BASE-QUOTE-PERP (e.g. BTC-USDT-PERP)
    - Future: BASE-QUOTE-EXPIRY (e.g. BTC-USD-231229)
    - All uppercase
    - Dash-separated

    Unknown venues: return raw.upper() unchanged.
    """
    fn = _VENUE_MAP.get(venue.lower())
    if fn is None:
        return raw.upper()
    return fn(raw)


__all__ = ["normalize_symbol"]
