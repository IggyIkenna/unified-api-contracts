"""Source capability registry -- declares what each external source provides."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "CapabilityResolutionError",
    "SourceCapability",
    "register_capability",
    "resolve_capability",
    "validate_mode_env_auth",
]


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


class CapabilityResolutionError(RuntimeError):
    """Raised when (source, operation) combination not declared in registry."""

    def __init__(self, source: str, operation: str) -> None:
        self.source = source
        self.operation = operation
        super().__init__(f"No capability declared for {source}.{operation}")


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
        from unified_trading_library import UnsupportedModeError  # noqa: qg-inside-import

        supported: list[str] = []
        if capability.supports_batch:
            supported.append("batch")
        raise UnsupportedModeError(capability.source, mode, supported)

    if mode and mode == "batch" and not capability.supports_batch:
        from unified_trading_library import UnsupportedModeError  # noqa: qg-inside-import

        supported = []
        if capability.supports_live:
            supported.append("live")
        raise UnsupportedModeError(capability.source, mode, supported)

    if env and env == "testnet" and not capability.supports_testnet:
        from unified_trading_library import UnsupportedEnvironmentError  # noqa: qg-inside-import

        supported_envs: list[str] = []
        if capability.supports_mainnet:
            supported_envs.append("mainnet")
        raise UnsupportedEnvironmentError(capability.source, env, supported_envs)
