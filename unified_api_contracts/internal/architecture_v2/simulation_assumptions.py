"""Simulation-assumptions gap registry — matching/fill model, supported
granularities, and batch-live symmetry nuances per venue / instrument type.

STATUS: schema shipped; ``SIM_ASSUMPTIONS_REGISTRY`` is intentionally empty.
The ``MatchingModel`` vocabulary IS derived from ``BenchmarkFillMode`` (the
existing canonical enum in ``architecture_v2.enums``), which documents
per-action reference-price semantics used by the backtest matching engine.
Mapping those to the per-venue/granularity surface requires reading
``strategy_service/engine/backtest/runner.py`` — a ``needs_code_scan`` gap
documented in
``plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md``.

Key source:
  ``unified_api_contracts.internal.architecture_v2.enums.BenchmarkFillMode``
  (canonical per-action reference-price mode, used by the backtest engine).

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P1.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.enums import BenchmarkFillMode

# ---------------------------------------------------------------------------
# Matching model enum
# ---------------------------------------------------------------------------


class MatchingModel(StrEnum):
    """Simulation fill/matching model used by the backtest engine.

    Values are derived from ``BenchmarkFillMode`` in ``architecture_v2.enums``,
    which is the canonical SSOT for per-action reference-price semantics.
    The wizard exposes this as the "What simulation matching/fill assumptions
    will the backtest use here?" question (Stage E, capability-wizard-question-bank).

    Relationship to ``BenchmarkFillMode``:
    - ``CANDLE_CLOSE``        → ``BenchmarkFillMode.ARRIVAL_MID`` applied at
                                the candle-close bar boundary.
    - ``CANDLE_OHLC_INTERPOLATED`` → intra-bar interpolation over OHLC;
                                exact method is a ``needs_code_scan`` gap.
    - ``POOL_MID_AT_BLOCK``   → ``BenchmarkFillMode.POOL_MID_AT_BLOCK``
                                (DeFi swaps/LP; on-chain fill price).
    - ``FUNDING_SNAPSHOT``    → ``BenchmarkFillMode.FUNDING_SNAPSHOT``
                                (perp funding, lend/borrow, stake/unstake).
    - ``PASSIVE_BBO``         → ``BenchmarkFillMode.PASSIVE_BBO``
                                (market-making quote simulation).
    - ``LIQUIDATION_BONUS``   → ``BenchmarkFillMode.LIQUIDATION_BONUS``
                                (DeFi liquidation capture archetype).
    """

    CANDLE_CLOSE = "candle_close"
    """Fill at the close price of the candle in which the signal fired."""

    CANDLE_OHLC_INTERPOLATED = "candle_ohlc_interpolated"
    """Fill at an OHLC-interpolated price within the signal candle.
    Exact interpolation method: ``needs_code_scan`` gap."""

    POOL_MID_AT_BLOCK = "pool_mid_at_block"
    """Fill at the on-chain pool mid-price at the block of execution
    (DeFi swaps, LP mint/burn). Mirrors ``BenchmarkFillMode.POOL_MID_AT_BLOCK``."""

    FUNDING_SNAPSHOT = "funding_snapshot"
    """Fill at the funding-rate snapshot (perp funding, lending APY, staking APY).
    Mirrors ``BenchmarkFillMode.FUNDING_SNAPSHOT``."""

    PASSIVE_BBO = "passive_bbo"
    """Fill at the best bid/offer passively (market-making / quote archetypes).
    Mirrors ``BenchmarkFillMode.PASSIVE_BBO``."""

    LIQUIDATION_BONUS = "liquidation_bonus"
    """Fill at the collateral-plus-liquidation-bonus price.
    Mirrors ``BenchmarkFillMode.LIQUIDATION_BONUS``."""


#: Convenience mapping to the canonical ``BenchmarkFillMode`` counterparts.
#: Used by the exporter to assert consistency.
MATCHING_MODEL_TO_BENCHMARK_FILL: dict[MatchingModel, BenchmarkFillMode | None] = {
    MatchingModel.CANDLE_CLOSE: BenchmarkFillMode.ARRIVAL_MID,
    MatchingModel.CANDLE_OHLC_INTERPOLATED: None,  # needs_code_scan gap
    MatchingModel.POOL_MID_AT_BLOCK: BenchmarkFillMode.POOL_MID_AT_BLOCK,
    MatchingModel.FUNDING_SNAPSHOT: BenchmarkFillMode.FUNDING_SNAPSHOT,
    MatchingModel.PASSIVE_BBO: BenchmarkFillMode.PASSIVE_BBO,
    MatchingModel.LIQUIDATION_BONUS: BenchmarkFillMode.LIQUIDATION_BONUS,
}


# ---------------------------------------------------------------------------
# Simulation assumption model
# ---------------------------------------------------------------------------


class SimulationAssumption(BaseModel):
    """Simulation assumptions for a (venue, instrument_type) pair.

    Documents which candle granularities can be backtested, what fill model
    the engine uses, and any known batch-live asymmetries for that surface.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(
        description=(
            "Venue identifier matching the instruments-service / "
            "ENDPOINT_REGISTRY convention (e.g. ``'hyperliquid'``, "
            "``'binance'``, ``'uniswap_v3'``)."
        )
    )
    instrument_type: str | None = Field(
        default=None,
        description=(
            "Optional instrument-type scope "
            "(e.g. ``'perp'``, ``'spot'``, ``'lp'``). "
            "``None`` = applies to all instrument types at this venue."
        ),
    )
    supported_granularities: list[str] = Field(
        default_factory=list,
        description=(
            "Candle granularities available for backtesting at this venue/type "
            "(e.g. ``['1m', '5m', '1h', '1d']``). "
            "Tick data is listed as ``'tick'``. "
            "Empty = not registered."
        ),
    )
    matching_model: MatchingModel = Field(
        description=("Simulation fill / matching model used by the backtest engine for this venue / instrument type.")
    )
    fill_assumptions: str = Field(
        default="",
        description=(
            "Free-text description of fill assumptions: slippage model, "
            "partial-fill handling, PIT (point-in-time) guard behaviour "
            "(``backtest_pit_guard.py``), batch-live asymmetries, "
            "and any known divergences between backtest and live fills."
        ),
    )


# ---------------------------------------------------------------------------
# Registry — intentionally empty (honest gap, needs_code_scan)
# ---------------------------------------------------------------------------

#: Per-venue simulation assumptions.
#: Empty: mapping from (venue, instrument_type) to granularities + fill model
#: requires reading ``strategy_service/engine/backtest/runner.py``.
#: This is a ``needs_code_scan`` gap tracked in
#: ``plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md``.
SIM_ASSUMPTIONS_REGISTRY: Final[list[SimulationAssumption]] = []


__all__ = [
    "MATCHING_MODEL_TO_BENCHMARK_FILL",
    "SIM_ASSUMPTIONS_REGISTRY",
    "MatchingModel",
    "SimulationAssumption",
]
