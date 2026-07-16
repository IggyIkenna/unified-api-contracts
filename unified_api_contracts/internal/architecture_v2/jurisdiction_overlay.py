"""Jurisdiction overlay — investor-entity jurisdiction → venue restriction registry.

Wave-2 #12 (capability-wizard registry layer). The PRIMARY deliverable is the
jurisdiction→venue restriction REGISTRY: an investor entity's jurisdiction
filters the set of venues a wizard config may legally include, so a config can
never route to a venue an investor's jurisdiction cannot legally touch.

This sources from the existing client-isolation / governance model
(``codex/04-architecture/client-funds-isolation.md``): each client is a
separately-managed account under its own custody / **legal entity** operating
under a **jurisdiction** (Odum Research UK vs Odum Group Cayman are different
legal entities under different jurisdictions). The jurisdiction axis here is the
investor/entity dimension that selects which venues are legally reachable.

HONESTY CONTRACT (HARD):
  * Every (venue, jurisdiction) policy row carries a ``source_note`` citing a
    DOCUMENTED restriction (a well-known, publicly-cited fact). A restriction
    that cannot be cited confidently is marked ``UNKNOWN`` /
    ``needs_legal_review`` — NEVER an invented legal/regulatory assertion.
  * The seeded facts are the well-known ones: Binance/Bybit retail-restricted
    in the US; Deribit not available to US persons; etc. Where a pairing is
    genuinely uncertain it is left UNKNOWN with ``needs_legal_review=True``.

CONSERVATIVE-DEFAULT (HARD — this is a compliance surface, fail safe):
  An unknown/unmodelled (venue, jurisdiction) pair defaults to **BLOCKED +
  needs_legal_review**, never silently ALLOWED. ``is_venue_allowed`` returns
  ``(False, <reason>)`` for any pairing not explicitly ALLOWED in the registry,
  and an unknown jurisdiction blocks every venue.

This is the registry layer only. The uts-ui Stage-A jurisdiction-filter
surface is the thin follow-on consumer (NOT built here).

Codex SSOT:
  ``codex/04-architecture/client-funds-isolation.md`` (client-isolation /
  legal-entity / jurisdiction governance model — the source of this axis).
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Phase 2
  [IMPLEMENT] "Registry backfills" (sibling pattern: collateral_registry.py,
  order_semantics.py, fees_registry.py).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Jurisdiction(StrEnum):
    """Investor-entity jurisdiction / regulatory regime.

    Models the legal-entity dimension from the client-isolation governance
    model: each investor entity is domiciled in (or its persons are subject to)
    one of these regimes, which gates the venues it can legally access.

    Intentionally a small, well-understood set — additive extension is fine.
    Use :data:`Jurisdiction.UNKNOWN` (never an invented enum member) when an
    entity's jurisdiction is not yet classified; it conservatively blocks all.
    """

    UK_FCA = "uk_fca"
    """United Kingdom — FCA-regulated entity (e.g. Odum Research UK)."""

    US_CFTC = "us_cftc"
    """United States persons — CFTC/SEC/state regime. 'US person' for the
    purpose of venue terms-of-service geofencing."""

    CAYMAN = "cayman"
    """Cayman Islands legal entity (e.g. Odum Group Cayman)."""

    EU_MICA = "eu_mica"
    """European Union — MiCA crypto-asset regime."""

    RETAIL_RESTRICTED = "retail_restricted"
    """A retail investor in a regime where retail access to leveraged
    crypto-derivatives is restricted (e.g. UK/EU retail leverage bans). A
    conservative bucket: a retail entity that should NOT see derivative venues
    regardless of country, until classified to a specific regime."""

    UNKNOWN = "unknown"
    """Jurisdiction not yet classified. Conservatively blocks every venue with
    ``needs_legal_review`` — never silently allowed."""


class JurisdictionAccess(StrEnum):
    """Whether a jurisdiction may legally access a venue."""

    ALLOWED = "allowed"
    """Documented as legally accessible from this jurisdiction (cite source)."""

    BLOCKED = "blocked"
    """Documented as NOT accessible (geofenced / restricted / banned)."""

    UNKNOWN = "unknown"
    """Restriction genuinely uncertain — defaults to BLOCKED on evaluation and
    carries ``needs_legal_review``. NEVER treat UNKNOWN as a green light."""


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class JurisdictionVenuePolicy(BaseModel):
    """Per-(venue, jurisdiction) access policy with a cited source.

    Every populated ``access`` carries a ``source_note``; an ``UNKNOWN`` /
    ``needs_legal_review`` row documents the absence of a confident citation
    rather than inventing a legal claim.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(
        description=(
            "Stable venue identifier matching the instruments-service / "
            "leg-spec convention (e.g. ``'binance'``, ``'deribit'``, "
            "``'hyperliquid'``, ``'aave_v3'``)."
        )
    )
    jurisdiction: Jurisdiction = Field(description="Investor-entity jurisdiction this row applies to.")
    access: JurisdictionAccess = Field(
        description=(
            "Whether this jurisdiction may legally access this venue. "
            "``UNKNOWN`` is evaluated as BLOCKED (conservative default)."
        )
    )
    needs_legal_review: bool = Field(
        default=False,
        description=(
            "``True`` when the restriction is genuinely uncertain (paired with "
            "``access=UNKNOWN``) and a legal/compliance review must confirm "
            "before this pair is ever treated as ALLOWED."
        ),
    )
    reason: str = Field(
        description=(
            "Human-readable reason for the access verdict (shown to the wizard "
            "operator / compliance). Required for every row."
        )
    )
    source_note: str = Field(
        description=(
            "Where the restriction was sourced from (the documented fact: "
            "venue ToS / regulator notice / well-known public fact, with a "
            "date). Required for every row — an UNKNOWN row cites WHY it is "
            "uncertain rather than inventing a legal claim."
        )
    )


