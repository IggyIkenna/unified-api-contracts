"""Unified venue context resolution — single query for execution pattern, auth, signing, and constraints.

Bridges three registries into one VenueContext object:
  1. SourceCapability + operation_details (capability.py)
  2. SportsVenueType + SportsAuthMethod + CAPTCHA_RISK (sports_venue_constants.py)
  3. InstructionConstraint (instruction_constraints.py)

Consumers call ``resolve_venue_context()`` to get everything they need before
executing against a venue, or ``compose_validation()`` to validate an instruction
end-to-end (structural + runtime) in one call.

The ``requires_operation_validation`` decorator can be applied to service methods
to automatically call ``validate_operation()`` before the method body, blocking
on ``UnsupportedOperationError`` and gracefully degrading on all other exceptions.
"""

from __future__ import annotations

import functools
import inspect
import logging
import re
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from ._sports_venue_constants import (
    SPORTS_AUTH_MAP,
    SPORTS_CAPTCHA_RISK,
    SPORTS_VENUE_TYPE_MAP,
    SUPPORTED_MARKET_TYPES,
)
from .capability import (
    CapabilityResolutionError,
    OperationEnvDetail,
    UnsupportedOperationError,
    resolve_capability,
    validate_operation,
)
from .instruction_constraints import (
    validate_instruction,
)
from .venue_constants import VENUE_CATEGORY_MAP

_logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., object])

__all__ = [
    "VenueContext",
    "compose_validation",
    "requires_operation_validation",
    "resolve_venue_context",
]


def _resolve_venue_value(
    args: tuple[object, ...],
    kwargs: dict[str, object],
    sig: inspect.Signature,
    *,
    venue_param: str | None,
    venue_attr: str | None,
) -> str:
    """Extract the venue string from method arguments or an attribute on *self*.

    When *venue_attr* is given (e.g. ``"self.venue_id"``), the value is read from
    the first positional argument (assumed to be *self*) by traversing the
    dot-separated attribute chain.

    When *venue_param* is given, it is resolved from the call signature by name or
    by position.
    """
    if venue_attr is not None:
        parts = venue_attr.split(".")
        # First part must be "self" — the first positional arg
        obj = args[0]
        for attr_name in parts[1:]:
            obj = getattr(obj, attr_name)
        return str(obj)

    if venue_param is not None:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return str(bound.arguments[venue_param])

    msg = "Either venue_param or venue_attr must be provided"
    raise TypeError(msg)


def _resolve_env_value(
    args: tuple[object, ...],
    kwargs: dict[str, object],
    sig: inspect.Signature,
    *,
    env_param: str,
) -> str:
    """Extract the env string from method arguments."""
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    return str(bound.arguments[env_param])


def requires_operation_validation(
    *,
    venue_param: str | None = None,
    venue_attr: str | None = None,
    operation_name: str,
    env_param: str = "env",
) -> Callable[[_F], _F]:
    """Decorator that validates an operation before the decorated method runs.

    Calls ``validate_operation(venue, operation_name, env)`` before the wrapped
    method body.

    - **UnsupportedOperationError** is re-raised (hard block).
    - All other exceptions from the validation call are logged and swallowed
      (graceful degradation) so that a missing registry entry does not break
      callers.

    Works on both sync and async methods.

    Args:
        venue_param: Name of the method parameter that holds the venue string.
            Mutually exclusive with *venue_attr*.
        venue_attr: Dot-separated attribute path on *self* (e.g. ``"self.venue_id"``).
            Mutually exclusive with *venue_param*.
        operation_name: Fixed operation name passed to ``validate_operation()``.
        env_param: Name of the method parameter that holds the environment string.
            Defaults to ``"env"``.

    Example — venue from parameter::

        @requires_operation_validation(venue_param="venue", operation_name="place_order")
        async def place_order(self, venue: str, symbol: str, env: str = "mainnet"):
            ...

    Example — venue from self attribute::

        @requires_operation_validation(venue_attr="self.venue_id", operation_name="supply")
        def supply(self, amount: float, env: str = "mainnet"):
            ...
    """
    if venue_param is None and venue_attr is None:
        msg = "Either venue_param or venue_attr must be provided"
        raise TypeError(msg)
    if venue_param is not None and venue_attr is not None:
        msg = "venue_param and venue_attr are mutually exclusive"
        raise TypeError(msg)

    def decorator(fn: _F) -> _F:
        sig = inspect.signature(fn)

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: object, **kwargs: object) -> object:
                try:
                    venue = _resolve_venue_value(args, kwargs, sig, venue_param=venue_param, venue_attr=venue_attr)
                    env = _resolve_env_value(args, kwargs, sig, env_param=env_param)
                    validate_operation(venue, operation_name, env)
                except UnsupportedOperationError:
                    raise
                except Exception:
                    _logger.debug(
                        "Operation validation skipped for %s (graceful degradation)",
                        operation_name,
                        exc_info=True,
                    )
                return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: object, **kwargs: object) -> object:
            try:
                venue = _resolve_venue_value(args, kwargs, sig, venue_param=venue_param, venue_attr=venue_attr)
                env = _resolve_env_value(args, kwargs, sig, env_param=env_param)
                validate_operation(venue, operation_name, env)
            except UnsupportedOperationError:
                raise
            except Exception:
                _logger.debug(
                    "Operation validation skipped for %s (graceful degradation)",
                    operation_name,
                    exc_info=True,
                )
            return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


