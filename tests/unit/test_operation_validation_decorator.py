"""Tests for the @requires_operation_validation decorator.

Covers:
- Sync function decorated
- Async function decorated
- UnsupportedOperationError propagates (hard block)
- Graceful degradation for unknown source (swallowed)
- venue_attr extraction from self
- Decorator argument validation
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.capability import (
    OperationDetail,
    OperationEnvDetail,
    SourceCapability,
    UnsupportedOperationError,
    register_capability,
)
from unified_api_contracts.registry.capability_data import bootstrap_capabilities
from unified_api_contracts.registry.venue_context import requires_operation_validation

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bootstrap() -> None:
    """Bootstrap all capability declarations before each test."""
    bootstrap_capabilities()


@pytest.fixture()
def _test_source() -> SourceCapability:
    """Register a test source with one supported and one blocked operation."""
    cap = SourceCapability(
        source="decorator-test-venue",
        domains=["execution"],
        crosscutting=["errors"],
        supports_live=True,
        supports_testnet=True,
        supports_mainnet=True,
        operation_details={
            "place_order": OperationDetail(
                environments={
                    "mainnet": OperationEnvDetail(
                        signing_scheme="hmac_sha256",
                        required_credential="api_key",
                    ),
                    "testnet": OperationEnvDetail(
                        supported=False,
                        notes="place_order blocked on testnet",
                    ),
                }
            ),
            "supply": OperationDetail(
                environments={
                    "mainnet": OperationEnvDetail(
                        signing_scheme="on_chain",
                        required_credential="wallet_private_key",
                    ),
                }
            ),
        },
    )
    register_capability(cap)
    return cap


# ---------------------------------------------------------------------------
# Test: Sync function decorated
# ---------------------------------------------------------------------------


class TestSyncDecorated:
    """@requires_operation_validation on a regular (sync) function."""

    def test_sync_function_passes_through(self, _test_source: SourceCapability) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        def place_order(venue: str, symbol: str, env: str = "mainnet") -> str:
            return f"placed:{symbol}"

        result = place_order("decorator-test-venue", "BTC-USD", env="mainnet")
        assert result == "placed:BTC-USD"

    def test_sync_preserves_return_value(self, _test_source: SourceCapability) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        def place_order(venue: str, symbol: str, env: str = "mainnet") -> dict[str, str]:
            return {"status": "ok", "symbol": symbol}

        result = place_order("decorator-test-venue", "ETH-USD")
        assert result == {"status": "ok", "symbol": "ETH-USD"}


# ---------------------------------------------------------------------------
# Test: Async function decorated
# ---------------------------------------------------------------------------


class TestAsyncDecorated:
    """@requires_operation_validation on an async function."""

    @pytest.mark.asyncio()
    async def test_async_function_passes_through(self, _test_source: SourceCapability) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        async def place_order(venue: str, symbol: str, env: str = "mainnet") -> str:
            return f"async_placed:{symbol}"

        result = await place_order("decorator-test-venue", "BTC-USD", env="mainnet")
        assert result == "async_placed:BTC-USD"

    @pytest.mark.asyncio()
    async def test_async_preserves_return_value(self, _test_source: SourceCapability) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        async def place_order(venue: str, symbol: str, env: str = "mainnet") -> dict[str, str]:
            return {"status": "ok", "symbol": symbol}

        result = await place_order("decorator-test-venue", "ETH-USD")
        assert result == {"status": "ok", "symbol": "ETH-USD"}


# ---------------------------------------------------------------------------
# Test: UnsupportedOperationError propagates (hard block)
# ---------------------------------------------------------------------------


class TestUnsupportedOperationPropagates:
    """UnsupportedOperationError must NOT be swallowed."""

    def test_sync_raises_unsupported(self, _test_source: SourceCapability) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        def place_order(venue: str, symbol: str, env: str = "mainnet") -> str:
            return f"placed:{symbol}"

        with pytest.raises(UnsupportedOperationError) as exc_info:
            place_order("decorator-test-venue", "BTC-USD", env="testnet")

        err = exc_info.value
        assert err.source == "decorator-test-venue"
        assert err.operation == "place_order"
        assert err.env == "testnet"
        assert "blocked on testnet" in (err.notes or "")

    @pytest.mark.asyncio()
    async def test_async_raises_unsupported(self, _test_source: SourceCapability) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        async def place_order(venue: str, symbol: str, env: str = "mainnet") -> str:
            return f"placed:{symbol}"

        with pytest.raises(UnsupportedOperationError) as exc_info:
            await place_order("decorator-test-venue", "BTC-USD", env="testnet")

        err = exc_info.value
        assert err.source == "decorator-test-venue"
        assert err.operation == "place_order"
        assert err.env == "testnet"


# ---------------------------------------------------------------------------
# Test: Graceful degradation for unknown source
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Non-UnsupportedOperationError exceptions are swallowed."""

    def test_sync_unknown_source_degrades_gracefully(self) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        def place_order(venue: str, symbol: str, env: str = "mainnet") -> str:
            return f"placed:{symbol}"

        # "totally-unknown-venue-xyz" is not registered, so CapabilityResolutionError
        # is raised internally — but swallowed. The method body still runs.
        result = place_order("totally-unknown-venue-xyz", "BTC-USD", env="mainnet")
        assert result == "placed:BTC-USD"

    @pytest.mark.asyncio()
    async def test_async_unknown_source_degrades_gracefully(self) -> None:
        @requires_operation_validation(
            venue_param="venue", operation_name="place_order", env_param="env"
        )
        async def place_order(venue: str, symbol: str, env: str = "mainnet") -> str:
            return f"async_placed:{symbol}"

        result = await place_order("totally-unknown-venue-xyz", "BTC-USD", env="mainnet")
        assert result == "async_placed:BTC-USD"


