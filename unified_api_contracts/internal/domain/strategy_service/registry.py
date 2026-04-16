"""
Strategy Registry — SSOT for all strategy definitions.

Consumed by backend services directly (Python import) and by UI via
the OpenAPI generation pipeline (generate_ui_reference_data.py →
ui-reference-data.json → generated.ts).

Strategy families, archetypes, allowed execution modes, and display
names are all defined here. No other source should duplicate these.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StrategyFamily(StrEnum):
    """Top-level grouping of related strategies."""

    BASIS_TRADE = "BASIS_TRADE"
    RECURSIVE_STAKED_BASIS = "RECURSIVE_STAKED_BASIS"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    MARKET_MAKING = "MARKET_MAKING"
    ARBITRAGE = "ARBITRAGE"
    LENDING = "LENDING"
    STAKING = "STAKING"
    LP_PROVISION = "LP_PROVISION"
    OPTIONS_VOL = "OPTIONS_VOL"
    ML_DIRECTIONAL = "ML_DIRECTIONAL"
    SPORTS_ARB = "SPORTS_ARB"
    SPORTS_VALUE = "SPORTS_VALUE"
    SPORTS_ML = "SPORTS_ML"
    SPORTS_MM = "SPORTS_MM"
    PREDICTION_ARB = "PREDICTION_ARB"
    PREDICTION_ML = "PREDICTION_ML"
    YIELD = "YIELD"


class StrategyArchetype(StrEnum):
    """Execution archetype — defines how the strategy interacts with execution."""

    BASIS_TRADE = "BASIS_TRADE"
    RECURSIVE_STAKED_BASIS = "RECURSIVE_STAKED_BASIS"
    DIRECTIONAL = "DIRECTIONAL"
    ML_DIRECTIONAL = "ML_DIRECTIONAL"
    MARKET_MAKING = "MARKET_MAKING"
    ARBITRAGE = "ARBITRAGE"
    YIELD = "YIELD"
    AMM_LP = "AMM_LP"
    OPTIONS = "OPTIONS"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    SPORTS_ARB = "SPORTS_ARB"
    PREDICTION_ARB = "PREDICTION_ARB"


class Category(StrEnum):
    """Asset class / domain category."""

    CEFI = "CEFI"
    DEFI = "DEFI"
    TRADFI = "TRADFI"
    SPORTS = "SPORTS"
    PREDICTION = "PREDICTION"


class ExecutionMode(StrEnum):
    """Strategy execution mode.

    - HUF: Hold until flip — signal updates drive position changes.
    - SCE: Same candle exit — ML-driven TP/SL within one candle.
      Only valid for specific CeFi/TradFi ML strategies.
    - EVT: Event-driven — tick-level or real-time event responses
      (market making, options quoting, live sports).
    """

    HUF = "HUF"
    SCE = "SCE"
    EVT = "EVT"


# ---------------------------------------------------------------------------
# Mode enforcement rules
# ---------------------------------------------------------------------------

# Which modes are allowed per category. SCE is narrow: only CeFi/TradFi ML.
_CATEGORY_ALLOWED_MODES: dict[Category, frozenset[ExecutionMode]] = {
    Category.DEFI: frozenset({ExecutionMode.HUF, ExecutionMode.EVT}),
    Category.CEFI: frozenset({ExecutionMode.HUF, ExecutionMode.SCE, ExecutionMode.EVT}),
    Category.TRADFI: frozenset({ExecutionMode.HUF, ExecutionMode.SCE, ExecutionMode.EVT}),
    Category.SPORTS: frozenset({ExecutionMode.HUF, ExecutionMode.EVT}),
    Category.PREDICTION: frozenset({ExecutionMode.HUF, ExecutionMode.EVT, ExecutionMode.SCE}),
}


def validate_mode_for_category(category: Category | str, mode: ExecutionMode | str) -> bool:
    """Check if a mode is valid for a given category."""
    cat = Category(category) if isinstance(category, str) else category
    m = ExecutionMode(mode) if isinstance(mode, str) else mode
    return m in _CATEGORY_ALLOWED_MODES.get(cat, frozenset())


# ---------------------------------------------------------------------------
# Strategy definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyDefinition:
    """Single strategy definition in the registry."""

    strategy_id: str
    name: str
    family: StrategyFamily
    category: Category
    archetype: StrategyArchetype
    execution_mode: ExecutionMode
    strategy_type: str  # Human-readable type label (e.g. "Basis Trade", "ML Directional")
    default_timeframe: str = ""
    version: int = 1
    description: str = ""
    client_id: str = ""  # Default client association (e.g. "patrick-elysium")

    @property
    def allowed_modes(self) -> frozenset[ExecutionMode]:
        """Modes allowed for this strategy's category."""
        return _CATEGORY_ALLOWED_MODES.get(self.category, frozenset())


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class StrategyRegistry:
    """SSOT for all strategy definitions.

    Backend services import this directly. The UI receives it via the
    OpenAPI generation pipeline (generate_ui_reference_data.py serialises
    to JSON, UI reads from ui-reference-data.json).
    """

    def __init__(self, strategies: list[StrategyDefinition] | None = None) -> None:
        entries = strategies or _DEFAULT_STRATEGIES
        self._by_id: dict[str, StrategyDefinition] = {s.strategy_id: s for s in entries}

    # -- Lookups -----------------------------------------------------------

    def get(self, strategy_id: str) -> StrategyDefinition | None:
        """Get a strategy definition by ID."""
        return self._by_id.get(strategy_id)

    def resolve_name(self, strategy_id: str) -> str:
        """Resolve strategy_id → display name. Returns ID if not found."""
        defn = self._by_id.get(strategy_id)
        return defn.name if defn else strategy_id

    def resolve_family(self, strategy_id: str) -> str:
        """Resolve strategy_id → family name. Returns empty string if not found."""
        defn = self._by_id.get(strategy_id)
        return defn.family.value if defn else ""

    def resolve_category(self, strategy_id: str) -> str:
        """Resolve strategy_id → category. Falls back to parsing ID prefix."""
        defn = self._by_id.get(strategy_id)
        if defn:
            return defn.category.value
        # Fallback: parse from strategy_id prefix
        parts = strategy_id.split("_", 1)
        prefix = parts[0].upper() if parts else ""
        if prefix in {c.value for c in Category}:
            return prefix
        return ""

    # -- Filtering ---------------------------------------------------------

    def get_by_family(self, family: StrategyFamily | str) -> list[StrategyDefinition]:
        """Get all strategies in a family."""
        f = StrategyFamily(family) if isinstance(family, str) else family
        return [s for s in self._by_id.values() if s.family == f]

    def get_by_category(self, category: Category | str) -> list[StrategyDefinition]:
        """Get all strategies in a category."""
        c = Category(category) if isinstance(category, str) else category
        return [s for s in self._by_id.values() if s.category == c]

    def get_by_archetype(self, archetype: StrategyArchetype | str) -> list[StrategyDefinition]:
        """Get all strategies with a given archetype."""
        a = StrategyArchetype(archetype) if isinstance(archetype, str) else archetype
        return [s for s in self._by_id.values() if s.archetype == a]

    # -- Validation --------------------------------------------------------

    def validate_mode(self, strategy_id: str, mode: str) -> bool:
        """Check if a mode is valid for a registered strategy."""
        defn = self._by_id.get(strategy_id)
        if not defn:
            return True  # Unknown strategy — don't block
        return ExecutionMode(mode) in defn.allowed_modes

    # -- Iteration ---------------------------------------------------------

    def all(self) -> list[StrategyDefinition]:
        """All registered strategies."""
        return list(self._by_id.values())

    @property
    def families(self) -> dict[str, list[StrategyDefinition]]:
        """Strategies grouped by family."""
        result: dict[str, list[StrategyDefinition]] = {}
        for s in self._by_id.values():
            result.setdefault(s.family.value, []).append(s)
        return result

    def __len__(self) -> int:
        return len(self._by_id)

    # -- Serialisation (for OpenAPI pipeline) ------------------------------

    def to_dict(self) -> dict[str, object]:
        """Serialise for JSON export (used by generate_ui_reference_data.py)."""
        return {
            "strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "name": s.name,
                    "family": s.family.value,
                    "category": s.category.value,
                    "archetype": s.archetype.value,
                    "execution_mode": s.execution_mode.value,
                    "strategy_type": s.strategy_type,
                    "default_timeframe": s.default_timeframe,
                    "version": s.version,
                    "description": s.description,
                    "client_id": s.client_id,
                }
                for s in self._by_id.values()
            ],
            "families": {fam: [s.strategy_id for s in strats] for fam, strats in self.families.items()},
            "categories": [c.value for c in Category],
            "archetypes": [a.value for a in StrategyArchetype],
            "execution_modes": [m.value for m in ExecutionMode],
        }


