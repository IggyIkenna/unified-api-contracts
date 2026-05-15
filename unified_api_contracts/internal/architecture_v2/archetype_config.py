"""Archetype operational risk-knob SSOT — collateral, hedge ratio, position cap, kill switches.

Closes the genuine gap identified in the cross_cutting Tab 6.A finding (issue
doc ``plans/active/issues/cross_cutting_strategy_catalogue_already_shipped_2026_05_08.md``):
operational risk knobs were scattered across strategy-service runtime config and
risk-and-exposure-service. They now have a single canonical SSOT — this module —
re-exported through :mod:`unified_api_contracts.strategy`.

This is the **schema floor** + **May-23 cutover seed**. Per-archetype knobs for
the May-23 live archetypes are seeded below; the other 48 archetypes get rows
as they activate (each row addition is a deliberate operator decision, not a
default-fill — fail-loud via :func:`get_archetype_config` ``KeyError``).

Operational ground truth lives in strategy-service runtime config; this UAC
module carries the canonical schema + initial values. Runtime config reads
from UAC and may override per-client. Per-client overrides flow through
:class:`unified_api_contracts.internal.domain.strategy_service.client_config.ClientStrategyOverride`
(out of scope for this module).

Operator decision 2026-05-08 (Option A — extend existing v2 SSOTs, NOT
greenfield) is recorded in the issue doc frontmatter
(``operator_decision: option_a_extend_v2``); this module is the deliverable.

Plan: ``plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #1 [DESIGN+UAC] (operational risk knobs sub-item).

Cross-references:

* :class:`unified_api_contracts.internal.architecture_v2.enums.StrategyArchetype`
  — canonical archetype enum (53 members) this module keys against.
* :mod:`unified_api_contracts.internal.architecture_v2.archetype_capability` —
  per-(archetype, asset_group, instrument_type) coverage cells; orthogonal
  axis (this module is per-archetype, that one is per-cell).
* ``unified-trading-pm/codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``
  — cross-cutting risk-gate SSOT consumes :func:`archetype_kill_switch_thresholds`.
* ``unified-trading-pm/plans/active/alerting_service_live_rules_2026_05_07.md`` —
  Tab 5's alerting plan consumes :func:`archetype_kill_switch_thresholds` to
  wire the per-archetype circuit breakers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype


@dataclass(frozen=True, slots=True)
class ArchetypeConfig:
    """Operational risk knobs for a single :class:`StrategyArchetype`.

    All fields are nullable so per-archetype overrides can declare only the
    knobs that apply (e.g. spot-only Stat Arb has no ``collateral_currency``;
    single-leg directional has no ``hedge_ratio``).

    Bounds-validated via :meth:`__post_init__`:

    * ``position_cap_usd > 0`` if specified.
    * ``0 < kill_switch_drawdown_pct <= 1.0`` if specified.
    * ``0 < kill_switch_position_breach_pct <= 1.0`` if specified.
    * ``hedge_ratio >= 0`` if specified (negative would invert direction —
      paired strategies are net-long the lead leg by convention).

    Out-of-bounds values raise :class:`ValueError` with descriptive messages
    (fail-loud — partial-truth risk config is the worst-case silent corruption
    per CLAUDE.md "Honest absence vs fake placeholders" principle applied to
    risk parameters).

    Attributes:
        collateral_currency: Venue margin / collateral asset (e.g. ``"USDT"``,
            ``"USDC"``, ``"ETH"``, ``"USD"``). ``None`` when not applicable
            (spot-only Stat Arb, equity-cash strategies).
        hedge_ratio: For paired strategies (basis perp / staked basis / pairs
            / risk reversal), the ratio of hedge-leg notional to lead-leg
            notional. Typically ``1.0`` for delta-neutral pairs, ``<1`` for
            partial hedge, ``>1`` for over-hedged risk-reduction structures.
            ``None`` for single-leg directional strategies.
        position_cap_usd: Maximum gross notional position the strategy may
            hold (USD). Must be ``> 0`` if specified. ``None`` defers to the
            client-level cap in
            :class:`unified_api_contracts.internal.architecture_v2.capital_allocation.CapitalAllocation`.
        kill_switch_drawdown_pct: Strategy halts if realised peak-to-trough
            drawdown exceeds this fraction. Range ``(0, 1.0]``. Sanity bound:
            no May-23 archetype tolerates ``> 0.10`` per operator-confirmed
            risk envelope.
        kill_switch_position_breach_pct: Strategy halts if a single fill
            would breach :attr:`position_cap_usd` by this margin. Range
            ``(0, 1.0]``. Tighter for leveraged strategies (smaller breach
            tolerance = earlier kill before liquidation cascade).
        perp_venue: For paired archetypes whose hedge leg is a CeFi perp
            (e.g. ``CARRY_RECURSIVE_BORROW_PERP_HEDGED``), the canonical
            venue name where the perp short executes. Must be a member of
            :func:`unified_api_contracts.registry.get_perp_venues` if
            specified. ``None`` for archetypes without a perp leg.
    """

    collateral_currency: str | None = None
    hedge_ratio: float | None = None
    position_cap_usd: float | None = None
    kill_switch_drawdown_pct: float | None = None
    kill_switch_position_breach_pct: float | None = None
    perp_venue: str | None = None

    def __post_init__(self) -> None:
        if self.position_cap_usd is not None and self.position_cap_usd <= 0:
            raise ValueError(
                f"position_cap_usd must be > 0 if specified; got {self.position_cap_usd}",
            )
        if self.kill_switch_drawdown_pct is not None and not (0 < self.kill_switch_drawdown_pct <= 1.0):
            raise ValueError(
                f"kill_switch_drawdown_pct must be in (0, 1.0] if specified; got {self.kill_switch_drawdown_pct}",
            )
        if self.kill_switch_position_breach_pct is not None and not (0 < self.kill_switch_position_breach_pct <= 1.0):
            raise ValueError(
                "kill_switch_position_breach_pct must be in (0, 1.0] if specified; "
                f"got {self.kill_switch_position_breach_pct}",
            )
        if self.hedge_ratio is not None and self.hedge_ratio < 0:
            raise ValueError(
                f"hedge_ratio must be >= 0 if specified (negative inverts direction); got {self.hedge_ratio}",
            )
        if self.perp_venue is not None:
            from unified_api_contracts.registry import get_perp_venues

            valid_perp_venues = get_perp_venues()
            if self.perp_venue not in valid_perp_venues:
                raise ValueError(
                    f"perp_venue {self.perp_venue!r} not in get_perp_venues(); "
                    f"valid: {sorted(valid_perp_venues)}",
                )


# ---------------------------------------------------------------------------
# May-23 cutover seed — 5 archetypes the live-DeFi rollout activates.
#
# Adding rows for the other 48 archetypes is a follow-up that lands as those
# archetypes activate (each row is a deliberate operator decision; default for
# unseeded archetypes is :class:`KeyError` via :func:`get_archetype_config`).
#
# Numerical conventions:
#
# * ``position_cap_usd`` is gross notional in USD. Conservative for May-23
#   smoke (operator can ratchet up post-cutover). Smaller caps for higher-risk
#   structures (recursive staking, basis dated).
# * ``kill_switch_drawdown_pct = 0.10`` is the May-23 default; tightened to
#   0.05 for ``CARRY_RECURSIVE_STAKED`` because leverage amplifies drawdown
#   into liquidation cascade territory.
# * ``kill_switch_position_breach_pct = 0.05`` default; tightened to 0.03 for
#   ``CARRY_RECURSIVE_STAKED`` to stop accumulating size before liquidation.
# * ``hedge_ratio = 1.0`` for paired carry archetypes (delta-neutral lead +
#   hedge); ``None`` for single-leg directional ML.
# * ``collateral_currency`` reflects the venue / chain margin asset. For
#   multi-venue archetypes (``CARRY_BASIS_PERP`` across 6 perp venues), the
#   USDT default reflects the dominant Tether-margined perp; per-venue
#   overrides flow through ``ClientStrategyOverride``. ``ETH`` for
#   Ethereum-staked-basis, with ``SOL`` overrides via per-client config when
#   the strategy runs on Solana LSTs (jitoSOL / mSOL / bSOL).
# ---------------------------------------------------------------------------


ARCHETYPE_CONFIG_SEED: Final[dict[StrategyArchetype, ArchetypeConfig]] = {
    StrategyArchetype.CARRY_STAKED_BASIS: ArchetypeConfig(
        collateral_currency="ETH",
        hedge_ratio=1.0,
        position_cap_usd=50_000.0,
        kill_switch_drawdown_pct=0.10,
        kill_switch_position_breach_pct=0.05,
    ),
    StrategyArchetype.CARRY_BASIS_PERP: ArchetypeConfig(
        collateral_currency="USDT",
        hedge_ratio=1.0,
        position_cap_usd=50_000.0,
        kill_switch_drawdown_pct=0.10,
        kill_switch_position_breach_pct=0.05,
    ),
    StrategyArchetype.CARRY_BASIS_DATED: ArchetypeConfig(
        collateral_currency="USDT",
        hedge_ratio=1.0,
        position_cap_usd=25_000.0,
        kill_switch_drawdown_pct=0.10,
        kill_switch_position_breach_pct=0.05,
    ),
    StrategyArchetype.CARRY_RECURSIVE_STAKED: ArchetypeConfig(
        collateral_currency="ETH",
        hedge_ratio=1.0,
        # Smaller cap due to liquidation-cascade risk in recursive staking.
        position_cap_usd=25_000.0,
        # Tighter drawdown gate — leverage amplifies p2t into liquidation territory.
        kill_switch_drawdown_pct=0.05,
        # Tighter breach gate — stop accumulating size before liquidation.
        kill_switch_position_breach_pct=0.03,
    ),
    # Family 1 — pure-lending recursive arb (no perp leg). Per
    # defi_recursive_borrow_archetypes_2026_05_10.md Family 1 design 2026-05-12.
    # No perp hedge → hedge_ratio=None; single-asset delta exposure equals base capital.
    StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY: ArchetypeConfig(
        collateral_currency="USDC",
        hedge_ratio=None,
        # Smaller cap than CARRY_RECURSIVE_STAKED — Family 1 hasn't been live-tested.
        position_cap_usd=15_000.0,
        # Drawdown gate tighter than CARRY_RECURSIVE_STAKED — pure-lending recursion has
        # no perp-hedge dampener on adverse moves; LST/ETH peg risk is the dominant tail.
        kill_switch_drawdown_pct=0.04,
        # Breach gate tighter than CARRY_RECURSIVE_STAKED — protect against position-size
        # creep when HF buffer is the load-bearing safety mechanism.
        kill_switch_position_breach_pct=0.025,
    ),
    # Family 2 — Family 1 + USDC-margined perp short for delta neutrality. Per
    # defi_recursive_borrow_archetypes_2026_05_10.md Family 2 design 2026-05-12.
    # Perp leg neutralises ETH-correlated delta → hedge_ratio=1.0 (matches base).
    StrategyArchetype.CARRY_RECURSIVE_BORROW_PERP_HEDGED: ArchetypeConfig(
        collateral_currency="ETH",
        hedge_ratio=1.0,
        # Slightly larger cap than Family 1 — perp hedge reduces directional tail risk.
        # Still smaller than CARRY_RECURSIVE_STAKED — Family 2 adds funding-flip + cross-
        # venue delta-drift risk surfaces not present in canonical staked-basis carry.
        position_cap_usd=20_000.0,
        # Drawdown gate slightly looser than Family 1 (perp dampens spot moves) but
        # tighter than CARRY_RECURSIVE_STAKED (additional funding-sign-flip tail).
        kill_switch_drawdown_pct=0.045,
        # Breach gate matches Family 1 — same HF-buffer-driven safety mechanism.
        kill_switch_position_breach_pct=0.03,
        # May-23 default perp hedge venue. Bybit alternative available via cell-id
        # override per defi_recursive_borrow_archetypes_2026_05_10.md variant-naming
        # decision (single archetype + perp_venue config field, no per-venue tarballs).
        perp_venue="HYPERLIQUID",
    ),
    StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS: ArchetypeConfig(
        collateral_currency="USDT",
        # Single-leg directional — no hedge.
        hedge_ratio=None,
        position_cap_usd=25_000.0,
        kill_switch_drawdown_pct=0.10,
        kill_switch_position_breach_pct=0.05,
    ),
}
"""May-23 cutover seed for live archetypes.

