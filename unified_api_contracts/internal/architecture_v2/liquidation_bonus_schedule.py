"""Liquidation-bonus schedule per DeFi protocol — G2.9 gap #4.

Stage 3E § 2.9 gap #4 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
Aave V3 liquidation bonus != Compound V3 != Euler != Morpho — each
protocol has its own per-collateral-token bonus schedule, close-factor
rules, and health-factor trigger. ``LIQUIDATION_CAPTURE`` computes edge
net-of-gas using these schedules.

Before this module, the schedule was hardcoded per-protocol inside
execution-service liquidation modules with no SSOT. Consequences:

* Changes to protocol governance (e.g. Aave DAO updating WBTC bonus
  from 7% to 6.5%) required editing N per-adapter constants.
* Backtest engine could drift from live because the live adapter was
  fixed but the backtest loader read stale fixtures.

This registry is the single source. Consumers call
``liquidation_bonus_for(protocol, chain, collateral_token, debt_token)``
and receive a frozen Pydantic record with bonus bps + close factor +
health-factor trigger + a ``source_url`` for audit.

Consumer integration:

* ``execution-service/execution_service/defi_execution/protocols/aave.py``
  — reads schedule at connect-time, fails loud on miss.
* Future ``LIQUIDATION_CAPTURE`` strategy (in ``strategy-service``) —
  edge-calc precision across Aave / Compound / Euler / Morpho / Kamino.
* Risk-and-exposure service — informs ``CARRY_RECURSIVE_STAKED``
  liquidation-risk modelling for collateral positions.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class LiquidationProtocol(StrEnum):
    """DeFi lending protocols with a liquidation bonus mechanism."""

    AAVE_V3 = "aave_v3"
    COMPOUND_V3 = "compound_v3"
    EULER = "euler"
    MORPHO = "morpho"
    KAMINO = "kamino"
    GMX_V2 = "gmx_v2"


class LiquidationBonusEntry(BaseModel):
    """One (protocol, chain, collateral, debt) schedule row.

    ``debt_token`` == None means "any debt token" — collapses rows that
    don't discriminate on debt. ``liquidation_bonus_bps`` is over 100%
    of the debt repaid (Aave v3 WBTC example: 700 = 7% bonus).
    ``close_factor`` is the fraction of debt that can be liquidated in
    a single tx (Aave v3 default 0.5 = 50%).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    protocol: LiquidationProtocol
    chain: str
    collateral_token: str
    debt_token: str | None = None
    liquidation_bonus_bps: int = Field(ge=0, le=5_000)
    close_factor: float = Field(gt=0.0, le=1.0)
    health_factor_trigger: float = Field(default=1.0, gt=0.0, le=2.0)
    source_url: str
    """Snapshot or governance proposal URL for audit trail."""


LIQUIDATION_BONUS_SCHEDULE: Final[tuple[LiquidationBonusEntry, ...]] = (
    # ── Aave V3 — Ethereum mainnet ─────────────────────────────────────
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.AAVE_V3,
        chain="ETHEREUM",
        collateral_token="WBTC",
        liquidation_bonus_bps=700,
        close_factor=0.5,
        source_url="https://app.aave.com/governance/proposals/aave-v3-ethereum",
    ),
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.AAVE_V3,
        chain="ETHEREUM",
        collateral_token="WETH",
        liquidation_bonus_bps=500,
        close_factor=0.5,
        source_url="https://app.aave.com/governance/proposals/aave-v3-ethereum",
    ),
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.AAVE_V3,
        chain="ETHEREUM",
        collateral_token="stETH",
        liquidation_bonus_bps=650,
        close_factor=0.5,
        source_url="https://app.aave.com/governance/proposals/steth-risk",
    ),
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.AAVE_V3,
        chain="ETHEREUM",
        collateral_token="USDC",
        liquidation_bonus_bps=450,
        close_factor=0.5,
        source_url="https://app.aave.com/governance/proposals/stablecoin-risk",
    ),
    # ── Aave V3 — Arbitrum ─────────────────────────────────────────────
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.AAVE_V3,
        chain="ARBITRUM",
        collateral_token="WBTC",
        liquidation_bonus_bps=750,
        close_factor=0.5,
        source_url="https://app.aave.com/governance/proposals/arbitrum-risk",
    ),
    # ── Compound V3 ────────────────────────────────────────────────────
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.COMPOUND_V3,
        chain="ETHEREUM",
        collateral_token="WETH",
        debt_token="USDC",
        liquidation_bonus_bps=500,
        close_factor=1.0,
        source_url="https://docs.compound.finance/v3/",
        # Compound V3 uses 100% close factor but staggered per-collateral.
    ),
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.COMPOUND_V3,
        chain="ETHEREUM",
        collateral_token="WBTC",
        debt_token="USDC",
        liquidation_bonus_bps=750,
        close_factor=1.0,
        source_url="https://docs.compound.finance/v3/",
    ),
    # ── Euler ──────────────────────────────────────────────────────────
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.EULER,
        chain="ETHEREUM",
        collateral_token="WETH",
        liquidation_bonus_bps=400,
        close_factor=0.2,
        source_url="https://docs.euler.finance/",
    ),
    # ── Morpho (aggregator — inherits from underlying markets) ─────────
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.MORPHO,
        chain="ETHEREUM",
        collateral_token="WBTC",
        liquidation_bonus_bps=700,
        close_factor=0.5,
        source_url="https://docs.morpho.org/",
    ),
    # ── Kamino (Solana) ────────────────────────────────────────────────
    LiquidationBonusEntry(
        protocol=LiquidationProtocol.KAMINO,
        chain="SOLANA",
        collateral_token="SOL",
        liquidation_bonus_bps=800,
        close_factor=0.5,
        source_url="https://docs.kamino.finance/",
    ),
)