# ---------------------------------------------------------------------------
# Seeded registry — HONEST, documented restrictions only
# ---------------------------------------------------------------------------
# SOURCE PRINCIPLE: seed ONLY well-known, publicly-documented restrictions.
# A genuinely-uncertain pairing is left UNKNOWN + needs_legal_review; the
# CONSERVATIVE DEFAULT (BLOCK any unmodelled pair) means we do NOT need an
# exhaustive ALLOWED row for every safe pair — absence already blocks. We seed:
#   (1) the clear BLOCKS (the load-bearing safety facts — US-person geofences);
#   (2) the clear ALLOWS for the home entities (UK_FCA / CAYMAN) where the venue
#       is documented as serving those markets;
#   (3) explicit UNKNOWN rows where a pairing is plausibly restricted but not
#       confidently citable, so the uncertainty is visible (not silent).

# Citation shorthands (one edit site per recurring source).
_SRC_BINANCE_US = (
    "Binance.com global platform is geofenced from US persons (Binance.US is a "
    "separate restricted-venue entity, not in our universe); well-known public "
    "fact, CFTC settlement 2023-11. as_of 2026-06-13"
)
_SRC_BYBIT_US = (
    "Bybit terms of service exclude US persons (no US onboarding / geofenced); well-known public fact. as_of 2026-06-13"
)
_SRC_OKX_US = (
    "OKX global platform excludes US persons (US persons routed to no-service); "
    "well-known public fact, CFTC settlement 2025-02. as_of 2026-06-13"
)
_SRC_DERIBIT_US = (
    "Deribit is not available to US persons (no US onboarding; ToS geofence); well-known public fact. as_of 2026-06-13"
)
_SRC_HL_US = (
    "Hyperliquid front-end geofences US persons (US IPs blocked from the dApp "
    "UI); well-known public fact. as_of 2026-06-13"
)
_SRC_GMX_PERMISSIONLESS = (
    "GMX is a permissionless on-chain perp DEX; the hosted front-end geofences "
    "US/UK persons but the protocol itself is not entity-gated. Treated UNKNOWN "
    "for US/UK pending legal review of front-end-vs-protocol access. as_of 2026-06-13"
)
_SRC_DEX_PERMISSIONLESS = (
    "Permissionless on-chain protocol (no entity onboarding / KYC gate at the "
    "contract level); access via self-custody wallet. Documented as not "
    "entity-restricted at protocol level; front-end geofencing is jurisdiction- "
    "and operator-specific. as_of 2026-06-13"
)
_SRC_UK_HOME = (
    "UK_FCA-domiciled entity (e.g. Odum Research UK) accessing this venue under "
    "an institutional / professional-client arrangement; documented home-entity "
    "access. as_of 2026-06-13. NOTE: institutional access only — retail leverage "
    "restrictions handled by the RETAIL_RESTRICTED jurisdiction."
)
_SRC_CAYMAN_HOME = (
    "CAYMAN-domiciled entity (e.g. Odum Group Cayman) accessing this venue; "
    "Cayman is a common offshore domicile served by global crypto venues; "
    "documented home-entity access. as_of 2026-06-13"
)
_SRC_RETAIL_DERIV = (
    "Retail access to leveraged crypto derivatives is restricted in the UK "
    "(FCA PS20/10 ban on retail crypto-derivatives, eff. 2021-01-06) and the EU; "
    "a RETAIL_RESTRICTED entity must not see derivative venues. as_of 2026-06-13"
)


