"""Replay VCR cassettes for Betfair Exchange API — verifies schema shape without live network.

Cassettes recorded with auth headers filtered. Auth not required for replay.
App key stored in GCP Secret Manager as BETFAIR_APP_KEY.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "betfair"
    / "mocks"
)

_LIST_CATALOGUE_BODY = (
    b'{"filter": {"eventTypeIds": ["1"]}, '
    b'"marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "COMPETITION", "EVENT_TYPE"], '
    b'"maxResults": 5}'
)
_LIST_BOOK_BODY = b'{"marketIds": ["1.23456789"]}'


def test_betfair_list_market_catalogue_cassette() -> None:
    """Replay VCR cassette for Betfair listMarketCatalogue endpoint."""
    cassette_path = CASSETTE_DIR / "list_market_catalogue.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/",
            content=_LIST_CATALOGUE_BODY,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


def test_betfair_market_catalogue_fields() -> None:
    """Betfair market catalogue items have required fields."""
    cassette_path = CASSETTE_DIR / "list_market_catalogue.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/",
            content=_LIST_CATALOGUE_BODY,
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        market = data[0]
        for field in ("marketId", "marketName", "runners"):
            assert field in market, f"Missing field: {field}"
        assert len(market["runners"]) > 0


def test_betfair_market_catalogue_schema() -> None:
    """Betfair market catalogue validates against BetfairMarketCatalogue schema."""
    from unified_api_contracts.unified_api_contracts_external.betfair.schemas import (
        BetfairMarketCatalogue,
    )

    cassette_path = CASSETTE_DIR / "list_market_catalogue.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/",
            content=_LIST_CATALOGUE_BODY,
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        market = BetfairMarketCatalogue.model_validate(data[0])
        assert market.market_id is not None
        assert market.market_name is not None
        assert market.runners is not None and len(market.runners) > 0


def test_betfair_list_market_book_cassette() -> None:
    """Replay VCR cassette for Betfair listMarketBook endpoint."""
    cassette_path = CASSETTE_DIR / "list_market_book.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/",
            content=_LIST_BOOK_BODY,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


def test_betfair_market_book_schema() -> None:
    """Betfair market book validates against BetfairMarketBook schema with runners."""
    from unified_api_contracts.unified_api_contracts_external.betfair.schemas import (
        BetfairMarketBook,
    )

    cassette_path = CASSETTE_DIR / "list_market_book.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketBook/",
            content=_LIST_BOOK_BODY,
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        book = BetfairMarketBook.model_validate(data[0])
        assert book.market_id == "1.23456789"
        assert book.status == "OPEN"
        assert book.runners is not None and len(book.runners) > 0
        runner = book.runners[0]
        assert runner.selection_id == 12345
        assert runner.ex is not None
        assert "availableToBack" in runner.ex
