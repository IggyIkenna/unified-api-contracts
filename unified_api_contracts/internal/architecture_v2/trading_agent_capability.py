"""Trading-agent / LLM capability gap registry — which archetypes permit
agent-driven instruction generation, what models are allowed, and what
parameter-guidance scope the agent has.

STATUS: schema shipped; ``TRADING_AGENT_CAPABILITIES`` is intentionally empty.
The trading-agent-service ↔ strategy registry link is currently absent — this
is a ``missing_registry`` gap. The schema is the forcing function.

``StrategyArchetype`` is REUSED from ``architecture_v2.enums``.
No duplicate definition.

Stage C wizard question: "Decision engine: ML (which models), rules, or
trading-agent LLM over features (which models permitted, what parameter scope)?"

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P2.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field

# StrategyArchetype is the canonical archetype vocabulary in UAC.
# REUSE — do NOT redefine here.
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

# ---------------------------------------------------------------------------
# Trading agent capability model
# ---------------------------------------------------------------------------


class TradingAgentCapability(BaseModel):
    """Per-archetype declaration of trading-agent / LLM instruction generation.

    Describes whether a strategy archetype permits an agent (LLM or rules
    engine) to generate instructions over feature outputs, which model IDs
    are allowed, and what parameters the agent may tune at runtime.

    The ``trading-agent-service`` is the runtime executor; this registry
    declares what the wizard presents as *configurable* for each archetype.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype: StrategyArchetype = Field(
        description=(
            "The strategy archetype this capability entry applies to. "
            "Reuses ``StrategyArchetype`` from ``architecture_v2.enums``."
        )
    )
    allowed_decision_models: list[str] = Field(
        default_factory=list,
        description=(
            "Model identifiers that are permitted to generate instructions "
            "for this archetype. Format: ``'{provider}/{model_id}'`` "
            "(e.g. ``'anthropic/claude-sonnet-4-6'``). "
            "Empty = agent-driven instruction generation is not permitted "
            "for this archetype."
        ),
    )
    parameter_guidance_scope: str = Field(
        default="",
        description=(
            "Free-text description of which strategy parameters the agent "
            "may modify at runtime (e.g. position sizing multipliers, "
            "entry threshold adjustments, hold-time guidance). "
            "Empty = full scope not defined (gap)."
        ),
    )
    enabled: bool = Field(
        description=(
            "True if trading-agent instruction generation is currently "
            "enabled and wired end-to-end for this archetype. "
            "False = declared but not yet operational."
        )
    )


# ---------------------------------------------------------------------------
# Registry — intentionally empty (honest gap, missing_registry)
# ---------------------------------------------------------------------------

#: Per-archetype trading-agent / LLM capability declarations.
#:
#: BACKFILLED 2026-06-13 from a scan of trading-agent-service. The service is
#: currently a STUB: ``core/allocation_directive_loop.py`` emits a NO-OP
#: ``ArchetypeAllocationDirective`` (source="trading-agent-service-stub",
#: docstring line 5/42) for the lead-pair archetypes
#: (``_LEAD_PAIR_ARCHETYPES = ("carry_staked_basis", "arbitrage_price_dispersion")``,
#: line 32) plus ``VOL_TRADING_OPTIONS`` (``_VOL_TRADING_OPTIONS_ARCHETYPE``,
#: line 38). The default decision model is ``claude-haiku-4-5-20251001``
#: (``config.py:156``). It is NOT yet operational end-to-end → every entry is
#: ``enabled=False`` (declared surface, no live agent-driven instruction
#: generation). All other archetypes are honestly absent (no agent surface).
TRADING_AGENT_CAPABILITIES: Final[list[TradingAgentCapability]] = [
    TradingAgentCapability(
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        allowed_decision_models=["anthropic/claude-haiku-4-5-20251001"],
        parameter_guidance_scope=(
            "Allocation-level only: emits ArchetypeAllocationDirective to strategy-service "
            "(no per-instruction generation). Currently a no-op stub."
        ),
        enabled=False,
    ),
    TradingAgentCapability(
        archetype=StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
        allowed_decision_models=["anthropic/claude-haiku-4-5-20251001"],
        parameter_guidance_scope=(
            "Allocation-level only: emits ArchetypeAllocationDirective to strategy-service "
            "(no per-instruction generation). Currently a no-op stub."
        ),
        enabled=False,
    ),
    TradingAgentCapability(
        archetype=StrategyArchetype.VOL_TRADING_OPTIONS,
        allowed_decision_models=["anthropic/claude-haiku-4-5-20251001"],
        parameter_guidance_scope=(
            "Allocation-level only (trading-agent-service allocation_directive_loop.py:38 "
            "_VOL_TRADING_OPTIONS_ARCHETYPE). Currently a no-op stub."
        ),
        enabled=False,
    ),
]


__all__ = [
    "TRADING_AGENT_CAPABILITIES",
    # Re-export for convenience; canonical definition is in enums.py.
    "StrategyArchetype",
    "TradingAgentCapability",
]