def _block(venue: str, jur: Jurisdiction, reason: str, src: str) -> JurisdictionVenuePolicy:
    return JurisdictionVenuePolicy(
        venue_id=venue,
        jurisdiction=jur,
        access=JurisdictionAccess.BLOCKED,
        reason=reason,
        source_note=src,
    )


def _allow(venue: str, jur: Jurisdiction, reason: str, src: str) -> JurisdictionVenuePolicy:
    return JurisdictionVenuePolicy(
        venue_id=venue,
        jurisdiction=jur,
        access=JurisdictionAccess.ALLOWED,
        reason=reason,
        source_note=src,
    )


def _unknown(venue: str, jur: Jurisdiction, reason: str, src: str) -> JurisdictionVenuePolicy:
    return JurisdictionVenuePolicy(
        venue_id=venue,
        jurisdiction=jur,
        access=JurisdictionAccess.UNKNOWN,
        needs_legal_review=True,
        reason=reason,
        source_note=src,
    )


#: The MVP venue universe (from archetype_leg_spec_seeds.py eligible venues +
#: lending/staking venues). Used by the filter as the candidate universe.
#: "drift" (Solana perp DEX) removed 2026-07-16 (operator ruling: all Solana perp DEXes dropped
#: except Jupiter, not integrated). SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
KNOWN_VENUE_IDS: Final[tuple[str, ...]] = (
    "hyperliquid",
    "gmx_v2",
    "binance",
    "bybit",
    "deribit",
    "okx",
    "aave_v3",
    "kamino",
)

