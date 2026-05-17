"""Round-trip tests for CARRY_RECURSIVE_BORROW Family 1 + Family 2 archetype configs.

Verifies that:
1. Family 1 (LENDING_ONLY) and Family 2 (PERP_HEDGED) have all Phase 2 fields populated.
2. Validation bounds fire correctly on bad inputs.
3. Existing non-recursive archetypes are unaffected (all new fields default to None).
4. LendingProtocol enum members are stable (no typo drift).

Plan: defi_recursive_borrow_archetypes_2026_05_10.md Phase 2 done-definition.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.defi import LendingProtocol
from unified_api_contracts.internal.architecture_v2.archetype_config import (
    ArchetypeConfig,
    get_archetype_config,
)
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

# ---------------------------------------------------------------------------
# LendingProtocol enum contract tests
# ---------------------------------------------------------------------------


def test_lending_protocol_members() -> None:
    expected = {"aave_v3", "compound_v3", "spark", "morpho_blue", "maker_dsr"}
    actual = {p.value for p in LendingProtocol}
    assert actual == expected, f"LendingProtocol members drifted: {actual ^ expected}"


def test_lending_protocol_string_eq() -> None:
    assert LendingProtocol.AAVE_V3 == "aave_v3"
    assert LendingProtocol.COMPOUND_V3 == "compound_v3"


# ---------------------------------------------------------------------------
# Family 1 — CARRY_RECURSIVE_BORROW_LENDING_ONLY
# ---------------------------------------------------------------------------


@pytest.fixture()
def family1_config() -> ArchetypeConfig:
    return get_archetype_config(StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY)


def test_family1_no_perp_leg(family1_config: ArchetypeConfig) -> None:
    assert family1_config.perp_leg_enabled is False
    assert family1_config.perp_venue is None


def test_family1_lending_protocol(family1_config: ArchetypeConfig) -> None:
    assert family1_config.lending_protocol is LendingProtocol.AAVE_V3


def test_family1_recursion_params(family1_config: ArchetypeConfig) -> None:
    assert family1_config.recursion_depth_max == 5
    assert family1_config.safety_buffer_ltv == pytest.approx(0.05)
    assert family1_config.opening_mode == "persistent"


def test_family1_target_net_delta(family1_config: ArchetypeConfig) -> None:
    assert family1_config.target_net_delta == pytest.approx(0.0)


def test_family1_no_usdc_margin_buffer(family1_config: ArchetypeConfig) -> None:
    # Family 1 has no CeFi perp venue → no USDC margin buffer.
    assert family1_config.usdc_margin_buffer_min is None


def test_family1_risk_knobs_unchanged(family1_config: ArchetypeConfig) -> None:
    assert family1_config.position_cap_usd == pytest.approx(15_000.0)
    assert family1_config.kill_switch_drawdown_pct == pytest.approx(0.04)
    assert family1_config.kill_switch_position_breach_pct == pytest.approx(0.025)
    assert family1_config.collateral_currency == "USDC"
    assert family1_config.hedge_ratio is None


# ---------------------------------------------------------------------------
# Family 2 — CARRY_RECURSIVE_BORROW_PERP_HEDGED
# ---------------------------------------------------------------------------


@pytest.fixture()
def family2_config() -> ArchetypeConfig:
    return get_archetype_config(StrategyArchetype.CARRY_RECURSIVE_BORROW_PERP_HEDGED)


def test_family2_perp_leg_enabled(family2_config: ArchetypeConfig) -> None:
    assert family2_config.perp_leg_enabled is True
    assert family2_config.perp_venue == "HYPERLIQUID"


def test_family2_lending_protocol(family2_config: ArchetypeConfig) -> None:
    assert family2_config.lending_protocol is LendingProtocol.AAVE_V3


def test_family2_recursion_params(family2_config: ArchetypeConfig) -> None:
    assert family2_config.recursion_depth_max == 5
    assert family2_config.safety_buffer_ltv == pytest.approx(0.05)
    assert family2_config.opening_mode == "persistent"


def test_family2_usdc_margin_buffer(family2_config: ArchetypeConfig) -> None:
    assert family2_config.usdc_margin_buffer_min == pytest.approx(500.0)


def test_family2_target_net_delta(family2_config: ArchetypeConfig) -> None:
    assert family2_config.target_net_delta == pytest.approx(0.0)


def test_family2_risk_knobs_unchanged(family2_config: ArchetypeConfig) -> None:
    assert family2_config.position_cap_usd == pytest.approx(20_000.0)
    assert family2_config.kill_switch_drawdown_pct == pytest.approx(0.045)
    assert family2_config.kill_switch_position_breach_pct == pytest.approx(0.03)
    assert family2_config.collateral_currency == "ETH"
    assert family2_config.hedge_ratio == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Existing archetypes — new fields must be None (no regression)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "archetype",
    [
        StrategyArchetype.CARRY_STAKED_BASIS,
        StrategyArchetype.CARRY_BASIS_PERP,
        StrategyArchetype.CARRY_BASIS_DATED,
        StrategyArchetype.CARRY_RECURSIVE_STAKED,
        StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
    ],
)
def test_existing_archetypes_new_fields_none(archetype: StrategyArchetype) -> None:
    cfg = get_archetype_config(archetype)
    assert cfg.perp_leg_enabled is None, f"{archetype}: perp_leg_enabled should be None"
    assert cfg.recursion_depth_max is None, f"{archetype}: recursion_depth_max should be None"
    assert cfg.safety_buffer_ltv is None, f"{archetype}: safety_buffer_ltv should be None"
    assert cfg.opening_mode is None, f"{archetype}: opening_mode should be None"
    assert cfg.lending_protocol is None, f"{archetype}: lending_protocol should be None"
    assert cfg.usdc_margin_buffer_min is None, f"{archetype}: usdc_margin_buffer_min should be None"


# ---------------------------------------------------------------------------
# Validation bound tests
# ---------------------------------------------------------------------------


def test_recursion_depth_max_zero_raises() -> None:
    with pytest.raises(ValueError, match="recursion_depth_max must be >= 1"):
        ArchetypeConfig(recursion_depth_max=0)


def test_safety_buffer_ltv_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="safety_buffer_ltv must be in"):
        ArchetypeConfig(safety_buffer_ltv=1.5)

    with pytest.raises(ValueError, match="safety_buffer_ltv must be in"):
        ArchetypeConfig(safety_buffer_ltv=0.0)


def test_usdc_margin_buffer_negative_raises() -> None:
    with pytest.raises(ValueError, match="usdc_margin_buffer_min must be >= 0"):
        ArchetypeConfig(usdc_margin_buffer_min=-1.0)


def test_valid_archetype_config_constructs() -> None:
    cfg = ArchetypeConfig(
        perp_leg_enabled=True,
        target_net_delta=0.0,
        recursion_depth_max=3,
        safety_buffer_ltv=0.03,
        opening_mode="flash",
        usdc_margin_buffer_min=200.0,
        lending_protocol=LendingProtocol.COMPOUND_V3,
    )
    assert cfg.lending_protocol is LendingProtocol.COMPOUND_V3
    assert cfg.opening_mode == "flash"
    assert cfg.recursion_depth_max == 3
