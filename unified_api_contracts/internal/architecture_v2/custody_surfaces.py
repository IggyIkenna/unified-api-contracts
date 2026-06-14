"""Custody / signing-surface registry — the real transaction-signing surfaces
the system offers, sourced from documented custody decisions (NOT invented).

STATUS (2026-06-13): seeds ``OFFERED_SIGNING_SURFACES`` for the documented
production signing surfaces, re-using the EXISTING UAC ``SigningSurface`` enum
(``internal/domain/defi/wallet_config.py``) as the surface identity — this
module NEVER redefines that enum. Each entry carries a ``status`` (May-23
active / June-1 active / out-of-scope) and a ``source_note`` citing
``custody-providers.md``. This is the F49 re-kind source: the capability
exporter (Wave B) reads this registry to populate ``signing_surface`` nodes
instead of abusing ``custody_provider`` as a catch-all.

SOURCING (per ``codex/04-architecture/custody-providers.md``, verified
2026-06-13 — NEVER invent a surface or a status):
  - ``CLOUD_KMS_ENCRYPTED`` — § R9 RESOLVED: **May-23 cutover ships on
    CLOUD_KMS_ENCRYPTED** (HSM-backed CMK envelope encryption);
    ``CloudKmsCustodyProvider`` SHIPPED. → ``active_may23``.
  - ``COPPER_MPC`` — § R9: **June-1 flips per-wallet to COPPER_MPC / CEFFU**
    on POD-provided creds; ``CopperCustodyProvider`` is the production MPC
    provider for DeFi (every chain) + non-Binance CeFi. → ``active_june1``.
  - ``FIREBLOCKS_MPC`` — § "POD client scope": **Fireblocks is OUT OF SCOPE
    per POD stack choice** (POD uses Copper + CEFFU only); the enum member
    stays for future-flexibility but is NOT a May-23 / June-1 target.
    → ``out_of_scope``.

NOT seeded (documented honestly, never silently dropped):
  - ``LOCAL_KEY`` / ``MOCK`` — dev/testnet-only signing surfaces (§ 2.1 / 2.2);
    not production-offered, so excluded from the OFFERED registry by design.
  - **CEFFU** — a June-1 custody provider (§ 2.4) but it is NOT a member of
    the ``SigningSurface`` enum: the factory routes CEFFU's signing **via
    Copper** (§ 1 factory table: CEFFU row "routes via Copper; CEFFU stub-
    only"), so there is no distinct CEFFU signing surface to seed without
    inventing an enum member. See ``CEFFU_ROUTES_VIA_COPPER_NOTE``.

Codex SSOT:
  ``codex/04-architecture/custody-providers.md``
Plan:
  ``plans/active/issues/capability_wizard_analysis_findings_2026_06_11.md``
  Wave A (F49 — exporter abuses ``custody_provider`` as a catch-all).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.domain.defi.wallet_config import SigningSurface

# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class SigningSurfaceStatus(StrEnum):
    """Rollout status of an offered signing surface.

    Closed set sourced from ``custody-providers.md`` § R9 + § "POD client
    scope":

    - ``active_may23``   → live for the May-23 cutover (CLOUD_KMS_ENCRYPTED).
    - ``active_june1``   → flips on per-wallet from June-1 (COPPER_MPC).
    - ``out_of_scope``   → enum member retained for future flexibility but NOT
      a May-23 / June-1 target (FIREBLOCKS_MPC, per POD stack choice).
    """

    ACTIVE_MAY23 = "active_may23"
    ACTIVE_JUNE1 = "active_june1"
    OUT_OF_SCOPE = "out_of_scope"


# ---------------------------------------------------------------------------
# Policy schema — frozen, extra=forbid, no Any; REUSES SigningSurface
# ---------------------------------------------------------------------------


class SigningSurfacePolicy(BaseModel):
    """Rollout + scope policy for a single signing surface.

    The ``surface`` field REUSES the existing UAC ``SigningSurface`` enum
    (imported, never redefined) so this registry stays the single source of
    surface identity. Every entry cites ``custody-providers.md`` in
    ``source_note`` — NEVER an invented surface or status.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface: SigningSurface = Field(
        description=(
            "The signing surface this policy describes. REUSES the existing "
            "``SigningSurface`` enum (``internal/domain/defi/wallet_config.py``)."
        )
    )
    status: SigningSurfaceStatus = Field(
        description=(
            "Rollout status: ``active_may23`` (May-23 cutover default) | "
            "``active_june1`` (per-wallet flip from June-1) | ``out_of_scope``."
        )
    )
    asset_groups: tuple[str, ...] = Field(
        description=(
            "Asset groups this surface signs for "
            "(``'defi'`` / ``'cefi'`` / ``'tradfi'`` / ``'sports'`` / "
            "``'prediction'``). Empty tuple = not yet scoped to any group."
        )
    )
    source_note: str = Field(
        description=(
            "Where the status + scope were sourced from (``custody-providers.md`` section + date). Required, non-empty."
        )
    )


