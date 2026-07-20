"""Verify canonical sports schemas: construction, validation, immutability."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.canonical.domain.sports.arbitrage import (
    ArbitrageMarket,
    ArbitrageOpportunity,
    ArbitrageStatus,
    ExpectedValue,
)
from unified_api_contracts.canonical.domain.sports.betting import (
    BetExecution,
    BetOrder,
    BetSide,
    BetStatus,
    BettingSignal,
    SignalSource,
)
from unified_api_contracts.canonical.domain.sports.bookmaker import (
    BookmakerCategory,
    BookmakerInfo,
)
from unified_api_contracts.canonical.domain.sports.fixture import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalPlayer,
    CanonicalReferee,
    CanonicalTeam,
    CanonicalVenue,
)
from unified_api_contracts.canonical.domain.sports.odds import (
    CanonicalBookmakerMarket,
    CanonicalOdds,
    MarketStatus,
    OddsType,
    OutcomeType,
)

NOW = datetime.now(tz=UTC)


def _make_team(team_id: str = "t1", name: str = "Test FC") -> CanonicalTeam:
    return CanonicalTeam(team_id=team_id, name=name, country="GB")


def _make_league() -> CanonicalLeague:
    return CanonicalLeague(league_id="l1", name="Premier League", country="GB")


@pytest.mark.unit
class TestCanonicalVenue:
    def test_construct_valid(self) -> None:
        v = CanonicalVenue(venue_id="v1", name="Old Trafford", city="Manchester")
        assert v.venue_id == "v1"
        assert v.city == "Manchester"

    def test_missing_required_field(self) -> None:
        with pytest.raises((TypeError, ValueError)):
            CanonicalVenue(name="Stadium")  # type: ignore[call-arg]

    def test_from_raw(self) -> None:
        v = CanonicalVenue.from_raw({"venue_id": "v2", "name": "Anfield"})
        assert v.name == "Anfield"

    def test_frozen(self) -> None:
        v = CanonicalVenue(venue_id="v1", name="Stadium")
        with pytest.raises(ValidationError):
            v.name = "Other"  # type: ignore[misc]


@pytest.mark.unit
class TestCanonicalReferee:
    def test_construct_valid(self) -> None:
        r = CanonicalReferee(referee_id="r1", name="Michael Oliver")
        assert r.referee_id == "r1"

    def test_missing_required(self) -> None:
        with pytest.raises((TypeError, ValidationError)):
            CanonicalReferee(name="Oliver")  # type: ignore[call-arg]


@pytest.mark.unit
class TestCanonicalPlayer:
    def test_construct_valid(self) -> None:
        p = CanonicalPlayer(player_id="p1", name="Marcus Rashford", position="Forward")
        assert p.position == "Forward"

    def test_optional_fields_default_none(self) -> None:
        p = CanonicalPlayer(player_id="p1", name="Test")
        assert p.nationality is None
        assert p.height_cm is None


@pytest.mark.unit
class TestCanonicalTeam:
    def test_construct_valid(self) -> None:
        t = _make_team()
        assert t.team_id == "t1"

    def test_with_venue(self) -> None:
        v = CanonicalVenue(venue_id="v1", name="Stadium")
        t = CanonicalTeam(team_id="t1", name="FC", country="GB", venue=v)
        assert t.venue is not None
        assert t.venue.name == "Stadium"


@pytest.mark.unit
class TestCanonicalLeague:
    def test_construct_valid(self) -> None:
        lg = _make_league()
        assert lg.country == "GB"

    def test_missing_country(self) -> None:
        with pytest.raises((TypeError, ValidationError)):
            CanonicalLeague(league_id="l1", name="PL")  # type: ignore[call-arg]


@pytest.mark.unit
class TestCanonicalFixture:
    def test_construct_valid(self) -> None:
        f = CanonicalFixture(
            fixture_id="af:12345",
            home_team=_make_team("h1", "Home FC"),
            away_team=_make_team("a1", "Away FC"),
            league=_make_league(),
            kickoff_utc=NOW,
            season="2024-25",
            source="api_football",
        )
        assert f.fixture_id == "af:12345"
        assert f.venue is None
        assert f.match_week is None

    def test_missing_required(self) -> None:
        with pytest.raises((TypeError, ValidationError)):
            CanonicalFixture(
                fixture_id="af:1",
                home_team=_make_team(),
                away_team=_make_team(),
                league=_make_league(),
                kickoff_utc=NOW,
                source="api_football",
            )  # type: ignore[call-arg]


@pytest.mark.unit
class TestCanonicalOdds:
    def test_construct_valid(self) -> None:
        o = CanonicalOdds(
            fixture_id="af:1",
            bookmaker_key="betfair",
            market=OddsType.H2H,
            home_odds=Decimal("2.10"),
            draw_odds=Decimal("3.50"),
            away_odds=Decimal("3.80"),
            timestamp_utc=NOW,
            source="betfair",
        )
        assert o.market == OddsType.H2H
        assert o.home_odds == Decimal("2.10")

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalOdds(
                fixture_id="af:1",
                bookmaker_key="betfair",
                market="invalid_market",  # type: ignore[arg-type]
                timestamp_utc="not-a-datetime",  # type: ignore[arg-type]
                source="betfair",
            )

    def test_lay_fields_default_none(self) -> None:
        """Back-only bookmakers leave lay prices unset (honest-None)."""
        o = CanonicalOdds(
            fixture_id="af:1",
            bookmaker_key="pinnacle",
            market=OddsType.H2H,
            home_odds=Decimal("2.10"),
            timestamp_utc=NOW,
            source="pinnacle",
        )
        assert o.home_lay_odds is None
        assert o.draw_lay_odds is None
        assert o.away_lay_odds is None

    def test_lay_fields_populated(self) -> None:
        """A lay-capable exchange can carry both back and lay prices."""
        o = CanonicalOdds(
            fixture_id="af:1",
            bookmaker_key="betfair",
            market=OddsType.H2H,
            home_odds=Decimal("2.10"),
            draw_odds=Decimal("3.50"),
            away_odds=Decimal("3.80"),
            home_lay_odds=Decimal("2.12"),
            draw_lay_odds=Decimal("3.55"),
            away_lay_odds=Decimal("3.90"),
            timestamp_utc=NOW,
            source="betfair",
        )
        assert o.home_lay_odds == Decimal("2.12")
        assert o.draw_lay_odds == Decimal("3.55")
        assert o.away_lay_odds == Decimal("3.90")


@pytest.mark.unit
class TestCanonicalBookmakerMarket:
    def test_construct_valid(self) -> None:
        m = CanonicalBookmakerMarket(
            bookmaker_key="pinnacle",
            market=OddsType.OVER_UNDER,
            outcomes={"over": Decimal("1.95"), "under": Decimal("1.95")},
        )
        assert m.bookmaker_key == "pinnacle"


@pytest.mark.unit
class TestOddsEnums:
    def test_odds_type_values(self) -> None:
        assert OddsType.H2H == "h2h"
        assert OddsType.ASIAN_HANDICAP == "asian_handicap"

    def test_outcome_type_values(self) -> None:
        assert OutcomeType.HOME == "home"
        assert OutcomeType.OVER == "over"

    def test_market_status_values(self) -> None:
        assert MarketStatus.ACTIVE == "active"
        assert MarketStatus.SETTLED == "settled"


@pytest.mark.unit
class TestBettingSignal:
    def test_construct_valid(self) -> None:
        s = BettingSignal(
            signal_id="sig1",
            fixture_id="af:1",
            market=OddsType.H2H,
            selection="HOME",
            confidence=Decimal("0.75"),
            expected_value=Decimal("1.12"),
            source=SignalSource.ML_MODEL,
            created_at_utc=NOW,
        )
        assert s.source == SignalSource.ML_MODEL


@pytest.mark.unit
class TestBetOrder:
    def test_construct_valid(self) -> None:
        o = BetOrder(
            order_id="ord1",
            fixture_id="af:1",
            bookmaker_key="betfair",
            market=OddsType.H2H,
            selection="HOME",
            requested_odds=Decimal("2.10"),
            stake=Decimal("50.00"),
            max_acceptable_odds=Decimal("2.00"),
            strategy_source=SignalSource.ARBITRAGE,
            created_at_utc=NOW,
        )
        assert o.stake == Decimal("50.00")

    def test_side_defaults_to_back(self) -> None:
        """Existing callers that omit ``side`` remain valid and default to BACK."""
        o = BetOrder(
            order_id="ord1",
            fixture_id="af:1",
            bookmaker_key="betfair",
            market=OddsType.H2H,
            selection="HOME",
            requested_odds=Decimal("2.10"),
            stake=Decimal("50.00"),
            max_acceptable_odds=Decimal("2.00"),
            strategy_source=SignalSource.ARBITRAGE,
            created_at_utc=NOW,
        )
        assert o.side is BetSide.BACK

    def test_side_lay_explicit(self) -> None:
        o = BetOrder(
            order_id="ord2",
            fixture_id="af:1",
            bookmaker_key="betfair",
            market=OddsType.H2H,
            selection="HOME",
            requested_odds=Decimal("2.10"),
            stake=Decimal("50.00"),
            max_acceptable_odds=Decimal("2.20"),
            strategy_source=SignalSource.ARBITRAGE,
            side=BetSide.LAY,
            created_at_utc=NOW,
        )
        assert o.side is BetSide.LAY

    def test_side_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            BetOrder(
                order_id="ord3",
                fixture_id="af:1",
                bookmaker_key="betfair",
                market=OddsType.H2H,
                selection="HOME",
                requested_odds=Decimal("2.10"),
                stake=Decimal("50.00"),
                max_acceptable_odds=Decimal("2.00"),
                strategy_source=SignalSource.ARBITRAGE,
                side="sideways",  # type: ignore[arg-type]
                created_at_utc=NOW,
            )


@pytest.mark.unit
class TestBetExecution:
    def test_construct_valid(self) -> None:
        e = BetExecution(
            execution_id="exec1",
            order_id="ord1",
            status=BetStatus.PLACED,
            executed_at_utc=NOW,
        )
        assert e.status == BetStatus.PLACED
        assert e.bet_id is None

    def test_bet_status_values(self) -> None:
        assert BetStatus.SETTLED_WIN == "settled_win"
        assert BetStatus.CANCELLED == "cancelled"


@pytest.mark.unit
class TestArbitrageMarket:
    def test_construct_valid(self) -> None:
        am = ArbitrageMarket(
            bookmaker_key="betfair",
            selection="HOME",
            odds=Decimal("2.20"),
            implied_prob=Decimal("0.4545"),
        )
        assert am.max_stake is None


@pytest.mark.unit
class TestExpectedValue:
    def test_construct_valid(self) -> None:
        ev = ExpectedValue(
            fixture_id="af:1",
            market=OddsType.H2H,
            selection="HOME",
            bookmaker_key="pinnacle",
            offered_odds=Decimal("2.20"),
            fair_odds=Decimal("2.00"),
            edge_pct=Decimal("10.0"),
        )
        assert ev.kelly_fraction is None


@pytest.mark.unit
class TestArbitrageOpportunity:
    def test_construct_valid(self) -> None:
        legs = [
            ArbitrageMarket(
                bookmaker_key="betfair",
                selection="HOME",
                odds=Decimal("2.20"),
                implied_prob=Decimal("0.4545"),
            ),
            ArbitrageMarket(
                bookmaker_key="pinnacle",
                selection="AWAY",
                odds=Decimal("2.10"),
                implied_prob=Decimal("0.4762"),
            ),
        ]
        arb = ArbitrageOpportunity(
            opportunity_id="arb1",
            fixture_id="af:1",
            market=OddsType.H2H,
            legs=legs,
            total_implied_prob=Decimal("0.9307"),
            expected_return_pct=Decimal("7.45"),
            detected_at_utc=NOW,
            status=ArbitrageStatus.DETECTED,
        )
        assert len(arb.legs) == 2
        assert arb.status == ArbitrageStatus.DETECTED


@pytest.mark.unit
class TestBookmakerInfo:
    def test_construct_valid(self) -> None:
        bi = BookmakerInfo(
            key="test",
            display_name="Test Book",
            category=BookmakerCategory.SCRAPER,
            currency="GBP",
            supports_live_betting=True,
            supports_cash_out=False,
            min_bet_gbp=Decimal("0.10"),
        )
        assert bi.category == BookmakerCategory.SCRAPER

    def test_from_raw(self) -> None:
        bi = BookmakerInfo.from_raw(
            {
                "key": "test",
                "display_name": "Test",
                "category": "exchange",
                "currency": "GBP",
                "supports_live_betting": True,
                "supports_cash_out": False,
                "min_bet_gbp": 1,
            }
        )
        assert bi.category == BookmakerCategory.EXCHANGE
