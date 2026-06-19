"""Strategy Architecture v2 — StrEnums (family, archetype, axes, routing).

Split from architecture_v2.py to keep each file under the 900-line QG limit.
"""

from __future__ import annotations

from enum import StrEnum


class StrategyFamily(StrEnum):
    """9 orthogonal families — a strategy belongs to exactly one.

    v1 ``StrategyFamily`` (17 values — ``BASIS_TRADE`` / ``MOMENTUM`` / …) was
    deleted on 2026-04-21 per ``plans/active/ui_unification_v2_sanitisation_2026_04_20``.
    PORTFOLIO added 2026-04-25 (cross-category sleeves) per Phase 9 of
    ``plans/active/dart_ui_strategy_filtering_and_onboarding_2026_04_24.md``.
    """

    ML_DIRECTIONAL = "ML_DIRECTIONAL"
    RULES_DIRECTIONAL = "RULES_DIRECTIONAL"
    CARRY_AND_YIELD = "CARRY_AND_YIELD"
    ARBITRAGE_STRUCTURAL = "ARBITRAGE_STRUCTURAL"
    MARKET_MAKING = "MARKET_MAKING"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    VOL_TRADING = "VOL_TRADING"
    STAT_ARB_PAIRS = "STAT_ARB_PAIRS"
    PORTFOLIO = "PORTFOLIO"


