"""Unit tests for sports error classes (no external API calls)."""

from __future__ import annotations

import pytest

from unified_api_contracts.external.sports.errors import (
    BetRejectedError,
    BookmakerUnavailableError,
    FixtureNotFoundError,
    MarketClosedError,
    OddsChangedError,
    ScraperError,
    SportsError,
)

pytestmark = pytest.mark.unit


def test_sports_error_base() -> None:
    """SportsError is the base for all sports errors."""
    err = SportsError("test")
    assert str(err) == "test"


def test_bookmaker_unavailable_error() -> None:
    """BookmakerUnavailableError stores bookmaker_key and reason."""
    err = BookmakerUnavailableError(bookmaker_key="betfair", reason="timeout")
    assert err.bookmaker_key == "betfair"
    assert err.reason == "timeout"
    assert "betfair" in str(err)
    assert "timeout" in str(err)
    assert isinstance(err, SportsError)


def test_bet_rejected_error() -> None:
    """BetRejectedError stores order_id, reason, bookmaker_key."""
    err = BetRejectedError(
        order_id="ord-1",
        reason="price moved",
        bookmaker_key="smarkets",
    )
    assert err.order_id == "ord-1"
    assert err.reason == "price moved"
    assert err.bookmaker_key == "smarkets"
    assert "ord-1" in str(err)
    assert isinstance(err, SportsError)


def test_odds_changed_error() -> None:
    """OddsChangedError stores requested and available odds."""
    err = OddsChangedError(requested=2.5, available=2.1)
    assert err.requested == 2.5
    assert err.available == 2.1
    assert "2.5" in str(err)
    assert isinstance(err, SportsError)


def test_market_closed_error() -> None:
    """MarketClosedError is a SportsError."""
    err = MarketClosedError("market suspended")
    assert "suspended" in str(err)
    assert isinstance(err, SportsError)


def test_scraper_error() -> None:
    """ScraperError stores bookmaker_key, url, reason."""
    err = ScraperError(
        bookmaker_key="skybet",
        url="https://www.skybet.com/",
        reason="selector not found",
    )
    assert err.bookmaker_key == "skybet"
    assert err.url == "https://www.skybet.com/"
    assert err.reason == "selector not found"
    assert isinstance(err, SportsError)


def test_fixture_not_found_error() -> None:
    """FixtureNotFoundError stores fixture_id and bookmaker_key."""
    err = FixtureNotFoundError(fixture_id="af:12345", bookmaker_key="pinnacle")
    assert err.fixture_id == "af:12345"
    assert err.bookmaker_key == "pinnacle"
    assert "af:12345" in str(err)
    assert isinstance(err, SportsError)
