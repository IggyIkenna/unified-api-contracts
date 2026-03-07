"""Replay VCR cassette for Predictit — verifies schema shape without live network.

PredictIt all markets
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "predictit"
    / "mocks"
)


def test_predictit_cassette() -> None:
    """Replay VCR cassette for Predictit endpoint."""
    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.predictit.org/api/marketdata/all/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_predictit_response_structure() -> None:
    """Response dict contains 'markets' key."""
    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.predictit.org/api/marketdata/all/")
        data = response.json()
        assert isinstance(data, dict)
        assert "markets" in data


def test_predictit_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.unified_api_contracts_external.predictit.schemas import (
        PredictItMarket,
    )

    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.predictit.org/api/marketdata/all/")
        data = response.json()
        result = PredictItMarket.model_validate(data["markets"][0])
        assert result is not None
