"""Unit tests for VCR cassette files — verify cassettes exist and contain valid data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EXTERNAL_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external"


class TestPolymarketCassettes:
    """Verify Polymarket VCR cassettes exist and contain well-formed data."""

    @pytest.mark.unit
    def test_gamma_events_cassette_exists(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "gamma_events_cassette.json"
        assert path.exists(), f"Missing cassette: {path}"

    @pytest.mark.unit
    def test_gamma_events_cassette_is_valid_json(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "gamma_events_cassette.json"
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.unit
    def test_gamma_events_has_required_fields(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "gamma_events_cassette.json"
        data = json.loads(path.read_text())
        event = data[0]
        assert "id" in event
        assert "title" in event
        assert "markets" in event

    @pytest.mark.unit
    def test_gamma_tags_cassette_exists(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "gamma_tags_cassette.json"
        assert path.exists(), f"Missing cassette: {path}"

    @pytest.mark.unit
    def test_gamma_tags_cassette_is_valid_json(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "gamma_tags_cassette.json"
        data = json.loads(path.read_text())
        assert isinstance(data, list)

    @pytest.mark.unit
    def test_prices_history_cassette_exists(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "prices_history_cassette.json"
        assert path.exists(), f"Missing cassette: {path}"

    @pytest.mark.unit
    def test_prices_history_cassette_is_valid_json(self) -> None:
        path = EXTERNAL_DIR / "polymarket" / "mocks" / "prices_history_cassette.json"
        data = json.loads(path.read_text())
        assert isinstance(data, (list, dict))


class TestCoinbaseCassettes:
    """Verify Coinbase products VCR cassette exists and contains well-formed data."""

    @pytest.mark.unit
    def test_products_cassette_exists(self) -> None:
        path = EXTERNAL_DIR / "coinbase" / "mocks" / "products_cassette.json"
        assert path.exists(), f"Missing cassette: {path}"

    @pytest.mark.unit
    def test_products_cassette_is_valid_json(self) -> None:
        path = EXTERNAL_DIR / "coinbase" / "mocks" / "products_cassette.json"
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.unit
    def test_products_cassette_has_required_fields(self) -> None:
        path = EXTERNAL_DIR / "coinbase" / "mocks" / "products_cassette.json"
        data = json.loads(path.read_text())
        product = data[0]
        assert "id" in product
        assert "base_currency" in product
        assert "quote_currency" in product
        assert "status" in product

    @pytest.mark.unit
    def test_products_cassette_has_btc_usd(self) -> None:
        path = EXTERNAL_DIR / "coinbase" / "mocks" / "products_cassette.json"
        data = json.loads(path.read_text())
        ids = [p["id"] for p in data]
        assert "BTC-USD" in ids
        assert "ETH-USD" in ids
