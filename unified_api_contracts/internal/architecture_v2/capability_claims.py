"""Firebase custom-claims schema for caller capability gates.

Stage 3E G2 § 4. Canonical shape of the custom claims set on every
Firebase Auth user by the ``setCapabilityClaim`` admin Cloud Function.
Claims are propagated in the ID token and read by:

1. Firestore security rules (``unified-trading-system-ui/firestore.rules``).
2. Python service middleware via ``access_control()`` (strategy-
   service / execution-service / deployment-api).
3. UAC ``cost()`` via the ``caller_has_internal_read`` + audience
   kwargs — callers translate claims → cost() args.

SSOT: codex/16-strategy-playbooks/infra-spec/stage-3e-g2-env-split.md § 4.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.derivation import (
    ClientAudience,
)


class CapabilityClaims(BaseModel):
    """Odum-specific custom-claims payload set on every authenticated user.

    Lives alongside Firebase's default claims (uid / email / email_verified /
    iat / exp / etc.) — this schema pins only the Odum-controlled keys so
    both Python (admin SDK) and UI (client SDK) readers stay aligned.

    Stored on the user via ``firebase_admin.auth.set_custom_user_claims(uid,
    claims.model_dump())``. Propagation to the ID token takes one refresh
    cycle (typ. 1 hour or an explicit ``getIdToken(true)`` call).

    Capability flags (bool) default ``False`` so new users are locked down
    by default and must be explicitly uplifted by admin.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    audience: ClientAudience
    org_id: str | None = None

    # --- capability flags (bool) ------------------------------------------
    pricing_read_internal: bool = False  # tier='internal' allowed in cost()
    strategy_catalogue_admin: bool = False  # can toggle lock_state / maturity
    im_desk: bool = False  # IM-desk view in UI + access to all /contracts reads
    admin: bool = False  # workspace-wide admin (Firestore wildcard reads/writes)


__all__ = [
    "CapabilityClaims",
]
