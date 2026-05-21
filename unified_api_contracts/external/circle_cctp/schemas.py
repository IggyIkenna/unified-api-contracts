"""Circle CCTP Iris API schemas (iris-api.circle.com/v1/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CircleCctpAttestation(BaseModel):
    """Attestation response from GET /v1/attestations/{message_hash}.

    No API key required — Circle Iris is a public attestation service.
    """

    status: str = Field(..., description="Attestation status: 'pending_confirmations' | 'complete'")
    attestation: str | None = Field(None, description="Hex-encoded attestation signature (once complete)")
