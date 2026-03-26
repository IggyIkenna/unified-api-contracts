"""Tests for SyntheticDataGenerator.generate_orderbook_snapshots().

Covers:
- Correct number of snapshots and levels
- Bid/ask ordering (bids descending, asks ascending)
- Spread is positive and reasonable
- Power-law size distribution (top of book thicker)
- Deterministic output with same seed
- Mid-price drift stays close to initial value
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.testing.synthetic import SyntheticDataGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_SPEC: dict[str, object] = {
    "gbm_params": {
        "BTC/USDT": {"vol": 0.80, "drift": 0.0, "base_price": 60000.0},
    },
}


@pytest.fixture()
def gen() -> SyntheticDataGenerator:
    return SyntheticDataGenerator(_MINIMAL_SPEC, seed=42)


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


class TestBasicStructure:
    def test_returns_correct_count(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=50)
        assert len(snapshots) == 50

    def test_default_count(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT")
        assert len(snapshots) == 100

    def test_snapshot_keys(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=5)
        for snap in snapshots:
            assert "symbol" in snap
            assert "timestamp" in snap
            assert "bids" in snap
            assert "asks" in snap
            assert "mid_price" in snap
            assert "spread_bps" in snap

    def test_correct_symbol(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("ETH/USDT", num_snapshots=3)
        for snap in snapshots:
            assert snap["symbol"] == "ETH/USDT"

    def test_correct_levels_count(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=5, levels=15)
        for snap in snapshots:
            bids: list[list[float]] = snap["bids"]  # type: ignore[assignment]
            asks: list[list[float]] = snap["asks"]  # type: ignore[assignment]
            assert len(bids) == 15
            assert len(asks) == 15


# ---------------------------------------------------------------------------
# Price ordering
# ---------------------------------------------------------------------------


class TestPriceOrdering:
    def test_bids_descending(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=10, levels=10)
        for snap in snapshots:
            bids: list[list[float]] = snap["bids"]  # type: ignore[assignment]
            prices = [b[0] for b in bids]
            for i in range(1, len(prices)):
                assert prices[i] <= prices[i - 1], f"Bid prices not descending: {prices}"

    def test_asks_ascending(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=10, levels=10)
        for snap in snapshots:
            asks: list[list[float]] = snap["asks"]  # type: ignore[assignment]
            prices = [a[0] for a in asks]
            for i in range(1, len(prices)):
                assert prices[i] >= prices[i - 1], f"Ask prices not ascending: {prices}"

    def test_best_bid_below_best_ask(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=50, levels=10)
        for snap in snapshots:
            bids: list[list[float]] = snap["bids"]  # type: ignore[assignment]
            asks: list[list[float]] = snap["asks"]  # type: ignore[assignment]
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            assert best_bid < best_ask, f"Best bid {best_bid} >= best ask {best_ask}"


# ---------------------------------------------------------------------------
# Spread and mid-price
# ---------------------------------------------------------------------------


class TestSpreadAndMidPrice:
    def test_spread_is_positive(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=50)
        for snap in snapshots:
            assert float(snap["spread_bps"]) > 0  # type: ignore[arg-type]

    def test_spread_stays_reasonable(self, gen: SyntheticDataGenerator) -> None:
        """Spread should stay within a reasonable range (1-30 bps)."""
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=200, spread_bps=5.0)
        for snap in snapshots:
            spread = float(snap["spread_bps"])  # type: ignore[arg-type]
            assert 0.5 < spread < 30.0, f"Spread {spread} bps out of range"

    def test_mid_price_near_initial(self, gen: SyntheticDataGenerator) -> None:
        """Mid price should drift slowly, staying within ~5% of initial."""
        initial = 60000.0
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=100, mid_price=initial)
        for snap in snapshots:
            mid = float(snap["mid_price"])  # type: ignore[arg-type]
            pct_change = abs(mid - initial) / initial
            assert pct_change < 0.05, f"Mid price drifted too far: {mid} vs initial {initial}"


# ---------------------------------------------------------------------------
# Power-law size distribution
# ---------------------------------------------------------------------------


class TestSizeDistribution:
    def test_sizes_are_positive(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=10, levels=10)
        for snap in snapshots:
            bids: list[list[float]] = snap["bids"]  # type: ignore[assignment]
            asks: list[list[float]] = snap["asks"]  # type: ignore[assignment]
            for lvl in bids:
                assert lvl[1] > 0, f"Bid size <= 0: {lvl}"
            for lvl in asks:
                assert lvl[1] > 0, f"Ask size <= 0: {lvl}"

    def test_top_of_book_thicker_on_average(self, gen: SyntheticDataGenerator) -> None:
        """On average, the top levels should have more liquidity (power-law)."""
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=500, levels=10)
        # Accumulate average size per level
        bid_level_totals = [0.0] * 10
        for snap in snapshots:
            bids: list[list[float]] = snap["bids"]  # type: ignore[assignment]
            for i, lvl in enumerate(bids):
                bid_level_totals[i] += lvl[1]

        # Level 0 (top) should have more total size than level 9 (deepest)
        assert bid_level_totals[0] > bid_level_totals[9], "Top of book should be thicker than deepest level on average"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_snapshots(self) -> None:
        gen1 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=42)
        gen2 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=42)
        snap1 = gen1.generate_orderbook_snapshots("BTC/USDT", num_snapshots=20)
        snap2 = gen2.generate_orderbook_snapshots("BTC/USDT", num_snapshots=20)
        assert snap1 == snap2

    def test_different_seed_different_snapshots(self) -> None:
        gen1 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=42)
        gen2 = SyntheticDataGenerator(_MINIMAL_SPEC, seed=99)
        snap1 = gen1.generate_orderbook_snapshots("BTC/USDT", num_snapshots=20)
        snap2 = gen2.generate_orderbook_snapshots("BTC/USDT", num_snapshots=20)
        # Mid prices should differ (different RNG sequences)
        mids1 = [s["mid_price"] for s in snap1]
        mids2 = [s["mid_price"] for s in snap2]
        assert mids1 != mids2


# ---------------------------------------------------------------------------
# Custom parameters
# ---------------------------------------------------------------------------


class TestCustomParameters:
    def test_custom_mid_price(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("ETH/USDT", num_snapshots=5, mid_price=2500.0)
        # First snapshot mid should be very close to 2500.0
        first_mid = float(snapshots[0]["mid_price"])  # type: ignore[arg-type]
        assert abs(first_mid - 2500.0) < 5.0

    def test_wide_spread(self, gen: SyntheticDataGenerator) -> None:
        """With a large spread_bps, the gap between best bid and ask is wider."""
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=50, spread_bps=20.0)
        avg_spread = sum(
            float(s["spread_bps"])
            for s in snapshots  # type: ignore[arg-type]
        ) / len(snapshots)
        # Average should be roughly near 20 bps (allowing stochastic noise)
        assert 10.0 < avg_spread < 30.0

    def test_single_level(self, gen: SyntheticDataGenerator) -> None:
        snapshots = gen.generate_orderbook_snapshots("BTC/USDT", num_snapshots=5, levels=1)
        for snap in snapshots:
            bids: list[list[float]] = snap["bids"]  # type: ignore[assignment]
            asks: list[list[float]] = snap["asks"]  # type: ignore[assignment]
            assert len(bids) == 1
            assert len(asks) == 1
