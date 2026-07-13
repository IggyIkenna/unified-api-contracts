"""Symbol-shape rule tables for the Databento raw-symbol classifier.

Extracted from :mod:`databento_classifier` (which exceeded the 900-line file
ceiling) — pure data (regexes, month/prefix maps, ticker sets), no dispatch
logic. Names are module-public (no leading underscore) since
:mod:`databento_classifier` imports them across the module boundary; the
classifier's own public API (:class:`DatabentoClassification`,
:func:`classify_databento_symbol`) is unaffected by this split.
"""

from __future__ import annotations

import re
from typing import Final

from unified_api_contracts import ComboStrategyType

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# CME futures month codes → calendar month.
CME_MONTH_MAP: Final[dict[str, int]] = {
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
CONTINUOUS_FUTURE_ROOTS: Final[frozenset[str]] = frozenset(
    {"ES", "NQ", "CL", "GC", "SI", "NG", "ZN", "ZB", "ZT", "ZF", "RTY", "YM"}
)

# Known index tickers (TradFi indices — cash products, not futures/ETFs).
INDEX_TICKERS: Final[frozenset[str]] = frozenset({"SPX", "NDX", "DJIA", "RUT", "VIX"})

# CME FX futures 2-char roots (``6A`` = AUD/USD, ``6E`` = EUR/USD, etc.).
# Shape is ``{ROOT2}{MONTH}{YEAR}`` where ROOT2 starts with ``6`` and is
# followed by a single currency letter. Expiries follow CME FX spec = second
# business day before the third Wednesday; we use the third Wednesday as the
# canonical listed date (the same convention used by instruments-service for
# FX futures metadata).
CME_FX_FUT_ROOTS: Final[frozenset[str]] = frozenset(
    # AUD, GBP, CAD, EUR, JPY, BRL, MXN, NZD, RUB, CHF, ZAR — mirrors the
    # 11 6-prefix codes in UAC UNDERLYING_NORMALIZATION.
    {"6A", "6B", "6C", "6E", "6J", "6L", "6M", "6N", "6R", "6S", "6Z"}
)

# Dated future: ROOT(2-4 alpha) + MONTH(1 alpha from FGHJKMNQUVXZ) + YEAR(1-2 digit).
DATED_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z]{2,4})([FGHJKMNQUVXZ])(\d{1,2})$")

# CME FX-future shape: leading ``6`` + single alpha currency letter + month + year.
# Example: ``6AM4`` = AUD Jun-2024, ``6EU4`` = EUR Sep-2024.
CME_FX_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^(6[A-Z])([FGHJKMNQUVXZ])(\d{1,2})$")

# Cboe VX (VIX) future outright shape: ``VX/{MONTH}{YEAR}`` — the slash-delimited
# parent-resolved symbology Databento returns on the XCBF.PITCH dataset.
# Example: ``VX/M6`` = VX Jun-2026, ``VX/Z6`` = VX Dec-2026. Calendar spreads
# (``VX/N6:1:S - VX/Q6:1:B``) carry the ``:`` qualifier + ` - ` join — they are
# NOT outrights and fall through to the combo splitter (and are then dropped as
# non-classifiable legs, which is the intended behaviour for OHLCV capture).
VX_FUTURE_RE: Final[re.Pattern[str]] = re.compile(r"^VX/([FGHJKMNQUVXZ])(\d{1,2})$")

# Calendar spread / combo: two or more valid Databento leg tokens joined
# by ``-``. Examples:
#   ``6AH5-6AM4``                   (2-leg calendar spread)
#   ``ESM4-ESU4``                   (2-leg calendar spread)
#   ``ESM4 C5500-ESU4 C5600``       (2-leg diagonal — leg tokens contain space)
#   ``ESH5-ESM5-ESU5``              (3-leg butterfly)
#   ``ESH5-ESM5-ESU5-ESZ5``         (4-leg condor)
# Databento never uses ``-`` inside a single-leg symbol (equities use ``.``,
# CME short options use a space), so ``-`` is an unambiguous leg separator.
MULTI_LEG_RE: Final[re.Pattern[str]] = re.compile(r"^[^-].*-[^-].*$")

