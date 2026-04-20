"""Restriction-profile engine — G1.7 of ``stage-3e-refactor-plan``.

Loads the 6 declarative YAML profiles at
``unified-trading-pm/codex/14-playbooks/demo-ops/profiles/`` and resolves a
:class:`RestrictionProfile` for a given persona + flavour + environment +
(optional) questionnaire response.

**Citadel host (Option X carry-through from G1.6):** pure functions live in
UAC alongside the other derivation logic. Strategy-service consumes via the
public ``unified_api_contracts.strategy`` facade; the strategy-service
internal API router at ``strategy_service/api/restriction_profile_router.py``
wraps :func:`resolve_profile` for HTTP callers (UI SSR, pricing-engine,
access-control middleware).

**YAML discovery** (mirrors the G1.8 codex-parity ancestor-walk pattern —
``_find_codex_markdown``):

1. If ``UNIFIED_TRADING_WORKSPACE_ROOT`` env var is set, look at
   ``<workspace>/unified-trading-pm/codex/14-playbooks/demo-ops/profiles/``.
2. Otherwise walk ancestors from this file looking for
   ``unified-trading-pm/codex/...``.
3. In truly-siloed CI (container without PM checkout), return a sentinel
   empty registry — callers receive ``RestrictionProfile(profile_id=<pid>,
   tiles={})`` which downstream UI treats as "resolve unknown → hidden".

The loader parses every YAML file at import and caches them in a
module-level frozen tuple (mirrors ``ARCHETYPE_CAPABILITY_REGISTRY``
pattern). No per-call I/O.

SSOT:
- ``unified-trading-pm/codex/14-playbooks/demo-ops/profiles/*.yaml``
- ``unified-trading-pm/codex/14-playbooks/demo-ops/demo-restriction-profiles.md``
- Validator: ``unified-trading-pm/codex/14-playbooks/demo-ops/_tools/validate_profiles.py``
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, cast

import yaml  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.derivation import (
    ClientAudience,
    DemoFlavour,
    Persona,
    RestrictionProfile,
    TileLockState,
)

Env = Literal["dev", "staging", "prod"]
"""Runtime environment marker. Profile computation is identical across all
three environments per the dev/staging parity rule (rule 03); ``env`` only
carries optional per-env overrides (none shipped today)."""


QuestionnaireCategory = Literal["CeFi", "DeFi", "TradFi", "Sports", "Prediction"]
"""Asset-class category picker — aligns with
``codex/09-strategy/architecture-v2/category-instrument-coverage.md``."""


QuestionnaireInstrumentType = Literal[
    "spot",
    "perp",
    "dated_future",
    "option",
    "lending",
    "staking",
    "lp",
    "event_settled",
]
"""Instrument-type picker — mirrors
``ArchetypeInstrumentType`` from archetype_capability.py."""


QuestionnaireStrategyStyle = Literal[
    "ml_directional",
    "rules_directional",
    "stat_arb",
    "arbitrage",
    "carry",
    "event_driven",
    "market_making",
    "vol_trading",
]
"""Strategy-style picker — mirrors ``StrategyFamilyV2`` minus the
``stat_arb_cross_sectional`` sub-family (UX rollup for prospects)."""


QuestionnaireServiceFamily = Literal["IM", "DART", "RegUmbrella", "combo"]
"""Prospect-facing 4-enum. Narrower than rule 12's ``ServiceFamily``
(which includes ``admin``, ``IM_desk``, ``DART_reporting_only``) —
prospects never pick internal audiences. ``combo`` maps to the union
of IM + DART + RegUmbrella via the overlay logic."""


QuestionnaireFundStructure = Literal["SMA", "Pooled", "NA"]
"""SMA (Separately Managed Account) vs Pooled Fund vs N/A (DART only).
Cross-ref: ``codex/14-playbooks/cross-cutting/sma-vs-pooled.md``."""


class QuestionnaireResponse(BaseModel):
    """G1.10 questionnaire response — 6 axes that feed the restriction-
    profile overlay.

    Every axis is required (no partial responses). ``venue_scope`` accepts
    either the sentinel string ``"all"`` or an explicit list of venue
    IDs; the sentinel is equivalent to ``all_capabilities()`` enumeration
    for scope purposes.

    SSOT for axis values:
    - Categories + instrument types:
      ``codex/09-strategy/architecture-v2/category-instrument-coverage.md``
    - Service family: ``codex/14-playbooks/_ssot-rules/12-service-family-scope-rules.md``
    - Fund structure: ``codex/14-playbooks/cross-cutting/sma-vs-pooled.md``

    The overlay logic in :func:`_apply_questionnaire_override` widens
    tile-level padlocks for vague responses (empty categories = fall back
    to base profile) and tightens them for narrow responses (single
    category = hide tiles irrelevant to that category).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    categories: tuple[QuestionnaireCategory, ...]
    instrument_types: tuple[QuestionnaireInstrumentType, ...]
    venue_scope: tuple[str, ...] | Literal["all"] = "all"
    strategy_style: tuple[QuestionnaireStrategyStyle, ...]
    service_family: QuestionnaireServiceFamily
    fund_structure: QuestionnaireFundStructure


