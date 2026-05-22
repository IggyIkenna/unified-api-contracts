"""CME event-contract root → Polymarket ``CanonicalQuestionGroup`` cross-link SSOT.

Each CME event-contract root resolves YES/NO at a binary price threshold.
Polymarket hosts equivalent binary markets on the same underlying.  This module
is the single authoritative mapping between the two venues' question taxonomy,
enabling ``ArbitrageCrossDomainEventEngine`` to build paired positions when the
basis exceeds a threshold.

**PARTIAL (2026-05-22)** — only ECES (S&P 500) and ECBTC (Bitcoin) are wired.
The remaining 7 roots (ECRTY/ECYM/ECGC/ECCL/ECNG/EC6E/ECNQ) require 6 new
``CanonicalQuestionGroup`` variants from ``predictions_master`` Phase 5.
Do NOT add those roots here until Phase 5 ships.

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
# ECES (E-mini S&P 500 event contract) → Polymarket SPX up/down daily markets.
# ECBTC (Bitcoin event contract)       → Polymarket BTC up/down daily markets.
#
# Roots absent from this dict have no wired Polymarket counterpart yet.
# Call ``linked_question_group`` and check for None before building arb pairs.
# ---------------------------------------------------------------------------
CME_ROOT_TO_POLYMARKET_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    "ECES": CanonicalQuestionGroup.SPX_UP_DOWN_DAILY,
    "ECBTC": CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,
    # BLOCKED: ECRTY/ECYM/ECGC/ECCL/ECNG/EC6E/ECNQ — predictions_master Phase 5
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
