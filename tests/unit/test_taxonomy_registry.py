"""Tests for registry/taxonomy.py — canonical term definitions and MarketAssetGroup."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.taxonomy import (
    InstrumentTypeFamily,
    MarketAssetGroup,
    PipelineCategory,
    asset_group_key,
)

# ---------------------------------------------------------------------------
# MarketAssetGroup StrEnum
# ---------------------------------------------------------------------------


def test_market_asset_group_values() -> None:
    assert MarketAssetGroup.CEFI == "CEFI"
    assert MarketAssetGroup.DEFI == "DEFI"
    assert MarketAssetGroup.TRADFI == "TRADFI"
    assert MarketAssetGroup.SPORTS == "SPORTS"
    assert MarketAssetGroup.PREDICTION == "PREDICTION"


def test_market_asset_group_has_five_members() -> None:
    assert len(list(MarketAssetGroup)) == 5


def test_market_asset_group_str_equality() -> None:
    assert MarketAssetGroup.CEFI == "CEFI"
    assert str(MarketAssetGroup.CEFI) == "CEFI"


# ---------------------------------------------------------------------------
# InstrumentTypeFamily StrEnum
# ---------------------------------------------------------------------------


def test_instrument_type_family_is_string_enum() -> None:
    assert isinstance(InstrumentTypeFamily.SPOT, str)
    assert len(list(InstrumentTypeFamily)) > 0


# ---------------------------------------------------------------------------
# PipelineCategory StrEnum
# ---------------------------------------------------------------------------


def test_pipeline_category_is_string_enum() -> None:
    assert isinstance(next(iter(PipelineCategory)), str)
    assert len(list(PipelineCategory)) > 0


# ---------------------------------------------------------------------------
# asset_group_key function
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ag", "expected"),
    [
        (MarketAssetGroup.CEFI, "cefi"),
        (MarketAssetGroup.DEFI, "defi"),
        (MarketAssetGroup.TRADFI, "tradfi"),
        (MarketAssetGroup.SPORTS, "sports"),
        (MarketAssetGroup.PREDICTION, "prediction"),
    ],
)
def test_asset_group_key_returns_lowercase_string(ag: MarketAssetGroup, expected: str) -> None:
    assert asset_group_key(ag) == expected


def test_asset_group_key_output_type_is_str() -> None:
    result = asset_group_key(MarketAssetGroup.CEFI)
    assert isinstance(result, str)
