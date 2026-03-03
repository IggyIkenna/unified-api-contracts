"""Verify live-mode canonical schemas: LiveOddsUpdate, LiveMatchState, ScraperVersionMeta."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.sports.canonical.live import (
    LiveMatchState,
    LiveOddsUpdate,
    MatchPeriod,
    ScraperVersionMeta,
)
from unified_api_contracts.sports.canonical.odds import CanonicalOdds, OddsType

NOW = datetime.now(tz=UTC)


def _make_odds() -> CanonicalOdds:
    return CanonicalOdds(
        fixture_id="af:12345",
        bookmaker_key="betfair",
        market=OddsType.H2H,
        home_odds=Decimal("2.10"),
        draw_odds=Decimal("3.50"),
        away_odds=Decimal("3.80"),
        timestamp_utc=NOW,
        source="betfair",
    )


@pytest.mark.unit
class TestMatchPeriod:
    def test_values(self) -> None:
        assert MatchPeriod.FIRST_HALF == "1H"
        assert MatchPeriod.HALF_TIME == "HT"
        assert MatchPeriod.SECOND_HALF == "2H"
        assert MatchPeriod.FULL_TIME == "FT"
        assert MatchPeriod.PENALTIES == "PEN"

    def test_all_periods_exist(self) -> None:
        assert len(MatchPeriod) == 10


@pytest.mark.unit
class TestLiveOddsUpdate:
    def test_construct_valid(self) -> None:
        update = LiveOddsUpdate(
            fixture_id="af:12345",
            bookmaker_key="betfair",
            timestamp_utc=NOW,
            is_in_play=True,
            match_minute=45,
            odds=_make_odds(),
            source_tier="exchange",
        )
        assert update.event_type == "ODDS_UPDATE"
        assert update.is_in_play is True
        assert update.match_minute == 45
        assert update.odds.home_odds == Decimal("2.10")

    def test_pre_match_no_minute(self) -> None:
        update = LiveOddsUpdate(
            fixture_id="af:12345",
            bookmaker_key="odds_api",
            timestamp_utc=NOW,
            is_in_play=False,
            match_minute=None,
            odds=_make_odds(),
            source_tier="odds_api",
        )
        assert update.match_minute is None
        assert update.source_tier == "odds_api"

    def test_frozen(self) -> None:
        update = LiveOddsUpdate(
            fixture_id="af:12345",
            bookmaker_key="betfair",
            timestamp_utc=NOW,
            is_in_play=True,
            match_minute=45,
            odds=_make_odds(),
            source_tier="exchange",
        )
        with pytest.raises(ValidationError):
            update.is_in_play = False  # type: ignore[misc]

    def test_from_raw(self) -> None:
        data = {
            "fixture_id": "af:12345",
            "bookmaker_key": "opticodds",
            "timestamp_utc": NOW.isoformat(),
            "is_in_play": True,
            "match_minute": 67,
            "odds": _make_odds().model_dump(),
            "source_tier": "opticodds",
        }
        update = LiveOddsUpdate.model_validate(data)
        assert update.source_tier == "opticodds"

    def test_source_tiers(self) -> None:
        for tier in ("odds_api", "opticodds", "oddsjam", "scraper", "exchange"):
            update = LiveOddsUpdate(
                fixture_id="af:1",
                bookmaker_key="test",
                timestamp_utc=NOW,
                is_in_play=False,
                odds=_make_odds(),
                source_tier=tier,
            )
            assert update.source_tier == tier


@pytest.mark.unit
class TestLiveMatchState:
    def test_construct_valid(self) -> None:
        state = LiveMatchState(
            fixture_id="af:12345",
            timestamp_utc=NOW,
            period=MatchPeriod.SECOND_HALF,
            match_minute=67,
            is_live=True,
            home_score=2,
            away_score=1,
        )
        assert state.period == MatchPeriod.SECOND_HALF
        assert state.home_score == 2
        assert state.stoppage_time == 0

    def test_with_red_cards(self) -> None:
        state = LiveMatchState(
            fixture_id="af:12345",
            timestamp_utc=NOW,
            period=MatchPeriod.SECOND_HALF,
            match_minute=80,
            is_live=True,
            home_score=1,
            away_score=0,
            home_red_cards=1,
            away_red_cards=0,
        )
        assert state.home_red_cards == 1

    def test_penalties(self) -> None:
        state = LiveMatchState(
            fixture_id="af:12345",
            timestamp_utc=NOW,
            period=MatchPeriod.PENALTIES,
            match_minute=120,
            is_live=True,
            home_score=2,
            away_score=2,
            home_penalties=4,
            away_penalties=3,
        )
        assert state.home_penalties == 4
        assert state.away_penalties == 3

    def test_frozen(self) -> None:
        state = LiveMatchState(
            fixture_id="af:12345",
            timestamp_utc=NOW,
            period=MatchPeriod.FIRST_HALF,
            match_minute=30,
            is_live=True,
            home_score=0,
            away_score=0,
        )
        with pytest.raises(ValidationError):
            state.home_score = 1  # type: ignore[misc]

    def test_from_raw(self) -> None:
        state = LiveMatchState.from_raw(
            {
                "fixture_id": "af:1",
                "timestamp_utc": NOW.isoformat(),
                "period": "1H",
                "match_minute": 15,
                "is_live": True,
                "home_score": 0,
                "away_score": 0,
            }
        )
        assert state.period == MatchPeriod.FIRST_HALF


@pytest.mark.unit
class TestScraperVersionMeta:
    def test_construct_valid(self) -> None:
        meta = ScraperVersionMeta(
            bookmaker_key="bet365",
            scraper_schema_version="bet365-v3",
            css_selector_hash="abc123def456",
            last_validated_utc=NOW,
            page_structure_version="2026-03-01",
        )
        assert meta.is_stale is False
        assert meta.last_error is None

    def test_stale_with_error(self) -> None:
        meta = ScraperVersionMeta(
            bookmaker_key="williamhill",
            scraper_schema_version="williamhill-v2",
            css_selector_hash="xyz789",
            last_validated_utc=NOW,
            page_structure_version="2026-02-15",
            is_stale=True,
            last_error="CSS selector .gl-MarketOdds not found",
        )
        assert meta.is_stale is True
        assert "CSS selector" in (meta.last_error or "")

    def test_frozen(self) -> None:
        meta = ScraperVersionMeta(
            bookmaker_key="bet365",
            scraper_schema_version="bet365-v3",
            css_selector_hash="abc123",
            last_validated_utc=NOW,
            page_structure_version="2026-03-01",
        )
        with pytest.raises(ValidationError):
            meta.is_stale = True  # type: ignore[misc]

    def test_from_raw(self) -> None:
        meta = ScraperVersionMeta.from_raw(
            {
                "bookmaker_key": "coral",
                "scraper_schema_version": "coral-v1",
                "css_selector_hash": "hash123",
                "last_validated_utc": NOW.isoformat(),
                "page_structure_version": "2026-03-02",
            }
        )
        assert meta.bookmaker_key == "coral"


@pytest.mark.unit
class TestLiveSchemaExports:
    def test_import_from_canonical(self) -> None:
        from unified_api_contracts.sports.canonical import (
            LiveMatchState,
            LiveOddsUpdate,
            MatchPeriod,
            ScraperVersionMeta,
        )

        assert all([LiveMatchState, LiveOddsUpdate, MatchPeriod, ScraperVersionMeta])

    def test_import_from_sports(self) -> None:
        from unified_api_contracts.sports import (
            LiveMatchState,
            LiveOddsUpdate,
            MatchPeriod,
            ScraperVersionMeta,
        )

        assert all([LiveMatchState, LiveOddsUpdate, MatchPeriod, ScraperVersionMeta])
