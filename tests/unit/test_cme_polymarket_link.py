"""Unit tests for CME event-contract → Polymarket canonical-group cross-link."""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.cme_polymarket_link import (
    CME_ROOT_TO_POLYMARKET_GROUP,
    LINKED_CME_ROOTS,
    linked_question_group,
)
from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CANONICAL_GROUP_METADATA,
    CanonicalQuestionGroup,
)

# All 9 CME event-contract roots per _CME_EVENT_CONTRACTS SSOT.
_ALL_9_CME_ROOTS = frozenset({"ECES", "ECNQ", "ECRTY", "ECYM", "ECGC", "ECCL", "ECNG", "EC6E", "ECBTC"})


def test_all_9_cme_roots_wired() -> None:
    """Every CME EC* root has a Polymarket group — no root returns None."""
    assert _ALL_9_CME_ROOTS == LINKED_CME_ROOTS


def test_linked_cme_roots_matches_dict_keys() -> None:
    assert frozenset(CME_ROOT_TO_POLYMARKET_GROUP) == LINKED_CME_ROOTS


def test_known_root_returns_correct_group() -> None:
    assert linked_question_group("ECES") == CanonicalQuestionGroup.SPX_UP_DOWN_DAILY
    assert linked_question_group("ECBTC") == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY
    assert linked_question_group("ECNQ") == CanonicalQuestionGroup.NDX_UP_DOWN_DAILY
    assert linked_question_group("ECRTY") == CanonicalQuestionGroup.RUT_UP_DOWN_DAILY
    assert linked_question_group("ECYM") == CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY
    assert linked_question_group("ECGC") == CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY
    assert linked_question_group("ECCL") == CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY
    assert linked_question_group("ECNG") == CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY
    assert linked_question_group("EC6E") == CanonicalQuestionGroup.EUR_UP_DOWN_DAILY


def test_unknown_root_returns_none() -> None:
    assert linked_question_group("INVALID") is None
    assert linked_question_group("") is None


def test_all_groups_are_daily_cadence() -> None:
    """All CME-linked groups resolve daily (CME daily binary settlement)."""
    for root, group in CME_ROOT_TO_POLYMARKET_GROUP.items():
        meta = CANONICAL_GROUP_METADATA[group]
        assert meta.cadence == "daily", f"{root} → {group}: expected daily cadence"
        assert meta.expected_market_ids_per_day == 1
        assert meta.resolution_basis == "price_threshold"