# ---------------------------------------------------------------------------
# Seeded registry — documented surfaces only, each cited
# ---------------------------------------------------------------------------

# Citation shorthand (one edit site per source section).
_SRC_CUSTODY_DOC = "codex/04-architecture/custody-providers.md"
_SRC_R9 = f"{_SRC_CUSTODY_DOC} § R9 RESOLVED 2026-05-12 (as_of 2026-06-13)"
_SRC_POD = f"{_SRC_CUSTODY_DOC} § 'POD client scope clarified 2026-05-12' (as_of 2026-06-13)"

#: The real signing surfaces the system OFFERS, each citing custody-providers.md.
#: Surfaces re-use the existing ``SigningSurface`` enum (no duplicate enum).
#: Dev/test surfaces (LOCAL_KEY / MOCK) and CEFFU (routes via Copper — no
#: distinct enum member) are deliberately excluded; see the module docstring.
OFFERED_SIGNING_SURFACES: Final[list[SigningSurfacePolicy]] = [
    SigningSurfacePolicy(
        surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        status=SigningSurfaceStatus.ACTIVE_MAY23,
        asset_groups=("defi",),
        source_note=(
            f"{_SRC_R9}: May-23 cutover ships on CLOUD_KMS_ENCRYPTED "
            "(HSM-backed CMK envelope encryption); CloudKmsCustodyProvider "
            "SHIPPED (execution-service@d45d24b4). Default DeFi signing surface."
        ),
    ),
    SigningSurfacePolicy(
        surface=SigningSurface.COPPER_MPC,
        status=SigningSurfaceStatus.ACTIVE_JUNE1,
        asset_groups=("defi", "cefi"),
        source_note=(
            f"{_SRC_R9}: June-1 flips per-wallet to COPPER_MPC on POD-provided "
            "creds. CopperCustodyProvider covers DeFi (every chain) + "
            "non-Binance CeFi (Bybit/OKX/Deribit/Kraken/Aster/Hyperliquid)."
        ),
    ),
    SigningSurfacePolicy(
        surface=SigningSurface.FIREBLOCKS_MPC,
        status=SigningSurfaceStatus.OUT_OF_SCOPE,
        asset_groups=(),
        source_note=(
            f"{_SRC_POD}: Fireblocks is OUT OF SCOPE per POD stack choice "
            "(POD uses Copper + CEFFU only). SigningSurface.FIREBLOCKS_MPC "
            "stays in the UAC enum for future flexibility but is NOT a "
            "May-23 / June-1 target."
        ),
    ),
]

#: Why CEFFU is not an OFFERED_SIGNING_SURFACES entry: it is a June-1 custody
#: provider (§ 2.4) but has NO ``SigningSurface`` enum member — the factory
#: routes CEFFU's signing via Copper (§ 1 factory table). Seeding it would
#: require inventing an enum value, which the NEVER-invent rule forbids.
CEFFU_ROUTES_VIA_COPPER_NOTE: Final[str] = (
    "CEFFU (June-1 Binance institutional custody, custody-providers.md § 2.4) "
    "has no distinct SigningSurface enum member — § 1 factory table routes it "
    "via Copper (CEFFU stub-only). No invented surface is seeded for it."
)


def surface_policy_for(surface: SigningSurface) -> SigningSurfacePolicy | None:
    """Return the offered policy for ``surface``, or ``None`` if not offered.

    ``None`` is the honest answer for LOCAL_KEY / MOCK (dev/test, not offered).
    """
    return next((p for p in OFFERED_SIGNING_SURFACES if p.surface == surface), None)


__all__ = [
    "CEFFU_ROUTES_VIA_COPPER_NOTE",
    "OFFERED_SIGNING_SURFACES",
    "SigningSurface",
    "SigningSurfacePolicy",
    "SigningSurfaceStatus",
    "surface_policy_for",
]