class StrategyArchetype(StrEnum):
    """53 archetypes. No category prefixes (no CEFI_/DEFI_/SPORTS_/TRADFI_).

    v1 ``StrategyArchetype`` was deleted on 2026-04-21 per
    ``plans/active/ui_unification_v2_sanitisation_2026_04_20``.

    Phase 9 expansion 2026-04-25 — VOL family expanded from 1 to 19 archetypes
    (legacy VOL_TRADING_OPTIONS retained + RV/IV arb, spread structures, carry,
    covered calls, protective put, straddle, synthetic delta, MM, ML lean,
    0DTE gamma scalping, 0DTE pin risk, term-structure arb / slope,
    dispersion, variance swap, LEAPS convexity, cross-asset spread, ratio
    spread). MM family expanded from 2 to 10 (passive spread / inventory skew /
    ML lean / queue microstructure / prediction MM on CEFI; concentrated /
    pool / vault DeFi LP). PORTFOLIO family added as the 9th orthogonal
    family (4 cross-category archetypes). MEV archetypes added under
    ARBITRAGE_STRUCTURAL (sandwich / JIT liquidity / backrun /
    liquidation bundle). Cross-domain event arb added.

    Legacy values (`VOL_TRADING_OPTIONS`, `MARKET_MAKING_CONTINUOUS`) retained
    for back-compat with existing Firestore + GCS records; new strategies use the
    granular variants. ``MARKET_MAKING_EVENT_SETTLED`` is NOT legacy — it is the
    canonical archetype for the ``SPORTS_MM_FAMILY`` (see ``strategy_family.py``).
    ``MARKET_MAKING_CONTINUOUS`` covers CeFi continuous-quoting strategies and
    also acts as the back-compat value for old records before the granular MM
    variants (passive-spread / inventory-skew / ML-lean / queue-micro) landed.

    Capability cells (per-archetype venue/category claims) are currently in
    ``unified-api-contracts/scripts/enumerate_envelope.py``; manifest
    incorporation is a follow-up.

    ──────────────────────────────────────────────────────────────────────────
    ADDING A NEW ARCHETYPE? Update these downstream consumers (the in-repo /
    strategy-service ones FAIL LOUDLY in QG; the UI ones are a SILENT cross-repo
    gap — there is no CI that catches them from here, so they're listed first):

      UI (unified-trading-system-ui — hand-maintained mirror, NOT auto-synced;
      a UI todo under the playwright gate, NOT optional if the archetype is to be
      operator-surfaced):
        • ``lib/architecture-v2/enums.ts`` — add to the ``StrategyArchetype``
          union + ``STRATEGY_ARCHETYPES_V2`` curated list + ``ARCHETYPE_TO_FAMILY``;
          bump ``tests/unit/lib/architecture-v2/enums.test.ts`` ``toHaveLength(N)``.
        • regenerate ``lib/registry/ui-reference-data.json`` via
          ``unified-api-contracts/scripts/generate_ui_reference_data.py``.

      Same-repo (QG-enforced — these RAISE at import or fail a test, so you can't
      miss them): ``ARCHETYPE_TO_FAMILY`` (this file) + a leg-spec seed in
      ``architecture_v2/archetype_leg_spec_seeds.py`` (``ARCHETYPE_LEG_STRUCTURES``
      raises at import if missing). strategy-service: factory registry,
      ``carry_and_yield/__init__`` (etc.) export, ``archetype_defaults``
      (Kelly tier / GREENFIELD), ``target_universe`` catalog builder + registry,
      the ``test_ml_directional_continuous`` family_map.
    ──────────────────────────────────────────────────────────────────────────
    """

    ML_DIRECTIONAL_CONTINUOUS = "ML_DIRECTIONAL_CONTINUOUS"
    ML_DIRECTIONAL_EVENT_SETTLED = "ML_DIRECTIONAL_EVENT_SETTLED"
    RULES_DIRECTIONAL_CONTINUOUS = "RULES_DIRECTIONAL_CONTINUOUS"
    RULES_DIRECTIONAL_EVENT_SETTLED = "RULES_DIRECTIONAL_EVENT_SETTLED"
    CARRY_BASIS_DATED = "CARRY_BASIS_DATED"
    CARRY_BASIS_DATED_INV = "CARRY_BASIS_DATED_INV"
    CARRY_BASIS_PERP = "CARRY_BASIS_PERP"
    # CARRY_BASIS_PERP_INV: inverse of CARRY_BASIS_PERP — strategy is short the basis
    # (lend USDC-margined perp, hold spot). Renamed from CARRY_RECURSIVE_BORROW_PERP_HEDGED
    # per operator decision 2026-05-12 (strategy_archetype_taxonomy_2026_05_12.md §rename).
    CARRY_BASIS_PERP_INV = "CARRY_BASIS_PERP_INV"
    # Dollar-neutral (NOT delta-neutral) cross-sectional funding-rank REVERSION: long the
    # lowest-funding / short the highest-funding perps (different coins, same arbitraged
    # venue). Per-coin directional, aggregate dollar-neutral, residual market beta hedged
    # at the book level. Venue-dependent (Binance/Bybit/OKX/Aster); HL is momentum,
    # excluded. SSOT: plans/active/carry_staked_basis_funding_scan_experiment_2026_06_16.md.
    CARRY_FUNDING_DISPERSION = "CARRY_FUNDING_DISPERSION"
    CARRY_STAKED_BASIS = "CARRY_STAKED_BASIS"
    CARRY_STAKED_BASIS_DATED = "CARRY_STAKED_BASIS_DATED"
    CARRY_RECURSIVE_STAKED = "CARRY_RECURSIVE_STAKED"
    # Recursive-borrow variant (Family 1 per
    # plans/active/defi_recursive_borrow_archetypes_2026_05_10.md AD-1
    # flip 2026-05-10 cross-plan audit Q10 ratification). Config sibling
    # of CARRY_RECURSIVE_STAKED — pure-lending-side recursion (LENDING_ONLY).
    # Family 2 (lending loop + matched-perp-short hedge) is now CARRY_BASIS_PERP_INV
    # (renamed from CARRY_RECURSIVE_BORROW_PERP_HEDGED 2026-05-12).
    CARRY_RECURSIVE_BORROW_LENDING_ONLY = "CARRY_RECURSIVE_BORROW_LENDING_ONLY"
    YIELD_ROTATION_LENDING = "YIELD_ROTATION_LENDING"
    YIELD_STAKING_SIMPLE = "YIELD_STAKING_SIMPLE"
    ARBITRAGE_PRICE_DISPERSION = "ARBITRAGE_PRICE_DISPERSION"
    LIQUIDATION_CAPTURE = "LIQUIDATION_CAPTURE"
    # MEV (DeFi-only structural arb under ARBITRAGE_STRUCTURAL family)
    ARBITRAGE_MEV_SANDWICH = "ARBITRAGE_MEV_SANDWICH"
    ARBITRAGE_MEV_JIT_LIQUIDITY = "ARBITRAGE_MEV_JIT_LIQUIDITY"
    ARBITRAGE_MEV_BACKRUN = "ARBITRAGE_MEV_BACKRUN"
    ARBITRAGE_MEV_LIQUIDATION_BUNDLE = "ARBITRAGE_MEV_LIQUIDATION_BUNDLE"
    # Cross-domain event arb (PREDICTION x SPORTS, primary_category=CROSS_CATEGORY)
    ARBITRAGE_CROSS_DOMAIN_EVENT = "ARBITRAGE_CROSS_DOMAIN_EVENT"
    # Market making
    MARKET_MAKING_CONTINUOUS = (
        "MARKET_MAKING_CONTINUOUS"  # legacy — back-compat for old records; new CeFi MM uses granular variants
    )
    MARKET_MAKING_EVENT_SETTLED = "MARKET_MAKING_EVENT_SETTLED"
    MARKET_MAKING_PASSIVE_SPREAD = "MARKET_MAKING_PASSIVE_SPREAD"
    MARKET_MAKING_INVENTORY_SKEW = "MARKET_MAKING_INVENTORY_SKEW"
    MARKET_MAKING_ML_LEAN = "MARKET_MAKING_ML_LEAN"
    MARKET_MAKING_QUEUE_MICROSTRUCTURE = "MARKET_MAKING_QUEUE_MICROSTRUCTURE"
    MARKET_MAKING_PREDICTION = "MARKET_MAKING_PREDICTION"
    # DeFi LP variants under MARKET_MAKING family
    DEFI_LP_CONCENTRATED = "DEFI_LP_CONCENTRATED"
    DEFI_LP_POOL = "DEFI_LP_POOL"
    DEFI_LP_VAULT = "DEFI_LP_VAULT"
    # Event-driven
    EVENT_DRIVEN = "EVENT_DRIVEN"
    # VOL family — 18 archetypes (was 1)
    VOL_TRADING_OPTIONS = "VOL_TRADING_OPTIONS"  # legacy
    VOL_ARB_RV_IV = "VOL_ARB_RV_IV"
    VOL_SPREAD_STRUCTURES = "VOL_SPREAD_STRUCTURES"
    VOL_CARRY = "VOL_CARRY"
    VOL_OVERLAY_COVERED_CALLS = "VOL_OVERLAY_COVERED_CALLS"
    VOL_OVERLAY_PROTECTIVE_PUT = "VOL_OVERLAY_PROTECTIVE_PUT"
    VOL_STRADDLE = "VOL_STRADDLE"
    VOL_SYNTHETIC_DELTA = "VOL_SYNTHETIC_DELTA"
    VOL_MARKET_MAKING = "VOL_MARKET_MAKING"
    VOL_ML_LEAN = "VOL_ML_LEAN"
    VOL_0DTE_GAMMA_SCALPING = "VOL_0DTE_GAMMA_SCALPING"
    VOL_0DTE_PIN_RISK = "VOL_0DTE_PIN_RISK"
    VOL_TERM_STRUCTURE_ARB = "VOL_TERM_STRUCTURE_ARB"
    VOL_TERM_STRUCTURE_SLOPE = "VOL_TERM_STRUCTURE_SLOPE"
    VOL_DISPERSION = "VOL_DISPERSION"
    VOL_VARIANCE_SWAP = "VOL_VARIANCE_SWAP"
    VOL_LEAPS_CONVEXITY = "VOL_LEAPS_CONVEXITY"
    VOL_CROSS_ASSET_SPREAD = "VOL_CROSS_ASSET_SPREAD"
    VOL_RATIO_SPREAD = "VOL_RATIO_SPREAD"
    # Stat-arb
    STAT_ARB_PAIRS_FIXED = "STAT_ARB_PAIRS_FIXED"
    STAT_ARB_CROSS_SECTIONAL = "STAT_ARB_CROSS_SECTIONAL"
    # Portfolio (cross-category)
    PORTFOLIO_MULTI_STRATEGY = "PORTFOLIO_MULTI_STRATEGY"
    PORTFOLIO_RISK_PARITY = "PORTFOLIO_RISK_PARITY"
    PORTFOLIO_FACTOR_ALLOCATION = "PORTFOLIO_FACTOR_ALLOCATION"
    PORTFOLIO_TACTICAL_OVERLAY = "PORTFOLIO_TACTICAL_OVERLAY"


