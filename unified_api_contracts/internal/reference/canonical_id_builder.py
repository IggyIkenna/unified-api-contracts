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
from collections.abc import Sequence
from decimal import Decimal
from typing import Final, Literal

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical.domain.derivatives import ComboStrategyType

__all__ = [
    "SUPPORTED_INSTRUMENT_TYPES",
    "UNSUPPORTED_BY_DESIGN",
    "build_combo_id",
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
        # DEX_POOL: spot-DEX orderbook + quote + per-swap shards (Solana
        # basis MVP Phase 2 2026-06-01). Distinct partition from POOL so
        # Phoenix orderbook / Jupiter quotes / Orca trades don't collide
        # with the EVM AMM pool contract.
        InstrumentType.DEX_POOL,
        InstrumentType.LENDING,
        InstrumentType.LST,
        InstrumentType.YIELD_BEARING,
        InstrumentType.A_TOKEN,
        InstrumentType.DEBT_TOKEN,
        InstrumentType.STAKING,
        InstrumentType.SPOT_ASSET,
        # DeFi Solana (distinct shapes; SchemaContracts at UAC@7e9f4ad9)
        InstrumentType.SOLANA_LENDING,
        InstrumentType.SOLANA_VAULT,
        InstrumentType.SOLANA_AMM_POOL,
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
        # TradFi x Prediction cross-venue
        InstrumentType.EVENT_CONTRACT,
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
        InstrumentType.DEX_POOL,
        InstrumentType.LENDING,
        InstrumentType.LST,
        InstrumentType.YIELD_BEARING,
        InstrumentType.A_TOKEN,
        InstrumentType.DEBT_TOKEN,
        InstrumentType.STAKING,
        InstrumentType.SPOT_ASSET,
        # Solana DeFi (same VENUE-CHAIN:TYPE:SYMBOL builder; chain="SOLANA")
        InstrumentType.SOLANA_LENDING,
        InstrumentType.SOLANA_VAULT,
        InstrumentType.SOLANA_AMM_POOL,
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
    quote_asset: str = "",
    margin_type: str = "",
) -> str:
    """Build ``VENUE:FUTURE:SYMBOL-YYYYMMDD`` for dated futures.

    v6: when ``quote_asset`` and ``margin_type`` are both non-empty (e.g.
    ``"USD"`` + ``"inverse"``), they are injected between the underlying and
    the expiry to disambiguate inverse/linear shards:
    ``DERIBIT:FUTURE:BTC-USD-inverse-20261226``.
    Legacy callers omit these kwargs and get the unchanged format.
    """
    if expiry_date is None:
        msg = f"{itype.value} requires expiry_date"
        raise ValueError(msg)
    sym_up = symbol.upper()
    if quote_asset and margin_type:
        return (
            f"{_venue_token(venue, None)}:{itype.value}:"
            f"{sym_up}-{quote_asset.upper()}-{margin_type.lower()}-{expiry_date.strftime('%Y%m%d')}"
        )
    return f"{_venue_token(venue, None)}:{itype.value}:{sym_up}-{expiry_date.strftime('%Y%m%d')}"


