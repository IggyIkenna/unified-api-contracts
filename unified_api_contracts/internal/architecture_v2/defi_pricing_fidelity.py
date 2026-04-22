"""DeFi spot-venue pricing fidelity — G2.9 gap #8.

Stage 3E § 2.9 gap #8 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
``ML_DIRECTIONAL_CONTINUOUS x DeFi x spot`` and
``RULES_DIRECTIONAL_CONTINUOUS x DeFi x spot`` both claim SUPPORTED in
the matrix but are actually PARTIAL because Uniswap V3 pricing
fidelity on thin pairs is not tick-level. Strategies need to know
whether a spot DEX offers tick streams (usable for ML) or snapshot
pricing (not usable) before deploying an ML directional model.

This registry declares per-(venue, pool) fidelity so strategy-service
can gate ML deployment on pool TVL + tick-stream source availability.

Consumer integration:

* execution-service DeFi connectors read fidelity before treating a
  swap quote as a live-tradable price.
* strategy-service ML deployment validator refuses to deploy an ML
  strategy on a pool below ``pool_tvl_usd_min_for_fidelity``.
* Pricing-engine (G3.1) reads ``tick_stream_source`` to choose between
  event-stream / TWAP / snapshot feed.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field


class PricingFidelity(StrEnum):
    """Fidelity tier of a DeFi pool's price feed."""

    TICK_STREAM = "tick_stream"
    """Continuous orderbook / AMM event stream; < 100ms staleness."""

    SNAPSHOT = "snapshot"
    """Periodic polls; 1-60s staleness."""

    DERIVED_TWAP = "derived_twap"
    """Uniswap V3 TWAP oracle only — lagging price."""

    NONE = "none"
    """No reliable price feed."""


TickStreamSource = Literal[
    "subgraph_events",
    "websocket",
    "rpc_poll",
    "chain_rpc",
    "none",
]


class DefiSpotVenueCapability(BaseModel):
    """Per (venue, chain, pool) fidelity declaration.

    Scoped at the pool level because the same DEX can have wildly
    different fidelity across its pools (blue-chip WETH/USDC vs
    long-tail tokens).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str
    """DEX slug (e.g. "uniswap_v3", "curve", "pancakeswap", "balancer")."""

    chain: str
    pool_id: str
    """Pool address on the chain (checksum) or curve pool name."""

    token_pair: tuple[str, str]
    """(token0, token1) — uppercase symbols."""

    pricing_fidelity: PricingFidelity
    tick_stream_source: TickStreamSource
    pool_tvl_usd_min_for_fidelity: int = Field(ge=0)
    """Minimum USD TVL at which the stated fidelity holds."""

    notes: str = ""


DEFI_SPOT_VENUE_FIDELITY: Final[tuple[DefiSpotVenueCapability, ...]] = (
    # ── Uniswap V3 blue-chip pools — tick-stream capable ───────────────
    DefiSpotVenueCapability(
        venue_id="uniswap_v3",
        chain="ETHEREUM",
        pool_id="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
        token_pair=("USDC", "WETH"),
        pricing_fidelity=PricingFidelity.TICK_STREAM,
        tick_stream_source="subgraph_events",
        pool_tvl_usd_min_for_fidelity=10_000_000,
        notes="USDC/WETH 0.05% — canonical tick-stream pool.",
    ),
    DefiSpotVenueCapability(
        venue_id="uniswap_v3",
        chain="ETHEREUM",
        pool_id="0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
        token_pair=("WBTC", "WETH"),
        pricing_fidelity=PricingFidelity.TICK_STREAM,
        tick_stream_source="subgraph_events",
        pool_tvl_usd_min_for_fidelity=5_000_000,
    ),
    # ── Uniswap V3 on L2s ──────────────────────────────────────────────
    DefiSpotVenueCapability(
        venue_id="uniswap_v3",
        chain="ARBITRUM",
        pool_id="0xC31E54c7a869B9FcBEcc14363CF510d1c41fa443",
        token_pair=("USDC", "WETH"),
        pricing_fidelity=PricingFidelity.TICK_STREAM,
        tick_stream_source="websocket",
        pool_tvl_usd_min_for_fidelity=2_000_000,
    ),
    # ── Uniswap V3 long-tail — snapshot only ───────────────────────────
    DefiSpotVenueCapability(
        venue_id="uniswap_v3",
        chain="ETHEREUM",
        pool_id="0x0000000000000000000000000000000000000001",  # placeholder
        token_pair=("WETH", "APE"),
        pricing_fidelity=PricingFidelity.SNAPSHOT,
        tick_stream_source="rpc_poll",
        pool_tvl_usd_min_for_fidelity=500_000,
        notes="Long-tail pool — snapshot only, not suitable for ML directional.",
    ),
    # ── Curve 3pool stablecoin ─────────────────────────────────────────
    DefiSpotVenueCapability(
        venue_id="curve",
        chain="ETHEREUM",
        pool_id="3pool",
        token_pair=("USDC", "USDT"),
        pricing_fidelity=PricingFidelity.TICK_STREAM,
        tick_stream_source="subgraph_events",
        pool_tvl_usd_min_for_fidelity=20_000_000,
        notes="Curve 3pool — stablecoin-stablecoin; 3-asset pool but tracked as USDC/USDT for basis.",
    ),
    # ── Pancakeswap BSC ────────────────────────────────────────────────
    DefiSpotVenueCapability(
        venue_id="pancakeswap",
        chain="BSC",
        pool_id="0x0000000000000000000000000000000000000002",  # placeholder
        token_pair=("BNB", "BUSD"),
        pricing_fidelity=PricingFidelity.DERIVED_TWAP,
        tick_stream_source="rpc_poll",
        pool_tvl_usd_min_for_fidelity=1_000_000,
        notes="Pancakeswap V2 — TWAP-oracle pricing only; lagging.",
    ),
)


class DefiPoolNotRegisteredError(LookupError):
    """Raised when ``fidelity_for(venue, chain, pool_id)`` can't resolve."""


