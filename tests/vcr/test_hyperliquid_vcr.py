"""Replay VCR cassette for Hyperliquid perpetuals meta — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "hyperliquid" / "mocks"


def test_hyperliquid_meta_cassette() -> None:
    """Replay VCR cassette for Hyperliquid perp meta endpoint."""
    cassette_path = CASSETTE_DIR / "meta.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post("https://api.hyperliquid.xyz/info", json={"type": "meta"})
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_hyperliquid_meta_universe() -> None:
    """Hyperliquid meta response contains a universe list with perpetual instruments."""
    cassette_path = CASSETTE_DIR / "meta.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post("https://api.hyperliquid.xyz/info", json={"type": "meta"})
        data = response.json()
        assert "universe" in data, "Missing 'universe' key in meta response"
        assert isinstance(data["universe"], list) and len(data["universe"]) > 0


def test_hyperliquid_meta_instrument_fields() -> None:
    """Each Hyperliquid perpetual has required fields."""
    cassette_path = CASSETTE_DIR / "meta.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post("https://api.hyperliquid.xyz/info", json={"type": "meta"})
        data = response.json()
        for instrument in data["universe"][:5]:
            for field in ("name", "szDecimals", "maxLeverage"):
                assert field in instrument, f"Missing field '{field}' in instrument {instrument}"


def test_hyperliquid_meta_schema() -> None:
    """Hyperliquid meta validates against api-contracts HyperliquidMeta."""
    from unified_api_contracts.hyperliquid.schemas import HyperliquidMeta

    cassette_path = CASSETTE_DIR / "meta.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post("https://api.hyperliquid.xyz/info", json={"type": "meta"})
        data = response.json()
        meta = HyperliquidMeta.model_validate(data)
        assert meta.universe is not None
        assert len(meta.universe) > 0
        btc = next((u for u in meta.universe if u.name == "BTC"), None)
        assert btc is not None, "BTC not found in Hyperliquid universe"
        assert btc.maxLeverage is not None and btc.maxLeverage > 0