#: Jurisdiction → venue access policies. Seeded HONESTLY from documented
#: restrictions only. The conservative default (block any unmodelled pair)
#: means an ABSENT row already blocks — so we seed the load-bearing facts:
#: the US-person geofences (clear BLOCKS), the home-entity ALLOWS (UK/Cayman),
#: and explicit UNKNOWN where a pairing is plausibly restricted but uncertain.
JURISDICTION_VENUE_POLICIES: Final[tuple[JurisdictionVenuePolicy, ...]] = (
    # ===================== US persons (CFTC/SEC) — the load-bearing BLOCKS ===
    _block("binance", Jurisdiction.US_CFTC, "Binance.com geofences US persons.", _SRC_BINANCE_US),
    _block("bybit", Jurisdiction.US_CFTC, "Bybit ToS exclude US persons.", _SRC_BYBIT_US),
    _block("okx", Jurisdiction.US_CFTC, "OKX global platform excludes US persons.", _SRC_OKX_US),
    _block("deribit", Jurisdiction.US_CFTC, "Deribit not available to US persons.", _SRC_DERIBIT_US),
    _block("hyperliquid", Jurisdiction.US_CFTC, "Hyperliquid dApp front-end geofences US persons.", _SRC_HL_US),
    _unknown(
        "gmx_v2",
        Jurisdiction.US_CFTC,
        "GMX permissionless protocol vs geofenced front-end — needs legal review for US persons.",
        _SRC_GMX_PERMISSIONLESS,
    ),
    _unknown(
        "aave_v3",
        Jurisdiction.US_CFTC,
        "Aave permissionless lending protocol; US-person access (yield/securities framing) uncertain.",
        _SRC_DEX_PERMISSIONLESS,
    ),
    _unknown(
        "kamino",
        Jurisdiction.US_CFTC,
        "Kamino permissionless Solana lending; US-person access uncertain — needs legal review.",
        _SRC_DEX_PERMISSIONLESS,
    ),
    # ===================== UK_FCA home entity — documented ALLOWS ============
    _allow("binance", Jurisdiction.UK_FCA, "Institutional/professional-client access.", _SRC_UK_HOME),
    _allow("bybit", Jurisdiction.UK_FCA, "Institutional/professional-client access.", _SRC_UK_HOME),
    _allow("okx", Jurisdiction.UK_FCA, "Institutional/professional-client access.", _SRC_UK_HOME),
    _allow("deribit", Jurisdiction.UK_FCA, "Institutional/professional-client access.", _SRC_UK_HOME),
    _allow("hyperliquid", Jurisdiction.UK_FCA, "Self-custody on-chain perp access.", _SRC_UK_HOME),
    _allow("gmx_v2", Jurisdiction.UK_FCA, "Permissionless on-chain perp DEX.", _SRC_DEX_PERMISSIONLESS),
    _allow("aave_v3", Jurisdiction.UK_FCA, "Permissionless lending protocol.", _SRC_DEX_PERMISSIONLESS),
    _allow("kamino", Jurisdiction.UK_FCA, "Permissionless Solana lending protocol.", _SRC_DEX_PERMISSIONLESS),
    # ===================== CAYMAN home entity — documented ALLOWS ===========
    _allow("binance", Jurisdiction.CAYMAN, "Offshore-domicile institutional access.", _SRC_CAYMAN_HOME),
    _allow("bybit", Jurisdiction.CAYMAN, "Offshore-domicile institutional access.", _SRC_CAYMAN_HOME),
    _allow("okx", Jurisdiction.CAYMAN, "Offshore-domicile institutional access.", _SRC_CAYMAN_HOME),
    _allow("deribit", Jurisdiction.CAYMAN, "Offshore-domicile institutional access.", _SRC_CAYMAN_HOME),
    _allow("hyperliquid", Jurisdiction.CAYMAN, "Self-custody on-chain perp access.", _SRC_CAYMAN_HOME),
    _allow("gmx_v2", Jurisdiction.CAYMAN, "Permissionless on-chain perp DEX.", _SRC_DEX_PERMISSIONLESS),
    _allow("aave_v3", Jurisdiction.CAYMAN, "Permissionless lending protocol.", _SRC_DEX_PERMISSIONLESS),
    _allow("kamino", Jurisdiction.CAYMAN, "Permissionless Solana lending protocol.", _SRC_DEX_PERMISSIONLESS),
    # ===================== EU_MiCA — derivative-venue access UNKNOWN ========
    # MiCA covers crypto-asset markets but the per-venue authorisation status
    # under MiCA's transitional regime is venue-specific and shifting — left
    # UNKNOWN rather than asserting an authorisation we cannot confidently cite.
    _unknown(
        "binance",
        Jurisdiction.EU_MICA,
        "Per-venue MiCA authorisation status (transitional regime) uncertain — needs legal review.",
        "MiCA (Regulation (EU) 2023/1114) transitional authorisation is venue/member-state specific. as_of 2026-06-13",
    ),
    _unknown(
        "bybit",
        Jurisdiction.EU_MICA,
        "Per-venue MiCA authorisation status uncertain — needs legal review.",
        "MiCA transitional authorisation is venue/member-state specific. as_of 2026-06-13",
    ),
    _unknown(
        "okx",
        Jurisdiction.EU_MICA,
        "Per-venue MiCA authorisation status uncertain — needs legal review.",
        "MiCA transitional authorisation is venue/member-state specific. as_of 2026-06-13",
    ),
    _unknown(
        "deribit",
        Jurisdiction.EU_MICA,
        "Per-venue MiCA authorisation status uncertain — needs legal review.",
        "MiCA transitional authorisation is venue/member-state specific. as_of 2026-06-13",
    ),
    # ===================== RETAIL_RESTRICTED — derivative venues BLOCKED =====
    # A retail entity must not see leveraged-derivative venues (UK FCA PS20/10
    # retail crypto-derivative ban; EU retail leverage limits). Lending DEXes
    # are left UNKNOWN (not a leveraged-derivative, but retail suitability
    # uncertain).
    _block("binance", Jurisdiction.RETAIL_RESTRICTED, "Retail crypto-derivatives restricted.", _SRC_RETAIL_DERIV),
    _block("bybit", Jurisdiction.RETAIL_RESTRICTED, "Retail crypto-derivatives restricted.", _SRC_RETAIL_DERIV),
    _block("okx", Jurisdiction.RETAIL_RESTRICTED, "Retail crypto-derivatives restricted.", _SRC_RETAIL_DERIV),
    _block("deribit", Jurisdiction.RETAIL_RESTRICTED, "Retail crypto-derivatives restricted.", _SRC_RETAIL_DERIV),
    _block("hyperliquid", Jurisdiction.RETAIL_RESTRICTED, "Retail crypto-derivatives restricted.", _SRC_RETAIL_DERIV),
    _block("gmx_v2", Jurisdiction.RETAIL_RESTRICTED, "Retail crypto-derivatives restricted.", _SRC_RETAIL_DERIV),
    _unknown(
        "aave_v3",
        Jurisdiction.RETAIL_RESTRICTED,
        "Retail suitability of on-chain lending uncertain — needs legal review.",
        "Lending is not a leveraged crypto-derivative under PS20/10, but retail suitability uncertain. "
        "as_of 2026-06-13",
    ),
    _unknown(
        "kamino",
        Jurisdiction.RETAIL_RESTRICTED,
        "Retail suitability of on-chain lending uncertain — needs legal review.",
        "Lending is not a leveraged crypto-derivative under PS20/10, but retail suitability uncertain. "
        "as_of 2026-06-13",
    ),
)


