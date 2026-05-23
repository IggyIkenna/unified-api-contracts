"""Instruction validation enums."""

from __future__ import annotations

from enum import StrEnum


class InstructionAction(StrEnum):
    """Action types per stage-3b §2.2 ``intended_action`` enum."""

    BUY = "BUY"
    SELL = "SELL"
    HEDGE = "HEDGE"
    CLOSE = "CLOSE"
    ROLL = "ROLL"
    REBALANCE = "REBALANCE"
    BACK = "BACK"
    LAY = "LAY"
    LEND = "LEND"
    BORROW = "BORROW"
    STAKE = "STAKE"
    UNSTAKE = "UNSTAKE"
    BRIDGE = "BRIDGE"
    ATOMIC = "ATOMIC"


class TimeframeMode(StrEnum):
    """Timeframe urgency mode per stage-3b §2.4."""

    MARKET = "MARKET"
    LIMIT_PASSIVE = "LIMIT_PASSIVE"
    TIME_WINDOW = "TIME_WINDOW"
    SCHEDULED = "SCHEDULED"
    AT_OPEN = "AT_OPEN"
    AT_CLOSE = "AT_CLOSE"


class TimeInForce(StrEnum):
    """Time-in-force per stage-3b §2.5."""

    IOC = "IOC"
    FOK = "FOK"
    GTC = "GTC"
    GTD = "GTD"
    DAY = "DAY"


class LifecycleSemantic(StrEnum):
    """Lifecycle semantic per stage-3b §2.7."""

    NEW = "NEW"
    REPLACE = "REPLACE"
    AMEND = "AMEND"
    ADD_CHILD = "ADD_CHILD"
    CANCEL = "CANCEL"


__all__ = [
    "InstructionAction",
    "LifecycleSemantic",
    "TimeInForce",
    "TimeframeMode",
]
