"""MEV normalizers — Flashbots, MEV-Share, MEV Blocker.

Maps MEV bundle/block schemas to canonical types:
- FlashbotsBundleResult, MevShareBundleResult -> CanonicalOnChainMetric (metric_type=mev_bundle)
- Bundle submission results stored as on-chain metrics for observability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalOnChainMetric
from .schemas import FlashbotsBundleResult, MevShareBundleResult


def normalize_flashbots_bundle_result(
    raw: FlashbotsBundleResult,
    venue: str = "flashbots",
    block_number: str | None = None,
) -> CanonicalOnChainMetric | None:
    """Normalize FlashbotsBundleResult to CanonicalOnChainMetric.

    metric_type = "mev_bundle"
    value = 1 (success indicator)
    entity = bundleHash
    """
    if not raw.bundleHash:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "bundleHash": raw.bundleHash,
        "smart": str(raw.smart) if raw.smart is not None else None,
        "blockNumber": block_number,
    }
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="mev_bundle",
        asset="ETH",
        value=Decimal("1"),
        entity=raw.bundleHash,
        raw=raw_dict,
    )


def normalize_mev_share_bundle_result(
    raw: MevShareBundleResult,
    venue: str = "mev_share",
) -> CanonicalOnChainMetric | None:
    """Normalize MevShareBundleResult to CanonicalOnChainMetric.

    metric_type = "mev_bundle"
    value = 1 (success indicator)
    entity = bundleHash
    """
    if not raw.bundleHash:
        return None
    raw_dict: dict[str, float | int | str | None] = {"bundleHash": raw.bundleHash}
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="mev_bundle",
        asset="ETH",
        value=Decimal("1"),
        entity=raw.bundleHash,
        raw=raw_dict,
    )


__all__ = [
    "normalize_flashbots_bundle_result",
    "normalize_mev_share_bundle_result",
]