def fidelity_for(
    venue_id: str,
    chain: str,
    pool_id: str,
    *,
    registry: Iterable[DefiSpotVenueCapability] = DEFI_SPOT_VENUE_FIDELITY,
) -> DefiSpotVenueCapability:
    """Resolve pool fidelity. Fail-loud on miss."""

    for entry in registry:
        if entry.venue_id == venue_id and entry.chain == chain and entry.pool_id == pool_id:
            return entry
    raise DefiPoolNotRegisteredError(
        f"no fidelity row for venue={venue_id!r}, chain={chain!r}, pool_id={pool_id!r}",
    )


def pools_at_fidelity(
    fidelity: PricingFidelity,
    *,
    registry: Iterable[DefiSpotVenueCapability] = DEFI_SPOT_VENUE_FIDELITY,
) -> tuple[DefiSpotVenueCapability, ...]:
    """All pools at a given fidelity tier."""

    return tuple(entry for entry in registry if entry.pricing_fidelity is fidelity)


def pools_for_pair(
    token_a: str,
    token_b: str,
    *,
    registry: Iterable[DefiSpotVenueCapability] = DEFI_SPOT_VENUE_FIDELITY,
) -> tuple[DefiSpotVenueCapability, ...]:
    """All pools for a token pair (order-insensitive)."""

    target = frozenset((token_a, token_b))
    return tuple(entry for entry in registry if frozenset(entry.token_pair) == target)


def _validate_registry_invariants(
    registry: Iterable[DefiSpotVenueCapability] = DEFI_SPOT_VENUE_FIDELITY,
) -> None:
    """Invariants:

    * (venue, chain, pool_id) unique.
    * ``token_pair`` tokens distinct + uppercase.
    * ``pricing_fidelity == NONE`` rows disallowed (use absence).
    * Token pair has exactly 2 elements (enforced by type).
    """

    seen: set[tuple[str, str, str]] = set()
    for entry in registry:
        key = (entry.venue_id, entry.chain, entry.pool_id)
        if key in seen:
            raise ValueError(
                f"duplicate pool in DEFI_SPOT_VENUE_FIDELITY: {key!r}",
            )
        seen.add(key)

        token0, token1 = entry.token_pair
        if token0 == token1:
            raise ValueError(
                f"{key!r}: token_pair tokens must differ ({token0!r})",
            )
        if token0 != token0.upper() or token1 != token1.upper():
            raise ValueError(
                f"{key!r}: token_pair must be uppercase ({entry.token_pair!r})",
            )
        if entry.pricing_fidelity is PricingFidelity.NONE:
            raise ValueError(
                f"{key!r}: NONE fidelity — drop the row instead of declaring it",
            )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "execution-service/execution_service/defi_execution/connectors/registry.py",
    "execution-service/execution_service/defi_execution/amm_adapter.py",
    "strategy-service/strategy_service/validation/data_certification.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "DEFI_SPOT_VENUE_FIDELITY",
    "DefiPoolNotRegisteredError",
    "DefiSpotVenueCapability",
    "PricingFidelity",
    "TickStreamSource",
    "fidelity_for",
    "pools_at_fidelity",
    "pools_for_pair",
]
