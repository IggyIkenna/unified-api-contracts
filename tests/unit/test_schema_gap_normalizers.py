"""Tests for normalizers added to close the schema audit gaps.

Gaps resolved:
  matchbook → Error        (MatchbookErrorResponse)
  onexbet   → ReferenceData (OneXBetMarket)
  sports    → ReferenceData (BetfairMarket from sports/sources/betfair)
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInternalServerError,
    CanonicalRateLimitError,
)


class TestSchemaGapNormalizers:
    def test_normalize_matchbook_error_known_codes(self) -> None:
        from unified_api_contracts.normalize_utils.errors import (
            normalize_matchbook_error,
        )

        assert isinstance(normalize_matchbook_error("UNAUTHORIZED"), CanonicalAuthenticationError)
        assert isinstance(normalize_matchbook_error("FORBIDDEN"), CanonicalAuthorizationError)
        assert isinstance(normalize_matchbook_error("TOO_MANY_REQUESTS"), CanonicalRateLimitError)
        assert isinstance(normalize_matchbook_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_matchbook_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_matchbook_error("UNKNOWN_CODE"), CanonicalError)

    def test_normalize_onexbet_market(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalBetMarket
        from unified_api_contracts.external.onexbet.schemas import (
            OneXBetMarket,
            OneXBetOutcome,
        )
        from unified_api_contracts.normalize_utils.sports import (
            normalize_onexbet_market,
        )

        market = OneXBetMarket(name="1x2", outcomes=[OneXBetOutcome(name="Home", price=1.85)])
        result = normalize_onexbet_market(market)
        assert isinstance(result, CanonicalBetMarket)
        assert result.market_id == "1x2"
        assert result.market_name == "1x2"
        assert result.venue == "onexbet"

    def test_normalize_sports_market(self) -> None:
        from datetime import UTC, datetime
        from decimal import Decimal

        from unified_api_contracts.canonical.domain import CanonicalBetMarket
        from unified_api_contracts.external.betfair.schemas import (
            BetfairMarket,
            BetfairMarketStatus,
        )
        from unified_api_contracts.normalize_utils.sports import (
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
