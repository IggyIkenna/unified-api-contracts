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
        # MLB — HHMM start time, 3-char codes. Team names canonicalise through the
        # per-league alias tables (external/sports/team_mappings.py) so Kalshi
        # city-only forms and Polymarket full-name forms produce the same canonical id.
        (
            "KXMLBGAME-26JUN261910SEACLE",
            "Seattle vs Cleveland",
            "MLB",
            "SEATTLE_MARINERS",
            "CLEVELAND_GUARDIANS",
            date(2026, 6, 26),
            "1910",
        ),
        (
            "KXMLBGAME-26JUN261910PHINYM",
            "Philadelphia vs New York M",
            "MLB",
            "PHILADELPHIA_PHILLIES",
            "NEW_YORK_METS",
            date(2026, 6, 26),
            "1910",
        ),
        # NFL — NO HHMM, VARIABLE-width codes. Team names canonicalise same as MLB above.
        (
            "KXNFLGAME-26SEP14DENKC",
            "Denver vs Kansas City",
            "NFL",
            "DENVER_BRONCOS",
            "KANSAS_CITY_CHIEFS",
            date(2026, 9, 14),
            None,
        ),
        (
            "KXNFLGAME-26SEP13WASPHI",
            "Washington vs Philadelphia",
            "NFL",
            "WASHINGTON_COMMANDERS",
            "PHILADELPHIA_EAGLES",
            date(2026, 9, 13),
            None,
        ),
        # Tennis — player pair, 3-char surname prefixes. Canonical player IDs from the
        # tennis alias table.
        (
            "KXATPMATCH-26JUN24HUMBRO",
            "Humbert vs Brooksby",
            "TENNIS",
            "HUMBERT",
            "BROOKSBY",
            date(2026, 6, 24),
            None,
        ),
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
    # Both sides canonicalise to the same team IDs via the per-league alias tables,
    # so "Seattle" (Kalshi) and "Seattle" (Polymarket) both resolve to SEATTLE_MARINERS.
    assert kalshi.pairing_key() == poly.pairing_key()
    assert kalshi.pairing_key() == ("MLB", "CLEVELAND_GUARDIANS", "SEATTLE_MARINERS", "2026-06-26")


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


# ---------------------------------------------------------------------------
# Team-name canonicalization via external/sports/team_mappings.py
# ---------------------------------------------------------------------------


def test_kalshi_mlb_city_only_canonicalizes_to_team_id():
    """Kalshi 'Tampa Bay' canonicalises to TAMPA_BAY_RAYS."""
    fx = parse_kalshi_sports_fixture("KXMLBGAME-26AUG042040TBCOL", "Tampa Bay vs Colorado")
    assert fx is not None
    assert fx.away == "TAMPA_BAY_RAYS"
    assert fx.home == "COLORADO_ROCKIES"


def test_kalshi_la_teams_have_distinct_trailing_qualifiers():
    """Kalshi disambiguates same-city teams with trailing letters — canonicalise correctly."""
    # Dodgers: "Los Angeles D"
    fx_d = parse_kalshi_sports_fixture("KXMLBGAME-26AUG042040LADSF", "Los Angeles D vs San Francisco")
    assert fx_d is not None
    assert fx_d.away == "LOS_ANGELES_DODGERS"
    # Angels: "Los Angeles A"
    fx_a = parse_kalshi_sports_fixture("KXMLBGAME-26AUG042040LAABAL", "Los Angeles A vs Baltimore")
    assert fx_a is not None
    assert fx_a.away == "LOS_ANGELES_ANGELS"


def test_kalshi_nfl_canonicalizes():
    """Kalshi NFL city names canonicalise to team IDs."""
    fx = parse_kalshi_sports_fixture("KXNFLGAME-26AUG13GBPIT", "Green Bay vs Pittsburgh")
    assert fx is not None
    assert fx.away == "GREEN_BAY_PACKERS"
    assert fx.home == "PITTSBURGH_STEELERS"


def test_kalshi_mets_vs_yankees_are_distinct():
    """Kalshi 'New York M' and 'New York Y' map to METS vs YANKEES."""
    fx_m = parse_kalshi_sports_fixture("KXMLBGAME-26AUG042040NYMCLE", "New York M vs Cleveland")
    assert fx_m is not None
    assert fx_m.away == "NEW_YORK_METS"
    fx_y = parse_kalshi_sports_fixture("KXMLBGAME-26AUG042040NYYBOS", "New York Y vs Boston")
    assert fx_y is not None
    assert fx_y.away == "NEW_YORK_YANKEES"


def test_kalshi_tennis_canonicalizes():
    """Kalshi tennis player surnames canonicalise via the player alias table."""
    fx = parse_kalshi_sports_fixture("KXATPMATCH-26JUN24HUMBRO", "Humbert vs Brooksby")
    assert fx is not None
    assert fx.away == "HUMBERT"
    assert fx.home == "BROOKSBY"


def test_polymarket_team_name_canonicalizes_same_as_kalshi():
    """Polymarket 'Seattle Mariners' and Kalshi 'Seattle' produce the SAME canonical id."""
    kalshi = parse_kalshi_sports_fixture("KXMLBGAME-26JUN261910SEACLE", "Seattle vs Cleveland")
    # Simulate a Polymarket title that uses the full team name
    poly = parse_polymarket_sports_fixture(
        league="MLB",
        event_title="Seattle Mariners vs. Cleveland Guardians",
        slug="mlb-sea-cle-2026-06-26",
    )
    assert kalshi is not None
    assert poly is not None
    # Both venues now produce the same canonical pairing key.
    assert kalshi.pairing_key() == poly.pairing_key()
    assert kalshi.away == "SEATTLE_MARINERS"
    assert poly.away == "SEATTLE_MARINERS"
    assert kalshi.home == "CLEVELAND_GUARDIANS"
    assert poly.home == "CLEVELAND_GUARDIANS"


def test_unknown_team_name_falls_back_to_raw_normalized_form():
    """An unresolvable team name stays as-is (honest absence — no false canonicalization)."""
    fx = parse_kalshi_sports_fixture("KXMLBGAME-26AUG042040ZZZXXX", "Zzyzx vs Cleveland")
    assert fx is not None
    # "Zzyzx" is not in any alias table — falls back to normalized raw form.
    assert fx.away == "zzyzx"
    # "Cleveland" IS in the alias table.
    assert fx.home == "CLEVELAND_GUARDIANS"


def test_nba_canonicalizes():
    """NBA team names canonicalise correctly when a game ticker appears."""
    # Kalshi NBA games are typically KXNBAGAME-... (no live samples during
    # off-season 2026-08-05, but the fixture format is proven to match the
    # NFL pattern with league=NBA). Verify via Polymarket path.
    poly = parse_polymarket_sports_fixture(
        league="NBA",
        event_title="Boston Celtics vs. Los Angeles Lakers",
        slug="nba-bos-lal-2026-06-15",
        resolution_date=date(2026, 6, 15),
    )
    assert poly is not None
    assert poly.away == "BOSTON_CELTICS"
    assert poly.home == "LOS_ANGELES_LAKERS"
