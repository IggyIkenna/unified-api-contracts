"""Source capability registry -- declares what each external source provides.

Layers of granularity (coarse → fine):
  1. SourceCapability  — per-source (e.g. "hyperliquid"): domains, live/batch/testnet flags
  2. operation_details — per-operation (e.g. "place_order"): signing, credential, env support
  3. EndpointSpec      — per-HTTP-endpoint (e.g. POST /info): schema, cassette, rate limit
"""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "CapabilityResolutionError",
    "OperationDetail",
    "OperationEnvDetail",
    "SourceCapability",
    "UnsupportedEnvironmentError",
    "UnsupportedModeError",
    "UnsupportedOperationError",
    "register_capability",
    "resolve_capability",
    "validate_mode_env_auth",
    "validate_operation",
]


# ---------------------------------------------------------------------------
# Operation-level environment detail
# ---------------------------------------------------------------------------


class OperationEnvDetail(BaseModel):
    """Per-environment detail for a single operation on a single source.

    Captures the facts that differ between testnet and mainnet for an operation,
    such as signing scheme, required credential type, and data fidelity.

    String fields use free-form values (not enums) to avoid maintenance burden.
    Common values are documented below for consistency.

    signing_scheme common values:
        "hmac_sha256"   — HMAC-SHA256 (most CeFi REST APIs)
        "ed25519"       — Ed25519 signature (some CeFi)
        "l1_action"     — Hyperliquid L1 phantom agent (msgpack + EIP-712)
        "user_signed"   — Hyperliquid user-signed action (EIP-712 direct)
        "eip712"        — EIP-712 typed data (Polymarket L1, DeFi)
        "on_chain"      — Web3 transaction signing (DeFi smart contracts)
        "api_key_header" — API key in HTTP header (data-only sources)
        "fix_logon"     — FIX protocol session logon
        "ib_gateway"    — Interactive Brokers TWS/Gateway connection
        "none"          — No authentication required

    required_credential common values:
        "api_key"           — Standard API key + secret pair
        "api_wallet"        — Agent wallet (can trade, cannot transfer/withdraw)
        "main_wallet"       — Main wallet (full access including transfers)
        "wallet_private_key" — Web3 wallet private key for on-chain signing
        "oauth_token"       — OAuth2 bearer token
        "cert"              — Client certificate (mTLS)
        "session_token"     — Session-based auth
        "none"              — No credentials required

    data_fidelity common values:
        "production"        — Real production data
        "synthetic"         — Fake test tokens/prices (testnet)
        "production_mirror" — Fork of production state (Anvil/Tenderly)
        "delayed"           — Real data with delay
    """

    supported: bool = True
    signing_scheme: str | None = None
    required_credential: str | None = None
    base_url: str | None = None
    data_fidelity: str | None = None
    notes: str | None = None


class OperationDetail(BaseModel):
    """Per-operation capability detail, keyed by environment.

    Example::

        OperationDetail(environments={
            "mainnet": OperationEnvDetail(
                signing_scheme="l1_action",
                required_credential="api_wallet",
            ),
            "testnet": OperationEnvDetail(
                supported=False,
                notes="API wallet cannot transfer; use UI",
            ),
        })
    """

    environments: dict[str, OperationEnvDetail] = {}


# ---------------------------------------------------------------------------
# Source-level capability
# ---------------------------------------------------------------------------


class SourceCapability(BaseModel):
    """Declares the capabilities of an external data source."""

    source: str
    domains: list[str]  # e.g. ["market", "execution", "reference", "position"]
    crosscutting: list[str]  # e.g. ["errors", "rate_limits", "latency", "connectivity"]
    supports_live: bool = False
    supports_batch: bool = False
    supports_historical: bool = False
    supports_testnet: bool = False
    supports_mainnet: bool = True
    auth_scope: list[str] = []  # ["api_key", "oauth", "cert", "none"]
    auth_environments: dict[str, str] = {}  # {"test": "testnet_key", "prod": "prod_key"}
    operations: dict[str, list[str]] = {}  # {"market": ["ticker", "orderbook"], ...}
    supported_testing_stages: list[str] = []  # TestingStage string values this source supports

    # --- New: operation-level detail (optional, backwards-compatible) ---
    operation_details: dict[str, OperationDetail] = {}
    """Per-operation environment detail. Keyed by operation name (must match a value
    in ``operations``). When absent for an operation, falls back to source-level flags."""

    base_urls: dict[str, str] = {}
    """Per-environment base URLs. e.g. {"mainnet": "https://api.x.com", "testnet": "https://testnet.x.com"}"""

    margin_model: dict[str, str] = {}
    """Per-environment margin model. e.g. {"mainnet": "cross", "testnet": "unified"}
    Common values: "cross", "isolated", "unified", "portfolio", "none"."""


