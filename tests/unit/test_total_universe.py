"""Unit tests for the total-reasonable-universe SSOT (B2).

Validates the two-concept hierarchy (MVP ⊆ TOTAL ⊆ ALL), the selection-axis
taxonomy, the provenance taxonomy, and the ``universe_membership`` classifier.
"""

from __future__ import annotations

from unified_api_contracts import (
    TOTAL_UNIVERSE_AXES,
    TOTAL_UNIVERSE_CONFIG_HASH,
    TOTAL_UNIVERSE_CONFIG_VERSION,
    UniverseAxis,
    UniverseProvenance,
    UniverseTier,
    is_mvp,
    is_total_universe,
    total_universe_config_descriptor,
    universe_membership,
)

_ALL_ASSET_GROUPS = ("cefi", "defi", "tradfi", "sports", "prediction")


def test_every_asset_group_has_an_axis_taxonomy() -> None:
    """All five asset_groups declare a non-empty selection-axis taxonomy."""
    for ag in _ALL_ASSET_GROUPS:
        assert ag in TOTAL_UNIVERSE_AXES, ag
        assert len(TOTAL_UNIVERSE_AXES[ag]) >= 1, ag
        for axis in TOTAL_UNIVERSE_AXES[ag]:
            assert isinstance(axis, UniverseAxis)
            assert axis.name
            assert axis.ssot_ref
            assert axis.description
            assert isinstance(axis.provenance, UniverseProvenance)


def test_provenance_taxonomy_is_closed_two_set() -> None:
    """Provenance is exactly HARDCODED_GENESIS | DOWNLOAD_DERIVED."""
    assert {p.value for p in UniverseProvenance} == {
        "hardcoded_genesis",
        "download_derived",
    }
    # Both provenances are actually USED across the taxonomy (not a dead enum).
    used = {axis.provenance for axes in TOTAL_UNIVERSE_AXES.values() for axis in axes}
    assert used == set(UniverseProvenance)


def test_operator_named_axes_are_present() -> None:
    """The axes the operator named (2026-06-18) are codified.

    base_currency (cefi), defi_pool_volume (defi), fixtures (sports), venue,
    data_type, combinations.
    """
    cefi_axes = {a.name for a in TOTAL_UNIVERSE_AXES["cefi"]}
    assert "base_currency" in cefi_axes
    defi_axes = {a.name for a in TOTAL_UNIVERSE_AXES["defi"]}
    assert "defi_pool_volume" in defi_axes
    sports_axes = {a.name for a in TOTAL_UNIVERSE_AXES["sports"]}
    assert "fixtures" in sports_axes
    # venue + data_type present in the cross-AG set
    all_axis_names = {a.name for axes in TOTAL_UNIVERSE_AXES.values() for a in axes}
    assert {"venue", "data_type", "combinations"} <= all_axis_names


def test_is_total_universe_true_for_declared_asset_groups() -> None:
    for ag in _ALL_ASSET_GROUPS:
        assert is_total_universe(ag, "ANY-VENUE", "ANY_TYPE") is True


def test_is_total_universe_false_for_unknown_asset_group() -> None:
    assert is_total_universe("equities_options", "X", "Y") is False
    assert is_total_universe("", "X", "Y") is False


def test_mvp_is_subset_of_total() -> None:
    """A known MVP cell classifies as MVP (and is therefore in TOTAL)."""
    # BTC perpetual trade on Binance — MVP per mvp_scope.
    assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")
    assert universe_membership("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC") == UniverseTier.MVP


def test_total_only_for_non_mvp_but_real_asset_group() -> None:
    """A non-MVP venue in a real asset_group is TOTAL_ONLY, not MVP."""
    # UPBIT is a real CeFi venue but NOT in the MVP scope.
    assert not is_mvp("cefi", "UPBIT", "SPOT_PAIR", "trades")
    assert universe_membership("cefi", "UPBIT", "SPOT_PAIR", "trades") == UniverseTier.TOTAL_ONLY


def test_not_in_universe_for_unknown_asset_group() -> None:
    assert universe_membership("equities_options", "NYSE", "STOCK", "trades") == UniverseTier.NOT_IN_UNIVERSE


def test_config_descriptor_is_deterministic() -> None:
    d1 = total_universe_config_descriptor()
    d2 = total_universe_config_descriptor()
    assert d1 == d2
    assert d1.config_version == TOTAL_UNIVERSE_CONFIG_VERSION
    assert d1.config_content_hash == TOTAL_UNIVERSE_CONFIG_HASH
    assert len(TOTAL_UNIVERSE_CONFIG_HASH) == 16