class ProfileYaml(BaseModel):
    """Parsed YAML shape — enforces the schema the PM validator already
    checks, so Pydantic validation here is a belt-and-braces sanity layer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_id: str
    base_audience: ClientAudience
    description: str = ""
    tiles: Mapping[str, TileLockState]
    flavour_overrides: Mapping[str, Mapping[str, TileLockState]] = {}


def _find_profiles_dir() -> Path | None:
    """Resolve the ``profiles/`` directory via env-var then ancestor walk.

    Returns ``None`` in siloed CI where PM is not checked out.
    """

    env_root = os.environ.get("UNIFIED_TRADING_WORKSPACE_ROOT")
    if env_root:
        candidate = Path(env_root) / "unified-trading-pm" / "codex" / "14-playbooks" / "demo-ops" / "profiles"
        if candidate.is_dir():
            return candidate

    current = Path(__file__).resolve()
    for ancestor in current.parents:
        candidate = ancestor / "unified-trading-pm" / "codex" / "14-playbooks" / "demo-ops" / "profiles"
        if candidate.is_dir():
            return candidate
    return None


def _load_profiles() -> tuple[ProfileYaml, ...]:
    profiles_dir = _find_profiles_dir()
    if profiles_dir is None:
        return ()
    parsed: list[ProfileYaml] = []
    for yaml_path in sorted(profiles_dir.glob("*.yaml")):
        with yaml_path.open("r", encoding="utf-8") as handle:
            raw = cast(object, yaml.safe_load(handle))  # pyright: ignore[reportUnknownMemberType]
        parsed.append(ProfileYaml.model_validate(raw))
    return tuple(parsed)


RESTRICTION_PROFILE_REGISTRY: tuple[ProfileYaml, ...] = _load_profiles()
"""Module-level immutable tuple of parsed YAML profiles. Populated at import.
Empty in truly-siloed CI (no PM checkout reachable)."""


_BY_PERSONA: dict[str, ProfileYaml] = {profile.persona_id: profile for profile in RESTRICTION_PROFILE_REGISTRY}


def _apply_flavour_overlay(
    tiles: Mapping[str, TileLockState],
    overrides: Mapping[str, Mapping[str, TileLockState]],
    flavour: DemoFlavour | None,
) -> Mapping[str, TileLockState]:
    """Layer flavour overrides on top of base tile states."""

    if flavour is None or flavour not in overrides:
        return dict(tiles)
    merged: dict[str, TileLockState] = dict(tiles)
    merged.update(overrides[flavour])
    return merged


def _apply_questionnaire_override(
    tiles: Mapping[str, TileLockState],
    questionnaire: QuestionnaireResponse | None,
) -> Mapping[str, TileLockState]:
    """Apply questionnaire-driven tile state overrides.

    Overlay semantics (G1.10 — 6-axis questionnaire):

    * **service_family = "IM"**: keeps investor-relations + reports
      unlocked; hides DART-specific tiles (trading / research / promote /
      observe / data) beyond what the base persona allows.
    * **service_family = "RegUmbrella"**: keeps reports + regulatory
      facing tiles; hides research/promote/trading (client operates
      their own stack under Odum's FCA wrapper — observing live is a
      client-side concern).
    * **service_family = "DART"**: keeps the full DART stack visible if
      the base profile already allowed it; hides investor-relations
      (IM-only surface).
    * **service_family = "combo"**: union of IM + DART + RegUmbrella
      overlays — no tightening. Surfaces everything the base profile
      allows.
    * **fund_structure = "SMA" or "Pooled"**: only meaningful for
      IM / RegUmbrella; purely informational today (no tile narrowing).
    * **Empty ``categories``** (vague answer): fall back to base profile
      untouched — G1.13 tempt-logic will widen padlocks later.

    The override only *tightens* — a tile that's ``unlocked`` in the base
    profile may become ``padlocked`` or ``hidden``; a tile that's
    ``hidden`` stays hidden regardless of questionnaire choices. (The
    prospect hasn't paid for surfaces the base profile already gates.)
    """

    if questionnaire is None:
        return dict(tiles)

    tiles_map: dict[str, TileLockState] = dict(tiles)

    # Vague response — no categories picked — skip the overlay.
    if not questionnaire.categories:
        return tiles_map

    def _tighten(tile_id: str, state: TileLockState) -> None:
        current = tiles_map.get(tile_id)
        if current is None:
            return  # Unknown tile — leave alone
        # Precedence: hidden > padlocked > unlocked.
        if current == "hidden":
            return
        if state == "hidden":
            tiles_map[tile_id] = "hidden"
        elif state == "padlocked" and current == "unlocked":
            tiles_map[tile_id] = "padlocked"

    sf = questionnaire.service_family

    if sf == "IM":
        # IM picker → hide DART-operations tiles; keep reports + IR.
        _tighten("trading", "hidden")
        _tighten("research", "hidden")
        _tighten("promote", "hidden")
        _tighten("observe", "hidden")
        _tighten("data", "padlocked")
    elif sf == "RegUmbrella":
        # Reg Umbrella picker → hide research/promote; padlock trading/observe
        # (client operates their own stack under Odum's permissions).
        _tighten("research", "hidden")
        _tighten("promote", "hidden")
        _tighten("trading", "padlocked")
        _tighten("observe", "padlocked")
        _tighten("investor-relations", "hidden")
    elif sf == "DART":
        # DART picker → hide IM-only investor-relations tile.
        _tighten("investor-relations", "hidden")
    # combo → no tightening (union semantics).

    return tiles_map


def _apply_env_override(
    tiles: Mapping[str, TileLockState],
    env: Env,
) -> Mapping[str, TileLockState]:
    """Env override — currently a no-op per dev/staging parity rule.

    Reserved for future staging-only rollouts (e.g. dark-launch a tile as
    padlocked in staging before unlocking in prod).
    """

    _ = env
    return dict(tiles)


def resolve_profile(
    persona: Persona,
    flavour: DemoFlavour | None = None,
    env: Env = "dev",
    questionnaire: QuestionnaireResponse | None = None,
) -> RestrictionProfile:
    """Resolve the full :class:`RestrictionProfile` for a persona.

    Overlay order (stage-3c §1.3): base → flavour → questionnaire → env.

    Returns a :class:`RestrictionProfile` whose ``tiles`` mapping is the
    authoritative per-tile lock-state input for the UI ``useTileLockState``
    hook. ``profile_id`` is populated from the YAML ``persona_id`` so
    downstream consumers have a stable identifier.

    Args:
        persona: Persona context (from G1.6 derivation). ``persona.id`` must
            match one of the YAML ``persona_id`` keys.
        flavour: Optional demo flavour; overlays applied if declared in the
            YAML's ``flavour_overrides``.
        env: Runtime environment — no-op today per dev/staging parity rule.
        questionnaire: Optional G1.10 questionnaire response; stub today.

    Returns:
        A :class:`RestrictionProfile` with populated ``tiles`` + empty
        block-level fields (the block-level shape is produced by the
        complementary G1.6 ``demo_universe`` / ``prod_restrictions`` calls).
    """

    profile_yaml = _BY_PERSONA.get(persona.persona_id)
    if profile_yaml is None:
        # Unknown persona → hidden-everywhere deterministic profile (safer
        # default than unlocked-everywhere; matches ``anon.yaml``'s shape).
        return RestrictionProfile(profile_id=persona.persona_id, tiles={})

    tiles = _apply_flavour_overlay(profile_yaml.tiles, profile_yaml.flavour_overrides, flavour)
    tiles = _apply_questionnaire_override(tiles, questionnaire)
    tiles = _apply_env_override(tiles, env)

    return RestrictionProfile(profile_id=profile_yaml.persona_id, tiles=tiles)


def known_persona_ids() -> tuple[str, ...]:
    """Return the sorted tuple of persona_ids that the registry knows about.

    Empty in siloed CI. Useful for parametric tests and UI debug panels.
    """

    return tuple(sorted(_BY_PERSONA.keys()))


__all__ = [
    "RESTRICTION_PROFILE_REGISTRY",
    "Env",
    "ProfileYaml",
    "QuestionnaireResponse",
    "known_persona_ids",
    "resolve_profile",
]
