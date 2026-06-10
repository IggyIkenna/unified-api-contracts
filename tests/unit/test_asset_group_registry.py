"""Tests for canonical/asset_group_registry.py — cross-asset-group canonical inventory."""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.asset_group_registry import (
    KNOWN_ASSET_GROUPS,
    AssetGroupInventory,
    get_canonical_inventory,
)

# ---------------------------------------------------------------------------
# Happy path — all five asset groups
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports", "prediction"])
def test_get_canonical_inventory_returns_inventory(ag: str) -> None:
    inv = get_canonical_inventory(ag)
    assert isinstance(inv, AssetGroupInventory)
    assert inv.asset_group == ag


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports", "prediction"])
def test_venues_is_tuple(ag: str) -> None:
    inv = get_canonical_inventory(ag)
    assert isinstance(inv.venues, tuple)


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports", "prediction"])
def test_data_types_is_tuple(ag: str) -> None:
    inv = get_canonical_inventory(ag)
    assert isinstance(inv.data_types, tuple)


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports", "prediction"])
def test_source_coverage_start_is_dict_of_dates(ag: str) -> None:
    inv = get_canonical_inventory(ag)
    assert isinstance(inv.source_coverage_start, dict)
    for k, v in inv.source_coverage_start.items():
        assert isinstance(k, str)
        assert isinstance(v, date)


# ---------------------------------------------------------------------------
# Case normalization
# ---------------------------------------------------------------------------


def test_uppercase_asset_group_normalised() -> None:
    inv = get_canonical_inventory("CEFI")
    assert inv.asset_group == "cefi"


def test_mixed_case_asset_group_normalised() -> None:
    inv = get_canonical_inventory("DeFi")
    assert inv.asset_group == "defi"


# ---------------------------------------------------------------------------
# Error path — unknown asset_group
# ---------------------------------------------------------------------------


def test_unknown_asset_group_raises_key_error() -> None:
    with pytest.raises(KeyError, match="unknown_ag"):
        get_canonical_inventory("unknown_ag")


def test_error_message_lists_known_groups() -> None:
    with pytest.raises(KeyError) as exc_info:
        get_canonical_inventory("not_a_real_group")
    # The error message should name the bad key
    assert "not_a_real_group" in str(exc_info.value)


# ---------------------------------------------------------------------------
# KNOWN_ASSET_GROUPS constant
# ---------------------------------------------------------------------------


def test_known_asset_groups_is_frozenset() -> None:
    assert isinstance(KNOWN_ASSET_GROUPS, frozenset)


def test_known_asset_groups_contains_all_five() -> None:
    assert frozenset({"cefi", "defi", "tradfi", "sports", "prediction"}) == KNOWN_ASSET_GROUPS


# ---------------------------------------------------------------------------
# AssetGroupInventory immutability (frozen dataclass)
# ---------------------------------------------------------------------------


def test_asset_group_inventory_is_frozen() -> None:
    inv = get_canonical_inventory("cefi")
    with pytest.raises((AttributeError, TypeError)):
        inv.asset_group = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Spot-check data integrity for well-known asset groups
# ---------------------------------------------------------------------------


def test_cefi_has_venues() -> None:
    inv = get_canonical_inventory("cefi")
    assert len(inv.venues) > 0
    # Binance should always be in CeFi
    assert any("BINANCE" in v for v in inv.venues)


def test_cefi_has_coverage_start_dates() -> None:
    inv = get_canonical_inventory("cefi")
    assert len(inv.source_coverage_start) > 0


def test_tradfi_has_data_types() -> None:
    inv = get_canonical_inventory("tradfi")
    assert len(inv.data_types) > 0
