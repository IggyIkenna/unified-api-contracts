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


class QuestionnaireResponse(BaseModel):
    """G1.10 stub — concrete fields arrive with the questionnaire plan.

    Shipped as an empty placeholder so :func:`resolve_profile` signature is
    stable for Wave-D callers; G1.10 widens this into a real response
    schema with commercial-path / risk-tolerance / venue-breadth selectors.
    """

    model_config = ConfigDict(frozen=True, extra="allow")


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
    """G1.10 stub — no override fields declared yet; returns tiles as-is.

    When G1.10 ships the real ``QuestionnaireResponse`` schema, this helper
    widens padlocks on vague answers per the G1.13 tempt-logic rules.
    """

    _ = questionnaire
    return dict(tiles)


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