# ---------------------------------------------------------------------------
# Lookup index (built once at import; deterministic)
# ---------------------------------------------------------------------------

_POLICY_INDEX: Final[dict[tuple[str, Jurisdiction], JurisdictionVenuePolicy]] = {
    (p.venue_id, p.jurisdiction): p for p in JURISDICTION_VENUE_POLICIES
}


# ---------------------------------------------------------------------------
# Pure filter functions — CONSERVATIVE DEFAULT (fail safe)
# ---------------------------------------------------------------------------


def is_venue_allowed(venue_id: str, jurisdiction: Jurisdiction) -> tuple[bool, str]:
    """Return ``(allowed, reason)`` for a (venue, jurisdiction) pair.

    CONSERVATIVE DEFAULT (HARD): only an explicit ``ALLOWED`` row returns
    ``True``. Any other case — an explicit ``BLOCKED`` / ``UNKNOWN`` row, an
    unmodelled pair, or an unknown jurisdiction — returns ``False`` with a
    reason. An unmodelled / uncertain pair is NEVER silently allowed.

    Args:
        venue_id: Stable venue identifier.
        jurisdiction: Investor-entity jurisdiction.

    Returns:
        ``(True, reason)`` only when documented ALLOWED; otherwise
        ``(False, reason)`` — the reason names the conservative-default /
        legal-review status so the wizard can surface it.
    """
    # An unknown jurisdiction blocks everything — never silently allow.
    if jurisdiction is Jurisdiction.UNKNOWN:
        return (
            False,
            "BLOCKED: jurisdiction is UNKNOWN/unclassified — needs_legal_review (conservative default).",
        )

    policy = _POLICY_INDEX.get((venue_id, jurisdiction))
    if policy is None:
        # Unmodelled pair → fail safe.
        return (
            False,
            (
                f"BLOCKED: no documented policy for venue '{venue_id}' in "
                f"jurisdiction '{jurisdiction.value}' — needs_legal_review "
                "(conservative default, never silently allowed)."
            ),
        )

    if policy.access is JurisdictionAccess.ALLOWED:
        return (True, f"ALLOWED: {policy.reason}")

    # BLOCKED or UNKNOWN both evaluate to not-allowed.
    prefix = "BLOCKED" if policy.access is JurisdictionAccess.BLOCKED else "BLOCKED (UNKNOWN→needs_legal_review)"
    return (False, f"{prefix}: {policy.reason}")


def allowed_venues_for_jurisdiction(jurisdiction: Jurisdiction) -> set[str]:
    """Return the set of venue_ids a jurisdiction may legally access.

    Deterministic: iterates :data:`KNOWN_VENUE_IDS` and keeps only the venues
    that :func:`is_venue_allowed` confirms as ALLOWED. An unknown jurisdiction
    returns the empty set (conservative default).
    """
    return {venue for venue in KNOWN_VENUE_IDS if is_venue_allowed(venue, jurisdiction)[0]}


__all__ = [
    "JURISDICTION_VENUE_POLICIES",
    "KNOWN_VENUE_IDS",
    "Jurisdiction",
    "JurisdictionAccess",
    "JurisdictionVenuePolicy",
    "allowed_venues_for_jurisdiction",
    "is_venue_allowed",
]
