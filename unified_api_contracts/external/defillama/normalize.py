"""DeFiLlama normalizers — all normalize_defillama_* functions.

Extracted from normalize_utils/onchain.py and normalize_utils/errors/_normalize_b.py.

Covers protocol TVL, chain TVL, TVL history, and yield pools.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.crosscutting.errors import (
    CanonicalError,
    ErrorAction,
)
from ...canonical.domain import CanonicalOnChainMetric
from ...normalize_utils.errors._utils import from_http_status
from .schemas import (
    DefiLlamaChainTvl,
    DefiLlamaProtocol,
    DefiLlamaTvlHistoryPoint,
    DefiLlamaYieldPool,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _d(val: float | int | str | Decimal | None) -> Decimal | None:
    """Convert numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _unix_to_utc(ts: int | None) -> datetime:
    """Convert unix timestamp (seconds) to aware UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC)
    except (ValueError, OSError, OverflowError):
        return datetime.now(UTC)


# ---------------------------------------------------------------------------
# DeFiLlama — protocol TVL, stablecoin, yield pools
# ---------------------------------------------------------------------------


def normalize_defillama_protocol(
    raw: DefiLlamaProtocol,
    venue: str = "defillama",
) -> CanonicalOnChainMetric | None:
    """Normalize DefiLlamaProtocol to CanonicalOnChainMetric.

    metric_type = "protocol_tvl"
    value = current TVL in USD
    secondary_value = TVL previous day
    entity = protocol name
    """
    if raw.tvl is None:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "tvl": raw.tvl,
        "change_1d": raw.change_1d,
        "change_7d": raw.change_7d,
        "category": raw.category,
    }
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="protocol_tvl",
        asset=raw.symbol,
        chain=raw.chain,
        value=_d(raw.tvl),
        secondary_value=_d(raw.tvlPrevDay),
        entity=raw.name,
        raw=raw_dict,
    )


def normalize_defillama_chain_tvl(
    raw: DefiLlamaChainTvl,
    venue: str = "defillama",
) -> CanonicalOnChainMetric | None:
    """Normalize DefiLlamaChainTvl to CanonicalOnChainMetric.

    metric_type = "chain_tvl"
    value = chain TVL in USD
    chain = chain name
    """
    if raw.tvl is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="chain_tvl",
        asset=raw.tokenSymbol,
        chain=raw.name,
        value=_d(raw.tvl),
        raw={"tvl": raw.tvl, "name": raw.name},
    )


def normalize_defillama_tvl_history_point(
    raw: DefiLlamaTvlHistoryPoint,
    protocol_name: str = "",
    venue: str = "defillama",
) -> CanonicalOnChainMetric | None:
    """Normalize DefiLlamaTvlHistoryPoint to CanonicalOnChainMetric.

    metric_type = "protocol_tvl_history"
    date is unix timestamp (seconds).
    """
    if raw.totalLiquidityUSD is None:
        return None
    ts = _unix_to_utc(raw.date)
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="protocol_tvl_history",
        entity=protocol_name,
        value=_d(raw.totalLiquidityUSD),
        raw={"date": raw.date, "totalLiquidityUSD": raw.totalLiquidityUSD},
    )


def normalize_defillama_yield_pool(
    raw: DefiLlamaYieldPool,
    venue: str = "defillama",
) -> CanonicalOnChainMetric | None:
    """Normalize DefiLlamaYieldPool to CanonicalOnChainMetric.

    metric_type = "yield_pool"
    value = APY (total)
    secondary_value = TVL in USD
    entity = project name
    """
    if raw.apy is None and raw.tvlUsd is None:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "apy": raw.apy,
        "apyBase": raw.apyBase,
        "apyReward": raw.apyReward,
        "tvlUsd": raw.tvlUsd,
    }
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="yield_pool",
        asset=raw.symbol,
        chain=raw.chain,
        value=_d(raw.apy),
        secondary_value=_d(raw.tvlUsd),
        entity=raw.project,
        raw=raw_dict,
    )


# ---------------------------------------------------------------------------
# Error normalizer
# ---------------------------------------------------------------------------


def normalize_defillama_error(
    error_code: str | int,
    message: str = "",
    venue: str = "defillama",
) -> CanonicalError:
    """Map a DefiLlama HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_defillama_chain_tvl",
    "normalize_defillama_error",
    "normalize_defillama_protocol",
    "normalize_defillama_tvl_history_point",
    "normalize_defillama_yield_pool",
]
