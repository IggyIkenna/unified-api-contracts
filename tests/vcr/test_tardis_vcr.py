"""Replay VCR cassette for Tardis public endpoints — verifies schema shape without live network.

Cassette recorded from public Tardis API (no API key required for /exchanges).
Auth-required endpoints (instruments, historical data) are tested in test_tardis_auth_vcr.py.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "tardis"
    / "mocks"
)


def test_tardis_exchanges_cassette() -> None:
    """Replay VCR cassette for Tardis exchanges list — verifies response shape."""
    cassette_path = CASSETTE_DIR / "exchanges.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.tardis.dev/v1/exchanges")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


def test_tardis_exchange_fields() -> None:
    """Required exchange fields are present in every entry."""
    cassette_path = CASSETTE_DIR / "exchanges.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.tardis.dev/v1/exchanges")
        data = response.json()
        for exchange in data:
            assert "id" in exchange, f"Missing id in {exchange}"
            assert "name" in exchange, f"Missing name in {exchange}"
            assert "enabled" in exchange, f"Missing enabled in {exchange}"
            assert "availableChannels" in exchange, f"Missing availableChannels in {exchange}"


def test_tardis_known_exchanges_present() -> None:
    """Canonical trading venues are present in the Tardis exchange list."""
    cassette_path = CASSETTE_DIR / "exchanges.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.tardis.dev/v1/exchanges")
        data = response.json()
        ids = {ex["id"] for ex in data}
        for expected in ("binance-futures", "deribit", "bybit"):
            assert expected in ids, f"Expected exchange '{expected}' not found in Tardis list"