class LiquidationBonusNotFoundError(LookupError):
    """Raised when ``liquidation_bonus_for(...)`` can't resolve."""


def liquidation_bonus_for(
    protocol: LiquidationProtocol,
    chain: str,
    collateral_token: str,
    debt_token: str | None = None,
    *,
    registry: Iterable[LiquidationBonusEntry] = LIQUIDATION_BONUS_SCHEDULE,
) -> LiquidationBonusEntry:
    """Resolve a schedule entry by (protocol, chain, collateral, debt).

    Match precedence:
    1. Exact (protocol, chain, collateral, debt) when ``debt_token`` is
       not None and a row explicitly declares that debt.
    2. Fallback to (protocol, chain, collateral) row with
       ``debt_token is None`` (any debt token).
    """

    exact: LiquidationBonusEntry | None = None
    wildcard: LiquidationBonusEntry | None = None
    for entry in registry:
        if entry.protocol is not protocol or entry.chain != chain or entry.collateral_token != collateral_token:
            continue
        if debt_token is not None and entry.debt_token == debt_token:
            exact = entry
            break
        if entry.debt_token is None:
            wildcard = entry
    result = exact or wildcard
    if result is None:
        raise LiquidationBonusNotFoundError(
            f"no liquidation bonus entry for protocol={protocol.value!r}, "
            f"chain={chain!r}, collateral={collateral_token!r}, debt={debt_token!r}",
        )
    return result


def bonuses_for_protocol(
    protocol: LiquidationProtocol,
    *,
    registry: Iterable[LiquidationBonusEntry] = LIQUIDATION_BONUS_SCHEDULE,
) -> tuple[LiquidationBonusEntry, ...]:
    """All schedule entries for a given protocol across chains."""

    return tuple(entry for entry in registry if entry.protocol is protocol)


def _validate_registry_invariants(
    registry: Iterable[LiquidationBonusEntry] = LIQUIDATION_BONUS_SCHEDULE,
) -> None:
    """Invariants:

    * (protocol, chain, collateral, debt_token) tuple unique.
    * ``source_url`` non-empty (audit trail mandatory).
    """

    seen: set[tuple[LiquidationProtocol, str, str, str | None]] = set()
    for entry in registry:
        key = (entry.protocol, entry.chain, entry.collateral_token, entry.debt_token)
        if key in seen:
            raise ValueError(
                f"duplicate schedule entry: {key!r}",
            )
        seen.add(key)
        if not entry.source_url:
            raise ValueError(
                f"{key!r}: source_url must be non-empty (audit trail)",
            )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "execution-service/execution_service/defi_execution/protocols/aave.py",
    "strategy-service/strategy_service/validation/data_certification.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "LIQUIDATION_BONUS_SCHEDULE",
    "LiquidationBonusEntry",
    "LiquidationBonusNotFoundError",
    "LiquidationProtocol",
    "bonuses_for_protocol",
    "liquidation_bonus_for",
]