ARCHETYPE_TO_FAMILY: dict[StrategyArchetype, StrategyFamily] = {
    StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS: StrategyFamily.ML_DIRECTIONAL,
    StrategyArchetype.ML_DIRECTIONAL_EVENT_SETTLED: StrategyFamily.ML_DIRECTIONAL,
    StrategyArchetype.RULES_DIRECTIONAL_CONTINUOUS: StrategyFamily.RULES_DIRECTIONAL,
    StrategyArchetype.RULES_DIRECTIONAL_EVENT_SETTLED: StrategyFamily.RULES_DIRECTIONAL,
    StrategyArchetype.CARRY_BASIS_DATED: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_BASIS_DATED_INV: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_BASIS_PERP: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_BASIS_PERP_INV: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_FUNDING_DISPERSION: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_STAKED_BASIS: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_STAKED_BASIS_DATED: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_RECURSIVE_STAKED: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.YIELD_ROTATION_LENDING: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.YIELD_STAKING_SIMPLE: StrategyFamily.CARRY_AND_YIELD,
    StrategyArchetype.ARBITRAGE_PRICE_DISPERSION: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.LIQUIDATION_CAPTURE: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.ARBITRAGE_MEV_SANDWICH: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.ARBITRAGE_MEV_JIT_LIQUIDITY: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.ARBITRAGE_MEV_BACKRUN: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.ARBITRAGE_MEV_LIQUIDATION_BUNDLE: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.ARBITRAGE_CROSS_DOMAIN_EVENT: StrategyFamily.ARBITRAGE_STRUCTURAL,
    StrategyArchetype.MARKET_MAKING_CONTINUOUS: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.MARKET_MAKING_EVENT_SETTLED: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.MARKET_MAKING_PASSIVE_SPREAD: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.MARKET_MAKING_INVENTORY_SKEW: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.MARKET_MAKING_ML_LEAN: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.MARKET_MAKING_QUEUE_MICROSTRUCTURE: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.MARKET_MAKING_PREDICTION: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.DEFI_LP_CONCENTRATED: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.DEFI_LP_POOL: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.DEFI_LP_VAULT: StrategyFamily.MARKET_MAKING,
    StrategyArchetype.EVENT_DRIVEN: StrategyFamily.EVENT_DRIVEN,
    StrategyArchetype.VOL_TRADING_OPTIONS: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_ARB_RV_IV: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_SPREAD_STRUCTURES: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_CARRY: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_OVERLAY_COVERED_CALLS: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_OVERLAY_PROTECTIVE_PUT: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_STRADDLE: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_SYNTHETIC_DELTA: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_MARKET_MAKING: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_ML_LEAN: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_0DTE_GAMMA_SCALPING: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_0DTE_PIN_RISK: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_TERM_STRUCTURE_ARB: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_TERM_STRUCTURE_SLOPE: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_DISPERSION: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_VARIANCE_SWAP: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_LEAPS_CONVEXITY: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_CROSS_ASSET_SPREAD: StrategyFamily.VOL_TRADING,
    StrategyArchetype.VOL_RATIO_SPREAD: StrategyFamily.VOL_TRADING,
    StrategyArchetype.STAT_ARB_PAIRS_FIXED: StrategyFamily.STAT_ARB_PAIRS,
    StrategyArchetype.STAT_ARB_CROSS_SECTIONAL: StrategyFamily.STAT_ARB_PAIRS,
    StrategyArchetype.PORTFOLIO_MULTI_STRATEGY: StrategyFamily.PORTFOLIO,
    StrategyArchetype.PORTFOLIO_RISK_PARITY: StrategyFamily.PORTFOLIO,
    StrategyArchetype.PORTFOLIO_FACTOR_ALLOCATION: StrategyFamily.PORTFOLIO,
    StrategyArchetype.PORTFOLIO_TACTICAL_OVERLAY: StrategyFamily.PORTFOLIO,
}


