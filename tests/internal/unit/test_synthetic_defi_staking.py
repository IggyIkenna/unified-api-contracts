"""Tests for SyntheticDataGenerator DeFi yield index columns and staking rates.

Covers:
- generate_defi_yields() returns both APY and cumulative index columns
- Liquidity/borrow indices start at 1.0 and are monotonically increasing
- Borrow APY > supply APY (spread factor applied)
- generate_staking_rates() produces valid staking rate series with indices
- Staking index is monotonically increasing (staking rates always positive)
- APY -> index round-trip consistency
- Deterministic output (same seed -> same result)
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from unified_api_contracts.internal.testing.synthetic import SyntheticDataGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_SPEC: dict[str, object] = {
    "defi_yield_params": {
        "aave_v3_USDC": {"mean": 0.045, "kappa": 2.0, "sigma": 0.01, "base_apy": 0.045},
    },
}

_START = date(2024, 1, 1)
_END = date(2024, 2, 1)  # 1 month — fast tests


@pytest.fixture()
def gen() -> SyntheticDataGenerator:
    return SyntheticDataGenerator(_MINIMAL_SPEC, seed=42)


# ---------------------------------------------------------------------------
# generate_defi_yields — columns present
# ---------------------------------------------------------------------------


class TestDefiYieldsColumns:
    def test_returns_expected_columns(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        expected = {
            "timestamp",
            "protocol",
            "asset",
            "apy",
            "liquidity_index",
            "borrow_apy",
            "variable_borrow_index",
            "tvl_usd",
        }
        assert set(df.columns) == expected

    def test_non_empty(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Index properties
# ---------------------------------------------------------------------------


class TestIndexProperties:
    def test_liquidity_index_starts_at_one(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        assert df["liquidity_index"].iloc[0] == pytest.approx(1.0)

    def test_variable_borrow_index_starts_at_one(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        assert df["variable_borrow_index"].iloc[0] == pytest.approx(1.0)

    def test_liquidity_index_monotonically_increasing(self, gen: SyntheticDataGenerator) -> None:
        """When APY >= 0 (clamped by OU), the index should be non-decreasing."""
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        idx = df["liquidity_index"].to_numpy()
        diffs = np.diff(idx)
        assert np.all(diffs >= -1e-15), "liquidity_index should be monotonically non-decreasing"

    def test_variable_borrow_index_monotonically_increasing(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        idx = df["variable_borrow_index"].to_numpy()
        diffs = np.diff(idx)
        assert np.all(diffs >= -1e-15), "variable_borrow_index should be monotonically non-decreasing"

    def test_borrow_index_exceeds_supply_index(self, gen: SyntheticDataGenerator) -> None:
        """Borrow accumulates faster because borrow_apy > supply_apy."""
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        # Compare final values — borrow should have grown more
        final_liq = float(df["liquidity_index"].iloc[-1])
        final_borrow = float(df["variable_borrow_index"].iloc[-1])
        assert final_borrow > final_liq


# ---------------------------------------------------------------------------
# Borrow spread
# ---------------------------------------------------------------------------


class TestBorrowSpread:
    def test_borrow_apy_exceeds_supply_apy(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        supply = df["apy"].to_numpy()
        borrow = df["borrow_apy"].to_numpy()
        # Where supply > 0, borrow should be strictly greater
        positive_mask = supply > 0
        assert np.all(borrow[positive_mask] > supply[positive_mask])

    def test_borrow_spread_within_range(self, gen: SyntheticDataGenerator) -> None:
        """Borrow/supply ratio should be within 1.2-1.5x for known protocols."""
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        supply = df["apy"].to_numpy()
        borrow = df["borrow_apy"].to_numpy()
        positive_mask = supply > 0
        ratios = borrow[positive_mask] / supply[positive_mask]
        # aave_v3 spread is 1.35
        assert np.allclose(ratios, 1.35, atol=1e-10)


# ---------------------------------------------------------------------------
# APY -> index round-trip consistency
# ---------------------------------------------------------------------------


class TestApyIndexRoundTrip:
    def test_index_growth_matches_apy(self, gen: SyntheticDataGenerator) -> None:
        """The total index growth over the period should be consistent with the APYs."""
        df = gen.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        final_index = float(df["liquidity_index"].iloc[-1])
        # The index should grow beyond 1.0 given positive APYs over 1 month
        assert final_index > 1.0
        # Rough check: ~4.5% APY over 1 month => ~0.375% growth => index ~1.00375
        # Allow wide tolerance since OU is stochastic
        assert 1.001 < final_index < 1.02


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_defi_result(self) -> None:
        gen1 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=99)
        gen2 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=99)
        df1 = gen1.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        df2 = gen2.generate_defi_yields("aave_v3", "USDC", _START, _END, "1h")
        pd.testing.assert_frame_equal(df1, df2)

    def test_same_seed_same_staking_result(self) -> None:
        gen1 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=99)
        gen2 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=99)
        df1 = gen1.generate_staking_rates(["lido"], duration_days=30, interval_hours=1)
        df2 = gen2.generate_staking_rates(["lido"], duration_days=30, interval_hours=1)
        pd.testing.assert_frame_equal(df1, df2)


# ---------------------------------------------------------------------------
# generate_staking_rates
# ---------------------------------------------------------------------------


class TestStakingRates:
    def test_returns_expected_columns(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_staking_rates(["lido"], duration_days=30)
        expected = {"timestamp", "protocol", "staking_apy", "staking_rate_index"}
        assert set(df.columns) == expected

    def test_multiple_protocols(self, gen: SyntheticDataGenerator) -> None:
        protocols = ["lido", "etherfi", "rocket_pool"]
        df = gen.generate_staking_rates(protocols, duration_days=30)
        assert set(df["protocol"].unique()) == set(protocols)
        # Each protocol should have the same number of timestamps
        counts = df.groupby("protocol").size()
        assert counts.nunique() == 1

    def test_staking_index_starts_at_one(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_staking_rates(["lido"], duration_days=30)
        assert df["staking_rate_index"].iloc[0] == pytest.approx(1.0)

    def test_staking_index_monotonically_increasing(self, gen: SyntheticDataGenerator) -> None:
        df = gen.generate_staking_rates(["lido"], duration_days=30)
        idx = df["staking_rate_index"].to_numpy()
        diffs = np.diff(idx)
        assert np.all(diffs >= -1e-15), "staking_rate_index should be monotonically non-decreasing"

    def test_staking_apy_always_positive(self, gen: SyntheticDataGenerator) -> None:
        """Staking APY is clamped to min 0.001 (0.1%), never zero."""
        df = gen.generate_staking_rates(["lido", "etherfi"], duration_days=90)
        assert (df["staking_apy"] > 0).all()

    def test_staking_apy_in_realistic_range(self, gen: SyntheticDataGenerator) -> None:
        """APY should stay roughly in 1-10% range for a well-parameterised OU."""
        df = gen.generate_staking_rates(["lido"], duration_days=365)
        apys = df["staking_apy"].to_numpy()
        assert apys.min() >= 0.001  # clamped floor
        assert apys.max() < 0.20  # should not explode (OU is mean-reverting)

    def test_staking_index_growth_consistent(self, gen: SyntheticDataGenerator) -> None:
        """Over 1 year at ~4% APY, index should grow to roughly 1.04."""
        df = gen.generate_staking_rates(["lido"], duration_days=365)
        final = float(df["staking_rate_index"].iloc[-1])
        assert 1.02 < final < 1.08

    def test_default_params_for_unknown_protocol(self, gen: SyntheticDataGenerator) -> None:
        """Unknown protocol falls back to _default staking params."""
        df = gen.generate_staking_rates(["unknown_proto"], duration_days=30)
        assert len(df) > 0
        assert (df["staking_apy"] > 0).all()

    def test_custom_interval_hours(self, gen: SyntheticDataGenerator) -> None:
        """4-hour interval should produce fewer rows than 1-hour."""
        df_1h = gen.generate_staking_rates(["lido"], duration_days=30, interval_hours=1)
        gen2 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=42)
        df_4h = gen2.generate_staking_rates(["lido"], duration_days=30, interval_hours=4)
        assert len(df_1h) > len(df_4h)
