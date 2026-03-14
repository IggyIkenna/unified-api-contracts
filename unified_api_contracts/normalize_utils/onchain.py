"""Alternative data normalizers: on-chain, oracle, and DeFi metrics.

Covers:
- Glassnode — on-chain analytics (MVRV, SOPR, NVT, HODL waves, exchange reserves, etc.)
- Arkham Intelligence — entity labeling and on-chain token flows
- Pyth Network — oracle price feeds (fixed-point conversion: price * 10^expo)
- DeFiLlama — protocol TVL, stablecoin circulating supply, yield pools

All numeric values are converted to Decimal for precision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ..canonical.domain import CanonicalOnChainMetric, CanonicalOraclePriceFeed
from ..external.arkham.schemas import (
    ArkhamAlertEvent,
    ArkhamNetFlow,
    ArkhamTokenFlow,
)
from ..external.defillama.schemas import (
    DefiLlamaChainTvl,
    DefiLlamaProtocol,
    DefiLlamaTvlHistoryPoint,
    DefiLlamaYieldPool,
)
from ..external.glassnode.schemas import (
    ExchangeReserves,
    GlassnodeTimeseriesPoint,
    HodlWave,
    MvrvRatio,
    MvrvZScore,
    NvtRatio,
    NvtSignal,
    RealizedCap,
    SoprMetric,
    ThermoCap,
)
from ..external.pyth.schemas import PythPriceFeed

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
# Glassnode — on-chain analytics
# ---------------------------------------------------------------------------


def normalize_glassnode_timeseries_point(
    raw: GlassnodeTimeseriesPoint,
    metric_type: str,
    asset: str = "BTC",
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a GlassnodeTimeseriesPoint to CanonicalOnChainMetric.

    GlassnodeTimeseriesPoint: {t: unix_seconds, v: float}.
    Skips points where v is None.

    Args:
        raw:         GlassnodeTimeseriesPoint from a metric response.
        metric_type: Metric name e.g. "mvrv", "sopr", "nvt".
        asset:       Asset symbol (e.g. "BTC", "ETH").
        venue:       Provider tag, defaults to "glassnode".
    """
    if raw.v is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.t),
        venue=venue,
        metric_type=metric_type,
        asset=asset,
        value=_d(raw.v),
        raw={"t": raw.t, "v": raw.v},
    )


def normalize_glassnode_mvrv(
    raw: MvrvRatio,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a MvrvRatio to CanonicalOnChainMetric (metric_type="mvrv")."""
    if raw.mvrv is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="mvrv",
        asset="BTC",
        value=_d(raw.mvrv),
        raw={"mvrv": raw.mvrv},
    )


def normalize_glassnode_mvrv_z_score(
    raw: MvrvZScore,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a MvrvZScore to CanonicalOnChainMetric (metric_type="mvrv_z_score")."""
    if raw.mvrv_z_score is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="mvrv_z_score",
        asset="BTC",
        value=_d(raw.mvrv_z_score),
        raw={"mvrv_z_score": raw.mvrv_z_score},
    )


def normalize_glassnode_sopr(
    raw: SoprMetric,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a SoprMetric to CanonicalOnChainMetric (metric_type="sopr")."""
    if raw.sopr is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="sopr",
        asset="BTC",
        value=_d(raw.sopr),
        raw={"sopr": raw.sopr},
    )


def normalize_glassnode_nvt(
    raw: NvtRatio,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a NvtRatio to CanonicalOnChainMetric (metric_type="nvt")."""
    if raw.nvt is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="nvt",
        asset="BTC",
        value=_d(raw.nvt),
        raw={"nvt": raw.nvt},
    )


