"""Centralised canonical instrument ID builder — SSOT.

Produces canonical instrument IDs of the form ``VENUE:INSTRUMENT_TYPE:SYMBOL``
for every :class:`InstrumentType` variant used across the Unified Trading
System. DeFi venues are composed as ``VENUE-CHAIN`` so that the same protocol
on different chains yields distinct IDs.

This module is the single dispatch point for financial instrument IDs. Sports
and prediction-market canonical IDs live in their domain modules
(``canonical/domain/sports/canonical_ids.py`` and
``canonical/domain/prediction/prediction_mapping.py``) and are re-used here
via imports, not duplicated.

Examples
--------
CeFi::

    build_instrument_id("binance_futures", InstrumentType.PERPETUAL, "BTCUSDT")
    # → "BINANCE_FUTURES:PERPETUAL:BTCUSDT"

    build_instrument_id(
        "deribit",
        InstrumentType.OPTION,
        "BTC",
        expiry_date=date(2026, 3, 28),
        strike=Decimal("65000"),
        option_right="C",
    )
    # → "DERIBIT:OPTION:BTC-20260328-65000-C"

TradFi::

    build_instrument_id(
        "cme",
        InstrumentType.FUTURE,
        "ES",
        expiry_date=date(2026, 6, 20),
    )
    # → "CME:FUTURE:ES-20260620"

DeFi::

    build_instrument_id(
        "uniswap_v3",
        InstrumentType.POOL,
        "USDC-WETH-500",
        chain="ethereum",
    )
    # → "UNISWAP_V3-ETHEREUM:POOL:USDC-WETH-500"
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Final, Literal

from unified_api_contracts._instrument_enums import InstrumentType

__all__ = [
    "SUPPORTED_INSTRUMENT_TYPES",
    "UNSUPPORTED_BY_DESIGN",
    "build_instrument_id",
]


# ---------------------------------------------------------------------------
# Coverage manifest
# ---------------------------------------------------------------------------

# Every InstrumentType this builder dispatches on. Unit tests assert that the
# union of SUPPORTED_INSTRUMENT_TYPES and UNSUPPORTED_BY_DESIGN equals the full
# InstrumentType enum — adding a new enum value fails the coverage test until
# the builder is extended (or the enum value is explicitly declared out of
# scope here).
SUPPORTED_INSTRUMENT_TYPES: Final[frozenset[InstrumentType]] = frozenset(
    {
        # CeFi
        InstrumentType.SPOT_PAIR,
        InstrumentType.PERPETUAL,
        InstrumentType.FUTURE,
        InstrumentType.OPTION,
        # DeFi
        InstrumentType.POOL,
        InstrumentType.LENDING,
        InstrumentType.LST,
        InstrumentType.YIELD_BEARING,
        InstrumentType.A_TOKEN,
        InstrumentType.DEBT_TOKEN,
        InstrumentType.STAKING,
        InstrumentType.SPOT_ASSET,
        # TradFi
        InstrumentType.ETF,
        InstrumentType.EQUITY,
        InstrumentType.COMMODITY,
        InstrumentType.CURRENCY,
        InstrumentType.INDEX,
        InstrumentType.BOND,
        InstrumentType.CDS,
        # Multi-leg
        InstrumentType.COMBO,
        # Sports / prediction
        InstrumentType.PREDICTION_MARKET,
        InstrumentType.EXCHANGE_ODDS,
        InstrumentType.FIXED_ODDS,
        InstrumentType.PROP,
    }
)

# InstrumentType values that this builder intentionally does not support.
# Empty today — every enum value is handled. Keep the constant so the coverage
# test has a single place to declare opt-outs if the enum grows non-tradable
# sentinel values in future.
UNSUPPORTED_BY_DESIGN: Final[frozenset[InstrumentType]] = frozenset()


# ---------------------------------------------------------------------------
# Grouping sets for dispatch
# ---------------------------------------------------------------------------

_CEFI_DATED_DERIVATIVES: Final[frozenset[InstrumentType]] = frozenset({InstrumentType.FUTURE, InstrumentType.OPTION})

_DEFI_TYPES: Final[frozenset[InstrumentType]] = frozenset(
    {
        InstrumentType.POOL,
        InstrumentType.LENDING,
        InstrumentType.LST,
        InstrumentType.YIELD_BEARING,
        InstrumentType.A_TOKEN,
        InstrumentType.DEBT_TOKEN,
        InstrumentType.STAKING,
        InstrumentType.SPOT_ASSET,
    }
)

_TRADFI_CASH_TYPES: Final[frozenset[InstrumentType]] = frozenset(
    {
        InstrumentType.ETF,
        InstrumentType.EQUITY,
        InstrumentType.COMMODITY,
        InstrumentType.CURRENCY,
        InstrumentType.INDEX,
        InstrumentType.BOND,
        InstrumentType.CDS,
    }
)

_SPORTS_AND_PREDICTION_TYPES: Final[frozenset[InstrumentType]] = frozenset(
    {
        InstrumentType.PREDICTION_MARKET,
        InstrumentType.EXCHANGE_ODDS,
        InstrumentType.FIXED_ODDS,
        InstrumentType.PROP,
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _venue_token(venue: str, chain: str | None) -> str:
    """Compose the venue segment of a canonical ID.

    For non-DeFi, returns the uppercased venue. For DeFi, returns
    ``VENUE-CHAIN`` when a chain is supplied.
    """
    if not venue:
        msg = "venue must be a non-empty string"
        raise ValueError(msg)
    venue_up = venue.upper()
    if chain:
        return f"{venue_up}-{chain.upper()}"
    return venue_up


def _format_strike(strike: Decimal) -> str:
    """Render a strike as an integer when possible, else as a plain decimal.

    Keeps canonical IDs deterministic and human-readable (``65000`` rather
    than ``65000.0`` or ``6.5E+4``).
    """
    if strike == strike.to_integral_value():
        return str(int(strike))
    # Strip trailing zeros / exponent form without losing precision.
    return format(strike.normalize(), "f")


def _build_cefi_simple(venue: str, itype: InstrumentType, symbol: str) -> str:
    """Build ``VENUE:TYPE:SYMBOL`` for CeFi spot/perpetual instruments."""
    return f"{_venue_token(venue, None)}:{itype.value}:{symbol.upper()}"


def _build_future(
    venue: str,
    itype: InstrumentType,
    symbol: str,
    expiry_date: _dt.date | None,
) -> str:
    """Build ``VENUE:FUTURE:SYMBOL-YYYYMMDD`` for dated futures."""
    if expiry_date is None:
        msg = f"{itype.value} requires expiry_date"
        raise ValueError(msg)
    return f"{_venue_token(venue, None)}:{itype.value}:{symbol.upper()}-{expiry_date.strftime('%Y%m%d')}"


def _build_option(
    venue: str,
    symbol: str,
    expiry_date: _dt.date | None,
    strike: Decimal | None,
    option_right: Literal["C", "P"] | None,
) -> str:
    """Build ``VENUE:OPTION:SYMBOL-YYYYMMDD-STRIKE-[C|P]``."""
    if expiry_date is None or strike is None or option_right is None:
        msg = (
            "OPTION requires expiry_date, strike, and option_right "
            f"(got expiry_date={expiry_date!r} strike={strike!r} option_right={option_right!r})"
        )
        raise ValueError(msg)
    if option_right not in ("C", "P"):
        msg = f"option_right must be 'C' or 'P', got {option_right!r}"
        raise ValueError(msg)
    strike_str = _format_strike(strike)
    return (
        f"{_venue_token(venue, None)}:{InstrumentType.OPTION.value}:"
        f"{symbol.upper()}-{expiry_date.strftime('%Y%m%d')}-{strike_str}-{option_right}"
    )


def _build_defi(
    venue: str,
    itype: InstrumentType,
    symbol: str,
    chain: str | None,
) -> str:
    """Build ``VENUE-CHAIN:TYPE:SYMBOL`` for DeFi instruments.

    DeFi IDs preserve symbol case (e.g. ``aUSDC``, ``variableDebtUSDC``,
    ``stETH``, ``sUSDe``) because DeFi token symbols are case-sensitive on
    chain. CeFi/TradFi IDs upper-case the symbol for normalisation.

    POOL symbols typically encode fee tiers (``USDC-WETH-500``) and are also
    preserved verbatim after stripping whitespace.
    """
    if itype is InstrumentType.POOL and not symbol:
        msg = "POOL requires a non-empty symbol (e.g. 'USDC-WETH-500')"
        raise ValueError(msg)
    return f"{_venue_token(venue, chain)}:{itype.value}:{symbol}"


def _build_tradfi_cash(
    venue: str,
    itype: InstrumentType,
    symbol: str,
) -> str:
    """Build ``VENUE:TYPE:SYMBOL`` for TradFi cash/reference instruments."""
    return f"{_venue_token(venue, None)}:{itype.value}:{symbol.upper()}"


def _build_combo(venue: str, symbol: str) -> str:
    """Build ``VENUE:COMBO:SYMBOL`` — symbol is an opaque combo identifier."""
    if not symbol:
        msg = "COMBO requires a non-empty symbol identifying the combo"
        raise ValueError(msg)
    return f"{_venue_token(venue, None)}:{InstrumentType.COMBO.value}:{symbol.upper()}"


def _build_sports_or_prediction(venue: str, itype: InstrumentType, symbol: str) -> str:
    """Build ``VENUE:TYPE:SYMBOL`` for sports/prediction wrappers.

    The ``symbol`` here is expected to already be a canonical sports or
    prediction instrument ID produced by
    ``canonical.domain.sports.canonical_ids.build_instrument_id`` /
    ``build_prediction_instrument_id``. This function wraps it with the
    ``VENUE:TYPE:`` prefix so the central dispatcher produces a homogeneous
    format across categories.
    """
    if not symbol:
        msg = f"{itype.value} requires a non-empty symbol (pre-built sports/prediction canonical id)"
        raise ValueError(msg)
    return f"{_venue_token(venue, None)}:{itype.value}:{symbol}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_instrument_id(
    venue: str,
    instrument_type: InstrumentType,
    symbol: str,
    *,
    expiry_date: _dt.date | None = None,
    strike: Decimal | None = None,
    option_right: Literal["C", "P"] | None = None,
    underlying: str | None = None,
    chain: str | None = None,
) -> str:
    """Build a canonical instrument ID for any supported InstrumentType.

    Format: ``VENUE:INSTRUMENT_TYPE:SYMBOL``.

    DeFi venues are composed with their chain as ``VENUE-CHAIN``. Dated
    derivatives (FUTURE, OPTION) append expiry/strike/right to the symbol
    with ``-`` separators. Sports and prediction markets pass through the
    domain canonical ID from :mod:`canonical.domain.sports.canonical_ids`
    as the ``symbol`` argument.

    Parameters
    ----------
    venue:
        Venue or protocol identifier (e.g. ``"binance"``, ``"uniswap_v3"``,
        ``"cme"``). Free-form but will be upper-cased.
    instrument_type:
        Canonical :class:`InstrumentType`. Raises ``ValueError`` for
        unsupported values.
    symbol:
        Base symbol — CeFi/TradFi symbols are upper-cased; DeFi token
        symbols are preserved as-is (case-sensitive on chain).
    expiry_date:
        Required for :attr:`InstrumentType.FUTURE` and
        :attr:`InstrumentType.OPTION`.
    strike:
        Required for :attr:`InstrumentType.OPTION`.
    option_right:
        ``"C"`` or ``"P"`` — required for :attr:`InstrumentType.OPTION`.
    underlying:
        Optional underlying symbol. Accepted for parity with
        ``InstrumentRecord`` but not currently emitted in the canonical ID.
    chain:
        Required for DeFi types when the protocol is deployed on multiple
        chains (appended as ``VENUE-CHAIN``).

    Raises
    ------
    ValueError
        If ``instrument_type`` is unsupported or required kwargs are missing.
    """
    # ``underlying`` is accepted so callers can pass through InstrumentRecord
    # fields unmodified. It's not part of the canonical ID today.
    del underlying

    if instrument_type in UNSUPPORTED_BY_DESIGN:
        msg = f"InstrumentType {instrument_type.value} is unsupported by design"
        raise ValueError(msg)

    if instrument_type not in SUPPORTED_INSTRUMENT_TYPES:
        msg = (
            f"Unsupported instrument_type: {instrument_type!r}. "
            f"Add to SUPPORTED_INSTRUMENT_TYPES in canonical_id_builder.py."
        )
        raise ValueError(msg)

    # CeFi simple (spot + perpetual)
    if instrument_type in (InstrumentType.SPOT_PAIR, InstrumentType.PERPETUAL):
        return _build_cefi_simple(venue, instrument_type, symbol)

    # Dated CeFi/TradFi derivatives
    if instrument_type is InstrumentType.FUTURE:
        return _build_future(venue, instrument_type, symbol, expiry_date)

    if instrument_type is InstrumentType.OPTION:
        return _build_option(venue, symbol, expiry_date, strike, option_right)

    # DeFi
    if instrument_type in _DEFI_TYPES:
        return _build_defi(venue, instrument_type, symbol, chain)

    # TradFi cash / reference
    if instrument_type in _TRADFI_CASH_TYPES:
        return _build_tradfi_cash(venue, instrument_type, symbol)

    # Multi-leg
    if instrument_type is InstrumentType.COMBO:
        return _build_combo(venue, symbol)

    # Sports / prediction
    if instrument_type in _SPORTS_AND_PREDICTION_TYPES:
        return _build_sports_or_prediction(venue, instrument_type, symbol)

    # Should be unreachable given the membership check above — defend anyway.
    msg = f"No builder registered for InstrumentType {instrument_type.value}"
    raise ValueError(msg)
