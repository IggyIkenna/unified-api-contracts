"""Unit tests for the public per-venue prediction/betting fee model.

Covers the Betfair exchange commission additions (constant, ``betfair_fee``
helper, and the bumped ``PREDICTION_VENUE_FEE_MODEL_VERSION``) alongside the
pre-existing Kalshi/Polymarket helpers, exercising every numeric and
control-flow branch.
"""

from __future__ import annotations

import math

from unified_api_contracts.predictions import (
    BETFAIR_COMMISSION_FRACTION,
    KALSHI_FEE_COEFF,
    POLYMARKET_FEE_FRACTION,
    PREDICTION_VENUE_FEE_MODEL_VERSION,
    betfair_fee,
    kalshi_fee,
    polymarket_fee,
)


def test_betfair_commission_constant() -> None:
    """Base rate is the standard 5% on net winnings."""
    assert BETFAIR_COMMISSION_FRACTION == 0.05


def test_betfair_fee_positive_winnings() -> None:
    """Winning bet: commission = fraction * net winnings."""
    assert math.isclose(betfair_fee(100.0), 5.0)
    assert math.isclose(betfair_fee(37.0), 37.0 * 0.05)


def test_betfair_fee_zero_winnings() -> None:
    """No net winnings → no commission (boundary of the max clamp)."""
    assert betfair_fee(0.0) == 0.0


def test_betfair_fee_negative_winnings_clamped() -> None:
    """Losing bet (negative net winnings) → 0, never a negative fee."""
    assert betfair_fee(-50.0) == 0.0


def test_version_string_mentions_betfair() -> None:
    """The model version must be bumped to advertise the Betfair coefficient."""
    assert "betfair" in PREDICTION_VENUE_FEE_MODEL_VERSION
    assert PREDICTION_VENUE_FEE_MODEL_VERSION == "v2_public_2026_07_kalshi0.07_poly0_betfair0.05"


def test_kalshi_fee_mid_is_convex_peak() -> None:
    """Sanity on the sibling helper: max fee at P=0.5, →0 at the tails."""
    mid = kalshi_fee(0.5)
    assert math.isclose(mid, KALSHI_FEE_COEFF * 0.25)
    assert kalshi_fee(0.5) > kalshi_fee(0.1)
    assert math.isclose(kalshi_fee(0.0), 0.0)
    assert math.isclose(kalshi_fee(1.0), 0.0)


def test_kalshi_fee_clamps_out_of_range() -> None:
    """Inputs outside [0, 1] are clamped before the formula (0 at both tails)."""
    assert math.isclose(kalshi_fee(-0.3), 0.0)
    assert math.isclose(kalshi_fee(1.4), 0.0)


def test_polymarket_fee_is_zero() -> None:
    """Polymarket is fee-free regardless of price."""
    assert polymarket_fee(0.5) == POLYMARKET_FEE_FRACTION
    assert polymarket_fee(0.9) == 0.0
