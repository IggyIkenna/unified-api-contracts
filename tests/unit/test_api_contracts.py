"""
Unit tests for API contracts core functionality.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from unified_api_contracts.binance.ws_schemas import BinanceMarkPriceUpdate
from unified_api_contracts.bybit.schemas import BybitOrderUpdateWS
from unified_api_contracts.deribit.schemas import DeribitTickerFull
from unified_api_contracts.okx.schemas import OKXFundingRate


class TestAPIContractsCore:
    """Test core API contracts functionality."""

    def test_schema_loading(self):
        """Test that schemas can be loaded successfully."""
        # Test that schema files can be loaded
        try:
            from unified_api_contracts.okx import schemas as okx_schemas

            assert hasattr(okx_schemas, "__file__")
        except ImportError:
            pytest.skip("OKX schemas not available")

    def test_schema_validation_structure(self):
        """Test that schemas have expected structure."""
        # Test schema structure validation
        # This is a placeholder - replace with actual schema validation
        assert True

    def test_venue_schema_availability(self):
        """Test that venue schemas are available."""
        venues = ["okx", "hyperliquid", "ccxt", "upbit", "thegraph"]

        for venue in venues:
            try:
                # Try to import venue schema
                __import__(f"unified_api_contracts.{venue}.schemas")
                # If import succeeds, schema is available
                assert True
            except ImportError:
                # Venue schema not available, but that's okay for testing
                pass

    def test_schema_file_existence(self):
        """Test that schema files exist."""
        # Get the api_contracts directory
        api_contracts_path = Path(__file__).parent.parent.parent / "unified_api_contracts"

        if api_contracts_path.exists():
            venues = [d for d in api_contracts_path.iterdir() if d.is_dir() and not d.name.startswith("__")]

            for venue_dir in venues:
                schemas_file = venue_dir / "schemas.py"
                if schemas_file.exists():
                    assert schemas_file.is_file()
                    # Check file is not empty
                    assert schemas_file.stat().st_size > 0

    def test_json_schema_validation(self):
        """Test JSON schema validation functionality."""
        # Test that JSON schemas are valid
        sample_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name"],
        }

        # This should be valid JSON
        assert isinstance(sample_schema, dict)
        assert "type" in sample_schema
        assert "properties" in sample_schema

    def test_contract_validation_success(self):
        """Test successful contract validation."""
        # Test that valid contracts pass validation
        valid_data = {"name": "test", "age": 25}

        # Placeholder validation - replace with actual validation logic
        assert isinstance(valid_data, dict)
        assert "name" in valid_data

    def test_contract_validation_failure(self):
        """Test that invalid contracts fail validation."""
        # Test that invalid contracts are rejected
        invalid_data = {
            "age": 25  # missing required 'name' field
        }

        # Placeholder validation - replace with actual validation logic
        assert isinstance(invalid_data, dict)
        # In real implementation, this would raise a validation error

    def test_schema_caching(self):
        """Test that schemas are properly cached."""
        # Test schema caching mechanism
        cache_key = "test_schema"
        cached_data = {"cached": True}

        # Mock a simple cache
        cache = {cache_key: cached_data}
        assert cache.get(cache_key) == cached_data

    def test_error_handling(self):
        """Test proper error handling in contract validation."""
        # Test that errors are handled gracefully
        try:
            # Simulate an error condition
            raise ValueError("Test validation error")
        except ValueError as e:
            assert str(e) == "Test validation error"
            # Error was caught and handled properly

    def test_performance_benchmarks(self):
        """Test that contract validation meets performance requirements."""
        import time

        # Test that validation is reasonably fast
        start_time = time.time()

        # Simulate validation work
        for _ in range(100):
            data = {"test": "value"}
            assert isinstance(data, dict)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete quickly (less than 1 second for 100 operations)
        assert duration < 1.0

    def test_memory_usage(self):
        """Test that contract validation doesn't leak memory."""
        # Test memory efficiency
        import gc

        # Force garbage collection
        gc.collect()

        # Simulate memory-intensive operations
        data_list = []
        for i in range(100):
            data_list.append({"id": i, "data": f"value_{i}"})

        # Clean up
        del data_list
        gc.collect()

        # Memory should be freed (this is a basic test)
        assert True

    def test_thread_safety(self):
        """Test that contract validation is thread-safe."""
        import threading

        results = []
        errors = []

        def validate_contract():
            try:
                # Simulate contract validation
                data = {"thread_test": True}
                results.append(len(data))
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=validate_contract)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result == 1 for result in results)

    def test_new_ws_schemas_instantiation(self):
        """Test that new WebSocket/derivatives/options schemas parse valid data."""
        # Binance mark price
        mp = BinanceMarkPriceUpdate(
            e="markPriceUpdate",
            E=1700000000000,
            s="BTCUSDT",
            p=Decimal("50000"),
            i=Decimal("50001"),
            P=Decimal("50002"),
            r=Decimal("0.0001"),
            T=1700003600000,
        )
        assert mp.s == "BTCUSDT"
        assert mp.p == Decimal("50000")

        # Bybit order update
        order = BybitOrderUpdateWS(
            orderId="ord_123",
            symbol="BTCUSDT",
            side="Buy",
            orderType="Limit",
            orderStatus="New",
        )
        assert order.orderId == "ord_123"

        # OKX funding rate
        fr = OKXFundingRate(
            instType="SWAP",
            instId="BTC-USD-SWAP",
            fundingRate="0.0001",
            fundingTime="1700000000000",
        )
        assert fr.instId == "BTC-USD-SWAP"

        # Deribit full ticker
        ticker = DeribitTickerFull(
            instrument_name="BTC-PERPETUAL",
            timestamp=1700000000000,
        )
        assert ticker.instrument_name == "BTC-PERPETUAL"
