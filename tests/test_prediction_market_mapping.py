"""Tests for canonical prediction market mapping system."""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.prediction import (
    MappingRule,
    OrphanDetector,
    PredictionMarketCategory,
    PredictionMarketMapper,
)


class TestPolymarketMapping:
    """Test mapping Polymarket questions to canonical prediction markets."""

    def test_political_question_maps_to_politics(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-12345",
            question="Will Biden win the 2024 presidential election?",
        )
        assert result.category == PredictionMarketCategory.POLITICS
        assert result.source_venue == "polymarket"
        assert result.source_market_id == "pm-12345"
        assert result.canonical_id.startswith("PRED:politics:")

    def test_outcomes_default_to_binary(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-99",
            question="Will Congress pass the spending bill?",
        )
        assert result.outcomes == ("YES", "NO")


class TestKalshiMapping:
    """Test mapping Kalshi questions to canonical prediction markets."""

    def test_financial_question_maps_to_financial(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="kalshi",
            market_id="kalshi-fed-rate-001",
            question="Will the Fed raise the interest rate above 5% by December?",
        )
        assert result.category == PredictionMarketCategory.FINANCIAL
        assert result.source_venue == "kalshi"
        assert result.canonical_id.startswith("PRED:financial:")

    def test_inflation_question_maps_to_financial(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="kalshi",
            market_id="kalshi-inflation-001",
            question="Will US inflation exceed 4% in Q3 2026?",
        )
        assert result.category == PredictionMarketCategory.FINANCIAL


class TestSportsMapping:
    """Test mapping sports questions to canonical prediction markets."""

    def test_sports_question_maps_to_sports(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-sport-001",
            question="Will Manchester City win the Premier League championship?",
        )
        assert result.category == PredictionMarketCategory.SPORTS
        assert result.canonical_id.startswith("PRED:sports:")

    def test_sports_with_mapped_event_id(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-super-bowl",
            question="Who will win the Super Bowl?",
            mapped_sport_event_id="FIXTURE:NFL:SB2026",
        )
        assert result.category == PredictionMarketCategory.SPORTS
        assert result.mapped_sport_event_id == "FIXTURE:NFL:SB2026"


class TestCrossVenueMatching:
    """Test cross-venue matching when the same question appears on multiple venues."""

    def test_same_question_on_two_venues_matches(self) -> None:
        mapper = PredictionMarketMapper()
        question = "Will the Fed raise interest rate by December 2026?"

        poly = mapper.map_market(venue="polymarket", market_id="pm-fed-1", question=question)
        kalshi = mapper.map_market(venue="kalshi", market_id="k-fed-1", question=question)

        # Same canonical_id because same normalized question
        assert poly.canonical_id == kalshi.canonical_id

        all_markets = [poly, kalshi]
        matches = mapper.find_cross_venue_matches(poly, all_markets)
        assert len(matches) == 1
        assert matches[0].source_venue == "kalshi"

    def test_no_self_match(self) -> None:
        mapper = PredictionMarketMapper()
        m = mapper.map_market(venue="polymarket", market_id="pm-1", question="Will it rain tomorrow?")
        matches = mapper.find_cross_venue_matches(m, [m])
        assert len(matches) == 0

    def test_different_questions_no_match(self) -> None:
        mapper = PredictionMarketMapper()
        m1 = mapper.map_market(venue="polymarket", market_id="pm-1", question="Will it rain tomorrow?")
        m2 = mapper.map_market(venue="kalshi", market_id="k-1", question="Will the sun shine tomorrow?")
        matches = mapper.find_cross_venue_matches(m1, [m1, m2])
        assert len(matches) == 0


class TestOrphanDetection:
    """Test orphan detection for unclassifiable markets."""

    def test_unclassifiable_question_is_orphan(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="manifold",
            market_id="mf-999",
            question="Will my cat learn to fetch by next Tuesday?",
        )
        assert result.category == PredictionMarketCategory.OTHER

        detector = OrphanDetector()
        orphans = detector.detect_orphans([result])
        assert len(orphans) == 1
        assert orphans[0].source_market_id == "mf-999"

    def test_classified_market_is_not_orphan(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-el",
            question="Will the election see record turnout?",
        )
        assert result.category == PredictionMarketCategory.POLITICS

        detector = OrphanDetector()
        orphans = detector.detect_orphans([result])
        assert len(orphans) == 0


class TestCanonicalIdDeterminism:
    """Test that canonical IDs are deterministic and stable."""

    def test_same_input_same_id(self) -> None:
        mapper = PredictionMarketMapper()
        r1 = mapper.map_market(venue="polymarket", market_id="pm-1", question="Will BTC reach 100k?")
        r2 = mapper.map_market(venue="kalshi", market_id="k-1", question="Will BTC reach 100k?")
        # Different venue/market_id, same question => same canonical_id
        assert r1.canonical_id == r2.canonical_id

    def test_different_questions_different_ids(self) -> None:
        mapper = PredictionMarketMapper()
        r1 = mapper.map_market(venue="polymarket", market_id="pm-1", question="Will ETH reach 10k?")
        r2 = mapper.map_market(venue="polymarket", market_id="pm-2", question="Will SOL reach 500?")
        assert r1.canonical_id != r2.canonical_id

    def test_canonical_id_format(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-1",
            question="Will the next president be a woman?",
        )
        parts = result.canonical_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "PRED"
        assert parts[1] == "politics"
        assert len(parts[2]) == 12  # 12 hex chars from sha256


