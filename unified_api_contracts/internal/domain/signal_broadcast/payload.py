"""Per-depth signal payload models for counterparty emissions.

Discriminated on :class:`SchemaDepth` at the envelope layer
(``SignalEmission.signal_payload``). Each model is frozen so a
transport-layer retry cannot mutate the payload between attempts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "SignalPayloadMinimal",
    "SignalPayloadRich",
    "SignalPayloadStandard",
]


# Cap on the feature snapshot dict size. Keeps the wire payload bounded
# and prevents counterparties from extracting wholesale feature tables.
_RICH_FEATURE_SNAPSHOT_MAX_KEYS: int = 32


class SignalPayloadMinimal(BaseModel):
    """Minimum-viable payload — direction + weight + optional confidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: Literal["long", "short", "flat"]
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class SignalPayloadStandard(BaseModel):
    """``MINIMAL`` + horizon + stop/take-profit hints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: Literal["long", "short", "flat"]
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_horizon_seconds: int = Field(gt=0)
    stop_loss_bps: int | None = Field(default=None, ge=0)
    take_profit_bps: int | None = Field(default=None, ge=0)


class SignalPayloadRich(BaseModel):
    """``STANDARD`` + rationale tags + bounded feature snapshot.

    Premium tier. ``feature_snapshot`` is capped at 32 keys to preserve
    attribution usefulness without leaking Odum's full feature table.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: Literal["long", "short", "flat"]
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_horizon_seconds: int = Field(gt=0)
    stop_loss_bps: int | None = Field(default=None, ge=0)
    take_profit_bps: int | None = Field(default=None, ge=0)
    rationale_tags: tuple[str, ...] = Field(default_factory=tuple)
    feature_snapshot: dict[str, float] = Field(default_factory=dict)

    def model_post_init(self, _context: object) -> None:
        """Enforce the 32-key cap on ``feature_snapshot`` at construction."""

        if len(self.feature_snapshot) > _RICH_FEATURE_SNAPSHOT_MAX_KEYS:
            raise ValueError(
                f"feature_snapshot exceeds max keys ({len(self.feature_snapshot)} > {_RICH_FEATURE_SNAPSHOT_MAX_KEYS})"
            )
