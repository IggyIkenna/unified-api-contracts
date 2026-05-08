"""Compliance sink protocol — the seam UAC ``cost()`` uses to emit pricing-rule violations.

Stage 3E G2 § 5. UAC stays pure Python with no direct dependency on
UTL's event bus — instead ``cost()`` accepts an optional
``compliance_sink`` callable and invokes it whenever a rule-07 or
rule-08 violation is detected. The wiring from :class:`CompliancEvent`
to UTL ``log_event(PRICING_RULE_0[78]_VIOLATION, ...)`` lives in the
caller (strategy-service / pricing-engine / admin tools).

SSOT:
    codex/16-strategy-playbooks/infra-spec/stage-3e-g2-env-split.md § 5
    codex/14-playbooks/_ssot-rules/07-data-licensing-boundaries.md
    codex/14-playbooks/_ssot-rules/08-pricing-principles.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

RuleId = Literal["07", "08"]
ViolationCode = Literal[
    "exclusivity_on_tier_a",
    "internal_cost_leakage",
    "mixed_tier_advisory",
    "raw_data_framing_on_tier_a",
    "missing_twelve_month_minimum",
]


@dataclass(frozen=True)
class ComplianceEvent:
    """Emitted by ``cost()`` when a pricing rule is violated.

    Fields mirror UTL ``PricingViolationPayload`` so a caller sink can
    translate 1:1 without losing information. UAC stays pure: no UTL
    import, no event-bus dependency.
    """

    rule_id: RuleId
    violation_code: ViolationCode
    combo_id: str
    caller_audience: str
    org_id: str | None
    requested_tier: str
    details: str


class ComplianceSink(Protocol):
    """Callable that forwards a :class:`ComplianceEvent` to UTL / Pub/Sub."""

    def __call__(self, event: ComplianceEvent) -> None: ...


def combo_id_for(
    archetype_id: str,
    asset_group: str,
    instrument_type: str,
    venue_id: str | None,
    chain: str | None,
) -> str:
    """Build the stable combo-id string used as the ComplianceEvent key.

    Matches the slot-label convention in strategy_availability.py so
    downstream BigQuery joins line up without re-derivation.
    """

    parts: list[str] = [archetype_id, asset_group, instrument_type]
    if venue_id:
        parts.append(venue_id)
    if chain:
        parts.append(chain)
    return ":".join(parts)


__all__ = [
    "ComplianceEvent",
    "ComplianceSink",
    "RuleId",
    "ViolationCode",
    "combo_id_for",
]
