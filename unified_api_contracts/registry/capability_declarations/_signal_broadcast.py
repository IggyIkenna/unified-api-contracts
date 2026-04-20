"""Signal-broadcast (signal-leasing) capability declaration.

Unlike the per-venue declarations in ``_cefi.py`` / ``_defi.py`` /
``_sports.py`` / etc., signal-broadcast is a *domain-level* capability —
not sourced from an external venue, but from strategy-service's
emitted-signal pipeline. The declaration records the supported schema
depths, the max counterparty count per environment, and the rate-limit
bounds enforced at the emitter.

SSOT: ``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import SchemaDepth

__all__ = [
    "SIGNAL_BROADCAST_CAPABILITIES",
    "SIGNAL_BROADCAST_CAPABILITY_TAGS",
    "SignalBroadcastCapability",
]


# Capability tags — consumed by registry-driven discovery tooling.
SIGNAL_BROADCAST_CAPABILITY_TAGS: tuple[str, ...] = (
    "signal_broadcast",
    "external_counterparty_emission",
)


class SignalBroadcastCapability(BaseModel):
    """Signal-leasing emitter capability record.

    Declares operator-enforced bounds at the emitter layer. Not a
    per-venue capability — this is the strategy-service → counterparty
    channel, not a raw-data source.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    module: str = "signal_broadcast"
    supported_schema_depths: tuple[SchemaDepth, ...] = Field(
        default=(SchemaDepth.MINIMAL, SchemaDepth.STANDARD, SchemaDepth.RICH)
    )
    max_counterparties: int = Field(default=100, ge=1)
    rate_limit_min_per_strategy_per_sec: int = Field(default=1, ge=1)
    rate_limit_max_per_strategy_per_sec: int = Field(default=100, ge=1)
    tags: tuple[str, ...] = Field(default=SIGNAL_BROADCAST_CAPABILITY_TAGS)


SIGNAL_BROADCAST_CAPABILITIES: SignalBroadcastCapability = SignalBroadcastCapability()