# Explicit combo-type prefixes emitted by CME (e.g. ``ES:BF U4-V4-X4``).
# Value is the :class:`ComboStrategyType` to assign when the prefix is
# present. The prefix is stripped before leg parsing; the underlying root
# appears before the ``:``.
COMBO_PREFIX_TO_STRATEGY: Final[dict[str, ComboStrategyType]] = {
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
COMBO_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z0-9]{1,4}):([A-Z]{2})\s+(.+)$")

# Month+year tail (``U4``, ``M24``) used when a combo prefix is present
# and legs are expressed as bare tails relative to a shared root.
MONTH_YEAR_TAIL_RE: Final[re.Pattern[str]] = re.compile(r"^([FGHJKMNQUVXZ])(\d{1,2})$")

# CME short option form: ROOT(2-5 alpha+digit) + MONTH + YEAR, space, then C/P + STRIKE.
# Example: ``E2AJ6 C6190`` → root=E2AJ, month=J (Apr), year=6 (2026), call, strike=6190.
CME_SHORT_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^([A-Z0-9]{2,5})([FGHJKMNQUVXZ])(\d{1,2})\s+([CP])([0-9]+(?:\.[0-9]+)?)$"
)

# CME event-contract daily option (binary YES/NO settlement).
# Format: ROOT(EC + 1-4 chars) + MONTH + YEAR(1 digit) + DAY(2 digits), space, C/P + STRIKE.
# Example: ``ECBTCJ615 P74000`` → root=ECBTC, month=J (Apr), year=6 (2026), day=15,
# put, strike=74000. Distinct from _CME_SHORT_OPTION_RE because event contracts
# encode the day-of-month directly (ES daily options put day-of-week in the root
# instead — E1A=Mon..E5A=Fri). Coverage on Databento: 2025-09-28 onward.
CME_EVENT_DAILY_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(EC[A-Z0-9]{1,4})([FGHJKMNQUVXZ])(\d)(\d{2})\s+([CP])([0-9]+(?:\.[0-9]+)?)$"
)

# OSI packed option: ROOT(1-6, right-padded with spaces) + YYMMDD + C/P + STRIKE(8 digits, price*1000).
# Example: ``AAPL  240119C00150000`` → AAPL Jan 19 2024 Call $150.00.
OSI_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<root>[A-Z0-9]{1,6})\s*(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})(?P<cp>[CP])(?P<strike>\d{8})$"
)

# Plain equity ticker: 1-5 uppercase letters, optional class suffix like BRK.A.
EQUITY_TICKER_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")

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
ICE_FUTURE_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z]{1,4})\s+FM([FGHJKMNQUVXZ])00(\d{2})([!_][A-Z0-9]*)?$")

# CME/ICE continuous-contract prefix: ``{ROOT}:{CODE}`` where CODE is a
# single letter (C=continuous, N=nearby, F=front) followed by a sequence
# number. Used as a bare symbol (``CL:C1``) or as a combo prefix
# (``CL:C1 HO-CL H0``). Letter variants observed: C, N, F, B.
CONTINUOUS_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z]{1,4}):([CNFB]\d+)(?:\s+(.+))?$")

# CBOE user-defined strategy shape: ``UD:{VERSION}V:\s+{GLOBEX_CODE}\s+{ID}``.
# Example: ``UD:1V: GN 0113805462``. These are proprietary multi-leg
# structures (condors, butterflies, jelly rolls, etc.) where the leg
# breakdown is in Databento's definitions feed, not the symbol itself.
# We classify these as COMBO + strategy_type=CUSTOM with the strategy ID
# preserved as a single ComboLeg so downstream can resolve later.
CBOE_UD_RE: Final[re.Pattern[str]] = re.compile(
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
