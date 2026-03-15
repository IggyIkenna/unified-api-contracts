"""CryptoQuant normalizers — all normalize_cryptoquant_* functions.

On-chain analytics (exchange flow, miner metrics, reserves, whale, stablecoin)
-> CanonicalOnChainMetric. Similar to Glassnode.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalOnChainMetric
from ...normalize_utils._helpers import _to_decimal
from .schemas import (
    CryptoQuantExchangeFlow,
    CryptoQuantMinerMetrics,
    CryptoQuantReserveMetrics,
    CryptoQuantStablecoinMetrics,
    CryptoQuantWhaleMetrics,
)


def _ensure_utc(dt: datetime | None) -> datetime:
    """Ensure datetime is UTC-aware."""
    if dt is None:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_cryptoquant_exchange_flow(
    raw: CryptoQuantExchangeFlow,
    venue: str = "cryptoquant",
) -> CanonicalOnChainMetric:
    """Convert CryptoQuantExchangeFlow to CanonicalOnChainMetric.

    metric_type = "exchange_flow"
    value = flow value (BTC or native)
    asset = symbol, entity = exchange
    """
    return CanonicalOnChainMetric(
        timestamp=_ensure_utc(raw.timestamp_utc),
        venue=venue,
        metric_type="exchange_flow",
        asset=raw.symbol,
        value=_to_decimal(raw.value),
        entity=raw.exchange,
        raw={"flow_type": raw.flow_type, "value": raw.value},
    )


def normalize_cryptoquant_miner_metrics(
    raw: CryptoQuantMinerMetrics,
    venue: str = "cryptoquant",
) -> list[CanonicalOnChainMetric]:
    """Convert CryptoQuantMinerMetrics to list of CanonicalOnChainMetric.

    One metric per non-None field: miner_revenue, hash_rate, miner_position_index,
    puell_multiple. Primary: miner_revenue_btc or miner_revenue.
    """
    ts = _ensure_utc(raw.timestamp_utc)
    results: list[CanonicalOnChainMetric] = []
    raw_dict: dict[str, float | int | str | None] = {
        "miner_revenue": raw.miner_revenue,
        "miner_revenue_btc": raw.miner_revenue_btc,
        "hash_rate": raw.hash_rate,
        "difficulty": raw.difficulty,
        "miner_position_index": raw.miner_position_index,
        "puell_multiple": raw.puell_multiple,
    }
    if raw.miner_revenue_btc is not None:
        results.append(
            CanonicalOnChainMetric(
                timestamp=ts,
                venue=venue,
                metric_type="miner_revenue_btc",
                asset="BTC",
                value=_to_decimal(raw.miner_revenue_btc),
                raw=raw_dict,
            )
        )
    if raw.hash_rate is not None:
        results.append(
            CanonicalOnChainMetric(
                timestamp=ts,
                venue=venue,
                metric_type="hash_rate",
                asset="BTC",
                value=_to_decimal(raw.hash_rate),
                raw=raw_dict,
            )
        )
    if raw.miner_position_index is not None:
        results.append(
            CanonicalOnChainMetric(
                timestamp=ts,
                venue=venue,
                metric_type="miner_position_index",
                asset="BTC",
                value=_to_decimal(raw.miner_position_index),
                raw=raw_dict,
            )
        )
    if raw.puell_multiple is not None:
        results.append(
            CanonicalOnChainMetric(
                timestamp=ts,
                venue=venue,
                metric_type="puell_multiple",
                asset="BTC",
                value=_to_decimal(raw.puell_multiple),
                raw=raw_dict,
            )
        )
    if not results and raw.miner_revenue is not None:
        results.append(
            CanonicalOnChainMetric(
                timestamp=ts,
                venue=venue,
                metric_type="miner_revenue",
                asset="BTC",
                value=_to_decimal(raw.miner_revenue),
                raw=raw_dict,
            )
        )
    return results


def normalize_cryptoquant_reserve_metrics(
    raw: CryptoQuantReserveMetrics,
    venue: str = "cryptoquant",
) -> CanonicalOnChainMetric:
    """Convert CryptoQuantReserveMetrics to CanonicalOnChainMetric.

    metric_type = "exchange_reserve"
    value = reserve, asset = symbol, entity = exchange
    """
    return CanonicalOnChainMetric(
        timestamp=_ensure_utc(raw.timestamp_utc),
        venue=venue,
        metric_type="exchange_reserve",
        asset=raw.symbol,
        value=_to_decimal(raw.reserve),
        secondary_value=_to_decimal(raw.reserve_change_1d),
        entity=raw.exchange,
        raw={
            "reserve": raw.reserve,
            "reserve_change_1d": raw.reserve_change_1d,
            "reserve_change_7d": raw.reserve_change_7d,
            "reserve_change_30d": raw.reserve_change_30d,
        },
    )


def normalize_cryptoquant_whale_metrics(
    raw: CryptoQuantWhaleMetrics,
    venue: str = "cryptoquant",
) -> CanonicalOnChainMetric | None:
    """Convert CryptoQuantWhaleMetrics to CanonicalOnChainMetric.

    metric_type = "whale_ratio" (primary), value = whale_ratio
    Returns None if no primary value.
    """
    if raw.whale_ratio is None and raw.whale_balance is None:
        return None
    value = _to_decimal(raw.whale_ratio) if raw.whale_ratio is not None else _to_decimal(raw.whale_balance)
    metric_type = "whale_ratio" if raw.whale_ratio is not None else "whale_balance"
    return CanonicalOnChainMetric(
        timestamp=_ensure_utc(raw.timestamp_utc),
        venue=venue,
        metric_type=metric_type,
        asset="BTC",
        value=value,
        secondary_value=_to_decimal(raw.whale_balance) if raw.whale_ratio is not None else None,
        raw={
            "whale_count": raw.whale_count,
            "whale_balance": raw.whale_balance,
            "whale_ratio": raw.whale_ratio,
            "large_transactions": raw.large_transactions,
            "large_transaction_volume": raw.large_transaction_volume,
        },
    )


def normalize_cryptoquant_stablecoin_metrics(
    raw: CryptoQuantStablecoinMetrics,
    venue: str = "cryptoquant",
) -> CanonicalOnChainMetric:
    """Convert CryptoQuantStablecoinMetrics to CanonicalOnChainMetric.

    metric_type = "stablecoin_supply"
    value = total_supply, asset = stablecoin
    """
    return CanonicalOnChainMetric(
        timestamp=_ensure_utc(raw.timestamp_utc),
        venue=venue,
        metric_type="stablecoin_supply",
        asset=raw.stablecoin,
        value=_to_decimal(raw.total_supply),
        secondary_value=_to_decimal(raw.supply_change_1d),
        raw={
            "total_supply": raw.total_supply,
            "supply_change_1d": raw.supply_change_1d,
            "supply_change_7d": raw.supply_change_7d,
            "supply_ratio": raw.supply_ratio,
        },
    )


__all__ = [
    "normalize_cryptoquant_exchange_flow",
    "normalize_cryptoquant_miner_metrics",
    "normalize_cryptoquant_reserve_metrics",
    "normalize_cryptoquant_stablecoin_metrics",
    "normalize_cryptoquant_whale_metrics",
]
