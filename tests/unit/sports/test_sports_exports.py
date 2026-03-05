"""Verify top-level imports from unified_api_contracts.sports work."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSportsExports:
    def test_import_canonical_fixture(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import CanonicalFixture

        assert CanonicalFixture is not None

    def test_import_canonical_odds(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import CanonicalOdds

        assert CanonicalOdds is not None

    def test_import_bet_order(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import BetOrder

        assert BetOrder is not None

    def test_import_bet_execution(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import BetExecution

        assert BetExecution is not None

    def test_import_arbitrage_opportunity(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import ArbitrageOpportunity

        assert ArbitrageOpportunity is not None

    def test_import_bookmaker_registry(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import BookmakerRegistry

        assert len(BookmakerRegistry) == 23

    def test_import_odds_type(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import OddsType

        assert OddsType.H2H == "h2h"

    def test_import_all_canonical_types(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import (
            ArbitrageMarket,
            ArbitrageOpportunity,
            ArbitrageStatus,
            BetExecution,
            BetOrder,
            BetStatus,
            BettingSignal,
            BookmakerCategory,
            BookmakerInfo,
            CanonicalBookmakerMarket,
            CanonicalFixture,
            CanonicalLeague,
            CanonicalOdds,
            CanonicalPlayer,
            CanonicalReferee,
            CanonicalTeam,
            CanonicalVenue,
            ExpectedValue,
            MarketStatus,
            OddsType,
            OutcomeType,
            SignalSource,
        )

        assert all(
            [
                ArbitrageMarket,
                ArbitrageOpportunity,
                ArbitrageStatus,
                BetExecution,
                BetOrder,
                BetStatus,
                BettingSignal,
                BookmakerCategory,
                BookmakerInfo,
                CanonicalBookmakerMarket,
                CanonicalFixture,
                CanonicalLeague,
                CanonicalOdds,
                CanonicalPlayer,
                CanonicalReferee,
                CanonicalTeam,
                CanonicalVenue,
                ExpectedValue,
                MarketStatus,
                OddsType,
                OutcomeType,
                SignalSource,
            ]
        )

    def test_import_errors(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports import (
            BetRejectedError,
            BookmakerUnavailableError,
            FixtureNotFoundError,
            MarketClosedError,
            OddsChangedError,
            ScraperError,
            SportsError,
        )

        assert issubclass(BetRejectedError, SportsError)
        assert issubclass(BookmakerUnavailableError, SportsError)
        assert issubclass(FixtureNotFoundError, SportsError)
        assert issubclass(MarketClosedError, SportsError)
        assert issubclass(OddsChangedError, SportsError)
        assert issubclass(ScraperError, SportsError)
