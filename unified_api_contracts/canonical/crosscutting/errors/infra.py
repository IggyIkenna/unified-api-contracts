"""Venue error classifications for infrastructure providers (RPC, indexers, relays).

These are transport-layer providers, NOT venues. We don't trade on them — we use them
to reach venues (e.g., Alchemy errors happen when talking to Aave, not Alchemy itself).
"""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve

INFRA_ERRORS: dict[str, list[VenueErrorClassification]] = {
    "alchemy": [
        ve(
            "alchemy",
            "-32600",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Invalid request",
        ),
        ve(
            "alchemy",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal error",
        ),
        ve(
            "alchemy",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
    ],
    "thegraph": [
        ve(
            "thegraph",
            "Subgraph not found",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Not found",
        ),
        ve(
            "thegraph",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
    ],
    "bloxroute": [
        ve(
            "bloxroute",
            "-32600",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Invalid request",
        ),
        ve(
            "bloxroute",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal error",
        ),
        ve(
            "bloxroute",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
    ],
    "onchain_revert": [
        ve(
            "onchain_revert",
            "EXECUTION_REVERTED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="EVM transaction reverted — contract logic rejected the call",
        ),
        ve(
            "onchain_revert",
            "OUT_OF_GAS",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Transaction ran out of gas — increase gas limit",
        ),
        ve(
            "onchain_revert",
            "INSUFFICIENT_FUNDS",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Sender has insufficient ETH for gas + value",
        ),
        ve(
            "onchain_revert",
            "NONCE_TOO_LOW",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Transaction nonce already used — resync nonce",
        ),
    ],
}
