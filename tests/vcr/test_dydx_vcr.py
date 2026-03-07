"""Replay VCR cassette for Dydx — verifies schema shape without live network.

dYdX v4 perpetual markets
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent / "unified_api_contracts" / "unified_api_contracts_external" / "dydx" / "mocks"
)


def test_dydx_cassette() -> None:
    """Replay VCR cassette for Dydx endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://indexer.dydx.trade/v4/perpetualMarkets?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_dydx_response_structure() -> None:
    """Response dict contains 'markets' key."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://indexer.dydx.trade/v4/perpetualMarkets?limit=3")
        data = response.json()
        assert isinstance(data, dict)
        assert "markets" in data


def test_dydx_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.unified_api_contracts_external.dydx.schemas import (
        DydxPerpetualMarket,
    )

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://indexer.dydx.trade/v4/perpetualMarkets?limit=3")
        data = response.json()
        result = DydxPerpetualMarket.model_validate(next(iter(data["markets"].values())))
        assert result is not None
