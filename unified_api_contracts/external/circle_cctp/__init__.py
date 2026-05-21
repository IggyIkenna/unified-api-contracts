"""Circle CCTP Iris API contracts (iris-api.circle.com/v1/).

Used by execution-service cctp.py to poll for cross-chain USDC burn attestations.
No API key required — public attestation endpoint.
"""

from unified_api_contracts.external.circle_cctp.schemas import (
    CircleCctpAttestation,
)

__all__ = ["CircleCctpAttestation"]
