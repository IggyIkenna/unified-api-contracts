"""Archetype leg-spec SEEDS — per-archetype structural builders for ALL 57 (F22 / Phase 6A).

WHY THIS MODULE EXISTS (split from ``archetype_leg_spec.py``, Phase 6A):
The schema (``ArchetypeLegStructure`` / ``ArchetypeLegSpec`` / ``LegConstraint``)
lives in ``archetype_leg_spec.py``. The per-archetype SEED builders were split
out here so the full 57-archetype backfill (Phase 6A) fits the 900-line file cap.
``archetype_leg_spec._build_registry`` imports ``build_all_structures()`` from
here and keys it by archetype.

LOGIC FREEZE / SOURCING (operator requirement — "every single possible one"):
Every leg is a *citation of* the shipped engine structure + the codex archetype
doc + the existing capability cells — NEVER invented. Each leg names its source in
``source_of_truth``. The three sources used per leg:
  (a) the archetype's engine class in strategy-service
      (``strategy_service/engine/strategies/v2/.../`` — the ``_build_legs`` /
      ``AtomicLeg`` / instruction structure), where one exists;
  (b) its codex doc ``codex/09-strategy/architecture-v2/archetypes/<kebab>.md``;
  (c) the ``ARCHETYPE_CAPABILITY_REGISTRY`` cell notes + venue lists.

EXHAUSTIVE ENUMERATION: ``build_all_structures()`` returns a structure for EVERY
``StrategyArchetype`` value (57). Where a leg structure is GENUINELY underivable —
no engine in ``ARCHETYPE_ENGINE_REGISTRY`` AND no structural legs in the codex doc
(a pure meta-allocation overlay, or an archetype intentionally absent pending an
upstream feed) — the builder emits a ``not_registered`` structure
(``legs=()`` + a cited ``not_registered_reason``) so the registry NEVER has an
absent key. The honest gaps as of Phase 6A:
  - ARBITRAGE_MEV_SANDWICH — theoretical-only tracer (``sandwich_theoretical.py``),
    intentionally absent from the strategy factory pending mempool data (Bloxroute
    feed removed); codex doc status=theoretical-only.
  - PORTFOLIO_FACTOR_ALLOCATION / PORTFOLIO_MULTI_STRATEGY / PORTFOLIO_RISK_PARITY /
    PORTFOLIO_TACTICAL_OVERLAY — pure meta-allocation overlays (``venue_universe=[]``;
    allocate equity across child strategies, no direct instrument legs).

The 18 engined archetypes are sourced from the strategy factory
(``strategy_service/engine/strategies/v2/factory.py`` →
``ARCHETYPE_ENGINE_REGISTRY``); the design-status vol / market-making /
cross-domain archetypes (registered in cells + full codex docs) are sourced from
their codex doc structure + cells.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.archetype_leg_spec import (
    ArchetypeLegRole,
    ArchetypeLegSpec,
    ArchetypeLegStructure,
    LegConstraint,
    LegConstraintKind,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    AtomicExecutionMode,
    StrategyArchetype,
    VenueCategoryV2,
)

# ---------------------------------------------------------------------------
# Citation shorthands + shared venue tuples (carry / yield family)
# ---------------------------------------------------------------------------

_ENGINE_STAKED = (
    "strategy-service CarryStakedBasisEngine._build_legs / _derive_structure "
    "(staked_basis.py); catalog_staked_basis.py venue tuples"
)
_CELL_STAKED = (
    "manifest cell CARRY_STAKED_BASIS (DEFI, staking) notes '3-leg ATOMIC "
    "(stake + lending + perp)' + slot labels lido-aave-hyperliquid / "
    "jito-kamino-bybit / lido-aave-{binance,bybit,deribit,okx}"
)
_DOC_STAKED = (
    "codex/09-strategy/architecture-v2/archetypes/carry-staked-basis.md § 'Token / position flow — LST_AS_MARGIN'"
)

#: "drift" (Solana perp DEX) removed 2026-07-16 (operator ruling: all Solana perp DEXes dropped
#: except Jupiter, not integrated). Solana-side hedge now runs via the CeFi perp venues below
#: (see jito-kamino-bybit-sol-usdt-prod slot label). SSOT:
#: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
#: "gmx_v2" removed 2026-07-25 (unreliable historical funding data — see
#: unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
_STAKED_HEDGE_VENUES: Final[tuple[str, ...]] = (
    "hyperliquid",
    "binance",
    "bybit",
    "deribit",
    "okx",
)
_STAKE_PROTOCOLS_ETH_SOL: Final[tuple[str, ...]] = (
    "lido",
    "rocketpool",
    "etherfi",  # 2026-07-24 containment fix — catalog_staked_basis.py's _STAKED_BASIS_ETH_LSTS
    # includes ("ETHERFI", "weETH"); confirmed missing via the Side-decision 2 containment check
    # (defi_archetype_universe_no_curtailment_mechanism_2026_07_23.md).
    "jito",
    "marinade",
)
_LEND_VENUES_STAKED: Final[tuple[str, ...]] = ("aave_v3", "kamino")
# Spot-leg (USDC→native SWAP) venues for CARRY_STAKED_BASIS — operator-
# selectable, NOT hardcoded per-LST (operator directive 2026-06-17; plan
# ``defi_collateral_sizing_and_wizard_full_parameterization_2026_06_17`` Phase
# D + issue ``e2e_defi_config_taxonomy_wizard_roundtrip`` D3). The SWAP leg
# trades the START STABLE → NATIVE asset (USDC→ETH / USDC→SOL), NOT the LST
# (that is the downstream STAKE leg), so the eligibility test is "does this
# venue trade USDC↔{ETH,SOL} spot" — the realistic liquid set spans a CEX
# (Binance-spot) and the family DEXes, each more liquid for different pairs.
# Every id is a registered venue (CARRY_BASIS_PERP spot leg + KNOWN_VENUE_TOKENS
# / venue catalog) that genuinely lists the native USDC pair:
#   * ETH (USDC↔ETH): ``uniswap_v3`` (deepest USDC/WETH pool), ``curve``
#     (tricrypto USDC↔ETH), ``binance`` (BINANCE-SPOT ETH/USDC).
#   * SOL (USDC↔SOL): ``jupiter`` (Solana DEX aggregator), ``orca`` (SOL/USDC
#     whirlpool), ``raydium`` (SOL/USDC AMM), ``binance`` (BINANCE-SPOT SOL/USDC).
# Union (sorted) — the engine catalog (catalog_staked_basis.py) emits one slot
# per (LST x spot_venue), and the wizard renders these as the spot-leg picker.
_SPOT_VENUES_STAKED: Final[tuple[str, ...]] = (
    "binance",
    "curve",
    "jupiter",
    "orca",
    "raydium",
    "uniswap_v3",
)

# Shared venue tuples for the design-status families (from cells + codex docs).
# F39: added kraken (kraken_rest_adapter.py:159 KRAKEN-FUTURES/SPOT adapter) and
# bitget (bitget_native.py:125 BITGET-FUTURES/SPOT adapter) — both are real CeFi
# CLOB venues with execution adapters in execution_service/trade_execution/adapters/.
_CEFI_CLOB_VENUES: Final[tuple[str, ...]] = (
    "binance",
    "bitget",  # F39: bitget_native.py:125 (BITGET-FUTURES/SPOT adapter)
    "bybit",
    "deribit",
    "hyperliquid",
    "kraken",  # F39: kraken_rest_adapter.py:159 (KRAKEN-FUTURES/SPOT adapter)
    "okx",
)
_OPTIONS_VENUES: Final[tuple[str, ...]] = ("deribit", "okx")
_OPTIONS_VENUES_WITH_CBOE: Final[tuple[str, ...]] = ("deribit", "okx", "cboe")
_DEX_SWAP_VENUES: Final[tuple[str, ...]] = (
    "uniswap_v3",
    "pancakeswap_v3",
    "sushiswap_v3",
    # 2026-07-24 containment fix — catalog_yield_defi.py's build_liquidation_capture() uses
    # swap_venue="aerodrome" (Base-chain row) and swap_venue="raydium" (Solana row); confirmed
    # missing via the Side-decision 2 containment check
    # (defi_archetype_universe_no_curtailment_mechanism_2026_07_23.md).
    "aerodrome",
    "raydium",
)
_LENDING_PROTOCOLS: Final[tuple[str, ...]] = ("aave_v3", "compound_v3", "morpho", "euler", "fluid")
_EVENT_SETTLED_VENUES: Final[tuple[str, ...]] = (
    "betfair_direct",
    "smarkets_direct",
    "matchbook_direct",
    "unity",
    "polymarket",
)
_PREDICTION_VENUES: Final[tuple[str, ...]] = ("polymarket", "kalshi")


def _atomic_constraint(bundle_id: str, description: str) -> LegConstraint:
    """A requires_atomic_bundle constraint (revert-all-or-nothing leg coupling)."""

    return LegConstraint(
        kind=LegConstraintKind.REQUIRES_ATOMIC_BUNDLE,
        params={"bundle_id": bundle_id},
        description=description,
    )


# ---------------------------------------------------------------------------
# Carry / yield family (the original F22 seeds — moved verbatim)
# ---------------------------------------------------------------------------


def _staked_basis_collateral_constraint() -> LegConstraint:
    """The staked-vs-straight-basis conditional (the F22 headline constraint)."""

    return LegConstraint(
        kind=LegConstraintKind.REQUIRES_COLLATERAL_ACCEPTANCE,
        params={"asset": "lst_token", "venue_role": "hedge_short"},
        fallback_variant="straight_basis",
        description=(
            "The LST must be accepted as cross-margin at the perp hedge venue "
            "(engine gate: accepted_perp_collateral(perp_venue)). On venues that "
            "accept the LST → staked basis (earn staking yield + funding). On "
            "venues that do NOT accept the LST as collateral → the stake leg is "
            "dropped and this runs as a straight perp-funding basis "
            "(== CARRY_BASIS_PERP) within the same archetype."
        ),
    )


def _staked_basis_structure(
    archetype: StrategyArchetype,
    *,
    hedge_role: ArchetypeLegRole,
    hedge_instrument: ArchetypeInstrumentType,
    notes: str,
) -> ArchetypeLegStructure:
    """Build a CARRY_STAKED_BASIS-family structure (perp or dated hedge)."""

    coll = _staked_basis_collateral_constraint()
    atomic = _atomic_constraint(
        "staked_basis",
        (
            "The SWAP→STAKE→TRANSFER→hedge sequence is coupled (LEADER_HEDGE): "
            "the hedge must fill within hedge_deadline_ms of the staked leader "
            "or the leader is closed (CompensationPolicy.CLOSE_LEADER_IF_HEDGE_FAILS)."
        ),
    )
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="spot",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.DEFI, VenueCategoryV2.CEFI),
                eligible_venue_ids=_SPOT_VENUES_STAKED,
                signal_variants=(),
                constraints=(),
                source_of_truth=f"{_ENGINE_STAKED} (SWAP leader leg, role=leader); {_DOC_STAKED}",
            ),
            ArchetypeLegSpec(
                leg_id="stake",
                role=ArchetypeLegRole.STAKE,
                required=False,  # dropped in straight-basis fallback
                instrument_types=(ArchetypeInstrumentType.STAKING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_STAKE_PROTOCOLS_ETH_SOL,
                signal_variants=("staking_apy_total",),
                constraints=(coll,),
                source_of_truth=f"{_ENGINE_STAKED} (STAKE leg, role=stake); {_CELL_STAKED}",
            ),
            ArchetypeLegSpec(
                leg_id="lend",
                role=ArchetypeLegRole.LEND,
                required=False,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_LEND_VENUES_STAKED,
                signal_variants=(),
                constraints=(),
                source_of_truth=(
                    f"{_CELL_STAKED} (lend@aave/kamino encoded in slot labels "
                    "lido-AAVE-hyperliquid / jito-KAMINO-bybit)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="hedge",
                role=hedge_role,
                required=True,
                instrument_types=(hedge_instrument,),
                asset_groups=(VenueCategoryV2.DEFI, VenueCategoryV2.CEFI),
                eligible_venue_ids=_STAKED_HEDGE_VENUES,
                signal_variants=("dynamic_hedge_ratio",),
                constraints=(coll, atomic),
                source_of_truth=(f"{_ENGINE_STAKED} (TRADE hedge leg, role=hedge, leg_type=PERP); {_CELL_STAKED}"),
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes=notes,
    )


def _basis_perp_structure(archetype: StrategyArchetype, *, inverse: bool, notes: str) -> ArchetypeLegStructure:
    """CARRY_BASIS_PERP (+ _INV): spot + perp delta-neutral basis."""

    perp_role = ArchetypeLegRole.PERP_LONG if inverse else ArchetypeLegRole.PERP_SHORT
    same_venue = LegConstraint(
        kind=LegConstraintKind.REQUIRES_SAME_VENUE,
        params={"other_leg_id": "spot"},
        description=(
            "Single-venue netted basis (spot + perp on one CEX) is the most "
            "capital-efficient form (manifest cell note 'single-venue netted'); "
            "cross-venue form runs LEADER_HEDGE instead."
        ),
    )
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="spot",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
                eligible_venue_ids=(
                    "aster",  # 2026-07-24 containment fix: catalog_carry.py _CARRY_BASIS_PERP_VENUE_BUNDLES
                    # sets spot_venue=full_venue for every single-venue-netted bundle (incl. aster/deribit/
                    # kalshi-perp/polymarket-perp) — see defi_archetype_universe_no_curtailment_
                    # mechanism_2026_07_23.md Finding 3 addendum + Side-decision 2 containment check.
                    "binance",
                    "bitfinex",  # bitfinex_native.py:167 (BITFINEX-SPOT adapter — spot only, no futures adapter exists)
                    "bitget",  # F39: bitget_native.py:125 (BITGET-SPOT adapter — spot leg)
                    "bybit",
                    "coinbase",  # F39: coinbase_ccxt.py:32 (COINBASE-SPOT adapter)
                    "deribit",  # 2026-07-24 containment fix (see aster comment above)
                    # "gmx_v2" removed 2026-07-25 (unreliable historical funding data — see
                    # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
                    "hyperliquid",
                    "kalshi_perp",  # 2026-07-24 containment fix (see aster comment above); distinct from
                    # bare "kalshi" (the event-market product) — VENUE_TO_ADAPTER_KEY["KALSHI-PERP"]="kalshi_perp".
                    "kraken",  # F39: kraken_rest_adapter.py:159 (KRAKEN-SPOT adapter — spot leg)
                    "okx",
                    "polymarket_perp",  # 2026-07-24 containment fix (see aster comment above); distinct from
                    # bare "polymarket" — VENUE_TO_ADAPTER_KEY["POLYMARKET-PERP"]="polymarket_perp".
                    "raydium",  # 2026-07-24 containment fix — catalog_carry.py's cross-venue row
                    # ("raydium", "hyperliquid", "sol", ...) sets spot_venue="raydium" (SOL/USDC AMM,
                    # DEX spot leg paired with a Hyperliquid perp hedge); confirmed missing via the
                    # Side-decision 2 containment check.
                    "uniswap_v3",
                ),
                source_of_truth=(
                    "manifest cell CARRY_BASIS_PERP (CEFI/DEFI, perp) venue_ids + "
                    "slot labels; strategy-service CarryBasisPerpEngine (basis_perp.py)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="perp",
                role=perp_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.PERP,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
                eligible_venue_ids=(
                    "aster",  # 2026-07-24 containment fix — live in catalog_carry.py's
                    # _CARRY_BASIS_PERP_VENUE_BUNDLES ("kalshi-perp live from 2026-05-29" per that
                    # file's own comment) — confirmed missing by the Finding 3 reconciliation-direction
                    # addendum (defi_archetype_universe_no_curtailment_mechanism_2026_07_23.md).
                    "binance",
                    "bitfinex",  # 2026-07-24 containment fix — catalog's BITFINEX-FUTURES venue bundle sets
                    # perp_venue=BITFINEX-FUTURES too; NOTE this may itself be a pre-existing catalog bug
                    # (bitfinex_native.py only ships a SPOT adapter per this file's own comment above) —
                    # flagged as a separate, out-of-scope finding, not fixed here (containment-check scope
                    # is catalog-declares vs UAC-cites, not catalog-declaration correctness).
                    "bitget",  # F39: bitget_native.py:125 (BITGET-FUTURES adapter — perp leg)
                    "bybit",
                    "deribit",
                    "hyperliquid",
                    "kalshi_perp",  # 2026-07-24 containment fix (see aster comment above)
                    "kraken",  # F39: kraken_rest_adapter.py:159 (KRAKEN-FUTURES adapter — perp leg)
                    "okx",
                    "polymarket_perp",  # 2026-07-24 containment fix (see aster comment above)
                ),
                signal_variants=("funding_rate_annualised_bps",),
                constraints=(same_venue,),
                source_of_truth=(
                    "strategy-service CarryBasisPerpEngine.on_tick (basis_perp.py, "
                    "direction flips on funding sign); manifest cell CARRY_BASIS_PERP"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes=notes,
    )


def _funding_dispersion_structure() -> ArchetypeLegStructure:
    """CARRY_FUNDING_DISPERSION: dollar-neutral (NOT delta-neutral) cross-sectional funding-rank reversion.

    Long the lowest-funding / short the highest-funding perps — DIFFERENT coins, same arbitraged venue. The
    two legs are independent directional positions, dollar-neutral in aggregate (residual market beta is hedged
    at the BOOK level via beta-hedge + vol-target overlays, not leg-vs-leg), so they are paced in, not atomically
    coupled or leader/hedge. The reversion edge is venue-dependent (Binance/Bybit/OKX/Aster); Hyperliquid is
    momentum and is excluded at the signal layer.
    """
    arbitraged_perp_venues = (
        "aster",  # 2026-07-24 containment fix — catalog_carry.py's _FUNDING_DISPERSION_VENUES
        # includes aster/kalshi-perp/polymarket-perp; confirmed missing via the Side-decision 2
        # containment check (defi_archetype_universe_no_curtailment_mechanism_2026_07_23.md).
        "binance",
        "bitget",
        "bybit",
        "kalshi_perp",  # 2026-07-24 containment fix (see aster comment above)
        "kraken",
        "okx",
        "polymarket_perp",  # 2026-07-24 containment fix (see aster comment above)
    )
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.CARRY_FUNDING_DISPERSION,
        legs=(
            ArchetypeLegSpec(
                leg_id="perp_long",
                role=ArchetypeLegRole.PERP_LONG,
                required=True,
                instrument_types=(ArchetypeInstrumentType.PERP,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
                eligible_venue_ids=arbitraged_perp_venues,
                signal_variants=("funding_rank_pct", "funding_rate_annualised_bps"),
                source_of_truth=(
                    "strategy-service CarryFundingDispersionEngine.on_tick (funding_dispersion.py — LONG the "
                    "lowest cross-sectional funding rank)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="perp_short",
                role=ArchetypeLegRole.PERP_SHORT,
                required=True,
                instrument_types=(ArchetypeInstrumentType.PERP,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
                eligible_venue_ids=arbitraged_perp_venues,
                signal_variants=("funding_rank_pct", "funding_rate_annualised_bps"),
                source_of_truth=(
                    "strategy-service CarryFundingDispersionEngine.on_tick (funding_dispersion.py — SHORT the "
                    "highest cross-sectional funding rank)"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes=(
            "Dollar-neutral (NOT delta-neutral) cross-sectional funding-rank reversion: long lowest-funding / "
            "short highest-funding PERPS on different coins, same arbitraged venue. Per-coin directional; "
            "aggregate dollar-neutral; residual BTC-beta hedged at the book level. Venue-dependent (HL excluded "
            "— momentum). SSOT: carry_staked_basis_funding_scan_experiment_2026_06_16.md."
        ),
    )


def _basis_dated_structure(archetype: StrategyArchetype, *, inverse: bool, notes: str) -> ArchetypeLegStructure:
    """CARRY_BASIS_DATED (+ _INV): spot + dated future cash-and-carry."""

    future_role = ArchetypeLegRole.FUTURE_LONG if inverse else ArchetypeLegRole.FUTURE_SHORT
    spot_role = ArchetypeLegRole.SPOT_SHORT if inverse else ArchetypeLegRole.SPOT_LONG
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="spot",
                role=spot_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.TRADFI),
                eligible_venue_ids=(
                    "binance",
                    "bitfinex",  # bitfinex_native.py:167 (BITFINEX-SPOT adapter — spot only, no futures adapter exists)
                    "bitget",  # F39: bitget_native.py:125 (BITGET-SPOT adapter — spot leg)
                    "bybit",  # F39: bybit_native.py:138 (BYBIT-SPOT adapter — spot leg)
                    "cboe",  # 2026-07-24 containment fix — catalog_carry.py's build_carry_basis_dated()
                    # equity-index rows set spot_venue="cboe" (SPX/NDX cash legs); confirmed missing via
                    # the Side-decision 2 containment check.
                    "cme",  # 2026-07-24 containment fix — same function's commodity rows (gold: spot_venue="cme")
                    "coinbase",
                    "deribit",
                    "ibkr",
                    "ice",  # 2026-07-24 containment fix — same function's crude-oil row (spot_venue="ice")
                    "kraken",  # F39: kraken_rest_adapter.py:159 (KRAKEN-SPOT adapter — spot leg)
                    "nasdaq",  # codex category-instrument-coverage.md §5 slot ibkr-cme-qqq-nq-dated-usd-prod (QQQ)
                    "nymex",  # 2026-07-24 containment fix — same function's nat-gas row (spot_venue="nymex")
                    "nyse",  # codex category-instrument-coverage.md §5 slot ibkr-cme-spy-es-dated-usd-prod (SPY)
                    "okx",  # F39: okx_native.py:151 (OKX-SPOT adapter — spot leg)
                ),
                source_of_truth=(
                    "strategy-service CarryBasisDatedEngine (basis_dated.py, spot leader); "
                    "manifest cell CARRY_BASIS_DATED (CEFI/TRADFI, dated_future)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="future",
                role=future_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.DATED_FUTURE,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.TRADFI),
                eligible_venue_ids=("deribit", "cme", "ice", "binance"),
                source_of_truth=(
                    "strategy-service CarryBasisDatedEngine (TRADE future leg, "
                    "leg_type=FUTURE; side flips on basis sign); manifest cell CARRY_BASIS_DATED"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes=notes,
    )


def _recursive_staked_structure() -> ArchetypeLegStructure:
    """CARRY_RECURSIVE_STAKED: leveraged LST loop (STAKE->LEND->BORROW) xN atomic."""

    src = (
        "strategy-service CarryRecursiveStakedEngine._build_loop_legs "
        "(recursive_staked.py, STAKE→LEND→BORROW loop, ATOMIC_ON_CHAIN); "
        "manifest cell CARRY_RECURSIVE_STAKED (DEFI, staking)"
    )
    atomic = _atomic_constraint(
        "recursive_loop",
        "All loop iterations execute atomically on-chain (ATOMIC_ON_CHAIN composite call).",
    )
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.CARRY_RECURSIVE_STAKED,
        legs=(
            ArchetypeLegSpec(
                leg_id="loop_stake",
                role=ArchetypeLegRole.STAKE,
                required=True,
                instrument_types=(ArchetypeInstrumentType.STAKING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                # 2026-07-24 containment fix — catalog_carry.py's _RECURSIVE_STAKED_LST includes
                # "etherfi" (staking_venue="etherfi" is a real emitted row); confirmed missing via
                # the Side-decision 2 containment check.
                eligible_venue_ids=("lido", "rocketpool", "etherfi", "jito", "marinade"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
            ArchetypeLegSpec(
                leg_id="loop_collateral",
                role=ArchetypeLegRole.LEND,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                # 2026-07-24 containment fix — catalog_carry.py's _RECURSIVE_STAKED_LEND includes
                # "compound" (lending_venue="compound" is a real emitted row, aliased to
                # "compound_v3" — same convention as "aave"/"aave_v3"); confirmed missing via the
                # Side-decision 2 containment check.
                eligible_venue_ids=("aave_v3", "compound_v3", "kamino"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
            ArchetypeLegSpec(
                leg_id="loop_borrow",
                role=ArchetypeLegRole.BORROW,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "compound_v3", "kamino"),  # 2026-07-24: see loop_collateral above
                signal_variants=("effective_ltv", "target_leverage"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="Up to 10 loop iterations (recursive_staked.py max_loops); LTV-gated leverage.",
    )


def _recursive_borrow_lending_only_structure() -> ArchetypeLegStructure:
    """CARRY_RECURSIVE_BORROW_LENDING_ONLY: pure lending-side recursion (no stake)."""

    src = (
        "strategy-service CarryRecursiveStakedEngine (recursive_staked.py, "
        "ALLOWED_ARCHETYPES includes CARRY_RECURSIVE_BORROW_LENDING_ONLY, "
        "LENDING_ONLY = LEND→BORROW loop); enums.py archetype comment"
    )
    atomic = _atomic_constraint("recursive_loop", "Lending-loop iterations execute atomically on-chain.")
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY,
        legs=(
            ArchetypeLegSpec(
                leg_id="loop_collateral",
                role=ArchetypeLegRole.LEND,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "kamino", "compound_v3", "morpho"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
            ArchetypeLegSpec(
                leg_id="loop_borrow",
                role=ArchetypeLegRole.BORROW,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "kamino", "compound_v3", "morpho"),
                signal_variants=("effective_ltv", "target_leverage"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="Family 2 recursive variant — lending-side only, no LST stake leg.",
    )


def _staking_simple_structure() -> ArchetypeLegStructure:
    """YIELD_STAKING_SIMPLE: a single stake leg, no hedge."""

    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.YIELD_STAKING_SIMPLE,
        legs=(
            ArchetypeLegSpec(
                leg_id="stake",
                role=ArchetypeLegRole.STAKE,
                required=True,
                instrument_types=(ArchetypeInstrumentType.STAKING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                # 2026-07-24 containment fix — catalog_yield_defi.py's build_yield_staking_simple()
                # has a 6th ethena/USDE row (deliberately excluded from paper-replay tick-loader
                # wiring per this issue doc's Phase 4a note, but still a REAL catalog row); confirmed
                # missing via the Side-decision 2 containment check.
                eligible_venue_ids=("lido", "rocketpool", "etherfi", "jito", "marinade", "ethena"),
                source_of_truth=(
                    "strategy-service YieldStakingSimpleEngine (staking_simple.py, "
                    "single STAKE leg); manifest cell YIELD_STAKING_SIMPLE (DEFI, staking) "
                    "note 'Pure staking, no hedge'"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="Single-leg archetype — included for leg-model completeness (the trivial structure).",
    )


def _rotation_lending_structure() -> ArchetypeLegStructure:
    """YIELD_ROTATION_LENDING: a single lend leg, rotated across venues."""

    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.YIELD_ROTATION_LENDING,
        legs=(
            ArchetypeLegSpec(
                leg_id="lend",
                role=ArchetypeLegRole.LEND,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                # 2026-07-24 containment fix — catalog_yield_defi.py's build_yield_rotation_lending()
                # cross-chain meta-rotation row sets candidate_protocols="aave,compound,morpho,spark";
                # "spark" confirmed missing via the Side-decision 2 containment check.
                eligible_venue_ids=("aave_v3", "compound_v3", "euler", "morpho", "kamino", "spark"),
                signal_variants=("apy_rotation",),
                source_of_truth=(
                    "strategy-service YieldRotationLendingEngine (rotation_lending.py, "
                    "rotate lent capital to highest-APY venue); manifest cell "
                    "YIELD_ROTATION_LENDING (DEFI, lending)"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes="Single-leg archetype; rotation across venues is a venue-switch, not a second leg.",
    )


def _price_dispersion_structure() -> ArchetypeLegStructure:
    """ARBITRAGE_PRICE_DISPERSION: a buy leg + a sell leg cross-venue."""

    src = (
        "strategy-service ArbitragePriceDispersionEngine (price_dispersion.py, "
        "BUY leader + SELL hedge AtomicLegs); manifest cell ARBITRAGE_PRICE_DISPERSION; "
        "codex/09-strategy/architecture-v2/archetypes/arbitrage-price-dispersion.md"
    )
    venues = (
        "aave_v3",  # 2026-07-24 containment fix — catalog_trading.py's build_arbitrage_price_dispersion()
        # lending-protocol-arb + cross-chain-yield-arb sub-families set candidate_venues/protocol="aave"
        # (aliased to "aave_v3" — same convention as elsewhere); confirmed missing via the Side-decision 2
        # containment check (defi_archetype_universe_no_curtailment_mechanism_2026_07_23.md).
        "aerodrome_v3",  # 2026-07-24 containment fix — same function's DEX cross-venue spot-dispersion
        # sub-family (_dex_dispersion_pairs) sets candidate_venues csv including AERODROME_V3.
        "balancer",
        "betfair",  # 2026-07-24 containment fix — same function's sports-cross-book row sets
        # venues="unity,betfair,matchbook" (bare "betfair", distinct from "betfair_direct" already below —
        # both are real, separately-registered ids per venue_tokens.py's own family-vs-routing-target split).
        "betfair_direct",
        "binance",
        "bitget",  # F39: bitget_native.py:125 (BITGET-FUTURES/SPOT adapter)
        "bybit",
        "camelot_v3",  # 2026-07-24 containment fix — _dex_dispersion_pairs (see aerodrome_v3 above)
        "cme",  # 2026-07-24 containment fix — same function's cross-venue dated-futures-arb sub-family
        # sets candidate_venues="cme,deribit" (CME micro vs Deribit dated, same expiry).
        "coinbase",  # F39: coinbase_ccxt.py:32 (COINBASE-SPOT adapter)
        "compound_v3",  # 2026-07-24 containment fix (see aave_v3 comment above; catalog "compound" aliased)
        "curve",
        "deribit",
        "hyperliquid",
        "kalshi",  # 2026-07-24 containment fix — same function's Kalshi<->Polymarket cross-venue row sets
        # arb_venues="polymarket,kalshi" (bare event-market id, distinct from the perp-product "kalshi_perp"
        # used by CARRY_BASIS_PERP/CARRY_FUNDING_DISPERSION above).
        "kraken",  # F39: kraken_rest_adapter.py:159 (KRAKEN-FUTURES/SPOT adapter)
        "matchbook",  # 2026-07-24 containment fix (see betfair comment above)
        "morpho",  # 2026-07-24 containment fix (see aave_v3 comment above; catalog emits literal "morpho")
        "okx",
        "orca",  # 2026-07-24 containment fix — _dex_dispersion_pairs (see aerodrome_v3 above)
        "pancakeswap_v3",  # 2026-07-24 containment fix — _dex_dispersion_pairs (see aerodrome_v3 above)
        "phoenix",  # 2026-07-24 containment fix — _dex_dispersion_pairs (see aerodrome_v3 above); NOTE
        # instruments-service's phoenix.py adapter is registered but its upstream is measurably dead
        # (venue_adapter_keys.py DEFI_VENUE_PHASE="pipeline") — cited here as a real catalog-declared
        # candidate_venue regardless of current data-availability (a separate, orthogonal question from
        # leg-eligibility citation).
        "polymarket",
        "raydium",  # 2026-07-24 containment fix — _dex_dispersion_pairs (see aerodrome_v3 above)
        "smarkets_direct",
        "sushiswap_v3",  # 2026-07-24 containment fix — _dex_dispersion_pairs (see aerodrome_v3 above)
        "uniswap_v3",
        "unity",
    )
    groups = (
        VenueCategoryV2.CEFI,
        VenueCategoryV2.DEFI,
        VenueCategoryV2.SPORTS,
        VenueCategoryV2.PREDICTION,
        VenueCategoryV2.TRADFI,
    )
    atomic = _atomic_constraint(
        "dispersion_pair",
        (
            "Same-chain pairs execute ATOMIC (multicall / flash-loan); cross-venue "
            "non-atomic pairs run LEADER_HEDGE with abort-on-adverse-move."
        ),
    )
    instr = (ArchetypeInstrumentType.SPOT, ArchetypeInstrumentType.PERP, ArchetypeInstrumentType.EVENT_SETTLED)
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
        legs=(
            ArchetypeLegSpec(
                leg_id="buy",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("dispersion_bps",),
                constraints=(atomic,),
                source_of_truth=f"{src} (cheaper venue = BUY leader)",
            ),
            ArchetypeLegSpec(
                leg_id="sell",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("dispersion_bps",),
                constraints=(atomic,),
                source_of_truth=f"{src} (richer venue = SELL hedge)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC,
        notes="2-leg paired cross-venue arb; same instrument (or equivalent) on two venues.",
    )


def _sports_dutching_structure() -> ArchetypeLegStructure:
    """ARBITRAGE_SPORTS_DUTCHING: N-venue dutched arb on a complete odds outcome set."""

    src = (
        "strategy-service SportsArbDutchingEngine (arbitrage_structural/sports_arb_dutching.py, "
        "dutched stake per outcome proportional to 1/best_odds, gated on "
        "min_overround_savings_pct); manifest cell ARBITRAGE_SPORTS_DUTCHING"
    )
    venues = ("betfair", "matchbook", "unity", "smarkets_direct", "betfair_direct")
    groups = (VenueCategoryV2.SPORTS,)
    instr = (ArchetypeInstrumentType.EVENT_SETTLED,)
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.ARBITRAGE_SPORTS_DUTCHING,
        legs=(
            ArchetypeLegSpec(
                leg_id="outcome_a",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("decimal_odds",),
                source_of_truth=f"{src} (back leg for outcome A of a >=2-way complete set)",
            ),
            ArchetypeLegSpec(
                leg_id="outcome_b",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("decimal_odds",),
                source_of_truth=f"{src} (back leg for outcome B; a 3-way set e.g. HOME/DRAW/AWAY adds a 3rd "
                "identically-shaped leg — the engine loops `outcome_set`, this spec models the 2-way minimum)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes=(
            "N-leg dutched back-every-outcome arb (no offsetting short — every outcome is BACKED, unlike the "
            "buy/sell pair in ARBITRAGE_PRICE_DISPERSION); legs execute within hedge_deadline_ms of each other, "
            "abort-on-adverse-move if a later leg's price moves before it fills."
        ),
    )


# ---------------------------------------------------------------------------
# Arbitrage-structural + MEV + liquidation family (engined, Phase 6A backfill)
# ---------------------------------------------------------------------------


def _cross_domain_event_structure() -> ArchetypeLegStructure:
    """ARBITRAGE_CROSS_DOMAIN_EVENT: 2-leg LEADER_HEDGE across domains."""

    src = (
        "strategy-service ArbitrageCrossDomainEventEngine (arbitrage_structural/cme_polymarket.py, "
        "leader TRADE + hedge TRADE, CLOSE_LEADER_IF_HEDGE_FAILS); "
        "codex .../arbitrage-cross-domain-event.md (same real-world outcome, all event-settled)"
    )
    groups = (VenueCategoryV2.PREDICTION, VenueCategoryV2.SPORTS, VenueCategoryV2.TRADFI)
    instr = (ArchetypeInstrumentType.EVENT_SETTLED, ArchetypeInstrumentType.OPTION)
    venues = ("cme", "polymarket", "kalshi", "betfair_direct")
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.ARBITRAGE_CROSS_DOMAIN_EVENT,
        legs=(
            ArchetypeLegSpec(
                leg_id="leader",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                source_of_truth=f"{src} (leader leg, leg=0)",
            ),
            ArchetypeLegSpec(
                leg_id="hedge",
                role=ArchetypeLegRole.HEDGE_SHORT,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                source_of_truth=f"{src} (hedge leg, opposite side, same outcome)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes="2-leg cross-domain event arb; both legs settle on the same real-world outcome.",
    )


def _mev_single_swap_structure(
    archetype: StrategyArchetype, *, mev_step: str, role: ArchetypeLegRole, notes: str, engine_file: str
) -> ArchetypeLegStructure:
    """Single-leg ATOMIC on-chain MEV swap (backrun / JIT-liquidity)."""

    src = (
        f"strategy-service {archetype.value} engine (mev/{engine_file}, single SWAP AtomicLeg "
        f"params mev_step={mev_step}, ATOMIC); codex .../{archetype.value.lower().replace('_', '-')}.md"
    )
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id=mev_step,
                role=role,
                required=True,
                instrument_types=(
                    (ArchetypeInstrumentType.SPOT,)
                    if role == ArchetypeLegRole.SPOT_LONG
                    else (ArchetypeInstrumentType.LP,)
                ),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_DEX_SWAP_VENUES,
                constraints=(_atomic_constraint(mev_step, "Single-tx atomic on-chain MEV step (revert-all)."),),
                source_of_truth=src,
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC,
        notes=notes,
    )


def _mev_liquidation_bundle_structure() -> ArchetypeLegStructure:
    """ARBITRAGE_MEV_LIQUIDATION_BUNDLE: 3-leg ATOMIC flash-loan bundle."""

    src = (
        "strategy-service ArbitrageMevLiquidationBundleEngine (mev/liquidation_bundle.py, "
        "BORROW + TRADE + SWAP AtomicLegs, ATOMIC); codex .../arbitrage-mev-liquidation-bundle.md"
    )
    atomic = _atomic_constraint("liquidation_bundle", "Flash-loan bundle reverts all-or-nothing within one tx.")
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.ARBITRAGE_MEV_LIQUIDATION_BUNDLE,
        legs=(
            ArchetypeLegSpec(
                leg_id="flash_borrow",
                role=ArchetypeLegRole.BORROW,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_LENDING_PROTOCOLS,
                constraints=(atomic,),
                source_of_truth=f"{src} (flash-loan borrow leg)",
            ),
            ArchetypeLegSpec(
                leg_id="liquidation_call",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_LENDING_PROTOCOLS,
                constraints=(atomic,),
                source_of_truth=f"{src} (liquidationCall, seize collateral + bonus)",
            ),
            ArchetypeLegSpec(
                leg_id="swap_repay",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_DEX_SWAP_VENUES,
                constraints=(atomic,),
                source_of_truth=f"{src} (swap collateral → debt asset, repay flash loan)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC,
        notes="Zero-capital flash-loan liquidation (extends LIQUIDATION_CAPTURE).",
    )


def _liquidation_capture_structure() -> ArchetypeLegStructure:
    """LIQUIDATION_CAPTURE: 5-leg ATOMIC_ON_CHAIN flash-loan + multicall."""

    src = (
        "strategy-service LiquidationCaptureEngine (arbitrage_structural/liquidation_capture.py, "
        "BORROW+TRADE+TRADE+SWAP+TRADE AtomicLegs, ATOMIC_ON_CHAIN, HOLD_LEG_AND_ALERT); "
        "manifest cell LIQUIDATION_CAPTURE (DEFI lending SUPPORTED); codex .../liquidation-capture.md"
    )
    atomic = _atomic_constraint(
        "liquidation_capture", "Monitor→flash-borrow→liquidationCall→swap→repay all in one on-chain tx."
    )
    lending = (ArchetypeInstrumentType.LENDING,)
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.LIQUIDATION_CAPTURE,
        legs=(
            ArchetypeLegSpec(
                leg_id="flash_borrow",
                role=ArchetypeLegRole.BORROW,
                required=True,
                instrument_types=lending,
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "compound_v3", "euler", "morpho", "kamino"),
                constraints=(atomic,),
                source_of_truth=f"{src} (flash borrow debt asset)",
            ),
            ArchetypeLegSpec(
                leg_id="repay_debt",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=lending,
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "compound_v3", "euler", "morpho", "kamino"),
                constraints=(atomic,),
                source_of_truth=f"{src} (repay underwater debt)",
            ),
            ArchetypeLegSpec(
                leg_id="seize_collateral",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=lending,
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "compound_v3", "euler", "morpho", "kamino"),
                constraints=(atomic,),
                source_of_truth=f"{src} (seize collateral + liquidation bonus)",
            ),
            ArchetypeLegSpec(
                leg_id="swap_collateral",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_DEX_SWAP_VENUES,
                constraints=(atomic,),
                source_of_truth=f"{src} (swap collateral → repayment asset)",
            ),
            ArchetypeLegSpec(
                leg_id="repay_flash",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=lending,
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "compound_v3", "euler", "morpho", "kamino"),
                constraints=(atomic,),
                source_of_truth=f"{src} (repay flash loan)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="5-leg atomic on-chain liquidation capture (CeFi perp variant adds a bid-ladder leg per cell).",
    )


# ---------------------------------------------------------------------------
# DeFi LP family (engined: single-leg mint/burn ATOMIC)
# ---------------------------------------------------------------------------


def _defi_lp_structure(
    archetype: StrategyArchetype, *, operation: str, venues: tuple[str, ...], engine_file: str, notes: str
) -> ArchetypeLegStructure:
    """Single-leg ATOMIC DeFi LP position (concentrated / pool / vault)."""

    src = (
        f"strategy-service {archetype.value} engine (defi_lp/{engine_file}, single SWAP AtomicLeg "
        f"lp_operation={operation}, ATOMIC); codex .../{archetype.value.lower().replace('_', '-')}.md"
    )
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="lp",
                role=ArchetypeLegRole.LP_PROVIDE,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LP,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=venues,
                constraints=(_atomic_constraint(operation, f"{operation}/withdraw executes atomically on-chain."),),
                source_of_truth=src,
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Directional + ML + rules + event-driven (single-instrument, 0 explicit legs →
# modelled as ONE directional leg; sourced from the TradeInstruction engines)
# ---------------------------------------------------------------------------


def _single_directional_structure(
    archetype: StrategyArchetype,
    *,
    role: ArchetypeLegRole,
    instrument_types: tuple[ArchetypeInstrumentType, ...],
    asset_groups: tuple[VenueCategoryV2, ...],
    venues: tuple[str, ...],
    engine_desc: str,
    notes: str,
    leg_id: str = "directional",
) -> ArchetypeLegStructure:
    """One directional leg (TradeInstruction engines: ML / rules / event-driven)."""

    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id=leg_id,
                role=role,
                required=True,
                instrument_types=instrument_types,
                asset_groups=asset_groups,
                eligible_venue_ids=venues,
                source_of_truth=engine_desc,
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Market-making family (quote leg; 0 explicit legs → ONE quote leg)
# ---------------------------------------------------------------------------


def _market_making_structure(
    archetype: StrategyArchetype,
    *,
    instrument_types: tuple[ArchetypeInstrumentType, ...],
    asset_groups: tuple[VenueCategoryV2, ...],
    venues: tuple[str, ...],
    source: str,
    notes: str,
    lp: bool = False,
) -> ArchetypeLegStructure:
    """A two-sided quote leg (CLOB MM) or LP-provide leg (AMM MM)."""

    role = ArchetypeLegRole.LP_PROVIDE if lp else ArchetypeLegRole.SPOT_LONG
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="quote",
                role=role,
                required=True,
                instrument_types=instrument_types,
                asset_groups=asset_groups,
                eligible_venue_ids=venues,
                signal_variants=("half_spread_bps", "inventory_skew"),
                source_of_truth=source,
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Stat-arb family (2-leg long/short)
# ---------------------------------------------------------------------------


def _stat_arb_pairs_structure() -> ArchetypeLegStructure:
    """STAT_ARB_PAIRS_FIXED: 2-leg LEADER_HEDGE long + short pair."""

    src = (
        "strategy-service StatArbPairsFixedEngine (stat_arb_pairs/pairs_fixed.py, "
        "leader TRADE + hedge TRADE, LEADER_HEDGE, CLOSE_LEADER_IF_HEDGE_FAILS, "
        "COINTEGRATION_BREAKDOWN kill); manifest cell STAT_ARB_PAIRS_FIXED"
    )
    groups = (VenueCategoryV2.CEFI, VenueCategoryV2.DEFI, VenueCategoryV2.TRADFI)
    instr = (ArchetypeInstrumentType.SPOT, ArchetypeInstrumentType.PERP)
    # nasdaq/nyse: codex .../stat-arb-pairs-fixed.md sector-pair slot labels ibkr-goog-meta/
    # ibkr-aapl-msft (NASDAQ), ibkr-xom-cvx/ibkr-jpm-bac (NYSE) — equities are spot-only so the
    # combined SPOT+PERP `instr` above doesn't misclaim a PERP capability for either exchange.
    venues = ("binance", "okx", "bybit", "hyperliquid", "ibkr", "cme", "nasdaq", "nyse")
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.STAT_ARB_PAIRS_FIXED,
        legs=(
            ArchetypeLegSpec(
                leg_id="long",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("spread_zscore",),
                source_of_truth=f"{src} (leader = long underperformer when z<0)",
            ),
            ArchetypeLegSpec(
                leg_id="short",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("spread_zscore",),
                source_of_truth=f"{src} (hedge = short outperformer)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes="Cointegrated pair: long underperformer + short outperformer; exit on z-flip.",
    )


def _stat_arb_cross_sectional_structure() -> ArchetypeLegStructure:
    """STAT_ARB_CROSS_SECTIONAL: long-basket + short-basket (2M legs)."""

    src = (
        "strategy-service StatArbCrossSectionalEngine (stat_arb_pairs/cross_sectional.py, "
        "long top-M + short bottom-M basket TRADEs, SEQUENCED_WITH_PACING); "
        "manifest cell STAT_ARB_CROSS_SECTIONAL"
    )
    groups = (VenueCategoryV2.CEFI, VenueCategoryV2.DEFI, VenueCategoryV2.TRADFI)
    instr = (ArchetypeInstrumentType.SPOT, ArchetypeInstrumentType.PERP)
    # nasdaq/nyse: codex .../stat-arb-cross-sectional.md slot labels ibkr-sp500-momentum /
    # ibkr-sp500-sector-rotation / ibkr-russell2000-mr — S&P 500 + Russell 2000 baskets span
    # both exchanges; equities are spot-only so the combined SPOT+PERP `instr` above doesn't
    # misclaim a PERP capability for either exchange.
    venues = ("binance", "hyperliquid", "bybit", "ibkr", "nasdaq", "nyse")
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.STAT_ARB_CROSS_SECTIONAL,
        legs=(
            ArchetypeLegSpec(
                leg_id="long_basket",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("cross_sectional_score", "rank_weight"),
                source_of_truth=f"{src} (top-M universe members by score)",
            ),
            ArchetypeLegSpec(
                leg_id="short_basket",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=instr,
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("cross_sectional_score", "rank_weight"),
                source_of_truth=f"{src} (bottom-M universe members by score)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes="Dynamic 2M-leg basket (long top-M / short bottom-M); rank- or equal-weighted.",
    )


# ---------------------------------------------------------------------------
# Vol-trading family — options structures (sourced from codex docs + cells)
# ---------------------------------------------------------------------------


def _vol_options_structure(
    archetype: StrategyArchetype,
    *,
    legs: tuple[tuple[str, ArchetypeLegRole, bool, str], ...],
    venues: tuple[str, ...],
    coupling: AtomicExecutionMode,
    notes: str,
    cross_asset: bool = False,
    with_hedge: bool = True,
) -> ArchetypeLegStructure:
    """Build a vol-trading options structure from a (leg_id, role, required, note) spec.

    ``legs`` are the option legs; a delta-hedge perp/future leg is appended when
    ``with_hedge`` (most vol archetypes are delta-hedged via the underlying).
    Sourced from the codex archetype doc + ARCHETYPE_CAPABILITY_REGISTRY cell.
    """

    kebab = archetype.value.lower().replace("_", "-")
    src = f"codex .../{kebab}.md (option structure) + manifest cell {archetype.value} (CEFI option)"
    groups = (VenueCategoryV2.CEFI, VenueCategoryV2.TRADFI) if "cboe" in venues else (VenueCategoryV2.CEFI,)
    built: list[ArchetypeLegSpec] = []
    for leg_id, role, required, note in legs:
        built.append(
            ArchetypeLegSpec(
                leg_id=leg_id,
                role=role,
                required=required,
                instrument_types=(ArchetypeInstrumentType.OPTION,),
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("implied_vol", "realised_vol"),
                source_of_truth=f"{src} — {note}",
            )
        )
    if with_hedge:
        built.append(
            ArchetypeLegSpec(
                leg_id="delta_hedge",
                role=ArchetypeLegRole.HEDGE_SHORT,
                required=False,
                instrument_types=(ArchetypeInstrumentType.PERP, ArchetypeInstrumentType.DATED_FUTURE),
                asset_groups=(VenueCategoryV2.CEFI,),
                eligible_venue_ids=("deribit", "binance", "okx", "hyperliquid"),
                signal_variants=("dynamic_hedge_ratio",),
                source_of_truth=f"{src} — continuous delta hedge via underlying perp/future",
            )
        )
    return ArchetypeLegStructure(archetype_id=archetype, legs=tuple(built), execution_coupling=coupling, notes=notes)


def _not_registered_structure(archetype: StrategyArchetype, reason: str) -> ArchetypeLegStructure:
    """An explicit ``not_registered`` structure (legs=() + cited reason)."""

    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        not_registered=True,
        not_registered_reason=reason,
    )


# ---------------------------------------------------------------------------
# Per-family seed lists (assembled in build_all_structures)
# ---------------------------------------------------------------------------


def _carry_yield_seeds() -> tuple[ArchetypeLegStructure, ...]:
    return (
        _staked_basis_structure(
            StrategyArchetype.CARRY_STAKED_BASIS,
            hedge_role=ArchetypeLegRole.HEDGE_SHORT,
            hedge_instrument=ArchetypeInstrumentType.PERP,
            notes=(
                "3-leg structure (spot_long + stake + lend) + perp hedge_short. "
                "Conditional: LST accepted as perp collateral on the hedge venue → "
                "staked basis; not accepted → straight_basis fallback (stake leg dropped)."
            ),
        ),
        _staked_basis_structure(
            StrategyArchetype.CARRY_STAKED_BASIS_DATED,
            hedge_role=ArchetypeLegRole.FUTURE_SHORT,
            hedge_instrument=ArchetypeInstrumentType.DATED_FUTURE,
            notes=(
                "Dated-hedge variant of CARRY_STAKED_BASIS — hedge leg is a Deribit "
                "dated ETH future (manifest cell CARRY_STAKED_BASIS_DATED; "
                "catalog_staked_basis dated slots). Same collateral conditional."
            ),
        ),
        _basis_perp_structure(
            StrategyArchetype.CARRY_BASIS_PERP,
            inverse=False,
            notes="Spot + perp delta-neutral basis (short the basis when funding > 0).",
        ),
        _basis_perp_structure(
            StrategyArchetype.CARRY_BASIS_PERP_INV,
            inverse=True,
            notes="Inverse basis-perp: lend/USDC-margined perp + hold spot (enums.py comment).",
        ),
        _funding_dispersion_structure(),
        _basis_dated_structure(
            StrategyArchetype.CARRY_BASIS_DATED,
            inverse=False,
            notes="Spot + dated-future cash-and-carry (contango: long spot, short future).",
        ),
        _basis_dated_structure(
            StrategyArchetype.CARRY_BASIS_DATED_INV,
            inverse=True,
            notes="Inverse dated basis (backwardation: short spot, long future).",
        ),
        _recursive_staked_structure(),
        _recursive_borrow_lending_only_structure(),
        _staking_simple_structure(),
        _rotation_lending_structure(),
    )


def _arbitrage_seeds() -> tuple[ArchetypeLegStructure, ...]:
    return (
        _price_dispersion_structure(),
        _sports_dutching_structure(),
        _cross_domain_event_structure(),
        _mev_single_swap_structure(
            StrategyArchetype.ARBITRAGE_MEV_BACKRUN,
            mev_step="backrun_arb",
            role=ArchetypeLegRole.SPOT_LONG,
            notes="Single-tx DEX-DEX/DEX-CEX spot arb after a confirmed large swap.",
            engine_file="backrun.py",
        ),
        _mev_single_swap_structure(
            StrategyArchetype.ARBITRAGE_MEV_JIT_LIQUIDITY,
            mev_step="jit_mint",
            role=ArchetypeLegRole.LP_PROVIDE,
            notes="2-block JIT concentrated-LP mint→collect-fees→burn around a pending swap.",
            engine_file="jit_liquidity.py",
        ),
        _mev_liquidation_bundle_structure(),
        _liquidation_capture_structure(),
        _not_registered_structure(
            StrategyArchetype.ARBITRAGE_MEV_SANDWICH,
            (
                "No leg structure: ARBITRAGE_MEV_SANDWICH is a theoretical-only tracer "
                "(strategy-service mev/sandwich_theoretical.py — SandwichTheoreticalProfit, "
                "NOT a BaseArchetypeEngineV2, intentionally absent from ARCHETYPE_ENGINE_REGISTRY "
                "pending mempool data; Bloxroute feed removed). codex "
                ".../arbitrage-mev-sandwich.md status=theoretical-only."
            ),
        ),
    )


def _defi_lp_seeds() -> tuple[ArchetypeLegStructure, ...]:
    return (
        _defi_lp_structure(
            StrategyArchetype.DEFI_LP_CONCENTRATED,
            operation="mint",
            venues=("uniswap_v3", "pancakeswap_v3", "sushiswap_v3", "trader_joe"),
            engine_file="concentrated.py",
            notes="Concentrated-liquidity AMM position (mint/burn around price range; rebalance on drift).",
        ),
        _defi_lp_structure(
            StrategyArchetype.DEFI_LP_POOL,
            operation="deposit",
            venues=("curve", "balancer_v2", "balancer_v3"),
            engine_file="pool.py",
            notes="Full-range pool deposit/withdraw (Curve stableswap / Balancer weighted); exit on depeg.",
        ),
        _defi_lp_structure(
            StrategyArchetype.DEFI_LP_VAULT,
            operation="vault_deposit",
            # 2026-07-24 containment fix — catalog_yield_defi.py's build_defi_lp_vault() has real
            # ethena/sUSDe + maker/sDAI rows (venue="ETHENA"/"MAKER"); confirmed missing via the
            # Side-decision 2 containment check (defi_archetype_universe_no_curtailment_mechanism_
            # 2026_07_23.md). "morpho"/"sommelier" are kept even though the catalog doesn't emit them
            # yet — a legitimately-broader UAC citation (codex-documented, not-yet-live venues; the
            # containment direction is catalog ⊆ UAC, not equality).
            venues=("yearn_v3", "morpho", "sommelier", "ethena", "maker"),
            engine_file="vault.py",
            notes="ERC-4626 vault deposit/redeem; exit on APY-below-floor or drawdown breach.",
        ),
    )


def _directional_seeds() -> tuple[ArchetypeLegStructure, ...]:
    cefi_defi_tradfi = (VenueCategoryV2.CEFI, VenueCategoryV2.DEFI, VenueCategoryV2.TRADFI)
    continuous_instr = (ArchetypeInstrumentType.SPOT, ArchetypeInstrumentType.PERP)
    # Shared by 3 archetypes below (ML/RULES_DIRECTIONAL_CONTINUOUS + TSMOM_BTC_CTA) — do NOT
    # add fx/nasdaq/nyse here, TSMOM_BTC_CTA's own codex doc states "BTC-only CeFi archetype by
    # design", so a TradFi-equity/FX addition to this shared tuple would leak into it.
    continuous_venues = ("binance", "okx", "bybit", "hyperliquid", "ibkr", "cme")
    # ML/RULES_DIRECTIONAL_CONTINUOUS-only extension: codex ml-directional-continuous.md /
    # rules-directional-continuous.md example instances ibkr-spy-1m-usd-prod (NYSE),
    # ibkr-aapl-daily-usd-prod / ibkr-qqq-15m-breakout (NASDAQ), ibkr-eurusd-fx-15m-usd-prod /
    # ibkr-eurusd-5m-usd-prod (FX).
    continuous_tradfi_venues = (*continuous_venues, "fx", "nasdaq", "nyse")
    event_venues = ("unity", "betfair_direct", "smarkets_direct", "polymarket")
    event_groups = (VenueCategoryV2.SPORTS, VenueCategoryV2.PREDICTION)
    return (
        _single_directional_structure(
            StrategyArchetype.EVENT_DRIVEN,
            role=ArchetypeLegRole.SPOT_LONG,
            instrument_types=(
                ArchetypeInstrumentType.SPOT,
                ArchetypeInstrumentType.PERP,
                ArchetypeInstrumentType.OPTION,
            ),
            asset_groups=cefi_defi_tradfi,
            # fx: codex event-driven.md example instance ibkr-eurusd-macro-usd-prod (Macro US
            # events). nasdaq: coverage.md §15 slot labels ibkr-aapl-earnings-usd-prod /
            # -msft-earnings- / -nvda-earnings- (all NASDAQ-listed). No NYSE-specific ticker
            # example found in either doc — not added, would be inventing.
            venues=("binance", "okx", "hyperliquid", "deribit", "ibkr", "cme", "fx", "nasdaq"),
            engine_desc=(
                "strategy-service EventDrivenEngine (event_driven/event_driven.py, TradeInstruction "
                "directional LONG/SHORT on event surprise, time-boxed FLAT exit); manifest cell EVENT_DRIVEN"
            ),
            notes="Pre-position + directional trade at event release; time-bounded ONE_SHOT.",
        ),
        _single_directional_structure(
            StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
            role=ArchetypeLegRole.SPOT_LONG,
            instrument_types=continuous_instr,
            asset_groups=cefi_defi_tradfi,
            venues=continuous_tradfi_venues,
            engine_desc=(
                "strategy-service MLDirectionalContinuousEngine (ml_directional/continuous.py, "
                "TradeInstruction LONG/SHORT from ML class, Kelly-sized); manifest cell ML_DIRECTIONAL_CONTINUOUS"
            ),
            notes="1-leg directional from ML prediction; long or short.",
        ),
        _single_directional_structure(
            StrategyArchetype.ML_DIRECTIONAL_EVENT_SETTLED,
            role=ArchetypeLegRole.SPOT_LONG,
            instrument_types=(ArchetypeInstrumentType.EVENT_SETTLED,),
            asset_groups=event_groups,
            venues=event_venues,
            engine_desc=(
                "strategy-service MLDirectionalEventSettledEngine (ml_directional/event_settled.py, "
                "TradeInstruction always-LONG value bet, fractional-Kelly); manifest cell ML_DIRECTIONAL_EVENT_SETTLED"
            ),
            notes="1-leg always-LONG value bet on event outcome (one-sided).",
        ),
        _single_directional_structure(
            StrategyArchetype.RULES_DIRECTIONAL_CONTINUOUS,
            role=ArchetypeLegRole.SPOT_LONG,
            instrument_types=continuous_instr,
            asset_groups=cefi_defi_tradfi,
            venues=continuous_tradfi_venues,
            engine_desc=(
                "strategy-service RulesDirectionalContinuousEngine (rules_directional/continuous.py, "
                "TradeInstruction signed LONG/SHORT on rule fire); manifest cell RULES_DIRECTIONAL_CONTINUOUS"
            ),
            notes="1-leg directional when a feature-threshold rule fires; long or short.",
        ),
        _single_directional_structure(
            StrategyArchetype.RULES_DIRECTIONAL_EVENT_SETTLED,
            role=ArchetypeLegRole.SPOT_LONG,
            instrument_types=(ArchetypeInstrumentType.EVENT_SETTLED,),
            asset_groups=event_groups,
            venues=event_venues,
            engine_desc=(
                "strategy-service RulesDirectionalEventSettledEngine (rules_directional/event_settled.py, "
                "TradeInstruction always-LONG per fired rule); manifest cell RULES_DIRECTIONAL_EVENT_SETTLED"
            ),
            notes="1-leg always-LONG bet per fired rule (one-sided).",
        ),
        _single_directional_structure(
            StrategyArchetype.TSMOM_BTC_CTA,
            role=ArchetypeLegRole.PERP_LONG,
            instrument_types=(ArchetypeInstrumentType.PERP,),
            asset_groups=cefi_defi_tradfi,
            venues=continuous_venues,
            engine_desc=(
                "strategy-service TsmomBtcCtaEngine (rules_directional/tsmom_btc_cta.py, "
                "TradeInstruction LONG/SHORT from the mean SIGN of trailing returns "
                "x inverse-vol scaling); plans/active/"
                "citadel_paper_batch_live_reconciliation_2026_06_19.md P2.11.14"
            ),
            notes="1-leg BTC trend-following (CTA) perp; long-or-short, vol-target-scaled.",
        ),
    )


def _market_making_seeds() -> tuple[ArchetypeLegStructure, ...]:
    clob_instr = (ArchetypeInstrumentType.SPOT, ArchetypeInstrumentType.PERP)
    clob_groups = (VenueCategoryV2.CEFI,)

    def _mm_clob(archetype: StrategyArchetype, design_note: str) -> ArchetypeLegStructure:
        kebab = archetype.value.lower().replace("_", "-")
        return _market_making_structure(
            archetype,
            instrument_types=clob_instr,
            asset_groups=clob_groups,
            venues=_CEFI_CLOB_VENUES,
            source=f"codex .../{kebab}.md ({design_note}); 2-sided CLOB quote leg",
            notes=f"2-sided CLOB market-making — {design_note}.",
        )

    return (
        _market_making_structure(
            StrategyArchetype.MARKET_MAKING_CONTINUOUS,
            instrument_types=(ArchetypeInstrumentType.SPOT, ArchetypeInstrumentType.PERP, ArchetypeInstrumentType.LP),
            asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
            venues=("binance", "okx", "bybit", "hyperliquid", "deribit", "uniswap_v3", "uniswap_v4", "curve"),
            source=(
                "strategy-service MarketMakingContinuousEngine (market_making/continuous.py, "
                "QuoteInstruction, mm_inventory LeveragedLeg, target_net_delta=0); "
                "manifest cell MARKET_MAKING_CONTINUOUS"
            ),
            notes="2-sided quotes (CLOB) or mint/burn (AMM LP); inventory-skewed, kill-switch armed.",
        ),
        _market_making_structure(
            StrategyArchetype.MARKET_MAKING_EVENT_SETTLED,
            instrument_types=(ArchetypeInstrumentType.EVENT_SETTLED,),
            asset_groups=(VenueCategoryV2.SPORTS, VenueCategoryV2.PREDICTION),
            venues=("betfair_direct", "smarkets_direct", "matchbook_direct", "polymarket"),
            source=(
                "strategy-service MarketMakingEventSettledEngine (market_making/event_settled.py, "
                "2x QuoteInstruction BET_BACK+BET_LAY, CancelInstruction on refresh); "
                "manifest cell MARKET_MAKING_EVENT_SETTLED"
            ),
            notes="Back+lay quotes around theo price on sports/prediction exchanges.",
        ),
        _mm_clob(StrategyArchetype.MARKET_MAKING_INVENTORY_SKEW, "Avellaneda-Stoikov reservation-price inventory skew"),
        _mm_clob(StrategyArchetype.MARKET_MAKING_ML_LEAN, "ML short-term direction tilt + inventory skew"),
        _mm_clob(StrategyArchetype.MARKET_MAKING_PASSIVE_SPREAD, "passive bid+ask at mid±half_spread, repost on fill"),
        _mm_clob(StrategyArchetype.MARKET_MAKING_QUEUE_MICROSTRUCTURE, "explicit queue-position / VPIN-toxicity model"),
        _market_making_structure(
            StrategyArchetype.MARKET_MAKING_PREDICTION,
            instrument_types=(ArchetypeInstrumentType.EVENT_SETTLED,),
            asset_groups=(VenueCategoryV2.PREDICTION,),
            venues=_PREDICTION_VENUES,
            source="codex .../market-making-prediction.md (2-sided YES/NO binary CLOB quotes)",
            notes="2-sided YES/NO binary quotes on prediction markets.",
        ),
    )


def _stat_arb_seeds() -> tuple[ArchetypeLegStructure, ...]:
    return (_stat_arb_pairs_structure(), _stat_arb_cross_sectional_structure())


def _vol_seeds() -> tuple[ArchetypeLegStructure, ...]:
    """Vol-trading family — option structures from codex docs + cells.

    The straddle/strangle/spread legs are transcribed from each archetype's codex
    doc structural description; all are delta-hedged via the underlying (the
    optional ``delta_hedge`` leg).
    """

    straddle = (
        ("call", ArchetypeLegRole.SPOT_LONG, True, "ATM call leg"),
        ("put", ArchetypeLegRole.SPOT_LONG, True, "ATM put leg"),
    )
    calendar = (
        ("front", ArchetypeLegRole.SPOT_SHORT, True, "front-month tenor leg"),
        ("back", ArchetypeLegRole.SPOT_LONG, True, "back-month tenor leg"),
    )
    seeds: list[ArchetypeLegStructure] = [
        # VOL_TRADING_OPTIONS is engined (VolTradingOptionsEngine, ATOMIC call+put).
        _vol_options_structure(
            StrategyArchetype.VOL_TRADING_OPTIONS,
            legs=straddle,
            venues=_OPTIONS_VENUES_WITH_CBOE,
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Delta-hedged ATM straddle (short-vol if IV>>RV, long-vol if IV<<RV); VolTradingOptionsEngine.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_STRADDLE,
            legs=straddle,
            venues=_OPTIONS_VENUES_WITH_CBOE,
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Long/short ATM straddle; long = gamma-scalped, short = theta harvest.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_0DTE_GAMMA_SCALPING,
            legs=straddle,
            venues=("deribit",),
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Same-day-expiry long straddle delta-hedged intraday (gamma scalp).",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_ARB_RV_IV,
            legs=(("vol_position", ArchetypeLegRole.SPOT_LONG, True, "long/short straddle on IV-RV divergence"),),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.LEADER_HEDGE,
            notes="Options vol position + delta hedge; long vol when IV<<RV, short when IV>>RV.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_CARRY,
            legs=(("short_option", ArchetypeLegRole.SPOT_SHORT, True, "short options theta harvest"),),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.LEADER_HEDGE,
            notes="Short options (1-4wk tenor) + delta hedge; harvest IV-over-RV premium.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_ML_LEAN,
            legs=(("vol_position", ArchetypeLegRole.SPOT_LONG, True, "ML RV-forecast-driven straddle direction"),),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.LEADER_HEDGE,
            notes="ML-forecast vol position + delta hedge.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_MARKET_MAKING,
            legs=(("iv_quote", ArchetypeLegRole.SPOT_LONG, True, "2-sided IV bid/ask via SVI/SSVI surface"),),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
            notes="2-sided options MM (IV quotes) + delta hedge of accumulated inventory.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_VARIANCE_SWAP,
            legs=(
                (
                    "option_strip",
                    ArchetypeLegRole.SPOT_LONG,
                    True,
                    "static strip weighted 1/K^2 (log-contract replication)",
                ),
            ),
            venues=("deribit",),
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Variance-swap replication via static option strip; continuously delta-hedged.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_LEAPS_CONVEXITY,
            legs=(("leap", ArchetypeLegRole.SPOT_LONG, True, "long far-dated (180d+) high-vega option"),),
            venues=("deribit", "cboe"),
            coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
            notes="Long LEAPS held through vol cycles; rolled quarterly.",
            with_hedge=False,
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_SYNTHETIC_DELTA,
            legs=(
                ("call", ArchetypeLegRole.SPOT_LONG, True, "long call"),
                ("put", ArchetypeLegRole.SPOT_SHORT, True, "short put (synthetic long)"),
            ),
            venues=_OPTIONS_VENUES_WITH_CBOE,
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Synthetic directional via call+put (same strike/expiry); replicates delta-1.",
            with_hedge=False,
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_RATIO_SPREAD,
            legs=(
                ("long_leg", ArchetypeLegRole.SPOT_LONG, True, "1 long ATM option"),
                ("short_legs", ArchetypeLegRole.SPOT_SHORT, True, "2+ short OTM options (1x2 ratio)"),
            ),
            venues=("deribit", "cboe"),
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Ratio spread (e.g. 1x2 call ratio); credit at entry, skew-premium signal.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_SPREAD_STRUCTURES,
            legs=calendar,
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Calendar / butterfly spreads on term structure + smile; vega-neutral at entry.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_TERM_STRUCTURE_ARB,
            legs=calendar,
            venues=("deribit", "cboe"),
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Calendar spread: buy underpriced tenor + sell overpriced tenor; dual-expiry.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_TERM_STRUCTURE_SLOPE,
            legs=calendar,
            venues=("deribit", "cboe"),
            coupling=AtomicExecutionMode.ATOMIC,
            notes="Calendar spread trading the term-structure slope parameter (Heston/SVI fit).",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_DISPERSION,
            legs=(
                ("index_straddle", ArchetypeLegRole.SPOT_SHORT, True, "short index vol straddle"),
                (
                    "component_straddles",
                    ArchetypeLegRole.SPOT_LONG,
                    True,
                    "N long component vol straddles (weighted basket)",
                ),
            ),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
            notes="Dispersion: short index vol + long basket of component vols; multiple expiries.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_CROSS_ASSET_SPREAD,
            legs=(
                ("cheap_vol", ArchetypeLegRole.SPOT_LONG, True, "long vol on cheap asset"),
                ("rich_vol", ArchetypeLegRole.SPOT_SHORT, True, "short vol on expensive asset, matched tenor"),
            ),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
            notes="Cross-asset vol spread (e.g. BTC IV vs ETH IV); both delta-hedged.",
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_OVERLAY_COVERED_CALLS,
            legs=(
                ("underlying", ArchetypeLegRole.SPOT_LONG, False, "existing delta-1 long (from parent)"),
                ("short_call", ArchetypeLegRole.SPOT_SHORT, True, "short OTM call (15-25 delta) written over it"),
            ),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
            notes="Overlay: short OTM call over an existing delta-1 long (requires parent position).",
            with_hedge=False,
        ),
        _vol_options_structure(
            StrategyArchetype.VOL_OVERLAY_PROTECTIVE_PUT,
            legs=(
                ("underlying", ArchetypeLegRole.SPOT_LONG, False, "existing delta-1 long (from parent)"),
                ("long_put", ArchetypeLegRole.SPOT_LONG, True, "long OTM put (15-30 delta) tail protection"),
            ),
            venues=_OPTIONS_VENUES,
            coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
            notes="Overlay: long OTM put protecting an existing delta-1 long (optional collar).",
            with_hedge=False,
        ),
    ]
    # VOL_0DTE_PIN_RISK is a risk-management overlay on an existing short-gamma book
    # (no standalone position legs) → not_registered with cited reason.
    seeds.append(
        _not_registered_structure(
            StrategyArchetype.VOL_0DTE_PIN_RISK,
            (
                "No standalone position legs: VOL_0DTE_PIN_RISK is a risk-management OVERLAY on an "
                "existing short-gamma options book near expiry (flattens/rolls existing positions, OI-weighted "
                "strikes) — not a position-initiating engine. No engine in ARCHETYPE_ENGINE_REGISTRY; codex "
                ".../vol-0dte-pin-risk.md describes it as a management overlay. Manages other archetypes' inventory."
            ),
        )
    )
    return tuple(seeds)


def _portfolio_seeds() -> tuple[ArchetypeLegStructure, ...]:
    """All four PORTFOLIO_* are pure meta-allocation overlays → not_registered."""

    reason = (
        "No direct instrument legs: {a} is a pure META-ALLOCATION overlay "
        "(codex .../{k}.md venue_universe=[]; allocates equity across child strategies, "
        "no venue/instrument legs). No engine in ARCHETYPE_ENGINE_REGISTRY. The leg model "
        "is for instrument-trading archetypes; allocation overlays carry no legs by design."
    )
    out: list[ArchetypeLegStructure] = []
    for a in (
        StrategyArchetype.PORTFOLIO_FACTOR_ALLOCATION,
        StrategyArchetype.PORTFOLIO_MULTI_STRATEGY,
        StrategyArchetype.PORTFOLIO_RISK_PARITY,
        StrategyArchetype.PORTFOLIO_TACTICAL_OVERLAY,
    ):
        out.append(_not_registered_structure(a, reason.format(a=a.value, k=a.value.lower().replace("_", "-"))))
    return tuple(out)


def build_all_structures() -> tuple[ArchetypeLegStructure, ...]:
    """Return a leg structure for EVERY one of the 59 archetypes (exhaustive).

    Real structures where a leg model is derivable from engine/doc/cells;
    explicit ``not_registered`` structures (legs=() + cited reason) where it is
    genuinely underivable. The caller (``_build_registry``) asserts every
    ``StrategyArchetype`` value is present exactly once.
    """

    return (
        *_carry_yield_seeds(),
        *_arbitrage_seeds(),
        *_defi_lp_seeds(),
        *_directional_seeds(),
        *_market_making_seeds(),
        *_stat_arb_seeds(),
        *_vol_seeds(),
        *_portfolio_seeds(),
    )
