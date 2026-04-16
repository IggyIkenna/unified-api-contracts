"""Transfer type discrimination and venue wallet capabilities.

Provides schemas for routing transfers to the correct execution path:
on-chain (Copper/local key), CeFi withdrawal (CCXT), CeFi internal
(exchange API for funding→trading), or custody transfer.

Also defines per-venue wallet capabilities so execution-service knows
which venues require funding→trading internal transfers, which support
direct-to-trading deposits, and which use custody providers.

Used by:
- execution-service transfer_handler (routes transfers by type)
- position-balance-monitor-service treasury_monitor (initiates transfers)
- unified-trading-system-ui Transfer Monitor page (displays wallet state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TransferType(StrEnum):
    """How a transfer should be executed."""

    ON_CHAIN = "ON_CHAIN"
    """Direct blockchain transfer — signed via Copper or local key.
    Used for DeFi→DeFi same-chain, DeFi→CeFi deposit, CeFi→DeFi withdrawal.
    Takes minutes (blockchain confirmations). Gas costs apply.
    """

    CEX_WITHDRAWAL = "CEX_WITHDRAWAL"
    """Exchange withdrawal to external address — via CCXT withdraw().
    Used for CeFi→CeFi cross-exchange or CeFi→DeFi.
    Takes minutes to hours (exchange processing + blockchain).
    Withdrawal fees apply.
    """

    CEX_INTERNAL = "CEX_INTERNAL"
    """Exchange internal transfer between wallet types — via exchange API.
    Used for funding→trading, spot→futures on same exchange.
    Instant. No fees. No blockchain.
    Examples: Binance universal transfer, OKX asset transfer, Bybit inter-transfer.
    """

    CUSTODY_TRANSFER = "CUSTODY_TRANSFER"
    """Transfer via custody provider (Copper, Fireblocks) — MPC signed.
    Used for DeFi operations where keys are in custody.
    Takes 1-5s for MPC signing + blockchain confirmation time.
    """

    BRIDGE = "BRIDGE"
    """Cross-chain bridge transfer — via bridge protocol (Across, etc.).
    Used for DeFi→DeFi cross-chain.
    Takes minutes. Bridge fees + gas apply.
    """


class WalletType(StrEnum):
    """Types of wallets on a venue."""

    FUNDING = "FUNDING"
    """Funding/deposit wallet — where deposits land. Not directly tradeable."""

    TRADING = "TRADING"
    """Trading/derivatives wallet — where orders are placed from."""

    SPOT = "SPOT"
    """Spot wallet — for spot trading (some venues separate this)."""

    UNIFIED = "UNIFIED"
    """Unified account — single wallet for all operations (Bybit unified, OKX unified)."""

    ON_CHAIN = "ON_CHAIN"
    """On-chain wallet — DeFi, custody, or self-hosted."""


@dataclass(frozen=True)
class VenueWalletCapabilities:
    """Per-venue knowledge of wallet structure and transfer capabilities.

    SSOT for execution-service transfer routing: which venues require
    funding→trading transfers, which support direct-to-trading deposits,
    and what custody provider is needed.
    """

    venue: str
    """Canonical venue name (e.g. 'BINANCE-FUTURES', 'AAVE_V3')."""

    # --- Wallet structure ---
    deposits_to: WalletType
    """Where client deposits land: FUNDING, TRADING, UNIFIED, ON_CHAIN."""

    trading_wallet_type: WalletType
    """Wallet type used for placing orders: TRADING, SPOT, UNIFIED, ON_CHAIN."""

    requires_internal_transfer: bool = False
    """True if deposits land in a different wallet than trading.
    Binance: True (funding→futures). OKX: True (funding→trading).
    Bybit unified: False. DeFi: False.
    """

    # --- Internal transfer support ---
    supports_internal_transfer: bool = False
    """Can move between wallet types within the venue (exchange internal API)."""

    internal_transfer_instant: bool = True
    """True for CeFi internal (instant), False for on-chain moves."""

    # --- External transfer support ---
    supports_withdrawal: bool = True
    supports_deposit: bool = True
    withdrawal_requires_whitelist: bool = False

    # --- Custody ---
    custody_provider: str = ""
    """'copper', 'fireblocks', or '' for direct (CCXT/self-hosted key)."""

    # --- CCXT compatibility ---
    ccxt_exchange_id: str = ""
    """CCXT exchange identifier for API calls (e.g. 'binance', 'okx', 'bybit')."""

    ccxt_transfer_params: dict[str, str] = field(default_factory=dict)
    """Venue-specific params for CCXT transfer() call.
    E.g. Binance: {'type': 'MAIN_UMFUTURE'}, OKX: {'type': '0'→'18'}.
    """


# ---------------------------------------------------------------------------
# Canonical venue wallet capabilities registry
# ---------------------------------------------------------------------------

VENUE_WALLET_CAPABILITIES: dict[str, VenueWalletCapabilities] = {
    # ── CeFi ──────────────────────────────────────────────────────────
    "BINANCE-SPOT": VenueWalletCapabilities(
        venue="BINANCE-SPOT",
        deposits_to=WalletType.FUNDING,
        trading_wallet_type=WalletType.SPOT,
        requires_internal_transfer=True,
        supports_internal_transfer=True,
        ccxt_exchange_id="binance",
        ccxt_transfer_params={"type": "MAIN_MARGIN"},
    ),
    "BINANCE-FUTURES": VenueWalletCapabilities(
        venue="BINANCE-FUTURES",
        deposits_to=WalletType.FUNDING,
        trading_wallet_type=WalletType.TRADING,
        requires_internal_transfer=True,
        supports_internal_transfer=True,
        ccxt_exchange_id="binance",
        ccxt_transfer_params={"type": "MAIN_UMFUTURE"},
    ),
    "OKX": VenueWalletCapabilities(
        venue="OKX",
        deposits_to=WalletType.FUNDING,
        trading_wallet_type=WalletType.TRADING,
        requires_internal_transfer=True,
        supports_internal_transfer=True,
        ccxt_exchange_id="okx",
        ccxt_transfer_params={"type": "0"},  # 0=funding→trading in OKX API
    ),
    "BYBIT": VenueWalletCapabilities(
        venue="BYBIT",
        deposits_to=WalletType.UNIFIED,
        trading_wallet_type=WalletType.UNIFIED,
        requires_internal_transfer=False,  # Unified account — no transfer needed
        supports_internal_transfer=True,  # Can still do inter-transfer if needed
        ccxt_exchange_id="bybit",
    ),
    "BYBIT-FUTURES": VenueWalletCapabilities(
        venue="BYBIT-FUTURES",
        deposits_to=WalletType.UNIFIED,
        trading_wallet_type=WalletType.UNIFIED,
        requires_internal_transfer=False,
        supports_internal_transfer=True,
        ccxt_exchange_id="bybit",
    ),
    "DERIBIT": VenueWalletCapabilities(
        venue="DERIBIT",
        deposits_to=WalletType.TRADING,
        trading_wallet_type=WalletType.TRADING,
        requires_internal_transfer=False,  # Direct to trading
        ccxt_exchange_id="deribit",
    ),
    "HYPERLIQUID": VenueWalletCapabilities(
        venue="HYPERLIQUID",
        deposits_to=WalletType.ON_CHAIN,
        trading_wallet_type=WalletType.ON_CHAIN,
        requires_internal_transfer=False,
        custody_provider="copper",
    ),
    # ── DeFi ──────────────────────────────────────────────────────────
    "AAVE_V3": VenueWalletCapabilities(
        venue="AAVE_V3",
        deposits_to=WalletType.ON_CHAIN,
        trading_wallet_type=WalletType.ON_CHAIN,
        requires_internal_transfer=False,
        custody_provider="copper",
    ),
    "UNISWAP_V3": VenueWalletCapabilities(
        venue="UNISWAP_V3",
        deposits_to=WalletType.ON_CHAIN,
        trading_wallet_type=WalletType.ON_CHAIN,
        requires_internal_transfer=False,
        custody_provider="copper",
    ),
    "ETHERFI": VenueWalletCapabilities(
        venue="ETHERFI",
        deposits_to=WalletType.ON_CHAIN,
        trading_wallet_type=WalletType.ON_CHAIN,
        requires_internal_transfer=False,
        custody_provider="copper",
    ),
    "MORPHO": VenueWalletCapabilities(
        venue="MORPHO",
        deposits_to=WalletType.ON_CHAIN,
        trading_wallet_type=WalletType.ON_CHAIN,
        requires_internal_transfer=False,
        custody_provider="copper",
    ),
    # ── TradFi ────────────────────────────────────────────────────────
    "CME": VenueWalletCapabilities(
        venue="CME",
        deposits_to=WalletType.TRADING,
        trading_wallet_type=WalletType.TRADING,
        requires_internal_transfer=False,
        supports_withdrawal=False,  # TradFi — not crypto
        supports_deposit=False,
    ),
    # ── Sports / Prediction ───────────────────────────────────────────
    "BETFAIR": VenueWalletCapabilities(
        venue="BETFAIR",
        deposits_to=WalletType.TRADING,
        trading_wallet_type=WalletType.TRADING,
        requires_internal_transfer=False,
    ),
    "POLYMARKET": VenueWalletCapabilities(
        venue="POLYMARKET",
        deposits_to=WalletType.ON_CHAIN,
        trading_wallet_type=WalletType.ON_CHAIN,
        requires_internal_transfer=False,
        custody_provider="copper",
    ),
}


def get_venue_wallet_capabilities(venue: str) -> VenueWalletCapabilities | None:
    """Look up wallet capabilities for a venue.

    Returns None if venue not in registry (caller should handle unknown venues).
    """
    return VENUE_WALLET_CAPABILITIES.get(venue)


def classify_transfer_type(
    from_venue: str,
    to_venue: str,
    from_capabilities: VenueWalletCapabilities | None = None,
    to_capabilities: VenueWalletCapabilities | None = None,
) -> TransferType:
    """Classify what type of transfer this is based on venues.

    Args:
        from_venue: Source venue canonical name.
        to_venue: Destination venue canonical name.
        from_capabilities: Source venue wallet capabilities (looked up if None).
        to_capabilities: Destination venue wallet capabilities (looked up if None).

    Returns:
        TransferType indicating the execution path for this transfer.
    """
    from_cap = from_capabilities or get_venue_wallet_capabilities(from_venue)
    to_cap = to_capabilities or get_venue_wallet_capabilities(to_venue)

    # Same venue, different wallet type → internal transfer
    base_from = from_venue.split("-")[0] if "-" in from_venue else from_venue
    base_to = to_venue.split("-")[0] if "-" in to_venue else to_venue
    if base_from == base_to:
        if from_cap and from_cap.supports_internal_transfer:
            return TransferType.CEX_INTERNAL
        return TransferType.ON_CHAIN  # DeFi same-venue (shouldn't happen but safe)

    # DeFi to DeFi — on-chain or bridge
    from_is_onchain = from_cap is not None and from_cap.trading_wallet_type == WalletType.ON_CHAIN
    to_is_onchain = to_cap is not None and to_cap.trading_wallet_type == WalletType.ON_CHAIN
    if from_is_onchain and to_is_onchain:
        return TransferType.ON_CHAIN  # Same chain assumed; caller can override to BRIDGE

    # Custody provider involved → custody transfer
    if from_cap and from_cap.custody_provider:
        return TransferType.CUSTODY_TRANSFER
    if to_cap and to_cap.custody_provider:
        return TransferType.CUSTODY_TRANSFER

    # Default: CeFi withdrawal (cross-exchange)
    return TransferType.CEX_WITHDRAWAL


__all__ = [
    "VENUE_WALLET_CAPABILITIES",
    "TransferType",
    "VenueWalletCapabilities",
    "WalletType",
    "classify_transfer_type",
    "get_venue_wallet_capabilities",
]