Five archetypes covered: ``CARRY_STAKED_BASIS`` (DeFi lead — Solana / Ethereum
LSTs), ``CARRY_BASIS_PERP`` (CeFi 6-perp-venue funding capture),
``CARRY_BASIS_DATED`` (CeFi/TradFi expiring-future basis),
``CARRY_RECURSIVE_STAKED`` (leveraged ETH staking), and
``ML_DIRECTIONAL_CONTINUOUS`` (CeFi-ML on OKX / Binance / Bybit).

The other 48 archetypes get seeded as they activate. Default for unseeded
archetypes is :class:`KeyError` via :func:`get_archetype_config` — fail-loud
forces a deliberate operator decision rather than a silent permissive default.
"""


def get_archetype_config(archetype: StrategyArchetype) -> ArchetypeConfig:
    """Resolve the operational config for ``archetype``.

    Args:
        archetype: A :class:`StrategyArchetype` member.

    Returns:
        The seeded :class:`ArchetypeConfig`.

    Raises:
        KeyError: If ``archetype`` is not in :data:`ARCHETYPE_CONFIG_SEED`.
            The error message names the missing archetype so the operator
            can add a row deliberately rather than silently defaulting to
            permissive values.
    """
    if archetype not in ARCHETYPE_CONFIG_SEED:
        raise KeyError(
            f"ArchetypeConfig not declared for {archetype!r}. "
            f"Add a seed row in archetype_config.ARCHETYPE_CONFIG_SEED before "
            f"activating this archetype — defaults are intentionally absent.",
        )
    return ARCHETYPE_CONFIG_SEED[archetype]


def is_archetype_config_declared(archetype: StrategyArchetype) -> bool:
    """Return ``True`` if ``archetype`` has an entry in :data:`ARCHETYPE_CONFIG_SEED`.

    Companion to :func:`get_archetype_config` for callers that want
    membership-check semantics without the ``KeyError``. Used by the
    deployment-UI strategy catalogue drilldown to render "config: declared /
    pending" badges per archetype.
    """
    return archetype in ARCHETYPE_CONFIG_SEED


def archetype_kill_switch_thresholds(
    archetype: StrategyArchetype,
) -> tuple[float | None, float | None]:
    """Return ``(drawdown_pct, position_breach_pct)`` for ``archetype``.

    Convenience accessor consumed by the alerting-service kill-switch wiring
    (per ``alerting_service_live_rules_2026_05_07.md``) and by the
    risk-and-exposure-service pre-trade gate (per
    ``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``).

    Args:
        archetype: A :class:`StrategyArchetype` member.

    Returns:
        Tuple of ``(kill_switch_drawdown_pct, kill_switch_position_breach_pct)``
        from the seeded config. Either field can be ``None`` per
        :class:`ArchetypeConfig` semantics (e.g. archetypes without a position
        cap also have no breach threshold).

    Raises:
        KeyError: If ``archetype`` is not in :data:`ARCHETYPE_CONFIG_SEED`.
            See :func:`get_archetype_config`.
    """
    config = get_archetype_config(archetype)
    return (config.kill_switch_drawdown_pct, config.kill_switch_position_breach_pct)


__all__ = [
    "ARCHETYPE_CONFIG_SEED",
    "ArchetypeConfig",
    "archetype_kill_switch_thresholds",
    "get_archetype_config",
    "is_archetype_config_declared",
]
