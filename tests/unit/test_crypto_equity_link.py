"""Unit tests for crypto-venue equity-perp → real-equity canonical cross-link.

Mirrors the structure of test_cme_polymarket_link.py.
Plan: cryptovenue_equity_perps_and_tokenized_stocks_2026_06_20.md Phase 1.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.crypto_equity_link import (
    CRYPTO_EQUITY_PERP_TO_REAL_EQUITY,
    LINKED_EQUITY_PERP_BASES,
    STANDALONE_EQUITY_PERP_SYMBOLS,
    tracks_equity,
)
from unified_api_contracts.registry.cefi_instrument_universe import (
    CEFI_EQUITY_PERP_BASE_UNIVERSE,
)

# The verified OKX 17 US equity perp bases + Binance/Bybit reps.
_OKX_17_BASES = frozenset(
    {
        "AAPL",
        "TSLA",
        "AMZN",
        "MSFT",
        "NVDA",
        "NFLX",
        "AMD",
        "INTC",
        "BABA",
        "COIN",
        "MSTR",
        "PLTR",
        "GME",
        "AMC",
        "MARA",
    }
)

# Binance/Bybit confirmed single-stock perp bases.
_BINANCE_BYBIT_BASES = frozenset(
    {
        "META",
        "GOOGL",
        "GOOG",
        "AAPL",
        "TSLA",
    }
)


def test_linked_equity_perp_bases_matches_dict_keys() -> None:
    """LINKED_EQUITY_PERP_BASES must exactly match the dict keys."""
    assert frozenset(CRYPTO_EQUITY_PERP_TO_REAL_EQUITY) == LINKED_EQUITY_PERP_BASES


def test_okx_17_bases_wired() -> None:
    """OKX 17 US equity perp bases must all have a real-equity canonical link."""
    missing = _OKX_17_BASES - LINKED_EQUITY_PERP_BASES
    assert not missing, f"OKX equity perp bases missing from link map: {sorted(missing)}"


def test_binance_bybit_bases_wired() -> None:
    """Binance/Bybit equity perp bases must all have a real-equity canonical link."""
    missing = _BINANCE_BYBIT_BASES - LINKED_EQUITY_PERP_BASES
    assert not missing, f"Binance/Bybit equity perp bases missing from link map: {sorted(missing)}"


def test_tracks_equity_returns_correct_ticker() -> None:
    """Known bases return the correct Databento canonical ticker."""
    assert tracks_equity("META") == "META"
    assert tracks_equity("NVDA") == "NVDA"
    assert tracks_equity("AAPL") == "AAPL"
    assert tracks_equity("TSLA") == "TSLA"
    # Alphabet: both GOOG and GOOGL map to canonical GOOGL (Databento ticker)
    assert tracks_equity("GOOG") == "GOOGL"
    assert tracks_equity("GOOGL") == "GOOGL"
    assert tracks_equity("AMZN") == "AMZN"
    assert tracks_equity("MSFT") == "MSFT"
    assert tracks_equity("COIN") == "COIN"
    assert tracks_equity("MSTR") == "MSTR"


def test_standalone_symbols_return_none() -> None:
    """Pre-IPO / standalone symbols with no real-equity twin return None."""
    # SPCX (SpaceX) is the canonical pre-IPO example — dispersion-only.
    assert tracks_equity("SPCX") is None


def test_unknown_base_returns_none() -> None:
    """Unknown / unregistered bases return None without raising."""
    assert tracks_equity("INVALID") is None
    assert tracks_equity("") is None
    assert tracks_equity("BTC") is None  # crypto coin, not equity base


def test_standalone_symbols_not_in_linked() -> None:
    """Standalone symbols must NOT appear in LINKED_EQUITY_PERP_BASES."""
    overlap = STANDALONE_EQUITY_PERP_SYMBOLS & LINKED_EQUITY_PERP_BASES
    assert not overlap, f"standalone symbols found in linked map: {sorted(overlap)}"


def test_cefi_equity_perp_base_universe_contains_linked_bases() -> None:
    """CEFI_EQUITY_PERP_BASE_UNIVERSE must contain all linked equity bases.

    The universe is the filter set for the instruments-service adapter; any
    linked base not in the universe would silently exclude its instruments.
    Note: Korean equity KRX codes (e.g. 005930) are also in the universe but
    are NOT in the link map (no Databento US-equity twin).
    """
    missing = LINKED_EQUITY_PERP_BASES - CEFI_EQUITY_PERP_BASE_UNIVERSE
    # GOOG is a Binance alias for GOOGL — the universe uses GOOGL canonical.
    # Strip the alias before asserting.
    aliases_not_in_universe = frozenset({"GOOG"})
    missing_non_alias = missing - aliases_not_in_universe
    assert not missing_non_alias, (
        f"Linked equity perp bases missing from CEFI_EQUITY_PERP_BASE_UNIVERSE: "
        f"{sorted(missing_non_alias)}"
    )


def test_instrument_types_exist() -> None:
    """EQUITY_PERP and TOKENIZED_EQUITY must be valid InstrumentType members."""
    from unified_api_contracts import InstrumentType

    assert InstrumentType.EQUITY_PERP == "EQUITY_PERP"
    assert InstrumentType.TOKENIZED_EQUITY == "TOKENIZED_EQUITY"
