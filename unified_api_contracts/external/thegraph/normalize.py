"""The Graph subgraph normalizers — SubgraphPool, SubgraphSwap, GraphUniswapPool, etc.

Maps The Graph subgraph entities to canonical types:
- SubgraphPool, GraphUniswapPool, GraphUniswapV2Pair -> CanonicalInstrument
- SubgraphSwap, GraphUniswapSwap, GraphUniswapV2Swap -> CanonicalTrade
- SubgraphToken, GraphToken -> CanonicalInstrument (token as instrument)
- GraphPoolHourData, GraphPairHourData -> CanonicalOnChainMetric
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import (
    CanonicalInstrument,
    CanonicalOnChainMetric,
    CanonicalTrade,
)
from ...canonical.domain.reference import InstructionType, InstrumentType
from .schemas import (
    GraphPairHourData,
    GraphPoolHourData,
    GraphToken,
    GraphUniswapPool,
    GraphUniswapSwap,
    GraphUniswapV2Pair,
    GraphUniswapV2Swap,
    SubgraphPool,
    SubgraphSwap,
    SubgraphToken,
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


def _unix_to_utc(ts: int | str | None) -> datetime:
    """Convert unix timestamp (seconds) to aware UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC)
    except (ValueError, OSError, OverflowError, TypeError):
        return datetime.now(UTC)


def _token_symbol(tok: dict[str, object] | object | None) -> str:
    """Extract symbol from token dict or GraphToken."""
    if tok is None:
        return "UNKNOWN"
    if isinstance(tok, dict):
        s = tok.get("symbol") or tok.get("Symbol")
        return str(s) if s else "UNKNOWN"
    return str(getattr(tok, "symbol", "UNKNOWN"))


# ---------------------------------------------------------------------------
# The Graph — pool/pair -> CanonicalInstrument
# ---------------------------------------------------------------------------


def normalize_thegraph_pool_to_instrument(
    raw: SubgraphPool | GraphUniswapPool | GraphUniswapV2Pair,
    venue: str = "thegraph",
    chain: str = "ethereum",
) -> CanonicalInstrument | None:
    """Normalize SubgraphPool, GraphUniswapPool, or GraphUniswapV2Pair to CanonicalInstrument."""
    pool_id = getattr(raw, "id", None) or ""
    if not pool_id:
        return None
    token0 = getattr(raw, "token0", None)
    token1 = getattr(raw, "token1", None)
    sym0 = _token_symbol(token0)
    sym1 = _token_symbol(token1)
    symbol = f"{sym0}-{sym1}"
    instrument_key = f"{venue}:SPOT_PAIR:{chain}:{pool_id}"
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=InstrumentType.SPOT_PAIR,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        instruction_type=InstructionType.SWAP,
        pool_id=str(pool_id),
        base_asset=sym0,
        quote_asset=sym1,
        schema_version="1.0",
    )


def normalize_thegraph_token_to_instrument(
    raw: SubgraphToken | GraphToken,
    venue: str = "thegraph",
    chain: str = "ethereum",
) -> CanonicalInstrument | None:
    """Normalize SubgraphToken or GraphToken to CanonicalInstrument."""
    token_id = getattr(raw, "id", None) or ""
    symbol = getattr(raw, "symbol", None) or "UNKNOWN"
    if not token_id and symbol == "UNKNOWN":
        return None
    instrument_key = f"{venue}:SPOT_PAIR:{chain}:{token_id or symbol}"
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=InstrumentType.SPOT_PAIR,
        symbol=str(symbol),
        timestamp=datetime.now(UTC),
        instruction_type=InstructionType.SWAP,
        schema_version="1.0",
    )


# ---------------------------------------------------------------------------
# The Graph — swap -> CanonicalTrade
# ---------------------------------------------------------------------------