def normalize_glassnode_nvt_signal(
    raw: NvtSignal,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a NvtSignal to CanonicalOnChainMetric (metric_type="nvt_signal")."""
    if raw.nvt_signal is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="nvt_signal",
        asset="BTC",
        value=_d(raw.nvt_signal),
        raw={"nvt_signal": raw.nvt_signal},
    )


def normalize_glassnode_exchange_reserves(
    raw: ExchangeReserves,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize ExchangeReserves to CanonicalOnChainMetric (metric_type="exchange_reserves").

    value = balance_sum, secondary_value = net_flow_24h.
    """
    if raw.balance_sum is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="exchange_reserves",
        asset=raw.asset or "BTC",
        value=_d(raw.balance_sum),
        secondary_value=_d(raw.net_flow_24h),
        raw={"balance_sum": raw.balance_sum, "net_flow_24h": raw.net_flow_24h},
    )


def normalize_glassnode_realized_cap(
    raw: RealizedCap,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize RealizedCap to CanonicalOnChainMetric (metric_type="realized_cap")."""
    if raw.realized_cap_usd is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="realized_cap",
        asset="BTC",
        value=_d(raw.realized_cap_usd),
        raw={"realized_cap_usd": raw.realized_cap_usd},
    )


def normalize_glassnode_thermocap(
    raw: ThermoCap,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize ThermoCap to CanonicalOnChainMetric (metric_type="thermocap")."""
    if raw.thermocap_usd is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="thermocap",
        asset="BTC",
        value=_d(raw.thermocap_usd),
        raw={"thermocap_usd": raw.thermocap_usd},
    )


