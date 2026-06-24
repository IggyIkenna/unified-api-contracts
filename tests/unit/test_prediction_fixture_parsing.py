"""Per-fixture cross-venue parsing — validated against REAL Kalshi tickers/titles.

Samples captured live 2026-06-23 from
``api.elections.kalshi.com/trade-api/v2/events?series_ticker=…&status=open``.
The per-league format DIFFERS (MLB has HHMM + 3-char codes; NFL has no time +
variable 2-3-char codes; tennis is a player pair) — these tests pin the real
shapes so a regression that re-introduces a fixed-width team split (which breaks
NFL) or drops the season-future guard (which creates false pairs) is caught.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from unified_api_contracts.canonical.domain.predictions.fixture_parsing import (
    SportsFixtureKey,
    normalize_participant,
    parse_kalshi_sports_fixture,
    parse_polymarket_sports_fixture,
)


@pytest.mark.parametrize(
    ("ticker", "title", "league", "away", "home", "fixture_date", "hhmm"),
    [
        # MLB — HHMM start time, 3-char codes
        (
            "KXMLBGAME-26JUN261910SEACLE",
            "Seattle vs Cleveland",
            "MLB",
            "seattle",
            "cleveland",
            date(2026, 6, 26),
            "1910",
        ),
        (
            "KXMLBGAME-26JUN261910PHINYM",
            "Philadelphia vs New York M",
            "MLB",
            "philadelphia",
            "new york m",
            date(2026, 6, 26),
            "1910",
        ),
        # NFL — NO HHMM, VARIABLE-width codes (DENKC=DEN+KC, WASPHI=WAS+PHI) → must use title, not a 3+3 split
        ("KXNFLGAME-26SEP14DENKC", "Denver vs Kansas City", "NFL", "denver", "kansas city", date(2026, 9, 14), None),
        (
            "KXNFLGAME-26SEP13WASPHI",
            "Washington vs Philadelphia",
            "NFL",
            "washington",
            "philadelphia",
            date(2026, 9, 13),
            None,
        ),
        # Tennis — player pair, 3-char surname prefixes
        ("KXATPMATCH-26JUN24HUMBRO", "Humbert vs Brooksby", "TENNIS", "humbert", "brooksby", date(2026, 6, 24), None),
    ],
)
def test_parse_kalshi_real_samples(ticker, title, league, away, home, fixture_date, hhmm):
    fx = parse_kalshi_sports_fixture(ticker, title)
    assert fx is not None
    assert fx.league == league
    assert fx.away == away
    assert fx.home == home
    assert fx.fixture_date == fixture_date
    if hhmm is None:
        assert fx.start_time is None
    else:
        assert fx.start_time == datetime(
            fixture_date.year, fixture_date.month, fixture_date.day, int(hhmm[:2]), int(hhmm[2:]), tzinfo=UTC
        )


@pytest.mark.parametrize(
    ("ticker", "title"),
    [
        ("KXNBA-27", "2027 Pro Basketball Champion"),  # season future — no fixture
        ("KXNHL-27", "2026-27 Stanley Cup Finals Winner"),  # season future
        ("KXCPI-26JUN", "CPI above 3%"),  # not a sports league
        ("KXMLBGAME-26JUN261910SEACLE", "Champion 2026"),  # sports but title is not "A vs B"
        ("", "Seattle vs Cleveland"),  # empty ticker
    ],
)
def test_parse_kalshi_non_fixture_returns_none(ticker, title):
    assert parse_kalshi_sports_fixture(ticker, title) is None


def test_polymarket_fixture_and_cross_venue_pairing():
    kalshi = parse_kalshi_sports_fixture("KXMLBGAME-26JUN261910SEACLE", "Seattle vs Cleveland")
    poly = parse_polymarket_sports_fixture(
        league="MLB", event_title="Seattle vs. Cleveland", slug="mlb-sea-cle-2026-06-26"
    )
    assert kalshi is not None
    assert poly is not None
    # The SAME real-world game from two venues joins on the order-independent key.
    assert kalshi.pairing_key() == poly.pairing_key()
    assert kalshi.pairing_key() == ("MLB", "cleveland", "seattle", "2026-06-26")


def test_polymarket_date_from_resolution_when_slug_has_no_date():
    poly = parse_polymarket_sports_fixture(
        league="NFL", event_title="Denver vs. Kansas City", slug="nfl-den-kc", resolution_date=date(2026, 9, 14)
    )
    assert poly is not None
    assert poly.fixture_date == date(2026, 9, 14)


def test_pairing_key_is_order_independent():
    a = SportsFixtureKey(league="NFL", away="denver", home="kansas city", fixture_date=date(2026, 9, 14))
    b = SportsFixtureKey(league="NFL", away="kansas city", home="denver", fixture_date=date(2026, 9, 14))
    assert a.pairing_key() == b.pairing_key()


def test_normalize_participant_collapses_case_and_space():
    assert normalize_participant("  New York   M ") == "new york m"