class AllocatorArchetype(StrEnum):
    FIXED = "FIXED"
    PNL_WEIGHTED = "PNL_WEIGHTED"
    SHARPE_WEIGHTED = "SHARPE_WEIGHTED"
    RISK_PARITY = "RISK_PARITY"
    KELLY = "KELLY"
    MIN_CVAR = "MIN_CVAR"
    REGIME_AWARE = "REGIME_AWARE"
    MANUAL = "MANUAL"
    # 3-stage hierarchical (coin -> venue) ranking by realised funding rate,
    # with a configurable ``min_funding_apy_bps`` threshold (default 250 = 2.5%).
    # Stage 1: filter coins by avg funding across eligible venues > threshold.
    # Stage 2: weight surviving coins by avg funding.
    # Stage 3: weight venues per coin by per-venue funding > threshold.
    # Below threshold = strategy stops (lend instead). See plan
    # ``carry_staked_basis_structure_axis_2026_05_04`` Phase 4c.
    CARRY_FUNDING_RANK = "CARRY_FUNDING_RANK"
    # Per-archetype rank allocators (Phase 8 of plan
    # ``carry_staked_basis_structure_axis_2026_05_04``). Each subclass shares
    # the ``BaseRankAllocator`` shape (universe filter -> ranking metric ->
    # threshold gate -> top-N) but ranks by an archetype-specific metric:
    #   YIELD_STAKING_SIMPLE_RANK    : staking_apy_total (base + EIGEN + seasonal - dust)
    #   CARRY_BASIS_PERP_RANK        : funding_apy (CarryFundingRank shape, MVP-coin universe)
    #   CARRY_STAKED_BASIS_RANK      : staking_apy_total + funding_apy, LST-margin-eligible only
    #   CARRY_RECURSIVE_STAKED_RANK  : leverage * (staking_apy_total - borrow_apy)
    #   CARRY_BASIS_DATED_RANK       : dated future basis APY, expiry-matched
    #   YIELD_ROTATION_LENDING_RANK  : lending_apy (supply-side, net of util cap)
    #   ARBITRAGE_PRICE_DISPERSION_RANK : signed funding spread (perp-mode) OR price
    #                                    differential (dated-mode) per ``mode`` config
    YIELD_STAKING_SIMPLE_RANK = "YIELD_STAKING_SIMPLE_RANK"
    CARRY_BASIS_PERP_RANK = "CARRY_BASIS_PERP_RANK"
    CARRY_STAKED_BASIS_RANK = "CARRY_STAKED_BASIS_RANK"
    CARRY_RECURSIVE_STAKED_RANK = "CARRY_RECURSIVE_STAKED_RANK"
    CARRY_BASIS_DATED_RANK = "CARRY_BASIS_DATED_RANK"
    YIELD_ROTATION_LENDING_RANK = "YIELD_ROTATION_LENDING_RANK"
    ARBITRAGE_PRICE_DISPERSION_RANK = "ARBITRAGE_PRICE_DISPERSION_RANK"


