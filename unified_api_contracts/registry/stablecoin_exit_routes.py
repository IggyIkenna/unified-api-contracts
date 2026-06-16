"""UAC stablecoin emergency-exit route registry (D.6).

``STABLECOIN_EMERGENCY_EXIT_ROUTES`` maps stable symbol → ordered tuple of
``ExitRoute`` records describing how to convert that stablecoin to a harder
collateral asset during a depeg event.

Usage::

    from unified_api_contracts.registry.stablecoin_exit_routes import (
        STABLECOIN_EMERGENCY_EXIT_ROUTES,
        ExitRoute,
        get_emergency_exit_routes,
    )

    # Cheapest routes for a $500k USDC exit
    routes = get_emergency_exit_routes("USDC", Decimal("500000"))
    # Each route: r.route_id, r.venue, r.priority_rank ...

SSOT: ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` Phase D.6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final


@dataclass(frozen=True)
class ExitRoute:
    """A single emergency-exit path from a stablecoin to a harder collateral asset.

    :param route_id: Unique route identifier, e.g. ``'USDC_TO_ETH_VIA_UNISWAP_V3'``.
    :param stable: Source stablecoin symbol, e.g. ``'USDC'``.
    :param target: Destination asset symbol, e.g. ``'ETH'``, ``'BTC'``, ``'WBTC'``.
    :param venue: Venue name, e.g. ``'UNISWAP_V3'``, ``'BINANCE_SPOT'``.
    :param pool_address: On-chain pool address for DEX routes (empty for CEX).
    :param typical_exit_size_usd: Representative exit size for slippage estimation.
    :param expected_slippage_bps_at_size: Expected slippage in bps at ``typical_exit_size_usd``.
    :param estimated_gas_cost_usd: Estimated gas/fee cost in USD for this route.
    :param priority_rank: Lower = faster/cheaper; 1 = primary route, higher = fallback.
    """

    route_id: str
    stable: str
    target: str
    venue: str
    pool_address: str = ""
    typical_exit_size_usd: Decimal = field(default_factory=lambda: Decimal("100000"))
    expected_slippage_bps_at_size: Decimal = field(default_factory=lambda: Decimal("10"))
    estimated_gas_cost_usd: Decimal = field(default_factory=lambda: Decimal("5"))
    priority_rank: int = 1


def _route(
    route_id: str,
    stable: str,
    target: str,
    venue: str,
    pool_address: str = "",
    typical_exit_size_usd: str = "100000",
    slippage_bps: str = "10",
    gas_usd: str = "5",
    priority_rank: int = 1,
) -> ExitRoute:
    """Constructor helper — avoids Decimal(...) noise in the registry body."""
    return ExitRoute(
        route_id=route_id,
        stable=stable,
        target=target,
        venue=venue,
        pool_address=pool_address,
        typical_exit_size_usd=Decimal(typical_exit_size_usd),
        expected_slippage_bps_at_size=Decimal(slippage_bps),
        estimated_gas_cost_usd=Decimal(gas_usd),
        priority_rank=priority_rank,
    )


# ---------------------------------------------------------------------------
# Registry: 30+ routes across 8 stablecoins
# ---------------------------------------------------------------------------

STABLECOIN_EMERGENCY_EXIT_ROUTES: Final[dict[str, tuple[ExitRoute, ...]]] = {
    # ── USDC → ETH / BTC ────────────────────────────────────────────────────
    "USDC": (
        _route(
            "USDC_TO_ETH_VIA_UNISWAP_V3",
            stable="USDC",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8",  # USDC/ETH 0.3%  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="8",
            gas_usd="12",
            priority_rank=1,
        ),
        _route(
            "USDC_TO_ETH_VIA_CURVE_3POOL",
            stable="USDC",
            target="ETH",
            venue="CURVE",
            pool_address="0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # Curve 3pool  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="10",
            gas_usd="15",
            priority_rank=2,
        ),
        _route(
            "USDC_TO_ETH_VIA_COINBASE_SPOT",
            stable="USDC",
            target="ETH",
            venue="COINBASE_SPOT",
            typical_exit_size_usd="500000",
            slippage_bps="5",
            gas_usd="0",
            priority_rank=3,
        ),
        _route(
            "USDC_TO_ETH_VIA_BINANCE_SPOT",
            stable="USDC",
            target="ETH",
            venue="BINANCE_SPOT",
            typical_exit_size_usd="500000",
            slippage_bps="4",
            gas_usd="0",
            priority_rank=4,
        ),
        _route(
            "USDC_TO_WBTC_VIA_UNISWAP_V3",
            stable="USDC",
            target="WBTC",
            venue="UNISWAP_V3",
            pool_address="0x99ac8cA7087fA4A2A1FB6357269965A2014ABc35",  # USDC/WBTC 0.3%  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="12",
            gas_usd="12",
            priority_rank=5,
        ),
    ),
    # ── USDT → ETH / BTC ────────────────────────────────────────────────────
    "USDT": (
        _route(
            "USDT_TO_ETH_VIA_UNISWAP_V3",
            stable="USDT",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36",  # USDT/ETH 0.3%  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="9",
            gas_usd="12",
            priority_rank=1,
        ),
        _route(
            "USDT_TO_ETH_VIA_CURVE",
            stable="USDT",
            target="ETH",
            venue="CURVE",
            pool_address="0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="10",
            gas_usd="15",
            priority_rank=2,
        ),
        _route(
            "USDT_TO_ETH_VIA_BINANCE_SPOT",
            stable="USDT",
            target="ETH",
            venue="BINANCE_SPOT",
            typical_exit_size_usd="500000",
            slippage_bps="4",
            gas_usd="0",
            priority_rank=3,
        ),
        _route(
            "USDT_TO_BTC_VIA_BINANCE_SPOT",
            stable="USDT",
            target="BTC",
            venue="BINANCE_SPOT",
            typical_exit_size_usd="500000",
            slippage_bps="3",
            gas_usd="0",
            priority_rank=4,
        ),
    ),
    # ── DAI → ETH ────────────────────────────────────────────────────────────
    "DAI": (
        _route(
            "DAI_TO_ETH_VIA_UNISWAP_V3",
            stable="DAI",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x60594a405d53811d3BC4766596EFD80fd545A270",  # DAI/ETH 0.05%  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="7",
            gas_usd="12",
            priority_rank=1,
        ),
        _route(
            "DAI_TO_ETH_VIA_CURVE",
            stable="DAI",
            target="ETH",
            venue="CURVE",
            pool_address="0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # QG-allow: defi-citation
            typical_exit_size_usd="500000",
            slippage_bps="10",
            gas_usd="15",
            priority_rank=2,
        ),
        _route(
            "DAI_TO_ETH_VIA_COINBASE_SPOT",
            stable="DAI",
            target="ETH",
            venue="COINBASE_SPOT",
            typical_exit_size_usd="200000",
            slippage_bps="10",
            gas_usd="0",
            priority_rank=3,
        ),
        _route(
            "DAI_TO_WBTC_VIA_UNISWAP_V3",
            stable="DAI",
            target="WBTC",
            venue="UNISWAP_V3",
            pool_address="0x391E8501b626C623d39474AfcA6f9e46c2686649",  # DAI/WBTC 0.3%  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="15",
            gas_usd="12",
            priority_rank=4,
        ),
    ),
    # ── USDE → ETH ───────────────────────────────────────────────────────────
    "USDE": (
        _route(
            "USDE_TO_ETH_VIA_CURVE",
            stable="USDE",
            target="ETH",
            venue="CURVE",
            pool_address="0x5426178799ee0a0181A89b4f57eFddfAb49941Ec",  # USDe/USDC Curve  # QG-allow: defi-citation
            typical_exit_size_usd="300000",
            slippage_bps="15",
            gas_usd="15",
            priority_rank=1,
        ),
        _route(
            "USDE_TO_ETH_VIA_PENDLE",
            stable="USDE",
            target="ETH",
            venue="PENDLE",
            pool_address="0x6fcf753f2C67b83f7B09746Bbc4FA0047b35D050",  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="20",
            gas_usd="18",
            priority_rank=2,
        ),
        _route(
            "USDE_TO_USDC_VIA_CURVE",
            stable="USDE",
            target="USDC",
            venue="CURVE",
            pool_address="0x5426178799ee0a0181A89b4f57eFddfAb49941Ec",  # QG-allow: defi-citation
            typical_exit_size_usd="300000",
            slippage_bps="12",
            gas_usd="15",
            priority_rank=3,
        ),
    ),
    # ── FRAX → ETH ───────────────────────────────────────────────────────────
    "FRAX": (
        _route(
            "FRAX_TO_ETH_VIA_UNISWAP_V3",
            stable="FRAX",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x92c7b5ce4CB0E5483F3365C1449f21578eE9f21A",  # FRAX/ETH 0.3%  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="18",
            gas_usd="12",
            priority_rank=1,
        ),
        _route(
            "FRAX_TO_ETH_VIA_CURVE_FRAXPOOL",
            stable="FRAX",
            target="ETH",
            venue="CURVE",
            pool_address="0xd632f22692FaC7611d2AA1C0D552930D43CAEd3B",  # Frax/3Crv  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="20",
            gas_usd="15",
            priority_rank=2,
        ),
        _route(
            "FRAX_TO_USDC_VIA_CURVE_FRAXPOOL",
            stable="FRAX",
            target="USDC",
            venue="CURVE",
            pool_address="0xd632f22692FaC7611d2AA1C0D552930D43CAEd3B",  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="15",
            gas_usd="15",
            priority_rank=3,
        ),
    ),
    # ── GHO → ETH ────────────────────────────────────────────────────────────
    "GHO": (
        _route(
            "GHO_TO_ETH_VIA_UNISWAP_V3",
            stable="GHO",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x7b925e617AEeDf3B435a1B4a9EE0Cc4b3c0B834D",  # GHO/ETH 0.3%  # QG-allow: defi-citation
            typical_exit_size_usd="100000",
            slippage_bps="25",
            gas_usd="12",
            priority_rank=1,
        ),
        _route(
            "GHO_TO_USDC_VIA_UNISWAP_V3",
            stable="GHO",
            target="USDC",
            venue="UNISWAP_V3",
            pool_address="0x7b925e617AEeDf3B435a1B4a9EE0Cc4b3c0B834D",  # QG-allow: defi-citation
            typical_exit_size_usd="100000",
            slippage_bps="20",
            gas_usd="12",
            priority_rank=2,
        ),
        _route(
            "GHO_TO_ETH_VIA_CURVE_GHOPOOL",
            stable="GHO",
            target="ETH",
            venue="CURVE",
            pool_address="0x8353157092ED8Be69a9Df8F95af097bbF33Cb2aF",  # GHO/USDC/USDT Curve  # QG-allow: defi-citation
            typical_exit_size_usd="100000",
            slippage_bps="28",
            gas_usd="15",
            priority_rank=3,
        ),
    ),
    # ── CRVUSD → ETH ─────────────────────────────────────────────────────────
    "CRVUSD": (
        _route(
            "CRVUSD_TO_ETH_VIA_CURVE",
            stable="CRVUSD",
            target="ETH",
            venue="CURVE",
            pool_address="0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E",  # crvUSD/USDC  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="15",
            gas_usd="15",
            priority_rank=1,
        ),
        _route(
            "CRVUSD_TO_WETH_VIA_CURVE",
            stable="CRVUSD",
            target="ETH",
            venue="CURVE",
            pool_address="0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E",  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="18",
            gas_usd="15",
            priority_rank=2,
        ),
        _route(
            "CRVUSD_TO_USDC_VIA_CURVE",
            stable="CRVUSD",
            target="USDC",
            venue="CURVE",
            pool_address="0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E",  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="12",
            gas_usd="15",
            priority_rank=3,
        ),
    ),
    # ── PYUSD → ETH ──────────────────────────────────────────────────────────
    "PYUSD": (
        _route(
            "PYUSD_TO_ETH_VIA_CURVE",
            stable="PYUSD",
            target="ETH",
            venue="CURVE",
            pool_address="0x383E6b4437b59fff47B619CBA855CA29342A8559",  # PYUSD/USDC Curve  # QG-allow: defi-citation
            typical_exit_size_usd="100000",
            slippage_bps="20",
            gas_usd="15",
            priority_rank=1,
        ),
        _route(
            "PYUSD_TO_ETH_VIA_UNISWAP_V3",
            stable="PYUSD",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x383E6b4437b59fff47B619CBA855CA29342A8559",  # QG-allow: defi-citation
            typical_exit_size_usd="100000",
            slippage_bps="25",
            gas_usd="12",
            priority_rank=2,
        ),
        _route(
            "PYUSD_TO_USDC_VIA_COINBASE_SPOT",
            stable="PYUSD",
            target="USDC",
            venue="COINBASE_SPOT",
            typical_exit_size_usd="100000",
            slippage_bps="15",
            gas_usd="0",
            priority_rank=3,
        ),
    ),
    # ── SUSDE → ETH ──────────────────────────────────────────────────────────
    "SUSDE": (
        _route(
            "SUSDE_TO_USDE_VIA_ETHENA_REDEEM",
            stable="SUSDE",
            target="USDE",
            venue="ETHENA",
            pool_address="",  # Ethena redeem contract (off-chain KYC; not a pool)
            typical_exit_size_usd="200000",
            slippage_bps="5",
            gas_usd="10",
            priority_rank=1,
        ),
        _route(
            "SUSDE_TO_ETH_VIA_CURVE",
            stable="SUSDE",
            target="ETH",
            venue="CURVE",
            pool_address="0x167478921b907422F8E88B43C4Af2B8BEa278d3A",  # sUSDe/USDC Curve  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="18",
            gas_usd="15",
            priority_rank=2,
        ),
        _route(
            "SUSDE_TO_ETH_VIA_UNISWAP_V3",
            stable="SUSDE",
            target="ETH",
            venue="UNISWAP_V3",
            pool_address="0x167478921b907422F8E88B43C4Af2B8BEa278d3A",  # QG-allow: defi-citation
            typical_exit_size_usd="200000",
            slippage_bps="22",
            gas_usd="12",
            priority_rank=3,
        ),
    ),
    # ── BUSD → ETH (historical — BUSD wound down; emergency exits still valid) ─
    "BUSD": (
        _route(
            "BUSD_TO_ETH_VIA_BINANCE_SPOT",
            stable="BUSD",
            target="ETH",
            venue="BINANCE_SPOT",
            typical_exit_size_usd="100000",
            slippage_bps="5",
            gas_usd="0",
            priority_rank=1,
        ),
        _route(
            "BUSD_TO_USDC_VIA_CURVE",
            stable="BUSD",
            target="USDC",
            venue="CURVE",
            pool_address="0x4fabb145d64652a948d72533023f6e7a623c7c53",  # BUSD/USDC  # QG-allow: defi-citation
            typical_exit_size_usd="100000",
            slippage_bps="12",
            gas_usd="15",
            priority_rank=2,
        ),
    ),
}


def get_emergency_exit_routes(
    stable: str,
    exit_size_usd: Decimal,
) -> list[ExitRoute]:
    """Return exit routes for ``stable`` sorted by total cost (slippage + gas) ascending.

    Cost metric: ``(expected_slippage_bps_at_size / 10000 * exit_size_usd) + estimated_gas_cost_usd``.
    Routes whose ``typical_exit_size_usd`` is less than 10% of ``exit_size_usd`` are
    ranked after adequately-sized routes (size-overflow signal).

    :param stable: Stablecoin symbol to exit (e.g. ``"USDC"``).
    :param exit_size_usd: Target exit notional in USD.
    :returns: Routes sorted cheapest first; empty list if stable not in registry.
    """
    routes = STABLECOIN_EMERGENCY_EXIT_ROUTES.get(stable.upper())
    if not routes:
        return []

    size_threshold = exit_size_usd * Decimal("0.10")

    def _cost_key(r: ExitRoute) -> tuple[int, Decimal]:
        """(overflow_flag, total_cost_usd) — overflow routes rank after normal."""
        overflow = 1 if r.typical_exit_size_usd < size_threshold else 0
        slippage_cost = (r.expected_slippage_bps_at_size / Decimal("10000")) * exit_size_usd
        total_cost = slippage_cost + r.estimated_gas_cost_usd
        return (overflow, total_cost)

    return sorted(routes, key=_cost_key)


__all__ = [
    "STABLECOIN_EMERGENCY_EXIT_ROUTES",
    "ExitRoute",
    "get_emergency_exit_routes",
]
