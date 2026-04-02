"""Index accumulation utilities for DeFi yield and staking rates.

Converts annualised percentage yields (APYs) and staking rates into
cumulative index time-series -- the standard representation used by
Aave's ``liquidity_index`` / ``variableBorrowIndex`` and by liquid
staking wrappers such as weETH/ETH.

Pure stdlib implementation (``datetime`` only, no numpy).

Functions:
    apy_to_cumulative_index: APY series -> cumulative liquidity index
    staking_rate_to_index:   Staking rate series -> cumulative index
"""

from __future__ import annotations

from datetime import datetime

# One year expressed in days -- used for annualisation.
_DAYS_PER_YEAR: float = 365.25


def _validate_inputs(
    values: list[float],
    timestamps: list[datetime],
) -> None:
    """Raise ``ValueError`` when *values* and *timestamps* are mismatched."""
    if len(values) != len(timestamps):
        raise ValueError(f"values length ({len(values)}) must equal timestamps length ({len(timestamps)})")


def _build_cumulative_index(
    rate_values: list[float],
    timestamps: list[datetime],
    base: float,
) -> list[float]:
    """Core accumulation shared by both public helpers.

    For each interval ``[i-1, i]`` the index grows by::

        index[i] = index[i-1] * (1 + rate * dt_years)

    where ``dt_years = (timestamps[i] - timestamps[i-1]).total_seconds()
    / (DAYS_PER_YEAR * 86400)``.
    """
    _validate_inputs(rate_values, timestamps)

    if len(rate_values) == 0:
        return []

    seconds_per_year = _DAYS_PER_YEAR * 86_400.0

    index: list[float] = [base]
    for i in range(1, len(rate_values)):
        dt_seconds = (timestamps[i] - timestamps[i - 1]).total_seconds()
        dt_years = dt_seconds / seconds_per_year
        index.append(index[-1] * (1.0 + rate_values[i - 1] * dt_years))

    return index


def apy_to_cumulative_index(
    apy_values: list[float],
    timestamps: list[datetime],
    base: float = 1.0,
) -> list[float]:
    """Convert an APY time-series into a cumulative index.

    This mirrors the Aave ``liquidity_index`` growth model:
    each interval compounds linearly at the prevailing APY.

    Args:
        apy_values: Annualised yields as decimals (e.g. ``0.05`` = 5 %).
        timestamps: Corresponding UTC timestamps (same length as *apy_values*).
        base: Starting index value (default ``1.0``).

    Returns:
        Cumulative index list of the same length as the inputs.

    Raises:
        ValueError: If *apy_values* and *timestamps* differ in length.
    """
    return _build_cumulative_index(apy_values, timestamps, base)


def staking_rate_to_index(
    rate_values: list[float],
    timestamps: list[datetime],
    base: float = 1.0,
) -> list[float]:
    """Convert a staking-rate time-series into a cumulative index.

    Semantically identical to :func:`apy_to_cumulative_index` but named
    for clarity when working with liquid-staking wrappers (e.g. weETH/ETH,
    stETH/ETH exchange rates).

    Args:
        rate_values: Annualised staking rates as decimals.
        timestamps: Corresponding UTC timestamps.
        base: Starting index value (default ``1.0``).

    Returns:
        Cumulative index list of the same length as the inputs.

    Raises:
        ValueError: If *rate_values* and *timestamps* differ in length.
    """
    return _build_cumulative_index(rate_values, timestamps, base)
