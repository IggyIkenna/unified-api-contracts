"""Tests verifying consolidated cassettes are accessible from UAC.

Validates that all cassettes previously stored in execution-service and
unified-defi-execution-interface are now accessible through the UAC
cassette_loader utility from their canonical locations in
external/<venue>/mocks/.
"""

from __future__ import annotations

import json

import pytest

from unified_api_contracts.testing.cassette_loader import (
    get_cassette_path,
    list_cassettes_for_venue,
    load_cassette,
    load_cassette_raw,
)

# ---------------------------------------------------------------------------
# Deribit cassettes (migrated from execution-service)
# ---------------------------------------------------------------------------


class TestDeribitCassettesConsolidated:
    """Verify deribit cassettes migrated from execution-service are accessible."""

    def test_auth_test_cassette_exists(self) -> None:
        """auth_test.yaml cassette exists in UAC deribit/mocks/."""
        path = get_cassette_path("deribit", "auth_test.yaml")
        assert path.is_file()

    def test_auth_test_cassette_loadable(self) -> None:
        """auth_test.yaml cassette loads and returns valid JSON body."""
        body = load_cassette("deribit", "auth_test.yaml")
        assert isinstance(body, dict)
        assert "result" in body
        result = body["result"]
        assert isinstance(result, dict)
        assert "access_token" in result
        assert "refresh_token" in result

    def test_risk_service_health_cassette_exists(self) -> None:
        """risk_service_health.yaml cassette exists in UAC deribit/mocks/."""
        path = get_cassette_path("deribit", "risk_service_health.yaml")
        assert path.is_file()

    def test_risk_service_health_cassette_loadable(self) -> None:
        """risk_service_health.yaml returns healthy status."""
        body = load_cassette("deribit", "risk_service_health.yaml")
        assert isinstance(body, dict)
        assert body["status"] == "healthy"

    def test_existing_deribit_cassettes_intact(self) -> None:
        """Pre-existing deribit cassettes (ticker, get_instruments_multi) still work."""
        cassettes = list_cassettes_for_venue("deribit")
        names = [c.name for c in cassettes]
        assert "ticker.yaml" in names
        assert "get_instruments_multi.yaml" in names

    def test_deribit_cassette_count(self) -> None:
        """Deribit should have at least 4 cassettes after consolidation."""
        cassettes = list_cassettes_for_venue("deribit")
        assert len(cassettes) >= 4


# ---------------------------------------------------------------------------
# Hyperliquid cassettes (migrated from unified-defi-execution-interface)
# ---------------------------------------------------------------------------


class TestHyperliquidCassettesConsolidated:
    """Verify hyperliquid cassettes migrated from UDEI are accessible."""

    def test_meta_and_asset_ctxs_cassette_exists(self) -> None:
        """meta_and_asset_ctxs.yaml cassette exists in UAC hyperliquid/mocks/."""
        path = get_cassette_path("hyperliquid", "meta_and_asset_ctxs.yaml")
        assert path.is_file()

    def test_meta_and_asset_ctxs_cassette_loadable(self) -> None:
        """meta_and_asset_ctxs.yaml loads and contains expected universe data."""
        body = load_cassette("hyperliquid", "meta_and_asset_ctxs.yaml")
        # Hyperliquid metaAndAssetCtxs returns [meta, assetCtxs] — a 2-element list
        assert isinstance(body, list)
        assert len(body) == 2
        meta = body[0]
        assert isinstance(meta, dict)
        assert "universe" in meta
        universe = meta["universe"]
        assert isinstance(universe, list)
        assert len(universe) >= 2
        btc = universe[0]
        assert btc["name"] == "BTC"

    def test_clearinghouse_state_cassette_exists(self) -> None:
        """clearinghouse_state.yaml cassette exists in UAC hyperliquid/mocks/."""
        path = get_cassette_path("hyperliquid", "clearinghouse_state.yaml")
        assert path.is_file()

    def test_clearinghouse_state_cassette_loadable(self) -> None:
        """clearinghouse_state.yaml loads and contains margin data."""
        body = load_cassette("hyperliquid", "clearinghouse_state.yaml")
        assert isinstance(body, dict)
        assert "marginSummary" in body
        assert "withdrawable" in body
        assert "assetPositions" in body

    def test_existing_hyperliquid_cassettes_intact(self) -> None:
        """Pre-existing hyperliquid cassette (meta.yaml) still works."""
        cassettes = list_cassettes_for_venue("hyperliquid")
        names = [c.name for c in cassettes]
        assert "meta.yaml" in names

    def test_hyperliquid_cassette_count(self) -> None:
        """Hyperliquid should have at least 3 cassettes after consolidation."""
        cassettes = list_cassettes_for_venue("hyperliquid")
        assert len(cassettes) >= 3


# ---------------------------------------------------------------------------
# Cassette loader utility tests
# ---------------------------------------------------------------------------


class TestCassetteLoaderUtility:
    """Tests for the cassette_loader utility functions."""

    def test_get_cassette_path_nonexistent_raises(self) -> None:
        """get_cassette_path raises FileNotFoundError for missing cassettes."""
        with pytest.raises(FileNotFoundError, match="Cassette not found"):
            get_cassette_path("deribit", "nonexistent_cassette.yaml")

    def test_list_cassettes_for_nonexistent_venue(self) -> None:
        """list_cassettes_for_venue returns empty list for unknown venue."""
        result = list_cassettes_for_venue("nonexistent_venue_xyz")
        assert result == []

    def test_load_cassette_raw_returns_full_structure(self) -> None:
        """load_cassette_raw returns complete cassette with interactions and version."""
        raw = load_cassette_raw("deribit", "auth_test.yaml")
        assert "interactions" in raw
        assert "version" in raw
        assert raw["version"] == 1
        assert isinstance(raw["interactions"], list)
        assert len(raw["interactions"]) > 0

    def test_load_cassette_roundtrip(self) -> None:
        """Loaded cassette body survives JSON roundtrip."""
        body = load_cassette("hyperliquid", "meta_and_asset_ctxs.yaml")
        roundtripped = json.loads(json.dumps(body))
        assert roundtripped == body

    def test_load_cassette_interaction_index(self) -> None:
        """get_instruments_multi.yaml has multiple interactions; index > 0 works."""
        body_0 = load_cassette("deribit", "get_instruments_multi.yaml", interaction_index=0)
        body_1 = load_cassette("deribit", "get_instruments_multi.yaml", interaction_index=1)
        # Both should be valid JSON dicts
        assert isinstance(body_0, dict)
        assert isinstance(body_1, dict)
        # They should be different interactions (different currencies)
        assert body_0 != body_1

    def test_load_cassette_out_of_range_index_raises(self) -> None:
        """Requesting a non-existent interaction index raises ValueError."""
        with pytest.raises(ValueError, match="has only"):
            load_cassette("deribit", "auth_test.yaml", interaction_index=999)