class CapabilityResolutionError(RuntimeError):
    """Raised when (source, operation) combination not declared in registry."""

    def __init__(self, source: str, operation: str) -> None:
        self.source = source
        self.operation = operation
        super().__init__(f"No capability declared for {source}.{operation}")


class UnsupportedModeError(RuntimeError):
    """Source doesn't support the requested mode (e.g., live for a batch-only source)."""

    def __init__(self, source: str, requested_mode: str, supported_modes: list[str]) -> None:
        self.source = source
        self.requested_mode = requested_mode
        self.supported_modes = supported_modes
        self.suggested_resolution = f"Use one of: {', '.join(supported_modes)}"
        super().__init__(f"{source} does not support mode '{requested_mode}'. Supported: {supported_modes}")


class UnsupportedEnvironmentError(RuntimeError):
    """Source doesn't support the requested environment."""

    def __init__(self, source: str, requested_env: str, supported_envs: list[str]) -> None:
        self.source = source
        self.requested_env = requested_env
        self.supported_envs = supported_envs
        self.suggested_resolution = f"Use one of: {', '.join(supported_envs)}"
        super().__init__(f"{source} does not support environment '{requested_env}'. Supported: {supported_envs}")


_CAPABILITIES: dict[str, SourceCapability] = {}


def register_capability(cap: SourceCapability) -> None:
    """Register a source's capability declaration."""
    _CAPABILITIES[cap.source] = cap


def resolve_capability(source: str) -> SourceCapability:
    """Resolve capability record for a source. Raises CapabilityResolutionError if not found."""
    if source not in _CAPABILITIES:
        raise CapabilityResolutionError(source, "*")
    return _CAPABILITIES[source]


def validate_mode_env_auth(
    capability: SourceCapability,
    mode: str | None = None,
    env: str | None = None,
) -> None:
    """Validate mode/env against capability. Raises UTL error classes on mismatch.

    Args:
        capability: The resolved SourceCapability for the data source.
        mode: If provided, validates "live" or "batch" against capability flags.
        env: If provided, validates "testnet" against capability flags.

    Raises:
        UnsupportedModeError: When the source does not support the requested mode.
        UnsupportedEnvironmentError: When the source does not support the requested env.
    """
    if mode and mode == "live" and not capability.supports_live:
        supported: list[str] = []
        if capability.supports_batch:
            supported.append("batch")
        raise UnsupportedModeError(capability.source, mode, supported)

    if mode and mode == "batch" and not capability.supports_batch:
        supported = []
        if capability.supports_live:
            supported.append("live")
        raise UnsupportedModeError(capability.source, mode, supported)

    if env and env == "testnet" and not capability.supports_testnet:
        supported_envs: list[str] = []
        if capability.supports_mainnet:
            supported_envs.append("mainnet")
        raise UnsupportedEnvironmentError(capability.source, env, supported_envs)


def validate_operation(
    source: str,
    operation: str,
    env: str = "mainnet",
) -> OperationEnvDetail:
    """Validate and return environment detail for a specific operation on a source.

    If ``operation_details`` has an entry for this operation+env, return it (and raise
    if ``supported=False``). Otherwise fall back to source-level ``validate_mode_env_auth``.

    Args:
        source: Source identifier (e.g. "hyperliquid").
        operation: Operation name (e.g. "place_order", "usd_class_transfer").
        env: Environment — "mainnet" or "testnet".

    Returns:
        OperationEnvDetail with signing/credential info for the caller.

    Raises:
        CapabilityResolutionError: If source not registered.
        UnsupportedOperationError: If operation is explicitly unsupported in this env.
    """
    cap = resolve_capability(source)

    detail = cap.operation_details.get(operation)
    if detail is None:
        # No per-operation detail — fall back to source-level check
        validate_mode_env_auth(cap, env=env)
        return OperationEnvDetail()

    env_detail = detail.environments.get(env)
    if env_detail is None:
        # Operation exists but no entry for this env — fall back to source-level
        validate_mode_env_auth(cap, env=env)
        return OperationEnvDetail()

    if not env_detail.supported:
        raise UnsupportedOperationError(source, operation, env, env_detail.notes)

    return env_detail


class UnsupportedOperationError(RuntimeError):
    """Raised when an operation is explicitly unsupported in the requested environment."""

    def __init__(self, source: str, operation: str, env: str, notes: str | None = None) -> None:
        self.source = source
        self.operation = operation
        self.env = env
        self.notes = notes
        msg = f"{source}.{operation} is not supported on {env}"
        if notes:
            msg += f": {notes}"
        super().__init__(msg)
