"""Replay VCR cassette for defillama — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "api_contracts" / "api_contracts_external" / "defillama" / "mocks"


def test_defillama_market_data_cassette() -> None:
    """Replay VCR cassette for defillama — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "protocols.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.llama.fi/protocols")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert isinstance(data, list) and len(data) > 0 and "tvl" in data[0]


def test_defillama_protocol_fields() -> None:
    """Required protocol fields are present in the first result."""
    cassette_path = CASSETTE_DIR / "protocols.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.llama.fi/protocols")
        data = response.json()
        protocol = data[0]
        for field in ("name", "symbol", "tvl", "chain"):
            assert field in protocol, f"Missing field: {field}"
