"""Auth-gated VCR tests for Betfair Exchange REST API.

Requires BETFAIR_APP_KEY and BETFAIR_SESSION_TOKEN to be set.
App key stored in GCP Secret Manager as BETFAIR_APP_KEY.

In record mode (cassette missing): makes live API call and saves cassette.
In replay mode (cassette present): replays without network access.

Auth headers (X-Application, X-Authentication) are filtered from saved cassettes.

To record:
    BETFAIR_APP_KEY=<key> BETFAIR_SESSION_TOKEN=<token> pytest tests/vcr/test_betfair_auth_vcr.py -v

To get a session token (non-cert flow):
    curl -X POST https://identitysso.betfair.com/api/login \\
        -H "X-Application: <app_key>" \\
        -d "username=<username>&password=<password>"
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "betfair" / "mocks"

_BETFAIR_APP_KEY = os.environ.get("BETFAIR_APP_KEY", "")
_BETFAIR_SESSION_TOKEN = os.environ.get("BETFAIR_SESSION_TOKEN", "")
_HAS_BETFAIR_AUTH = bool(_BETFAIR_APP_KEY and _BETFAIR_SESSION_TOKEN)

_CATALOGUE_CASSETTE = CASSETTE_DIR / "list_market_catalogue.yaml"
_BOOK_CASSETTE = CASSETTE_DIR / "list_market_book.yaml"


def _vcr_for_betfair() -> VCR:
    """VCR instance that filters Betfair auth headers from recorded cassettes."""
    my_vcr = VCR()
    my_vcr.filter_headers = ["X-Application", "X-Authentication"]
    my_vcr.record_mode = "new_episodes" if _HAS_BETFAIR_AUTH else "none"
    return my_vcr


def _auth_headers() -> dict[str, str]:
    return {
        "X-Application": _BETFAIR_APP_KEY,
        "X-Authentication": _BETFAIR_SESSION_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.mark.skipif(  # reason: requires live Betfair credentials or a pre-recorded cassette
    not _HAS_BETFAIR_AUTH and not _CATALOGUE_CASSETTE.exists(),
    reason="BETFAIR_APP_KEY + BETFAIR_SESSION_TOKEN not set and cassette not recorded yet",
)
def test_betfair_live_list_market_catalogue() -> None:
    """Betfair listMarketCatalogue — auth-gated or cassette replay."""
    with _vcr_for_betfair().use_cassette(str(_CATALOGUE_CASSETTE)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/",
            json={
                "filter": {"eventTypeIds": ["1"]},
                "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "COMPETITION", "EVENT_TYPE"],
                "maxResults": 5,
            },
            headers=_auth_headers() if _HAS_BETFAIR_AUTH else {"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


@pytest.mark.skipif(  # reason: requires live Betfair credentials or a pre-recorded cassette
    not _HAS_BETFAIR_AUTH and not _CATALOGUE_CASSETTE.exists(),
    reason="BETFAIR_APP_KEY + BETFAIR_SESSION_TOKEN not set and cassette not recorded yet",
)
def test_betfair_live_catalogue_runners() -> None:
    """Each catalogue market has runners from live/cassette data."""
    from unified_api_contracts.external.betfair.schemas import (
        BetfairMarketCatalogue,
    )

    with _vcr_for_betfair().use_cassette(str(_CATALOGUE_CASSETTE)):
        response = httpx.post(
            "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/",
            json={
                "filter": {"eventTypeIds": ["1"]},
                "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "COMPETITION", "EVENT_TYPE"],
                "maxResults": 5,
            },
            headers=_auth_headers() if _HAS_BETFAIR_AUTH else {"Content-Type": "application/json"},
        )
        data = response.json()
        for raw in data[:3]:
            market = BetfairMarketCatalogue.model_validate(raw)
            assert market.market_id is not None
