"""Tests for registry/archetype_capability_matrix.py — asset-group ontology registry."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.archetype_capability_matrix import (
    ASSET_GROUP_ONTOLOGY,
    AssetGroupOntology,
    FillModel,
    SettlementModel,
    get_asset_group_ontology,
    venues_for,
)
from unified_api_contracts.registry.taxonomy import MarketAssetGroup

# ---------------------------------------------------------------------------
# ASSET_GROUP_ONTOLOGY dict — basic presence
# ---------------------------------------------------------------------------


def test_ontology_has_all_five_asset_groups() -> None:
    assert set(ASSET_GROUP_ONTOLOGY.keys()) == {
        MarketAssetGroup.CEFI,
        MarketAssetGroup.DEFI,
        MarketAssetGroup.TRADFI,
        MarketAssetGroup.SPORTS,
        MarketAssetGroup.PREDICTION,
    }


@pytest.mark.parametrize("ag", list(MarketAssetGroup))
def test_ontology_each_group_has_venues(ag: MarketAssetGroup) -> None:
    ont = ASSET_GROUP_ONTOLOGY[ag]
    assert isinstance(ont.venues, frozenset)
    assert len(ont.venues) > 0


# ---------------------------------------------------------------------------
# get_asset_group_ontology
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ag", list(MarketAssetGroup))
def test_get_asset_group_ontology_returns_ontology(ag: MarketAssetGroup) -> None:
    ont = get_asset_group_ontology(ag)
    assert isinstance(ont, AssetGroupOntology)
    assert ont.asset_group == ag


def test_get_asset_group_ontology_cefi() -> None:
    ont = get_asset_group_ontology(MarketAssetGroup.CEFI)
    assert ont.has_liquidations is True
    assert any("binance" in v for v in ont.venues)


def test_get_asset_group_ontology_sports_no_liquidations() -> None:
    ont = get_asset_group_ontology(MarketAssetGroup.SPORTS)
    assert ont.has_liquidations is False


def test_get_asset_group_ontology_prediction_no_liquidations() -> None:
    ont = get_asset_group_ontology(MarketAssetGroup.PREDICTION)
    assert ont.has_liquidations is False


def test_get_asset_group_ontology_tradfi_has_liquidations() -> None:
    ont = get_asset_group_ontology(MarketAssetGroup.TRADFI)
    assert ont.has_liquidations is True


# ---------------------------------------------------------------------------
# venues_for
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ag", list(MarketAssetGroup))
def test_venues_for_returns_frozenset(ag: MarketAssetGroup) -> None:
    result = venues_for(ag)
    assert isinstance(result, frozenset)
    assert len(result) > 0


def test_venues_for_cefi_includes_binance() -> None:
    result = venues_for(MarketAssetGroup.CEFI)
    assert any("binance" in v for v in result)


def test_venues_for_defi_includes_uniswap() -> None:
    result = venues_for(MarketAssetGroup.DEFI)
    assert any("uniswap" in v for v in result)


# ---------------------------------------------------------------------------
# AssetGroupOntology dataclass
# ---------------------------------------------------------------------------


def test_asset_group_ontology_is_frozen() -> None:
    ont = get_asset_group_ontology(MarketAssetGroup.CEFI)
    with pytest.raises((AttributeError, TypeError)):
        ont.asset_group = MarketAssetGroup.DEFI  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FillModel and SettlementModel dataclass basics
# ---------------------------------------------------------------------------


def test_fill_model_has_expected_fields() -> None:
    for ag in MarketAssetGroup:
        ont = get_asset_group_ontology(ag)
        assert isinstance(ont.fill_model, FillModel)


def test_settlement_model_has_expected_fields() -> None:
    for ag in MarketAssetGroup:
        ont = get_asset_group_ontology(ag)
        assert isinstance(ont.settlement_model, SettlementModel)
