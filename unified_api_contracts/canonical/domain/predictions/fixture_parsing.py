"""Per-FIXTURE cross-venue parsing for prediction sports markets.

The cqg classifier (`classifiers.py`) maps a market to a SPORTS_{LEAGUE}_{BETTYPE}
CATEGORY (discovery). This module is the next layer down: it parses the exact
real-world FIXTURE (a single game / match) a market settles on, so the arb engine
can pair the *same-game* Kalshi and Polymarket instruments WITHIN a shared cqg
group.

Kalshi encodes the fixture in the EVENT ticker; the per-league formats differ
(verified live 2026-06-23 vs `api.elections.kalshi.com/trade-api/v2/events`):

* MLB  ``KXMLBGAME-{YY}{MON}{DD}{HHMM}{AWAY}{HOME}`` — has an HHMM start time;
       3-char team codes (``KXMLBGAME-26JUN261910SEACLE`` → 2026-06-26 19:10,
       SEA @ CLE; title "Seattle vs Cleveland").
* NFL  ``KXNFLGAME-{YY}{MON}{DD}{AWAY}{HOME}`` — NO HHMM; team codes are
       VARIABLE 2-3 chars (``KXNFLGAME-26SEP14DENKC`` → 2026-09-14, DEN @ KC;
       ``DALNYG`` = DAL+NYG, ``WASPHI`` = WAS+PHI) so a fixed 3+3 split FAILS.
* Tennis ``KX{ATP,WTA}MATCH-{YY}{MON}{DD}{P1}{P2}`` — player pair, 3-char surname
       prefixes (``KXATPMATCH-26JUN24HUMBRO`` → Humbert vs Brooksby).

Because the concatenated team segment is NOT reliably splittable (NFL variable
width), the two participants are derived from the human-readable ``title``
("Away vs Home") — deterministic across leagues — while the ticker supplies the
league + date (+ optional start time). Season-futures / award / draft tickers
(``KXNBA-27`` "2027 Pro Basketball Champion", ``KXNHL-27``) carry NO date+game
token → they are NOT a fixture and parse to ``None`` (never a false pair).

The companion ``parse_polymarket_sports_fixture`` derives the same
``(league, away, home, date)`` key from the Polymarket gamma slug / event_title,
so the two venues join on the canonical key (team normalisation to a shared id is
the consumer's job via the sports team registry).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Final

from unified_api_contracts.canonical.domain.predictions.classifiers import (
    kalshi_sports_league_for_ticker,
)
from unified_api_contracts.external.sports.team_mappings import (
    canonicalize_sports_participant,
)

__all__ = [
    "SportsFixtureKey",
    "normalize_participant",
    "parse_kalshi_sports_fixture",
    "parse_polymarket_sports_fixture",
]


@dataclass(frozen=True, slots=True)
class SportsFixtureKey:
    """A parsed cross-venue sports fixture (one real-world game/match).

    ``away``/``home`` are the venue-reported participant names, lower-cased +
    whitespace-collapsed via :func:`normalize_participant` so the same fixture
    from two venues compares equal on ``(league, away, home, fixture_date)``
    even when the surrounding ticker/slug differs. ``start_time`` is populated
    only when the source carries an intraday time (Kalshi MLB HHMM); a date-only
    source leaves it ``None`` and the date is the pairing key.
    """

    league: str
    away: str
    home: str
    fixture_date: date
    start_time: datetime | None = None
    source_venue: str = ""
    source_id: str = ""

    def pairing_key(self) -> tuple[str, str, str, str]:
        """The order-independent join key — sorted participants so a venue that
        lists the pair in the opposite order still pairs."""
        a, b = sorted((self.away, self.home))
        return (self.league, a, b, self.fixture_date.isoformat())


_MONTHS: Final[dict[str, int]] = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# Suffix after the ``-``: 2-digit year, 3-letter month, 2-digit day, OPTIONAL
# 4-digit HHMM (MLB), then the letter-led team segment (variable width).
_KALSHI_FIXTURE_SUFFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<yy>\d{2})(?P<mon>[A-Z]{3})(?P<dd>\d{2})(?P<hhmm>\d{4})?(?P<teams>[A-Z].*)$"
)

# A per-game / per-match token MUST be present (else season-future / award → no
# fixture). MATCH covers tennis/UFC/boxing; GAME covers the team leagues.
_KALSHI_FIXTURE_MARKERS: Final[tuple[str, ...]] = ("GAME", "MATCH")

_VS_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"\s+vs\.?\s+", re.IGNORECASE)


def normalize_participant(name: str) -> str:
    """Lower-case + collapse whitespace + strip trailing single-letter qualifiers.

    Kalshi titles disambiguate same-city teams with a trailing letter ("New York
    M" / "New York Y" for Mets/Yankees, "New York G" for Giants). We keep that
    qualifier (it distinguishes the team) but collapse case/space so a venue that
    writes "new york m" vs "New York  M" compares equal.
    """
    return re.sub(r"\s+", " ", name.strip()).lower()


def parse_kalshi_sports_fixture(event_ticker: str, title: str) -> SportsFixtureKey | None:
    """Parse a Kalshi sports EVENT ticker + title into a fixture key, or ``None``.

    ``None`` when: the ticker is not a mapped sports league, carries no GAME/MATCH
    fixture marker (season-future / award / draft), the date/suffix is unparseable,
    or the title is not a two-participant "Away vs Home".
    """
    if not event_ticker or not title:
        return None
    upper = event_ticker.upper()
    league = kalshi_sports_league_for_ticker(event_ticker)
    if league is None:
        return None
    if not any(marker in upper for marker in _KALSHI_FIXTURE_MARKERS):
        return None  # season-future / award — not a single fixture

    _, sep, suffix = event_ticker.partition("-")
    if not sep:
        return None
    m = _KALSHI_FIXTURE_SUFFIX_RE.match(suffix.upper())
    if m is None:
        return None
    month = _MONTHS.get(m.group("mon"))
    if month is None:
        return None
    try:
        fixture_date = date(2000 + int(m.group("yy")), month, int(m.group("dd")))
    except ValueError:
        return None
    start_time: datetime | None = None
    hhmm = m.group("hhmm")
    if hhmm is not None:
        hh, mm = int(hhmm[:2]), int(hhmm[2:])
        if hh < 24 and mm < 60:
            start_time = datetime(fixture_date.year, fixture_date.month, fixture_date.day, hh, mm, tzinfo=UTC)

    parts = _VS_SPLIT_RE.split(title.strip(), maxsplit=1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    away_raw = normalize_participant(parts[0])
    home_raw = normalize_participant(parts[1])
    return SportsFixtureKey(
        league=league,
        away=canonicalize_sports_participant(away_raw, league),
        home=canonicalize_sports_participant(home_raw, league),
        fixture_date=fixture_date,
        start_time=start_time,
        source_venue="KALSHI",
        source_id=event_ticker,
    )


# Polymarket gamma sports slugs are league-prefixed "Away vs. Home" titles, e.g.
# event_title "Seattle vs. Cleveland" / slug "mlb-sea-cle-2026-06-26". The title
# is the reliable participant source (slugs use abbrevs that vary); the date comes
# from the slug's trailing ISO date or the market resolution date supplied by the
# caller. Polymarket does not encode the league in a fixed prefix, so the caller
# supplies the league it already classified (the shared cqg group).
_PM_SLUG_DATE_RE: Final[re.Pattern[str]] = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def parse_polymarket_sports_fixture(
    *,
    league: str,
    event_title: str,
    slug: str,
    resolution_date: date | None = None,
) -> SportsFixtureKey | None:
    """Parse a Polymarket sports market into the same fixture key, or ``None``.

    ``league`` is the cqg-classified league (Polymarket has no fixed ticker
    prefix). The fixture date is the slug's trailing ISO date when present, else
    ``resolution_date`` (the market end date). Participants come from the
    "Away vs Home" event_title.
    """
    if not league or not event_title:
        return None
    parts = _VS_SPLIT_RE.split(event_title.strip(), maxsplit=1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    fixture_date: date | None = None
    dm = _PM_SLUG_DATE_RE.search(slug or "")
    if dm is not None:
        try:
            fixture_date = date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
        except ValueError:
            fixture_date = None
    if fixture_date is None:
        fixture_date = resolution_date
    if fixture_date is None:
        return None
    away_raw = normalize_participant(parts[0])
    home_raw = normalize_participant(parts[1])
    return SportsFixtureKey(
        league=league,
        away=canonicalize_sports_participant(away_raw, league),
        home=canonicalize_sports_participant(home_raw, league),
        fixture_date=fixture_date,
        start_time=None,
        source_venue="POLYMARKET",
        source_id=slug or event_title,
    )
