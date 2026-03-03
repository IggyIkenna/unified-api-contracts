"""Bookmaker registry — all supported bookmakers, exchanges, and aggregators."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict


class BookmakerCategory(StrEnum):
    """How we connect to the bookmaker."""

    EXCHANGE = "exchange"
    BOOKMAKER_API = "bookmaker_api"
    AGGREGATOR = "aggregator"
    STREAMING_API = "streaming_api"
    SCRAPER = "scraper"


class BookmakerInfo(BaseModel):
    """Metadata for a single bookmaker or exchange."""

    model_config = ConfigDict(frozen=True)

    key: str
    display_name: str
    category: BookmakerCategory
    currency: str
    supports_live_betting: bool
    supports_cash_out: bool
    min_bet_gbp: Decimal
    max_bet_gbp: Decimal | None = None
    api_docs_url: str | None = None
    scrape_url: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


BOOKMAKER_REGISTRY: dict[str, BookmakerInfo] = {
    "betfair": BookmakerInfo(
        key="betfair",
        display_name="Betfair Exchange",
        category=BookmakerCategory.EXCHANGE,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("2.00"),
        max_bet_gbp=None,
        api_docs_url="https://docs.developer.betfair.com/",
    ),
    "smarkets": BookmakerInfo(
        key="smarkets",
        display_name="Smarkets Exchange",
        category=BookmakerCategory.EXCHANGE,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=False,
        min_bet_gbp=Decimal("1.00"),
        max_bet_gbp=None,
        api_docs_url="https://docs.smarkets.com/",
    ),
    "matchbook": BookmakerInfo(
        key="matchbook",
        display_name="Matchbook Exchange",
        category=BookmakerCategory.EXCHANGE,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=False,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=None,
        api_docs_url="https://www.matchbook.com/edge/rest",
    ),
    "betdaq": BookmakerInfo(
        key="betdaq",
        display_name="Betdaq Exchange",
        category=BookmakerCategory.EXCHANGE,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=False,
        min_bet_gbp=Decimal("0.50"),
        max_bet_gbp=None,
        api_docs_url="https://www.betdaq.com/",
    ),
    "pinnacle": BookmakerInfo(
        key="pinnacle",
        display_name="Pinnacle",
        category=BookmakerCategory.BOOKMAKER_API,
        currency="USD",
        supports_live_betting=True,
        supports_cash_out=False,
        min_bet_gbp=Decimal("1.00"),
        max_bet_gbp=Decimal("50000.00"),
        api_docs_url="https://pinnacleapi.github.io/",
    ),
    "onexbet": BookmakerInfo(
        key="onexbet",
        display_name="1xBet",
        category=BookmakerCategory.BOOKMAKER_API,
        currency="EUR",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.20"),
        max_bet_gbp=Decimal("10000.00"),
    ),
    "odds_api": BookmakerInfo(
        key="odds_api",
        display_name="The Odds API",
        category=BookmakerCategory.AGGREGATOR,
        currency="USD",
        supports_live_betting=False,
        supports_cash_out=False,
        min_bet_gbp=Decimal("0.00"),
        max_bet_gbp=None,
        api_docs_url="https://the-odds-api.com/liveapi/guides/v4/",
    ),
    "opticodds": BookmakerInfo(
        key="opticodds",
        display_name="OpticOdds",
        category=BookmakerCategory.STREAMING_API,
        currency="USD",
        supports_live_betting=False,
        supports_cash_out=False,
        min_bet_gbp=Decimal("0.00"),
        max_bet_gbp=None,
        api_docs_url="https://docs.opticodds.com/",
    ),
    "oddsjam": BookmakerInfo(
        key="oddsjam",
        display_name="OddsJam",
        category=BookmakerCategory.STREAMING_API,
        currency="USD",
        supports_live_betting=False,
        supports_cash_out=False,
        min_bet_gbp=Decimal("0.00"),
        max_bet_gbp=None,
        api_docs_url="https://developer.oddsjam.com/",
    ),
    "skybet": BookmakerInfo(
        key="skybet",
        display_name="Sky Bet",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("10000.00"),
        scrape_url="https://www.skybet.com/",
    ),
    "coral": BookmakerInfo(
        key="coral",
        display_name="Coral",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("50000.00"),
        scrape_url="https://www.coral.co.uk/",
    ),
    "paddypower": BookmakerInfo(
        key="paddypower",
        display_name="Paddy Power",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("50000.00"),
        scrape_url="https://www.paddypower.com/",
    ),
    "betfred": BookmakerInfo(
        key="betfred",
        display_name="Betfred",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("25000.00"),
        scrape_url="https://www.betfred.com/",
    ),
    "betvictor": BookmakerInfo(
        key="betvictor",
        display_name="BetVictor",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("25000.00"),
        scrape_url="https://www.betvictor.com/",
    ),
    "boylesports": BookmakerInfo(
        key="boylesports",
        display_name="BoyleSports",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("10000.00"),
        scrape_url="https://www.boylesports.com/",
    ),
    "bwin": BookmakerInfo(
        key="bwin",
        display_name="bwin",
        category=BookmakerCategory.SCRAPER,
        currency="EUR",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("25000.00"),
        scrape_url="https://www.bwin.com/",
    ),
    "ladbrokes": BookmakerInfo(
        key="ladbrokes",
        display_name="Ladbrokes",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("50000.00"),
        scrape_url="https://www.ladbrokes.com/",
    ),
    "williamhill": BookmakerInfo(
        key="williamhill",
        display_name="William Hill",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("50000.00"),
        scrape_url="https://www.williamhill.com/",
    ),
    "betway": BookmakerInfo(
        key="betway",
        display_name="Betway",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("25000.00"),
        scrape_url="https://www.betway.com/",
    ),
    "unibet": BookmakerInfo(
        key="unibet",
        display_name="Unibet",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("25000.00"),
        scrape_url="https://www.unibet.co.uk/",
    ),
    "bet888sport": BookmakerInfo(
        key="bet888sport",
        display_name="888sport",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("25000.00"),
        scrape_url="https://www.888sport.com/",
    ),
    "bet365": BookmakerInfo(
        key="bet365",
        display_name="Bet365",
        category=BookmakerCategory.SCRAPER,
        currency="GBP",
        supports_live_betting=True,
        supports_cash_out=True,
        min_bet_gbp=Decimal("0.10"),
        max_bet_gbp=Decimal("50000.00"),
        scrape_url="https://www.bet365.com/",
    ),
}

# Alias for code that expects a registry-like name.
BookmakerRegistry = BOOKMAKER_REGISTRY
