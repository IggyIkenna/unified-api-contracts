"""Source capability registry -- declares what each external source provides."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "CapabilityResolutionError",
    "SourceCapability",
    "register_capability",
    "resolve_capability",
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
