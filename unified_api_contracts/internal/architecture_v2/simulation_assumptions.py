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
# Registry — backfilled from the strategy-service backtest-runner scan (F11)
# ---------------------------------------------------------------------------

#: Candle granularities the backtest engine can simulate on, from the CLI
#: validation constant ``strategy_service/cli/resolvers.py:32`` (``TIMEFRAMES``).
_BACKTEST_GRANULARITIES: Final[list[str]] = ["1m", "5m", "15m", "1h", "4h", "24h"]

#: Shared batch↔live divergence note (the documented exceptions to the
#: "batch = live" HARD RULE), from ``strategy_service/engine/backtest/``:
#: benchmark_fills.py + batch_harness.py.
_BATCH_LIVE_DIVERGENCE: Final[str] = (
    "Batch fills are FillSource.BENCHMARK (benchmark_fills.py:91) — no real slippage, "
    "no partial fills; execution_alpha_bps hardcoded 0 (benchmark_fills.py:93). Live fills "
    "come from the matching engine (FillSource.MATCHING_ENGINE). Position state is held "
    "in-process by V2BatchHarness in batch (batch_harness.py:126); PBMS owns it live. "
    "Simulated deposits are batch-only (batch_harness.py:234-249)."
)

#: F11 ANSWER (gap tracker): the GroupBRunner is ONE category-agnostic engine
#: (runner.py:17-20). Fill model is dispatched by INSTRUCTION ACTION TYPE
#: (TRADE/SWAP/LEND/BORROW/STAKE/QUOTE/ATOMIC) in benchmark_fills.py, NOT by
#: archetype family — so simulation assumptions are keyed on the (venue,
#: instrument_type)→action surface, not on the archetype. The only
#: archetype-specific assumption is LIQUIDATION_CAPTURE → LIQUIDATION_BONUS
#: (benchmark_fills.py:273-286). Default engine mode is ARRIVAL_MID
#: (runner.py:191-193) → MatchingModel.CANDLE_CLOSE.
#:
#: BACKFILLED 2026-06-13 from the code-scan; every entry cites its source.

# Perp/spot CEX surfaces: TRADE action → ARRIVAL_MID → CANDLE_CLOSE.
# "drift" (Solana perp DEX) removed 2026-07-16 (operator ruling: all Solana perp DEXes dropped
# except Jupiter, not integrated). SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
_CLOB_PERP_VENUES: Final[list[str]] = ["hyperliquid", "binance", "bybit", "okx", "deribit", "gmx_v2"]
_CLOB_SPOT_VENUES: Final[list[str]] = ["binance", "bybit", "okx"]
# DeFi AMM surfaces: SWAP action → POOL_MID_AT_BLOCK.
_AMM_VENUES: Final[list[str]] = ["uniswap_v3", "curve", "balancer"]
# Lending surfaces: LEND/BORROW → FUNDING_SNAPSHOT.
_LENDING_VENUES: Final[list[str]] = ["aave_v3", "kamino"]
# Staking surfaces: STAKE/UNSTAKE → FUNDING_SNAPSHOT.
_STAKING_VENUES: Final[list[str]] = ["lido", "rocketpool", "jito", "marinade"]


def _sim(venue_id: str, instrument_type: str, model: MatchingModel, fill: str) -> SimulationAssumption:
    return SimulationAssumption(
        venue_id=venue_id,
        instrument_type=instrument_type,
        supported_granularities=list(_BACKTEST_GRANULARITIES),
        matching_model=model,
        fill_assumptions=f"{fill} {_BATCH_LIVE_DIVERGENCE}",
    )


SIM_ASSUMPTIONS_REGISTRY: Final[list[SimulationAssumption]] = [
    *[
        _sim(
            v,
            "perp",
            MatchingModel.CANDLE_CLOSE,
            "TRADE action → ARRIVAL_MID at signal-arrival mid (benchmark_fills.py:135-140).",
        )
        for v in _CLOB_PERP_VENUES
    ],
    *[
        _sim(v, "spot", MatchingModel.CANDLE_CLOSE, "TRADE action → ARRIVAL_MID (benchmark_fills.py:135-140).")
        for v in _CLOB_SPOT_VENUES
    ],
    _sim(
        "deribit",
        "option",
        MatchingModel.CANDLE_CLOSE,
        "Options trade as a TRADE action → ARRIVAL_MID (benchmark_fills.py:135-140); no options-specific fill model.",
    ),
    *[
        _sim(
            v,
            "swap",
            MatchingModel.POOL_MID_AT_BLOCK,
            "SWAP action → on-chain pool mid at block (benchmark_fills.py:143-146); degrades to ARRIVAL_MID if absent.",
        )
        for v in _AMM_VENUES
    ],
    *[
        _sim(
            v,
            "lend",
            MatchingModel.FUNDING_SNAPSHOT,
            "LEND/BORROW action → funding-snapshot price (benchmark_fills.py:136-139).",
        )
        for v in _LENDING_VENUES
    ],
    *[
        _sim(
            v,
            "stake",
            MatchingModel.FUNDING_SNAPSHOT,
            "STAKE/UNSTAKE action → funding-snapshot price (benchmark_fills.py:136-139).",
        )
        for v in _STAKING_VENUES
    ],
]


__all__ = [
    "MATCHING_MODEL_TO_BENCHMARK_FILL",
    "SIM_ASSUMPTIONS_REGISTRY",
    "MatchingModel",
    "SimulationAssumption",
]
