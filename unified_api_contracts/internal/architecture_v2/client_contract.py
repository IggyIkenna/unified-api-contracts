"""ClientContract schema — Firestore ``/contracts/{org_id}`` document shape.

Stage 3E G2 § 2. Contracts live in Firestore (prod + staging Firebase
projects; IDs resolved at runtime via ``UnifiedCloudConfig``, never
hardcoded) and drive ``cost()`` discounts, Tier A usage-metered
pricing, and rule-08 exclusivity enforcement.

UAC owns the Python schema (pydantic BaseModel); the TypeScript mirror
in unified-trading-system-ui is generated from this file at build
time, identical to the pattern used for restriction profiles
(Stage 3E G1.7) and archetype capability (G1.8).

SSOT: codex/16-strategy-playbooks/infra-spec/stage-3e-g2-env-split.md § 2.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.derivation import (
    ClientAudience,
    CommercialPath,
    IntegrationDepth,
    PricingTier,
)


class ClientContract(BaseModel):
    """One contracted pricing package tied to a client org.

    Stored in Firestore under ``/contracts/{org_id}``. Read access is
    admin + im_desk for every contract; org-scoped readers see only
    their own document (enforced by Firestore security rules — see
    ``unified-trading-system-ui/firestore.rules``).

    ``pricing_overrides`` is a free-form string-keyed dict for bespoke
    deals — e.g. {"block_1_reporting_core": "0", "discount_percent": "15"}.
    Keys are interpreted by ``cost()``'s discount_if_applicable stub
    (still shape-only as of G2). Production use requires finance
    sign-off per pricing-building-blocks.md.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    org_id: str
    audience: ClientAudience
    commercial_path: CommercialPath
    tier: PricingTier
    integration_depth: IntegrationDepth | None = None
    has_exclusivity: bool = False
    effective_from: str  # ISO-8601 date
    effective_to: str | None = None  # ISO-8601 date; None = open-ended
    contract_version: str  # semver-ish, e.g. "2026-04.v1"
    signed_by: str  # admin email that provisioned the contract
    pricing_overrides: dict[str, str] = {}


__all__ = [
    "ClientContract",
]
