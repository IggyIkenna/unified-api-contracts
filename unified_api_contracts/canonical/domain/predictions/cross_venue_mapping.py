"""Per-instrument Kalshi ↔ Polymarket SAME-MARKET matcher.

The cqg classifier (:mod:`classifiers`) and the two-axis decomposition
(:mod:`two_axis`) answer *"do these two venues trade the same FAMILY?"*
(``BTC_UP_DOWN_DAILY`` ↔ ``BTC_UP_DOWN_DAILY``). They do NOT answer *"is THIS
Kalshi market the SAME individual contract as THAT Polymarket market — same
strike, same settlement date?"*. Without that per-instrument join the
``arbitrage_price_dispersion`` strategy cannot quote a live cross-venue spread.

This module is that join. It populates the existing-but-unused
:class:`~unified_api_contracts.prediction.PredictionMarketCrossVenueMapping`
schema (``polymarket_condition_id`` + ``kalshi_market_ticker`` +
``strike`` + ``expiry_utc`` + ``underlying`` + ``canonical_event_id``).

What an :class:`InstrumentRecord` ACTUALLY carries for a prediction market
(verified against the live Kalshi + Polymarket instruments-service adapters,
2026-06-24)
-----------------------------------------------------------------------------
Both venues write ``instrument_type=PREDICTION_MARKET`` rows where:

* ``instrument_key`` — Kalshi MARKET ticker (e.g. ``KXBTCD-26JUN24-T95000``) /
  Polymarket ``condition_id``.
* ``raw_symbol``     — Kalshi EVENT ticker (``KXBTCD-26JUN24``) / Polymarket
  market ``slug`` (e.g. ``will-bitcoin-reach-95000-by-june-24``).
* ``base_asset``     — Kalshi series_ticker / Polymarket base_asset.
* ``expiry``         — populated on BOTH (Kalshi ``close_time`` / Polymarket
  resolution); this is the per-instrument settlement timestamp.
* ``strike``         — **always ``None``** on the prediction record (the
  ``InstrumentRecord.strike`` Decimal field is only populated for TradFi
  options). The strike is encoded in the Kalshi MARKET ticker (``-T<n>`` /
  ``-B<n>`` suffix) and in the Polymarket slug (a numeric token, optionally
  ``k``/``m`` suffixed). **So this matcher PARSES the strike from
  ``instrument_key`` (Kalshi) / ``raw_symbol`` (Polymarket)** — it does NOT
  read ``InstrumentRecord.strike`` (which would always be ``None``).
* **NO title / ``symbol`` field** — the canonical ``InstrumentRecord`` schema
  DROPPED ``symbol`` (it is silently ignored at construction even though the
  adapters pass it). The human "Away vs Home" title that sports fixture parsing
  needs is therefore NOT on the record. Price/macro matching needs no title
  (ticker/slug suffice); **sports matching takes the title from an optional
  ``titles`` map** (``instrument_key`` → title) supplied by the caller — without
  it a sports instrument is honest-absent (no false pair), never a wrong pair.

Matching strategy — PER bet-type family (operator: NO FALSE PAIRS)
-----------------------------------------------------------------
The cqg is classified per instrument from its tickers/slug via the existing
SSOT classifiers; ``underlying_for_group`` / ``bet_type_for_group`` then give
the Axis-1 underlying + Axis-2 bet-type. A pair is emitted ONLY when the
same-settlement guard holds — never on underlying overlap alone (that is the
two-axis categoriser's job, not a tradeable pair).

* **Crypto / index / commodity price markets** (``UP_DOWN`` / ``PRICE_RANGE`` /
  ``PRICE_LEVEL``) → join on ``(underlying, bet_type, settlement_date, strike)``.
  Same underlying + same parsed strike + same settlement date + same bet-type =
  the same market. A ``PRICE_RANGE``/``PRICE_LEVEL`` market with no parseable
  strike on a side yields NO key (honest absence — never a strikeless false
  pair). ``UP_DOWN`` is direction-only so its strike component is a fixed
  sentinel (the close is the implicit strike).
* **Macro** (``PER_MONTH``: CPI / FED / NONFARM_PAYROLLS …) → join on
  ``(underlying, bet_type, release_month, strike/threshold)``. Macro prints
  settle on a release whose MONTH is the join grain (the exact print
  day/time differs by venue), so the settlement key is the year-month, not the
  full date.
* **Sports** → PREFER the resolved API-Football ``af_fixture_id`` (a strong
  exact key: same fixture + same bet-type ⇒ same market); fall back to the fuzzy
  :meth:`SportsFixtureKey.pairing_key` (order-independent
  ``(league, sorted(teams), date)``) only when ``af_fixture_id`` is ``None``
  (unresolved market). Either path still requires the bet-type to match
  (MATCH / SPREAD / TOTAL must agree).
* Unmatched instruments → no row (honest absence; never a false pair).

The matcher is pure + deterministic: same inputs → byte-identical output
(rows sorted by ``canonical_event_id``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Final, NamedTuple

from unified_api_contracts.canonical.domain.prediction.prediction_mapping import (
    PredictionMarketCategory,
    PredictionMarketCrossVenueMapping,
)
from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CanonicalQuestionGroup,
)
from unified_api_contracts.canonical.domain.predictions.classifiers import (
    classify_kalshi_to_canonical_group,
    classify_polymarket_to_canonical_group,
)
from unified_api_contracts.canonical.domain.predictions.fixture_parsing import (
    parse_kalshi_sports_fixture,
    parse_polymarket_sports_fixture,
)
from unified_api_contracts.canonical.domain.predictions.two_axis import (
    PredictionBetType,
    PredictionUnderlying,
    bet_type_for_group,
    underlying_for_group,
)

if TYPE_CHECKING:
    from unified_api_contracts.internal.reference.instrument import InstrumentRecord

__all__ = [
    "build_cross_venue_mapping",
    "category_for_group",
    "match_key",
]


# Bet-types that join on a parsed STRIKE + settlement DATE (crypto/index/commodity).
_PRICE_BET_TYPES: Final[frozenset[PredictionBetType]] = frozenset(
    {PredictionBetType.UP_DOWN, PredictionBetType.PRICE_RANGE, PredictionBetType.PRICE_LEVEL}
)
# Macro recurring prints join on a release MONTH + threshold.
_MACRO_BET_TYPES: Final[frozenset[PredictionBetType]] = frozenset({PredictionBetType.PER_MONTH})
# Sports bet-types that participate in the fixture join (must match across venues).
_SPORTS_BET_TYPES: Final[frozenset[PredictionBetType]] = frozenset(
    {
        PredictionBetType.MATCH,
        PredictionBetType.SPREAD,
        PredictionBetType.TOTAL,
        PredictionBetType.NRFI,
    }
)

# Sentinel strike for direction-only (UP_DOWN) markets: the candle close is the
# implicit strike, so both venues key on the same fixed token rather than a
# parsed number (a parsed level on an UP_DOWN market would over-segment).
_UP_DOWN_STRIKE_KEY: Final[str] = "DIR"

# Underlyings whose markets pair on the price/strike axis. Sports underlyings are
# handled by the fixture path; everything else (politics/geo/weather/culture) has
# no clean per-instrument cross-venue strike and is left to the family categoriser.
_SPORTS_UNDERLYINGS: Final[frozenset[PredictionUnderlying]] = frozenset(
    u for u in PredictionUnderlying if u.value.startswith("SPORTS_")
)

# Kalshi MARKET-ticker strike suffix: ``…-T95000`` (threshold) / ``…-B95000``
# (below). Captures an optional decimal (``-T3.2`` for CPI). The leading T/B is
# the side, not part of the number — both sides share the same numeric strike so
# the cap/floor side does NOT enter the key (a YES-above-95000 on Kalshi pairs the
# Polymarket above-95000 market regardless of the T/B letter).
# The T/B prefix is OPTIONAL: long-horizon series (e.g. ``KXBTCMAXY-26DEC31-99999.99``)
# use bare numeric suffixes without a direction letter.
_KALSHI_STRIKE_RE: Final[re.Pattern[str]] = re.compile(r"-[TB]?(?P<strike>\d+(?:\.\d+)?)$")

# Polymarket slug strike token: a number after an above/below/reach/hit/price verb
# OR a trailing numeric token, optionally ``k``/``m`` (``90k`` → 90000). Excludes a
# trailing ISO date (handled separately) by requiring the number is NOT a 4-digit
# year inside a date pattern — we strip the date first.
_PM_SLUG_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\d{4}-\d{2}-\d{2}")
_PM_STRIKE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:above|below|reach|hit|over|under|price|level|of|to|at)[-_]?(?P<num>\d+(?:[.,]\d+)?)(?P<suffix>[km])?",
    re.IGNORECASE,
)
_PM_TRAILING_NUM_RE: Final[re.Pattern[str]] = re.compile(
    r"[-_](?P<num>\d+(?:[.,]\d+)?)(?P<suffix>[km])?$", re.IGNORECASE
)

# Matches "june-25-2026" or "jun-25-2026" style month-day-year tokens inside a Polymarket slug.
# Used to extract the ET question-date from UP_DOWN slugs like
# "bitcoin-up-or-down-june-25-2026-6pm-et" (expiry = midnight UTC ≠ slug date).
_PM_SLUG_MONTH_DATE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[-_](?P<day>\d{1,2})[-_](?P<year>\d{4})",
    re.IGNORECASE,
)
_PM_MONTH_MAP: Final[dict[str, int]] = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _polymarket_slug_date(slug: str) -> date | None:
    """ET question-date from a Polymarket UP/DOWN slug, or None when absent.

    Parses patterns like ``bitcoin-up-or-down-june-25-2026-6pm-et`` →
    ``date(2026, 6, 25)``.  Returns ``None`` when no parseable month-name date
    is present (non-UP/DOWN slugs, hex condition-id fallbacks, etc.).
    """
    m = _PM_SLUG_MONTH_DATE_RE.search(slug)
    if m is None:
        return None
    month_key = m.group("month").lower()[:3]
    month = _PM_MONTH_MAP.get(month_key)
    if month is None:
        return None
    try:
        return date(int(m.group("year")), month, int(m.group("day")))
    except ValueError:
        return None


class _Classified(NamedTuple):
    """One side of a candidate pair: its instrument + the derived join key."""

    record: InstrumentRecord
    key: str | None  # None ⇒ no honest discriminator ⇒ never pairs
    underlying: PredictionUnderlying
    bet_type: PredictionBetType
    strike: float | None
    canonical_event_id: str
    title: str  # human-readable label for fungibility alerts


def _normalize_strike(num: str, suffix: str | None) -> float | None:
    """``("90", "k")`` → ``90000.0``; ``("3.2", None)`` → ``3.2``. ``None`` on junk."""
    try:
        value = float(num.replace(",", ""))
    except ValueError:
        return None
    if suffix:
        sfx = suffix.lower()
        if sfx == "k":
            value *= 1_000.0
        elif sfx == "m":
            value *= 1_000_000.0
    return value


def _parse_kalshi_strike(market_ticker: str) -> float | None:
    """Strike from a Kalshi MARKET ticker (``KXBTCD-26JUN24-T95000`` → 95000.0).

    Kalshi long-horizon series avoid settling exactly on a round number by using
    a one-cent-below threshold (``KXBTCMAXY-26DEC31-99999.99`` ≈ $100 k). This
    function rounds those ``.99``-ending values up to the nearest whole number so
    the strike matches the Polymarket round-number slug (``reach-100000``).
    """
    m = _KALSHI_STRIKE_RE.search(market_ticker.upper())
    if m is None:
        return None
    value = _normalize_strike(m.group("strike"), None)
    if value is not None and abs(value % 1.0 - 0.99) < 1e-6:
        value = float(round(value + 0.01))
    return value


def _parse_polymarket_strike(slug: str, title: str) -> float | None:
    """Strike from a Polymarket slug/title (``bitcoin-above-95000`` / ``…-90k``)."""
    for text in (slug, title):
        if not text:
            continue
        cleaned = _PM_SLUG_DATE_RE.sub("", text)  # drop ISO date so its digits aren't read as a strike
        m = _PM_STRIKE_RE.search(cleaned)
        if m is not None:
            parsed = _normalize_strike(m.group("num"), m.group("suffix"))
            if parsed is not None:
                return parsed
        tm = _PM_TRAILING_NUM_RE.search(cleaned)
        if tm is not None:
            parsed = _normalize_strike(tm.group("num"), tm.group("suffix"))
            if parsed is not None:
                return parsed
    return None


def _settlement_date_key(expiry: datetime | None) -> str | None:
    """``YYYY-MM-DD`` settlement key for price markets (None when expiry absent)."""
    if expiry is None:
        return None
    return expiry.date().isoformat()


def _settlement_month_key(expiry: datetime | None) -> str | None:
    """``YYYY-MM`` settlement key for macro release markets (None when absent)."""
    if expiry is None:
        return None
    return f"{expiry.year:04d}-{expiry.month:02d}"


def _category_for_underlying(underlying: PredictionUnderlying) -> PredictionMarketCategory:
    """Map an Axis-1 underlying to the coarse :class:`PredictionMarketCategory`."""
    name = underlying.value
    crypto = {
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "DOGE",
        "BNB",
        "ADA",
        "AVAX",
        "LINK",
        "LTC",
        "SUI",
        "HYPE",
        "CRYPTO_SENTIMENT",
    }
    financial = {
        "SPX",
        "NDX",
        "RUT",
        "DJIA",
        "GOLD",
        "SILVER",
        "CRUDE_OIL",
        "NATGAS",
        "EUR",
        "CPI",
        "FED",
        "GDP",
        "UNEMPLOYMENT_RATE",
        "NONFARM_PAYROLLS",
        "PPI",
        "PCE",
        "TREASURY",
    }
    if name in crypto:
        return PredictionMarketCategory.CRYPTO
    if name in financial:
        return PredictionMarketCategory.FINANCIAL
    if name.startswith("SPORTS_"):
        return PredictionMarketCategory.SPORTS
    if name == "WEATHER_TEMP":
        return PredictionMarketCategory.WEATHER
    if name in {"OSCARS", "BOX_OFFICE"}:
        return PredictionMarketCategory.ENTERTAINMENT
    if name in {"ELECTION", "TRUMP", "ELON"} or name.startswith("GEO_"):
        return PredictionMarketCategory.POLITICS
    return PredictionMarketCategory.OTHER


def category_for_group(cqg: CanonicalQuestionGroup) -> PredictionMarketCategory:
    """Coarse :class:`PredictionMarketCategory` for a canonical question group.

    Public composition of the Axis-1 :func:`underlying_for_group` decomposition
    with the underlying→category classifier already used internally by
    :func:`_build_mapping` (:func:`_category_for_underlying`) — reused here, not
    duplicated. Lives in this module (rather than ``two_axis.py`` next to
    :func:`underlying_for_group`) to avoid a circular import: this module
    already imports from ``two_axis`` and from the ``prediction_mapping``
    module that defines :class:`PredictionMarketCategory`, so composing here
    needs no new dependency edge.
    """
    return _category_for_underlying(underlying_for_group(cqg))


def _price_or_macro_key(
    underlying: PredictionUnderlying,
    bet_type: PredictionBetType,
    settlement_key: str | None,
    strike: float | None,
) -> str | None:
    """Build the join key for a price/macro market, or ``None`` (no honest pair).

    The same-settlement guard lives HERE: a key is only produced when the
    settlement bucket is known AND (for non-direction markets) a strike was
    parsed. Equal keys ⇒ same underlying + bet-type + settlement bucket + strike
    ⇒ a tradeable same-market pair.
    """
    if settlement_key is None:
        return None
    if bet_type is PredictionBetType.UP_DOWN:
        strike_token = _UP_DOWN_STRIKE_KEY
    else:
        # PRICE_RANGE / PRICE_LEVEL / PER_MONTH need a parsed strike/threshold —
        # no strike ⇒ no honest pair (never collapse distinct strikes together).
        if strike is None:
            return None
        strike_token = format(strike, ".6g")
    return f"PRICE::{underlying.value}::{bet_type.value}::{settlement_key}::{strike_token}"


def match_key(
    *,
    venue: str,
    instrument_key: str,
    raw_symbol: str,
    symbol: str,
    expiry: datetime | None,
    underlying: PredictionUnderlying,
    bet_type: PredictionBetType,
    strike: float | None,
    sports_pairing_key: tuple[str, str, str, str] | None,
    af_fixture_id: int | None = None,
) -> str | None:
    """Order-independent cross-venue join key for ONE prediction instrument.

    Returns the same string for the Kalshi and Polymarket sides of the SAME
    real-world market, and ``None`` when no honest per-instrument discriminator
    exists (so the instrument can never form a false pair). The key is symmetric
    by construction: it is built from venue-NEUTRAL fields (underlying, bet-type,
    settlement bucket, strike, or the order-independent fixture pairing key) —
    never from the venue name or a venue-native id.

    For sports, a resolved API-Football ``af_fixture_id`` is a STRONG exact key:
    when it is set the sports key is ``SPORTS_FIX::{af_fixture_id}::{bet_type}``
    (two venues on the same fixture + bet-type match EXACTLY, no reliance on
    fuzzy team-name pairing). When ``af_fixture_id`` is ``None`` (unresolved
    market / absent column) the join FALLS BACK to the existing fuzzy
    ``sports_pairing_key`` path, so behaviour is unchanged for those markets.
    """
    del venue, instrument_key, raw_symbol, symbol  # captured upstream into the neutral fields
    if bet_type in _SPORTS_BET_TYPES and underlying in _SPORTS_UNDERLYINGS:
        if af_fixture_id is not None:
            # Strong exact key: same API-Football fixture + same bet-type ⇒ same
            # market, independent of the fuzzy team-name pairing below.
            return f"SPORTS_FIX::{af_fixture_id}::{bet_type.value}"
        if sports_pairing_key is None:
            return None  # not a single fixture (season-future / unparseable) → no pair
        league, a, b, fdate = sports_pairing_key
        return f"SPORTS::{league}::{bet_type.value}::{a}::{b}::{fdate}"
    if bet_type in _MACRO_BET_TYPES:
        return _price_or_macro_key(underlying, bet_type, _settlement_month_key(expiry), strike)
    if bet_type in _PRICE_BET_TYPES and underlying not in _SPORTS_UNDERLYINGS:
        return _price_or_macro_key(underlying, bet_type, _settlement_date_key(expiry), strike)
    # politics / geo / weather / culture / OTHER — no clean per-instrument
    # cross-venue strike join → honest absence (the family categoriser's domain).
    return None


def _classify_kalshi(record: InstrumentRecord, titles: Mapping[str, str]) -> _Classified:
    """Derive the join key for a Kalshi prediction instrument.

    ``titles`` maps ``instrument_key`` → the human market title ("Away vs Home"
    for sports). The canonical :class:`InstrumentRecord` carries NO title field
    (it was dropped from the schema), so a title is needed from the caller for
    sports fixture parsing; price/macro families do not need it.
    """
    market_ticker = record.instrument_key
    event_ticker = record.raw_symbol or market_ticker
    title = titles.get(market_ticker, "")
    cqg = classify_kalshi_to_canonical_group(ticker=event_ticker or market_ticker)
    underlying = underlying_for_group(cqg)
    bet_type = bet_type_for_group(cqg)
    strike = _parse_kalshi_strike(market_ticker)
    sports_key: tuple[str, str, str, str] | None = None
    if bet_type in _SPORTS_BET_TYPES and underlying in _SPORTS_UNDERLYINGS:
        fixture = parse_kalshi_sports_fixture(event_ticker or market_ticker, title)
        sports_key = fixture.pairing_key() if fixture is not None else None
    key = match_key(
        venue=record.venue,
        instrument_key=market_ticker,
        raw_symbol=event_ticker,
        symbol=title,
        expiry=record.expiry,
        underlying=underlying,
        bet_type=bet_type,
        strike=strike,
        sports_pairing_key=sports_key,
        af_fixture_id=record.af_fixture_id,
    )
    return _Classified(record, key, underlying, bet_type, strike, _canonical_event_id(underlying, bet_type, key), title)


def _classify_polymarket(record: InstrumentRecord, titles: Mapping[str, str]) -> _Classified:
    """Derive the join key for a Polymarket prediction instrument.

    ``titles`` maps ``condition_id`` (``instrument_key``) → the human market
    title; needed only for sports fixture parsing (the canonical record has no
    title field). The slug (``raw_symbol``) drives cqg + strike for price/macro.
    """
    slug = record.raw_symbol or record.instrument_key
    title = titles.get(record.instrument_key, "") or slug
    cqg = classify_polymarket_to_canonical_group(
        title=title,
        slug=slug,
        event_slug=slug,
        outcome="",
        condition_id=record.instrument_key,
    )
    underlying = underlying_for_group(cqg)
    bet_type = bet_type_for_group(cqg)
    strike = _parse_polymarket_strike(slug, title)
    sports_key: tuple[str, str, str, str] | None = None
    if bet_type in _SPORTS_BET_TYPES and underlying in _SPORTS_UNDERLYINGS:
        fixture = parse_polymarket_sports_fixture(
            league=underlying.value.removeprefix("SPORTS_"),
            event_title=title,
            slug=slug,
            resolution_date=record.expiry.date() if record.expiry is not None else None,
        )
        sports_key = fixture.pairing_key() if fixture is not None else None
    # For UP_DOWN markets the IS stores all hourly contracts at midnight UTC of the
    # PREVIOUS day (expiry = 2026-06-25 00:00 UTC for June 25 ET markets), producing a
    # systematic 1-day offset vs Kalshi (which uses the actual expiry timestamp).
    # Parse the ET question-date from the slug ("june-25-2026" token) and use it as
    # the settlement key so both venues produce the same PRICE::*::UP_DOWN::YYYY-MM-DD::DIR.
    expiry_for_key = record.expiry
    if bet_type is PredictionBetType.UP_DOWN:
        slug_d = _polymarket_slug_date(slug)
        if slug_d is not None:
            expiry_for_key = datetime(slug_d.year, slug_d.month, slug_d.day, tzinfo=UTC)
    key = match_key(
        venue=record.venue,
        instrument_key=record.instrument_key,
        raw_symbol=slug,
        symbol=title,
        expiry=expiry_for_key,
        underlying=underlying,
        bet_type=bet_type,
        strike=strike,
        sports_pairing_key=sports_key,
        af_fixture_id=record.af_fixture_id,
    )
    return _Classified(record, key, underlying, bet_type, strike, _canonical_event_id(underlying, bet_type, key), title)


def _canonical_event_id(
    underlying: PredictionUnderlying,
    bet_type: PredictionBetType,
    key: str | None,
) -> str:
    """Deterministic cross-venue event id (the join key IS the identity)."""
    return key or f"UNMATCHED::{underlying.value}::{bet_type.value}"


def _build_mapping(kalshi: _Classified, poly: _Classified) -> PredictionMarketCrossVenueMapping:
    """Assemble the :class:`PredictionMarketCrossVenueMapping` for a matched pair."""
    underlying = kalshi.underlying
    bet_type = kalshi.bet_type
    is_sports = bet_type in _SPORTS_BET_TYPES and underlying in _SPORTS_UNDERLYINGS
    # Prefer the parsed strike that exists (UP_DOWN has none; both sides share it).
    strike = kalshi.strike if kalshi.strike is not None else poly.strike
    # Settlement: prefer Kalshi expiry (close_time), fall back to Polymarket.
    expiry = kalshi.record.expiry or poly.record.expiry
    # Settlement method per venue. Kalshi always resolves on the closing price
    # at settlement time (point-in-time). Polymarket PRICE_LEVEL / PRICE_RANGE
    # resolve if the price EVER touches the level during the contract lifetime
    # (path-dependent). Polymarket UP_DOWN / MATCH / SPREAD / TOTAL / PER_MONTH
    # use the final closing value (point-in-time). The difference matters: two
    # markets nominally on the same strike may not be fungible when one is
    # path-dependent and the other is point-in-time.
    poly_path_dependent = bet_type in {PredictionBetType.PRICE_LEVEL, PredictionBetType.PRICE_RANGE}
    # The strong sports key embeds af_fixture_id literally (`SPORTS_FIX::{id}::{bet_type}`),
    # so a shared key means both sides' `record.af_fixture_id` are the SAME int — but that
    # numeric id was previously computed only to build the key string, then discarded (never
    # copied onto the dedicated schema field). Stamp it back for a consumer that wants the raw
    # id (not just the composite canonical_event_id string) without re-parsing it.
    af_fixture_id = kalshi.record.af_fixture_id if (kalshi.key or "").startswith("SPORTS_FIX::") else None
    return PredictionMarketCrossVenueMapping(
        canonical_event_id=kalshi.key or poly.canonical_event_id,
        category=_category_for_underlying(underlying),
        sub_category=underlying.value.lower(),
        underlying=None if is_sports else underlying.value,
        api_football_fixture_id=af_fixture_id,
        polymarket_condition_id=poly.record.instrument_key,
        kalshi_event_ticker=kalshi.record.raw_symbol or None,
        kalshi_market_ticker=kalshi.record.instrument_key,
        strike=None if is_sports else strike,
        expiry_utc=expiry,
        kalshi_settlement_method="point_in_time",
        polymarket_settlement_method="path_dependent" if poly_path_dependent else "point_in_time",
        kalshi_title=kalshi.title or None,
        polymarket_title=poly.title or None,
    )


def build_cross_venue_mapping(
    kalshi_instruments: Iterable[InstrumentRecord],
    polymarket_instruments: Iterable[InstrumentRecord],
    *,
    titles: Mapping[str, str] | None = None,
) -> list[PredictionMarketCrossVenueMapping]:
    """Join Kalshi ↔ Polymarket prediction instruments into same-market pairs.

    Each instrument is classified to its cqg (via the existing SSOT classifiers),
    decomposed to ``(underlying, bet_type)``, and reduced to a venue-NEUTRAL join
    key (:func:`match_key`). Instruments whose keys are equal are the SAME
    real-world market and emit one :class:`PredictionMarketCrossVenueMapping`
    carrying both venues' ids + the shared strike + expiry.

    Fields matched, per family (all derived from the REAL canonical
    :class:`InstrumentRecord` — see module docstring):

    * crypto / index / commodity price → ``(underlying, bet_type,
      settlement_date, strike)`` — strike PARSED from the Kalshi market ticker
      (``instrument_key``) / Polymarket slug (``raw_symbol``), NOT the
      always-``None`` ``InstrumentRecord.strike``.
    * macro (``PER_MONTH``) → ``(underlying, bet_type, release_month, threshold)``.
    * sports → :meth:`SportsFixtureKey.pairing_key` + bet-type — REQUIRES the
      human "Away vs Home" title, which the canonical record does NOT carry
      (the ``symbol`` field was removed from ``InstrumentRecord``); pass it via
      ``titles`` (``instrument_key`` → title). Without ``titles`` a sports
      instrument yields no key (honest absence), so the price/macro join still
      works from the record alone.

    Honest absence: an instrument with no parseable strike (for a strike-based
    family) or no settlement date, a season-future / non-fixture sports market, a
    sports market with no supplied title, or an underlying with no clean
    per-instrument cross-venue join (politics / geo / weather) produces NO key →
    NO row. Underlying overlap alone NEVER yields a pair (that is the two-axis
    categoriser's job). The result is sorted by ``canonical_event_id`` so the
    output is deterministic.

    :param kalshi_instruments: Kalshi ``PREDICTION_MARKET`` instrument records.
    :param polymarket_instruments: Polymarket ``PREDICTION_MARKET`` records.
    :param titles: optional ``instrument_key`` → human title map (only sports
        pairing needs it; the canonical record has no title field).
    :returns: One mapping row per matched same-market pair, deterministically
        ordered. No row for unmatched instruments.
    """
    title_map: Mapping[str, str] = titles or {}
    kalshi_classified = [_classify_kalshi(rec, title_map) for rec in kalshi_instruments]
    poly_classified = [_classify_polymarket(rec, title_map) for rec in polymarket_instruments]

    poly_by_key: dict[str, list[_Classified]] = {}
    for pc in poly_classified:
        if pc.key is not None:
            poly_by_key.setdefault(pc.key, []).append(pc)

    mappings: list[PredictionMarketCrossVenueMapping] = []
    for kc in kalshi_classified:
        if kc.key is None:
            continue
        for pc in poly_by_key.get(kc.key, ()):
            mappings.append(_build_mapping(kc, pc))

    return _dedupe_sorted(mappings)


def _dedupe_sorted(
    mappings: Sequence[PredictionMarketCrossVenueMapping],
) -> list[PredictionMarketCrossVenueMapping]:
    """Deterministic order + de-dup on the full venue-id identity."""
    seen: set[tuple[str, str | None, str | None]] = set()
    unique: list[PredictionMarketCrossVenueMapping] = []
    for m in sorted(
        mappings,
        key=lambda x: (x.canonical_event_id, x.kalshi_market_ticker or "", x.polymarket_condition_id or ""),
    ):
        identity = (m.canonical_event_id, m.kalshi_market_ticker, m.polymarket_condition_id)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(m)
    return unique
