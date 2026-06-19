# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAny=false, reportArgumentType=false, reportUnknownMemberType=false
"""Explicit Databento raw-symbol classifier (Phase 1.7).

Replaces the previous silent ``instrument_type = "future"`` default that
hid unparseable symbols. Every Databento raw symbol is classified into a
:class:`DatabentoClassification` record carrying the canonical
:class:`InstrumentType`, underlying root, expiry date (where applicable),
strike, option right, and a ``is_continuous`` flag for root-only codes
that MTDS must skip (continuous contracts are built internally, not
fetched from Databento).

Raises :class:`ValueError` for any symbol shape the classifier does not
understand — no silent fallbacks.

Symbol shapes handled:

* Continuous root codes — ``ES``, ``NQ``, ``CL`` (is_continuous=True).
* Dated futures — ``ESM6``, ``NQU5``, ``CLZ24`` (root + month + year).
* CME FX futures — ``6AM4`` (AUD Jun-2024), ``6EU4`` (EUR Sep-2024)
  (2-char ``6X`` root + month + single-digit year).
* CME futures options (short form) — ``E2AJ6 C6190`` (week/series root,
  month, year; separate call/put + strike token).
* OSI-packed equity options — ``AAPL  240119C00150000``.
* Equities — ``AAPL``, ``TSLA`` (1-5 alpha ticker).
* Indices — ``SPX``, ``NDX``, ``DJIA`` (known index set).
* Calendar spreads / combos — ``6AH5-6AM4``, ``ESM4-ESU4``
  (two valid Databento symbols joined by ``-``; both legs are
  re-classified individually and must parse).

Asset class hints (``"equity"`` / ``"etf"`` / ``"index"``) are accepted
for ambiguous tickers like ``SPY`` so callers can disambiguate EQUITY vs
ETF. Without a hint, such tickers default to EQUITY.
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final, Literal

from unified_api_contracts import (
    UNDERLYING_NORMALIZATION,
    ComboLeg,
    ComboStrategyType,
    InstrumentType,
    MultiLegInstrument,
)
from unified_api_contracts.registry import extract_es_options_cluster

logger = logging.getLogger(__name__)

__all__ = [
    "DatabentoClassification",
    "classify_databento_symbol",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# CME futures month codes → calendar month.
_CME_MONTH_MAP: Final[dict[str, int]] = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}

# Continuous futures root codes that MTDS builds itself — fetching these from
# Databento is a no-op and yields duplicate data.
_CONTINUOUS_FUTURE_ROOTS: Final[frozenset[str]] = frozenset(
    {"ES", "NQ", "CL", "GC", "SI", "NG", "ZN", "ZB", "ZT", "ZF", "RTY", "YM"}
)

# Known index tickers (TradFi indices — cash products, not futures/ETFs).
_INDEX_TICKERS: Final[frozenset[str]] = frozenset({"SPX", "NDX", "DJIA", "RUT", "VIX"})

# CME FX futures 2-char roots (``6A`` = AUD/USD, ``6E`` = EUR/USD, etc.).
# Shape is ``{ROOT2}{MONTH}{YEAR}`` where ROOT2 starts with ``6`` and is
# followed by a single currency letter. Expiries follow CME FX spec = second
# business day before the third Wednesday; we use the third Wednesday as the
# canonical listed date (the same convention used by instruments-service for
# FX futures metadata).
_CME_FX_FUT_ROOTS: Final[frozenset[str]] = frozenset(
    # AUD, GBP, CAD, EUR, JPY, BRL, MXN, NZD, RUB, CHF, ZAR — mirrors the
    # 11 6-prefix codes in UAC UNDERLYING_NORMALIZATION.
    {"6A", "6B", "6C", "6E", "6J", "6L", "6M", "6N", "6R", "6S", "6Z"}
)

# Dated future: ROOT(2-4 alpha) + MONTH(1 alpha from FGHJKMNQUVXZ) + YEAR(1-2 digit).
_DATED_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z]{2,4})([FGHJKMNQUVXZ])(\d{1,2})$")

# CME FX-future shape: leading ``6`` + single alpha currency letter + month + year.
# Example: ``6AM4`` = AUD Jun-2024, ``6EU4`` = EUR Sep-2024.
_CME_FX_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^(6[A-Z])([FGHJKMNQUVXZ])(\d{1,2})$")

# Cboe VX (VIX) future outright shape: ``VX/{MONTH}{YEAR}`` — the slash-delimited
# parent-resolved symbology Databento returns on the XCBF.PITCH dataset.
# Example: ``VX/M6`` = VX Jun-2026, ``VX/Z6`` = VX Dec-2026. Calendar spreads
# (``VX/N6:1:S - VX/Q6:1:B``) carry the ``:`` qualifier + ` - ` join — they are
# NOT outrights and fall through to the combo splitter (and are then dropped as
# non-classifiable legs, which is the intended behaviour for OHLCV capture).
_VX_FUTURE_RE: Final[re.Pattern[str]] = re.compile(r"^VX/([FGHJKMNQUVXZ])(\d{1,2})$")

# Calendar spread / combo: two or more valid Databento leg tokens joined
# by ``-``. Examples:
#   ``6AH5-6AM4``                   (2-leg calendar spread)
#   ``ESM4-ESU4``                   (2-leg calendar spread)
#   ``ESM4 C5500-ESU4 C5600``       (2-leg diagonal — leg tokens contain space)
#   ``ESH5-ESM5-ESU5``              (3-leg butterfly)
#   ``ESH5-ESM5-ESU5-ESZ5``         (4-leg condor)
# Databento never uses ``-`` inside a single-leg symbol (equities use ``.``,
# CME short options use a space), so ``-`` is an unambiguous leg separator.
_MULTI_LEG_RE: Final[re.Pattern[str]] = re.compile(r"^[^-].*-[^-].*$")

# Explicit combo-type prefixes emitted by CME (e.g. ``ES:BF U4-V4-X4``).
# Value is the :class:`ComboStrategyType` to assign when the prefix is
# present. The prefix is stripped before leg parsing; the underlying root
# appears before the ``:``.
_COMBO_PREFIX_TO_STRATEGY: Final[dict[str, ComboStrategyType]] = {
    "BF": ComboStrategyType.BUTTERFLY,
    "IC": ComboStrategyType.IRON_CONDOR,
    "IB": ComboStrategyType.IRON_BUTTERFLY,
    "CO": ComboStrategyType.CONDOR,
    "CL": ComboStrategyType.CALENDAR,
    "CA": ComboStrategyType.CALENDAR,
    "DG": ComboStrategyType.DIAGONAL,
    "VT": ComboStrategyType.VERTICAL,
    "ST": ComboStrategyType.STRADDLE,
    "SG": ComboStrategyType.STRANGLE,
    "RR": ComboStrategyType.RISK_REVERSAL,
    "RS": ComboStrategyType.RATIO_SPREAD,
    "BX": ComboStrategyType.BOX,
    "JR": ComboStrategyType.JELLY_ROLL,
    "CC": ComboStrategyType.COVERED_CALL,
    "PP": ComboStrategyType.PROTECTIVE_PUT,
    "CR": ComboStrategyType.COLLAR,
    "EF": ComboStrategyType.EFP,
    # CME Energy references (Henry Hub, Summer/Annual strips).
    "HH": ComboStrategyType.SPREAD,  # Henry Hub reference spread
    "SA": ComboStrategyType.SPREAD,  # Summer/Annual strip
    "WA": ComboStrategyType.SPREAD,  # Winter/Annual strip
    "QT": ComboStrategyType.SPREAD,  # Quarterly strip
    "MO": ComboStrategyType.SPREAD,  # Monthly strip
    "CS": ComboStrategyType.SPREAD,  # Crack spread
    "PK": ComboStrategyType.SPREAD,  # Peak / off-peak
    "OP": ComboStrategyType.SPREAD,  # Option package / option pair
    "SW": ComboStrategyType.SPREAD,  # Swap / swapped
}

# ``UNDERLYING:PREFIX LEGTOKENS…`` shape, e.g. ``ES:BF U4-V4-X4``.
_COMBO_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z0-9]{1,4}):([A-Z]{2})\s+(.+)$")

# Month+year tail (``U4``, ``M24``) used when a combo prefix is present
# and legs are expressed as bare tails relative to a shared root.
_MONTH_YEAR_TAIL_RE: Final[re.Pattern[str]] = re.compile(r"^([FGHJKMNQUVXZ])(\d{1,2})$")

# CME short option form: ROOT(2-5 alpha+digit) + MONTH + YEAR, space, then C/P + STRIKE.
# Example: ``E2AJ6 C6190`` → root=E2AJ, month=J (Apr), year=6 (2026), call, strike=6190.
_CME_SHORT_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^([A-Z0-9]{2,5})([FGHJKMNQUVXZ])(\d{1,2})\s+([CP])([0-9]+(?:\.[0-9]+)?)$"
)

# CME event-contract daily option (binary YES/NO settlement).
# Format: ROOT(EC + 1-4 chars) + MONTH + YEAR(1 digit) + DAY(2 digits), space, C/P + STRIKE.
# Example: ``ECBTCJ615 P74000`` → root=ECBTC, month=J (Apr), year=6 (2026), day=15,
# put, strike=74000. Distinct from _CME_SHORT_OPTION_RE because event contracts
# encode the day-of-month directly (ES daily options put day-of-week in the root
# instead — E1A=Mon..E5A=Fri). Coverage on Databento: 2025-09-28 onward.
_CME_EVENT_DAILY_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(EC[A-Z0-9]{1,4})([FGHJKMNQUVXZ])(\d)(\d{2})\s+([CP])([0-9]+(?:\.[0-9]+)?)$"
)

# OSI packed option: ROOT(1-6, right-padded with spaces) + YYMMDD + C/P + STRIKE(8 digits, price*1000).
# Example: ``AAPL  240119C00150000`` → AAPL Jan 19 2024 Call $150.00.
_OSI_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<root>[A-Z0-9]{1,6})\s*(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})(?P<cp>[CP])(?P<strike>\d{8})$"
)

# Plain equity ticker: 1-5 uppercase letters, optional class suffix like BRK.A.
_EQUITY_TICKER_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")

# ICE commodity futures shape: ``{ROOT} FM{MONTH}00{YY}[{QUALIFIER}]``.
# Examples:
#   ``BRN FMH0020``          (Brent March 2020)
#   ``G FMN0024``            (Gasoil July 2024)
#   ``CC FMN0024``           (Cocoa July 2024)
#   ``BRN FMH0020!``         (continuous/active marker)
#   ``BRN FMH0020_MD1``      (market-depth level-1 variant)
#   ``BRN FMH0020_MM1``      (market-maker variant)
#   ``BRN FMH0020_P``        (pending/posting variant)
#   ``BRN FMH0020_Z``        (close-auction variant)
# Month letter is CME/ICE standard (FGHJKMNQUVXZ). Year is 4-digit with a
# leading ``00`` padding — e.g. ``0020`` = 2020, ``0024`` = 2024.
_ICE_FUTURE_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z]{1,4})\s+FM([FGHJKMNQUVXZ])00(\d{2})([!_][A-Z0-9]*)?$")

# CME/ICE continuous-contract prefix: ``{ROOT}:{CODE}`` where CODE is a
# single letter (C=continuous, N=nearby, F=front) followed by a sequence
# number. Used as a bare symbol (``CL:C1``) or as a combo prefix
# (``CL:C1 HO-CL H0``). Letter variants observed: C, N, F, B.
_CONTINUOUS_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z]{1,4}):([CNFB]\d+)(?:\s+(.+))?$")

# CBOE user-defined strategy shape: ``UD:{VERSION}V:\s+{GLOBEX_CODE}\s+{ID}``.
# Example: ``UD:1V: GN 0113805462``. These are proprietary multi-leg
# structures (condors, butterflies, jelly rolls, etc.) where the leg
# breakdown is in Databento's definitions feed, not the symbol itself.
# We classify these as COMBO + strategy_type=CUSTOM with the strategy ID
# preserved as a single ComboLeg so downstream can resolve later.
_CBOE_UD_RE: Final[re.Pattern[str]] = re.compile(
    # User-defined strategy prefixes. Observed forms:
    #   ``UD:1V: GN 0113805462``      — version-numbered spaced
    #   ``UD:1V:CFO 0129826976``      — version-numbered compact alpha
    #   ``UD:1V: 12 0129837586``      — version-numbered numeric code
    #   ``UD:1V: 3W 0204816500``      — version-numbered mixed code
    #   ``UD:ZN: TL 0219823765``      — root-qualified (CME Treasury: ZN/ZF/ZT)
    #   ``UD:ZF: TL 0201003002``      — same class
    # First capture group is the qualifier (``\d+V`` version OR 2-4 alpha root).
    r"^UD:(\d+V|[A-Z]{2,4}):\s*([A-Z0-9]{1,4})\s+(\d+)$"
)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DatabentoClassification:
    """Structured classification of a Databento raw symbol.

    Attributes:
        instrument_type: Canonical :class:`InstrumentType` enum value.
        underlying: Root/underlying symbol. For single-leg instruments
            this is the raw Databento root (e.g. ``ES``, ``AAPL``). For
            combos, this is the shared root across all legs (e.g. ``ES``)
            when legs share an underlying, otherwise a ``-`` joined form
            (e.g. ``ES-NQ``).
        expiry_date: Expiry for dated derivatives (FUTURE, OPTION); None
            otherwise. For combos, the **near-leg** expiry (earliest)
            is stored so downstream callers can shard by expiry window.
        strike: Option strike price; None for non-options.
        option_right: ``"C"`` or ``"P"`` for options; None otherwise.
        is_continuous: True when the raw symbol is a root-only continuous
            contract code (e.g. ``ES``) — MTDS skips fetching these.
        leg_symbols: Raw Databento leg tokens for COMBO instruments.
            ``None`` for single-leg. Length is ``>= 2`` for combos.
        combo_strategy: :class:`ComboStrategyType` for COMBO instruments,
            derived from the Databento shape (``:BF`` → BUTTERFLY,
            ``:CL`` → CALENDAR, ``:IC`` → IRON_CONDOR, etc.) or inferred
            from leg arithmetic (2 legs → CALENDAR/VERTICAL,
            3 legs → BUTTERFLY, 4 legs → IRON_CONDOR).
        multileg: Full :class:`MultiLegInstrument` for combos — canonical
            representation with structured ``ComboLeg`` entries. ``None``
            for single-leg instruments.
        strikes: Ordered strikes for strike-anchored combos (butterflies,
            condors). Empty for non-strike combos.
        expiries: Ordered expiries for expiry-anchored combos (calendars,
            jelly rolls). Empty for non-expiry combos.
    """

    instrument_type: InstrumentType
    underlying: str
    expiry_date: _dt.date | None
    strike: Decimal | None
    option_right: Literal["C", "P"] | None
    is_continuous: bool
    leg_symbols: tuple[str, ...] | None = None
    combo_strategy: ComboStrategyType | None = None
    multileg: MultiLegInstrument | None = None
    strikes: tuple[Decimal, ...] = field(default_factory=tuple)
    expiries: tuple[_dt.date, ...] = field(default_factory=tuple)
    root_cluster: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _third_friday(year: int, month: int) -> _dt.date:
    """Return the third Friday of the given year/month (standard listed expiry)."""
    first = _dt.date(year, month, 1)
    # weekday(): Mon=0 ... Fri=4 ... Sun=6
    first_friday_day = 1 + (4 - first.weekday()) % 7
    return _dt.date(year, month, first_friday_day + 14)


def _third_wednesday(year: int, month: int) -> _dt.date:
    """Return the third Wednesday of the given year/month (CME FX futures expiry).

    CME FX futures formally settle on the second business day before the third
    Wednesday; we use the third Wednesday itself as the canonical listed date
    (matching the convention instruments-service records for FX futures).
    """
    first = _dt.date(year, month, 1)
    # weekday(): Mon=0 ... Wed=2 ... Sun=6
    first_wednesday_day = 1 + (2 - first.weekday()) % 7
    return _dt.date(year, month, first_wednesday_day + 14)


def _vx_future_expiry(year: int, month: int) -> _dt.date:
    """Return the VIX-future (VX) final-settlement date for a contract month.

    Cboe VX futures settle on the Wednesday that is **30 days before** the third
    Friday of the calendar month **immediately following** the contract month
    (i.e. 30 days before the standard SPX-option expiration of the next month).
    This is the canonical listed expiry the instruments-service catalogue records
    for VX contracts, so the classifier MUST reproduce it for the instrument_id to
    match (a naive third-Friday would mint a mismatched id).
    """
    nxt_year = year + 1 if month == 12 else year
    nxt_month = 1 if month == 12 else month + 1
    return _third_friday(nxt_year, nxt_month) - _dt.timedelta(days=30)


def _expand_two_digit_year(year_token: str) -> int:
    """Expand a 1- or 2-digit year token into a four-digit year.

    Databento month-code years are typically single-digit (``6`` → 2026) or
    two-digit (``24`` → 2024). This function uses a fixed 2020 decade anchor
    for single digits and 2000 anchor for two digits, matching the
    CME/Databento convention used elsewhere in this codebase.
    """
    if len(year_token) == 1:
        return 2020 + int(year_token)
    return 2000 + int(year_token)


# ---------------------------------------------------------------------------
# Classification entry point
# ---------------------------------------------------------------------------


def _classify_databento_combo(symbol: str, asset_class_hint: str | None) -> DatabentoClassification | None:
    """Combo / multi-leg Databento symbol shapes (decision 338 refactor).

    Extracted from :func:`classify_databento_symbol` to keep that dispatcher
    under the function-size limit. Tries, in order, CBOE user-defined
    strategies, prefix-annotated combos, continuous-contract prefix combos,
    and generic N-leg combos. Returns ``None`` when no combo shape matches.
    """
    # 0-pre. CBOE user-defined strategy (``UD:1V: GN 0113805462``). CBOE
    #         emits these as opaque IDs whose leg breakdown lives in the
    #         Databento definitions feed; we classify as COMBO + CUSTOM
    #         and preserve the strategy ID for downstream resolution.
    ud_match = _CBOE_UD_RE.match(symbol)
    if ud_match:
        version = ud_match.group(1)
        globex_code = ud_match.group(2)
        strategy_id = ud_match.group(3)
        leg = ComboLeg(
            instrument_id=f"CBOE:UD:{version}V:{globex_code}:{strategy_id}",
            direction="buy",
            ratio=1,
            venue="CBOE",
        )
        multileg = MultiLegInstrument(
            venue="CBOE",
            strategy_type=ComboStrategyType.CUSTOM,
            underlying=globex_code,
            legs=[leg],
            block_trade_only=False,
            description=f"CBOE user-defined strategy v{version} ({globex_code}) id={strategy_id}",
        )
        return DatabentoClassification(
            instrument_type=InstrumentType.COMBO,
            underlying=globex_code,
            expiry_date=None,
            strike=None,
            option_right=None,
            is_continuous=False,
            leg_symbols=(strategy_id,),
            combo_strategy=ComboStrategyType.CUSTOM,
            multileg=multileg,
        )

    # 0a. Prefix-annotated combo (``UNDERLYING:PREFIX LEGTAILS``), e.g.
    #     ``ES:BF U4-V4-X4`` (3-leg butterfly on ES) or ``ES:IC U4-V4-X4-Z4``
    #     (iron condor). The prefix yields an explicit ComboStrategyType;
    #     legs are expanded against the shared root and classified.
    prefix_match = _COMBO_PREFIX_RE.match(symbol)
    if prefix_match:
        root = prefix_match.group(1)
        prefix = prefix_match.group(2)
        leg_tail = prefix_match.group(3)
        # Unknown combo prefix \u2192 treat as CUSTOM rather than raise.
        # Databento introduces new prefixes over time; classify liberally
        # and let downstream CUSTOM policy decide whether to trade them.
        strategy = _COMBO_PREFIX_TO_STRATEGY.get(prefix, ComboStrategyType.CUSTOM)
        # Leg expansion may still fail on non-month-year tail shapes; if
        # so, emit a single synthetic leg preserving the raw tail so the
        # row isn't dropped (shard isolation intent).
        try:
            expanded_legs = tuple(_expand_prefixed_leg(root, tok) for tok in leg_tail.split("-"))
            return _build_combo_classification(expanded_legs, asset_class_hint, strategy_override=strategy)
        except ValueError:
            leg = ComboLeg(
                instrument_id=f"{root}:{prefix} {leg_tail}",
                direction="buy",
                ratio=1,
                venue="CME",
            )
            multileg = MultiLegInstrument(
                venue="CME",
                strategy_type=strategy,
                underlying=root,
                legs=[leg],
                block_trade_only=False,
                description=f"CME prefix-combo (unclassifiable leg tail): {symbol}",
            )
            return DatabentoClassification(
                instrument_type=InstrumentType.COMBO,
                underlying=root,
                expiry_date=None,
                strike=None,
                option_right=None,
                is_continuous=False,
                leg_symbols=(leg_tail,),
                combo_strategy=strategy,
                multileg=multileg,
            )

    # 0b-pre. CME/ICE continuous-contract prefix combo form (``CL:C1 HO-CL H0``).
    #          Must fire BEFORE the generic ``-`` leg splitter so the
    #          annotated body isn't split across the continuous marker.
    cont_prefix_match = _CONTINUOUS_PREFIX_RE.match(symbol)
    if cont_prefix_match and cont_prefix_match.group(3):
        cont_root = cont_prefix_match.group(1)
        cont_code = cont_prefix_match.group(2)
        cont_body = cont_prefix_match.group(3)
        leg = ComboLeg(
            instrument_id=f"{cont_root}:{cont_code} {cont_body}",
            direction="buy",
            ratio=1,
            venue="CME",
        )
        multileg = MultiLegInstrument(
            venue="CME",
            strategy_type=ComboStrategyType.SPREAD,
            underlying=cont_root,
            legs=[leg],
            block_trade_only=False,
            description=f"CME continuous-contract combo: {symbol}",
        )
        return DatabentoClassification(
            instrument_type=InstrumentType.COMBO,
            underlying=cont_root,
            expiry_date=None,
            strike=None,
            option_right=None,
            is_continuous=False,
            leg_symbols=(cont_body,),
            combo_strategy=ComboStrategyType.SPREAD,
            multileg=multileg,
        )

    # 0b. Generic N-leg combo (``LEG1-LEG2[-LEG3…]``). A dash is not used
    #     inside any single Databento symbol shape (equities use ``.``,
    #     CME short options use a space), so ``-`` is an unambiguous leg
    #     separator.
    if _MULTI_LEG_RE.match(symbol) and "-" in symbol:
        legs_raw = tuple(symbol.split("-"))
        if len(legs_raw) >= 2 and all(tok for tok in legs_raw):
            return _build_combo_classification(legs_raw, asset_class_hint, strategy_override=None)

    return None


def _classify_databento_option(symbol: str) -> DatabentoClassification | None:
    """Option Databento symbol shapes (decision 338 refactor).

    Extracted from :func:`classify_databento_symbol`. Tries, in order,
    OSI-packed equity options, CME event-contract daily options, and CME
    short-form options. Returns ``None`` when no option shape matches.
    """
    # 1. OSI-packed option (equity options via OPRA) — check first, very specific.
    osi_match = _OSI_OPTION_RE.match(symbol.replace(" ", ""))
    if osi_match and len(symbol) >= 15:
        # Require the root+padding to preserve space-padding OR fit within 6 chars.
        # The compact regex matches ``AAPL240119C00150000`` too, which is acceptable.
        year = 2000 + int(osi_match.group("yy"))
        month = int(osi_match.group("mm"))
        day = int(osi_match.group("dd"))
        strike = Decimal(osi_match.group("strike")) / Decimal("1000")
        return DatabentoClassification(
            instrument_type=InstrumentType.OPTION,
            underlying=osi_match.group("root"),
            expiry_date=_dt.date(year, month, day),
            strike=strike,
            option_right="C" if osi_match.group("cp") == "C" else "P",
            is_continuous=False,
        )

    # 1b. CME event-contract daily option (``ECBTCJ615 P74000``).
    #     Tried before _CME_SHORT_OPTION_RE because event contracts have an
    #     extra day-of-month digit pair after the year that would otherwise
    #     fail the short-form regex (which only allows 1-2 digit year).
    event_match = _CME_EVENT_DAILY_OPTION_RE.match(symbol)
    if event_match:
        root = event_match.group(1)
        month = _CME_MONTH_MAP[event_match.group(2)]
        year = _expand_two_digit_year(event_match.group(3))
        day = int(event_match.group(4))
        option_right: Literal["C", "P"] = "C" if event_match.group(5) == "C" else "P"
        strike = Decimal(event_match.group(6))
        # Keep the full EC-prefixed root as the underlying so event contracts
        # partition separately from standard options on the same base asset
        # (ECES → underlying=ECES, distinct from ES.OPT → underlying=ES).
        # The UAC DatabentoInstrumentDef.base_asset field captures the
        # underlying base ("BTC", "SP500", "GOLD") for cross-instrument joins.
        return DatabentoClassification(
            instrument_type=InstrumentType.OPTION,
            underlying=root,
            expiry_date=_dt.date(year, month, day),
            strike=strike,
            option_right=option_right,
            is_continuous=False,
        )

    # 2. CME short-form option (``E2AJ6 C6190``).
    cme_opt_match = _CME_SHORT_OPTION_RE.match(symbol)
    if cme_opt_match:
        root = cme_opt_match.group(1)
        month = _CME_MONTH_MAP[cme_opt_match.group(2)]
        year = _expand_two_digit_year(cme_opt_match.group(3))
        option_right: Literal["C", "P"] = "C" if cme_opt_match.group(4) == "C" else "P"
        strike = Decimal(cme_opt_match.group(5))
        # Underlying for CME options is the futures root — strip leading
        # week/series digits (``E2AJ`` → ``ES`` via known prefixes) by
        # falling back to the first 2 alpha characters when a recognised
        # CME root (ES, NQ, CL, GC, NG) is embedded. Otherwise keep the
        # option's own root which callers can remap via UAC.
        underlying = _derive_cme_option_underlying(root)
        return DatabentoClassification(
            instrument_type=InstrumentType.OPTION,
            underlying=underlying,
            expiry_date=_third_friday(year, month),
            strike=strike,
            option_right=option_right,
            is_continuous=False,
            root_cluster=extract_es_options_cluster(symbol),
        )

    return None


def classify_databento_symbol(
    raw_symbol: str,
    asset_class_hint: str | None = None,
) -> DatabentoClassification:
    """Classify a raw Databento symbol into a structured record.

    Args:
        raw_symbol: The raw symbol string as returned by Databento
            (e.g. ``ESM6``, ``E2AJ6 C6190``, ``AAPL``).
        asset_class_hint: Optional hint to disambiguate equity vs ETF vs
            index for symbols that are ambiguous from shape alone
            (``SPY``, ``QQQ``). Accepted values: ``"equity"``, ``"etf"``,
            ``"index"``. Any other value is ignored.

    Returns:
        A :class:`DatabentoClassification` describing the symbol.

    Raises:
        ValueError: If the symbol is empty or cannot be classified.

    Dispatch order (preserved across the 2026-06-16 helper extraction):
    combo forms → option forms → FX future → dated future → continuous
    future → index → ICE future → bare continuous → equity/ETF.
    """
    if not raw_symbol or not raw_symbol.strip():
        msg = "raw_symbol must be a non-empty string"
        raise ValueError(msg)

    symbol = raw_symbol.strip().upper()
    hint = (asset_class_hint or "").strip().lower() or None

    # 0. Combo / multi-leg shapes (CBOE UD, prefix-combo, continuous-prefix
    #    combo, generic N-leg) — must precede the single-instrument shapes.
    combo = _classify_databento_combo(symbol, asset_class_hint)
    if combo is not None:
        return combo

    # 1-2. Option shapes (OSI-packed, CME event-daily, CME short-form).
    option = _classify_databento_option(symbol)
    if option is not None:
        return option

    # 2b. CME FX future (``6AM4``, ``6EU4``). The 2-char root starts with
    #     ``6`` so it does not match the alpha-only ``_DATED_FUT_RE``. FX
    #     futures expire on the third Wednesday of the contract month.
    fx_match = _CME_FX_FUT_RE.match(symbol)
    if fx_match and fx_match.group(1) in _CME_FX_FUT_ROOTS:
        fx_root = fx_match.group(1)
        fx_month = _CME_MONTH_MAP[fx_match.group(2)]
        fx_year = _expand_two_digit_year(fx_match.group(3))
        return DatabentoClassification(
            instrument_type=InstrumentType.FUTURE,
            underlying=fx_root,
            expiry_date=_third_wednesday(fx_year, fx_month),
            strike=None,
            option_right=None,
            is_continuous=False,
        )

    # 2c. Cboe VX (VIX) future outright (``VX/M6``, ``VX/Z6``) on XCBF.PITCH.
    #     Slash-delimited so it never matches the alpha-only _DATED_FUT_RE; VX
    #     settles 30 days before the next month's third Friday (not third Friday).
    vx_match = _VX_FUTURE_RE.match(symbol)
    if vx_match:
        vx_month = _CME_MONTH_MAP[vx_match.group(1)]
        vx_year = _expand_two_digit_year(vx_match.group(2))
        return DatabentoClassification(
            instrument_type=InstrumentType.FUTURE,
            underlying="VX",
            expiry_date=_vx_future_expiry(vx_year, vx_month),
            strike=None,
            option_right=None,
            is_continuous=False,
        )

    # 3. Dated future (``ESM6``, ``NQU24``).
    fut_match = _DATED_FUT_RE.match(symbol)
    if fut_match:
        root = fut_match.group(1)
        month = _CME_MONTH_MAP[fut_match.group(2)]
        year = _expand_two_digit_year(fut_match.group(3))
        return DatabentoClassification(
            instrument_type=InstrumentType.FUTURE,
            underlying=root,
            expiry_date=_third_friday(year, month),
            strike=None,
            option_right=None,
            is_continuous=False,
        )

    # 4. Continuous futures (root only, no month/year).
    if symbol in _CONTINUOUS_FUTURE_ROOTS:
        return DatabentoClassification(
            instrument_type=InstrumentType.FUTURE,
            underlying=symbol,
            expiry_date=None,
            strike=None,
            option_right=None,
            is_continuous=True,
        )

    # 5. Indices (known cash-index tickers).
    if symbol in _INDEX_TICKERS:
        return DatabentoClassification(
            instrument_type=InstrumentType.INDEX,
            underlying=symbol,
            expiry_date=None,
            strike=None,
            option_right=None,
            is_continuous=False,
        )

    # 5b. ICE commodity future (``BRN FMH0020``, ``G FMN0024``, ``CC FMN0024``).
    #     ``FM`` is ICE's futures-monthly series prefix. Year encoding is
    #     ``00{YY}`` → 20YY. Optional qualifier suffix (``!``, ``_MD1``,
    #     ``_MM1``, ``_P``, ``_SD1``, ``_Z``) marks a venue-specific
    #     variant of the same base contract; we preserve it in the
    #     underlying string so dedup downstream can merge or keep split.
    ice_match = _ICE_FUTURE_RE.match(symbol)
    if ice_match:
        ice_root = ice_match.group(1)
        ice_month = _CME_MONTH_MAP[ice_match.group(2)]
        ice_year = 2000 + int(ice_match.group(3))
        qualifier = ice_match.group(4) or ""
        underlying = f"{ice_root}{qualifier}" if qualifier else ice_root
        return DatabentoClassification(
            instrument_type=InstrumentType.FUTURE,
            underlying=underlying,
            expiry_date=_third_friday(ice_year, ice_month),
            strike=None,
            option_right=None,
            is_continuous=False,
        )

    # 5c. CME/ICE bare continuous-contract future (``CL:C1``, ``NG:N1``).
    #     The combo-body form (``CL:C1 HO-CL H0``) is handled earlier at
    #     step 0b-pre before the ``-`` leg splitter runs.
    cont_match = _CONTINUOUS_PREFIX_RE.match(symbol)
    if cont_match and cont_match.group(3) is None:
        return DatabentoClassification(
            instrument_type=InstrumentType.FUTURE,
            underlying=cont_match.group(1),
            expiry_date=None,
            strike=None,
            option_right=None,
            is_continuous=True,
        )

    # 6. Equity / ETF tickers — plain alpha roots. Hint resolves ETF vs EQUITY
    #    when ambiguous (``SPY`` is an ETF; without hint we default to EQUITY
    #    and document the tradeoff).
    if _EQUITY_TICKER_RE.match(symbol):
        if hint == "etf":
            itype = InstrumentType.ETF
        elif hint == "index":
            itype = InstrumentType.INDEX
        else:
            # Default — documented. Callers with reference data must pass hint.
            itype = InstrumentType.EQUITY
        return DatabentoClassification(
            instrument_type=itype,
            underlying=symbol,
            expiry_date=None,
            strike=None,
            option_right=None,
            is_continuous=False,
        )

    msg = f"Cannot classify Databento symbol: {raw_symbol!r}"
    raise ValueError(msg)


def _expand_prefixed_leg(root: str, leg_tail: str) -> str:
    """Expand a prefix-combo leg token relative to its shared root.

    Given a combo like ``ES:BF U4-V4-X4``, each leg tail (``U4``, ``V4``,
    ``X4``) must be re-combined with the shared root (``ES``) to form a
    valid dated-future symbol (``ESU4``). Leg tokens that already contain
    the root or are richer option/future shapes pass through unchanged.
    """
    tail = leg_tail.strip().upper()
    if _MONTH_YEAR_TAIL_RE.match(tail):
        return f"{root}{tail}"
    # Already a full leg token (e.g. ``ESU4``, ``ESU4 C5500``) — pass through.
    return tail


def _infer_combo_strategy_from_legs(leg_cls: tuple[DatabentoClassification, ...]) -> ComboStrategyType:
    """Infer a :class:`ComboStrategyType` from pre-classified legs.

    Fallback when Databento does not emit an explicit ``:BF``/``:IC``
    prefix. Rules:

    * 2 legs, both FUTURE same underlying, different expiries → CALENDAR.
    * 2 legs, both OPTION same underlying/expiry, different strikes →
      VERTICAL.
    * 2 legs, both OPTION same underlying, different expiries →
      DIAGONAL.
    * 3 legs, all OPTION same underlying/expiry, strikes A-B-C with
      evenly spaced centre → BUTTERFLY.
    * 4 legs, mixed calls/puts same underlying/expiry → IRON_CONDOR.
    * Otherwise CUSTOM.
    """
    if len(leg_cls) == 2:
        leg1, leg2 = leg_cls
        if (
            leg1.instrument_type is InstrumentType.FUTURE
            and leg2.instrument_type is InstrumentType.FUTURE
            and leg1.underlying == leg2.underlying
            and leg1.expiry_date != leg2.expiry_date
        ):
            return ComboStrategyType.CALENDAR
        if (
            leg1.instrument_type is InstrumentType.OPTION
            and leg2.instrument_type is InstrumentType.OPTION
            and leg1.underlying == leg2.underlying
        ):
            if leg1.expiry_date == leg2.expiry_date:
                return ComboStrategyType.VERTICAL
            return ComboStrategyType.DIAGONAL
        return ComboStrategyType.SPREAD
    if len(leg_cls) == 3 and all(leg.instrument_type is InstrumentType.OPTION for leg in leg_cls):
        return ComboStrategyType.BUTTERFLY
    if len(leg_cls) == 3 and all(leg.instrument_type is InstrumentType.FUTURE for leg in leg_cls):
        return ComboStrategyType.BUTTERFLY
    if len(leg_cls) == 4:
        return ComboStrategyType.IRON_CONDOR
    return ComboStrategyType.CUSTOM


def _shared_underlying(leg_cls: tuple[DatabentoClassification, ...]) -> str:
    """Return the shared underlying across legs, or ``-``-joined form.

    Human-readable via :func:`normalize_underlying` when the shared root
    is a known CME/ICE futures code (e.g. ``ES`` → ``SP500``).
    """
    unders = {leg.underlying for leg in leg_cls}
    if len(unders) == 1:
        raw = next(iter(unders))
        if raw in UNDERLYING_NORMALIZATION:
            return UNDERLYING_NORMALIZATION[raw]
        return raw
    # Multi-underlying combo — join unique roots, normalising known codes.
    normalized = [UNDERLYING_NORMALIZATION.get(leg.underlying, leg.underlying) for leg in leg_cls]
    seen: list[str] = []
    for name in normalized:
        if name not in seen:
            seen.append(name)
    return "-".join(seen)


def _build_combo_classification(
    legs_raw: tuple[str, ...],
    asset_class_hint: str | None,
    strategy_override: ComboStrategyType | None,
) -> DatabentoClassification:
    """Classify each leg, derive the combo strategy, and return the combo.

    Each leg is re-classified via :func:`classify_databento_symbol`
    recursively — every leg must parse or we fail loud (no silent skips).
    """
    if len(legs_raw) < 2:
        msg = f"COMBO requires at least 2 legs, got {legs_raw!r}"
        raise ValueError(msg)
    leg_cls = tuple(classify_databento_symbol(tok, asset_class_hint=asset_class_hint) for tok in legs_raw)

    strategy = strategy_override or _infer_combo_strategy_from_legs(leg_cls)

    expiry_dates = [leg.expiry_date for leg in leg_cls if leg.expiry_date is not None]
    near_expiry: _dt.date | None = min(expiry_dates) if expiry_dates else None

    strikes = tuple(sorted({leg.strike for leg in leg_cls if leg.strike is not None}))
    expiries = tuple(sorted({leg.expiry_date for leg in leg_cls if leg.expiry_date is not None}))

    underlying = _shared_underlying(leg_cls)

    # Build the canonical MultiLegInstrument. Leg direction is unknown at
    # the symbol level (Databento doesn't encode BUY/SELL in the string);
    # we set each leg to ``buy`` with ratio 1 as a sane default — callers
    # with trade-level data can override.
    combo_legs = [
        ComboLeg(
            instrument_id=leg_raw,
            direction="buy",
            ratio=1,
            venue="CME",
        )
        for leg_raw in legs_raw
    ]
    multileg = MultiLegInstrument(
        venue="CME",
        strategy_type=strategy,
        underlying=underlying,
        legs=combo_legs,
        block_trade_only=False,
    )

    return DatabentoClassification(
        instrument_type=InstrumentType.COMBO,
        underlying=underlying,
        expiry_date=near_expiry,
        strike=None,
        option_right=None,
        is_continuous=False,
        leg_symbols=legs_raw,
        combo_strategy=strategy,
        multileg=multileg,
        strikes=strikes,
        expiries=expiries,
    )


def _derive_cme_option_underlying(option_root: str) -> str:
    """Map a CME option root (``E2AJ``, ``EW2``, ``OG``) to a futures underlying.

    This is a conservative mapping — when the option root embeds a known
    futures root, we return that root. Otherwise we return the option root
    itself so callers can perform their own UAC-backed remap.
    """
    # Common CME option → future root prefixes. Kept small on purpose; the UAC
    # instrument registry is the SSOT for the full mapping.
    known_prefixes: Final[tuple[tuple[str, str], ...]] = (
        ("E2", "ES"),  # ES weekly options
        ("EW", "ES"),  # ES Wednesday options
        ("E1", "ES"),
        ("E3", "ES"),
        ("E4", "ES"),
        ("E5", "ES"),
        ("NQ", "NQ"),
        ("OG", "GC"),  # Gold options
        ("LO", "CL"),  # Crude options
        ("ON", "NG"),  # NG options
    )
    for prefix, underlying in known_prefixes:
        if option_root.startswith(prefix):
            return underlying
    return option_root
