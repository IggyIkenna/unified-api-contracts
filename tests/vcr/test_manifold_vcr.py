"""Replay VCR cassette for Manifold — verifies schema shape without live network.

Manifold prediction markets
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "manifold" / "mocks"


def test_manifold_cassette() -> None:
    """Replay VCR cassette for Manifold endpoint."""
    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.manifold.markets/v0/markets?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_manifold_response_structure() -> None:
    """Response is a non-empty list."""
    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.manifold.markets/v0/markets?limit=3")
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


def test_manifold_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.external.manifold.schemas import ManifoldMarket

    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.manifold.markets/v0/markets?limit=3")
        data = response.json()
        result = ManifoldMarket.model_validate(data[0])
        assert result is not None