# ---------------------------------------------------------------------------
# Test: venue_attr extraction from self
# ---------------------------------------------------------------------------


class TestVenueAttrExtraction:
    """venue_attr reads the venue from an attribute on self."""

    def test_sync_venue_attr_from_self(self, _test_source: SourceCapability) -> None:
        class DeFiAdapter:
            def __init__(self, venue_id: str) -> None:
                self.venue_id = venue_id

            @requires_operation_validation(
                venue_attr="self.venue_id", operation_name="supply", env_param="env"
            )
            def supply(self, amount: float, env: str = "mainnet") -> str:
                return f"supplied:{amount}"

        adapter = DeFiAdapter("decorator-test-venue")
        result = adapter.supply(100.0, env="mainnet")
        assert result == "supplied:100.0"

    @pytest.mark.asyncio()
    async def test_async_venue_attr_from_self(self, _test_source: SourceCapability) -> None:
        class DeFiAdapter:
            def __init__(self, venue_id: str) -> None:
                self.venue_id = venue_id

            @requires_operation_validation(
                venue_attr="self.venue_id", operation_name="supply", env_param="env"
            )
            async def supply(self, amount: float, env: str = "mainnet") -> str:
                return f"supplied:{amount}"

        adapter = DeFiAdapter("decorator-test-venue")
        result = await adapter.supply(100.0, env="mainnet")
        assert result == "supplied:100.0"

    def test_venue_attr_nested(self, _test_source: SourceCapability) -> None:
        """Test dot-separated attribute path deeper than one level."""

        class VenueConfig:
            def __init__(self, venue_id: str) -> None:
                self.venue_id = venue_id

        class DeFiAdapter:
            def __init__(self, config: VenueConfig) -> None:
                self.config = config

            @requires_operation_validation(
                venue_attr="self.config.venue_id", operation_name="supply", env_param="env"
            )
            def supply(self, amount: float, env: str = "mainnet") -> str:
                return f"supplied:{amount}"

        adapter = DeFiAdapter(VenueConfig("decorator-test-venue"))
        result = adapter.supply(100.0, env="mainnet")
        assert result == "supplied:100.0"

    def test_venue_attr_unsupported_propagates(self, _test_source: SourceCapability) -> None:
        """UnsupportedOperationError still propagates with venue_attr."""

        class DeFiAdapter:
            def __init__(self, venue_id: str) -> None:
                self.venue_id = venue_id

            @requires_operation_validation(
                venue_attr="self.venue_id", operation_name="place_order", env_param="env"
            )
            def place_order(self, symbol: str, env: str = "mainnet") -> str:
                return f"placed:{symbol}"

        adapter = DeFiAdapter("decorator-test-venue")
        with pytest.raises(UnsupportedOperationError):
            adapter.place_order("BTC-USD", env="testnet")


# ---------------------------------------------------------------------------
# Test: Decorator argument validation
# ---------------------------------------------------------------------------


class TestDecoratorArgValidation:
    """Decorator raises TypeError for invalid argument combinations."""

    def test_neither_venue_param_nor_venue_attr_raises(self) -> None:
        with pytest.raises(TypeError, match="Either venue_param or venue_attr"):
            requires_operation_validation(operation_name="place_order")

    def test_both_venue_param_and_venue_attr_raises(self) -> None:
        with pytest.raises(TypeError, match="mutually exclusive"):
            requires_operation_validation(
                venue_param="venue", venue_attr="self.venue_id", operation_name="place_order"
            )