class VenueContext(BaseModel):
    """Consolidated execution context for a venue + operation + environment.

    Merges source capability, sports-specific metadata, and operation-level
    detail into one queryable object. Returned by ``resolve_venue_context()``.
    """

    # Identity
    venue: str
    source: str
    env: str
    venue_category: str | None = None  # "cefi", "defi", "tradfi", "sports"

    # Execution pattern (derived)
    execution_pattern: str = "unknown"
    """Derived execution pattern: clob_api, on_chain_tx, web_scraper, data_only, fix_protocol, ib_gateway."""

    # Operation detail (from capability registry)
    operation_env_detail: OperationEnvDetail | None = None

    # Sports-specific (from _sports_venue_constants.py)
    sports_venue_type: str | None = None  # SportsVenueType value
    sports_auth_method: str | None = None  # SportsAuthMethod value
    captcha_risk: bool = False
    supported_market_types: list[str] = []

    # Source-level metadata
    base_url: str | None = None
    margin_model_value: str | None = None
    supports_testnet: bool = False


def _derive_execution_pattern(
    signing_scheme: str | None,
    sports_venue_type: str | None,
    venue_category: str | None,
) -> str:
    """Derive the execution pattern from available metadata."""
    if sports_venue_type == "web_scraper":
        return "web_scraper"
    if sports_venue_type == "dfs_platform":
        return "web_scraper"
    if sports_venue_type == "data_only":
        return "data_only"
    if sports_venue_type in ("exchange_api", "bookmaker_api", "prediction_market_api"):
        return "clob_api"
    if signing_scheme == "on_chain":
        return "on_chain_tx"
    if signing_scheme == "fix_logon":
        return "fix_protocol"
    if signing_scheme == "ib_gateway":
        return "ib_gateway"
    if signing_scheme in ("none", "api_key_header") and venue_category not in ("cefi", "tradfi", "sports"):
        return "data_only"
    if signing_scheme in ("hmac_sha256", "hmac_sha384", "hmac_sha512", "ed25519", "jwt", "l1_action", "eip712"):
        return "clob_api"
    if venue_category in ("cefi", "tradfi"):
        return "clob_api"
    if venue_category == "defi":
        return "on_chain_tx"
    return "data_only"


