"""Fault injection middleware for integration testing.

Provides configurable failure scenarios for httpx clients to validate
circuit breakers, retries, and graceful degradation under real failure conditions.

Usage:
    fault_middleware = FaultInjectionMiddleware(error_rate=0.5, latency_ms=100)
    async with fault_middleware.apply_to_httpx(base_transport):
        response = await client.get(url)
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FaultConfig:
    """Configuration for fault injection scenarios."""

    latency_ms: float = 0.0
    error_rate: float = 0.0  # 0.0-1.0 probability of returning 500
    timeout_rate: float = 0.0  # 0.0-1.0 probability of raising TimeoutError
    rate_limit_rate: float = 0.0  # 0.0-1.0 probability of returning 429
    enabled: bool = True

    def should_inject_error(self) -> bool:
        return self.enabled and random.random() < self.error_rate

    def should_inject_timeout(self) -> bool:
        return self.enabled and random.random() < self.timeout_rate

    def should_inject_rate_limit(self) -> bool:
        return self.enabled and random.random() < self.rate_limit_rate


class FaultInjectionTransport(httpx.AsyncBaseTransport):
    """HTTPX transport wrapper that injects configurable faults."""

    def __init__(
        self,
        wrapped: httpx.AsyncBaseTransport,
        config: FaultConfig,
    ) -> None:
        self._wrapped = wrapped
        self._config = config

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not self._config.enabled:
            return await self._wrapped.handle_async_request(request)

        if self._config.should_inject_timeout():
            logger.debug("FaultInjection: timeout on %s", request.url)
            raise httpx.TimeoutException(f"Injected timeout for {request.url}")

        if self._config.should_inject_rate_limit():
            logger.debug("FaultInjection: 429 rate-limit on %s", request.url)
            return httpx.Response(429, json={"error": "rate_limited"})

        if self._config.should_inject_error():
            logger.debug("FaultInjection: 500 error on %s", request.url)
            return httpx.Response(500, json={"error": "injected_server_error"})

        if self._config.latency_ms > 0:
            await asyncio.sleep(self._config.latency_ms / 1000.0)

        return await self._wrapped.handle_async_request(request)


def make_fault_transport(
    config: FaultConfig,
    base_transport: httpx.AsyncBaseTransport | None = None,
) -> FaultInjectionTransport:
    """Create a fault injection transport wrapping the given base transport."""
    if base_transport is None:
        base_transport = httpx.AsyncHTTPTransport()
    return FaultInjectionTransport(wrapped=base_transport, config=config)


# Preset configurations for common test scenarios
TIMEOUT_SCENARIO = FaultConfig(timeout_rate=1.0)
RATE_LIMIT_SCENARIO = FaultConfig(rate_limit_rate=1.0)
FLAKY_SCENARIO = FaultConfig(error_rate=0.5, latency_ms=50)
HIGH_LATENCY_SCENARIO = FaultConfig(latency_ms=2000)
CASCADE_SCENARIO = FaultConfig(error_rate=0.8, timeout_rate=0.2)