class TestCustomRulesOverride:
    """Test that custom rules can override default categorization."""

    def test_custom_rule_higher_priority_wins(self) -> None:
        custom = [
            MappingRule(
                keywords=("cat", "fetch"),
                category=PredictionMarketCategory.ENTERTAINMENT,
                priority=100,
            ),
        ]
        mapper = PredictionMarketMapper(custom_rules=custom)
        result = mapper.map_market(
            venue="manifold",
            market_id="mf-cat",
            question="Will my cat learn to fetch by next Tuesday?",
        )
        # Custom rule at priority=100 matches "cat" and overrides OTHER
        assert result.category == PredictionMarketCategory.ENTERTAINMENT

    def test_custom_rule_lower_priority_loses_to_default(self) -> None:
        custom = [
            MappingRule(
                keywords=("will",),
                category=PredictionMarketCategory.OTHER,
                priority=0,
            ),
        ]
        mapper = PredictionMarketMapper(custom_rules=custom)
        result = mapper.map_market(
            venue="kalshi",
            market_id="k-1",
            question="Will the election see record turnout?",
        )
        # Default POLITICS rule (priority=10) beats custom (priority=0)
        assert result.category == PredictionMarketCategory.POLITICS


class TestNormalizedQuestion:
    """Test whitespace and case normalization."""

    def test_whitespace_collapsed(self) -> None:
        mapper = PredictionMarketMapper()
        r1 = mapper.map_market(
            venue="polymarket",
            market_id="pm-1",
            question="Will   the  election    happen?",
        )
        r2 = mapper.map_market(
            venue="polymarket",
            market_id="pm-2",
            question="Will the election happen?",
        )
        assert r1.question_normalized == r2.question_normalized
        assert r1.canonical_id == r2.canonical_id

    def test_case_insensitive(self) -> None:
        mapper = PredictionMarketMapper()
        r1 = mapper.map_market(
            venue="polymarket",
            market_id="pm-1",
            question="Will The ELECTION Happen?",
        )
        r2 = mapper.map_market(
            venue="polymarket",
            market_id="pm-2",
            question="will the election happen?",
        )
        assert r1.question_normalized == r2.question_normalized
        assert r1.canonical_id == r2.canonical_id

    def test_leading_trailing_whitespace_stripped(self) -> None:
        mapper = PredictionMarketMapper()
        r1 = mapper.map_market(
            venue="polymarket",
            market_id="pm-1",
            question="  Will it rain?  ",
        )
        assert r1.question_normalized == "will it rain?"


class TestCategoryKeywords:
    """Test that each category triggers correctly on expected keywords."""

    def test_crypto_category(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-crypto",
            question="Will Ethereum merge to proof of stake in 2026?",
        )
        assert result.category == PredictionMarketCategory.CRYPTO

    def test_weather_category(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="kalshi",
            market_id="k-weather",
            question="Will a hurricane hit Florida this season?",
        )
        assert result.category == PredictionMarketCategory.WEATHER

    def test_entertainment_category(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="manifold",
            market_id="mf-oscar",
            question="Will Oppenheimer take home the Oscar for best picture?",
        )
        assert result.category == PredictionMarketCategory.ENTERTAINMENT


class TestResolutionDate:
    """Test resolution date propagation."""

    def test_resolution_date_stored(self) -> None:
        mapper = PredictionMarketMapper()
        dt = datetime(2026, 12, 31, tzinfo=UTC)
        result = mapper.map_market(
            venue="kalshi",
            market_id="k-1",
            question="Will GDP grow above 3% in 2026?",
            resolution_date=dt,
        )
        assert result.resolution_date == dt

    def test_resolution_date_none_by_default(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-1",
            question="Will the election happen?",
        )
        assert result.resolution_date is None


class TestMappedInstrumentId:
    """Test financial instrument linkage."""

    def test_mapped_instrument_id_stored(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="kalshi",
            market_id="k-sp500",
            question="Will the S&P 500 close above 5000?",
            mapped_instrument_id="INST:SP500:IDX",
        )
        assert result.mapped_instrument_id == "INST:SP500:IDX"
        assert result.category == PredictionMarketCategory.FINANCIAL


class TestModelFrozen:
    """Test that CanonicalPredictionMarket is immutable."""

    def test_cannot_mutate_market(self) -> None:
        mapper = PredictionMarketMapper()
        result = mapper.map_market(
            venue="polymarket",
            market_id="pm-1",
            question="Will the election happen?",
        )
        import pytest

        with pytest.raises(Exception):
            result.category = PredictionMarketCategory.SPORTS  # type: ignore[misc]