class HoldPolicy(StrEnum):
    SAME_CANDLE_EXIT = "SAME_CANDLE_EXIT"
    HOLD_UNTIL_FLIP = "HOLD_UNTIL_FLIP"
    CONTINUOUS = "CONTINUOUS"
    ONE_SHOT = "ONE_SHOT"
    EXPIRY_DRIVEN = "EXPIRY_DRIVEN"
    CONVERGENCE_DRIVEN = "CONVERGENCE_DRIVEN"
    REBALANCE_DRIVEN = "REBALANCE_DRIVEN"


class ShareClass(StrEnum):
    USDT = "USDT"
    USDC = "USDC"
    FDUSD = "FDUSD"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    ETH = "ETH"
    BTC = "BTC"
    SOL = "SOL"


class VenueRoutingMode(StrEnum):
    SOR_AT_EXECUTION = "SOR_AT_EXECUTION"
    STRATEGY_PICKED = "STRATEGY_PICKED"
    META_BROKER = "META_BROKER"


class StakingMethod(StrEnum):
    FRACTIONAL_KELLY = "FRACTIONAL_KELLY"
    FULL_KELLY = "FULL_KELLY"
    CONFIDENCE_SCALED = "CONFIDENCE_SCALED"
    FIXED_PCT = "FIXED_PCT"
    FIXED_NOTIONAL = "FIXED_NOTIONAL"
    VOL_SCALED = "VOL_SCALED"
    DELTA_NEUTRAL_PAIRED = "DELTA_NEUTRAL_PAIRED"
    INVENTORY_SKEWED = "INVENTORY_SKEWED"
    VEGA_NOTIONAL = "VEGA_NOTIONAL"
    GAMMA_NOTIONAL = "GAMMA_NOTIONAL"
    TIER_BASED = "TIER_BASED"
    RANK_WEIGHTED = "RANK_WEIGHTED"
    EQUAL_WEIGHT = "EQUAL_WEIGHT"


