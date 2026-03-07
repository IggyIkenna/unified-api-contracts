"""Tests for normalizers added to close the 5 schema audit gaps.

Gaps resolved:
  betdaq    → Order        (BetdaqOrder)
  matchbook → Error        (MatchbookErrorResponse)
  onexbet   → ReferenceData (OneXBetMarket)
  smarkets  → Order        (SmarketsOrderResponse)
  sports    → ReferenceData (BetfairMarket from sports/sources/betfair)
"""

from __future__ import annotations

from unified_api_contracts.unified_normalised_contracts.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInternalServerError,
    CanonicalRateLimitError,
)


class TestSchemaGapNormalizers:
    def test_normalize_betdaq_order_accepted(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.betdaq.schemas import BetdaqOrder
        from unified_api_contracts.unified_normalised_contracts.domain import CanonicalBetOrder
        from unified_api_contracts.unified_normalised_contracts.normalize.sports import (
            normalize_betdaq_order,
        )

        order = BetdaqOrder(Id=12345, Result=0)
        result = normalize_betdaq_order(order)
        assert isinstance(result, CanonicalBetOrder)
        assert result.order_id == "12345"
        assert result.status == "accepted"
        assert result.venue == "betdaq"

    def test_normalize_betdaq_order_rejected(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.betdaq.schemas import BetdaqOrder
        from unified_api_contracts.unified_normalised_contracts.normalize.sports import (
            normalize_betdaq_order,
        )

        order = BetdaqOrder(Id=99, Result=-1)
        result = normalize_betdaq_order(order)
        assert result.status == "rejected"

    def test_normalize_matchbook_error_known_codes(self) -> None:
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import (
            normalize_matchbook_error,
        )

        assert isinstance(normalize_matchbook_error("UNAUTHORIZED"), CanonicalAuthenticationError)
        assert isinstance(normalize_matchbook_error("FORBIDDEN"), CanonicalAuthorizationError)
        assert isinstance(normalize_matchbook_error("TOO_MANY_REQUESTS"), CanonicalRateLimitError)
        assert isinstance(normalize_matchbook_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_matchbook_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_matchbook_error("UNKNOWN_CODE"), CanonicalError)

    def test_normalize_onexbet_market(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.onexbet.schemas import (
            OneXBetMarket,
            OneXBetOutcome,
        )
        from unified_api_contracts.unified_normalised_contracts.domain import CanonicalBetMarket
        from unified_api_contracts.unified_normalised_contracts.normalize.sports import (
            normalize_onexbet_market,
        )

        market = OneXBetMarket(name="1x2", outcomes=[OneXBetOutcome(name="Home", price=1.85)])
        result = normalize_onexbet_market(market)
        assert isinstance(result, CanonicalBetMarket)
        assert result.market_id == "1x2"
        assert result.market_name == "1x2"
        assert result.venue == "onexbet"

    def test_normalize_smarkets_order(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.smarkets.schemas import (
            SmarketsOrderResponse,
        )
        from unified_api_contracts.unified_normalised_contracts.domain import CanonicalBetOrder
        from unified_api_contracts.unified_normalised_contracts.normalize.sports import (
            normalize_smarkets_order,
        )

        order = SmarketsOrderResponse(id="ord_abc123")
        result = normalize_smarkets_order(order)
        assert isinstance(result, CanonicalBetOrder)
        assert result.order_id == "ord_abc123"
        assert result.status == "submitted"
        assert result.venue == "smarkets"

    def test_normalize_sports_market(self) -> None:
        from datetime import UTC, datetime
        from decimal import Decimal

        from unified_api_contracts.unified_api_contracts_external.sports.sources.betfair.schemas import (
            BetfairMarket,
            BetfairMarketStatus,
        )
        from unified_api_contracts.unified_normalised_contracts.domain import CanonicalBetMarket
        from unified_api_contracts.unified_normalised_contracts.normalize.sports import (
            normalize_sports_market,
        )

        market = BetfairMarket(
            market_id="1.234567",
            market_name="Match Odds",
            event_id="28.12345",
            event_name="Arsenal vs Chelsea",
            status=BetfairMarketStatus.OPEN,
            market_start_time=datetime(2026, 3, 10, 15, 0, 0, tzinfo=UTC),
            total_matched=Decimal("50000"),
        )
        result = normalize_sports_market(market)
        assert isinstance(result, CanonicalBetMarket)
        assert result.market_id == "1.234567"
        assert result.market_name == "Match Odds"
        assert result.event_name == "Arsenal vs Chelsea"
        assert result.status == "OPEN"
        assert result.close_time is not None