def resolve_venue_context(
    venue: str,
    operation: str | None = None,
    env: str = "mainnet",
) -> VenueContext:
    """Resolve full execution context for a venue.

    Merges source capability, sports metadata, and operation detail into one object.
    Does NOT raise for unsupported operations — use ``compose_validation()`` for that.

    Args:
        venue: Venue identifier (e.g. "HYPERLIQUID", "BETFAIR", "DRAFTKINGS").
        operation: Optional operation name. If provided, includes operation_env_detail.
        env: Environment — "mainnet" or "testnet".

    Returns:
        VenueContext with all available metadata merged.

    Raises:
        CapabilityResolutionError: If the venue's source is not registered.
    """
    # Resolve source name (venue constants use uppercase, capabilities use lowercase)
    source = venue.lower().replace("-", "_").replace(" ", "_")
    # Build candidate list for capability lookup
    candidates = [source]
    # Strip product suffix for split venues (e.g. "BINANCE-SPOT" → "binance")
    parts = source.split("_")
    if len(parts) > 1 and parts[-1] in ("spot", "futures", "eth", "ethereum", "base", "plasma", "v3"):
        candidates.append(parts[0])
        # Also try without last two parts (e.g. "aave_v3_eth" → "aave")
        if len(parts) > 2:
            candidates.append(parts[0])
    # Try without version suffix (e.g. "aave_v3" → "aave")
    if len(parts) == 2 and parts[1].startswith("v"):
        candidates.append(parts[0])
    # Strip trailing version from protocol names (aavev3 → aave, compoundv3 → compound)
    for c in list(candidates):
        stripped = re.sub(r"v\d+$", "", c)
        if stripped and stripped != c:
            candidates.append(stripped)
    candidates.append(venue.lower())

    # Try to resolve capability
    cap = None
    source_lookup = source
    for alias in dict.fromkeys(candidates):  # deduplicate, preserve order
        try:
            cap = resolve_capability(alias)
            source_lookup = alias
            break
        except CapabilityResolutionError:
            continue

    venue_category = VENUE_CATEGORY_MAP.get(venue)

    # Sports-specific metadata
    sports_venue_type: str | None = None
    sports_auth_method: str | None = None
    captcha_risk = False
    supported_market_types_list: list[str] = []

    if venue_category == "sports":
        sports_venue_type = SPORTS_VENUE_TYPE_MAP.get(venue)
        sports_auth_method = SPORTS_AUTH_MAP.get(venue)
        captcha_risk = venue in SPORTS_CAPTCHA_RISK
        market_types = SUPPORTED_MARKET_TYPES.get(venue)
        if market_types:
            supported_market_types_list = sorted(str(mt) for mt in market_types)

    # Operation-level detail
    op_detail: OperationEnvDetail | None = None
    if cap is not None and operation is not None:
        op_info = cap.operation_details.get(operation)
        if op_info is not None:
            op_detail = op_info.environments.get(env)

    # Derive execution pattern
    signing_scheme = op_detail.signing_scheme if op_detail else None
    execution_pattern = _derive_execution_pattern(signing_scheme, sports_venue_type, venue_category)

    # Base URL and margin model
    base_url: str | None = None
    margin_model_value: str | None = None
    supports_testnet = False

    if cap is not None:
        base_url = cap.base_urls.get(env)
        margin_model_value = cap.margin_model.get(env)
        supports_testnet = cap.supports_testnet

    return VenueContext(
        venue=venue,
        source=source_lookup,
        env=env,
        venue_category=venue_category,
        execution_pattern=execution_pattern,
        operation_env_detail=op_detail,
        sports_venue_type=sports_venue_type,
        sports_auth_method=sports_auth_method,
        captcha_risk=captcha_risk,
        supported_market_types=supported_market_types_list,
        base_url=base_url,
        margin_model_value=margin_model_value,
        supports_testnet=supports_testnet,
    )


def compose_validation(
    venue: str,
    instruction_type: str,
    operation: str,
    env: str = "mainnet",
    order_type: str | None = None,
    instrument_type: str | None = None,
) -> OperationEnvDetail:
    """Validate an instruction end-to-end: structural + runtime, in one call.

    Step 1 (structural): Calls ``validate_instruction()`` to check instruction_type
    is valid for the given order_type, instrument_type, and venue_category.

    Step 2 (runtime): Calls ``validate_operation()`` to check the specific operation
    is supported on this venue in this environment, and returns signing/credential detail.

    Args:
        venue: Venue identifier (e.g. "HYPERLIQUID").
        instruction_type: Instruction type (e.g. "TRADE", "SWAP", "ZERO_ALPHA").
        operation: Operation name (e.g. "place_order", "supply").
        env: Environment — "mainnet" or "testnet".
        order_type: Optional order type (e.g. "LIMIT", "MARKET").
        instrument_type: Optional instrument type (e.g. "PERPETUAL", "POOL").

    Returns:
        OperationEnvDetail with signing/credential info.

    Raises:
        InstructionValidationError: If instruction_type is structurally invalid.
        CapabilityResolutionError: If source is not registered.
        UnsupportedOperationError: If operation is unsupported in this env.
    """
    # Step 1: Structural validation
    venue_category = VENUE_CATEGORY_MAP.get(venue)
    validate_instruction(
        instruction_type=instruction_type,
        order_type=order_type,
        instrument_type=instrument_type,
        venue_category=venue_category,
    )

    # Step 2: Runtime validation — reuse same candidate logic as resolve_venue_context
    source = venue.lower().replace("-", "_").replace(" ", "_")
    candidates = [source]
    parts = source.split("_")
    if len(parts) > 1 and parts[-1] in ("spot", "futures", "eth", "ethereum", "base", "plasma", "v3"):
        candidates.append(parts[0])
        if len(parts) > 2:
            candidates.append(parts[0])
    if len(parts) == 2 and parts[1].startswith("v"):
        candidates.append(parts[0])
    # Strip trailing version from protocol names (aavev3 → aave, compoundv3 → compound)
    for c in list(candidates):
        stripped = re.sub(r"v\d+$", "", c)
        if stripped and stripped != c:
            candidates.append(stripped)
    candidates.append(venue.lower())

    for alias in dict.fromkeys(candidates):
        try:
            return validate_operation(alias, operation, env)
        except CapabilityResolutionError:
            continue

    raise CapabilityResolutionError(venue, operation)
