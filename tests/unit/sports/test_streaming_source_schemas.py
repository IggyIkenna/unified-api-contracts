"""Verify OpticOdds and OddsJam source schemas: construction, from_raw(), immutability."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.external.sports.sources.oddsjam.schemas import (
    OddsJamGame,
    OddsJamMarket,
    OddsJamOdds,
)
from unified_api_contracts.external.sports.sources.opticodds.schemas import (
    OpticOddsFixture,
    OpticOddsMarket,
    OpticOddsSportsbook,
)

NOW = datetime.now(tz=UTC)


@pytest.mark.unit
class TestOpticOddsSchemas:
    def test_market_construct(self) -> None:
        m = OpticOddsMarket(
            market_id="m1",
            market_type="moneyline",
            home_odds=Decimal("2.10"),
            draw_odds=Decimal("3.50"),
            away_odds=Decimal("3.80"),
            is_live=True,
            last_updated=NOW,
        )
        assert m.market_type == "moneyline"
        assert m.is_live is True

    def test_market_optional_fields(self) -> None:
        m = OpticOddsMarket(market_id="m2", market_type="total")
        assert m.home_odds is None
        assert m.line is None
        assert m.is_live is False

    def test_sportsbook_construct(self) -> None:
        market = OpticOddsMarket(
            market_id="m1",
            market_type="moneyline",
            home_odds=Decimal("2.10"),
        )
        sb = OpticOddsSportsbook(
            sportsbook_id="sb1",
            sportsbook_name="Betfair",
            markets=[market],
        )
        assert len(sb.markets) == 1
        assert sb.sportsbook_name == "Betfair"

    def test_fixture_construct(self) -> None:
        fixture = OpticOddsFixture(
            fixture_id="fix1",
            sport="soccer",
            league="EPL",
            home_team="Man Utd",
            away_team="Liverpool",
            start_time=NOW,
            is_live=True,
            sportsbooks=[],
        )
        assert fixture.sport == "soccer"
        assert fixture.is_live is True

    def test_fixture_frozen(self) -> None:
        fixture = OpticOddsFixture(
            fixture_id="fix1",
            sport="soccer",
            league="EPL",
            home_team="A",
            away_team="B",
            start_time=NOW,
            sportsbooks=[],
        )
        with pytest.raises(ValidationError):
            fixture.is_live = True  # type: ignore[misc]

    def test_market_from_raw(self) -> None:
        m = OpticOddsMarket.from_raw(
            {
                "market_id": "m3",
                "market_type": "spread",
                "line": 1.5,
                "home_odds": 1.85,
                "away_odds": 2.05,
            }
        )
        assert m.line == Decimal("1.5")

    def test_fixture_round_trip(self) -> None:
        market = OpticOddsMarket(market_id="m1", market_type="moneyline")
        sb = OpticOddsSportsbook(sportsbook_id="s1", sportsbook_name="Test", markets=[market])
        fixture = OpticOddsFixture(
            fixture_id="f1",
            sport="soccer",
            league="EPL",
            home_team="A",
            away_team="B",
            start_time=NOW,
            sportsbooks=[sb],
        )
        data = fixture.model_dump()
        f2 = OpticOddsFixture.model_validate(data)
        assert f2.sportsbooks[0].markets[0].market_type == "moneyline"


@pytest.mark.unit
class TestOddsJamSchemas:
    def test_odds_construct(self) -> None:
        o = OddsJamOdds(
            sportsbook="bet365",
            odds=Decimal("2.10"),
            is_main=True,
            last_updated=NOW,
        )
        assert o.sportsbook == "bet365"
        assert o.odds == Decimal("2.10")

    def test_odds_optional_fields(self) -> None:
        o = OddsJamOdds(sportsbook="pinnacle", odds=Decimal("1.95"))
        assert o.is_main is True
        assert o.last_updated is None

    def test_market_construct(self) -> None:
        odds = OddsJamOdds(sportsbook="bet365", odds=Decimal("2.10"))
        m = OddsJamMarket(
            market_name="moneyline",
            bet_name="home",
            odds_list=[odds],
        )
        assert m.market_name == "moneyline"
        assert m.line is None

    def test_market_with_line(self) -> None:
        m = OddsJamMarket(
            market_name="total",
            bet_name="over",
            line=Decimal("2.5"),
            odds_list=[],
        )
        assert m.line == Decimal("2.5")

    def test_game_construct(self) -> None:
        game = OddsJamGame(
            game_id="g1",
            sport="soccer",
            league="EPL",
            home_team="Man City",
            away_team="Arsenal",
            start_date=NOW,
            is_live=False,
            markets=[],
        )
        assert game.sport == "soccer"
        assert game.is_live is False

    def test_game_frozen(self) -> None:
        game = OddsJamGame(
            game_id="g1",
            sport="soccer",
            league="EPL",
            home_team="A",
            away_team="B",
            start_date=NOW,
            markets=[],
        )
        with pytest.raises(ValidationError):
            game.is_live = True  # type: ignore[misc]

    def test_odds_from_raw(self) -> None:
        o = OddsJamOdds.from_raw({"sportsbook": "pinnacle", "odds": 1.95})
        assert o.odds == Decimal("1.95")

    def test_game_round_trip(self) -> None:
        odds = OddsJamOdds(sportsbook="bet365", odds=Decimal("2.10"))
        market = OddsJamMarket(market_name="moneyline", bet_name="home", odds_list=[odds])
        game = OddsJamGame(
            game_id="g1",
            sport="soccer",
            league="EPL",
            home_team="A",
            away_team="B",
            start_date=NOW,
            markets=[market],
        )
        data = game.model_dump()
        g2 = OddsJamGame.model_validate(data)
        assert g2.markets[0].odds_list[0].sportsbook == "bet365"


@pytest.mark.unit
class TestStreamingSourceExports:
    def test_import_opticodds(self) -> None:
        from unified_api_contracts.external.sports.sources.opticodds import (
            OpticOddsFixture,
            OpticOddsMarket,
            OpticOddsSportsbook,
        )

        assert all([OpticOddsFixture, OpticOddsMarket, OpticOddsSportsbook])

    def test_import_oddsjam(self) -> None:
        from unified_api_contracts.external.sports.sources.oddsjam import (
            OddsJamGame,
            OddsJamMarket,
            OddsJamOdds,
        )

        assert all([OddsJamGame, OddsJamMarket, OddsJamOdds])
