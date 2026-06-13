"""Fund-structure gap registry — what pooled/SMA/prop structures are offerable.

STATUS: schema shipped; ``OFFERED_FUND_STRUCTURES`` is intentionally empty.
The fund-administration-service state machines (subscription/redemption cadence
rules) are the runtime SSOT; this registry declares what is *offerable* to
the wizard — a separate, currently-unregistered surface.

``ShareClass`` is REUSED from ``architecture_v2.enums`` (USDC/ETH/SOL/BTC/etc.).
No duplicate definition.

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
  ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P1.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

# ShareClass is the canonical share-class vocabulary already defined in
# architecture_v2.enums. REUSE — do NOT redefine here (that would be the
# exact dual-implementation antipattern this project hunts).
from unified_api_contracts.internal.architecture_v2.enums import ShareClass

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FundStructureKind(StrEnum):
    """Broad fund-structure categories.

    Determines subscription/redemption mechanics, segregation model, and
    capital routing rules.
    """

    POOLED = "pooled"
    """Multiple investors share one pool; NAV-per-unit accounting."""

    SMA = "sma"
    """Separately managed account — one investor, segregated capital."""

    PROP = "prop"
    """Proprietary capital; no external investor redemption pathway."""


class CadenceKind(StrEnum):
    """Subscription or redemption cadence options.

    The fund-administration state machines enforce these at runtime.
    The wizard uses these to filter structures to those compatible with
    the investor's liquidity requirements (Stage A question).
    """

    DAILY = "daily"
    """Daily subscription or redemption window."""

    WEEKLY = "weekly"
    """Weekly subscription or redemption window."""

    MONTHLY = "monthly"
    """Monthly subscription or redemption window."""

    ON_DEMAND = "on_demand"
    """Immediate / on-request with no fixed window."""


# ---------------------------------------------------------------------------
# Fund structure offering model
# ---------------------------------------------------------------------------


class FundStructureOffering(BaseModel):
    """An offerable fund-structure configuration.

    Describes what the system can offer to investors at configuration time.
    The fund-administration-service state machines remain the runtime truth;
    this declares the *schema* of what is configurable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: FundStructureKind = Field(description="Broad fund-structure category (pooled / SMA / prop).")
    share_classes: list[ShareClass] = Field(
        default_factory=list,
        description=(
            "Share classes this structure supports for investor accounting. "
            "Reuses ``ShareClass`` from ``architecture_v2.enums`` "
            "(USDC/ETH/SOL/BTC/etc.). "
            "Source: ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``."
        ),
    )
    subscription_cadence: list[CadenceKind] = Field(
        default_factory=list,
        description=(
            "Supported subscription (deposit) cadences. ``[CadenceKind.ON_DEMAND]`` = daily deposit supported."
        ),
    )
    redemption_cadence: list[CadenceKind] = Field(
        default_factory=list,
        description=(
            "Supported redemption (withdrawal) cadences. ``[CadenceKind.ON_DEMAND]`` = daily withdrawal supported."
        ),
    )
    rebalance_cadence: list[CadenceKind] = Field(
        default_factory=list,
        description=("Supported rebalance cadences (how often capital is reallocated across strategies / wallets)."),
    )
    supports_daily_withdraw_deposit: bool = Field(
        description=(
            "True if this structure supports same-day deposit AND withdrawal "
            "(i.e. both ``subscription_cadence`` and ``redemption_cadence`` "
            "include ``CadenceKind.ON_DEMAND`` or ``CadenceKind.DAILY``). "
            "Surfaced prominently in the wizard because it constrains strategy "
            "liquidity profiles."
        )
    )
    notes: str = Field(
        default="",
        description=(
            "Free-text operational notes on this offering "
            "(e.g. lock-up periods, minimum ticket, jurisdiction restrictions)."
        ),
    )


# ---------------------------------------------------------------------------
# Registry — backfilled 2026-06-13 from the SMA-vs-Pooled codex SSOT
# ---------------------------------------------------------------------------
#
# Source: codex/14-customer-journeys/playbook-concepts/sma-vs-pooled.md +
# fund-org-hierarchy.md (the documented structural decision: org → Pooled/SMA →
# funds → clients). POOLED + SMA are the two documented offerable structures.
# PROP (proprietary own-capital) is NOT a documented external offering today →
# honestly omitted (not invented). The codex does NOT constrain subscription/
# redemption/rebalance cadence at the STRUCTURE level (cadence is a per-fund
# configuration), so the cadence lists are left empty here rather than invent
# values; supports_daily_withdraw_deposit is conservatively False (no
# structure-level same-day-liquidity guarantee is documented).
OFFERED_FUND_STRUCTURES: Final[list[FundStructureOffering]] = [
    FundStructureOffering(
        kind=FundStructureKind.POOLED,
        share_classes=list(ShareClass),
        subscription_cadence=[],
        redemption_cadence=[],
        rebalance_cadence=[],
        supports_daily_withdraw_deposit=False,
        notes=(
            "One fund holds multiple clients; each client is a SHARE CLASS with per-share-class NAV via the allocation "
            "engine (one set of positions / market-data feed / API keys). Source: sma-vs-pooled.md. Subscription/"
            "redemption/rebalance cadence is per-fund configuration, not constrained at the structure level."
        ),
    ),
    FundStructureOffering(
        kind=FundStructureKind.SMA,
        share_classes=list(ShareClass),
        subscription_cadence=[],
        redemption_cadence=[],
        rebalance_cadence=[],
        supports_daily_withdraw_deposit=False,
        notes=(
            "Separately Managed Account — each client has their OWN fund running independently (per-client positions / "
            "API keys / NAV = actual P&L; no allocation engine). HNW/institutional, bespoke mandate, per-client "
            "regulatory reporting. Source: sma-vs-pooled.md. Cadence is per-fund configuration."
        ),
    ),
]


__all__ = [
    "OFFERED_FUND_STRUCTURES",
    "CadenceKind",
    "FundStructureKind",
    "FundStructureOffering",
    # Re-export for convenience; canonical definition is in enums.py.
    "ShareClass",
]
