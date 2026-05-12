"""Client share-class registry seed — demo client + cutover archetypes.

SSOT: plans/active/client_reporting_pnl_attribution_mvp_2026_05_10.md Phase 1.D.

This module provides the canonical seed data for the May-23 cutover:
  - 1 internal demo client subscribed to both cutover archetypes.
  - Demo share class: USDT (market-neutral, USD-denominated).

External callers MUST import via the facade:
  from unified_api_contracts.internal.reporting import ClientReportingMode
  from unified_api_contracts.canonical.crosscutting.share_class import ShareClass

Consumers reading registry state at runtime MUST use the tranche_router
registry YAML — this module seeds the canonical *contract* values only.
"""

from __future__ import annotations

from dataclasses import dataclass

from unified_api_contracts.canonical.crosscutting.share_class import ShareClass
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
