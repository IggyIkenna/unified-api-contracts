"""UAC stablecoin peg restore history registry (D.3).

``STABLECOIN_PEG_RESTORE_HISTORY`` maps stable symbol → ordered tuple of
historical depeg events. Feeds the crystallize-vs-wait operator decision at
the 5-10% tier of the depeg ladder.

:data:`DepegEvent.restore_duration_hours` is ``None`` for structural failures
(stablecoin never recovered; issuer permanently wound down).
:data:`DepegEvent.was_structural` is ``True`` for stablecoins that lost their
peg permanently (UST, BUSD) vs transient liquidity crises (USDC, PYUSD, USDE).
"""

from __future__ import annotations

from datetime import date
from typing import Final, NamedTuple


class DepegEvent(NamedTuple):
    """Single historical depeg incident for a stablecoin."""

    event_date: date
    trough_depeg_bps: int
    """Peak deviation below $1 peg in basis points (negative). -1300 = -13% = $0.87."""
    restore_duration_hours: int | None
    """Hours to full peg restoration. ``None`` if the stable never recovered."""
    was_structural: bool
    """``True`` if the depegging was a permanent structural failure (issuer shutdown /
    algorithmic death spiral). ``False`` for transient liquidity / bank-run events."""


STABLECOIN_PEG_RESTORE_HISTORY: Final[dict[str, tuple[DepegEvent, ...]]] = {
    "USDC": (
        # 2023-03-11 Silicon Valley Bank collapse — Circle held ~$3.3B in SVB
        DepegEvent(date(2023, 3, 11), -1300, 72, False),
    ),
    "USDT": (
        # 2018-10-15 early liquidity panic driven by exchange de-listings + FUD
        DepegEvent(date(2018, 10, 15), -700, 24, False),
    ),
    "UST": (
        # 2022-05-09 Terra Luna algorithmic death spiral — permanent structural failure
        DepegEvent(date(2022, 5, 9), -10000, None, True),
    ),
    "PYUSD": (
        # 2024-07 PayPal stablecoin brief depeg driven by thin liquidity on Curve
        DepegEvent(date(2024, 7, 1), -700, 336, False),
    ),
    "USDE": (
        # Q4-2024: multiple <-300bps episodes driven by funding-rate compression
        DepegEvent(date(2024, 10, 7), -280, 48, False),
        DepegEvent(date(2024, 11, 14), -260, 36, False),
        DepegEvent(date(2024, 12, 3), -295, 60, False),
    ),
    "BUSD": (
        # 2024-12: NYDFS + SEC enforcement led to Paxos winding down issuance; never reissued
        DepegEvent(date(2024, 12, 1), -200, None, True),
    ),
}

__all__ = (
    "STABLECOIN_PEG_RESTORE_HISTORY",
    "DepegEvent",
)
