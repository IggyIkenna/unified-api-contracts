"""Strategy Registry (v2) — SSOT for strategy name / family / category resolution.

Backed by the v2 archetype capability matrix in
``unified_api_contracts.internal.architecture_v2.archetype_capability``. Each
"strategy entry" is derived from an (archetype x representative slot label)
pair — representative slot labels are declared per cell in the manifest and
follow the slot-label grammar ``ARCHETYPE@venue-asset-instrument-period-quote-env``.

Consumers:
    * ``unified_trading_library.utils.record_enricher.RecordEnricher`` — stamps
      ``strategy_name`` / ``category`` / ``strategy_family`` on exec/pos records.
    * ``unified_trading_api.routes.trading_analytics`` — powers
      ``/api/trading/strategies/catalog`` (UI consumer).
    * ``unified_trading_pm.scripts.openapi.generate_ui_reference_data`` —
      emits ``ui-reference-data.json`` for the UI pipeline.

This module also re-exports ``Category`` and ``ExecutionMode`` — narrow
strategy-service enums that pre-date the v2 refactor and are still consumed
by engine code (strategy-service / execution-service). The v2 canonical
category axis is ``unified_api_contracts.internal.architecture_v2.enums.
VenueCategoryV2`` — new code should import from there. ``Category`` is kept
here only for the engine-side enum semantics (mode validation).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
    CoverageStatus,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyArchetype,
    StrategyFamily,
    VenueCategoryV2,
)

__all__ = [
    "STRATEGY_REGISTRY",
    "Category",
    "ExecutionMode",
    "StrategyArchetype",
    "StrategyDefinition",
    "StrategyFamily",
    "StrategyRegistry",
    "validate_mode_for_category",
]


class Category(StrEnum):
    """Engine-side category enum (strategy-service mode validation).

    The canonical v2 category axis is ``VenueCategoryV2`` (upper-case string
    values). ``Category`` values are kept stable for strategy-service engine
    legacy code that maps ``Category`` → mode rules. New consumers should
    use ``VenueCategoryV2`` (from the ``unified_api_contracts`` facade).
    """

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
# Strategy entry — derived from (archetype x representative slot label)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyDefinition:
    """Single strategy entry in the v2 registry.

    Derived from ``ArchetypeCapability`` + one of its cells'
    ``representative_slot_labels``. ``strategy_id`` is the slot label itself
    (e.g., ``ML_DIRECTIONAL_CONTINUOUS@binance-btc-usdt-5m-usdt-prod``);
    ``name`` is a humanised rendering.
    """

    strategy_id: str
    name: str
    family: StrategyFamily
    category: Category
    archetype: StrategyArchetype
    coverage_status: CoverageStatus


def _category_from_v2(v2_category: VenueCategoryV2) -> Category:
    """Map the v2 ``VenueCategoryV2`` to the engine-side ``Category`` enum.

    Both use identical upper-case string values so the translation is a 1:1
    lookup. Kept as an explicit function so the mapping is auditable.
    """
    return Category(v2_category.value)


def _humanise_slot_label(slot_label: str, archetype: StrategyArchetype) -> str:
    """Produce a human-readable name from a slot label.

    e.g., ``ML_DIRECTIONAL_CONTINUOUS@binance-btc-usdt-5m-usdt-prod`` →
    ``"ML Directional Continuous — binance · btc-usdt · 5m"``. Best-effort
    rendering — callers that need structured fields should parse the slot
    label themselves.
    """
    if "@" not in slot_label:
        return slot_label
    _, body = slot_label.split("@", 1)
    archetype_pretty = archetype.value.replace("_", " ").title()
    return f"{archetype_pretty} — {body}"


def _build_entries_from_capabilities(
    capabilities: tuple[ArchetypeCapability, ...],
) -> list[StrategyDefinition]:
    """Flatten (archetype, cell, representative_slot_label) into entries.

    A capability cell may declare 0, 1, or multiple representative slot
    labels. Each becomes one ``StrategyDefinition``. Cells with
    ``status == BLOCKED`` are excluded (they have no representatives).
    """
    entries: list[StrategyDefinition] = []
    seen: set[str] = set()
    for capability in capabilities:
        family = capability.family
        archetype = capability.archetype_id
        for cell in capability.cells:
            if cell.status == CoverageStatus.BLOCKED:
                continue
            category = _category_from_v2(cell.category)
            for slot_label in cell.representative_slot_labels:
                if slot_label in seen:
                    continue
                seen.add(slot_label)
                entries.append(
                    StrategyDefinition(
                        strategy_id=slot_label,
                        name=_humanise_slot_label(slot_label, archetype),
                        family=family,
                        category=category,
                        archetype=archetype,
                        coverage_status=cell.status,
                    )
                )
    return entries


# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------


class StrategyRegistry:
    """SSOT for strategy lookups backed by the v2 archetype capability matrix.

    Public methods match the pre-v2 interface (``resolve_name`` /
    ``resolve_category`` / ``resolve_family`` / ``to_dict``) so consumers
    migrate without signature churn.
    """

    def __init__(self, strategies: list[StrategyDefinition] | None = None) -> None:
        entries = strategies if strategies is not None else _default_entries()
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
        """Resolve strategy_id → family name. Returns empty string if not found.

        Falls back to parsing the archetype prefix out of the slot label when
        the exact ID is absent — this keeps legacy records (not in the v2
        manifest) routable.
        """
        defn = self._by_id.get(strategy_id)
        if defn:
            return defn.family.value
        # Fallback: if the id follows the slot-label grammar (ARCHETYPE@...)
        # look up the archetype -> family mapping.
        if "@" in strategy_id:
            archetype_token = strategy_id.split("@", 1)[0]
            try:
                archetype = StrategyArchetype(archetype_token)
            except ValueError:
                return ""
            for capability in ARCHETYPE_CAPABILITY_REGISTRY:
                if capability.archetype_id is archetype:
                    return capability.family.value
        return ""

    def resolve_category(self, strategy_id: str) -> str:
        """Resolve strategy_id → category. Empty string if unknown."""
        defn = self._by_id.get(strategy_id)
        if defn:
            return defn.category.value
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

    # -- Iteration ---------------------------------------------------------

    def all(self) -> list[StrategyDefinition]:
        """All registered strategies."""
        return list(self._by_id.values())

    @property
    def families(self) -> dict[str, list[StrategyDefinition]]:
        """Strategies grouped by family value."""
        result: dict[str, list[StrategyDefinition]] = {}
        for s in self._by_id.values():
            result.setdefault(s.family.value, []).append(s)
        return result

    def __len__(self) -> int:
        return len(self._by_id)

    # -- Serialisation (for OpenAPI pipeline) ------------------------------

    def to_dict(self) -> dict[str, object]:
        """Serialise for JSON export (used by ``generate_ui_reference_data.py``).

        v2 shape. Consumers that depended on v1-only fields (``execution_mode``,
        ``strategy_type``, ``default_timeframe``, ``version``, ``description``,
        ``client_id``) must migrate — those fields are gone. The ``coverage_status``
        field is new.
        """
        return {
            "strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "name": s.name,
                    "family": s.family.value,
                    "category": s.category.value,
                    "archetype": s.archetype.value,
                    "coverage_status": s.coverage_status.value,
                }
                for s in self._by_id.values()
            ],
            "families": {fam: [s.strategy_id for s in strats] for fam, strats in self.families.items()},
            "categories": [c.value for c in Category],
            "archetypes": [a.value for a in StrategyArchetype],
            "coverage_statuses": [st.value for st in CoverageStatus],
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def _default_entries() -> list[StrategyDefinition]:
    """Default entries — derived once at module import from the v2 manifest."""
    return _build_entries_from_capabilities(ARCHETYPE_CAPABILITY_REGISTRY)


STRATEGY_REGISTRY = StrategyRegistry()
"""Module-level singleton — import this for lookups."""