class EdgeMethod(StrEnum):
    VALUE_PROB_VS_IMPLIED = "VALUE_PROB_VS_IMPLIED"
    THRESHOLD_CROSSED = "THRESHOLD_CROSSED"
    RATE_DIFFERENTIAL_SUSTAINED = "RATE_DIFFERENTIAL_SUSTAINED"
    SPREAD_CAPTURE = "SPREAD_CAPTURE"
    ARBITRAGE_DISPERSION_GT_COST = "ARBITRAGE_DISPERSION_GT_COST"
    STRUCTURAL_BONUS = "STRUCTURAL_BONUS"
    Z_SCORE_MEAN_REVERSION = "Z_SCORE_MEAN_REVERSION"
    MOMENTUM_TREND = "MOMENTUM_TREND"
    VOL_METRIC_DISLOCATION = "VOL_METRIC_DISLOCATION"
    SURPRISE_DIRECTION = "SURPRISE_DIRECTION"


class Urgency(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    IMMEDIATE = "IMMEDIATE"


class InstructionActionV2(StrEnum):
    TRADE = "TRADE"
    SWAP = "SWAP"
    LEND = "LEND"
    BORROW = "BORROW"
    STAKE = "STAKE"
    UNSTAKE = "UNSTAKE"
    QUOTE = "QUOTE"
    TRANSFER = "TRANSFER"
    BRIDGE = "BRIDGE"
    ATOMIC = "ATOMIC"
    CANCEL = "CANCEL"
    CONVERT_DUST = "CONVERT_DUST"
    # DeFi LP archetype actions (defi_pipeline_extension Phase 4 → e2e closeout)
    # Routed via NonfungiblePositionManager (Uniswap V3 / clones) for
    # CONCENTRATED LPs, or pool-deposit/withdraw for POOL / VAULT LPs.
    # The DEFI_LP_CONCENTRATED engine emits LP_MINT / LP_BURN; the
    # orchestrator dispatches them to UniswapConnector.mint_position()
    # / burn_position().
    LP_MINT = "LP_MINT"
    LP_BURN = "LP_BURN"


class AccountActionV2(StrEnum):
    CLOSE_ALL = "CLOSE_ALL"
    CLOSE_ALL_FOR_STRATEGY = "CLOSE_ALL_FOR_STRATEGY"
    SET_MARGIN_MODE = "SET_MARGIN_MODE"
    SET_LEVERAGE = "SET_LEVERAGE"
    EMERGENCY_LIQUIDATE = "EMERGENCY_LIQUIDATE"
    TRANSFER_SUBACCOUNT = "TRANSFER_SUBACCOUNT"
    WITHDRAW = "WITHDRAW"
    DEPOSIT_ACK = "DEPOSIT_ACK"
    ROTATE_CREDENTIAL = "ROTATE_CREDENTIAL"
    PAUSE = "PAUSE"
    RESUME = "RESUME"


class AtomicExecutionMode(StrEnum):
    ATOMIC = "ATOMIC"
    LEADER_HEDGE = "LEADER_HEDGE"
    SEQUENCED_WITH_PACING = "SEQUENCED_WITH_PACING"
    ATOMIC_ON_CHAIN = "ATOMIC_ON_CHAIN"


class CompensationPolicy(StrEnum):
    CLOSE_LEADER_IF_HEDGE_FAILS = "CLOSE_LEADER_IF_HEDGE_FAILS"
    HOLD_LEG_AND_ALERT = "HOLD_LEG_AND_ALERT"
    RETRY_HEDGE_UNTIL_DEADLINE = "RETRY_HEDGE_UNTIL_DEADLINE"


class MevSubmissionMode(StrEnum):
    PUBLIC_MEMPOOL = "PUBLIC_MEMPOOL"
    FLASHBOTS_PROTECT = "FLASHBOTS_PROTECT"
    MEV_BLOCKER = "MEV_BLOCKER"
    MANIFOLD = "MANIFOLD"
    CUSTOM_PRIVATE_RPC = "CUSTOM_PRIVATE_RPC"
    # Solana — Jito bundle submission via block-engine RPC. Private mempool,
    # 2-block max delay (Solana slot ~400ms). Resolved via UCI/Secret Manager
    # at dispatch time. See defi_catalogue_chain_primitives_2026_05_10.md Phase 1D.
    JITO_BUNDLE = "JITO_BUNDLE"


class VenueType(StrEnum):
    SINGLE_VENUE = "SINGLE_VENUE"
    META_BROKER = "META_BROKER"
    DATA_AGGREGATOR = "DATA_AGGREGATOR"


class VenueCategoryV2(StrEnum):
    """Derived category label. Uppercase values to match slot-label grammar.

    `CROSS_CATEGORY` added 2026-04-25 — primary category for portfolio
    archetypes (cross-category sleeves) and `ARBITRAGE_CROSS_DOMAIN_EVENT`
    (same real-world event listed in PREDICTION + SPORTS).
    """

    CEFI = "CEFI"
    DEFI = "DEFI"
    SPORTS = "SPORTS"
    TRADFI = "TRADFI"
    PREDICTION = "PREDICTION"
    CROSS_CATEGORY = "CROSS_CATEGORY"


class MarginMode(StrEnum):
    ISOLATED = "ISOLATED"
    CROSS = "CROSS"
    PORTFOLIO = "PORTFOLIO"
    REG_T = "REG_T"
    SPAN = "SPAN"


class CommissionStructureType(StrEnum):
    FLAT = "FLAT"
    TIERED = "TIERED"
    PERCENT = "PERCENT"
    COMMISSION_ON_WIN = "COMMISSION_ON_WIN"
    MAKER_TAKER = "MAKER_TAKER"


class KillSwitchReason(StrEnum):
    DISABLED = "DISABLED"
    DAILY_LOSS_BREACH = "DAILY_LOSS_BREACH"
    MAX_DRAWDOWN_BREACH = "MAX_DRAWDOWN_BREACH"
    DATA_STALE = "DATA_STALE"
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"
    COINTEGRATION_BREAKDOWN = "COINTEGRATION_BREAKDOWN"
    GREEK_LIMIT_BREACH = "GREEK_LIMIT_BREACH"
    VENUE_UNAVAILABLE = "VENUE_UNAVAILABLE"


class VenueFeature(StrEnum):
    CROSS_MARGIN = "CROSS_MARGIN"
    PORTFOLIO_MARGIN = "PORTFOLIO_MARGIN"
    SUBACCOUNT = "SUBACCOUNT"
    ATOMIC_MULTI_LEG = "ATOMIC_MULTI_LEG"
    FLASH_LOAN = "FLASH_LOAN"
    NATIVE_STAKING = "NATIVE_STAKING"
    LP_PROVISION = "LP_PROVISION"
    OPTIONS_TRADING = "OPTIONS_TRADING"
    PERPS_TRADING = "PERPS_TRADING"
    SPOT_TRADING = "SPOT_TRADING"
    DARK_POOL = "DARK_POOL"
    BACK_LAY_EXCHANGE = "BACK_LAY_EXCHANGE"


class FillSource(StrEnum):
    VENUE = "VENUE"
    BENCHMARK = "BENCHMARK"
    MATCHING_ENGINE = "MATCHING_ENGINE"


class BenchmarkFillMode(StrEnum):
    ARRIVAL_MID = "ARRIVAL_MID"
    TWAP_WINDOW = "TWAP_WINDOW"
    VWAP_WINDOW = "VWAP_WINDOW"
    PASSIVE_BBO = "PASSIVE_BBO"
    POOL_MID_AT_BLOCK = "POOL_MID_AT_BLOCK"
    LIQUIDATION_BONUS = "LIQUIDATION_BONUS"
    FUNDING_SNAPSHOT = "FUNDING_SNAPSHOT"


BENCHMARK_FILL_MODE_BY_ACTION: dict[InstructionActionV2, BenchmarkFillMode] = {
    InstructionActionV2.TRADE: BenchmarkFillMode.ARRIVAL_MID,
    InstructionActionV2.SWAP: BenchmarkFillMode.POOL_MID_AT_BLOCK,
    InstructionActionV2.LEND: BenchmarkFillMode.FUNDING_SNAPSHOT,
    InstructionActionV2.BORROW: BenchmarkFillMode.FUNDING_SNAPSHOT,
    InstructionActionV2.STAKE: BenchmarkFillMode.FUNDING_SNAPSHOT,
    InstructionActionV2.UNSTAKE: BenchmarkFillMode.FUNDING_SNAPSHOT,
    InstructionActionV2.QUOTE: BenchmarkFillMode.PASSIVE_BBO,
    InstructionActionV2.TRANSFER: BenchmarkFillMode.ARRIVAL_MID,
    InstructionActionV2.BRIDGE: BenchmarkFillMode.POOL_MID_AT_BLOCK,
    InstructionActionV2.ATOMIC: BenchmarkFillMode.ARRIVAL_MID,
    InstructionActionV2.CANCEL: BenchmarkFillMode.PASSIVE_BBO,
    InstructionActionV2.CONVERT_DUST: BenchmarkFillMode.POOL_MID_AT_BLOCK,
    InstructionActionV2.LP_MINT: BenchmarkFillMode.POOL_MID_AT_BLOCK,
    InstructionActionV2.LP_BURN: BenchmarkFillMode.POOL_MID_AT_BLOCK,
}
"""Per-action BenchmarkFillMode — canonical SSOT (closes GAP-16, topology_qgroup_gap_closure_2026_05_09).

Every InstructionActionV2 must have an entry. Matching engine reads this at BATCH mode
always-fill to determine the reference price for simulated fills.
"""


class BacktestGroup(StrEnum):
    A_ML_TRAINING = "A_ML_TRAINING"
    B_STRATEGY = "B_STRATEGY"
    C_EXECUTION_ALPHA = "C_EXECUTION_ALPHA"


class RiskGateLayer(StrEnum):
    STRATEGY_SELF_CHECK = "STRATEGY_SELF_CHECK"
    RISK_PREFLIGHT = "RISK_PREFLIGHT"
    EXECUTION_PRETRADE = "EXECUTION_PRETRADE"
    VENUE_SIDE = "VENUE_SIDE"


class RiskGateDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESIZED = "RESIZED"
    DEFERRED = "DEFERRED"


class TransferType(StrEnum):
    INTERNAL_SUBACCOUNT = "INTERNAL_SUBACCOUNT"
    CEX_WITHDRAWAL_DEPOSIT = "CEX_WITHDRAWAL_DEPOSIT"
    ON_CHAIN_TRANSFER = "ON_CHAIN_TRANSFER"
    BRIDGE = "BRIDGE"
    WRAP_UNWRAP = "WRAP_UNWRAP"
    UNITY_WALLET_OP = "UNITY_WALLET_OP"
    IBKR_FUND_MOVE = "IBKR_FUND_MOVE"


__all__ = [
    "ARCHETYPE_TO_FAMILY",
    "BENCHMARK_FILL_MODE_BY_ACTION",
    "AccountActionV2",
    "AllocatorArchetype",
    "AtomicExecutionMode",
    "BacktestGroup",
    "BenchmarkFillMode",
    "CommissionStructureType",
    "CompensationPolicy",
    "EdgeMethod",
    "FillSource",
    "HoldPolicy",
    "InstructionActionV2",
    "KillSwitchReason",
    "MarginMode",
    "MevSubmissionMode",
    "RiskGateDecision",
    "RiskGateLayer",
    "ShareClass",
    "StakingMethod",
    "StrategyArchetype",
    "StrategyFamily",
    "TransferType",
    "Urgency",
    "VenueCategoryV2",
    "VenueFeature",
    "VenueRoutingMode",
    "VenueType",
]
