"""Crypto-venue equity-perp / tokenized-stock → real-equity canonical cross-link SSOT.

Crypto venues (Binance, OKX, Bybit) now list **single-stock perpetual contracts**
and **tokenized stocks** that track real underlying equities.  This module is the
single authoritative mapping from each crypto-venue equity-perp symbol to its
Databento ``DBEQ.BASIC`` canonical equity ticker, enabling:

* **Equity basis arb** — crypto-venue stock-perp vs Databento real equity.
* **Cross-venue dispersion** — same underlying across Binance / OKX / Bybit.
* **24/7-vs-market-hours overnight-gap arb** — crypto venues trade around the clock.

Symbol taxonomy
---------------
``basis_arb_able`` symbols have a real-equity twin in Databento ``DBEQ.BASIC``.
``tracks_equity()`` returns their canonical ticker (e.g. ``"AAPL"`` for ``AAPLX``).

Pre-IPO / standalone symbols (e.g. Binance ``SPCXUSDT`` — SpaceX) have NO
real-equity Databento twin.  ``tracks_equity()`` returns ``None`` for them; they
are tracked in :data:`STANDALONE_EQUITY_PERP_SYMBOLS` (dispersion-only across
crypto venues).

Venue-symbol conventions
-------------------------
Symbols are stored in canonical SHORT form (venue-independent base):

* ``METAUSDT`` — the Binance/Bybit USDT-margined perp base string.
* ``META-USDT-SWAP`` — the OKX format (stored as ``META`` base, resolved by
  the instruments-service adapter which normalises to the base ticker).

To avoid the proliferation of per-venue symbol strings, the key of
:data:`CRYPTO_EQUITY_PERP_TO_REAL_EQUITY` is the **base equity ticker** that
appears in the crypto-venue symbol (``META``, not ``METAUSDT`` or
``META-USDT-SWAP``).  Each instruments-service adapter extracts the base ticker
and calls :func:`tracks_equity` for the canonical equity link.

Operator-seeded 2026-06-20: OKX 17 US equity perps + Binance Meta/NVDA/GOOG perps
+ Bybit TSLA/AAPL stock perps + tokenized AAPLX.

Plan: ``cryptovenue_equity_perps_and_tokenized_stocks_2026_06_20.md`` Phase 1.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Canonical cross-link map — crypto-venue equity base → real equity ticker
#
# Key: the BASE component of the crypto-venue equity-perp symbol (e.g. ``META``
#   for Binance ``METAUSDT``, OKX ``META-USDT-SWAP``).
# Value: the Databento ``DBEQ.BASIC`` canonical ticker for the real equity.
#   In most cases key == value (``META`` → ``META``).
#   Exceptions: Alphabet (``GOOGL`` Databento ticker vs ``GOOG`` crypto label).
#
# Symbols absent from this dict → check STANDALONE_EQUITY_PERP_SYMBOLS.
# Symbols absent from both → unknown / not yet registered (return None).
# ---------------------------------------------------------------------------
CRYPTO_EQUITY_PERP_TO_REAL_EQUITY: Final[dict[str, str]] = {
    # --- US equities — Binance/OKX/Bybit confirmed coverage ---
    "AAPL": "AAPL",  # Apple — Bybit AAPLX tokenized + OKX AAPL-USDT-SWAP
    "TSLA": "TSLA",  # Tesla — Bybit TSLA + OKX TSLA-USDT-SWAP
    "AMZN": "AMZN",  # Amazon — OKX AMZN-USDT-SWAP
    "MSFT": "MSFT",  # Microsoft — OKX MSFT-USDT-SWAP
    "GOOGL": "GOOGL",  # Alphabet — OKX/Binance may label "GOOG"; canonical Databento is GOOGL
    "GOOG": "GOOGL",  # Alphabet Class C alias (some venues use GOOG, Databento=GOOGL)
    "META": "META",  # Meta Platforms — Binance METAUSDT perp, OKX META-USDT-SWAP
    "NVDA": "NVDA",  # NVIDIA — Binance NVDAUSDT perp, OKX NVDA-USDT-SWAP
    "NFLX": "NFLX",  # Netflix — OKX NFLX-USDT-SWAP
    "AMD": "AMD",  # AMD — OKX AMD-USDT-SWAP
    "INTC": "INTC",  # Intel — OKX INTC-USDT-SWAP
    "BABA": "BABA",  # Alibaba — OKX BABA-USDT-SWAP
    "COIN": "COIN",  # Coinbase — OKX COIN-USDT-SWAP
    "MSTR": "MSTR",  # MicroStrategy — OKX MSTR-USDT-SWAP
    "PLTR": "PLTR",  # Palantir — OKX PLTR-USDT-SWAP
    "GME": "GME",  # GameStop — OKX GME-USDT-SWAP
    # AMC / MARA REMOVED 2026-07-08: verified genuinely delisted from all 3
    # tracked venues — absent from Binance fapi/v1/exchangeInfo (no symbol,
    # any contractType/status), OKX (SWAP/FUTURES/SPOT/MARGIN instruments,
    # AMC-USDT-SWAP / MARA-USDT-SWAP return OKX error 51001 "doesn't exist"),
    # and Bybit (/v5/market/instruments-info?category=linear). See matching
    # removal in cefi_instrument_universe.CEFI_EQUITY_PERP_BASE_UNIVERSE.
}

# ---------------------------------------------------------------------------
# Standalone equity-perp symbols — NO real-equity Databento twin.
# These are dispersion-only (cross-crypto-venue) and cannot form a
# basis-arb pair against a real equity.
# ---------------------------------------------------------------------------
STANDALONE_EQUITY_PERP_SYMBOLS: Final[frozenset[str]] = frozenset(
    {
        # Binance SPCXUSDT — SpaceX (pre-IPO as of 2026-06-20; its #2 product on Binance)
        "SPCX",
    }
)

# Frozenset of crypto equity-perp base symbols that ARE linked to a real equity.
LINKED_EQUITY_PERP_BASES: Final[frozenset[str]] = frozenset(CRYPTO_EQUITY_PERP_TO_REAL_EQUITY)


def tracks_equity(equity_perp_base: str) -> str | None:
    """Return the Databento ``DBEQ.BASIC`` canonical ticker tracked by *equity_perp_base*.

    *equity_perp_base* is the BASE component of the crypto-venue equity-perp
    symbol (e.g. ``"META"`` for ``METAUSDT``, ``"AAPL"`` for ``AAPLX``).

    Returns the canonical real-equity ticker (e.g. ``"META"``, ``"AAPL"``) when
    the symbol has a wired Databento twin, or ``None`` for standalone /
    pre-IPO symbols (e.g. ``"SPCX"``).

    Callers MUST handle ``None`` — it is not an error; it means the instrument
    is a dispersion-only position with no real-equity basis leg.

    Example::

        ticker = tracks_equity("META")   # → "META"
        ticker = tracks_equity("SPCX")   # → None  (SpaceX pre-IPO)
        ticker = tracks_equity("UNKNOWN")  # → None
    """
    return CRYPTO_EQUITY_PERP_TO_REAL_EQUITY.get(equity_perp_base)


__all__ = [
    "CRYPTO_EQUITY_PERP_TO_REAL_EQUITY",
    "LINKED_EQUITY_PERP_BASES",
    "STANDALONE_EQUITY_PERP_SYMBOLS",
    "tracks_equity",
]
