"""Client share-class registry seed — demo client + cutover archetypes.

SSOT: plans/active/client_reporting_pnl_attribution_mvp_2026_05_10.md Phase 1.D.
      plans/active/wallet_treasury_client_flow_2026_05_10.md Phase 4.C.

This module provides the canonical seed data for the May-23 cutover:
  - 1 internal demo client subscribed to both cutover archetypes.
  - Demo share class: USDT (market-neutral, USD-denominated).

Also provides HWM + perf-fee configurations per share class (Phase 4.C).

External callers MUST import via the facade:
  from unified_api_contracts.internal.reporting import ClientReportingMode
  from unified_api_contracts.canonical.crosscutting.share_class import ShareClass

Consumers reading registry state at runtime MUST use the tranche_router
registry YAML — this module seeds the canonical *contract* values only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.share_class import ShareClass
from unified_api_contracts.internal.domain.hwm_ledger import (
    CrystallizationCadence,
    ShareClassPerfFeeConfig,
)
from unified_api_contracts.internal.reporting import ClientReportingMode

DEMO_CLIENT_ID: str = "demo-internal"
"""Canonical ID for the May-23 internal demo client."""

LIVE_DEFI_CUTOVER_ARCHETYPES: list[str] = [
    "carry_staked_basis",
    "leveraged_funding_arb",
]
"""The two DeFi archetypes running in the May-23 live cutover demo."""


@dataclass(frozen=True)
class ClientShareClassSeed:
    """Seed row for a client's share-class subscription."""

    client_id: str
    share_class: ShareClass
    mode: ClientReportingMode
    archetypes: tuple[str, ...]


DEMO_CLIENT_SEED: ClientShareClassSeed = ClientShareClassSeed(
    client_id=DEMO_CLIENT_ID,
    share_class=ShareClass.USDT,
    mode=ClientReportingMode.DEMO,
    archetypes=tuple(LIVE_DEFI_CUTOVER_ARCHETYPES),
)
"""Canonical seed for the May-23 demo client — 1 client, 2 archetypes, USDT."""


# ---------------------------------------------------------------------------
# HWM + perf-fee config registry (Phase 4.C)
# ---------------------------------------------------------------------------

SHARE_CLASS_PERF_FEE_CONFIGS: dict[str, ShareClassPerfFeeConfig] = {
    "USDC_CUTOVER_V1": ShareClassPerfFeeConfig(
        share_class_id="USDC_CUTOVER_V1",
        crystallization_cadence=CrystallizationCadence.MONTHLY,
        perf_fee_rate=Decimal("0.20"),
        management_fee_rate_annual=Decimal("0.02"),
        flat_fee_per_trade=Decimal("0"),
    ),
    "ETH_FLAGSHIP": ShareClassPerfFeeConfig(
        share_class_id="ETH_FLAGSHIP",
        crystallization_cadence=CrystallizationCadence.QUARTERLY,
        perf_fee_rate=Decimal("0.25"),
        management_fee_rate_annual=Decimal("0.02"),
        flat_fee_per_trade=Decimal("0"),
    ),
}
"""Per-share-class HWM + perf-fee configurations.

SSOT for client_reporting + wallet_treasury services.
"""


def get_share_class_perf_fee_config(share_class_id: str) -> ShareClassPerfFeeConfig:
    """Return HWM + perf-fee config for a share class.

    Args:
        share_class_id: Share class identifier (e.g., "USDC_CUTOVER_V1").

    Returns:
        ShareClassPerfFeeConfig for the given share class.

    Raises:
        KeyError: If share_class_id is not registered.
    """
    return SHARE_CLASS_PERF_FEE_CONFIGS[share_class_id]
