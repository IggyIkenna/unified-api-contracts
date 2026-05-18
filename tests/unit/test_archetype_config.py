"""Unit tests for the archetype_config SSOT.

Covers the May-23 cutover schema floor — :class:`ArchetypeConfig`,
:data:`ARCHETYPE_CONFIG_SEED`, and the helper functions wired by the alerting
+ risk-and-exposure consumer plans.

Plan: ``plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #1 [DESIGN+UAC] (operational risk knobs sub-item, Option A).
Issue doc: ``plans/active/issues/cross_cutting_strategy_catalogue_already_shipped_2026_05_08.md``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.architecture_v2.archetype_config import (
    ARCHETYPE_CONFIG_SEED,
    ArchetypeConfig,
    archetype_kill_switch_thresholds,
    get_archetype_config,
    is_archetype_config_declared,
)
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

# ---------------------------------------------------------------------------
# ArchetypeConfig dataclass — bounds validation
# ---------------------------------------------------------------------------


def test_archetype_config_default_constructs_all_none() -> None:
    """All-None construction is legal — it represents 'no operational config declared'."""
    cfg = ArchetypeConfig()
    assert cfg.collateral_currency is None
    assert cfg.hedge_ratio is None
    assert cfg.position_cap_usd is None
    assert cfg.kill_switch_drawdown_pct is None
    assert cfg.kill_switch_position_breach_pct is None


def test_archetype_config_position_cap_zero_raises() -> None:
    with pytest.raises(ValueError, match="position_cap_usd must be > 0"):
        ArchetypeConfig(position_cap_usd=0.0)


def test_archetype_config_position_cap_negative_raises() -> None:
    with pytest.raises(ValueError, match="position_cap_usd must be > 0"):
        ArchetypeConfig(position_cap_usd=-100.0)


def test_archetype_config_kill_switch_drawdown_zero_raises() -> None:
    with pytest.raises(ValueError, match="kill_switch_drawdown_pct must be in"):
        ArchetypeConfig(kill_switch_drawdown_pct=0.0)


def test_archetype_config_kill_switch_drawdown_above_one_raises() -> None:
    with pytest.raises(ValueError, match="kill_switch_drawdown_pct must be in"):
        ArchetypeConfig(kill_switch_drawdown_pct=1.5)


def test_archetype_config_kill_switch_drawdown_at_one_allowed() -> None:
    """Inclusive upper bound — 100% drawdown gate is legal (catastrophic but legal)."""
    cfg = ArchetypeConfig(kill_switch_drawdown_pct=1.0)
    assert cfg.kill_switch_drawdown_pct == 1.0


def test_archetype_config_kill_switch_breach_zero_raises() -> None:
    with pytest.raises(ValueError, match="kill_switch_position_breach_pct must be in"):
        ArchetypeConfig(kill_switch_position_breach_pct=0.0)


def test_archetype_config_kill_switch_breach_above_one_raises() -> None:
    with pytest.raises(ValueError, match="kill_switch_position_breach_pct must be in"):
        ArchetypeConfig(kill_switch_position_breach_pct=2.0)


def test_archetype_config_negative_hedge_ratio_raises() -> None:
    """Negative hedge ratio would invert direction — banned."""
    with pytest.raises(ValueError, match="hedge_ratio must be >= 0"):
        ArchetypeConfig(hedge_ratio=-0.5)


def test_archetype_config_zero_hedge_ratio_allowed() -> None:
    """Zero hedge ratio = no hedge leg, distinct from None (paired strategy with hedge disabled)."""
    cfg = ArchetypeConfig(hedge_ratio=0.0)
    assert cfg.hedge_ratio == 0.0


def test_archetype_config_is_frozen() -> None:
    """Frozen dataclass — instances are immutable."""
    cfg = ArchetypeConfig(collateral_currency="USDT")
    with pytest.raises((AttributeError, TypeError)):
        cfg.collateral_currency = "USDC"  # type: ignore[misc]


def test_archetype_config_is_hashable() -> None:
    """Frozen + slots ⇒ hashable. Required so configs can sit in sets / dict keys."""
    cfg_a = ArchetypeConfig(collateral_currency="USDT", hedge_ratio=1.0)
    cfg_b = ArchetypeConfig(collateral_currency="USDT", hedge_ratio=1.0)
    cfg_c = ArchetypeConfig(collateral_currency="USDC", hedge_ratio=1.0)
    assert hash(cfg_a) == hash(cfg_b)
    assert {cfg_a, cfg_b, cfg_c} == {cfg_a, cfg_c}


# ---------------------------------------------------------------------------
# ARCHETYPE_CONFIG_SEED — May-23 cutover coverage
# ---------------------------------------------------------------------------


_MAY_23_LIVE_ARCHETYPES: tuple[StrategyArchetype, ...] = (
    StrategyArchetype.CARRY_STAKED_BASIS,
    StrategyArchetype.CARRY_BASIS_PERP,
    StrategyArchetype.CARRY_BASIS_DATED,
    StrategyArchetype.CARRY_RECURSIVE_STAKED,
    StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
)


def test_seed_covers_all_may_23_live_archetypes() -> None:
    """All 5 May-23 live archetypes have config seeded."""
    for archetype in _MAY_23_LIVE_ARCHETYPES:
        assert archetype in ARCHETYPE_CONFIG_SEED, f"missing seed for {archetype!r}"


def test_seed_carry_staked_basis_eth_collateral() -> None:
    cfg = ARCHETYPE_CONFIG_SEED[StrategyArchetype.CARRY_STAKED_BASIS]
    assert cfg.collateral_currency == "ETH"
    assert cfg.hedge_ratio == 1.0
    assert cfg.position_cap_usd == 50_000.0


def test_seed_carry_recursive_staked_tightened_thresholds() -> None:
    """Recursive staking has tighter drawdown / breach thresholds due to liquidation-cascade risk."""
    cfg = ARCHETYPE_CONFIG_SEED[StrategyArchetype.CARRY_RECURSIVE_STAKED]
    assert cfg.kill_switch_drawdown_pct == 0.05
    assert cfg.kill_switch_position_breach_pct == 0.03
    # Smaller cap than vanilla CARRY_STAKED_BASIS.
    assert cfg.position_cap_usd == 25_000.0


def test_seed_ml_directional_continuous_no_hedge() -> None:
    """Single-leg directional — hedge_ratio is None (not 0.0)."""
    cfg = ARCHETYPE_CONFIG_SEED[StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS]
    assert cfg.hedge_ratio is None
    assert cfg.collateral_currency == "USDT"


def test_seed_drawdown_sanity_bound() -> None:
    """No May-23 archetype tolerates > 10% drawdown — operator-confirmed risk envelope."""
    for archetype, cfg in ARCHETYPE_CONFIG_SEED.items():
        assert cfg.kill_switch_drawdown_pct is not None, f"{archetype!r}: drawdown_pct missing"
        assert cfg.kill_switch_drawdown_pct <= 0.10, (
            f"{archetype!r}: drawdown_pct {cfg.kill_switch_drawdown_pct} exceeds 10% sanity bound"
        )


def test_seed_all_values_are_archetype_configs() -> None:
    """No stray values — every entry must be a real :class:`ArchetypeConfig`."""
    for archetype, cfg in ARCHETYPE_CONFIG_SEED.items():
        assert isinstance(archetype, StrategyArchetype)
        assert isinstance(cfg, ArchetypeConfig)


# ---------------------------------------------------------------------------
# get_archetype_config resolution
# ---------------------------------------------------------------------------


def test_get_archetype_config_returns_seeded_value() -> None:
    cfg = get_archetype_config(StrategyArchetype.CARRY_STAKED_BASIS)
    assert cfg is ARCHETYPE_CONFIG_SEED[StrategyArchetype.CARRY_STAKED_BASIS]


def test_get_archetype_config_unseeded_raises_keyerror_with_archetype_name() -> None:
    """Unseeded archetype raises KeyError — fail-loud forces deliberate operator decision."""
    # MARKET_MAKING_PASSIVE_SPREAD is a real archetype but not yet activated for May-23.
    with pytest.raises(KeyError, match="MARKET_MAKING_PASSIVE_SPREAD"):
        get_archetype_config(StrategyArchetype.MARKET_MAKING_PASSIVE_SPREAD)


# ---------------------------------------------------------------------------
# is_archetype_config_declared
# ---------------------------------------------------------------------------


def test_is_archetype_config_declared_seeded_true() -> None:
    assert is_archetype_config_declared(StrategyArchetype.CARRY_STAKED_BASIS) is True


def test_is_archetype_config_declared_unseeded_false() -> None:
    assert is_archetype_config_declared(StrategyArchetype.MARKET_MAKING_PASSIVE_SPREAD) is False


# ---------------------------------------------------------------------------
# archetype_kill_switch_thresholds
# ---------------------------------------------------------------------------


def test_archetype_kill_switch_thresholds_returns_pair() -> None:
    drawdown, breach = archetype_kill_switch_thresholds(StrategyArchetype.CARRY_STAKED_BASIS)
    assert drawdown == 0.10
    assert breach == 0.05


def test_archetype_kill_switch_thresholds_recursive_tightened() -> None:
    drawdown, breach = archetype_kill_switch_thresholds(StrategyArchetype.CARRY_RECURSIVE_STAKED)
    assert drawdown == 0.05
    assert breach == 0.03


def test_archetype_kill_switch_thresholds_unseeded_raises() -> None:
    with pytest.raises(KeyError):
        archetype_kill_switch_thresholds(StrategyArchetype.MARKET_MAKING_PASSIVE_SPREAD)


# ---------------------------------------------------------------------------
# perp_venue config field — defi_recursive_borrow Phase 6 variant-naming P0
# ---------------------------------------------------------------------------


def test_archetype_config_default_perp_venue_is_none() -> None:
    cfg = ArchetypeConfig()
    assert cfg.perp_venue is None


def test_archetype_config_perp_venue_valid_accepted() -> None:
    cfg = ArchetypeConfig(perp_venue="HYPERLIQUID")
    assert cfg.perp_venue == "HYPERLIQUID"


def test_archetype_config_perp_venue_bybit_futures_accepted() -> None:
    cfg = ArchetypeConfig(perp_venue="BYBIT-FUTURES")
    assert cfg.perp_venue == "BYBIT-FUTURES"


def test_archetype_config_perp_venue_invalid_rejected() -> None:
    with pytest.raises(ValueError, match="not in get_perp_venues"):
        ArchetypeConfig(perp_venue="NOT_A_VENUE")


def test_archetype_config_perp_venue_spot_only_rejected() -> None:
    """Spot-only venues are not perp-trade-capable."""
    with pytest.raises(ValueError, match="not in get_perp_venues"):
        ArchetypeConfig(perp_venue="BINANCE-SPOT")


def test_seed_carry_basis_perp_inv_has_hyperliquid() -> None:
    """Per defi_recursive_borrow variant-naming P0 — single archetype + perp_venue config."""
    cfg = ARCHETYPE_CONFIG_SEED[StrategyArchetype.CARRY_BASIS_PERP_INV]
    assert cfg.perp_venue == "HYPERLIQUID"
