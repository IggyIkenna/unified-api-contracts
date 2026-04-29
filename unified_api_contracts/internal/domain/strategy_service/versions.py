"""Stub for missing versions module.

Same situation as `subscription.py` — referenced but not present in
this checkout. Stubbed minimally so the API can boot. NOT a real
implementation.

Workaround for local dev only. Track + resolve via UAC owner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class VersionStatus(str, Enum):
    """Stub."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass
class ApprovalRecord:
    """Stub."""

    approver: str = ""
    approved_at: datetime | None = None
    notes: str = ""


@dataclass
class ConfigDiff:
    """Stub."""

    field_path: str = ""
    old_value: Any = None
    new_value: Any = None


@dataclass
class StrategyVersion:
    """Stub."""

    version_id: str = ""
    status: VersionStatus = VersionStatus.DRAFT
    approvals: list[ApprovalRecord] = field(default_factory=list)
    diffs: list[ConfigDiff] = field(default_factory=list)


def minimum_approval_maturity() -> int:  # pragma: no cover — stub
    """Stub. Real value unknown."""
    return 0
