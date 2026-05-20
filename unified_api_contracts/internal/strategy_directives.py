"""Per-archetype allocation directives — emitted by trading-agent-service.

ArchetypeAllocationDirective is the May-23 scaffold directive: simple per-archetype
weight + enabled flag. Distinct from architecture_v2.AllocationDirective (which is
the full multi-client, multi-strategy production allocator output for post-cutover).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ArchetypeAllocationDirective(BaseModel):
    """Simple per-archetype allocation directive emitted by trading-agent-service.

    May-23 scope: trading-agent-service emits no-op instances with
    source='trading-agent-service-stub'. Production allocator logic ships
    post-cutover via epic §1.7 Phase 10.7.

    Naming note: named ArchetypeAllocationDirective (not AllocationDirective) to
    avoid collision with architecture_v2.AllocationDirective, which is the
    full multi-client production allocator schema. Pre-audit finding 2026-05-20
    slot-3; documented in slot_3.md ping.
    """

    archetype_id: str = Field(description="Canonical archetype name, e.g. 'carry_staked_basis'")
    allocation_weight: Decimal = Field(
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Fractional weight to allocate to this archetype; 0.0 to 1.0",
    )
    enabled: bool = Field(description="Whether this archetype is enabled in the current directive")
    param_overrides: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Free-form per-archetype parameter overrides. Values typed as object "
            "for strict pyright compliance; closed-set restriction ships post-cutover."
        ),
    )
    valid_from: datetime = Field(description="UTC timestamp from which this directive is valid")
    valid_until: datetime | None = Field(
        default=None,
        description="UTC timestamp after which directive expires; None = no expiry",
    )
    source: str = Field(description="Service that emitted this directive, e.g. 'trading-agent-service-stub'")
    available_at: datetime = Field(description="Write-time UTC timestamp per per-row available_at rule")

    @model_validator(mode="after")
    def _validate_valid_range(self) -> ArchetypeAllocationDirective:
        if self.valid_until is not None and self.valid_from >= self.valid_until:
            msg = f"valid_from ({self.valid_from}) must be before valid_until ({self.valid_until})"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_available_at(self) -> ArchetypeAllocationDirective:
        if self.available_at < self.valid_from:
            msg = f"available_at ({self.available_at}) must be >= valid_from ({self.valid_from})"
            raise ValueError(msg)
        return self
