"""Outbound signal payload envelope for counterparty emissions.

The :class:`SignalPayload` model is the canonical on-the-wire shape
posted to a counterparty webhook endpoint (after HMAC-signing via
``unified_trading_library.security.hmac_signing.build_signed_envelope``).

Three :class:`PayloadDepth` tiers govern which optional fields are
populated:

* ``MINIMAL`` — core identification fields + directional intent + target
  exposure. Cheapest tier, minimal Odum alpha leakage.
* ``STANDARD`` — ``MINIMAL`` plus horizon, stop/take-profit hints, and
  confidence. Enough for a counterparty to route through their own
  execution stack.
* ``RICH`` — ``STANDARD`` plus rationale tags and a bounded feature
  snapshot. Premium tier.

All fields are kept on a single Pydantic model (rather than three
separate models) so the wire representation serialises deterministically
via ``model_dump(mode="json")`` — this is what the HMAC-signing helper
(``build_signed_envelope``) canonicalises and signs.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DirectionalIntent",
    "PayloadDepth",
    "SignalPayload",
]

# Bounded-by-design cap on the ``feature_snapshot`` dict. Prevents
# counterparties from extracting wholesale feature tables while still
# giving them enough attribution context.
_RICH_FEATURE_SNAPSHOT_MAX_KEYS: int = 32


class PayloadDepth(StrEnum):
    """Depth tier governing which payload fields are populated."""

    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    RICH = "RICH"


DirectionalIntent = Literal["LONG", "SHORT", "FLAT", "REBALANCE"]
"""Direction-type literal carried on every emission payload.

* ``LONG`` / ``SHORT`` — open (or hold) directional exposure.
* ``FLAT`` — close to zero exposure.
* ``REBALANCE`` — maintain direction, adjust weight toward
  ``target_exposure``.
"""


class SignalPayload(BaseModel):
    """Canonical outbound signal payload.

    Serialises via ``model_dump(mode="json")`` to a dict suitable for
    :func:`unified_trading_library.security.hmac_signing.build_signed_envelope`.
    The envelope helper adds a ``signature`` field and a ``signed_at``
    field; all other payload fields are preserved verbatim.

    ``signed_delivery_receipt`` is an optional structured block a
    counterparty may use to attribute signed receipts (analogous to
    email DKIM) — it is populated only by the emitter after delivery
    acknowledgement and should never be set by the signal-generation
    layer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Core identification (all depths) ---------------------------
    slot_label: str = Field(min_length=1)
    """Archetype/venue/instrument slot, canonical form
    (``stat-arb-pairs-fixed-cefi-spot-btc-eth``, etc.)."""

    signal_version: str = Field(min_length=1)
    """Semver of the strategy code that produced this signal. Lets
    counterparties detect upgrade events in the audit trail."""

    directional_intent: DirectionalIntent
    """Direction type — see :data:`DirectionalIntent`."""

    target_exposure: float
    """Target exposure on the slot (abstract units — the counterparty
    interprets these against their own position-sizing model)."""

    timeframe: str = Field(min_length=1)
    """Human-readable timeframe (``1m``, ``5m``, ``1h``, ``1d``) — the
    horizon over which the signal expects to realise."""

    emitted_at: datetime
    """UTC emission timestamp on the Odum side. Counterparties compare
    this against their own ingestion timestamp for latency SLAs."""

    depth: PayloadDepth = PayloadDepth.MINIMAL
    """Tier this payload is serialised at. MINIMAL payloads should have
    all STANDARD/RICH fields set to ``None``."""

    # --- STANDARD + RICH fields -------------------------------------
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    """Model confidence in ``[0, 1]``. ``None`` at ``MINIMAL`` depth."""

    expected_horizon_seconds: int | None = Field(default=None, gt=0)
    """Expected signal horizon in seconds. ``None`` at ``MINIMAL``
    depth."""

    stop_loss_bps: int | None = Field(default=None, ge=0)
    """Suggested stop-loss in basis points. ``None`` at ``MINIMAL``
    depth."""

    take_profit_bps: int | None = Field(default=None, ge=0)
    """Suggested take-profit in basis points. ``None`` at ``MINIMAL``
    depth."""

    # --- RICH-only fields -------------------------------------------
    rationale_tags: tuple[str, ...] = Field(default_factory=tuple)
    """Free-form rationale tags (model name, regime, feature group).
    Empty tuple outside ``RICH``."""

    feature_snapshot: dict[str, float] = Field(default_factory=dict)
    """Bounded feature snapshot (max 32 keys). Empty dict outside
    ``RICH``. The 32-key cap is enforced at construction."""

    # --- Delivery receipt (populated post-delivery) -----------------
    signed_delivery_receipt: dict[str, str] | None = None
    """Optional structured signed-receipt block attached post-delivery.
    ``None`` on the initial emission payload."""

    def model_post_init(self, _context: object) -> None:
        """Enforce the 32-key cap on ``feature_snapshot`` at
        construction time."""

        if len(self.feature_snapshot) > _RICH_FEATURE_SNAPSHOT_MAX_KEYS:
            raise ValueError(
                f"feature_snapshot exceeds max keys ({len(self.feature_snapshot)} > {_RICH_FEATURE_SNAPSHOT_MAX_KEYS})"
            )
