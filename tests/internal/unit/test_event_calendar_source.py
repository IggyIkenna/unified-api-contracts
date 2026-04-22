"""Tests for G2.9 gap #5 — EventCalendarSourceCapability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.event_calendar_source import (
    CONSUMER_CALL_SITES,
    EVENT_CALENDAR_SOURCES,
    EventCalendarSource,
    EventCategory,
    EventSourceNotFoundError,
    EventSourceType,
    _validate_registry_invariants,
    source_for,
    sources_covering,
    sources_covering_market,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(EVENT_CALENDAR_SOURCES) >= 6

    def test_source_ids_unique(self) -> None:
        ids = [e.source_id for e in EVENT_CALENDAR_SOURCES]
        assert len(ids) == len(set(ids))


class TestContent:
    def test_bloomberg_macro_covers_macro_release(self) -> None:
        src = source_for("bloomberg_macro")
        assert src.source_type is EventSourceType.MACRO_CONSENSUS
        assert EventCategory.MACRO_RELEASE in src.covered_categories
        assert "US" in src.covered_markets

    def test_token_unlocks_covers_token_unlock(self) -> None:
        src = source_for("token_unlocks_io")
        assert EventCategory.TOKEN_UNLOCK in src.covered_categories
        assert src.api_auth_model == "public"

    def test_snapshot_gov_covers_governance(self) -> None:
        src = source_for("snapshot_gov")
        assert EventCategory.GOVERNANCE_VOTE in src.covered_categories

    def test_sharp_api_sports(self) -> None:
        src = source_for("sharp_api_sports")
        assert EventCategory.SPORTS_LINEUP_RELEASE in src.covered_categories
        assert EventCategory.SPORTS_INJURY_NEWS in src.covered_categories
        assert "NFL" in src.covered_markets


class TestHelpers:
    def test_unknown_source_raises(self) -> None:
        with pytest.raises(EventSourceNotFoundError):
            source_for("nonexistent_source")

    def test_sources_covering_macro_release(self) -> None:
        results = sources_covering(EventCategory.MACRO_RELEASE)
        ids = {r.source_id for r in results}
        assert "bloomberg_macro" in ids
        assert "trading_economics_macro" in ids

    def test_sources_covering_earnings(self) -> None:
        results = sources_covering(EventCategory.EARNINGS)
        assert len(results) >= 1
        assert all(EventCategory.EARNINGS in r.covered_categories for r in results)

    def test_sources_covering_market_us(self) -> None:
        results = sources_covering_market("US")
        assert any(r.source_id == "bloomberg_macro" for r in results)

    def test_sources_covering_unknown_market(self) -> None:
        # Empty tuple rather than raising — sources can silently lack a market.
        assert sources_covering_market("MADE_UP_MARKET") == ()

    def test_sources_covering_ethereum_governance_token(self) -> None:
        results = sources_covering_market("ETHEREUM:AAVE")
        assert len(results) == 1
        assert results[0].source_id == "snapshot_gov"


class TestInvariants:
    def test_duplicate_source_id_rejected(self) -> None:
        bad = (
            EventCalendarSource(
                source_id="dup",
                source_type=EventSourceType.MACRO_CONSENSUS,
                covered_categories=(EventCategory.MACRO_RELEASE,),
                covered_markets=("US",),
                ingestion_latency_sla_seconds=10,
                data_freshness_ref="x",
                api_auth_model="public",
            ),
            EventCalendarSource(
                source_id="dup",
                source_type=EventSourceType.EARNINGS_CALENDAR,
                covered_categories=(EventCategory.EARNINGS,),
                covered_markets=("NYSE",),
                ingestion_latency_sla_seconds=10,
                data_freshness_ref="y",
                api_auth_model="public",
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_empty_categories_rejected(self) -> None:
        bad = (
            EventCalendarSource(
                source_id="empty",
                source_type=EventSourceType.MACRO_CONSENSUS,
                covered_categories=(),
                covered_markets=("US",),
                ingestion_latency_sla_seconds=10,
                data_freshness_ref="x",
                api_auth_model="public",
            ),
        )
        with pytest.raises(ValueError, match="covered_categories"):
            _validate_registry_invariants(bad)

    def test_empty_markets_rejected(self) -> None:
        bad = (
            EventCalendarSource(
                source_id="empty",
                source_type=EventSourceType.MACRO_CONSENSUS,
                covered_categories=(EventCategory.MACRO_RELEASE,),
                covered_markets=(),
                ingestion_latency_sla_seconds=10,
                data_freshness_ref="x",
                api_auth_model="public",
            ),
        )
        with pytest.raises(ValueError, match="covered_markets"):
            _validate_registry_invariants(bad)

    def test_empty_freshness_ref_rejected(self) -> None:
        bad = (
            EventCalendarSource(
                source_id="empty",
                source_type=EventSourceType.MACRO_CONSENSUS,
                covered_categories=(EventCategory.MACRO_RELEASE,),
                covered_markets=("US",),
                ingestion_latency_sla_seconds=10,
                data_freshness_ref="",
                api_auth_model="public",
            ),
        )
        with pytest.raises(ValueError, match="data_freshness_ref"):
            _validate_registry_invariants(bad)

    def test_negative_latency_rejected_by_pydantic(self) -> None:
        with pytest.raises(ValidationError):
            EventCalendarSource(
                source_id="x",
                source_type=EventSourceType.MACRO_CONSENSUS,
                covered_categories=(EventCategory.MACRO_RELEASE,),
                covered_markets=("US",),
                ingestion_latency_sla_seconds=-1,
                data_freshness_ref="x",
                api_auth_model="public",
            )


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1
