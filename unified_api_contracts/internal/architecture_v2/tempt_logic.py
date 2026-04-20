"""G1.13 — demo upsell-overlay tempt-logic transform.

Operates between questionnaire ingestion and
:func:`unified_api_contracts.internal.architecture_v2.restriction_profiles.resolve_profile`:
when a prospect's response is **vague** on a widenable axis, the tempt
logic widens the response by one hierarchy step before it feeds into the
overlay. In prod (``env="prod"``), the transform is a no-op — tight
picks stay tight.

**Citadel host (Option X carry-through from G1.6 / G1.7):** pure
functions + types live in UAC alongside the rest of the derivation
layer. Strategy-service consumes via the public
``unified_api_contracts.strategy`` facade; the HTTP router
``strategy_service/api/restriction_profile_router.py`` calls
``apply_tempt_logic`` before passing the questionnaire to
``resolve_profile``.

Axes that widen: ``categories``, ``instrument_types``, ``venue_scope``,
``strategy_style``. Axes that **never** widen: ``service_family``,
``fund_structure`` — these are commercial / structural picks, not
discovery signals (per ``upsell-overlays.md`` and the validator enum).

SSOT:
- YAML hierarchy:
  ``unified-trading-pm/codex/14-playbooks/demo-ops/upsell-overlay-hierarchy.yaml``
- Validator:
  ``unified-trading-pm/codex/14-playbooks/demo-ops/_tools/validate_upsell_hierarchy.py``
- Narrative: ``codex/14-playbooks/demo-ops/upsell-overlays.md``
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.restriction_profiles import (
    Env,
    QuestionnaireCategory,
    QuestionnaireInstrumentType,
    QuestionnaireResponse,
    QuestionnaireStrategyStyle,
)

# Hierarchy mirrors upsell-overlay-hierarchy.yaml. Kept as a literal
# dict (not loaded from YAML at runtime) because the widening rules are
# small + stable; the validator tool in PM enforces YAML parity.
#
# Each axis's "widen" step produces the concrete fallback value that
# replaces a vague response. For Wave F we ship a minimal widening:
# empty answer → the "all"-equivalent fallback. Future G2.x waves can
# layer more nuanced adjacent-family resolution (e.g. "CeFi + DeFi"
# for a prospect who picked only "CeFi").

_ALL_CATEGORIES: tuple[QuestionnaireCategory, ...] = (
    "CeFi",
    "DeFi",
    "TradFi",
    "Sports",
    "Prediction",
)

_ALL_INSTRUMENT_TYPES: tuple[QuestionnaireInstrumentType, ...] = (
    "spot",
    "perp",
    "dated_future",
    "option",
    "lending",
    "staking",
    "lp",
    "event_settled",
)

_ALL_STRATEGY_STYLES: tuple[QuestionnaireStrategyStyle, ...] = (
    "ml_directional",
    "rules_directional",
    "stat_arb",
    "arbitrage",
    "carry",
    "event_driven",
    "market_making",
    "vol_trading",
)


def _is_demo_env(env: Env) -> bool:
    """Tempt-logic runs in dev + staging demo flows; disabled in prod."""

    return env in {"dev", "staging"}


def _categories_vague(picks: tuple[QuestionnaireCategory, ...]) -> bool:
    # Empty array OR every category selected (the "all-selected" signal).
    if len(picks) == 0:
        return True
    return set(picks) >= set(_ALL_CATEGORIES)


def _instrument_types_vague(picks: tuple[QuestionnaireInstrumentType, ...]) -> bool:
    return len(picks) == 0


def _strategy_style_vague(picks: tuple[QuestionnaireStrategyStyle, ...]) -> bool:
    return len(picks) == 0


def _venue_scope_vague(picks: tuple[str, ...] | str) -> bool:
    if isinstance(picks, str):
        # "all" sentinel — matches the YAML ``all_keyword`` trigger.
        return picks == "all"
    return len(picks) == 0


def apply_tempt_logic(
    response: QuestionnaireResponse | None,
    env: Env,
) -> QuestionnaireResponse | None:
    """Widen a vague questionnaire response by one hierarchy step.

    Returns ``response`` unchanged when ``env`` is ``"prod"`` or when the
    response is ``None`` (fresh visitor, no submission yet).

    For Wave F we apply a minimal widening: each vague widenable-axis
    picks the "all" fallback for that axis. service_family and
    fund_structure are **never** widened — operator directive (rule 13
    drafted in upsell-overlay-hierarchy.yaml).
    """

    if response is None or not _is_demo_env(env):
        return response

    updates: dict[str, object] = {}

    if _categories_vague(response.categories):
        updates["categories"] = _ALL_CATEGORIES
    if _instrument_types_vague(response.instrument_types):
        updates["instrument_types"] = _ALL_INSTRUMENT_TYPES
    if _strategy_style_vague(response.strategy_style):
        updates["strategy_style"] = _ALL_STRATEGY_STYLES
    if _venue_scope_vague(response.venue_scope):
        updates["venue_scope"] = "all"

    # service_family + fund_structure intentionally omitted — they never widen.

    if not updates:
        return response

    return response.model_copy(update=updates)


__all__ = ["apply_tempt_logic"]
