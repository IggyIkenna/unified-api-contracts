"""Centralised canonical instrument ID builder — SSOT.

Produces canonical instrument IDs of the form ``VENUE:INSTRUMENT_TYPE:SYMBOL``
for every :class:`InstrumentType` variant used across the Unified Trading
System. DeFi venues are composed as ``VENUE-CHAIN`` so that the same protocol
on different chains yields distinct IDs.

This module is the single dispatch point for financial instrument IDs.
:func:`build_canonical_instrument_id` is the **one entry point for every
asset group** (operator decision, 2026-07-08 —
``unified-trading-pm/plans/active/issues/instrument_id_format_canonicalization_2026_07_08.md``:
"one builder for everything ... every asset group, every instrument type, can
get its canonical instrument IDs, same with fixtures, just by filling in the
right inputs"): it dispatches CeFi/DeFi/TradFi/Prediction to
:func:`build_instrument_id` below, and Sports to the fixture-id domain
builder (``canonical/domain/sports/canonical_ids.py``) — imported and
re-used here, not duplicated, and NOT forced into the ``VENUE:TYPE:SYMBOL``
shape (sports keeps its own ``LEAGUE:MATCHUP:DATE`` scheme, a separate,
confirmed operator decision — see :func:`build_canonical_instrument_id`).

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

    # Raw exchange-native passthrough (Tardis/CCXT convention for dated
    # derivatives whose native symbol already encodes expiry/strike/right —
    # bypasses structured reconstruction entirely):
    build_instrument_id("deribit", InstrumentType.OPTION, "BTC-9JUL26-56000-C", passthrough=True)
    # → "DERIBIT:OPTION:BTC-9JUL26-56000-C"

    # margin_marker — the operator-decided ``@LIN``/``@INV`` settlement suffix
    # (instrument_id_format_canonicalization_2026_07_08.md finding 1; applies
    # to PERPETUAL and dated derivatives alike, per the 2026-07-09 scope
    # expansion — margin type is NOT always inferrable from quote currency
    # alone, e.g. Kraken-Futures' USD-quoted linear AND inverse perpetuals):
    build_instrument_id("binance_futures", InstrumentType.PERPETUAL, "BTC-USDT", margin_marker="LIN")
    # → "BINANCE_FUTURES:PERPETUAL:BTC-USDT@LIN"

    build_instrument_id(
        "binance_delivery", InstrumentType.FUTURE, "BTC-USD", expiry_date=date(2026, 9, 25), margin_marker="INV",
    )
    # → "BINANCE_DELIVERY:FUTURE:BTC-USD@INV-20260925"

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

One entry point, any asset group (:func:`build_canonical_instrument_id`)::

    build_canonical_instrument_id(AssetGroup.CEFI, "bybit", InstrumentType.PERPETUAL, "BTCUSDT")
    # → "BYBIT:PERPETUAL:BTCUSDT"

    build_canonical_instrument_id(
        AssetGroup.DEFI, "aave_v3", InstrumentType.LENDING, "USDC", chain="arbitrum",
    )
    # → "AAVE_V3-ARBITRUM:LENDING:USDC"

    build_canonical_instrument_id(
        AssetGroup.SPORTS, "", None,
        league="ENG_PREMIER_LEAGUE", home_team="ARSENAL", away_team="CHELSEA",
        fixture_date="2026-03-22",
    )
    # → "ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322"  (NOT VENUE:TYPE:SYMBOL — by design)
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from decimal import Decimal
from typing import Final, Literal

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical.domain.derivatives import ComboStrategyType
from unified_api_contracts.canonical.domain.sports.canonical_ids import (
    build_fixture_id as _build_sports_fixture_id,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup
from unified_api_contracts.internal.reference.instrument import InstrumentLeg

__all__ = [
    "SUPPORTED_INSTRUMENT_TYPES",
    "UNSUPPORTED_BY_DESIGN",
    "build_canonical_instrument_id",
    "build_combo_id",
    "build_instrument_id",
    "build_leg",
    "is_two_token_pair_symbol",
    "validate_defi_spot_pair_symbol",
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
        # Crypto-venue equity instruments (2026-06-20)
        InstrumentType.EQUITY_PERP,
        InstrumentType.TOKENIZED_EQUITY,
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
        # Liquid restaking (ezETH/rsETH/pufETH) — same VENUE-CHAIN:TYPE:SYMBOL
        # DeFi builder shape as LST/STAKING.
        InstrumentType.RESTAKING,
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
        InstrumentType.RESTAKING,
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


# Instrument types eligible for the ``@LIN``/``@INV`` margin-marker suffix
# (operator decision 2026-07-08/09 — instrument_id_format_canonicalization).
# SPOT_PAIR has no margin dimension; dated derivatives and perpetuals both do.
_MARGIN_MARKER_ELIGIBLE_TYPES: Final[frozenset[InstrumentType]] = frozenset(
    {InstrumentType.PERPETUAL, InstrumentType.FUTURE, InstrumentType.OPTION}
)


def _normalize_margin_marker(value: str) -> str:
    """Normalise a margin-marker input to its canonical ``LIN``/``INV`` token.

    Accepts the marker itself (``"LIN"``/``"INV"``, any case) or the full
    :class:`~unified_api_contracts._instrument_enums.MarginType`-style word
    (``"linear"``/``"inverse"``, any case) — callers threading a raw
    ``margin_type`` value straight through don't need to pre-translate it.
    """
    token = value.strip().upper()
    if token in ("LIN", "LINEAR"):
        return "LIN"
    if token in ("INV", "INVERSE"):
        return "INV"
    msg = f"margin_marker must be 'LIN'/'linear' or 'INV'/'inverse', got {value!r}"
    raise ValueError(msg)


def _build_with_margin_marker(
    venue: str,
    instrument_type: InstrumentType,
    symbol: str,
    marker: str,
    expiry_date: _dt.date | None,
    strike: Decimal | None,
    option_right: Literal["C", "P"] | None,
    quote_asset: str = "",
) -> str:
    """Build ``VENUE:TYPE:BASE[-QUOTE]@LIN|INV[-YYYYMMDD[-STRIKE-C|P]]``.

    The margin marker rides directly on the ``symbol`` segment (e.g.
    ``BTC-USDT@LIN``), immediately before any dated-derivative suffix — this
    is the operator-decided target format
    (``instrument_id_format_canonicalization_2026_07_08.md`` finding 1),
    superseding the older ``-linear-``/``-inverse-`` word-form still produced
    by :func:`_build_future`/:func:`_build_option` when their legacy
    ``quote_asset``/``margin_type`` kwargs are used directly (kept unchanged
    for existing callers — this is a purely additive, opt-in code path).

    ``quote_asset`` (additive, opt-in — default ``""`` keeps every existing
    ``margin_marker`` caller byte-identical) composes an explicit quote onto
    the *bare* product-root symbol segment as ``PRODUCT_ROOT-QUOTE@marker``.
    This is the operator-decided TradFi shape (2026-07-18):
    ``CME:FUTURE:SP500-USD@LIN-20300621`` /
    ``CME:OPTION:SP500-USD@LIN-20251017-5000-C`` /
    ``CBOE:FUTURE:VIX-USD@LIN-20260722`` — every TradFi FUTURE/OPTION carries
    an explicit ``-USD`` quote so "same pattern regardless of asset class" is
    literally true and consistent with the 2026-07-18 DERIBIT quote ruling.
    Do NOT pass ``quote_asset`` when the ``symbol`` already embeds its quote
    (the CeFi convention, e.g. ``BTC-USDT``) — that would double-append.
    """
    sym_up = symbol.upper()
    quote = quote_asset.strip().upper()
    if quote:
        sym_up = f"{sym_up}-{quote}"
    venue_token = _venue_token(venue, None)

    if instrument_type is InstrumentType.PERPETUAL:
        return f"{venue_token}:{instrument_type.value}:{sym_up}@{marker}"

    if instrument_type is InstrumentType.FUTURE:
        if expiry_date is None:
            msg = f"{instrument_type.value} requires expiry_date"
            raise ValueError(msg)
        return f"{venue_token}:{instrument_type.value}:{sym_up}@{marker}-{expiry_date.strftime('%Y%m%d')}"

    # OPTION
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
        f"{venue_token}:{InstrumentType.OPTION.value}:{sym_up}@{marker}"
        f"-{expiry_date.strftime('%Y%m%d')}-{strike_str}-{option_right}"
    )


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


# ---------------------------------------------------------------------------
# DeFi SPOT_PAIR taxonomy validator (importable by instruments-service adapters)
# ---------------------------------------------------------------------------
#
# Operator ruling 2026-07-18 (defi_consolidated_closeout_2026_07_18.md, "SPOT_ASSET
# vs SPOT_PAIR vs POOL"): for ``asset_group=defi`` a ``SPOT_PAIR`` MUST be a
# two-token quoted market (``BASE-QUOTE``). A SINGLE on-chain token you want
# oracle-price / transfer / gas / bridge data for is a ``SPOT_ASSET``; an AMM/DEX
# liquidity pool is a ``POOL`` (EVM) or ``DEX_POOL`` / ``SOLANA_AMM_POOL`` (Solana).
# This guards the SINGLE-TOKEN SPOT_PAIR-misuse class only (single tokens like
# EIGEN/ETHFI mis-minted as SPOT_PAIR — they fail the two-token check here).
# Two-token AMM/DEX pools (meteora/lifinity, e.g. ``SOL-USDC``) PASS the
# two-token check and are guarded at adapter type-selection (typed
# SOLANA_AMM_POOL / POOL), NOT by this validator.


def is_two_token_pair_symbol(symbol: str) -> bool:
    """Return ``True`` iff ``symbol`` is a two-token ``BASE-QUOTE`` (both legs non-empty).

    The base is the segment before the first ``-``; the quote is everything
    after it (so a multi-hyphen quote like ``"USDC-USDT"`` still counts as
    two-token). A single bare token (``"WETH"``) or a blank / hanging-hyphen
    symbol (``"WETH-"`` / ``"-USDC"``) is ``False``.
    """
    base, sep, quote = symbol.strip().partition("-")
    return bool(base.strip()) and bool(sep) and bool(quote.strip())


def validate_defi_spot_pair_symbol(symbol: str) -> None:
    """Enforce the DeFi ``SPOT_PAIR`` two-token rule; raise ``ValueError`` otherwise.

    For ``asset_group=defi`` a ``SPOT_PAIR`` REQUIRES a two-token ``BASE-QUOTE``
    symbol (operator ruling 2026-07-18). A single token must be typed
    ``SPOT_ASSET``; an AMM/DEX pool must be a ``POOL`` (EVM) or ``DEX_POOL`` /
    ``SOLANA_AMM_POOL`` (Solana) type. Importable + callable by the
    instruments-service adapters so a single-token misuse is rejected at
    construction time rather than silently minting a wrong canonical id.
    Enforced at the single UAC entry point :func:`build_canonical_instrument_id`
    when ``asset_group=defi`` and ``instrument_type=SPOT_PAIR``.
    """
    if not is_two_token_pair_symbol(symbol):
        msg = (
            f"asset_group=defi SPOT_PAIR requires a two-token BASE-QUOTE symbol, got {symbol!r}. "
            "A single on-chain token must be typed SPOT_ASSET; an AMM/DEX pool must be POOL "
            "(EVM) or DEX_POOL/SOLANA_AMM_POOL (Solana)."
        )
        raise ValueError(msg)


# TradFi cash types that carry the explicit base-quote suffix (operator
# decision, 2026-07-18 — tradfi_consolidated_closeout_2026_07_18.md "Equity id
# = -USD on ALL FOUR surfaces", extended by the same ruling to every other
# TradFi cash type so the pattern is uniform regardless of asset class). CDS
# is intentionally excluded: a CDS index (e.g. ITRAXX_EUR) is quoted in basis
# points on notional, not a base/quote currency pair, so the quote-suffix
# convention doesn't apply — keep it in the plain ``VENUE:TYPE:SYMBOL`` form
# unless/until an operator decision says otherwise.
_TRADFI_CASH_QUOTE_SUFFIXED_TYPES: Final[frozenset[InstrumentType]] = frozenset(
    {
        InstrumentType.INDEX,
        InstrumentType.EQUITY,
        InstrumentType.CURRENCY,
        InstrumentType.ETF,
        InstrumentType.BOND,
        InstrumentType.COMMODITY,
    }
)


def _build_tradfi_cash(
    venue: str,
    itype: InstrumentType,
    symbol: str,
    quote_asset: str = "",
) -> str:
    """Build the canonical key for TradFi cash/reference instruments.

    Every TradFi cash type — ``INDEX``, ``EQUITY``, ``CURRENCY``, ``ETF``,
    ``BOND``, ``COMMODITY`` — carries an explicit base-quote suffix (e.g.
    ``CBOE:INDEX:US10Y-USD``, ``NASDAQ:EQUITY:AAPL-USD``, ``FX:CURRENCY:KRW-USD``)
    to match the symbology GCS key and the ``data_source_continuity`` resolver
    keys — a bare ``VENUE:TYPE:SYMBOL`` mismatches the captured-data path and
    silently breaks source/data-status resolution. This is the operator-decided
    target (2026-07-18, ``tradfi_consolidated_closeout_2026_07_18.md``):
    "same pattern regardless of asset class." ``quote_asset`` defaults to
    ``USD`` for these types (every listed cash instrument today is
    USD-denominated); pass ``quote_asset="EUR"`` etc. to override. ``CDS`` is
    excluded — it has no base/quote currency dimension — and keeps the plain
    ``VENUE:CDS:SYMBOL`` form.
    """
    base = f"{_venue_token(venue, None)}:{itype.value}:{symbol.upper()}"
    if itype in _TRADFI_CASH_QUOTE_SUFFIXED_TYPES:
        quote = (quote_asset or "USD").upper()
        return f"{base}-{quote}"
    return base


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


def _build_passthrough(venue: str, itype: InstrumentType, symbol: str, chain: str | None) -> str:
    """Wrap an already-fully-formed native/raw symbol as ``VENUE[-CHAIN]:TYPE:SYMBOL``.

    Bypasses every type-specific structured construction (expiry/strike
    reconstruction, fee-tier validation, etc.) — the caller is responsible
    for ``symbol`` already being in its final, correct form. This is the
    convention Tardis (batch CeFi/TradFi) and the CCXT live-mode adapter
    already use verbatim for dated derivatives whose native symbol already
    encodes expiry/strike/right (e.g. Deribit's ``BTC-9JUL26-56000-C``):
    ``VENUE:TYPE:RAW_NATIVE_ID``, case preserved as given rather than
    reconstructed from parts. Before this escape hatch existed,
    :func:`build_instrument_id` could only RECONSTRUCT FUTURE/OPTION ids from
    ``expiry_date``/``strike``/``option_right`` — exactly the reason the CCXT
    live-mode fix (``instruments-service@8544273d``) chose not to route
    through this module (see
    ``canonical_id_p0_ccxt_live_batch_divergence_2026_07_08.md``). DeFi
    symbols keep their on-chain case (delegates to :func:`_build_defi`);
    every other category is upper-cased for CeFi/TradFi normalisation.
    """
    if not symbol:
        msg = f"{itype.value} passthrough=True requires a non-empty symbol (the raw, already-formed native id)"
        raise ValueError(msg)
    if itype in _DEFI_TYPES:
        return _build_defi(venue, itype, symbol, chain)
    return f"{_venue_token(venue, chain)}:{itype.value}:{symbol.upper()}"


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
    passthrough: bool = False,
    margin_marker: str = "",
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
    passthrough:
        When ``True``, skip all type-specific structured construction and
        wrap ``symbol`` verbatim as ``VENUE[-CHAIN]:TYPE:SYMBOL`` (DeFi
        preserves on-chain case; everything else upper-cases) — see
        :func:`_build_passthrough`. Use this for raw exchange-native ids
        that already encode their own expiry/strike/right (the Tardis/CCXT
        convention for dated derivatives), instead of supplying
        ``expiry_date``/``strike``/``option_right`` for reconstruction.
    margin_marker:
        Operator-decided settlement-type suffix — ``"LIN"``/``"linear"`` or
        ``"INV"``/``"inverse"`` (any case) — embedded as ``@LIN``/``@INV``
        directly on the symbol segment for :attr:`InstrumentType.PERPETUAL`,
        :attr:`InstrumentType.FUTURE`, and :attr:`InstrumentType.OPTION`
        (``instrument_id_format_canonicalization_2026_07_08.md`` finding 1).
        Mutually exclusive with ``passthrough=True``. This supersedes the
        older ``quote_asset``/``margin_type`` word-form suffix for NEW
        callers — existing callers using ``quote_asset``/``margin_type``
        keep their unchanged output since this parameter defaults to ``""``.

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

    # FAIL LOUD instead of silently minting a double-wrapped id (operator ruling
    # 2026-07-20, canonical_path_oracle_blind_to_filename_stem_2026_07_20.md §7 —
    # "remove the silent build_instrument_id(venue, itype, symbol) catalogue-miss
    # fallback that mints double-wrapped VENUE:ITYPE:<raw wire> ids"). ``:`` is
    # this builder's OWN top-level ``VENUE:TYPE:SYMBOL`` field delimiter, so a
    # ``symbol`` carrying one is never well-formed input for any asset group
    # EXCEPT sports/prediction, whose ``symbol`` is itself a pre-built domain id
    # that legitimately embeds colons (see :func:`_build_sports_or_prediction`,
    # e.g. ``FOOTBALL:PINNACLE:MATCH_ODDS:...``). This is the exact shape a
    # catalogue-miss fallback that passes a raw wire symbol straight through
    # produces — e.g. Bitfinex's own colon-delimited funding-pair wire notation
    # (``ADAF0:USTF0``) reaching this function unresolved mints
    # ``BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0``, a double-wrapped id that
    # silently polluted the CeFi corpus. A caller that cannot resolve a symbol
    # against the catalogue/wire-map must not call this builder with the raw
    # wire form — it should either fail the row (``record_failed``) or route the
    # genuinely-unresolvable case through the UAC quarantine model
    # (:mod:`unified_api_contracts.canonical.quarantine`) instead.
    if instrument_type not in _SPORTS_AND_PREDICTION_TYPES and ":" in symbol:
        msg = (
            f"build_instrument_id: symbol {symbol!r} for instrument_type="
            f"{instrument_type.value} carries an embedded ':' — the canonical id's "
            "own VENUE:TYPE:SYMBOL delimiter. This is never well-formed input for a "
            "non-sports/prediction asset group; resolve the symbol against the "
            "catalogue/wire-map before calling this builder, or route a "
            "genuinely-unresolvable instrument through the UAC quarantine model "
            "(unified_api_contracts.canonical.quarantine) instead of building a "
            "malformed double-wrapped id."
        )
        raise ValueError(msg)

    if margin_marker:
        if passthrough:
            msg = "margin_marker is not supported together with passthrough=True"
            raise ValueError(msg)
        if instrument_type not in _MARGIN_MARKER_ELIGIBLE_TYPES:
            msg = (
                "margin_marker is only supported for PERPETUAL/FUTURE/OPTION, "
                f"got instrument_type={instrument_type.value}"
            )
            raise ValueError(msg)
        marker = _normalize_margin_marker(margin_marker)
        return _build_with_margin_marker(
            venue, instrument_type, symbol, marker, expiry_date, strike, option_right, quote_asset
        )

    if passthrough:
        return _build_passthrough(venue, instrument_type, symbol, chain)

    # CeFi simple (spot + perpetual + crypto-venue equity instruments)
    if instrument_type in (
        InstrumentType.SPOT_PAIR,
        InstrumentType.PERPETUAL,
        InstrumentType.EQUITY_PERP,
        InstrumentType.TOKENIZED_EQUITY,
    ):
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
        return _build_tradfi_cash(venue, instrument_type, symbol, quote_asset)

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


# ---------------------------------------------------------------------------
# Multi-leg combo/spread leg construction
# ---------------------------------------------------------------------------


def build_leg(
    venue: str,
    instrument_type: InstrumentType,
    symbol: str,
    *,
    side: Literal["BUY", "SELL"],
    ratio: int = 1,
    passthrough: bool = False,
    expiry_date: _dt.date | None = None,
    strike: Decimal | None = None,
    option_right: Literal["C", "P"] | None = None,
    chain: str | None = None,
    quote_asset: str = "",
    margin_type: str = "",
    margin_marker: str = "",
    include_venue: bool = True,
) -> InstrumentLeg:
    """Build one multi-leg combo/spread :class:`InstrumentLeg` via the shared builder.

    Extends — rather than reinvents — the existing
    :class:`~unified_api_contracts.internal.InstrumentLeg` infrastructure
    already used by ``databento/symbology.py``'s
    ``_parse_cme_calendar_spread_legs`` and both Deribit combo builders
    (``deribit_combo_adapter.py``, ``tardis/combos.py``), each of which today
    builds a leg's ``instrument_key`` with an ad hoc f-string (e.g.
    ``f"{venue}:FUTURE:{front}"`` or ``f"DERIBIT:{leg_name}"``) instead of
    going through :func:`build_instrument_id`. Routing leg construction
    through this function gives every leg the same validation and
    ``VENUE:TYPE:SYMBOL`` convention as a standalone instrument, and closes
    real drift like a leg missing its ``:TYPE:`` segment entirely.

    Args:
        side: ``"BUY"`` or ``"SELL"`` — matches :attr:`InstrumentLeg.side`.
        ratio: Leg ratio (e.g. ``2`` in a 1x2 ratio spread). Defaults to 1.
        passthrough: See :func:`build_instrument_id` — pass an already
            fully-formed native leg symbol (e.g. a Deribit
            ``instrument_name``) straight through instead of reconstructing
            it from ``expiry_date``/``strike``/``option_right``.
        include_venue: When ``False``, drop the leading ``VENUE:`` segment
            from the leg key, producing ``TYPE:SYMBOL`` instead of
            ``VENUE:TYPE:SYMBOL``. ``venue`` is still required (used to
            build the id internally, e.g. DeFi's ``VENUE-CHAIN`` composition)
            — only the OUTPUT prefix is omitted. For a combo already scoped
            to one venue at its own top-level ``VENUE:COMBO:...`` id,
            repeating the venue on every leg is redundant (the TradFi
            CBOE/VX combo-leg convention —
            ``canonical_id_p1_tradfi_combo_leg_canonicalization_2026_07_08.md``).
            Safe to strip unconditionally: every :func:`build_instrument_id`
            dispatch path formats its result as
            ``{_venue_token(...)}:{itype.value}:{symbol...}`` and
            :func:`_venue_token` never itself contains a ``:`` (DeFi's
            chain composition uses ``-``), so the leading segment up to the
            first ``:`` is always exactly the venue token.

    Examples
    --------
    CME calendar-spread front leg (raw exchange ticker passthrough, matching
    the real convention already used by ``_parse_cme_calendar_spread_legs``)::

        build_leg("CME", InstrumentType.FUTURE, "ESM6", side="BUY", passthrough=True)
        # → InstrumentLeg(instrument_key="CME:FUTURE:ESM6", side="BUY", ratio=1)

    Deribit combo leg::

        build_leg(
            "DERIBIT", InstrumentType.OPTION, "BTC-25DEC26-70000-C",
            side="SELL", ratio=2, passthrough=True,
        )
        # → InstrumentLeg(instrument_key="DERIBIT:OPTION:BTC-25DEC26-70000-C", side="SELL", ratio=2)

    Venue-less TradFi combo leg (matches the ``_build_leg_key`` convention
    ``databento/symbology.py`` used before this mode existed)::

        build_leg("CME", InstrumentType.FUTURE, "SP500", side="BUY", passthrough=True, include_venue=False)
        # → InstrumentLeg(instrument_key="FUTURE:SP500", side="BUY", ratio=1)
    """
    leg_key = build_instrument_id(
        venue,
        instrument_type,
        symbol,
        expiry_date=expiry_date,
        strike=strike,
        option_right=option_right,
        chain=chain,
        quote_asset=quote_asset,
        margin_type=margin_type,
        passthrough=passthrough,
        margin_marker=margin_marker,
    )
    if not include_venue:
        leg_key = leg_key.split(":", 1)[1]
    return InstrumentLeg(instrument_key=leg_key, side=side, ratio=ratio)


# ---------------------------------------------------------------------------
# One entry point, every asset group
# ---------------------------------------------------------------------------


def build_canonical_instrument_id(
    asset_group: AssetGroup | str,
    venue: str = "",
    instrument_type: InstrumentType | None = None,
    symbol: str = "",
    *,
    expiry_date: _dt.date | None = None,
    strike: Decimal | None = None,
    option_right: Literal["C", "P"] | None = None,
    chain: str | None = None,
    quote_asset: str = "",
    margin_type: str = "",
    passthrough: bool = False,
    margin_marker: str = "",
    league: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    fixture_date: str | None = None,
    fixture_time: str = "",
) -> str:
    """Single dispatch entry point for a canonical id, for ANY asset group.

    Operator decision, 2026-07-08 (`instrument_id_format_canonicalization_2026_07_08.md`):
    *"one builder for everything ... every asset group, every instrument
    type, can get its canonical instrument IDs, same with fixtures, just by
    filling in the right inputs."* Per-domain builders that each
    independently canonicalize are explicitly rejected — this function is
    the single call site every adapter (CeFi/DeFi/TradFi/Prediction/Sports)
    should route through; it never re-implements construction logic itself,
    it dispatches to the one shared implementation per asset group:

    - ``CEFI`` / ``DEFI`` / ``TRADFI`` / ``PREDICTION`` → :func:`build_instrument_id`
      (``VENUE:TYPE:SYMBOL``, ``VENUE-CHAIN:TYPE:SYMBOL`` for DeFi).
    - ``SPORTS`` → the sports domain builder
      (``canonical/domain/sports/canonical_ids.build_fixture_id``),
      producing ``LEAGUE:MATCHUP:DATE`` — **not** ``VENUE:TYPE:SYMBOL``. This
      is an intentional, separately operator-confirmed design decision
      ("sports doesn't have a clean TYPE/SYMBOL concept"), not a gap: a
      fixture is an event between two named participants on a date, not a
      type+symbol pair. Sports callers pass ``league``/``home_team``/
      ``away_team``/``fixture_date`` (and optional ``fixture_time``) instead
      of ``venue``/``instrument_type``/``symbol``.

    Args:
        asset_group: :class:`AssetGroup` or its lowercase string value
            (``"cefi"``, ``"defi"``, ``"tradfi"``, ``"sports"``,
            ``"prediction"``).
        venue: Required for every group except ``SPORTS``.
        instrument_type: Required for every group except ``SPORTS``.
        symbol, expiry_date, strike, option_right, chain, quote_asset,
        margin_type, passthrough: Forwarded verbatim to
            :func:`build_instrument_id` — see its docstring.
        league, home_team, away_team, fixture_date, fixture_time:
            ``SPORTS``-only — already-canonical entity ids (e.g. built via
            ``build_league_id``/``build_team_id``) and an ISO-ish date
            string. Forwarded to ``build_fixture_id``.

    Returns:
        The canonical instrument id (or fixture id, for ``SPORTS``).

    Raises:
        ValueError: If ``asset_group`` is not a valid :class:`AssetGroup`
            value, if a non-``SPORTS`` group is missing ``instrument_type``,
            or if ``SPORTS`` is missing any of ``league``/``home_team``/
            ``away_team``/``fixture_date``.

    Examples
    --------
    CeFi::

        build_canonical_instrument_id(AssetGroup.CEFI, "bybit", InstrumentType.PERPETUAL, "BTCUSDT")
        # → "BYBIT:PERPETUAL:BTCUSDT"

    DeFi::

        build_canonical_instrument_id(
            AssetGroup.DEFI, "aave_v3", InstrumentType.LENDING, "USDC", chain="arbitrum",
        )
        # → "AAVE_V3-ARBITRUM:LENDING:USDC"

    TradFi::

        build_canonical_instrument_id(
            AssetGroup.TRADFI, "cme", InstrumentType.FUTURE, "ES", expiry_date=date(2026, 6, 20),
        )
        # → "CME:FUTURE:ES-20260620"

    Sports (fixture, not VENUE:TYPE:SYMBOL)::

        build_canonical_instrument_id(
            "sports", league="ENG_PREMIER_LEAGUE", home_team="ARSENAL",
            away_team="CHELSEA", fixture_date="2026-03-22",
        )
        # → "ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322"
    """
    group = asset_group if isinstance(asset_group, AssetGroup) else AssetGroup(str(asset_group).lower())

    if group is AssetGroup.SPORTS:
        missing = [
            name
            for name, value in (
                ("league", league),
                ("home_team", home_team),
                ("away_team", away_team),
                ("fixture_date", fixture_date),
            )
            if not value
        ]
        if missing:
            msg = (
                "build_canonical_instrument_id: asset_group=sports requires "
                f"league, home_team, away_team, fixture_date — missing: {missing}. "
                "Sports keeps its own LEAGUE:MATCHUP:DATE scheme (operator-decided, "
                "not forced into VENUE:TYPE:SYMBOL) — see build_fixture_id()."
            )
            raise ValueError(msg)
        # Narrowed non-None by the `missing` check above.
        assert league is not None
        assert home_team is not None
        assert away_team is not None
        assert fixture_date is not None
        return _build_sports_fixture_id(league, home_team, away_team, fixture_date, fixture_time)

    if instrument_type is None:
        msg = f"build_canonical_instrument_id: asset_group={group.value} requires instrument_type"
        raise ValueError(msg)

    # DeFi SPOT_PAIR taxonomy hard-enforce (operator ruling 2026-07-18): a defi
    # SPOT_PAIR must be a two-token BASE-QUOTE — a single token is a SPOT_ASSET,
    # an AMM is a POOL/DEX_POOL/SOLANA_AMM_POOL. Rejects the misuse at the one
    # entry point rather than silently minting a wrong id.
    if group is AssetGroup.DEFI and instrument_type is InstrumentType.SPOT_PAIR:
        validate_defi_spot_pair_symbol(symbol)

    return build_instrument_id(
        venue,
        instrument_type,
        symbol,
        expiry_date=expiry_date,
        strike=strike,
        option_right=option_right,
        chain=chain,
        quote_asset=quote_asset,
        margin_type=margin_type,
        passthrough=passthrough,
        margin_marker=margin_marker,
    )
