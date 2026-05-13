"""Venue error classifications for DeFi protocols."""

from __future__ import annotations

from enum import StrEnum

from ._canonical import CanonicalError
from ._types import ErrorAction, VenueErrorClassification, ve


class DefiAlertType(StrEnum):
    """Canonical DeFi alert type enum.

    Used by alerting-service DeFi rules to classify alert categories.
    """

    HEALTH_FACTOR_CRITICAL = "health_factor_critical"
    POSITION_LIQUIDATED = "position_liquidated"
    WEETH_DEPEG = "weeth_depeg"
    AAVE_UTILIZATION_SPIKE = "aave_utilization_spike"
    FUNDING_RATE_FLIP = "funding_rate_flip"
    FEATURE_STALE = "feature_stale"
    TX_SIMULATION_FAILED = "tx_simulation_failed"
    RATE_DEVIATION = "rate_deviation"


class DefiErrorCode:
    """Known DeFi error codes for structured error classification.

    These codes are used by execution-service DeFi connectors (e.g.
    ``protocols/aave.py``) to classify on-chain revert reasons into structured
    error codes. Execution-service routes on the code prefix (FAIL/RETRY/SKIP)
    via ``classify_venue_error()``. (Docstring corrected 2026-05-12 per slot 8
    execution audit EX-6 — the prior "UDEI connectors" reference predated the
    UDEI → execution-service merge.)

    Each constant aligns with the aave_v3 venue error classifications in
    VENUE_ERRORS_DEFI below.
    """

    INSUFFICIENT_COLLATERAL = "INSUFFICIENT_COLLATERAL"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    NO_COLLATERAL_DEPOSITED = "NO_COLLATERAL_DEPOSITED"
    ASSET_NOT_SUPPORTED = "ASSET_NOT_SUPPORTED"
    ZERO_AMOUNT = "ZERO_AMOUNT"
    TX_REVERTED = "TX_REVERTED"
    GAS_ESTIMATION_FAILED = "GAS_ESTIMATION_FAILED"
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"
    FLASH_LOAN_RECEIVER_INVALID = "FLASH_LOAN_RECEIVER_INVALID"
    FLASH_LOAN_INSUFFICIENT_LIQUIDITY = "FLASH_LOAN_INSUFFICIENT_LIQUIDITY"
    NO_OUTSTANDING_DEBT = "NO_OUTSTANDING_DEBT"
    BORROW_CAP_EXCEEDED = "BORROW_CAP_EXCEEDED"
    SUPPLY_CAP_EXCEEDED = "SUPPLY_CAP_EXCEEDED"

    # Recursive-loop orchestrator codes (added 2026-05-12 per Phase 5 design;
    # routes via FAIL/RETRY/SKIP-prefix dispatcher)
    RECURSIVE_LOOP_ABORTED_HF = "RECURSIVE_LOOP_ABORTED_HF"
    """Pre-iter HF gate triggered; SKIP — caller reports partial result."""
    RECURSIVE_LOOP_GAS_BUDGET_EXCEEDED = "RECURSIVE_LOOP_GAS_BUDGET_EXCEEDED"
    """Gas-budget gate triggered mid-loop; SKIP — caller reports partial result."""
    RECURSIVE_LOOP_SLIPPAGE_REVERT = "RECURSIVE_LOOP_SLIPPAGE_REVERT"
    """Cross-asset swap exceeded slippage_tolerance; RETRY once with widened slippage."""
    RECURSIVE_LOOP_FLASH_RECEIVER_NOT_FOUND = "RECURSIVE_LOOP_FLASH_RECEIVER_NOT_FOUND"
    """UAC flash_loan_receiver_for(...) returned None; FAIL — config bug, no retry."""
    RECURSIVE_LOOP_FLASH_REPAYMENT_INSUFFICIENT = "RECURSIVE_LOOP_FLASH_REPAYMENT_INSUFFICIENT"
    """Receiver's InsufficientRepaymentBalance revert; FAIL — alpha decay or oracle drift."""
    RECURSIVE_LOOP_FLASH_ACTION_FAILED = "RECURSIVE_LOOP_FLASH_ACTION_FAILED"
    """Receiver's ActionFailed(idx, ret) revert; FAIL — idx-encoded for forensic."""
    RECURSIVE_LOOP_PARTIAL_OPEN_NO_UNWIND_FUNDS = "RECURSIVE_LOOP_PARTIAL_OPEN_NO_UNWIND_FUNDS"
    """Persistent driver aborted mid-loop; residue cannot self-unwind (HF too tight);
    FAIL — routes to alerting LIQUIDATION_IMMINENT per Phase 8."""

    # Hyperliquid LIVE perp connector codes (added 2026-05-12 per Phase 6 design)
    HL_INSUFFICIENT_MARGIN = "HL_INSUFFICIENT_MARGIN"
    """HL place_order rejected for insufficient USDC margin; FAIL — caller decides."""
    HL_REDUCE_ONLY_VIOLATION = "HL_REDUCE_ONLY_VIOLATION"
    """reduce_only=True on a size-increasing order; FAIL — caller-side bug."""
    HL_INVALID_TIF = "HL_INVALID_TIF"
    """TimeInForce mismatch (HL accepts Alo / Ioc / Gtc only); FAIL."""
    HL_RATE_LIMITED = "HL_RATE_LIMITED"
    """429 or 1-req/s breach; RETRY with exponential backoff (1s base)."""
    HL_NONCE_TOO_LOW = "HL_NONCE_TOO_LOW"
    """EIP-712 nonce race; RETRY after re-reading latest nonce from /info."""
    HL_SIGNATURE_INVALID = "HL_SIGNATURE_INVALID"
    """Wallet config / chainId drift; FAIL — do NOT retry; alert operator."""
    HL_POSITION_CLOSED = "HL_POSITION_CLOSED"
    """Auto-liquidation race; SKIP — cancel/modify against ghost position."""
    HL_FILL_CONFIRMATION_MISSED = "HL_FILL_CONFIRMATION_MISSED"
    """WS fill arrived > timeout; RETRY — re-query /info userFills before declaring lost."""

    # Oracle error codes (added 2026-05-13 per writegate Phase 2.A +
    # simulation_scenarios Day-1 gap #3/#8)
    ORACLE_STALE = "ORACLE_STALE"
    """Chainlink/Pyth feed heartbeat exceeded threshold; SKIP — caller records honest absence."""
    ORACLE_DEVIATION_EXCEEDED = "ORACLE_DEVIATION_EXCEEDED"
    """Multi-source oracle prices diverge >= sigma threshold; FAIL — triggers KILL_SWITCH_ORACLE_DIVERGENCE."""


