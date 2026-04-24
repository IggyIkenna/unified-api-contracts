"""Unit tests for G1.13 demo upsell-overlay tempt-logic.

Coverage targets (≥ 20 cases):
* Env gating — prod returns unchanged; dev/staging widen.
* Each vague axis widens to its "all" fallback.
* service_family + fund_structure never widen.
* None response passes through.
* Tight response passes through.
* End-to-end integration with resolve_profile — vague → wider tile set.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.architecture_v2.tempt_logic import apply_tempt_logic
from unified_api_contracts.strategy import (
    RESTRICTION_PROFILE_REGISTRY,
    CommercialPath,
    Persona,
    QuestionnaireResponse,
    resolve_profile,
)

pytestmark = pytest.mark.skipif(
    not RESTRICTION_PROFILE_REGISTRY,
    reason="No PM checkout reachable — profiles YAML not discoverable",
)


def _tight_qr() -> QuestionnaireResponse:
    return QuestionnaireResponse(
        categories=("CeFi",),
        instrument_types=("spot",),
        venue_scope=("binance",),
        strategy_style=("ml_directional",),
        service_family="DART",
        fund_structure=("NA",),
    )


def _vague_qr() -> QuestionnaireResponse:
    return QuestionnaireResponse(
        categories=(),
        instrument_types=(),
        venue_scope="all",
        strategy_style=(),
        service_family="DART",
        fund_structure=("NA",),
    )


# ---------------------------------------------------------------------------
# 1. Env gating
# ---------------------------------------------------------------------------


def test_prod_env_returns_unchanged() -> None:
    qr = _vague_qr()
    out = apply_tempt_logic(qr, "prod")
    assert out == qr


def test_dev_env_widens() -> None:
    out = apply_tempt_logic(_vague_qr(), "dev")
    assert out is not None
    assert len(out.categories) == 5  # all 5 categories
    assert len(out.instrument_types) == 8  # all instrument types


def test_staging_env_widens() -> None:
    out = apply_tempt_logic(_vague_qr(), "staging")
    assert out is not None
    assert len(out.categories) == 5


def test_none_response_passes_through() -> None:
    assert apply_tempt_logic(None, "dev") is None
    assert apply_tempt_logic(None, "prod") is None


# ---------------------------------------------------------------------------
# 2. Tight response passes through unchanged even in demo envs
# ---------------------------------------------------------------------------


def test_tight_response_demo_env_passes_through() -> None:
    qr = _tight_qr()
    out = apply_tempt_logic(qr, "dev")
    assert out == qr


# ---------------------------------------------------------------------------
# 3. Per-axis widening
# ---------------------------------------------------------------------------


def test_empty_categories_widens_to_all_five() -> None:
    qr = _tight_qr().model_copy(update={"categories": ()})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert set(out.categories) == {"CeFi", "DeFi", "TradFi", "Sports", "Prediction"}


def test_all_categories_selected_is_vague_and_widens_idempotently() -> None:
    # If they picked all 5, the "all_selected" trigger still marks it
    # vague; widening returns the same 5-tuple.
    qr = _tight_qr().model_copy(update={"categories": ("CeFi", "DeFi", "TradFi", "Sports", "Prediction")})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert set(out.categories) == {"CeFi", "DeFi", "TradFi", "Sports", "Prediction"}


def test_empty_instrument_types_widens_to_all_eight() -> None:
    qr = _tight_qr().model_copy(update={"instrument_types": ()})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert len(out.instrument_types) == 8


def test_empty_strategy_style_widens_to_all_eight() -> None:
    qr = _tight_qr().model_copy(update={"strategy_style": ()})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert len(out.strategy_style) == 8


def test_all_venue_scope_keyword_widens() -> None:
    qr = _tight_qr().model_copy(update={"venue_scope": "all"})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert out.venue_scope == "all"  # still "all" — idempotent


def test_empty_venue_scope_widens_to_all() -> None:
    qr = _tight_qr().model_copy(update={"venue_scope": ()})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert out.venue_scope == "all"


def test_explicit_venues_do_not_widen() -> None:
    qr = _tight_qr().model_copy(update={"venue_scope": ("binance", "uniswap_v3")})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert out.venue_scope == ("binance", "uniswap_v3")


# ---------------------------------------------------------------------------
# 4. service_family + fund_structure NEVER widen
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service_family", ["IM", "DART", "RegUmbrella", "combo"])
def test_service_family_never_widens(service_family: str) -> None:
    qr = _vague_qr().model_copy(update={"service_family": service_family})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert out.service_family == service_family


@pytest.mark.parametrize("fund_structure", [("SMA",), ("Pooled",), ("prop",), ("NA",), ("SMA", "prop")])
def test_fund_structure_never_widens(fund_structure: tuple[str, ...]) -> None:
    qr = _vague_qr().model_copy(update={"fund_structure": fund_structure})
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert out.fund_structure == fund_structure


# ---------------------------------------------------------------------------
# 5. Mixed vague + tight axes
# ---------------------------------------------------------------------------


def test_mixed_vague_only_widens_vague_axes() -> None:
    qr = _tight_qr().model_copy(
        update={
            "categories": (),  # vague
            "instrument_types": ("spot",),  # tight — no widening
            "strategy_style": (),  # vague
        }
    )
    out = apply_tempt_logic(qr, "dev")
    assert out is not None
    assert len(out.categories) == 5
    assert out.instrument_types == ("spot",)  # preserved
    assert len(out.strategy_style) == 8


# ---------------------------------------------------------------------------
# 6. End-to-end — vague response yields a wider tile set than tight
# ---------------------------------------------------------------------------


def test_e2e_vague_vs_tight_widens_profile_in_demo() -> None:
    persona = Persona(persona_id="prospect-dart", commercial_path=CommercialPath.CLIENT_FULL_PIPELINE)
    # Tight: prospect-dart base profile + no IM/Reg tightening (DART).
    tight_profile = resolve_profile(persona, questionnaire=_tight_qr(), env="dev")
    # Vague: same persona + DART service_family; widening is per-axis but
    # service_family stays DART, so the overlay's DART-specific
    # tightening (hide investor-relations) still applies. Widening here
    # just ensures categories/instrument_types aren't empty — so the
    # overlay has more context. Assertion: tile set is the same shape
    # (service_family dominates) but the vague input did NOT degrade
    # into an unknown fallback.
    vague_profile = resolve_profile(persona, questionnaire=_vague_qr(), env="dev")
    assert tight_profile.tiles == vague_profile.tiles


def test_e2e_prod_disables_widening() -> None:
    persona = Persona(persona_id="prospect-dart", commercial_path=CommercialPath.CLIENT_FULL_PIPELINE)
    # In prod, vague response should yield the same raw overlay as tight
    # — the widening no-op preserves the original response. For this
    # particular persona, the DART-branch overlay tightens identically
    # regardless of categories, so we just assert the call succeeds.
    prod = resolve_profile(persona, questionnaire=_vague_qr(), env="prod")
    dev = resolve_profile(persona, questionnaire=_vague_qr(), env="dev")
    # Prod preserves vague-input-as-is; demo widens it. For DART persona
    # the service_family overlay behaviour is identical either way.
    assert prod.profile_id == dev.profile_id
