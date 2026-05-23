"""CME event-contract root → Polymarket ``CanonicalQuestionGroup`` cross-link SSOT.

Each CME event-contract root resolves YES/NO at a binary price threshold.
Polymarket hosts equivalent binary markets on the same underlying.  This module
is the single authoritative mapping between the two venues' question taxonomy,
enabling ``ArbitrageCrossDomainEventEngine`` to build paired positions when the
basis exceeds a threshold.

All 9 CME EC* roots are wired as of predictions_master Phase 5 (2026-05-22).

Plan: ``cme_polymarket_arb_2026_05_08.md`` Phase 2.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CanonicalQuestionGroup,
)

# ---------------------------------------------------------------------------
# Canonical cross-link map — CME root → CanonicalQuestionGroup
#
# All 9 CME event-contract roots wired to their Polymarket canonical groups.
# Roots absent from this dict have no wired Polymarket counterpart.
# Call ``linked_question_group`` and check for None before building arb pairs.
# ---------------------------------------------------------------------------
CME_ROOT_TO_POLYMARKET_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    "ECES": CanonicalQuestionGroup.SPX_UP_DOWN_DAILY,  # E-mini S&P 500
    "ECBTC": CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,  # Bitcoin
    "ECNQ": CanonicalQuestionGroup.NDX_UP_DOWN_DAILY,  # E-mini NDX 100
    "ECRTY": CanonicalQuestionGroup.RUT_UP_DOWN_DAILY,  # E-mini Russell 2000
    "ECYM": CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY,  # E-mini Dow Jones
    "ECGC": CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY,  # Gold
    "ECCL": CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY,  # Crude WTI
    "ECNG": CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY,  # Natural Gas
    "EC6E": CanonicalQuestionGroup.EUR_UP_DOWN_DAILY,  # Euro FX
}

# Frozenset of CME roots with a live Polymarket link (convenience for callers).
LINKED_CME_ROOTS: Final[frozenset[str]] = frozenset(CME_ROOT_TO_POLYMARKET_GROUP)


def linked_question_group(cme_root: str) -> CanonicalQuestionGroup | None:
    """Return the Polymarket ``CanonicalQuestionGroup`` paired with *cme_root*.

    Returns ``None`` when the root has no wired Polymarket counterpart (either
    the root is unknown or it is waiting on ``predictions_master`` Phase 5).
    Callers MUST handle ``None`` — this is not an error condition; it means the
    arb pair does not exist yet and should be skipped.
    """
    return CME_ROOT_TO_POLYMARKET_GROUP.get(cme_root)


__all__ = [
    "CME_ROOT_TO_POLYMARKET_GROUP",
    "LINKED_CME_ROOTS",
    "linked_question_group",
]
