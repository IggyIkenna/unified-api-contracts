"""Unit tests for Odds API raw source schemas (ODOutcomeRaw, ODMarketRaw, etc.).

Covers construction, from_raw(), round-trip serialisation, frozen immutability,
and deeply nested ODEventRaw with bookmakers/markets/outcomes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.external.odds_api.schemas import (
    ODBookmakerRaw,
    ODEventRaw,
    ODMarketRaw,
    ODOddsRaw,
    ODOutcomeRaw,
    ODTeamsRaw,
)

NOW = datetime.now(tz=UTC)

_RAW_NESTED_EVENT: dict[str, object] = {
    "event_id": "evt-002",
    "sport_key": "soccer_epl",
    "sport_title": "EPL",
    "commence_time": NOW.isoformat(),
    "home_team": "Man City",
    "away_team": "Liverpool",
    "bookmakers": [
        {
            "bookmaker_key": "bet365",
            "bookmaker_title": "Bet365",
            "last_update": NOW.isoformat(),
            "markets": [
                {
                    "market_key": "h2h",
                    "outcomes": [
                        {"name": "Man City", "price": 2.10},
                        {"name": "Draw", "price": 3.40},
                        {"name": "Liverpool", "price": 3.20},
                    ],
                },
                {
                    "market_key": "spreads",
                    "outcomes": [
                        {"name": "Man City", "price": 1.91, "point": -0.5},
                        {"name": "Liverpool", "price": 1.91, "point": 0.5},
                    ],
                },
            ],
        },
        {
            "bookmaker_key": "pinnacle",
            "bookmaker_title": "Pinnacle",
            "markets": [
                {
                    "market_key": "h2h",
                    "outcomes": [
                        {"name": "Man City", "price": 2.15},
                        {"name": "Draw", "price": 3.50},
                        {"name": "Liverpool", "price": 3.10},
                    ],
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# ODOutcomeRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestODOutcomeRaw:
    def test_construct_minimal(self) -> None:
        o = ODOutcomeRaw(name="Chelsea", price=Decimal("2.10"))
        assert o.name == "Chelsea"
        assert o.price == Decimal("2.10")
        assert o.point is None

    def test_construct_with_point(self) -> None:
        o = ODOutcomeRaw(name="Over", price=Decimal("1.91"), point=Decimal("2.5"))
        assert o.point == Decimal("2.5")

    def test_from_raw(self) -> None:
        o = ODOutcomeRaw.from_raw({"name": "Draw", "price": 3.25})
        assert o.name == "Draw"
        assert o.price == Decimal("3.25")

    def test_frozen(self) -> None:
        o = ODOutcomeRaw(name="Home", price=Decimal("1.50"))
        with pytest.raises(ValidationError):
            o.name = "Away"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        o = ODOutcomeRaw(name="Under", price=Decimal("1.85"), point=Decimal("2.5"))
        data = o.model_dump()
        o2 = ODOutcomeRaw.model_validate(data)
        assert o == o2


# ---------------------------------------------------------------------------
# ODMarketRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestODMarketRaw:
    def test_construct_empty_outcomes(self) -> None:
        m = ODMarketRaw(market_key="h2h")
        assert m.outcomes == ()

    def test_construct_with_outcomes(self) -> None:
        outcomes = (
            ODOutcomeRaw(name="Home", price=Decimal("1.80")),
            ODOutcomeRaw(name="Draw", price=Decimal("3.60")),
            ODOutcomeRaw(name="Away", price=Decimal("4.20")),
        )
        m = ODMarketRaw(market_key="h2h", outcomes=outcomes)
        assert len(m.outcomes) == 3
        assert m.outcomes[1].name == "Draw"

    def test_from_raw(self) -> None:
        m = ODMarketRaw.from_raw(
            {
                "market_key": "spreads",
                "outcomes": [
                    {"name": "Home", "price": 1.91, "point": -1.5},
                    {"name": "Away", "price": 1.91, "point": 1.5},
                ],
            }
        )
        assert m.market_key == "spreads"
        assert len(m.outcomes) == 2
        assert m.outcomes[0].point == Decimal("-1.5")

    def test_frozen(self) -> None:
        m = ODMarketRaw(market_key="totals")
        with pytest.raises(ValidationError):
            m.market_key = "h2h"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        m = ODMarketRaw(
            market_key="h2h",
            outcomes=(ODOutcomeRaw(name="Home", price=Decimal("2.00")),),
        )
        data = m.model_dump()
        m2 = ODMarketRaw.model_validate(data)
        assert m == m2


# ---------------------------------------------------------------------------
# ODBookmakerRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestODBookmakerRaw:
    def test_construct_minimal(self) -> None:
        b = ODBookmakerRaw(bookmaker_key="pinnacle", bookmaker_title="Pinnacle")
        assert b.last_update is None
        assert b.markets == ()

    def test_construct_with_markets(self) -> None:
        market = ODMarketRaw(
            market_key="h2h",
            outcomes=(
                ODOutcomeRaw(name="Home", price=Decimal("1.80")),
                ODOutcomeRaw(name="Away", price=Decimal("2.10")),
            ),
        )
        b = ODBookmakerRaw(
            bookmaker_key="bet365",
            bookmaker_title="Bet365",
            last_update=NOW,
            markets=(market,),
        )
        assert len(b.markets) == 1
        assert b.markets[0].market_key == "h2h"

    def test_from_raw(self) -> None:
        b = ODBookmakerRaw.from_raw(
            {
                "bookmaker_key": "unibet",
                "bookmaker_title": "Unibet",
                "last_update": NOW.isoformat(),
                "markets": [
                    {
                        "market_key": "totals",
                        "outcomes": [
                            {"name": "Over", "price": 1.91, "point": 2.5},
                            {"name": "Under", "price": 1.91, "point": 2.5},
                        ],
                    }
                ],
            }
        )
        assert b.bookmaker_key == "unibet"
        assert len(b.markets) == 1
        assert len(b.markets[0].outcomes) == 2

    def test_frozen(self) -> None:
        b = ODBookmakerRaw(bookmaker_key="pk", bookmaker_title="PK")
        with pytest.raises(ValidationError):
            b.bookmaker_key = "other"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        b = ODBookmakerRaw(
            bookmaker_key="pinnacle",
            bookmaker_title="Pinnacle",
            last_update=NOW,
            markets=(),
        )
        data = b.model_dump()
        b2 = ODBookmakerRaw.model_validate(data)
        assert b == b2


# ---------------------------------------------------------------------------
# ODEventRaw — deeply nested
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestODEventRaw:
    def test_construct_minimal(self) -> None:
        e = ODEventRaw(
            event_id="abc123",
            sport_key="soccer_epl",
            sport_title="EPL",
            commence_time=NOW,
            home_team="Arsenal",
            away_team="Chelsea",
        )
        assert e.bookmakers == ()
        assert e.home_team == "Arsenal"

    def test_construct_nested(self) -> None:
        """Full nested construction: event -> bookmakers -> markets -> outcomes."""
        outcome_home = ODOutcomeRaw(name="Arsenal", price=Decimal("1.65"))
        outcome_draw = ODOutcomeRaw(name="Draw", price=Decimal("3.80"))
        outcome_away = ODOutcomeRaw(name="Chelsea", price=Decimal("5.50"))

        outcome_over = ODOutcomeRaw(name="Over", price=Decimal("1.85"), point=Decimal("2.5"))
        outcome_under = ODOutcomeRaw(name="Under", price=Decimal("1.95"), point=Decimal("2.5"))

        market_h2h = ODMarketRaw(
            market_key="h2h",
            outcomes=(outcome_home, outcome_draw, outcome_away),
        )
        market_totals = ODMarketRaw(
            market_key="totals",
            outcomes=(outcome_over, outcome_under),
        )

        bookmaker = ODBookmakerRaw(
            bookmaker_key="pinnacle",
            bookmaker_title="Pinnacle",
            last_update=NOW,
            markets=(market_h2h, market_totals),
        )

        event = ODEventRaw(
            event_id="evt-001",
            sport_key="soccer_epl",
            sport_title="EPL",
            commence_time=NOW,
            home_team="Arsenal",
            away_team="Chelsea",
            bookmakers=(bookmaker,),
        )

        assert len(event.bookmakers) == 1
        assert len(event.bookmakers[0].markets) == 2
        assert len(event.bookmakers[0].markets[0].outcomes) == 3
        assert event.bookmakers[0].markets[1].outcomes[0].point == Decimal("2.5")

    def test_from_raw_nested(self) -> None:
        """Construct deeply nested ODEventRaw from raw dict via model_validate."""
        event = ODEventRaw.model_validate(_RAW_NESTED_EVENT)
        assert event.event_id == "evt-002"
        assert len(event.bookmakers) == 2
        assert event.bookmakers[0].bookmaker_key == "bet365"
        assert event.bookmakers[1].last_update is None  # not provided
        assert len(event.bookmakers[0].markets) == 2
        assert event.bookmakers[0].markets[1].outcomes[0].point == Decimal("-0.5")

    def test_frozen(self) -> None:
        e = ODEventRaw(
            event_id="e1",
            sport_key="soccer_epl",
            sport_title="EPL",
            commence_time=NOW,
            home_team="A",
            away_team="B",
        )
        with pytest.raises(ValidationError):
            e.event_id = "e2"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        event = ODEventRaw(
            event_id="evt-rt",
            sport_key="soccer_epl",
            sport_title="EPL",
            commence_time=NOW,
            home_team="A",
            away_team="B",
            bookmakers=(
                ODBookmakerRaw(
                    bookmaker_key="pk",
                    bookmaker_title="PK",
                    markets=(
                        ODMarketRaw(
                            market_key="h2h",
                            outcomes=(
                                ODOutcomeRaw(name="A", price=Decimal("1.50")),
                                ODOutcomeRaw(name="B", price=Decimal("2.80")),
                            ),
                        ),
                    ),
                ),
            ),
        )
        data = event.model_dump()
        event2 = ODEventRaw.model_validate(data)
        assert event == event2
        assert isinstance(event2.bookmakers, tuple)
        assert isinstance(event2.bookmakers[0].markets, tuple)
        assert isinstance(event2.bookmakers[0].markets[0].outcomes, tuple)


# ---------------------------------------------------------------------------
# ODOddsRaw — flattened odds snapshot
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestODOddsRaw:
    def test_construct_h2h(self) -> None:
        o = ODOddsRaw(
            od_fixture_id="fix-001",
            home_team="Arsenal",
            away_team="Chelsea",
            commence_time=NOW,
            measurement_time=NOW,
            bookmaker_key="pinnacle",
            market="h2h",
            outcome_name="Arsenal",
            outcome_price=Decimal("1.65"),
        )
        assert o.outcome_point is None
        assert o.market == "h2h"

    def test_construct_spreads(self) -> None:
        o = ODOddsRaw(
            od_fixture_id="fix-002",
            home_team="Real Madrid",
            away_team="Barcelona",
            commence_time=NOW,
            measurement_time=NOW,
            bookmaker_key="bet365",
            market="spreads",
            outcome_name="Real Madrid",
            outcome_price=Decimal("1.91"),
            outcome_point=Decimal("-1.5"),
        )
        assert o.outcome_point == Decimal("-1.5")

    def test_construct_totals(self) -> None:
        o = ODOddsRaw(
            od_fixture_id="fix-003",
            home_team="A",
            away_team="B",
            commence_time=NOW,
            measurement_time=NOW,
            bookmaker_key="unibet",
            market="totals",
            outcome_name="Over",
            outcome_price=Decimal("1.85"),
            outcome_point=Decimal("2.5"),
        )
        assert o.outcome_name == "Over"

    def test_from_raw(self) -> None:
        o = ODOddsRaw.from_raw(
            {
                "od_fixture_id": "fix-004",
                "home_team": "A",
                "away_team": "B",
                "commence_time": NOW.isoformat(),
                "measurement_time": NOW.isoformat(),
                "bookmaker_key": "pinnacle",
                "market": "h2h",
                "outcome_name": "Draw",
                "outcome_price": 3.40,
            }
        )
        assert o.outcome_name == "Draw"
        assert o.outcome_price == Decimal("3.4")

    def test_frozen(self) -> None:
        o = ODOddsRaw(
            od_fixture_id="f1",
            home_team="A",
            away_team="B",
            commence_time=NOW,
            measurement_time=NOW,
            bookmaker_key="pk",
            market="h2h",
            outcome_name="A",
            outcome_price=Decimal("1.50"),
        )
        with pytest.raises(ValidationError):
            o.market = "spreads"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        o = ODOddsRaw(
            od_fixture_id="fix-rt",
            home_team="X",
            away_team="Y",
            commence_time=NOW,
            measurement_time=NOW,
            bookmaker_key="bet365",
            market="totals",
            outcome_name="Under",
            outcome_price=Decimal("1.95"),
            outcome_point=Decimal("2.5"),
        )
        data = o.model_dump()
        o2 = ODOddsRaw.model_validate(data)
        assert o == o2


# ---------------------------------------------------------------------------
# ODTeamsRaw — team mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestODTeamsRaw:
    def test_construct_minimal(self) -> None:
        t = ODTeamsRaw(
            league_name="Premier League",
            season="2024",
            od_team_id="arsenal",
            team_name="Arsenal",
        )
        assert t.af_league_id is None

    def test_construct_with_af_league(self) -> None:
        t = ODTeamsRaw(
            league_name="La Liga",
            af_league_id=140,
            season="2024",
            od_team_id="real-madrid",
            team_name="Real Madrid",
        )
        assert t.af_league_id == 140

    def test_from_raw(self) -> None:
        t = ODTeamsRaw.from_raw(
            {
                "league_name": "Serie A",
                "af_league_id": 135,
                "season": "2024",
                "od_team_id": "ac-milan",
                "team_name": "AC Milan",
            }
        )
        assert t.team_name == "AC Milan"

    def test_frozen(self) -> None:
        t = ODTeamsRaw(
            league_name="PL",
            season="2024",
            od_team_id="t1",
            team_name="Team",
        )
        with pytest.raises(ValidationError):
            t.team_name = "Other"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        t = ODTeamsRaw(
            league_name="Bundesliga",
            af_league_id=78,
            season="2024",
            od_team_id="bayern",
            team_name="Bayern Munich",
        )
        data = t.model_dump()
        t2 = ODTeamsRaw.model_validate(data)
        assert t == t2
