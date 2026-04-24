"""Verify OpticOdds source schemas: construction, from_raw(), immutability."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.external.opticodds.schemas import (
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
class TestStreamingSourceExports:
    def test_import_opticodds(self) -> None:
        from unified_api_contracts.external.opticodds import (
            OpticOddsFixture,
            OpticOddsMarket,
            OpticOddsSportsbook,
        )

        assert all([OpticOddsFixture, OpticOddsMarket, OpticOddsSportsbook])
