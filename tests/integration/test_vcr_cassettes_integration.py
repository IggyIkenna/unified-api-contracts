"""Integration tests for VCR cassettes — verify cassettes align with endpoint registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unified_api_contracts.registry._endpoint_registry_data import ENDPOINT_REGISTRY
from unified_api_contracts.registry._endpoint_registry_types import CassetteStatus

EXTERNAL_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external"


class TestCassetteRegistryAlignment:
    """Verify cassette RECORDED status in registry matches actual cassette files."""

    @pytest.mark.integration
    def test_polymarket_gamma_events_recorded_in_registry(self) -> None:
        """Polymarket gamma events endpoint is marked RECORDED."""
        found = False
        for spec in ENDPOINT_REGISTRY:
            if spec.venue == "polymarket" and "gamma-api" in spec.endpoint_path and "events" in spec.endpoint_path:
                assert spec.cassette_status == CassetteStatus.RECORDED
                found = True
                break
        assert found, "Polymarket gamma events endpoint not found in registry"

    @pytest.mark.integration
    def test_polymarket_gamma_tags_recorded_in_registry(self) -> None:
        """Polymarket gamma tags endpoint is marked RECORDED."""
        found = False
        for spec in ENDPOINT_REGISTRY:
            if spec.venue == "polymarket" and "tags" in spec.endpoint_path:
                assert spec.cassette_status == CassetteStatus.RECORDED
                found = True
                break
        assert found, "Polymarket gamma tags endpoint not found in registry"

    @pytest.mark.integration
    def test_polymarket_prices_history_recorded_in_registry(self) -> None:
        """Polymarket prices-history endpoint is marked RECORDED."""
        found = False
        for spec in ENDPOINT_REGISTRY:
            if spec.venue == "polymarket" and "prices-history" in spec.endpoint_path:
                assert spec.cassette_status == CassetteStatus.RECORDED
                found = True
                break
        assert found, "Polymarket prices-history endpoint not found in registry"

    @pytest.mark.integration
    def test_coinbase_exchange_products_recorded_in_registry(self) -> None:
        """Coinbase Exchange products endpoint is marked RECORDED."""
        found = False
        for spec in ENDPOINT_REGISTRY:
            if spec.venue == "coinbase" and "exchange.coinbase.com/products" in spec.endpoint_path:
                assert spec.cassette_status == CassetteStatus.RECORDED
                found = True
                break
        assert found, "Coinbase Exchange products endpoint not found in registry"

    @pytest.mark.integration
    def test_recorded_cassettes_have_actual_files(self) -> None:
        """Every RECORDED cassette has a corresponding non-stub file on disk."""
        polymarket_mocks = EXTERNAL_DIR / "polymarket" / "mocks"
        coinbase_mocks = EXTERNAL_DIR / "coinbase" / "mocks"

        # Polymarket cassettes
        for cassette in ["gamma_events_cassette.json", "gamma_tags_cassette.json", "prices_history_cassette.json"]:
            path = polymarket_mocks / cassette
            assert path.exists(), f"Missing Polymarket cassette: {cassette}"
            data = json.loads(path.read_text())
            assert data, f"Empty Polymarket cassette: {cassette}"

        # Coinbase cassette
        path = coinbase_mocks / "products_cassette.json"
        assert path.exists(), "Missing Coinbase products cassette"
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0