class OracleStaleError(CanonicalError):
    """Oracle price feed heartbeat exceeded threshold — feed age too old for safe execution.

    Emitted by execution-service and features-onchain when a Chainlink/Pyth feed
    age exceeds the configured heartbeat threshold. Routes to the
    ORACLE_STALENESS_SECONDS circuit-breaker trip. Action=SKIP so the caller
    records honest absence rather than using a stale price.

    Added 2026-05-13 per writegate Phase 2.A + simulation_scenarios Day-1 gap #3/#8.
    """

    def __init__(
        self,
        feed: str,
        chain: str,
        feed_age_seconds: int,
        threshold_seconds: int,
        venue: str | None = None,
    ) -> None:
        super().__init__(
            code=DefiErrorCode.ORACLE_STALE,
            message=(f"Oracle feed {feed} on {chain} is stale: {feed_age_seconds}s > {threshold_seconds}s threshold"),
            action=ErrorAction.SKIP,
            venue=venue,
        )
        self.feed = feed
        self.chain = chain
        self.feed_age_seconds = feed_age_seconds
        self.threshold_seconds = threshold_seconds


class OracleDeviationError(CanonicalError):
    """Oracle price deviation exceeds sigma threshold across multiple sources.

    Emitted when Chainlink / Pyth / on-chain TWAP prices diverge by >= sigma
    threshold (default 30 sigma per ``oracle_divergence_sigma`` AlertThreshold).
    Triggers KILL_SWITCH_ORACLE_DIVERGENCE alert. Action=FAIL -- position delta
    is undefined when oracle sources disagree at this scale.

    Added 2026-05-13 per writegate Phase 2.A + simulation_scenarios Day-1 gap #8.
    """

    def __init__(
        self,
        asset: str,
        chain: str,
        primary_price: float,
        secondary_price: float,
        sigma_deviation: float,
        venue: str | None = None,
    ) -> None:
        super().__init__(
            code=DefiErrorCode.ORACLE_DEVIATION_EXCEEDED,
            message=(
                f"Oracle price deviation {sigma_deviation:.1f} sigma for {asset} on {chain}: "
                f"primary={primary_price}, secondary={secondary_price}"
            ),
            action=ErrorAction.FAIL,
            venue=venue,
        )
        self.asset = asset
        self.chain = chain
        self.primary_price = primary_price
        self.secondary_price = secondary_price
        self.sigma_deviation = sigma_deviation