def _build_option(
    venue: str,
    symbol: str,
    expiry_date: _dt.date | None,
    strike: Decimal | None,
    option_right: Literal["C", "P"] | None,
    quote_asset: str = "",
    margin_type: str = "",
) -> str:
    """Build ``VENUE:OPTION:SYMBOL-YYYYMMDD-STRIKE-[C|P]``.

    v6: when ``quote_asset`` and ``margin_type`` are both non-empty, they are
    injected between the underlying and the expiry to disambiguate:
    ``DERIBIT:OPTION:BTC-USD-inverse-20261226-65000-C``.
    Legacy callers omit these kwargs and get the unchanged format.
    """
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
    sym_up = symbol.upper()
    if quote_asset and margin_type:
        return (
            f"{_venue_token(venue, None)}:{InstrumentType.OPTION.value}:"
            f"{sym_up}-{quote_asset.upper()}-{margin_type.lower()}"
            f"-{expiry_date.strftime('%Y%m%d')}-{strike_str}-{option_right}"
        )
    return (
        f"{_venue_token(venue, None)}:{InstrumentType.OPTION.value}:"
        f"{sym_up}-{expiry_date.strftime('%Y%m%d')}-{strike_str}-{option_right}"
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
    """Build ``VENUE:COMBO:SYMBOL`` — symbol is an opaque combo identifier.

    For structured combo IDs (butterfly/iron-condor/calendar) use
    :func:`build_combo_id` which encodes strategy + expiries + strikes.
    """
    if not symbol:
        msg = "COMBO requires a non-empty symbol identifying the combo"
        raise ValueError(msg)
    return f"{_venue_token(venue, None)}:{InstrumentType.COMBO.value}:{symbol.upper()}"


# Strategies whose anchor points are **strikes** (N strike points).
_STRIKE_ANCHORED_STRATEGIES: Final[frozenset[ComboStrategyType]] = frozenset(
    {
        ComboStrategyType.BUTTERFLY,
        ComboStrategyType.CALL_BUTTERFLY,
        ComboStrategyType.PUT_BUTTERFLY,
        ComboStrategyType.IRON_BUTTERFLY,
        ComboStrategyType.CONDOR,
        ComboStrategyType.IRON_CONDOR,
        ComboStrategyType.STRADDLE,
        ComboStrategyType.STRANGLE,
        ComboStrategyType.VERTICAL,
        ComboStrategyType.BULL_CALL_SPREAD,
        ComboStrategyType.BEAR_PUT_SPREAD,
        ComboStrategyType.RATIO_SPREAD,
        ComboStrategyType.RISK_REVERSAL,
        ComboStrategyType.BOX,
        ComboStrategyType.COLLAR,
        ComboStrategyType.COVERED_CALL,
        ComboStrategyType.PROTECTIVE_PUT,
    }
)

# Strategies whose anchor points are **expiries** (N expiry dates).
_EXPIRY_ANCHORED_STRATEGIES: Final[frozenset[ComboStrategyType]] = frozenset(
    {
        ComboStrategyType.CALENDAR_SPREAD,
        ComboStrategyType.CALENDAR,
        ComboStrategyType.DIAGONAL,
        ComboStrategyType.SPREAD,
        ComboStrategyType.JELLY_ROLL,
        ComboStrategyType.EFP,
    }
)


def build_combo_id(
    venue: str,
    underlying: str,
    strategy: ComboStrategyType,
    *,
    anchor_expiry: _dt.date | None = None,
    strikes: Sequence[Decimal] | None = None,
    expiries: Sequence[_dt.date] | None = None,
) -> str:
    """Build a structured canonical COMBO id.

    Format: ``VENUE:COMBO:{UNDERLYING}-{STRATEGY}-{anchor_expiry?}-{ANCHORS...}``.

    Strike-anchored strategies (butterfly, iron condor, straddle, …) need
    one ``anchor_expiry`` plus the ordered ``strikes``. Expiry-anchored
    strategies (calendar, diagonal, jelly roll, …) need the ordered
    ``expiries``.

    Examples
    --------
    Butterfly::

        build_combo_id(
            "CME",
            "SP500",
            ComboStrategyType.BUTTERFLY,
            anchor_expiry=date(2024, 6, 21),
            strikes=[Decimal(5500), Decimal(5600), Decimal(5700)],
        )
        # → "CME:COMBO:SP500-BUTTERFLY-20240621-5500-5600-5700"

    Calendar::

        build_combo_id(
            "CME",
            "SP500",
            ComboStrategyType.CALENDAR,
            expiries=[date(2024, 6, 21), date(2024, 9, 20)],
        )
        # → "CME:COMBO:SP500-CALENDAR-20240621-20240920"

    Iron condor::

        build_combo_id(
            "CME",
            "SP500",
            ComboStrategyType.IRON_CONDOR,
            anchor_expiry=date(2024, 6, 21),
            strikes=[Decimal(5400), Decimal(5500), Decimal(5600), Decimal(5700)],
        )
        # → "CME:COMBO:SP500-IRON_CONDOR-20240621-5400-5500-5600-5700"
    """
    if not underlying:
        msg = "build_combo_id requires a non-empty underlying"
        raise ValueError(msg)
    if strategy is ComboStrategyType.CUSTOM:
        msg = (
            "build_combo_id does not accept ComboStrategyType.CUSTOM — "
            "fall back to build_instrument_id(InstrumentType.COMBO, symbol=...) "
            "for opaque combos."
        )
        raise ValueError(msg)

    venue_token = _venue_token(venue, None)
    underlying_up = underlying.strip().upper()
    strategy_token = strategy.value.upper()

    if strategy in _STRIKE_ANCHORED_STRATEGIES:
        if anchor_expiry is None:
            msg = f"build_combo_id: strategy={strategy.value} requires anchor_expiry"
            raise ValueError(msg)
        if not strikes:
            msg = f"build_combo_id: strategy={strategy.value} requires at least one strike"
            raise ValueError(msg)
        strike_tokens = "-".join(_format_strike(s) for s in strikes)
        tail = f"{anchor_expiry.strftime('%Y%m%d')}-{strike_tokens}"
    elif strategy in _EXPIRY_ANCHORED_STRATEGIES:
        if not expiries or len(expiries) < 2:
            msg = f"build_combo_id: strategy={strategy.value} requires at least two expiries"
            raise ValueError(msg)
        tail = "-".join(e.strftime("%Y%m%d") for e in expiries)
    else:
        msg = (
            f"build_combo_id: no anchor convention registered for strategy={strategy.value}. "
            "Add it to _STRIKE_ANCHORED_STRATEGIES or _EXPIRY_ANCHORED_STRATEGIES."
        )
        raise ValueError(msg)

    return f"{venue_token}:{InstrumentType.COMBO.value}:{underlying_up}-{strategy_token}-{tail}"


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
    quote_asset: str = "",
    margin_type: str = "",
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
    quote_asset:
        v6 settlement dimension — e.g. ``"USD"``, ``"USDT"``, ``"USDC"``.
        When non-empty (and ``margin_type`` is also non-empty) for OPTION or
        FUTURE, it is embedded in the canonical ID between the underlying and
        the expiry so inverse and linear shards on the same underlying produce
        distinct IDs. Legacy callers that omit this kwarg get the unchanged
        pre-v6 format.
    margin_type:
        v6 settlement dimension — ``"inverse"`` or ``"linear"``. Only
        meaningful (and emitted) when ``quote_asset`` is also non-empty.

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
        return _build_future(venue, instrument_type, symbol, expiry_date, quote_asset, margin_type)

    if instrument_type is InstrumentType.OPTION:
        return _build_option(venue, symbol, expiry_date, strike, option_right, quote_asset, margin_type)

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

    # TradFi x Prediction cross-venue (EVENT_CONTRACT) -- resolution_date axis
    if instrument_type is InstrumentType.EVENT_CONTRACT:
        return _build_future(venue, instrument_type, symbol, expiry_date)

    # Should be unreachable given the membership check above — defend anyway.
    msg = f"No builder registered for InstrumentType {instrument_type.value}"
    raise ValueError(msg)
