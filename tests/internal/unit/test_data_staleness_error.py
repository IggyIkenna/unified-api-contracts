"""Unit tests for DataStalenessError.

Covers:
- Construction with all keyword arguments
- Attribute access
- String representation
- Import from top-level and reference modules
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.reference.data_freshness import DataStalenessError


class TestDataStalenessError:
    def test_basic_construction(self) -> None:
        err = DataStalenessError("data is stale")
        assert str(err) == "data is stale"
        assert err.source == ""
        assert err.age_seconds == 0.0
        assert err.max_age_seconds == 0

    def test_construction_with_kwargs(self) -> None:
        err = DataStalenessError(
            "binance data is 12s old",
            source="binance",
            age_seconds=12.5,
            max_age_seconds=5,
        )
        assert str(err) == "binance data is 12s old"
        assert err.source == "binance"
        assert err.age_seconds == 12.5
        assert err.max_age_seconds == 5

    def test_is_runtime_error(self) -> None:
        err = DataStalenessError("test")
        assert isinstance(err, RuntimeError)

    def test_can_be_caught_as_runtime_error(self) -> None:
        with pytest.raises(RuntimeError, match="stale"):
            raise DataStalenessError("stale data")

    def test_can_be_caught_as_data_staleness_error(self) -> None:
        with pytest.raises(DataStalenessError) as exc_info:
            raise DataStalenessError(
                "stale",
                source="binance",
                age_seconds=10.0,
                max_age_seconds=5,
            )
        assert exc_info.value.source == "binance"
        assert exc_info.value.age_seconds == 10.0


class TestDataStalenessErrorImports:
    def test_import_from_reference(self) -> None:
        from unified_api_contracts.internal.reference import DataStalenessError as DataStalenessErr

        assert DataStalenessErr is DataStalenessError

    def test_import_from_top_level(self) -> None:
        from unified_api_contracts.internal import DataStalenessError as DataStalenessErr

        assert DataStalenessErr is DataStalenessError
