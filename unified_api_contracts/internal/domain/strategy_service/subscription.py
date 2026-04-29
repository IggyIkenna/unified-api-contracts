"""Stub for missing subscription module.

This module was referenced by `unified_api_contracts/strategy.py:110`
but the file was missing in this checkout. Stubbed minimally so the
API can boot. NOT a real implementation — anyone consuming these
symbols at runtime will need the proper module.

Workaround for local dev only. Track + resolve via UAC owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SubscriptionType(str, Enum):
    """Stub. Real values unknown at this checkout."""

    DEFAULT = "default"


class ExclusiveLockViolation(Exception):
    """Stub. Raised when a strategy subscription conflicts with another."""


@dataclass
class StrategyInstanceSubscription:
    """Stub. Real fields unknown at this checkout."""

    strategy_id: str = ""
    client_id: str = ""
    subscription_type: SubscriptionType = SubscriptionType.DEFAULT

    def __post_init__(self) -> None:  # pragma: no cover — stub
        pass

    @classmethod
    def from_dict(
        cls, d: dict[str, Any]
    ) -> "StrategyInstanceSubscription":  # pragma: no cover
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
