"""Unit tests for G1.7 restriction-profile engine.

Coverage targets (≥ 20 cases):
* Every one of the 6 YAML profiles parses + appears in the registry.
* `resolve_profile(persona)` returns the declared tiles for every persona.
* Flavour overlays apply in overlay order (base → flavour).
* Unknown persona → hidden-everywhere deterministic fallback.
* Dev/staging parity: same input → byte-identical `RestrictionProfile`.
* Unknown / invalid inputs surface via Pydantic validation.

SSOTs:
- ``unified-trading-pm/codex/14-playbooks/demo-ops/profiles/*.yaml``
- Validator: ``unified-trading-pm/codex/14-playbooks/demo-ops/_tools/validate_profiles.py``
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.strategy import (
    RESTRICTION_PROFILE_REGISTRY,
    CommercialPath,
    Env,
    Persona,
    ProfileYaml,
    QuestionnaireResponse,
    RestrictionProfile,
    known_persona_ids,
    resolve_profile,
)

# ---------------------------------------------------------------------------
# Skip the whole module in truly-siloed CI (no PM checkout)
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not RESTRICTION_PROFILE_REGISTRY,
    reason="No PM checkout reachable — profiles YAML not discoverable",
)


_EXPECTED_PERSONA_IDS = (
    "admin",
    "anon",
    "client-full",
    "prospect-dart",
    "prospect-im",
    "prospect-regulatory",
)

_EXPECTED_TILE_IDS = frozenset(
    {
        "data",
        "research",
        "promote",
        "trading",
        "observe",
        "reports",
        "investor-relations",
        "admin",
    }
)


def _persona(persona_id: str, commercial_path: CommercialPath = CommercialPath.CLIENT_FULL_PIPELINE) -> Persona:
    return Persona(persona_id=persona_id, commercial_path=commercial_path)


# ---------------------------------------------------------------------------
# 1. Registry shape
# ---------------------------------------------------------------------------


def test_registry_loaded_from_pm_checkout() -> None:
    assert len(RESTRICTION_PROFILE_REGISTRY) == 6


def test_all_expected_personas_present() -> None:
    assert known_persona_ids() == _EXPECTED_PERSONA_IDS


@pytest.mark.parametrize("expected_id", _EXPECTED_PERSONA_IDS)
def test_every_persona_id_appears_once(expected_id: str) -> None:
    matches = [p for p in RESTRICTION_PROFILE_REGISTRY if p.persona_id == expected_id]
    assert len(matches) == 1


def test_every_profile_declares_all_tile_ids() -> None:
    """Profiles must cover the full tile-id enum from services.ts."""

    for profile in RESTRICTION_PROFILE_REGISTRY:
        assert set(profile.tiles.keys()) == _EXPECTED_TILE_IDS, (
            f"persona {profile.persona_id} missing tiles: {_EXPECTED_TILE_IDS - set(profile.tiles.keys())}"
        )


def test_profile_yaml_is_frozen() -> None:
    profile = RESTRICTION_PROFILE_REGISTRY[0]
    with pytest.raises(ValidationError):
        profile.persona_id = "mutated"  # pyright: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# 2. resolve_profile — happy path per persona
# ---------------------------------------------------------------------------


def test_resolve_admin_unlocks_everything() -> None:
    profile = resolve_profile(_persona("admin", CommercialPath.ODUM_INTERNAL))
    assert profile.profile_id == "admin"
    assert all(state == "unlocked" for state in profile.tiles.values())


def test_resolve_client_full_hides_im_tiles() -> None:
    profile = resolve_profile(_persona("client-full"))
    assert profile.tiles["investor-relations"] == "hidden"
    assert profile.tiles["admin"] == "hidden"
    assert profile.tiles["trading"] == "unlocked"
    assert profile.tiles["reports"] == "unlocked"


def test_resolve_prospect_im_shows_reports_only_path() -> None:
    profile = resolve_profile(_persona("prospect-im"))
    assert profile.tiles["reports"] == "unlocked"
    assert profile.tiles["investor-relations"] == "unlocked"
    assert profile.tiles["trading"] == "hidden"
    assert profile.tiles["research"] == "hidden"


def test_resolve_prospect_dart_padlocks_promote() -> None:
    profile = resolve_profile(_persona("prospect-dart"))
    assert profile.tiles["trading"] == "unlocked"
    assert profile.tiles["promote"] == "padlocked"
    assert profile.tiles["investor-relations"] == "hidden"


def test_resolve_prospect_regulatory_reports_unlocked() -> None:
    profile = resolve_profile(_persona("prospect-regulatory"))
    assert profile.tiles["reports"] == "unlocked"
    assert profile.tiles["research"] == "hidden"
    assert profile.tiles["trading"] == "padlocked"


def test_resolve_anon_hides_everything() -> None:
    profile = resolve_profile(_persona("anon"))
    assert all(state == "hidden" for state in profile.tiles.values())


# ---------------------------------------------------------------------------
# 3. Flavour overlays
# ---------------------------------------------------------------------------


def test_prospect_dart_broader_platform_unlocks_promote() -> None:
    profile = resolve_profile(_persona("prospect-dart"), flavour="broader_platform")
    assert profile.tiles["promote"] == "unlocked"


def test_prospect_dart_turbo_padlocks_ancillary_tiles() -> None:
    profile = resolve_profile(_persona("prospect-dart"), flavour="turbo")
    assert profile.tiles["data"] == "padlocked"
    assert profile.tiles["research"] == "padlocked"
    assert profile.tiles["reports"] == "padlocked"
    assert profile.tiles["trading"] == "unlocked"


def test_prospect_im_turbo_hides_data() -> None:
    profile = resolve_profile(_persona("prospect-im"), flavour="turbo")
    assert profile.tiles["data"] == "hidden"


def test_client_full_deep_dive_no_op_equal_to_base() -> None:
    base = resolve_profile(_persona("client-full"))
    deep = resolve_profile(_persona("client-full"), flavour="deep_dive")
    assert dict(base.tiles) == dict(deep.tiles)


def test_unknown_flavour_falls_through_to_base() -> None:
    # prospect-im does not declare a sales_pitch.data override; ensure that
    # the fallback path picks the base state.
    profile = resolve_profile(_persona("prospect-im"), flavour="deep_dive")
    assert profile.tiles["reports"] == "unlocked"


# ---------------------------------------------------------------------------
# 4. Env + questionnaire overlays (both no-ops today)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("env", ["dev", "staging", "prod"])
def test_env_override_is_a_noop_per_parity_rule(env: Env) -> None:
    dev_profile = resolve_profile(_persona("prospect-dart"))
    env_profile = resolve_profile(_persona("prospect-dart"), env=env)
    assert dict(dev_profile.tiles) == dict(env_profile.tiles)


def test_questionnaire_none_is_a_noop() -> None:
    """Passing no questionnaire leaves the base profile untouched."""

    base = resolve_profile(_persona("prospect-dart"))
    with_none = resolve_profile(_persona("prospect-dart"), questionnaire=None)
    assert dict(base.tiles) == dict(with_none.tiles)


def test_questionnaire_empty_categories_is_a_noop() -> None:
    """Vague response (no categories picked) falls back to base — G1.13
    tempt-logic will later widen padlocks for this case."""

    empty_qr = QuestionnaireResponse(
        categories=(),
        instrument_types=(),
        strategy_style=(),
        service_family="DART",
        fund_structure=("NA",),
    )
    base = resolve_profile(_persona("prospect-dart"))
    with_vague = resolve_profile(_persona("prospect-dart"), questionnaire=empty_qr)
    assert dict(base.tiles) == dict(with_vague.tiles)


def test_questionnaire_service_family_im_hides_dart_tiles() -> None:
    """IM picker on a DART-base profile hides trading/research/promote/
    observe and padlocks data — converging toward the IM reporting path."""

    im_qr = QuestionnaireResponse(
        categories=("CeFi",),
        instrument_types=("spot",),
        strategy_style=("ml_directional",),
        service_family="IM",
        fund_structure=("Pooled",),
    )
    profile = resolve_profile(_persona("prospect-dart"), questionnaire=im_qr)
    assert profile.tiles["trading"] == "hidden"
    assert profile.tiles["research"] == "hidden"
    assert profile.tiles["promote"] == "hidden"  # was padlocked; tightens to hidden
    assert profile.tiles["observe"] == "hidden"
    assert profile.tiles["data"] in {"padlocked", "hidden"}


def test_questionnaire_service_family_regumbrella_tightens_ops_tiles() -> None:
    reg_qr = QuestionnaireResponse(
        categories=("TradFi",),
        instrument_types=("spot",),
        strategy_style=("carry",),
        service_family="RegUmbrella",
        fund_structure=("SMA",),
    )
    profile = resolve_profile(_persona("prospect-dart"), questionnaire=reg_qr)
    assert profile.tiles["research"] == "hidden"
    assert profile.tiles["promote"] == "hidden"
    # prospect-dart base is trading=unlocked; Reg Umbrella padlocks it
    assert profile.tiles["trading"] in {"padlocked", "hidden"}
    assert profile.tiles["investor-relations"] == "hidden"


def test_questionnaire_service_family_dart_hides_investor_relations() -> None:
    dart_qr = QuestionnaireResponse(
        categories=("DeFi",),
        instrument_types=("perp",),
        strategy_style=("stat_arb",),
        service_family="DART",
        fund_structure=("NA",),
    )
    profile = resolve_profile(_persona("prospect-dart"), questionnaire=dart_qr)
    assert profile.tiles["investor-relations"] == "hidden"
    # Other DART surfaces stay unchanged
    assert profile.tiles["trading"] == "unlocked"
    assert profile.tiles["research"] == "unlocked"


def test_questionnaire_service_family_combo_no_tightening() -> None:
    """Combo service_family picks the union — no tightening applied."""

    combo_qr = QuestionnaireResponse(
        categories=("CeFi", "DeFi"),
        instrument_types=("spot", "perp"),
        strategy_style=("ml_directional", "stat_arb"),
        service_family="combo",
        fund_structure=("NA",),
    )
    base = resolve_profile(_persona("prospect-dart"))
    with_combo = resolve_profile(_persona("prospect-dart"), questionnaire=combo_qr)
    assert dict(base.tiles) == dict(with_combo.tiles)


def test_questionnaire_cannot_unlock_a_hidden_tile() -> None:
    """Overlay only tightens — a tile hidden in the base profile stays
    hidden regardless of questionnaire choices."""

    # anon.yaml has all tiles hidden; any questionnaire response must preserve that.
    aggressive_qr = QuestionnaireResponse(
        categories=("CeFi",),
        instrument_types=("spot",),
        strategy_style=("ml_directional",),
        service_family="DART",
        fund_structure=("NA",),
    )
    profile = resolve_profile(_persona("anon"), questionnaire=aggressive_qr)
    assert all(state == "hidden" for state in profile.tiles.values())


def test_questionnaire_response_rejects_extra_fields() -> None:
    """``extra='forbid'`` — unknown axes must be rejected."""

    with pytest.raises(ValidationError):
        QuestionnaireResponse.model_validate(
            {
                "categories": ["CeFi"],
                "instrument_types": ["spot"],
                "strategy_style": ["ml_directional"],
                "service_family": "DART",
                "fund_structure": ["NA"],
                "unknown_axis": "oops",
            }
        )


# ---------------------------------------------------------------------------
# 5. Unknown-persona fallback
# ---------------------------------------------------------------------------


def test_unknown_persona_returns_hidden_deterministic_profile() -> None:
    profile = resolve_profile(_persona("does-not-exist"))
    assert profile.profile_id == "does-not-exist"
    assert profile.tiles == {}


# ---------------------------------------------------------------------------
# 6. Pydantic validation guards
# ---------------------------------------------------------------------------


def test_profile_yaml_rejects_unknown_state() -> None:
    with pytest.raises(ValidationError):
        ProfileYaml.model_validate(
            {
                "persona_id": "test",
                "base_audience": "admin",
                "tiles": {"data": "not-a-state"},
                "flavour_overrides": {},
            }
        )


def test_profile_yaml_rejects_unknown_audience() -> None:
    with pytest.raises(ValidationError):
        ProfileYaml.model_validate(
            {
                "persona_id": "test",
                "base_audience": "not-an-audience",
                "tiles": {},
                "flavour_overrides": {},
            }
        )


def test_returned_profile_keeps_extra_forbid() -> None:
    """RestrictionProfile ``extra='forbid'`` survives G1.7 tile-field add."""

    profile = resolve_profile(_persona("admin", CommercialPath.ODUM_INTERNAL))
    assert isinstance(profile, RestrictionProfile)
    with pytest.raises(ValidationError):
        profile.foo = "bar"  # pyright: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# Reg-Umbrella axes (2026-04-21 — plan
# `reg_umbrella_questionnaire_and_onboarding_docs_2026_04_21`)
# ---------------------------------------------------------------------------


def test_questionnaire_accepts_reg_umbrella_fields_populated() -> None:
    """All 7 new Reg-Umbrella axes accept their declared types."""

    qr = QuestionnaireResponse(
        categories=("TradFi",),
        instrument_types=("spot",),
        strategy_style=("carry",),
        service_family="RegUmbrella",
        fund_structure=("SMA",),
        licence_region="EU_and_UK",
        targets_3mo="Onboard 2 client orgs; £5M AUM",
        targets_1yr="£25M AUM; 3 live strategies",
        targets_2yr="£100M AUM; regulatory audit passed",
        own_mlro=False,
        entity_jurisdiction="GB",
        supported_currencies=("GBP", "EUR", "USD"),
    )
    assert qr.licence_region == "EU_and_UK"
    assert qr.targets_3mo and "AUM" in qr.targets_3mo
    assert qr.own_mlro is False
    assert qr.entity_jurisdiction == "GB"
    assert qr.supported_currencies == ("GBP", "EUR", "USD")


def test_questionnaire_accepts_reg_umbrella_fields_omitted() -> None:
    """Payloads authored before 2026-04-21 (no Reg-Umbrella axes) must
    continue to validate — every new field defaults to ``None`` / ``()``.
    This is the backwards-compat contract for all downstream consumers
    (tempt_logic, resolve-persona, admin playback)."""

    qr = QuestionnaireResponse(
        categories=("CeFi",),
        instrument_types=("spot",),
        strategy_style=("ml_directional",),
        service_family="DART",
        fund_structure=("NA",),
    )
    assert qr.licence_region is None
    assert qr.targets_3mo is None
    assert qr.targets_1yr is None
    assert qr.targets_2yr is None
    assert qr.own_mlro is None
    assert qr.entity_jurisdiction is None
    assert qr.supported_currencies == ()


def test_questionnaire_overlay_unchanged_when_reg_umbrella_populated() -> None:
    """Regression guard — the tile-lock overlay behaviour must not change
    when Reg-Umbrella axes are present. Overlay logic reads the 6 base
    axes only; the new axes surface in admin UI, not persona resolution."""

    base_qr = QuestionnaireResponse(
        categories=("TradFi",),
        instrument_types=("spot",),
        strategy_style=("carry",),
        service_family="RegUmbrella",
        fund_structure=("SMA",),
    )
    enriched_qr = QuestionnaireResponse(
        categories=("TradFi",),
        instrument_types=("spot",),
        strategy_style=("carry",),
        service_family="RegUmbrella",
        fund_structure=("SMA",),
        licence_region="EU_or_UK",
        targets_3mo="Stand up £10M SMA",
        targets_1yr="Add two more SMAs",
        targets_2yr="Pooled fund launch",
        own_mlro=True,
        entity_jurisdiction="Gibraltar",
        supported_currencies=("GBP", "USD"),
    )
    base_profile = resolve_profile(_persona("prospect-dart"), questionnaire=base_qr)
    enriched_profile = resolve_profile(_persona("prospect-dart"), questionnaire=enriched_qr)
    assert dict(base_profile.tiles) == dict(enriched_profile.tiles)


def test_questionnaire_rejects_unknown_licence_region() -> None:
    """Closed enum — Pydantic must reject licence_region outside the
    declared literal set."""

    with pytest.raises(ValidationError):
        QuestionnaireResponse(
            categories=("TradFi",),
            instrument_types=("spot",),
            strategy_style=("carry",),
            service_family="RegUmbrella",
            fund_structure=("SMA",),
            licence_region="APAC",  # pyright: ignore[reportArgumentType] — deliberately invalid
        )


def test_questionnaire_rejects_unknown_top_level_field() -> None:
    """``extra='forbid'`` still holds — unknown fields raise
    ValidationError even after the Reg-Umbrella extension."""

    with pytest.raises(ValidationError):
        QuestionnaireResponse(
            categories=("TradFi",),
            instrument_types=("spot",),
            strategy_style=("carry",),
            service_family="RegUmbrella",
            fund_structure=("SMA",),
            totally_unknown_axis="nope",  # pyright: ignore[reportCallIssue] — deliberately invalid
        )