def normalize_glassnode_hodl_wave(
    raw: HodlWave,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize HodlWave to CanonicalOnChainMetric (metric_type="hodl_wave").

    value = 1d band (most short-term); secondary_value = 10y+ band (most long-term).
    Full band data stored in raw dict.
    """
    if raw.timestamp is None:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "band_1d": raw.band_1d,
        "band_1d_1w": raw.band_1d_1w,
        "band_1w_1m": raw.band_1w_1m,
        "band_1m_3m": raw.band_1m_3m,
        "band_3m_6m": raw.band_3m_6m,
        "band_6m_12m": raw.band_6m_12m,
        "band_1y_2y": raw.band_1y_2y,
        "band_2y_3y": raw.band_2y_3y,
        "band_3y_5y": raw.band_3y_5y,
        "band_5y_7y": raw.band_5y_7y,
        "band_7y_10y": raw.band_7y_10y,
        "band_10y_plus": raw.band_10y_plus,
    }
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="hodl_wave",
        asset="BTC",
        value=_d(raw.band_1d),
        secondary_value=_d(raw.band_10y_plus),
        raw=raw_dict,
    )


# ---------------------------------------------------------------------------
# Arkham Intelligence — entity labeling and token flows
# ---------------------------------------------------------------------------


def normalize_arkham_token_flow(
    raw: ArkhamTokenFlow,
    venue: str = "arkham",
) -> CanonicalOnChainMetric | None:
    """Normalize ArkhamTokenFlow (on-chain transaction) to CanonicalOnChainMetric.

    metric_type = "entity_flow"
    value = usd_value of the transfer
    entity = from_entity → to_entity direction label
    """
    if raw.usd_value is None and raw.amount is None:
        return None
    ts = _unix_to_utc(raw.timestamp)
    entity_label = f"{raw.from_entity or 'unknown'}->{raw.to_entity or 'unknown'}"
    raw_dict: dict[str, float | int | str | None] = {
        "tx_hash": raw.tx_hash,
        "from_entity": raw.from_entity,
        "to_entity": raw.to_entity,
        "amount": raw.amount,
        "usd_value": raw.usd_value,
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="entity_flow",
        asset=raw.token_symbol,
        chain=raw.chain,
        value=_d(raw.usd_value),
        secondary_value=_d(raw.amount),
        entity=entity_label,
        raw=raw_dict,
    )


def normalize_arkham_net_flow(
    raw: ArkhamNetFlow,
    venue: str = "arkham",
) -> CanonicalOnChainMetric | None:
    """Normalize ArkhamNetFlow to CanonicalOnChainMetric.

    metric_type = "net_flow"
    value = net_flow_usd (negative = net outflow = bullish)
    secondary_value = inflow_usd
    """
    if raw.net_flow_usd is None:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "inflow_usd": raw.inflow_usd,
        "outflow_usd": raw.outflow_usd,
        "net_flow_usd": raw.net_flow_usd,
        "time_window": raw.time_window,
    }
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="net_flow",
        asset=raw.token_symbol,
        chain=raw.chain,
        value=_d(raw.net_flow_usd),
        secondary_value=_d(raw.inflow_usd),
        entity=raw.entity,
        raw=raw_dict,
    )


def normalize_arkham_alert_event(
    raw: ArkhamAlertEvent,
    venue: str = "arkham",
) -> CanonicalOnChainMetric | None:
    """Normalize ArkhamAlertEvent (large transfer / whale activity) to CanonicalOnChainMetric.

    metric_type = alert_type (e.g. "large_transfer", "new_whale_accumulation")
    value = usd_value
    entity = from_entity → to_entity
    """
    if raw.usd_value is None:
        return None
    ts = _unix_to_utc(raw.timestamp)
    entity_label = f"{raw.from_entity or 'unknown'}->{raw.to_entity or 'unknown'}"
    alert_type = raw.alert_type or "alert"
    raw_dict: dict[str, float | int | str | None] = {
        "alert_id": raw.alert_id,
        "alert_type": raw.alert_type,
        "usd_value": raw.usd_value,
        "from_entity": raw.from_entity,
        "to_entity": raw.to_entity,
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type=alert_type,
        asset=raw.token_symbol,
        chain=raw.chain,
        value=_d(raw.usd_value),
        entity=entity_label,
        raw=raw_dict,
    )


# ---------------------------------------------------------------------------
# Pyth Network — oracle price feeds
# ---------------------------------------------------------------------------


def normalize_pyth_price_feed(
    raw: PythPriceFeed,
    venue: str = "pyth",
) -> CanonicalOraclePriceFeed | None:
    """Normalize PythPriceFeed to CanonicalOraclePriceFeed.

    Pyth fixed-point: actual_price = price_mantissa * 10^expo.
    publish_time is microseconds since epoch.

    Args:
        raw:   PythPriceFeed from the WebSocket or REST response.
        venue: Provider tag, defaults to "pyth".
    """
    if raw.price is None or raw.expo is None:
        return None

    try:
        exponent = int(raw.expo)
        price_decimal = Decimal(str(raw.price)) * (Decimal(10) ** exponent)
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return None

    confidence: Decimal | None = None
    if raw.conf is not None:
        try:
            confidence = Decimal(str(raw.conf)) * (Decimal(10) ** exponent)
        except (InvalidOperation, ValueError, TypeError, ArithmeticError):
            confidence = None

    # publish_time is microseconds
    ts: datetime
    if raw.publish_time is not None:
        try:
            ts = datetime.fromtimestamp(raw.publish_time / 1_000_000, tz=UTC)
        except (ValueError, OSError, OverflowError):
            ts = datetime.now(UTC)
    else:
        ts = datetime.now(UTC)

    return CanonicalOraclePriceFeed(
        timestamp=ts,
        venue=venue,
        feed_id=raw.id or "",
        price=price_decimal,
        confidence=confidence,
    )


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


__all__ = [
    "normalize_arkham_alert_event",
    "normalize_arkham_net_flow",
    "normalize_arkham_token_flow",
    "normalize_defillama_chain_tvl",
    "normalize_defillama_protocol",
    "normalize_defillama_tvl_history_point",
    "normalize_defillama_yield_pool",
    "normalize_glassnode_exchange_reserves",
    "normalize_glassnode_hodl_wave",
    "normalize_glassnode_mvrv",
    "normalize_glassnode_mvrv_z_score",
    "normalize_glassnode_nvt",
    "normalize_glassnode_nvt_signal",
    "normalize_glassnode_realized_cap",
    "normalize_glassnode_sopr",
    "normalize_glassnode_thermocap",
    "normalize_glassnode_timeseries_point",
    "normalize_pyth_price_feed",
]