def normalize_thegraph_swap_to_trade(
    raw: SubgraphSwap | GraphUniswapSwap | GraphUniswapV2Swap,
    venue: str = "thegraph",
    symbol: str = "UNKNOWN",
) -> CanonicalTrade | None:
    """Normalize SubgraphSwap, GraphUniswapSwap, or GraphUniswapV2Swap to CanonicalTrade."""
    swap_id = getattr(raw, "id", None) or ""
    if not swap_id:
        return None
    amount_usd = _d(getattr(raw, "amountUSD", 0))
    amount0 = _d(getattr(raw, "amount0", None) or getattr(raw, "amount0In", 0) or getattr(raw, "amount0Out", 0))
    amount1 = _d(getattr(raw, "amount1", None) or getattr(raw, "amount1In", 0) or getattr(raw, "amount1Out", 0))
    ts = _unix_to_utc(getattr(raw, "timestamp", None))
    price = amount_usd if amount_usd and amount_usd > 0 else Decimal("1")
    qty = amount0 if amount0 and amount0 > 0 else (amount1 if amount1 and amount1 > 0 else Decimal("1"))
    a0_in = _d(getattr(raw, "amount0In", 0))
    side = "sell" if (a0_in and a0_in > 0) else "buy"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol,
        trade_id=swap_id,
        timestamp=ts,
        price=price,
        quantity=qty,
        side=side,
        buyer_maker=None,
        venue_trade_id=swap_id,
        instrument_key=None,
        is_liquidation=None,
        schema_version="1.0",
    )


# ---------------------------------------------------------------------------
# The Graph — pool hour data -> CanonicalOnChainMetric
# ---------------------------------------------------------------------------


def normalize_thegraph_pool_hour_to_metric(
    raw: GraphPoolHourData,
    metric_type: str = "pool_tvl",
    venue: str = "thegraph",
) -> CanonicalOnChainMetric | None:
    """Normalize GraphPoolHourData to CanonicalOnChainMetric."""
    ts = _unix_to_utc(getattr(raw, "periodStartUnix", None))
    val = _d(getattr(raw, "tvlUSD", None) or getattr(raw, "liquidity", None) or getattr(raw, "volumeUSD", 0))
    if val is None or val <= 0:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "liquidity": str(getattr(raw, "liquidity", "")),
        "volumeUSD": str(getattr(raw, "volumeUSD", "")),
        "token0Price": str(getattr(raw, "token0Price", "")),
        "token1Price": str(getattr(raw, "token1Price", "")),
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type=metric_type,
        asset=None,
        value=val,
        secondary_value=_d(getattr(raw, "volumeUSD", None)),
        entity=getattr(raw, "id", ""),
        raw=raw_dict,
        schema_version="1.0",
    )


def normalize_thegraph_pair_hour_to_metric(
    raw: GraphPairHourData,
    metric_type: str = "pair_tvl",
    venue: str = "thegraph",
) -> CanonicalOnChainMetric | None:
    """Normalize GraphPairHourData to CanonicalOnChainMetric."""
    ts = _unix_to_utc(getattr(raw, "hourStartUnix", None))
    val = _d(getattr(raw, "reserveUSD", None) or getattr(raw, "hourlyVolumeUSD", 0))
    if val is None or val <= 0:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "reserve0": str(getattr(raw, "reserve0", "")),
        "reserve1": str(getattr(raw, "reserve1", "")),
        "hourlyVolumeUSD": str(getattr(raw, "hourlyVolumeUSD", "")),
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type=metric_type,
        asset=None,
        value=val,
        secondary_value=_d(getattr(raw, "hourlyVolumeUSD", None)),
        entity=getattr(raw, "id", ""),
        raw=raw_dict,
        schema_version="1.0",
    )


__all__ = [
    "normalize_thegraph_pair_hour_to_metric",
    "normalize_thegraph_pool_hour_to_metric",
    "normalize_thegraph_pool_to_instrument",
    "normalize_thegraph_swap_to_trade",
    "normalize_thegraph_token_to_instrument",
]
