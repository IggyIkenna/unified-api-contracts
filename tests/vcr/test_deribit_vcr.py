"""Replay VCR cassette for Deribit — verifies schema shape without live network.

Deribit BTC futures instruments
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "deribit" / "mocks"


def test_deribit_cassette() -> None:
    """Replay VCR cassette for Deribit endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=future&expired=false"
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_deribit_response_structure() -> None:
    """Response dict contains 'result' key."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=future&expired=false"
        )
        data = response.json()
        assert isinstance(data, dict)
        assert "result" in data


def test_deribit_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.external.deribit.schemas import (
        DeribitInstrument,
    )

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=future&expired=false"
        )
        data = response.json()
        result = DeribitInstrument.model_validate(data["result"][0])
        assert result is not None