VENUE_ERRORS_DEFI: dict[str, list[VenueErrorClassification]] = {
    "balancer": [
        ve(
            "balancer",
            "BAL#001",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized — caller not authorised",
        ),
        ve(
            "balancer",
            "BAL#304",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Swap limit exceeded",
        ),
        ve(
            "balancer",
            "BAL#508",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Pool paused",
        ),
        ve(
            "balancer",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "balancer",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "balancer",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "balancer",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "balancer",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
    "curve": [
        ve(
            "curve",
            "SLIPPAGE_TOO_HIGH",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Slippage exceeds allowed tolerance",
        ),
        ve(
            "curve",
            "POOL_IMBALANCED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Pool reserves severely imbalanced — retry later",
        ),
        ve(
            "curve",
            "RPC_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="JSON-RPC error from Ethereum node",
        ),
        ve(
            "curve",
            "TIMEOUT",
            retry=True,
            reconnect=True,
            action=ErrorAction.RECONNECT,
            desc="RPC call timed out",
        ),
        ve(
            "curve",
            "CONNECTION_ERROR",
            retry=True,
            reconnect=True,
            action=ErrorAction.RECONNECT,
            desc="Network connection failure to RPC endpoint",
        ),
        ve(
            "curve",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "curve",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "curve",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "curve",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "curve",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="API server error",
        ),
    ],
    "ethena": [
        ve(
            "ethena",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "ethena",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "ethena",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "ethena",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "ethena",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
    ],
    "fluid": [
        ve(
            "fluid",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "fluid",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "fluid",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "fluid",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "fluid",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
    ],
    "etherfi": [
        ve(
            "etherfi",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "etherfi",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "etherfi",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "etherfi",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "etherfi",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
    ],
    "lido": [
        ve(
            "lido",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "lido",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "lido",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "lido",
            "WITHDRAWAL_NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Withdrawal request not found",
        ),
        ve(
            "lido",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "lido",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
    ],
    "morpho": [
        ve(
            "morpho",
            "INSUFFICIENT_COLLATERAL",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Collateral value below required threshold",
        ),
        ve(
            "morpho",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request — malformed GraphQL query or invalid parameters",
        ),
        ve(
            "morpho",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "morpho",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "morpho",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "morpho",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "morpho",
            "SUBGRAPH_NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Morpho subgraph not found or unavailable",
        ),
    ],
    "uniswap_v2": [
        ve(
            "uniswap_v2",
            "INSUFFICIENT_LIQUIDITY",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Pair has insufficient liquidity",
        ),
        ve(
            "uniswap_v2",
            "INSUFFICIENT_OUTPUT_AMOUNT",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Output amount below minimum — slippage exceeded",
        ),
        ve(
            "uniswap_v2",
            "SUBGRAPH_NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Subgraph not found or invalid ID",
        ),
        ve(
            "uniswap_v2",
            "AUTH_FAILURE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="API key invalid, malformed, or not found",
        ),
        ve(
            "uniswap_v2",
            "QUERY_ERROR",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="GraphQL query syntax or schema error",
        ),
        ve(
            "uniswap_v2",
            "INDEXING_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Subgraph indexing in progress or stale",
        ),
        ve(
            "uniswap_v2",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "uniswap_v2",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "uniswap_v2",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "uniswap_v2",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "uniswap_v2",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
    "uniswap_v3": [
        ve(
            "uniswap_v3",
            "INSUFFICIENT_LIQUIDITY",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Pool tick range has no liquidity",
        ),
        ve(
            "uniswap_v3",
            "TOO_LITTLE_RECEIVED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Slippage tolerance exceeded",
        ),
        ve(
            "uniswap_v3",
            "PRICE_SLIPPAGE_CHECK",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="sqrtPriceLimitX96 violated",
        ),
        ve(
            "uniswap_v3",
            "SUBGRAPH_NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Subgraph not found or invalid ID",
        ),
        ve(
            "uniswap_v3",
            "AUTH_FAILURE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="API key invalid, malformed, or not found",
        ),
        ve(
            "uniswap_v3",
            "QUERY_ERROR",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="GraphQL query syntax or schema error",
        ),
        ve(
            "uniswap_v3",
            "INDEXING_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Subgraph indexing in progress or stale",
        ),
        ve(
            "uniswap_v3",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "uniswap_v3",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "uniswap_v3",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "uniswap_v3",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "uniswap_v3",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
    "uniswap_v4": [
        ve(
            "uniswap_v4",
            "INSUFFICIENT_LIQUIDITY",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Hook or pool has no liquidity",
        ),
        ve(
            "uniswap_v4",
            "HOOK_DELTA_EXCEEDS_SWAP_AMOUNT",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Hook delta exceeds swap amount",
        ),
        ve(
            "uniswap_v4",
            "SUBGRAPH_NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Subgraph not found or invalid ID",
        ),
        ve(
            "uniswap_v4",
            "AUTH_FAILURE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="API key invalid, malformed, or not found",
        ),
        ve(
            "uniswap_v4",
            "QUERY_ERROR",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="GraphQL query syntax or schema error",
        ),
        ve(
            "uniswap_v4",
            "INDEXING_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Subgraph indexing in progress or stale",
        ),
        ve(
            "uniswap_v4",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "uniswap_v4",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "uniswap_v4",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "uniswap_v4",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "uniswap_v4",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
    "aave_v3": [
        ve(
            "aave_v3",
            "INSUFFICIENT_COLLATERAL",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Health factor below 1 — liquidation risk",
        ),
        ve(
            "aave_v3",
            "INSUFFICIENT_BALANCE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Token balance too low for the requested operation",
        ),
        ve(
            "aave_v3",
            "NO_COLLATERAL_DEPOSITED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="No collateral deposited — cannot borrow",
        ),
        ve(
            "aave_v3",
            "ASSET_NOT_SUPPORTED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Token not supported by AAVE V3 pool",
        ),
        ve(
            "aave_v3",
            "ZERO_AMOUNT",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Operation amount must be greater than zero",
        ),
        ve(
            "aave_v3",
            "TX_REVERTED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="On-chain transaction reverted",
        ),
        ve(
            "aave_v3",
            "GAS_ESTIMATION_FAILED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Gas estimation failed — node may be congested",
        ),
        ve(
            "aave_v3",
            "SLIPPAGE_EXCEEDED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Slippage tolerance exceeded during execution",
        ),
        ve(
            "aave_v3",
            "FLASH_LOAN_RECEIVER_INVALID",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Flash loan receiver is not a valid contract",
        ),
        ve(
            "aave_v3",
            "FLASH_LOAN_INSUFFICIENT_LIQUIDITY",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Insufficient pool liquidity for flash loan amount",
        ),
        ve(
            "aave_v3",
            "NO_OUTSTANDING_DEBT",
            retry=False,
            reconnect=False,
            action=ErrorAction.SKIP,
            desc="No outstanding debt to repay — operation is a no-op",
        ),
        ve(
            "aave_v3",
            "BORROW_CAP_EXCEEDED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Borrow cap for asset reached",
        ),
        ve(
            "aave_v3",
            "SUPPLY_CAP_EXCEEDED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Supply cap for asset reached",
        ),
        ve(
            "aave_v3",
            "PRICE_ORACLE_SENTINEL",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Oracle price feed stale — retry",
        ),
        ve(
            "aave_v3",
            "SUBGRAPH_NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Subgraph not found or invalid ID",
        ),
        ve(
            "aave_v3",
            "AUTH_FAILURE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="API key invalid, malformed, or not found",
        ),
        ve(
            "aave_v3",
            "QUERY_ERROR",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="GraphQL query syntax or schema error",
        ),
        ve(
            "aave_v3",
            "INDEXING_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Subgraph indexing in progress or stale",
        ),
        ve(
            "aave_v3",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "aave_v3",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "aave_v3",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "aave_v3",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "aave_v3",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
    "aave_plasma": [
        ve(
            "aave_plasma",
            "INSUFFICIENT_COLLATERAL",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Health factor below 1 — liquidation risk",
        ),
        ve(
            "aave_plasma",
            "INSUFFICIENT_BALANCE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Token balance too low for the requested operation",
        ),
        ve(
            "aave_plasma",
            "NO_COLLATERAL_DEPOSITED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="No collateral deposited — cannot borrow",
        ),
        ve(
            "aave_plasma",
            "ASSET_NOT_SUPPORTED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Token not supported by AAVE Plasma pool",
        ),
        ve(
            "aave_plasma",
            "ZERO_AMOUNT",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Operation amount must be greater than zero",
        ),
        ve(
            "aave_plasma",
            "TX_REVERTED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="On-chain transaction reverted",
        ),
        ve(
            "aave_plasma",
            "GAS_ESTIMATION_FAILED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Gas estimation failed — node may be congested",
        ),
        ve(
            "aave_plasma",
            "SLIPPAGE_EXCEEDED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Slippage tolerance exceeded during execution",
        ),
        ve(
            "aave_plasma",
            "FLASH_LOAN_RECEIVER_INVALID",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Flash loan receiver is not a valid contract",
        ),
        ve(
            "aave_plasma",
            "FLASH_LOAN_INSUFFICIENT_LIQUIDITY",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Insufficient pool liquidity for flash loan amount",
        ),
        ve(
            "aave_plasma",
            "NO_OUTSTANDING_DEBT",
            retry=False,
            reconnect=False,
            action=ErrorAction.SKIP,
            desc="No outstanding debt to repay — operation is a no-op",
        ),
        ve(
            "aave_plasma",
            "BORROW_CAP_EXCEEDED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Borrow cap for asset reached",
        ),
        ve(
            "aave_plasma",
            "SUPPLY_CAP_EXCEEDED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Supply cap for asset reached",
        ),
        ve(
            "aave_plasma",
            "PRICE_ORACLE_SENTINEL",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Oracle price feed stale — retry",
        ),
        ve(
            "aave_plasma",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "aave_plasma",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "aave_plasma",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "aave_plasma",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "aave_plasma",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
    "instadapp": [
        ve(
            "instadapp",
            "DS_PROXY_EXEC_FAILED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="DSProxy execution failed — revert in spell",
        ),
        ve(
            "instadapp",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "instadapp",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "instadapp",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "instadapp",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
        ve(
            "instadapp",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
    ],
    "defillama": [
        ve(
            "defillama",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "defillama",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "defillama",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "defillama",
            "404",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Protocol or chain not found",
        ),
        ve(
            "defillama",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
        ve(
            "defillama",
            "503",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Service temporarily unavailable",
        ),
        ve(
            "defillama",
            "-32603",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="RPC internal error — retry",
        ),
    ],
}