# ---------------------------------------------------------------------------
# Default strategy catalogue (migrated from UI strategy-registry.ts)
# ---------------------------------------------------------------------------

_s = StrategyDefinition  # short alias for readability

_DEFAULT_STRATEGIES: list[StrategyDefinition] = [
    # ── DeFi ──────────────────────────────────────────────────────────────
    _s(
        "DEFI_ETH_BASIS_HUF_1H",
        "ETH Basis Trade",
        StrategyFamily.BASIS_TRADE,
        Category.DEFI,
        StrategyArchetype.BASIS_TRADE,
        ExecutionMode.HUF,
        "Basis Trade",
        "1H",
    ),
    _s(
        "DEFI_ETH_REC_STAKE_HUF_1H",
        "ETH Recursive Staked Basis",
        StrategyFamily.RECURSIVE_STAKED_BASIS,
        Category.DEFI,
        StrategyArchetype.RECURSIVE_STAKED_BASIS,
        ExecutionMode.EVT,
        "Leveraged Basis",
        "1H",
    ),
    _s(
        "DEFI_UNI_LP_HUF_1H",
        "Uniswap V3 LP (ETH-USDT)",
        StrategyFamily.LP_PROVISION,
        Category.DEFI,
        StrategyArchetype.AMM_LP,
        ExecutionMode.EVT,
        "LP Provision",
        "1H",
    ),
    _s(
        "DEFI_AAVE_LEND_HUF_1D",
        "AAVE Lending (USDT)",
        StrategyFamily.LENDING,
        Category.DEFI,
        StrategyArchetype.YIELD,
        ExecutionMode.EVT,
        "Lending",
        "1D",
    ),
    _s(
        "DEFI_MORPHO_LEND_HUF_1D",
        "Morpho Lending",
        StrategyFamily.LENDING,
        Category.DEFI,
        StrategyArchetype.YIELD,
        ExecutionMode.EVT,
        "Lending",
        "1D",
    ),
    _s(
        "DEFI_WBTC_BASIS_HUF_4H",
        "WBTC Basis Trade",
        StrategyFamily.BASIS_TRADE,
        Category.DEFI,
        StrategyArchetype.BASIS_TRADE,
        ExecutionMode.HUF,
        "Basis Trade",
        "4H",
    ),
    _s(
        "DEFI_STETH_STAKED_BASIS_HUF_1D",
        "stETH Staked Basis",
        StrategyFamily.BASIS_TRADE,
        Category.DEFI,
        StrategyArchetype.BASIS_TRADE,
        ExecutionMode.EVT,
        "Staked Basis",
        "1D",
    ),
    _s(
        "DEFI_ETH_RECURSIVE_STAKED_HUF_BLOCK",
        "ETH Recursive Staked (Acme)",
        StrategyFamily.RECURSIVE_STAKED_BASIS,
        Category.DEFI,
        StrategyArchetype.RECURSIVE_STAKED_BASIS,
        ExecutionMode.EVT,
        "Recursive Staked Basis",
        "BLOCK",
    ),
    _s(
        "DEFI_USDC_AAVE_LEND_HUF_1H",
        "USDC Aave Lending",
        StrategyFamily.LENDING,
        Category.DEFI,
        StrategyArchetype.YIELD,
        ExecutionMode.EVT,
        "Lending",
        "1H",
    ),
    _s(
        "DEFI_ARB_AMM_LP_HUF_4H",
        "ARB AMM LP",
        StrategyFamily.LP_PROVISION,
        Category.DEFI,
        StrategyArchetype.AMM_LP,
        ExecutionMode.HUF,
        "AMM LP",
        "4H",
    ),
    _s(
        "DEFI_MATIC_AMM_LP_HUF_2H",
        "MATIC AMM LP",
        StrategyFamily.LP_PROVISION,
        Category.DEFI,
        StrategyArchetype.AMM_LP,
        ExecutionMode.HUF,
        "AMM LP",
        "2H",
    ),
    _s(
        "DEFI_DAI_AAVE_LEND_HUF_8H",
        "DAI Aave Lending",
        StrategyFamily.LENDING,
        Category.DEFI,
        StrategyArchetype.YIELD,
        ExecutionMode.EVT,
        "Lending",
        "8H",
    ),
    _s(
        "DEFI_ETH_STAKED_BASIS_HUF_1H",
        "ETH Staked Basis (weETH + Short Perp)",
        StrategyFamily.BASIS_TRADE,
        Category.DEFI,
        StrategyArchetype.BASIS_TRADE,
        ExecutionMode.HUF,
        "Staked Basis",
        "1H",
    ),
    _s(
        "DEFI_AAVE_SUPPLY_USDC_HUF_1H",
        "Aave V3 USDC Supply",
        StrategyFamily.LENDING,
        Category.DEFI,
        StrategyArchetype.YIELD,
        ExecutionMode.HUF,
        "Lending",
        "1H",
    ),
    # Client-specific DeFi
    _s(
        "ELYSIUM_AAVE_LENDING",
        "AAVE Lending",
        StrategyFamily.LENDING,
        Category.DEFI,
        StrategyArchetype.YIELD,
        ExecutionMode.HUF,
        "Yield Lending",
        "",
        1,
        "",
        "patrick-elysium",
    ),
    _s(
        "ELYSIUM_BASIS_TRADE",
        "Multi-Venue Basis Trade",
        StrategyFamily.BASIS_TRADE,
        Category.DEFI,
        StrategyArchetype.BASIS_TRADE,
        ExecutionMode.HUF,
        "Basis Trade",
        "",
        1,
        "",
        "patrick-elysium",
    ),
    _s(
        "ELYSIUM_RECURSIVE_STAKED_BASIS",
        "Recursive Staked Basis (Hedged)",
        StrategyFamily.RECURSIVE_STAKED_BASIS,
        Category.DEFI,
        StrategyArchetype.RECURSIVE_STAKED_BASIS,
        ExecutionMode.HUF,
        "Recursive Yield",
        "",
        1,
        "",
        "patrick-elysium",
    ),
    # ── CeFi ──────────────────────────────────────────────────────────────
    _s(
        "CEFI_BTC_MM_EVT_TICK",
        "BTC Market Making (Binance)",
        StrategyFamily.MARKET_MAKING,
        Category.CEFI,
        StrategyArchetype.MARKET_MAKING,
        ExecutionMode.EVT,
        "Market Making",
        "TICK",
    ),
    _s(
        "CEFI_ETH_OPT_MM_EVT_TICK",
        "ETH Options MM (Deribit)",
        StrategyFamily.OPTIONS_VOL,
        Category.CEFI,
        StrategyArchetype.OPTIONS,
        ExecutionMode.EVT,
        "Options MM",
        "TICK",
    ),
    _s(
        "CEFI_BTC_BASIS_SCE_1H",
        "BTC Basis (Binance-HL)",
        StrategyFamily.BASIS_TRADE,
        Category.CEFI,
        StrategyArchetype.BASIS_TRADE,
        ExecutionMode.SCE,
        "Basis Trade",
        "1H",
    ),
    _s(
        "CEFI_BTC_ML_DIR_HUF_4H",
        "ML Directional BTC",
        StrategyFamily.ML_DIRECTIONAL,
        Category.CEFI,
        StrategyArchetype.ML_DIRECTIONAL,
        ExecutionMode.HUF,
        "ML Directional",
        "4H",
    ),
    _s(
        "CEFI_ETH_MOM_HUF_4H",
        "ETH Momentum",
        StrategyFamily.MOMENTUM,
        Category.CEFI,
        StrategyArchetype.MOMENTUM,
        ExecutionMode.HUF,
        "Momentum",
        "4H",
    ),
    _s(
        "CEFI_SOL_MOM_HUF_4H",
        "SOL Momentum",
        StrategyFamily.MOMENTUM,
        Category.CEFI,
        StrategyArchetype.MOMENTUM,
        ExecutionMode.HUF,
        "Momentum",
        "4H",
    ),
    _s(
        "CEFI_MULTI_ARB_SCE_TICK",
        "Multi-Venue Arbitrage",
        StrategyFamily.ARBITRAGE,
        Category.CEFI,
        StrategyArchetype.ARBITRAGE,
        ExecutionMode.SCE,
        "Arbitrage",
        "TICK",
    ),
    _s(
        "CEFI_AVAX_MOMENTUM_HUF_1H",
        "AVAX Momentum",
        StrategyFamily.MOMENTUM,
        Category.CEFI,
        StrategyArchetype.MOMENTUM,
        ExecutionMode.HUF,
        "Momentum",
        "1H",
    ),
    _s(
        "CEFI_ETH_MEAN_REV_SCE_4H",
        "ETH Mean Reversion",
        StrategyFamily.MEAN_REVERSION,
        Category.CEFI,
        StrategyArchetype.MEAN_REVERSION,
        ExecutionMode.SCE,
        "Mean Reversion",
        "4H",
    ),
    _s(
        "CEFI_DOGE_MM_HUF_30S",
        "DOGE Market Making",
        StrategyFamily.MARKET_MAKING,
        Category.CEFI,
        StrategyArchetype.MARKET_MAKING,
        ExecutionMode.HUF,
        "Market Making",
        "30S",
    ),
    _s(
        "CEFI_LINK_MOMENTUM_SCE_2H",
        "LINK Momentum",
        StrategyFamily.MOMENTUM,
        Category.CEFI,
        StrategyArchetype.MOMENTUM,
        ExecutionMode.SCE,
        "Momentum",
        "2H",
    ),
    _s(
        "CEFI_ARB_MEAN_REV_HUF_15M",
        "ARB Mean Reversion",
        StrategyFamily.MEAN_REVERSION,
        Category.CEFI,
        StrategyArchetype.MEAN_REVERSION,
        ExecutionMode.HUF,
        "Mean Reversion",
        "15M",
    ),
    _s(
        "CEFI_XRP_MM_HUF_1M",
        "XRP Market Making",
        StrategyFamily.MARKET_MAKING,
        Category.CEFI,
        StrategyArchetype.MARKET_MAKING,
        ExecutionMode.HUF,
        "Market Making",
        "1M",
    ),
    _s(
        "CEFI_MATIC_MOMENTUM_SCE_2H",
        "MATIC Momentum",
        StrategyFamily.MOMENTUM,
        Category.CEFI,
        StrategyArchetype.MOMENTUM,
        ExecutionMode.SCE,
        "Momentum",
        "2H",
    ),
    _s(
        "CEFI_SUI_MOMENTUM_HUF_1H",
        "SUI Momentum",
        StrategyFamily.MOMENTUM,
        Category.CEFI,
        StrategyArchetype.MOMENTUM,
        ExecutionMode.HUF,
        "Momentum",
        "1H",
    ),
    # ── TradFi ────────────────────────────────────────────────────────────
    _s(
        "TRADFI_SPY_MOM_HUF_1D",
        "SPY ML Directional",
        StrategyFamily.ML_DIRECTIONAL,
        Category.TRADFI,
        StrategyArchetype.DIRECTIONAL,
        ExecutionMode.HUF,
        "ML Directional",
        "1D",
    ),
    _s(
        "TRADFI_BOND_MEAN_REV_HUF_1D",
        "Bond Mean Reversion",
        StrategyFamily.MEAN_REVERSION,
        Category.TRADFI,
        StrategyArchetype.MEAN_REVERSION,
        ExecutionMode.HUF,
        "Mean Reversion",
        "1D",
    ),
    _s(
        "TRADFI_ES_ML_DIR_SCE_30M",
        "ES ML Directional",
        StrategyFamily.ML_DIRECTIONAL,
        Category.TRADFI,
        StrategyArchetype.ML_DIRECTIONAL,
        ExecutionMode.SCE,
        "ML Directional",
        "30M",
    ),
    _s(
        "TRADFI_SPY_OPTIONS_ML_EVT_1D",
        "SPY Options ML",
        StrategyFamily.OPTIONS_VOL,
        Category.TRADFI,
        StrategyArchetype.OPTIONS,
        ExecutionMode.EVT,
        "Options ML",
        "1D",
    ),
    _s(
        "TRADFI_CL_ML_DIR_SCE_1H",
        "Crude Oil ML Directional",
        StrategyFamily.ML_DIRECTIONAL,
        Category.TRADFI,
        StrategyArchetype.ML_DIRECTIONAL,
        ExecutionMode.SCE,
        "ML Directional",
        "1H",
    ),
    _s(
        "TRADFI_GC_MM_OPTIONS_EVT_TICK",
        "Gold Options MM",
        StrategyFamily.OPTIONS_VOL,
        Category.TRADFI,
        StrategyArchetype.OPTIONS,
        ExecutionMode.EVT,
        "Options MM",
        "TICK",
    ),
    _s(
        "TRADFI_ZN_OPTIONS_ML_SCE_4H",
        "Treasury Options ML",
        StrategyFamily.OPTIONS_VOL,
        Category.TRADFI,
        StrategyArchetype.OPTIONS,
        ExecutionMode.SCE,
        "Options ML",
        "4H",
    ),
    _s(
        "TRADFI_SI_ML_DIR_SCE_2H",
        "Silver ML Directional",
        StrategyFamily.ML_DIRECTIONAL,
        Category.TRADFI,
        StrategyArchetype.ML_DIRECTIONAL,
        ExecutionMode.SCE,
        "ML Directional",
        "2H",
    ),
    _s(
        "TRADFI_QQQ_MM_OPTIONS_EVT_5M",
        "QQQ Options MM",
        StrategyFamily.OPTIONS_VOL,
        Category.TRADFI,
        StrategyArchetype.OPTIONS,
        ExecutionMode.EVT,
        "Options MM",
        "5M",
    ),
    _s(
        "TRADFI_EURUSD_ML_DIR_SCE_1H",
        "EUR/USD ML Directional",
        StrategyFamily.ML_DIRECTIONAL,
        Category.TRADFI,
        StrategyArchetype.ML_DIRECTIONAL,
        ExecutionMode.SCE,
        "ML Directional",
        "1H",
    ),
    _s(
        "TRADFI_HG_OPTIONS_ML_SCE_1D",
        "Copper Options ML",
        StrategyFamily.OPTIONS_VOL,
        Category.TRADFI,
        StrategyArchetype.OPTIONS,
        ExecutionMode.SCE,
        "Options ML",
        "1D",
    ),
    # ── Sports ────────────────────────────────────────────────────────────
    _s(
        "SPORTS_NFL_ARB_SCE_GAME",
        "Football Cross-Book Arb",
        StrategyFamily.SPORTS_ARB,
        Category.SPORTS,
        StrategyArchetype.SPORTS_ARB,
        ExecutionMode.EVT,
        "Arbitrage",
        "GAME",
    ),
    _s(
        "SPORTS_NBA_ML_HUF_GAME",
        "NBA Halftime ML",
        StrategyFamily.SPORTS_ML,
        Category.SPORTS,
        StrategyArchetype.DIRECTIONAL,
        ExecutionMode.HUF,
        "Sports ML",
        "GAME",
    ),
    _s(
        "SPORTS_EPL_ARB_EVT_MATCH",
        "EPL Cross-Book Arb",
        StrategyFamily.SPORTS_ARB,
        Category.SPORTS,
        StrategyArchetype.SPORTS_ARB,
        ExecutionMode.EVT,
        "Arbitrage",
        "MATCH",
    ),
    _s(
        "SPORTS_NFL_VALUE_BET_EVT_GAME",
        "NFL Value Betting",
        StrategyFamily.SPORTS_VALUE,
        Category.SPORTS,
        StrategyArchetype.SPORTS_ARB,
        ExecutionMode.EVT,
        "Value Betting",
        "GAME",
    ),
    _s(
        "SPORTS_LALIGA_ML_EVT_MATCH",
        "La Liga ML Sports",
        StrategyFamily.SPORTS_ML,
        Category.SPORTS,
        StrategyArchetype.SPORTS_ARB,
        ExecutionMode.EVT,
        "Sports ML",
        "MATCH",
    ),
    _s(
        "SPORTS_NBA_MM_EVT_QUARTER",
        "NBA Market Making",
        StrategyFamily.SPORTS_MM,
        Category.SPORTS,
        StrategyArchetype.MARKET_MAKING,
        ExecutionMode.EVT,
        "Sports MM",
        "QUARTER",
    ),
    _s(
        "SPORTS_MLB_VALUE_BET_EVT_GAME",
        "MLB Value Betting",
        StrategyFamily.SPORTS_VALUE,
        Category.SPORTS,
        StrategyArchetype.SPORTS_ARB,
        ExecutionMode.EVT,
        "Value Betting",
        "GAME",
    ),
    _s(
        "SPORTS_SERIE_A_ARB_EVT_MATCH",
        "Serie A Arbitrage",
        StrategyFamily.SPORTS_ARB,
        Category.SPORTS,
        StrategyArchetype.SPORTS_ARB,
        ExecutionMode.EVT,
        "Arbitrage",
        "MATCH",
    ),
    _s(
        "SPORTS_BETFAIR_MM_EVT_TICK",
        "Betfair EPL Market Making",
        StrategyFamily.SPORTS_MM,
        Category.SPORTS,
        StrategyArchetype.MARKET_MAKING,
        ExecutionMode.EVT,
        "Sports MM",
        "TICK",
    ),
    # ── Prediction ────────────────────────────────────────────────────────
    _s(
        "PRED_POLY_ARB_SCE_1M",
        "Prediction Market Arb",
        StrategyFamily.PREDICTION_ARB,
        Category.PREDICTION,
        StrategyArchetype.PREDICTION_ARB,
        ExecutionMode.EVT,
        "Arbitrage",
        "1M",
    ),
    _s(
        "PRED_BTC_CEFI_ARB_SCE_5M",
        "BTC Prediction-CeFi Arb",
        StrategyFamily.PREDICTION_ARB,
        Category.PREDICTION,
        StrategyArchetype.PREDICTION_ARB,
        ExecutionMode.EVT,
        "Arbitrage",
        "5M",
    ),
    _s(
        "PREDICTION_POLY_ML_DIR_EVT_4H",
        "Prediction ML Directional",
        StrategyFamily.PREDICTION_ML,
        Category.PREDICTION,
        StrategyArchetype.PREDICTION_ARB,
        ExecutionMode.EVT,
        "ML Directional",
        "4H",
    ),
    _s(
        "PREDICTION_POLY_ARB_EVT_1H",
        "Prediction Cross-Platform Arb",
        StrategyFamily.PREDICTION_ARB,
        Category.PREDICTION,
        StrategyArchetype.PREDICTION_ARB,
        ExecutionMode.EVT,
        "Arbitrage",
        "1H",
    ),
]

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY = StrategyRegistry()
"""Module-level singleton — import this for lookups."""
